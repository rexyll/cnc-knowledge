# Watch连接健康与存活检测策略决策记录

- **状态：** 设计决策（本轮仅文档，不启用新的生产运行机制）
- **日期：** 2026-11-27
- **适用实现：** 当前`Etcd3gwV3Client`、`EtcdV3CoordinatorAuthorityStore`及etcd v3.7.0 / etcd3gw 2.7.0验证夹具
- **关联任务：** CH17-T004，第六十三至第六十九轮
- **决策焦点：** 将Watch流传输状态、Watch所在成员的本地进度、Quorum读能力和应用端到端业务心跳分开观测，不再用单个“心跳/超时”布尔值代表整体健康。

## 1. 背景与问题定义

第六十八轮已经确认：当前Watch连接即使所在etcd成员仍然运行、仍连接Raft网络且三成员Quorum健康，只要整个KV空间没有revision推进，4秒`watch_read_timeout`仍会触发；当目标prefix之外的marker推进revision时，Watch才观测到空Progress响应，而且Progress header可能落后于刚完成的marker写入。由此可见至少存在四个不同判断：

1. **传输连接是否仍能收发字节：** 客户端与某个HTTP endpoint之间的TCP/HTTP通道状态。
2. **Watch流是否在向应用交付响应：** 包括业务事件、created/canceled控制响应或Progress响应。
3. **Watch endpoint本地观察到了什么revision：** 这是流连接所在成员的本地进度，不代表Quorum最新revision。
4. **集群是否能提供Quorum一致性操作：** 需要单独的线性一致读/健康检查证据。

这些状态不能互相替代。一个TCP连接可以仍处于ESTABLISHED但应用层已不再响应；一个HTTP流可以持续交付本地Progress，但其revision落后于多数派；一个Quorum Range可以成功，而原Watch连接仍然卡住；一个Watch能交付事件也不代表此时新的线性一致Range可成功。

## 2. 当前仓库实现事实

### 2.1 Watch传输方式

`scripts/spare_parts_provider_etcd3gw_driver.py`中的`Etcd3gwV3Client.watch()`通过`client.session.post("/v3/watch", stream=True, timeout=(connect_timeout, watch_read_timeout))`发起HTTP gRPC-gateway流式请求。创建请求中设置`create_request`、`progress_notify`、prefix/range和`prev_kv`；请求被某个endpoint接受后，活动流固定在该endpoint。建立流后的传输异常向上报告，不会自动将同一个旧cursor切换到另一个endpoint。

当前接口没有在已建立的Watch流上继续写入`WatchProgressRequest`或`WatchCancelRequest`的双向请求能力。etcd原生Watch API是双向gRPC stream，客户端可以向流写入create/cancel/progress请求；仓库当前使用的REST/gateway调用方式不是该原生双向客户端接口。

### 2.2 Range和状态探测

- `Etcd3gwV3Client.range(..., serializable=False)`发送`serializable=false`，对应默认线性一致Range语义；`EtcdV3CoordinatorAuthorityStore.linearizable_range()`也显式传入`serializable=False`。
- `_post(..., read_only=True)`允许Range类只读请求在配置的endpoint间failover。因此一次独立Range成功，能证明某个可用endpoint当时能够完成线性一致读；它不证明既有Watch流所在endpoint或原连接仍健康。
- `Etcd3gwV3Client.status()`当前调用`/maintenance/status`。这是一次状态查询，不等同于对Quorum能力的线性一致读探测。
- 当前Watch读取的`watch_read_timeout`默认`None`。配置数值后，它限制的是HTTP response body连续无字节的间隔，不是请求总耗时，也不验证etcd成员或Quorum本身。

### 2.3 第六十八轮实测基线

一次性三节点Compose环境中：
- 初始Quorum snapshot revision=38，Watch从39建立，读取空闲超时=4秒。
- 全局完全静默时未在4秒窗口内观测到Progress；流在约4.0045秒后以`ConnectionError`结束并被Store映射为`AuthorityStoreUnavailableError`。此时etcd1仍running、仍在Raft网络、Quorum健康，prefix未变化。
- prefix外marker写入revision=39、40后，Watch收到Progress header revision=39、39，目标prefix事件数为0。
- 仅断开etcd1专用客户端访问bridge、保留进程和Raft网络后，活动流约4.0045秒结束；Quorum仍可用。

该基线是有限CI夹具观察，不构成生产Progress最大间隔、真实WAN半开或生产SLO证据。

## 3. 检测机制比较

| 机制 | 能证明什么 | 不能证明什么 | 对当前实现的适用性 | 成本/风险 |
|---|---|---|---|---|
| etcd Watch Progress | 该Watch流收到一个服务端控制响应；header可观察流所在成员的本地revision水位 | 不证明Quorum最新revision；不保证固定间隔；不等于线性一致快照；没有Progress不一定代表故障 | 当前create请求可以设置`progress_notify=true`并读取服务端Progress，但不能主动在已建立流上发送Progress请求 | 服务端按当前负载决定通知频率；应用不能把它设定成严格定时心跳 |
| TCP SO_KEEPALIVE | 内核TCP栈在配置的探测/重试策略下可以发现部分不可达或失去响应的对端路径 | 不证明HTTP handler、etcd Watch逻辑、Raft Quorum或KV读取健康 | 当前Requests/urllib3 session没有在仓库中显式配置socket keepalive；需要专门HTTPAdapter/socket options或受控传输层 | 操作系统默认值和容器/NAT/代理行为可能不同；探测时间可能远长于应用SLO；必须通过目标平台实测 |
| HTTP/2 gRPC PING Keepalive | gRPC HTTP/2 transport上对端是否响应PING；适用于长连接与代理空闲连接维护 | 不证明etcd业务操作成功或Quorum可用 | 当前使用Requests访问gRPC-gateway，不是原生gRPC HTTP/2 channel；不能直接把gRPC PING选项套用到现有Watch请求 | 客户端与服务端需协商频率；过于频繁的PING可能被服务端限流/GOAWAY；会引入协议迁移与兼容性工作 |
| 独立线性一致Range探测 | 当前某个可用endpoint是否能完成Quorum线性一致读；返回revision与延迟可监测 | 不证明既有Watch流还活着、不证明该Watch endpoint健康、不证明事件消费线程没有卡住 | 当前已有`linearizable_range()`和只读endpoint failover，可作为独立Quorum-read探针 | 需要额外请求和Quorum读成本；探针应由进程级共享调度器复用，不要每条Watch都高频发送 |
| Lease-backed应用心跳 | 客户端写入心跳、服务端提交、同一Watch收到心跳事件时，可覆盖应用写入到Watch交付的端到端路径 | 不能单独证明所有业务prefix完整、所有成员健康或整体业务服务可用 | 需要新增专用heartbeat key/lease和事件过滤/识别；当前没有该机制 | 持续写入制造新revision和Watch事件，增加Raft、MVCC、compaction、权限和清理负担；TTL/续约参数也需单独设计 |

**术语提醒：** Requests/urllib3在Session中自动复用HTTP持久连接，是HTTP连接池/连接复用，不等同于操作系统TCP`SO_KEEPALIVE`探测。gRPC HTTP/2 PING也不同于TCP keepalive。三种机制不应在配置或监控中共用一个含糊的`keepalive=true`字段。

## 4. 本轮决策

### 4.1 采用分层健康模型

生产实现应维护至少两个彼此独立的健康维度，再加一个可选业务端到端维度：

- **Watch transport / stream：** 当前流是否已创建、最后一次收到任意合法响应的时间、最后业务事件时间、最后Progress时间、活动endpoint、关闭/取消/传输错误原因。
- **Quorum read capability：** 最近一次成功的线性一致Range时间、耗时、response header revision、失败类型和探测endpoint。
- **可选业务端到端心跳：** 只有在明确要求验证写入提交到指定Watch消费者交付的SLO时才引入；必须采用独立控制key并评估事件过滤、Lease TTL、revision和compaction成本。

不要将三者压缩成单个布尔健康值。可在监控层组合成下列状态：

| Watch流观测 | 独立Quorum Range | 合理判定 | 推荐处理 |
|---|---|---|---|
| 持续收到事件/Progress | 成功 | Watch路径有响应，Quorum读能力可用 | 正常；单独监测本地Progress revision与Quorum Range revision差距 |
| 静默/读超时/连接错误 | 成功 | Quorum读仍可用，但原Watch流不可用或可疑 | 标记Watch degraded；重新建立时先取得权威snapshot，再从R+1恢复 |
| 收到事件/Progress | 失败 | 流仍有数据，但当前Quorum读能力无法确认 | 不得宣称集群整体健康；按服务策略限制依赖Quorum的写操作并继续探测 |
| 静默/断流 | 失败 | Watch与Quorum探测均失败 | 报告协调服务不可用/状态未知；退避后重试，只读/写请求分别遵循自己的幂等与结果未知契约 |

### 4.2 Progress使用规则

1. `progress_notify=true`保留为可选的Watch进度观测能力，但不得假定它提供严格周期性心跳。
2. Progress header记录为`watch_local_progress_revision`，不要标记为`cluster_revision`或`quorum_revision`。
3. 只在与时间接近的独立Quorum Range比较时，计算`quorum_revision - watch_local_progress_revision`作为本地进度差距指标。单次差值不能直接触发数据丢弃或游标重置。
4. Progress不包含KV事件，不改变业务投影；不能取代Range snapshot。
5. 当前HTTP gateway路径没有双向`WatchProgressRequest`；如果未来要求客户端主动请求立即报告进度，应评估原生gRPC双向Watch客户端，而不是假设当前Requests流可以在已建立连接上继续写JSON请求。

### 4.3 Timeout默认策略

- 当前`watch_read_timeout=None`继续作为默认策略。
- 只有当服务端或应用机制能提供**有界且经生产验证的最大响应间隔**时，才允许对对应Watch配置有限read timeout。
- 超时阈值应依据服务端响应间隔高分位、代理/NAT最大空闲时长、网络抖动和调度延迟预算推导，并给出误判概率/SLO；不得把测试中的4秒直接推广为生产阈值。
- 如果没有可证明的有界流量间隔，有限read timeout只会将合法静默Watch判为Unavailable；此时应使用独立Quorum探测，而不是用短read timeout充当集群健康探针。
- 一旦read timeout触发并关闭流，状态恢复必须执行线性一致snapshot整体替换并从R+1恢复；不能只从上一个Progress revision续接。

### 4.4 Quorum探测策略

- 复用现有`linearizable_range()`，读取一个固定、最小、权限允许的专用探测key/range；不需要周期性写入该key。
- 该探测由进程级共享调度器执行，多个Watch共享最近一次探测结果与时间戳，避免每条Watch各自制造Quorum读负担。
- 探测请求必须有独立且有界的请求deadline；单次失败只更新Quorum探测状态，不得自动关闭仍有业务事件的Watch。
- 若现有权限模型不能读固定探测key，应为服务身份授予明确的只读探测范围；不要读取业务敏感数据作为健康探针。
- `/maintenance/status`可以作为诊断信息，但不能替代线性一致Range。运维工具的`etcdctl endpoint health`适合端点/集群运维健康检查；应用探针仍应使用本身的线性一致读路径以验证应用凭据和访问路由。

### 4.5 TCP / gRPC Keepalive决策

- **当前不添加TCP Keepalive代码。** 需要先确认生产部署使用的Requests/urllib3 adapter、操作系统、容器、负载均衡器/NAT和期望故障检测时间，再通过实际socket option和网络故障实验验证。
- **当前不切换gRPC PING。** 现有客户端不是原生gRPC channel；如果将来迁移原生gRPC，应一起评估etcd服务端`--grpc-keepalive-min-time`、`--grpc-keepalive-interval`、`--grpc-keepalive-timeout`以及客户端PING频率限制。
- TCP/gRPC Keepalive只负责传输层连接探测，不取代Quorum Range，也不取代Watch事件/快照恢复。

### 4.6 应用心跳决策

默认不引入Lease-backed heartbeat写入。只有当业务明确提出“每隔某个上限时间必须证明该Watch消费者确实收到服务端交付”的端到端要求时才考虑：
- heartbeat key使用独立保留前缀/命名空间和最小权限；
- Watch需显式识别/过滤heartbeat事件，不能把它们应用到业务投影；
- 选择Lease TTL、keepalive周期、重试窗口时考虑暂停/GC/网络抖动；
- 评估每周期写入带来的revision、Raft复制、Watch fan-out和compaction历史负担；
- 对心跳丢失、Lease过期、重复写入和Watch恢复做专门Live测试。

## 5. 推荐的运行时状态与恢复流程

建议未来实现一个Supervisor，将阻塞的Watch消费循环与独立Quorum探测循环解耦。当前驱动是同步pull iterator，`next(stream)`会等待下一响应；不要把Quorum探测安排在同一个可能永久阻塞的消费线程内。

建议运行时记录：

- `watch_state`: CONNECTING / ACTIVE / SUSPECT / DISCONNECTED / RECOVERING
- `watch_endpoint`: 当前活动流所绑定的endpoint
- `watch_last_response_at`、`watch_last_event_at`、`watch_last_progress_at`
- `watch_local_progress_revision`
- `quorum_probe_state`: HEALTHY / DEGRADED / UNAVAILABLE
- `quorum_probe_last_success_at`、`quorum_probe_latency_seconds`、`quorum_probe_revision`
- `watch_quorum_revision_gap`
- `watch_disconnect_total`、`watch_rebuild_total`及带原因分类的计数

恢复流程：

1. 活动Watch若收到EOF/取消/传输异常或经验证的读超时，标记该流不可用；不要在原缓存投影上继续假定事件完整。
2. 通过健康endpoint执行线性一致Range，读取完整目标prefix snapshot及revision R。
3. 整体替换旧投影，不合并或保留旧流的不确定尾部状态。
4. 使用R+1建立新Watch；如果建流前已有新revision，etcd会从指定revision回放。
5. 若新Watch因Compaction取消，重新获取snapshot并重复恢复流程。
6. 独立Quorum探测失败时不要仅因本地Watch仍有Progress就恢复Quorum健康状态。

监控标签应避免使用原始业务key/value作为高基数或敏感标签；按endpoint、错误分类和watch类型等有限维度聚合。

## 6. 实施路线

| 阶段 | 工作内容 | 进入条件 |
|---|---|---|
| A. 观测面 | 在Watch Supervisor中记录流响应/事件/Progress时间，独立记录Quorum Range探测 | 明确实际消费线程、生命周期和指标出口 |
| B. Quorum探测 | 以进程级共享调度器执行小型线性一致Range，评估频率/延迟/故障窗口 | 完成生产读SLO和权限范围定义 |
| C. 传输探测 | 根据真实部署决定TCP keepalive，或迁移原生gRPC并设计HTTP/2 PING | 确认协议、代理与服务端keepalive策略 |
| D. 端到端心跳（可选） | 只有业务SLO需要时才新增Lease-backed marker与事件过滤 | 完成revision写入率、compaction和权限成本评估 |
| E. 故障演练 | 分别模拟静默集群、路径黑洞、单成员落后、Quorum丢失、代理回收连接、消费者阻塞 | 形成各环境可复现的网络故障模型与验收SLO |

在阶段A/B没有完成前，不开启生产read timeout、不配置人为推测的TCP Keepalive阈值，也不引入应用层周期性KV写入。

## 7. 非目标与证据边界

本记录不是生产HA验收，也不是对当前驱动的生产连接健康状态机交付。第六十八轮只在一次性etcd v3.7.0 / etcd3gw 2.7.0 Compose场景中观察4秒静默超时、prefix外marker Progress和专用访问bridge断开；没有测量生产NAT、真实WAN黑洞、SO_KEEPALIVE探测、HTTP/2 PING、应用心跳写入成本或长时间运行的误判概率。

本轮不实现：
- TCP `SO_KEEPALIVE` socket options；
- 原生gRPC HTTP/2 client或PING；
- Watch双向Progress/Cancel控制消息；
- 独立Quorum探测Scheduler / Watch Supervisor；
- Lease-backed application heartbeat；
- 自动重连、自动failover或业务状态机迁移。

CH17-T004仍为`IN_PROGRESS`；ASSET-000092正式30项仍`PROPOSED_NOT_APPROVED / NOT_RUN`；schema-v2仍为唯一生产权威，SQLite Coordinator业务状态机尚未迁移。

## 8. 上游与仓库参考

### etcd v3.7

- [etcd API：Watch是双向gRPC stream，Progress通知和响应字段](https://etcd.io/docs/v3.7/learning/api/)
- [etcd API reference：WatchCreateRequest、WatchProgressRequest和WatchCancelRequest](https://etcd.io/docs/v3.7/dev-guide/api_reference_v3/)
- [Interacting with etcd：Progress revision来自连接的本地成员，少数派时可落后于Quorum读](https://etcd.io/docs/v3.7/dev-guide/interacting_v3/)
- [Configuration options：gRPC Keepalive服务端参数](https://etcd.io/docs/v3.7/op-guide/configuration/)
- [How to check cluster status：endpoint status与endpoint health](https://etcd.io/docs/v3.7/tasks/operator/how-to-check-cluster-status/)
- [Upgrade guide：endpoint health示例返回成功提交proposal](https://etcd.io/docs/v3.7/upgrades/upgrade_3_7/)

### transport与客户端库

- [gRPC Keepalive guide：HTTP/2 PING与服务端最小PING间隔/限制](https://grpc.io/docs/guides/keepalive/)
- [Requests Quickstart：read timeout按底层socket连续无字节间隔触发，不是整个响应的总时限](https://requests.readthedocs.io/en/latest/user/quickstart/#timeouts)

### 本仓库证据

- CH17技术正文第27节：慢消费者、积压与Compaction竞争。
- CH17技术正文第28节：Watch异常EOF与部分投影快照恢复。
- CH17技术正文第29节：空闲Progress、读取超时和客户端访问路径失联。
- [第六十八轮Live Run 45987534125](https://github.com/rexyll/cnc-knowledge/actions/runs/45987534125)。
- [第六十八轮Quality Run 45987533954](https://github.com/rexyll/cnc-knowledge/actions/runs/45987533954)。
