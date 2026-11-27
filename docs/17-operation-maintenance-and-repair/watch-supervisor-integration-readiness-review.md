# Watch Supervisor 与 Quorum Probe 生产接入边界审查

- **状态：** DONE（代码路径与接口边界审查；不是生产功能交付）
- **日期：** 2026-11-27
- **关联任务：** CH17-T004，第七十轮
- **审查范围：** 当前Coordinator authority服务、KV/Txn/Lease端口、可选Watch端口、etcd3gw HTTP Gateway驱动及其测试
- **目的：** 在实现Watch Supervisor或后台Quorum探测前，确认真实业务接入点、生命周期所有权和必要前置条件，避免把底层能力误认为生产服务能力。

## 1. 结论摘要

**当前不应直接实现或启用生产Watch Supervisor、定时Quorum探测线程或自动恢复状态机。**

仓库已经具备底层构件，也**已经存在一条store-backed业务Coordinator参考实现**；上一版审查漏看了第41轮的统一Coordinator实现，现更正如下：

1. `scripts/spare_parts_provider_unified_coordinator_authority.py`中的`StoreBackedCoordinatorAuthority`实现了Leader、scope fencing、ACTIVATE/REVOKE/PUBLISH operation ledger、序列分配与恢复协调业务方法，具备`DurableCoordinatorAuthorityBackend`所要求的同名接口。
2. 该业务服务以`StoreBackedProviderAdmissionCoordinator`为统一Admission scheduler，把Coordinator子状态写入同一schema-v2 aggregate；其业务状态转换通过同一个`CoordinatorAuthorityStore`事务比较aggregate revision、Leader TTL key及Admission活动Lease/request索引。
3. 现有`tests/test_spare_parts_provider_unified_coordinator_authority.py`已把同一契约分别运行于`SQLiteCoordinatorAuthorityStore`和`EtcdV3CoordinatorAuthorityStore(InMemoryEtcdV3Client)`。这是Fake etcd adapter证据，不是真实etcd服务器证据；此前未发现该业务实现的三节点Live集成测试或显式runtime Protocol符合性断言。
4. 旧`SQLiteDurableCoordinatorAuthority`和旧`SQLiteProviderAdmissionCoordinator`仍保留；尚无旧SQLite表/Admission队列向统一schema-v2 aggregate迁移的工具、写冻结、回滚和正式cutover。
5. `CoordinatorAuthorityWatchStore`仍是独立可选能力；`StoreBackedCoordinatorAuthority`没有持有Watch消费者或运行时Supervisor。Watch生命周期owner、start/stop、线程/任务调度及关闭流程仍未建立。
6. Watch迭代器是同步pull模型；`next(stream)`可能阻塞。生产探测key权限、请求deadline、频率、实例预算、指标出口、部署网络和业务SLO尚未定义。

因此，本轮只完成代码事实审查和接入门禁设计；**不新增运行线程、不自动触发Range、不改变默认超时、不启用自动重连/failover，也不改变schema-v2生产权威。**

## 2. 当前代码结构和职责边界

| 层次 | 当前实现 | 已具备能力 | 尚缺少的生产职责 |
|---|---|---|---|
| 业务服务契约 | `DurableCoordinatorAuthorityBackend`，定义于 `scripts/spare_parts_provider_authority_store.py` | 领导权、激活/撤销、序列分配、发布确认、恢复协调等业务操作契约 | 该契约尚无基于etcd KV端口的完整业务状态机实现 |
| 旧业务服务实现 | `SQLiteDurableCoordinatorAuthority` | SQLite WAL同机参考实现 | 旧SQLite数据迁移、冻结、回滚和cutover未完成 |
| Store-backed业务服务 | `StoreBackedCoordinatorAuthority` | Leader/Scope/Operation状态机；与Admission aggregate共用同一Store Txn；具备Durable backend方法集 | 仍是参考实现；真实etcd、多主机与生产Provider验证缺失 |
| Admission调度器 | `StoreBackedProviderAdmissionCoordinator` | schema-v2统一aggregate，保存quota、waiter、Admission Lease和Coordinator子状态 | 单aggregate是全局写串行点；旧SQLite Admission迁移未完成 |
| 基础存储端口 | `CoordinatorAuthorityStore` | 线性一致读、Txn、Lease操作 | 不负责业务服务生命周期或Watch运行时管理 |
| 可选Watch端口 | `CoordinatorAuthorityWatchStore` | 以revision为基础订阅KV变化；Watch只是唤醒提示，不能作为权威状态 | 未定义业务消费者、投影缓存所有权、并发模型和关停管理 |
| etcd适配器 | `EtcdV3CoordinatorAuthorityStore` | `linearizable_get`、`linearizable_range`、Txn、Lease及可选Watch转换 | 不负责创建进程级Supervisor，也不负责业务层恢复编排 |
| 传输驱动 | `scripts/spare_parts_provider_etcd3gw_driver.py` 中的 `Etcd3gwV3Client` | HTTP gRPC-gateway Range/Txn/Lease和Watch响应流解析；只读操作按既有策略处理endpoint故障 | 当前Watch是单向HTTP server-streaming；流建立后固定endpoint，不支持已建立流上的双向Progress/Cancel控制 |

当前职责关系：

```text
业务服务契约：DurableCoordinatorAuthorityBackend
  ├─ 旧实现：SQLiteDurableCoordinatorAuthority
  │    └─ SQLite WAL（同机参考）
  └─ Store-backed参考实现：StoreBackedCoordinatorAuthority
       └─ StoreBackedProviderAdmissionCoordinator
            └─ CoordinatorAuthorityStore
                 ├─ SQLiteCoordinatorAuthorityStore（本地契约测试）
                 └─ EtcdV3CoordinatorAuthorityStore
                      └─ Etcd3gwV3Client
                           ├─ linearizable Range / Txn / Lease
                           └─ HTTP Watch stream（独立可选接口）
```

关键区别：**存储适配器已经存在，不等于业务Coordinator已经迁移到该适配器。** 只有业务层开始真实持有etcd-backed服务后，针对业务运行时的健康探测和Watch生命周期管理才有明确的集成对象。

## 3. 已有能力核查

### 3.1 Quorum读能力

`EtcdV3CoordinatorAuthorityStore.linearizable_get()`和`linearizable_range()`调用底层Range时显式使用`serializable=False`。驱动的只读Range路径支持在符合条件的连接/超时错误下尝试其他endpoint。因此，底层已具备发起线性一致读的能力。

这仍然只是一次读操作的语义，不是持续运行的探测服务。目前没有：
- 进程级共享调度器；
- 多个Watch之间的探测复用；
- 探测请求独立deadline和频率预算；
- 探测状态缓存及其过期语义；
- 与业务服务生命周期关联的start/stop；
- 面向监控系统的统一指标出口。

探测若投入实施，应读取专用、最小权限范围；优先使用不产生写revision的只读Range。探测key是否存在并非健康模型的核心，核心是Range必须保持线性一致语义，并确认该身份有且仅有必要的读权限。

### 3.2 Watch能力

当前Watch接口以同步迭代器向调用方交付created、事件、Progress、canceled和异常终止等响应。第六十七至六十八轮已验证异常EOF、部分投影恢复、Compaction、静默与访问路径断开等边界。

这些测试建立的是协议和故障语义证据，不代表已交付业务级Watch消费者。尤其：
- `next(stream)`是阻塞式读取；
- Watch建立后不会自动切换到另一endpoint；
- HTTP gateway实现不具备当前活动流上的双向WatchProgress/WatchCancel；
- 流关闭不代表收到服务端Cancel确认；
- 任一不确定断流都不能继续信任不完整投影。

恢复规则维持不变：通过健康多数派执行线性一致Range快照，取得revision R，整体替换旧投影，再从R+1建立新Watch。

### 3.3 测试证据边界

`tests/test_spare_parts_provider_authority_store_watch.py`和`tests/test_spare_parts_provider_etcd3gw_driver.py`覆盖Fake/契约行为；三节点Compose Live测试提供etcd v3.7.0 / etcd3gw 2.7.0的一次性集成证据。

它们不能证明：
- 生产Coordinator业务服务已经切换到etcd；
- 生产Watch线程/任务管理正确；
- 在目标操作系统、容器、代理、NAT和负载均衡器路径上的实际SLO；
- 生产探测频率、并发数或资源消耗预算；
- 生产指标系统已经接入。

## 4. 为什么现在不实现后台探测

在没有业务服务owner的情况下加入后台线程会造成生命周期悬空：谁负责启动、停止和重建？一个进程有多个Store实例时是否创建多个探测器？Watch重建或服务滚动关闭期间如何避免探测线程继续使用已关闭Session？多进程部署时如何控制总探测请求率？这些问题目前没有可验证答案。

同样，不能简单地给每条Watch各建一个Quorum探测循环。这样会使探测请求量随Watch实例数增长，并可能在进程/实例扩容时形成探测风暴。推荐的目标模型是**每个业务进程一个共享探测服务**，多个Watch消费者读取最近一次探测结果；但其实现必须等待业务服务生命周期和部署模型确定。

## 5. 生产接入门禁

下列条件全部满足前，不把Watch健康Supervisor或Quorum探测器标记为生产功能。

### G1. 业务服务迁移完成

- 已有`StoreBackedCoordinatorAuthority`作为业务级store-backed参考实现；先补充显式`DurableCoordinatorAuthorityBackend` runtime Protocol符合性测试，并在真实三节点etcd上执行核心业务契约。
- 验证覆盖领导权TTL/epoch fencing、Admission Lease同Txn保护、ACTIVATE/REVOKE/PUBLISH、幂等、未知Txn结果、并发序列分配和恢复流程。
- 旧`SQLiteDurableCoordinatorAuthority`与旧`SQLiteProviderAdmissionCoordinator`仍作为迁移源和回退参考；单独设计并审批SQLite旧表/队列到Unified schema-v2的冻结、导入、核验、回滚和单权威cutover。
- 真实etcd Live通过仍只属于supporting evidence；不得据此自动切换生产权威或宣称正式企业验收。

### G2. 运行时生命周期已定义

- 明确服务实例创建、启动、健康、关闭、重启和升级的调用路径。
- 明确Watch数量、订阅范围、每条流的所有者，以及关闭/取消时序。
- 明确同步线程、线程池或异步任务模型；阻塞Watch消费不得阻塞Quorum探测。
- 明确多实例/多进程部署下每个进程的探测器数量和资源预算。

### G3. Quorum探测契约已定义

- 使用固定的专用只读Key/Range，限定最小权限；不读取业务敏感key作为健康探针。
- 探测使用线性一致Range（`serializable=False`），记录返回revision、延迟、endpoint和结果类别。
- 探测有独立且有界的deadline；频率、抖动、并发和结果缓存TTL由部署预算及SLO确定，不能从Compose测试值推导。
- 多个Watch共享探测结果；探测失败只改变Quorum-read维度，不自动关闭仍在交付事件的Watch。
- 不以`/maintenance/status`、TCP ACK或Watch本地Progress替代Quorum读验证。

### G4. 健康状态语义固定

至少独立记录：
- Watch流状态：CONNECTING / ACTIVE / SUSPECT / DISCONNECTED / RECOVERING；
- Watch最后响应、最后事件、最后Progress时间及Watch本地revision；
- Quorum Range探测状态、最近成功时间、耗时、revision和错误类别。

组合状态必须允许“Watch静默但Quorum读成功”和“Watch有响应但Quorum读失败”这两种情况。不得压缩成一个不能解释原因的健康布尔值。

### G5. 指标与隐私出口确定

- 指标至少覆盖Watch断开/重建计数、当前活动数、响应/事件/Progress时间、Quorum探测延迟和失败分类。
- endpoint标签采用有限集合；禁止将业务Key、Value、token或其他敏感数据用作metric label。
- 指标后端、日志结构、采样策略、告警阈值和运维Runbook有明确归属。

### G6. 故障验收与运维准备完成

- Fake测试覆盖并发关闭、重复启动、探测超时、Watch阻塞期间探测仍可运行、探测共享和资源释放。
- Live测试覆盖Quorum可读、Quorum失去多数派、单成员落后、Watch单独断流、读请求endpoint故障和恢复。
- 明确哪些故障可以重建Watch、哪些需要业务服务fail-closed；禁止对写Txn/Lease操作套用只读Range的自动重试策略。
- 正式场景矩阵获批前，CI Live结果仍只标记为supporting evidence。

## 6. 建议实施顺序

| 顺序 | 后续工作 | 前置条件 | 本轮状态 |
|---|---|---|---|
| 1 | 补齐StoreBackedCoordinatorAuthority与Durable backend Protocol一致性断言，并执行三节点真实etcd Live契约 | 已有Unified schema-v2 Store-backed实现 | IN_PROGRESS：Fake已覆盖，真实etcd待补 |
| 2 | 设计旧SQLite Admission/Coordinator表与Unified schema-v2 aggregate受控迁移/回滚cutover | 步骤1 Live evidence通过；外部Provider fencing floor来源确认 | BLOCKED：无迁移工具/审批 |
| 3 | 明确服务生命周期、Watch消费者和阻塞模型 | 统一业务服务单权威cutover设计明确 | TODO |
| 3 | 实现每进程共享Quorum探测器及状态快照 | 步骤1、2完成；读权限、deadline、频率预算明确 | TODO |
| 4 | 将Watch流观测和Quorum探测结果接入监控 | 指标出口、标签和告警SLO明确 | TODO |
| 5 | 开展目标部署环境下故障演练 | 生产网络路径和场景矩阵确定 | TODO |

## 7. 本轮决策与明确不做事项

1. 本轮只完成静态代码路径审查和设计门禁记录；不新增Python运行时代码或测试。
2. `watch_read_timeout`继续默认`None`；不把第六十八轮4秒测量值复制为生产配置。
3. 不新增TCP SO_KEEPALIVE选项、原生gRPC HTTP/2 PING、Lease-backed心跳写入、后台Quorum线程或Watch Supervisor。
4. 不添加自动重连、自动failover、自动重放cursor或不完整投影合并逻辑。
5. 不将本轮结果描述为etcd生产Authority切换、生产HA验收或Watch健康状态机交付。

## 8. 验收依据与关联资料

- `scripts/spare_parts_provider_authority_store.py`：`CoordinatorAuthorityStore`、`CoordinatorAuthorityWatchStore`、`DurableCoordinatorAuthorityBackend`及`EtcdV3CoordinatorAuthorityStore`。
- `scripts/spare_parts_provider_coordinator_authority.py`：旧SQLite Durable Coordinator业务服务实现。
- `scripts/spare_parts_provider_unified_admission_store.py`：统一Admission schema-v2 aggregate与store-backed scheduler。
- `scripts/spare_parts_provider_unified_coordinator_authority.py`：Store-backed Unified Coordinator业务服务实现。
- `tests/test_spare_parts_provider_unified_coordinator_authority.py`：SQLite与Fake etcd adapter业务契约测试。
- `scripts/spare_parts_provider_etcd3gw_driver.py`：HTTP gateway驱动、线性一致Range和Watch流实现。
- `tests/test_spare_parts_provider_authority_store.py`、`tests/test_spare_parts_provider_authority_store_watch.py`、`tests/test_spare_parts_provider_etcd3gw_driver.py`：存储契约、Watch和驱动Fake测试。
- `docs/17-operation-maintenance-and-repair/watch-connection-health-and-liveness-decision-record.md`：第六十九轮健康分层决策。
- `docs/17-operation-maintenance-and-repair/spare-parts-inventory-backup-provider-coordinator-etcd3gw-driver-and-three-node-integration.md`：当前驱动和三节点集成的完整技术记录。

**最终结论：** 先完成业务服务对存储端口的真实接入和生命周期归属，再实现共享探测；当前Watch/Quorum能力保留为可验证的底层构件，不提前宣称生产健康能力。


## 9. 第七十一轮审查更正与真实etcd验证计划

第七十轮审查发布后进一步检索历史实现，发现其“尚无etcd-backed业务Coordinator状态机”表述不准确。第41轮已经交付`StoreBackedCoordinatorAuthority`和`StoreBackedProviderAdmissionCoordinator`：Coordinator状态嵌入Unified Admission schema-v2 aggregate，并通过同一`CoordinatorAuthorityStore`事务处理业务转换及Admission活动Lease/request索引比较。它可使用SQLite存储适配器或etcd v3存储适配器。

该实现仍不是旧SQLite服务的自动迁移，也没有生产cutover；已有etcd侧测试使用`InMemoryEtcdV3Client`，并非真实etcd服务器。因此第七十一轮优先补充业务Protocol符合性断言和真实三节点etcd Live测试，随后仍需单独规划旧SQLite数据迁移、写冻结、回滚及单权威切换。

本次更正保留第七十轮“暂不增加Watch Supervisor”的决定：虽然store-backed业务Coordinator参考实现存在，但它尚未持有Watch stream owner，也没有业务级Supervisor、独立Quorum探测调度和监控生命周期。
