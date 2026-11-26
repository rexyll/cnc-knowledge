# 备件库存备份 Coordinator：真实 etcd v3 Gateway 驱动与三节点集成环境

**知识编号：** KNOW-000061  
**章节：** CH17 操作、维护与维修  
**关联知识：** KNOW-000051、KNOW-000059、KNOW-000060  
**正式场景矩阵：** ASSET-000092  
**实现状态：** etcd3gw Range/Txn/Lease 与低层HTTP Watch server-streaming均已提交；真实三成员CI集成8/8通过；WatchProgress/WatchCancel双向控制未实现  
**生产状态：** 未启用，schema-v2仍是唯一生产权威

## 1. 本轮目标与边界

在既有 EtcdV3CoordinatorAuthorityStore / EtcdV3Client 注入接口上提供一个可安装、可连接实际 etcd v3 HTTP gRPC-gateway 的 Python 驱动，并建立本地三节点 etcd 测试拓扑。驱动采用 OpenStack 项目维护的 etcd3gw 2.7.0，版本固定在独立的 requirements-ch17-etcd-integration.txt，不增加普通知识库CI的安装依赖。SRC-000408记录该客户端的PyPI发行信息、OpenStack源码位置和接口；etcd三节点静态启动方式见SRC-000409。

当前驱动实现以下真实协议请求映射：
- KV Range：精确Key与range_end前缀/范围读取、Base64字节编解码、header revision归一化、强一致读(serializable=false)；
- KV Txn：VERSION/CREATE/MOD/VALUE Compare、Range/Put/DeleteRange操作、Txn响应和嵌套Range KV解码；
- Lease：Grant、同步KeepAlive、Revoke；
- Watch：低层HTTP server-streaming WatchCreate请求和完整响应包络保真，不依赖高层事件回调；
- 多endpoint：只读Range/status/member-list和Watch连接建立阶段在连接超时/连接失败时尝试下一endpoint；Txn/Lease操作不自动重试，Watch流建立后不自动迁移或重放。

**这不是生产Authority后端切换。** 本轮没有将现有SQLite Coordinator业务状态迁移到Store Port；未将驱动接入实际业务服务；没有现场数据或真实生产读写。普通CI不会启动etcd容器。CI通过只能证明驱动映射和错误语义单测通过。

## 2. 客户端选型与Watch能力审查

etcd3gw是OpenStack维护的Python etcd v3 gRPC-gateway客户端，当前固定版本为2.7.0。它通过HTTP JSON transcoding访问v3 API；它不是etcd-io官方Go/Java客户端，也不是直接的Python gRPC WatchResponse类型绑定。引用：SRC-000408。

对etcd3gw 2.7.0高层Watch helper的审查结论仍然成立：该helper将stream响应转换成事件回调，会跳过created握手并丢失部分WatchResponse控制字段。因此，本驱动不使用该高层Watcher，而是复用已配置的HTTP session直接请求/v3/watch server-streaming endpoint。

低层适配器逐个解析HTTP响应中的JSON对象，能够跨任意网络chunk边界重组UTF-8/JSON帧，并保留完整result包络：header revision、watch_id、created、canceled、compact_revision、cancel_reason、fragment、events和KV/prev_kv；二进制键值解码为bytes。protobuf JSON可能省略零值PUT枚举，因此缺失/0 event type按默认PUT解释；DELETE显式保留，未知枚举失败关闭。

Watch创建阶段可以在连接超时/连接失败时尝试下一个endpoint；HTTP流建立后不自动重连或重放事件，传输断线显式传播给上层。上层必须执行linearizable Range snapshot并从R+1恢复，不能依据断线前的局部事件缓存继续授权。

WatchCreate支持start_revision、progress_notify、filters、prev_kv、range_end、watch_id及fragment。请求progress_notify=true允许服务端按自身机制周期发送进度响应，但当前HTTP实现没有双向WatchProgress/WatchCancel消息，也没有服务端cancel ack；调用方取消/结束消费时只关闭响应流，不把本地close描述为服务端已确认撤销。

## 3. 网络驱动实现

代码：scripts/spare_parts_provider_etcd3gw_driver.py  
可选依赖：requirements-ch17-etcd-integration.txt  
单测：tests/test_spare_parts_provider_etcd3gw_driver.py

### 3.1 Endpoint和传输配置

驱动接受逗号分隔或序列形式的http(s) endpoint。每个endpoint单独创建etcd3gw客户端，API路径固定为/v3/，timeout通过客户端构造参数传递。支持CA证书路径及客户端证书/私钥路径；mTLS证书必须成对配置。endpoint不得带用户密码、query、fragment或额外path。

当前版本没有接入etcd用户名/密码、RBAC用户管理或额外HTTP metadata。证书文件是否可信、证书轮换、RBAC角色是否满足Coordinator最小权限均需要部署方另行设计和现场验证。

### 3.2 Range强一致读

Range的key及range_end按etcd v3 JSON/gRPC-gateway规则Base64编码。默认serializable=false，响应KV的key/value解码为bytes；create_revision、mod_revision、version、lease及header.revision统一为整数。

读请求遇到ConnectionTimeoutError或ConnectionFailedError时，可以尝试配置的其他endpoint；不会把linearizable Range降级为serializable=true。所有endpoint均不可达时，将连接错误交给EtcdV3CoordinatorAuthorityStore，最终按UNAVAILABLE处理。非传输类协议/服务错误不会被无差别吞掉或无限重试。

### 3.3 Txn Compare/Success/Failure

Compare支持VERSION、CREATE、MOD和VALUE目标；key以及VALUE比较值按bytes编码，数字比较值保持整数。Success/Failure分支支持request_range、request_put、request_delete_range。

Txn使用etcd3gw公开客户端的Txn请求序列化方式发送JSON payload；响应中的header revision和嵌套Range KV被归一化为现有Store Port使用的字段名及bytes类型。收到Txn网络超时或连接中断时，不切换endpoint再次发送同一写请求。既有EtcdV3CoordinatorAuthorityStore会把这类传输异常转为OUTCOME_UNKNOWN，业务层需使用原幂等键和业务身份字段进行线性一致读回，不能盲目重放非幂等操作。

### 3.4 Lease生命周期

Grant映射到/lease/grant，KeepAlive映射到/lease/keepalive同步请求，Revoke映射到/kv/lease/revoke。Lease ID与TTL在适配层转换为整数；KeepAlive没有有效TTL时返回0，交由上层按续租未确认/fail-closed语义处理。

Grant和Revoke属于写操作，不自动跨endpoint重试。Grant响应丢失可能产生尚未附着业务key的孤儿Lease；Revoke响应丢失不能据此认定已撤销。恢复决策必须读取业务附着key/Leader状态，而非通过重发猜测结果。

### 3.5 Watch server-streaming与响应包络

Etcd3gwV3Client.watch()返回可关闭的响应迭代器。客户端使用已配置session发送单个WatchCreate JSON请求，并以HTTP stream读取服务端连续JSON响应。解析器不假设一个HTTP chunk就是一个JSON对象，而是增量解码UTF-8并从缓冲区读取完整JSON frame，避免跨chunk边界拆分字段时损坏包络。

响应保留header.revision、watch_id、created、canceled、compact_revision、cancel_reason、fragment、events及事件中的KV/prev_kv，二进制key/value解码为bytes。protobuf JSON可能省略零值PUT枚举字段，因此缺失/0 event type按PUT默认值解码；DELETE使用显式非零类型，未知类型失败关闭。

WatchCreate请求支持start_revision、progress_notify、filters、prev_kv、range_end、watch_id和fragment。当前HTTP实现不提供后续双向WatchProgress/WatchCancel请求及服务端cancel acknowledgement；调用方取消/结束消费时通过关闭响应流释放资源。progress_notify只请求服务端周期发送进度响应，不表示客户端能够在同一连接上主动发送双向控制消息。

连接建立阶段的endpoint failover仅用于创建Watch的只读请求；建立流后的超时/断线不进行自动切换或重放。应由CoordinatorAuthorityWatchStore检测流失败，先做linearizable Range恢复，再从revision R+1重建Watch。Watch事件仅作通知，永远不能替代Coordinator的线性一致Range/Txn授权判断。

## 4. 三节点集成环境

目录：scripts/etcd-integration/  
Compose：scripts/etcd-integration/compose.yaml  
运行器：scripts/etcd-integration/run.sh  
说明：scripts/etcd-integration/README.md  
版本：quay.io/coreos/etcd:v3.7.0

拓扑包含etcd1/etcd2/etcd3三个独立成员、独立数据卷、内部peer端口2380和宿主机client端口23791/23792/23793。配置使用静态initial-cluster引导方式，符合etcd官方容器文档的三成员启动模式（SRC-000409）。

从仓库根目录运行：

    bash scripts/etcd-integration/run.sh

该命令安装可选依赖、启动三节点、轮询每个client endpoint及member list，确认集群包含3个成员后执行可选集成测试。默认退出时删除测试容器与volume；设置ETCD_KEEP_CLUSTER=1可保留环境。普通CI不触发此脚本。

该Compose文件仅用于本机可丢弃环境：明文HTTP、无认证/RBAC、固定端口，虽使用named volume仍不构成生产持久性或灾备配置。不得连接生产数据或真实Coordinator authority。

## 5. 测试覆盖与状态

### 5.1 默认CI执行的网络映射契约单测

tests/test_spare_parts_provider_etcd3gw_driver.py包含13项契约测试，使用fake gateway transport，不需要安装etcd3gw或启动服务端：
- Range key/value二进制Base64往返和header revision；
- prefix range_end映射及多条KV解码；
- Compare + Put事务字段映射与响应revision；
- Txn中Range响应的嵌套KV解码；
- Lease Grant/KeepAlive/Revoke路径和返回字段；
- 线性一致Range在第一个endpoint连接失败时尝试第二endpoint；
- Txn超时后不自动发送到第二endpoint，并由现有Store适配器转为OUTCOME_UNKNOWN；
- Watch stream跨chunk解码、created/fragment/canceled/compaction/header保留、PUT/DELETE KV与prev_kv Base64解码、连接建立failover、流断线传播和close-before-first-frame资源释放；不暴露双向watch_progress；
- 拒绝含认证信息、非/v3路径、错误scheme或query的endpoint；
- from_env缺少endpoint配置时失败关闭。

这些测试以可控HTTP响应对象验证序列化/归一化逻辑，不是真实网络协议互通或服务端行为证据。

### 5.2 需要人工显式启动的真实集成测试

真实集成测试文件共包含8项可选场景：
- tests/test_spare_parts_provider_authority_store_etcd_integration.py：6项，覆盖3成员发现、二进制Range/Txn、双客户端CAS、Lease生命周期、endpoint failover，以及真实Watch created/PUT/DELETE/prev_kv与关闭流；
- tests/test_spare_parts_provider_authority_store_member_outage_etcd_integration.py：1项，停止一个成员验证剩余2/3多数派线性一致读写和节点恢复；
- tests/test_spare_parts_provider_authority_store_quorum_loss_etcd_integration.py：1项，停止两个成员验证失去quorum时读写失败关闭，恢复后重新CAS写入。

只有在ETCD_INTEGRATION=1且ETCD_ENDPOINTS显式设置时执行。最终真实CI [Run 45842517310](https://github.com/rexyll/cnc-knowledge/actions/runs/45842517310)使用一次性etcd v3.7.0三成员Compose运行8/8 PASS；诊断Artifact [15128407498](https://github.com/rexyll/cnc-knowledge/actions/runs/45842517310/artifacts/15128407498)。这只是一次性集成证据，不是正式企业场景矩阵验收。

### 5.3 正式场景矩阵

ASSET-000092包含30项拟议场景，均为PROPOSED_NOT_APPROVED / NOT_RUN。矩阵覆盖endpoint配置、Base64、Range一致性/failover、Txn compare/未知结果、Lease生命周期、三成员集群、成员故障与Watch能力门禁。Fake contract和live smoke均不改变正式场景的审批/执行状态；正式矩阵必须经企业审批后才可执行。

### 5.4 默认CI结果

- 最新默认回归：[Run 45842517156](https://github.com/rexyll/cnc-knowledge/actions/runs/45842517156)两个必需Job均completed/success；全库505项unittest，497通过、8项opt-in live测试按默认策略skip；CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构和数据质量0 errors，另有5项既有DRAFT/企业审批warning。

- 最终代码head：`871fe0d2673fb1b39502236568dc7dd57ad3bef0`；[GitHub Actions Run 45832644686](https://github.com/rexyll/cnc-knowledge/actions/runs/45832644686)两个必需Job均completed/success。
- 全库499项unittest完成，494项通过、5项跳过；5项skip是需ETCD_INTEGRATION=1的真实etcd集成测试，不作为通过证据。本轮10项fake gateway驱动映射单测全部通过。
- CH12 143项数值资源测试通过；strict knowledge lint 0 errors；独立CH17合成夹具校验为0 errors、5 warnings。5项警告均为既有治理门禁：数据集仍为DRAFT、未批准企业测试环境/级别、30项SPAT源测试案例仍NOT_RUN、manifest checksum pending，并非etcd驱动测试失败。
- 默认CI不安装etcd3gw可选依赖、不启动Docker/etcd服务；因此本次CI仅证明驱动映射、错误处理和知识库回归通过，不证明与真实etcd服务端互通。

## 6. 当前限制与生产门禁

| 项目 | 当前状态 | 下一步要求 |
|---|---|---|
| etcd3gw网络驱动 | Range/Txn/Lease与HTTP Watch server-streaming已实现；13项fake契约测试与8项真实etcd live测试通过（Run 45842517310） | 继续验证更复杂网络分区、mTLS/RBAC、长时流背压 |
| endpoint failover | 只读请求/Watch建立阶段可跨endpoint尝试；已建立Watch流不自动迁移 | 测量连接建立与断线恢复策略，必须保持Range+R+1 |
| Watch/WatchProgress | Watch响应完整包络与PUT/DELETE/prev_kv可用；WatchProgress/WatchCancel双向请求不支持，取消仅关闭HTTP响应 | 如需显式进度/取消与服务端ack，改用原生gRPC双向流驱动并进行多主机/长期压力验收 |
| TLS/mTLS | 构造参数已映射，未真实握手测试 | CA链、双向证书、过期/轮换及失败注入 |
| RBAC/认证 | 未实现账户/角色集成 | 明确最小权限和认证材料注入方案 |
| Raft/quorum | 已在一次性3成员集群验证1节点停机后2/3多数派读写，以及2节点停机时失去quorum、读写失败关闭和恢复；未测网络分区与磁盘故障 | 补充非对称网络分区、长时间失联、磁盘/快照恢复与选举/恢复时延测量 |
| Coordinator迁移 | 业务服务仍使用既有SQLite实现 | 独立迁移设计、双读比对、灰度、回滚与批准 |
| 生产权威 | 未启用 | 所有协议、故障、安全和业务迁移验收通过前保持关闭 |

etcd集群的三节点成员数量不自动代表业务高可用已验收；读请求重试也不等于写请求可安全重试。任何无法确认的Txn/Lease结果均需保持未知或fail-closed，Watch通知不能成为授权依据。schema-v2仍是唯一生产权威。

## 7. 本轮后续工作

1. 在可用Docker主机执行run.sh，记录etcd server/client版本、所有成员的status与member list、5项live integration结果和测试日志；
2. 单节点停止后使用其余两个成员验证读写与leader变化；再研究无多数派行为及恢复，不将故障注入放到生产集群；
3. 评估是否需要原生gRPC双向Watch驱动以支持主动WatchProgress/Cancel和服务端确认；当前HTTP Watch已保留完整响应包络，但只通过关闭流取消；
4. 对mTLS/RBAC/认证、endpoint轮换和超时预算补充部署配置与安全验收；
5. 完成业务层Store Port迁移设计、独立兼容测试、数据迁移/回滚和企业批准前，不替换当前SQLite Coordinator。

## 8. 第四十八轮真实服务端实测补充（2026-11-26）

在第四十七轮初始5项live集成测试基础上，新增真实单成员故障场景`tests/test_spare_parts_provider_authority_store_member_outage_etcd_integration.py`。它在一次性三成员etcd v3.7.0 Compose环境中停止etcd1，随后：

1. 通过配置为“停止成员优先、存活成员其次”的Endpoint列表，验证linearizable Range在首endpoint连接失败后成功failover，且请求仍保持`serializable=false`；
2. 等待存活成员报告有效Leader，再向健康endpoint发送单次Txn Compare/Put，不对写操作进行自动重试；
3. 线性一致读回新写数据，确认剩余2/3多数派接受本次验证的读写；
4. 重启etcd1并等待其endpoint恢复、member list回到3个成员。

**真实CI结果：** [Run 45839556952](https://github.com/rexyll/cnc-knowledge/actions/runs/45839556952)在三成员集群上执行6项测试全部通过（6/6，0 failures，0 skips）；诊断Artifact [15127610627](https://github.com/rexyll/cnc-knowledge/actions/runs/45839556952/artifacts/15127610627)，SHA-256 `74b04904535cce72b7a08fdf6265020bcb9086b43003106ab4eb4271847869f2`。同一代码head的默认回归[Run 45839557095](https://github.com/rexyll/cnc-knowledge/actions/runs/45839557095)两个必需Job均成功：全库500项unittest（494通过、6项opt-in live集成测试按默认策略skip），CH12 143项数值资源测试通过，strict knowledge lint 0 errors，CH17合成夹具validator 0 errors/5项既有warning。

**不可扩大的结论：** 本次验证是单次、临时、明文HTTP的集成冒烟测试。它证明限定场景下单节点停止期间2/3节点仍能完成该次linearizable Range/Txn读写，且节点重启后成员列表恢复；不证明2节点同时故障、长时间网络分区、磁盘故障、生产RPO/RTO、性能/吞吐、TLS/mTLS、RBAC、Watch或真实多主机Coordinator。ASSET-000092的30项正式企业场景仍全部PROPOSED_NOT_APPROVED / NOT_RUN；SQLite业务服务未迁移，schema-v2仍是唯一生产权威。

## 9. 第四十九轮失去多数派与恢复补充（2026-11-26）

新增真实集成测试`tests/test_spare_parts_provider_authority_store_quorum_loss_etcd_integration.py`，在三成员etcd v3.7.0临时集群中依次停止etcd1与etcd2，使etcd3成为唯一存活节点：

1. 线性一致读取在无quorum状态下必须失败关闭；
2. 对唯一存活节点发送一次Txn，若请求超时则保持OUTCOME_UNKNOWN，若服务端拒绝则转为Unavailable；不得将失败/未知写入宣称成功，也不自动重试；
3. 恢复etcd1、etcd2并等待三成员和Leader恢复；
4. 对目标key执行线性一致读回，确认无quorum期间未提交该值；随后对同一key发起VERSION=0 CAS写入并读回成功。

**真实CI结果：** [Run 45840903997](https://github.com/rexyll/cnc-knowledge/actions/runs/45840903997)在一次性三成员etcd v3.7.0集群上运行7项live集成测试，7/7 PASS、0 failures、0 skips；集群资源清理成功。诊断Artifact [15128755397](https://github.com/rexyll/cnc-knowledge/actions/runs/45840903997/artifacts/15128755397)，SHA-256 `d326119ddda7cc64a1cf3e14fbefc83e21d4693b25d2b9d870604bbee28747b8`。同一代码head默认回归[Run 45840904137](https://github.com/rexyll/cnc-knowledge/actions/runs/45840904137)：全库501项unittest（494通过、7项opt-in live测试按默认策略skip），CH12 143项数值测试通过，strict knowledge lint 0 errors，合成fixture validator 0 errors/5项既有warning。

**验收边界：** 这只验证受控的两成员停止/恢复流程，不涵盖非对称网络分区、长时间网络分割、磁盘/文件系统故障、性能指标、mTLS/RBAC、Watch或多主机Coordinator。ASSET-000092的30项正式场景仍全部PROPOSED_NOT_APPROVED / NOT_RUN；schema-v2仍是唯一生产权威。

## 10. 第五十轮 Watch Gateway 流式包络真实验收（2026-11-26）

第五十轮在不改变KV/Txn/Lease协议的前提下，增加低层HTTP Watch server-streaming解析。驱动直接通过已配置的etcd3gw session发送/v3/watch WatchCreate请求，不使用会丢弃控制响应的高层Watcher；解析器对任意HTTP chunk边界进行增量UTF-8/JSON重组，保留完整result包络和event KV/prev_kv。proto3零值PUT枚举可在JSON中省略，适配器按默认PUT解释；DELETE和未知枚举按明确类型处理/失败关闭。

**真实CI：** [Run 45842517310](https://github.com/rexyll/cnc-knowledge/actions/runs/45842517310)在一次性三成员etcd v3.7.0集群中执行8项测试全部通过（8/8，0 failures，0 skips），其中真实Watch测试收到created握手、PUT、DELETE及DELETE previous KV，结束时关闭响应流。诊断Artifact [15128407498](https://github.com/rexyll/cnc-knowledge/actions/runs/45842517310/artifacts/15128407498)，SHA-256 `9c45a263c409f9f7eb808670df14c5a7f7455f8cea85ad0cadec5d053699ccb9`。

**默认CI：** [Run 45842517156](https://github.com/rexyll/cnc-knowledge/actions/runs/45842517156)两个必需Job成功；全库505项unittest（497通过、8项opt-in live测试按默认策略skip），CH12 143项数值资源测试通过，strict knowledge lint 0 errors，结构/数据质量0 errors（5项既有治理warning）。

**能力边界：** WatchCreate支持progress_notify参数以请求服务端周期进度通知，但当前HTTP请求/响应模型不提供双向WatchProgress和WatchCancel消息，故驱动不暴露watch_progress；取消仅关闭HTTP流，不宣称服务端取消已确认。建立流之后的网络中断不自动failover/replay，调用方需执行linearizable Range + R+1恢复。mTLS握手、RBAC、复杂网络分区与长期流压力仍未验证；正式矩阵ASSET-000092的30项场景仍PROPOSED_NOT_APPROVED / NOT_RUN。
