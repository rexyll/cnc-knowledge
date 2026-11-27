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
| etcd3gw网络驱动 | Range/Txn/Lease/HTTP Watch已实现；Gateway错误分类有20项Fake契约测试；mTLS/RBAC、短TTL Token、quorum隔离和单成员故障均有etcd v3.7.0 disposable live证据（最新Live Run 45927091505） | 仍需网络分区、长时流背压、企业Token provider/轮换/审计及生产HA验收 |
| endpoint failover | 只读Range/status/member-list与Watch建立阶段仅在真实transport/timeout错误时跨endpoint尝试；401/403/请求错误不触发failover；已建立Watch流不自动迁移 | 保持Range+R+1恢复；认证失败由调用方显式重新认证并调用set_auth_token，不做匿名回退 |
| Watch/WatchProgress | Watch响应完整包络与PUT/DELETE/prev_kv可用；WatchProgress/WatchCancel双向请求不支持，取消仅关闭HTTP响应 | 如需显式进度/取消与服务端ack，改用原生gRPC双向流驱动并进行多主机/长期压力验收 |
| TLS/mTLS | etcd v3.7.0一次性三成员环境已验证双向证书、缺失客户端证书拒绝和不可信CA拒绝（Run 45918152363） | 企业PKI、证书轮换/吊销、生产密钥托管和长期压力仍需独立验收 |
| RBAC/认证 | 已验证reader/writer最小权限、跨prefix拒绝、HTTP 401/403错误分类和显式Token替换；无自动refresh | 企业IAM、token provider、凭据轮换/撤销、审计和多实例并发刷新仍需独立设计验收 |
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


## 11. 第五十一轮 etcd Gateway mTLS 实时验收（2026-11-27）

新增`scripts/etcd-integration/compose-mtls.yaml`、`scripts/etcd-integration/run-mtls.sh`及`tests/test_spare_parts_provider_authority_store_mtls_etcd_integration.py`，使用一次性 etcd v3.7.0 三成员 TLS 集群验证 Gateway 客户端证书配置。runner 临时生成 CA、server/client cert 和 key，所有敏感文件位于runner临时目录，job退出时清理；TLS Compose volumes也删除。

**真实CI：** [Run 45918152363](https://github.com/rexyll/cnc-knowledge/actions/runs/45918152363)成功。独立mTLS测试3/3通过：合法双向证书完成成员发现、CAS Txn写入及linearizable readback；缺失客户端证书连接被服务端拒绝；错误CA无法验证服务端证书。诊断Artifact [15163390323](https://github.com/rexyll/cnc-knowledge/actions/runs/45918152363/artifacts/15163390323)，SHA-256 `91014d3f47cf09152dd81488231494fdc04afc675b428cdad3e0556cf00aac74`。

**默认CI：** [Run 45918152436](https://github.com/rexyll/cnc-knowledge/actions/runs/45918152436)两个必需Job成功；全库508项unittest通过，CH12 143项通过，strict knowledge lint 0 errors，结构/数据校验0 errors、5项既有治理warning。

**能力边界：** 这是指定版本和一次性Compose环境的TLS握手/CA信任/客户端证书认证证据，不代表企业PKI接入、证书轮换或吊销、生产密钥托管、etcd RBAC、长期压力或生产环境验收。`etcd3gw` 对TLS底层异常可能包装成无文本ConnectionError，负向测试验证连接失败并以有效证书用例作为健康基线。ASSET-000092的30项正式场景仍PROPOSED_NOT_APPROVED / NOT_RUN；schema-v2仍是唯一生产权威。


## 12. 第五十二轮 etcd Gateway RBAC 与最小权限账户验证（2026-11-27）

Etcd3gwV3Client新增可选auth_token参数，将token写入各endpoint底层HTTP session的Authorization header；没有自动用户名密码持久化、匿名回退或明文降级。新增`tests/test_spare_parts_provider_authority_store_rbac_mtls_etcd_integration.py`，通过一次性三成员mTLS集群验证etcd原生Authentication/RBAC。

**真实验证：** [Run 45919206834](https://github.com/rexyll/cnc-knowledge/actions/runs/45919206834)成功，mTLS suite 8/8通过（原mTLS 3项 + RBAC 5项）：reader在授权prefix内Range成功，写入及越权Range被拒绝；writer在授权prefix内Range/CAS成功，未授权prefix读写被拒绝；无token及错误密码认证失败。普通三成员live suite 8项也全部通过。诊断Artifact 15163741056，SHA-256 `b7e7476a08e1e9c4a77e4bb02e2b80727dd09e1baadc1b66866b6a54b72c8ee0`。

**Gateway证书身份限制：** 初次联测发现etcd HTTP gRPC-Gateway拒绝将非空mTLS客户端证书CN作为用户身份。runner因此生成无CN但仍由临时CA签发的客户端证书；TLS链校验与客户端证书强制认证继续开启。RBAC身份通过用户名/密码调用`/v3/auth/authenticate`取得token，再由Authorization头传递。mTLS和RBAC是两层不同控制，不得把客户端证书CN映射宣称为此Gateway的用户认证能力。

**默认质量：** [Run 45919206886](https://github.com/rexyll/cnc-knowledge/actions/runs/45919206886)两个Job成功；515项unittest（499通过、16项opt-in live skip），CH12 143项通过，strict knowledge lint 0 errors，结构/数据校验0 errors、5项既有治理warning。

**能力边界：** token由调用方显式提供并在内存中应用，本轮没有token自动刷新/过期续期。企业IAM、密码/凭据轮换、撤销、审计、生产密钥托管、跨租户身份治理均未验证。/health端点不等同于KV数据面授权证据。ASSET-000092的30项正式场景继续PROPOSED_NOT_APPROVED / NOT_RUN；schema-v2仍为唯一生产权威，SQLite Coordinator业务状态机未迁移。



## 13. 第五十三轮 Token 生命周期、显式更新与失败关闭（2026-11-27）

etcd v3.7 配置参考（SRC-000410）显示，`--auth-token`支持`simple`与`jwt`类型，`--auth-token-ttl`默认300秒并用于simple token；JWT的TTL由JWT token选项配置，不能将两者混为一谈。官方认证设计（SRC-000411）指出simple token是有状态的开发/测试机制，不应作为生产token方案；JWT签名和验证由服务端配置完成，客户端仍需负责在过期前取得新token并更新客户端生命周期。RBAC文档（SRC-000412）说明mTLS Common Name身份映射不适用于HTTP gRPC-Gateway，因此此处继续采用mTLS证书保护传输、Authorization token承载etcd RBAC身份的双层方式。

第五十三轮驱动增加`Etcd3gwV3Client.set_auth_token(token)`，可显式替换或清除所有endpoint HTTP session上的Authorization header；Watch复用同一endpoint session，因此同步继承替换后的token。该方法只负责安装调用方取得的token，不接收或保存用户名/密码，不自动认证、不自动刷新、不推测token到期时间。Fake Gateway新增token轮换/清除和认证异常不得触发endpoint failover的契约测试。

新增短TTL mTLS集成测试入口：通过`--auth-token=simple`和可配置`--auth-token-ttl`在独立临时集群中验证旧token过期后被拒绝、显式重新认证取得新token、对全部endpoint更新Authorization、Range读回及Watch创建握手。默认mTLS/RBAC套件继续使用300秒TTL，短TTL套件独立启动并清理集群，避免影响原有RBAC用例。代码和测试已提交；实时CI验收：[Run 45920726761](https://github.com/rexyll/cnc-knowledge/actions/runs/45920726761)成功；基础三节点suite 6项、mTLS/RBAC suite 8项、独立10秒TTL生命周期测试1项均通过。诊断Artifact [15164208273](https://github.com/rexyll/cnc-knowledge/actions/runs/45920726761/artifacts/15164208273)，SHA-256 `0b66c69eb7f1ecc12e0d8bfbbf80ab0bf51de739ec31d8d2e9f3db878619e476`。默认质量CI [Run 45920726730](https://github.com/rexyll/cnc-knowledge/actions/runs/45920726730)两个Job成功：全库518项unittest（501 passed、17项opt-in live skip），CH12 143项通过，strict knowledge lint 0 errors。所有密码/token/证书仍只在CI临时目录或进程内存中，不进入仓库。

**当前限制：** 本轮尚未实现自动token provider/后台续期；也未验证JWT密钥管理、企业身份源、生产token轮换/撤销、审计、时钟偏差策略和多实例并发刷新。工程测试仍不改变ASSET-000092正式30项场景的`PROPOSED_NOT_APPROVED / NOT_RUN`状态，schema-v2仍是唯一生产权威，SQLite Coordinator业务状态机未迁移。


**错误分类边界补充：** etcd3gw 2.7.0 对部分HTTP状态（如内部错误、服务不可用、请求/网关超时）映射为传输/服务异常，而其他非200响应统一抛出通用 `Etcd3Exception`；驱动会原样传播该非传输异常，不把认证/授权拒绝作为endpoint failover条件。当前尚未将HTTP 401/403或Gateway结构化错误码归一为独立的Unauthenticated/PermissionDenied类型；也未完成认证服务不可用/多数派丢失期间“已有token读写”与“重新认证”差异测试。该项列为后续切片，不能声称本轮已完成精细错误分类或认证服务HA验证。


## 14. 第五十四轮 Gateway 认证错误分类与多数派故障隔离（2026-11-27）

etcd Gateway错误响应的协议依据补充如下：SRC-000413记录etcd v3.6+ gRPC-Gateway以HTTP状态码和google.rpc.Status JSON承载RPC错误；SRC-000414记录etcd rpctypes中invalid auth token对应Unauthenticated（code 16）、permission denied对应PermissionDenied（code 7），而no leader、leader changed、stopped和timeout属于Unavailable；SRC-000415记录etcd3gw 2.7.0只对部分HTTP状态映射专用异常，其他非200响应抛出通用Etcd3Exception。

**驱动实现：** `scripts/spare_parts_provider_etcd3gw_driver.py`新增`Etcd3gwAuthenticationError`、`Etcd3gwPermissionDeniedError`、`Etcd3gwRequestError`和Gateway状态解析函数。解析优先使用HTTP 401/403与gRPC code 16/7，并兼容HTTP 400/code 3且message明确为authentication failed的etcd错误；普通InvalidArgument仍归类为request error。异常保留原始cause。Watch建立请求也使用相同错误分类。未识别载荷继续作为原异常传播，不做猜测。

**Failover策略：** 只读Range/status/member-list仍只对真实连接/超时故障切换endpoint；认证失败、权限拒绝、其他Gateway请求错误和协议错误不会触发切换。Txn/Lease写请求仍只发送一次。没有匿名回退，不记录Authorization token。

**Fake契约测试：** 覆盖HTTP 401/code16、HTTP 403/code7、400错误密码消息、普通400参数错误、畸形错误JSON、原始异常cause，以及认证/授权拒绝时第二endpoint未被触达；Watch的403也验证不触发failover。驱动契约测试当前20项。

**Live RBAC/mTLS：** [Run 45922792420](https://github.com/rexyll/cnc-knowledge/actions/runs/45922792420)中mTLS/RBAC suite 12/12通过（原mTLS 3项 + RBAC 9项），包括invalid token归一为AuthenticationError、reader越权归一为PermissionDeniedError、错误密码HTTP Gateway错误载荷归一为AuthenticationError，以及无效endpoint连接失败后切换到健康endpoint成功。

**多数派故障隔离：** 同一live run另起一次性mTLS三成员集群，停止两个成员后，有效token的线性一致Range超时；同一节点上的显式`/auth/authenticate`请求也超时（观测值`AUTH_REAUTH_RESULT_DURING_QUORUM_LOSS=timeout`）。恢复两个成员后，原有效token再次成功完成Range，未要求匿名降级或自动刷新。该实验说明数据面和重新认证在quorum loss期间都不可用；token本身在恢复后仍有效。它不证明认证API能在失去多数派时独立提供服务。

**Live结果：** Run 45922792420全部步骤成功：普通三节点基础/成员故障/失去多数派suite 8项、mTLS/RBAC suite 12项、10秒token生命周期suite 1项、认证/quorum隔离suite 1项通过。诊断Artifact 15165755534，SHA-256 `c3b8d8e25e91cc7bff7e3d2893a55688de0b2567836052a20cb887fd2bcc7608`。runner清理临时证书、凭据及Compose volumes。

**默认质量CI：** [Run 45922792429](https://github.com/rexyll/cnc-knowledge/actions/runs/45922792429)成功：全库526项unittest（504 passed、22项opt-in live skip），CH12 143项通过，strict knowledge lint 0 errors，fixture validator 0 errors/5项既有warning；结构数据为22章、178 Markdown、260实体、240关系、412来源、584内部链接。

**限制：** 本轮测试只覆盖etcd v3.7.0/etcd3gw 2.7.0的Gateway状态和一次性三节点环境。没有构建自动token provider/refresh；没有测试跨节点简单token复制的长期稳定性、认证请求在单节点实际停机时的独立切换、网络分区和生产IAM/审计/密钥管理。正式30项场景继续PROPOSED_NOT_APPROVED / NOT_RUN；schema-v2仍是唯一生产权威，SQLite Coordinator未迁移，CH17-T004保持IN_PROGRESS。


## 15. 第五十五轮 mTLS + RBAC 单成员故障、Token传播与重启恢复（2026-11-27）

新增 `tests/test_spare_parts_provider_authority_store_member_outage_auth_etcd_integration.py`，在一次性 etcd v3.7.0 三成员 mTLS + RBAC 集群中，创建最小权限 reader 身份，分别观测 Token 签发后即时状态和收敛状态；真实停止 etcd1，保留 etcd2/etcd3 两成员多数派；通过首个 endpoint 指向故障成员的 Etcd3gwV3Client 发起线性一致 Range；再直接访问两个健康成员区分 Token 接受与 driver failover；最后重启 etcd1 并测试旧 Token 和显式重新认证后的新 Token。

**关键实测结果：** [Live Run 45927091505](https://github.com/rexyll/cnc-knowledge/actions/runs/45927091505)在同一代码head的五个独立阶段全部成功：基础三成员etcd suite 6项、mTLS/RBAC suite 12项、短TTL token生命周期1项、auth/quorum隔离1项、单成员故障与Token传播1项。新增单成员故障测试1/1通过，输出结果：
- Token签发后即时访问：member1/member2/member3均accepted；
- 等待传播后访问：三个成员均accepted；
- 停止etcd1后Driver从故障endpoint经transport failover成功完成Range；
- etcd2和etcd3直接接受原Token，均HTTP 200；
- 重启etcd1后，旧reader simple Token返回HTTP 401；
- 从健康成员etcd2显式重新认证后，新Token在member1/member2/member3均accepted，Driver使用新Token恢复读取成功。

诊断Artifact [15167295428](https://github.com/rexyll/cnc-knowledge/actions/runs/45927091505/artifacts/15167295428)，SHA-256 `2f06dbcea1b1e69bf9dfcf2666bfedff3811321aa8a8dd1474181c88b75e7aff`。本轮还修正runner诊断目录归档，使mTLS Compose成员日志和状态文件纳入CI Artifact。

**默认质量CI：** [Run 45927138505](https://github.com/rexyll/cnc-knowledge/actions/runs/45927138505)在最终文档head成功：全库527项unittest（504 passed、23 skipped）；CH12 143项数值测试通过；strict knowledge lint 0 errors；fixture validator 0 errors / 5项既有治理warning；结构数据为22章、178 Markdown、260实体、240关系、412来源、584内部链接。

**技术解释与限制：** 本次结果证明限定环境下存活成员可继续接受旧Token，Driver可从停机成员failover；但成员重启后旧simple Token在该成员返回401，而从健康成员重新认证得到的新Token在三个成员都可用。该结果只描述本次etcd v3.7.0/simple-token实验，不将原因扩展推断为所有etcd版本或JWT token行为。Driver仍不保存用户名/密码，不自动重新认证，不自动刷新Token；调用方必须通过受控凭据源显式重新认证并调用token替换接口。不得匿名回退，不得将401/403作为endpoint failover条件。

**治理边界：** 本轮只是supporting engineering evidence，不执行或批准ASSET-000092正式30项场景；其`PROPOSED_NOT_APPROVED / NOT_RUN`保持不变。schema-v2仍是唯一生产权威，SQLite Coordinator业务状态机未迁移，CH17-T004保持`IN_PROGRESS`。


## 16. 第五十六轮：三成员多数派/少数派网络分区实测

新增 `tests/test_spare_parts_provider_authority_store_network_partition_etcd_integration.py`，仅在显式设置 `ETCD_INTEGRATION=1` 的一次性CI集成环境执行。测试通过Compose project/service标签确认etcd1容器身份，只将etcd1从专用 `cnc-knowledge-etcd-itest_default` 网络断开；不修改宿主机iptables，也不接触其他容器或网络。

分区期间，etcd1容器进程仍运行且本地客户端端口可达。测试通过容器内etcdctl对etcd1本地endpoint发起线性一致Range和Put，两项均以非零退出码失败，证明隔离的单节点不能在没有Raft多数派时确认线性一致读写。etcd2/etcd3仍互通，Coordinator Store经Etcd3gwV3Client对唯一临时key执行初始线性一致读取、VERSION=0 CAS Txn写入及线性一致读回；事务成功且读回值与提交值一致。

测试的finally路径重新连接etcd1网络，并轮询三个endpoint及成员列表，确认三成员恢复。恢复后，测试单独通过etcd1 endpoint执行Coordinator Store线性一致读取，成功读到多数派提交的同一值。隔离期间少数派写入没有被确认，也没有覆盖多数派数据。

**实时证据：** [CH17 Live Run 45929955634](https://github.com/rexyll/cnc-knowledge/actions/runs/45929955634)的 `test_minority_partition_fails_closed_and_majority_recovers` 实际执行并通过（1/1，8.248秒）。修复后的runner还完成基础etcd、成员故障、quorum loss、mTLS、RBAC、短TTL token、auth/quorum及成员Token传播阶段；整个live Job success。诊断Artifact [15168271744](https://github.com/rexyll/cnc-knowledge/actions/runs/45929955634/artifacts/15168271744)。

**默认质量门禁：** [Run 45930090004](https://github.com/rexyll/cnc-knowledge/actions/runs/45930090004)在当时main head通过：全库528项unittest（504 passed、24 skipped）、CH12 143项数值资源测试、strict knowledge lint 0 errors（5项既有治理warning）、结构与最终自检0 errors。30个SPAT包在隔离环境仅完成模拟构建校验，记录为 `business_test_status=NOT_RUN`，没有外部连接或写入。

**验证边界：** 该测试从etcdctl本地endpoint验证少数派的失败关闭，从Coordinator Store验证多数派事务及恢复后的收敛；它没有验证Etcd3gwV3Client在少数派endpoint上的多endpoint只读failover，也没有验证Coordinator Store对少数派Txn超时的 `OUTCOME_UNKNOWN` 分类或单次发送行为。非对称分区、多机房、性能与生产故障演练未覆盖。第五十七轮继续验证驱动层的这些语义。

本轮工程任务完成，但不批准或执行正式验收矩阵。ASSET-000092仍30项、`PROPOSED_NOT_APPROVED / NOT_RUN`；schema-v2仍唯一生产权威，SQLite Coordinator业务状态机未迁移，CH17-T004总状态保持`IN_PROGRESS`。


## CH17-T004 第五十七轮：少数派分区下Driver读取故障转移与Txn结果核验（2026-11-27）

新增live方法 `test_driver_partition_read_failover_and_single_txn_outcome`，在一次性三成员etcd v3.7.0集群中，真实隔离etcd1后通过Etcd3gwV3Client和EtcdV3CoordinatorAuthorityStore观察调用层行为。使用记录型post包装捕捉每次HTTP endpoint调用；对Txn使用只包含隔离etcd1的单endpoint driver，避免将自动重试误判为Raft行为。finally中关闭driver、恢复Compose网络并等待三成员恢复；事务恢复核对只读，不重放写请求。

**实时观测：** [CH17 Live Run 45931474359](https://github.com/rexyll/cnc-knowledge/actions/runs/45931474359)整个Job成功。新增测试与第五十六轮基础网络分区测试均通过（网络分区文件2项测试，8.670秒）。CI日志的结构化观测如下：

- 线性一致Range的endpoint尝试顺序为 `http://127.0.0.1:23791`（被隔离的etcd1），随后 `http://127.0.0.1:23792`（健康多数派成员）；最终读取成功，证实只读transport故障转移实际走到第二endpoint。
- 隔离etcd1上的CAS Txn仅发送一次（唯一尝试endpoint为 `http://127.0.0.1:23791`），存储适配层将连接错误报告为 `OUTCOME_UNKNOWN/ConnectionError`；第二endpoint没有被写请求触达。
- finally恢复网络及quorum后，对事务key执行线性一致读回结果为 `not-committed`。这将初始未知结果收敛为本次“未提交”；测试没有重放事务，也未观察到重复写入。
- 第五十六轮网络分区基础测试 `test_minority_partition_fails_closed_and_majority_recovers` 在同一运行中再次通过。随后mTLS、短TTL Token、auth/quorum隔离、RBAC单成员故障/Token传播、诊断采集、Compose volumes清理及artifact上传全部成功。

诊断Artifact [15168243294](https://github.com/rexyll/cnc-knowledge/actions/runs/45931474359/artifacts/15168243294)。

**默认质量门禁：** [Knowledge Quality Run 45931474322](https://github.com/rexyll/cnc-knowledge/actions/runs/45931474322)两个必需Job成功：全库529项unittest（504 passed、25 skipped），CH12 143项通过，strict knowledge lint 0 errors / 5项既有warning，结构/最终自检0 errors。SPAT合成夹具30包模拟检查成功，但 `business_test_status=NOT_RUN`、`external_connections=NO`、`writes=NO`，不构成正式业务验收。

**第五十七轮结论：** 工程测试范围验收完成。实测证明只读Range在隔离首endpoint后能够继续尝试健康endpoint；Txn对隔离少数派只发送一次，连接中断按既有端口契约报告 `OUTCOME_UNKNOWN`，恢复后的线性一致读回确认本次未提交。此实验没有模拟“Txn已经提交而HTTP响应丢失”的窗口，也没有证明所有HTTP/gRPC Gateway错误均能区分为transport错误或确定性拒绝；不对etcd v3.7.0以外版本外推。CH17-T004总任务仍`IN_PROGRESS`。

治理边界不变：ASSET-000092正式30项继续`PROPOSED_NOT_APPROVED / NOT_RUN`；schema-v2仍是唯一生产权威，SQLite Coordinator业务状态机未迁移；本轮仅为一次性CI supporting engineering evidence。


## 17. 第五十七轮：少数派分区下Coordinator Driver读取故障转移与Txn未知结果

新增live测试方法 `test_driver_partition_read_failover_and_single_txn_outcome`，与第五十六轮的基础分区测试在同一专用CI Compose集群中执行。测试在确认Compose project/service标签后断开etcd1网络；每次HTTP POST均记录实际endpoint，读请求使用三endpoint client，事务则使用只包含隔离etcd1的单endpoint client。finally关闭client、恢复网络、等待三成员quorum，再用健康多数派endpoint线性一致读回Txn key；不重新发送事务。

**真实观测：** [Live Run 45931474359](https://github.com/rexyll/cnc-knowledge/actions/runs/45931474359)中的网络分区测试文件2项通过，耗时8.670秒。结构化日志显示：

- 线性一致Range先触达隔离成员 `http://127.0.0.1:23791`，随后触达健康成员 `http://127.0.0.1:23792`，最终返回成功；这验证当前只读transport failover路径确实可从失联/不可线性一致的首endpoint转向健康多数派。
- 少数派CAS Txn仅触达 `http://127.0.0.1:23791` 一次，Store结果为 `OUTCOME_UNKNOWN/ConnectionError`，没有第二endpoint写入尝试。
- finally恢复网络后，线性一致读回Txn key不存在，日志为 `PARTITION_DRIVER_TXN_RECOVERY=not-committed`。因此本次请求初始结果未知，但事后核对确认没有提交；测试未重放事务。

Live workflow所有后续mTLS、short-TTL token、auth/quorum、RBAC成员故障/Token传播、诊断和清理步骤均成功。Artifact [15168243294](https://github.com/rexyll/cnc-knowledge/actions/runs/45931474359)。默认质量[Run 45931474322](https://github.com/rexyll/cnc-knowledge/actions/runs/45931474322)通过：529项unittest（504 passed、25 skipped），CH12 143项，strict lint 0 errors/5既有warning，结构和最终自检0 errors。SPAT 30包只是离线模拟，business_test_status仍NOT_RUN。

**解释边界：** `OUTCOME_UNKNOWN`是发出写请求后连接丢失时的保守调用契约；恢复后未找到key，说明这一次没有提交。此测试没有控制“Raft已经提交、Gateway响应在返回客户端前丢失”的精确故障窗口，也没有将所有Gateway HTTP/gRPC状态重分类为transport错误。只读failover与写入单次发送的结果只针对当前etcd v3.7.0/etcd3gw 2.7.0测试环境。第五十七轮工程验收完成；ASSET-000092正式30项仍PROPOSED_NOT_APPROVED / NOT_RUN，schema-v2仍唯一生产权威，SQLite Coordinator业务状态机未迁移。


## 18. 第五十八轮：少数派Lease KeepAlive失败、自然过期与Leader fencing

新增 `tests/test_spare_parts_provider_authority_store_lease_partition_etcd_integration.py`。测试只操作一次性三成员Compose集群：首先经健康多数派创建TTL=8秒Lease，使用单个CAS Txn将唯一leader authority key绑定Lease，并在非租约epoch key上记录epoch=1；随后仅从专用Compose网络断开etcd1，并校验容器的Compose project/service标签。

**KeepAlive实际请求路径：** 客户端配置三个endpoint，顺序为etcd1/23791、etcd2/23792、etcd3/23793；通过记录型HTTP post包装捕获LeaseKeepAlive的dispatch。网络隔离后对旧Lease调用KeepAlive，Store返回`AuthorityStoreUnavailableError`，记录的实际endpoint尝试只有`127.0.0.1:23791`一次，没有自动failover至健康多数派。多数派etcdctl LeaseTimeToLive显示TTL从7秒下降至5秒，证明本次续租失败没有重置租约。

**自然过期和authority清理：** 多数派LeaseTimeToLive随后报告`ttl=-1`。测试不调用LeaseRevoke来制造过期，而是继续通过多数派线性一致Range轮询，直至绑定Lease的leader authority key实际消失；独立epoch key仍为1。将TTL报告与key删除分开验证，避免把过期计时器状态误作KV删除已完成。

**新Leader与fencing：** 多数派签发新的Lease，并以一个CAS事务比较leader key不存在、epoch值仍为1，再写入新owner/Lease及epoch=2。旧owner尝试同时比较旧owner值和epoch=1后写入fencing保护key，Txn返回`succeeded=false`，旧写入key不存在；新owner按epoch=2进行比较写入则成功。恢复网络并等待三成员quorum后，通过原etcd1 endpoint线性一致读取，确认新owner、新Lease、epoch=2和新epoch写入均可见，旧fenced key不存在。

**实时证据：** [Live Run 45933111643](https://github.com/rexyll/cnc-knowledge/actions/runs/45933111643)整个Job success。Lease专项1/1 PASS（14.526秒），网络分区测试文件2项通过，后续mTLS、短TTL Token、auth/quorum隔离、RBAC成员故障与Token传播、诊断收集、容器与volumes清理全部成功。诊断Artifact [15169352034](https://github.com/rexyll/cnc-knowledge/actions/runs/45933111643/artifacts/15169352034)。

**质量门禁：** [Knowledge Quality Run 45933111606](https://github.com/rexyll/cnc-knowledge/actions/runs/45933111606)两个Job成功：全库530项unittest（504 passed、26 skipped），CH12 143项通过，strict knowledge lint 0 errors / 5既有warning，结构和最终自检0 errors。SPAT 30包只是离线模拟，`business_test_status=NOT_RUN`、无外部连接、无写入。

**限制：** 这是etcd v3.7.0/etcd3gw 2.7.0一次性Compose集成证据；fencing写入由Store KV compare事务模拟，未证明现有SQLite业务Coordinator已迁移并在所有业务写入口检查epoch。该实验不等同生产Leader HA、跨机房故障演练或正式30项矩阵执行。第五十八轮工程任务完成，CH17-T004总体仍IN_PROGRESS。
