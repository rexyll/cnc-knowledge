# 备件库存备份 Admission Lease Authority 统一事务存储模型

**知识编号：** KNOW-000053  
**章节：** CH17 操作、维护与维修  
**状态：** Store-backed lease lifecycle reference 已实现，迁移评审中  
**关联知识：** KNOW-000050、KNOW-000051、KNOW-000052  
**关联资源：** ASSET-000084

## 1. 目标与边界

上一阶段已为 `CoordinatorAuthorityStore` 增加事务分支内的有序Get/Put/Delete。第三十九轮在其上建立一个后端无关的Admission lease authority参考组件，把lease的持久身份、request_id幂等、fencing token、续租/释放和受保护authority事务所需的lease校验统一到同一个KV/Txn/Lease存储端口。

本轮没有把既有 `SQLiteProviderAdmissionCoordinator` 完整替换为该组件。现有Admission实现还在同一个SQLite事务中处理等待队列、公平调度、全局并发配额、租户并发配额、策略hash、request_id和lease。只迁移lease而保留配额/等待队列在另一存储中，会造成双写和容量超卖风险。因此本组件当前只负责lease权威生命周期，不负责capacity admission、队列和公平调度。

同样，`SQLiteDurableCoordinatorAuthority` 仍直接读写自己的SQLite领域表。新增的lease比较可以被authority事务复用，但现有领域状态机尚未改造为通过该接口执行。不能据此声明Admission与Coordinator领域服务已经整体统一。

## 2. 键空间与记录模型

实现位于 `scripts/spare_parts_provider_admission_authority_store.py`，核心类型为 `StoreBackedAdmissionLeaseAuthority`。它复用现有 `ProviderAdmissionLease` 公共值对象，不把后端native lease ID暴露给调用者。

| 键 | 生命周期 | 作用 |
|---|---|---|
| `/cnc/admission/v1/meta/fencing-token` | 持久 | 全局单调fencing token计数器 |
| `/cnc/admission/v1/leases/<sha256(lease_id)>` | backend TTL lease | 当前活动lease记录，原子附着底层Store Lease |
| `/cnc/admission/v1/requests/<sha256(request_id)>` | 持久 | request_id幂等映射与RELEASED/EXPIRED终态tombstone |

lease与request索引存储相同的规范化JSON值，包括request/lease ID、owner、task、tenant、domain、fencing token、expires_at、state和backend_lease_id。request索引不附着TTL，因而活动lease过期后仍可防止同一request_id被重新用于另一业务动作。租户和domain信息保存在记录内；request_id与lease_id通过SHA-256摘要构造键名，避免把调用者提供的原始标识直接拼进KV路径。

计数器采用全局单键，而不是按tenant/domain分片，以保持与旧Admission Coordinator全局递增fencing token语义的一致性。并发申请者通过counter的version/mod_revision Compare争抢递增，只有一个事务能提交同一个token。

## 3. 获取Lease：counter、活动记录和幂等索引一次提交

`acquire()` 的过程：

1. 线性一致读取request_id索引。如果已存在，校验owner/task/tenant/domain身份；同一身份的活动请求返回原lease，不匹配身份则拒绝；已释放/过期请求拒绝复用。
2. 读取全局token counter并计算候选token；为新lease申请backend TTL Lease。
3. 在同一Txn中比较counter版本、request索引不存在和lease键不存在。
4. 成功分支一次性写入新counter、附着backend TTL的活动lease记录，以及不附着TTL的request索引。三者同revision提交。
5. CAS输家释放未被使用的backend TTL Lease并重读request索引；有界重试，不得绕过原request_id创建第二个逻辑操作。

若Txn提交后响应丢失，组件按原request_id线性一致读回。若可见同一身份的活动记录则恢复为成功；无法确知提交状态时抛出unknown-outcome错误，不能换一个request_id盲目重试。

## 4. 续租：迁移到新的backend TTL Lease

`renew()` 不仅更新expires_at，还把活动lease记录迁移到新授予的backend TTL Lease：

- 线性一致读取活动lease和持久request索引，核对两者记录相同，且输入的 `ProviderAdmissionLease` 与持久值完全一致。
- 新授予一个backend TTL Lease。
- 在同一个Txn中Compare旧活动记录值和旧request索引值，Success分支把活动记录写入新backend lease、把request索引更新为相同的新JSON。
- 新Txn成功后，旧backend lease不再拥有活动键，可撤销；若清理请求失败，旧Lease只会成为无权威键的TTL资源，最终自行到期。
- 旧的调用者lease对象因为expires_at与持久记录不再相同而失效；只有新返回对象可用于后续操作。

backend Lease API以整数秒为单位，组件要求调用TTL至少1秒，并向后端使用向下取整秒数，因而底层活动键可能比请求的浮点expires_at更早失效，不会为了凑足小数秒把权威键延长到请求期限之后。调用方应将该保守提前失效纳入续租窗口。

## 5. 释放与TTL过期

`release()` 在同一个Txn中Compare活动lease记录与request索引，然后删除活动lease键并把request索引更新为 `RELEASED`。提交后再撤销底层backend TTL Lease。释放与受保护写入若竞争同一lease guard，只有一个事务能通过精确值Compare。

底层TTL到期会删除活动lease键；request索引仍保留。读取到活动request索引但活动lease键已经缺失/过期时，组件尝试以CAS把索引转为 `EXPIRED`。即使终态修复暂时失败，活动键缺失也会使validate和authority guard失败关闭。

## 6. 与Coordinator Authority共享同一事务：Lease Guard

`active_lease_compares(lease)` 会线性一致读取活动lease和request索引，核验：

- 两个记录都存在且内容完全相同；
- state为ACTIVE；
- owner、tenant、domain、lease ID、token与过期时间同输入lease一致；
- expires_at仍满足当前时刻及调用方给出的最小剩余时间要求。

随后它返回两条 `AuthorityStoreCompare(VALUE == exact_bytes)`。调用方应把这两条compare与Leader epoch、scope revision、幂等操作等比较一起传入同一个 `CoordinatorAuthorityStore.transact()`，并在成功分支中写authority状态。快捷方法 `transact_with_active_lease()` 展示了这一用法。

若释放、续租或TTL过期与受保护写入并发，活动键或request索引的值/存在性会改变，原compare不再成立，受保护写入不能提交。注意：单独调用 `validate()` 后再发起另一个独立Txn并不等价于原子guard；必须把guard比较纳入同一个业务写Txn。

## 7. OUTCOME_UNKNOWN与幂等恢复

- **Acquire：** 使用同一request_id读回request索引和活动lease。匹配后返回原lease；无法完成读取则返回unknown outcome。
- **Renew：** 读回活动记录、request索引及backend lease attachment，只有完整匹配新值才认为续租已提交；无法确认时保留unknown。
- **Release：** 持久request索引已是RELEASED时可恢复成功；否则不能猜测。
- **CAS竞争：** 只允许有限次数重读/重试；request_id不能因竞争失败而被替换。

底层Lease Grant可能在后续Txn失败时留下短暂的空Lease，组件会尽力撤销；撤销失败只产生无authority key的TTL资源，不会授予调用者写权限。真实etcd网络超时、Lease grant响应丢失和服务端quorum失败仍须在真实集群验证。

## 8. 测试与验收矩阵

新增 `tests/test_spare_parts_provider_admission_authority_store.py`。5个契约测试方法分别在SQLite WAL store和单进程 `InMemoryEtcdV3Client` 测试替身上执行，共10次适配器测试执行，覆盖全局单调token和request_id幂等、身份冲突和终态复用阻断、续租时backend lease迁移及旧lease对象fencing、release/expiry与同Txn authority guard竞争、acquire提交后响应丢失的原request_id恢复、同request_id多写者竞争。

代码提交 `b9b7f6af6f34fc012fee95c96e77cca10c5e6442`；GitHub Actions Run 45775642132两个必需Job均completed/success。全库314项unittest、CH12 143项数值资源测试通过，strict knowledge lint 0 errors / 5 warnings，知识结构与数据质量0 errors。仓库单元测试仅验证参考适配器和合成测试替身，不构成ASSET-000084企业场景批准或执行。

ASSET-000084包含20条需求场景，全部保持 `PROPOSED_NOT_APPROVED` / `NOT_RUN`。

## 9. 尚未完成的统一迁移工作

1. 现有Admission scheduler仍在SQLite SQL表中实现公平队列、等待者、全局/租户配额、策略hash、拒绝指标和lease签发；本轮的Store-backed组件没有取代这些逻辑。
2. 不得把现有SQL配额事务与本组件KV lease事务拆开双写运行。下一步需把waiter、容量计数/配额、request幂等、fencing counter和lease active/tombstone一起迁移到同一Store/Txn后端。
3. `SQLiteDurableCoordinatorAuthority` 尚未接入本组件的 `active_lease_compares()`；需要把Leader epoch、scope token、operation ledger和Admission lease guards组装到同一事务。
4. 对etcd还没有真实客户端、gRPC/JSON Gateway配置、mTLS/RBAC、quorum与网络分区演练；当前etcd路径仍通过注入式driver和单进程测试替身。
5. 该组件尚不提供多键prefix Range/列表操作；未来迁移公平队列与容量核算需要额外定义可线性一致的prefix读取/聚合或采用显式配额计数器设计，并证明防超卖属性。

## 10. 生产治理状态

```text
production_backup_enabled = false
governance_readiness = BLOCKED_PENDING_ENTERPRISE_APPROVAL
business_rule_assertions = NOT_EVALUATED
```

## 11. 来源

- SRC-000397、SRC-000398：etcd v3线性一致Range、KV Txn和Lease API。
- SRC-000391、SRC-000392：SQLite事务与WAL参考。


### 文档同步CI验收

文档同步提交 `b79aede8a06cc55ac60681cbfc9acf03b1f44a55`；[GitHub Actions Run 45776156101](https://github.com/rexyll/cnc-knowledge/actions/runs/45776156101)两个必需Job均completed/success。全库314项unittest、CH12 143项数值资源测试通过；strict knowledge lint 0 errors / 5 warnings；知识结构与数据质量0 errors。该CI不改变ASSET-000084的20条场景 `PROPOSED_NOT_APPROVED / NOT_RUN` 状态，也不代表真实etcd或企业Admission系统验收。


### 第三十九轮最终元数据同步说明

- 代码提交 `b9b7f6af6f34fc012fee95c96e77cca10c5e6442` / [Run 45775642132](https://github.com/rexyll/cnc-knowledge/actions/runs/45775642132)：两个必需Job均completed/success。
- 文档提交 `b79aede8a06cc55ac60681cbfc9acf03b1f44a55` / [Run 45776156101](https://github.com/rexyll/cnc-knowledge/actions/runs/45776156101)：两个必需Job均completed/success。
- 最终元数据提交 `7209c094079830eb0789fbbe041757ee764e611c` / [Run 45776292616](https://github.com/rexyll/cnc-knowledge/actions/runs/45776292616)：两个必需Job均completed/success。
- 三次运行均以全库314项unittest、CH12 143项测试、strict lint 0 errors/5 warnings、知识结构质量0 errors为验收基线。ASSET-000084的20条正式场景仍PROPOSED_NOT_APPROVED / NOT_RUN。
