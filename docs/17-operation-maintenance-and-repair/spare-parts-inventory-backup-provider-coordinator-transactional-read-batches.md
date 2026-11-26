# 备件库存备份 Coordinator 事务内有序读取与状态快照

**知识编号：** KNOW-000052  
**章节：** CH17 操作、维护与维修  
**状态：** 设计与本地适配器实现已进入评审；不代表领域状态机迁移完成  
**关联知识：** KNOW-000050、KNOW-000051  
**关联资源：** ASSET-000083

## 1. 问题背景

KNOW-000051已经定义 `CoordinatorAuthorityStore` 的线性一致单键读取、Compare/Success/Failure事务和Lease接口。不过，Coordinator领域状态机在处理Leader epoch、scope高水位、幂等操作和Admission lease时，经常需要先观察一个或多个键，再以这些观察结果为条件写入新状态。

若将读取与条件写入拆成独立RPC，虽然写入端可通过mod_revision比较拒绝陈旧值，但调用端还需要自行组合多次读取、CAS失败重试和分支回读；若读取对象必须与写入处于同一个事务快照中，现有只返回事务是否成功的接口也无法提供数据。这是把SQLite SQL领域状态机迁移到通用KV/Txn端口前必须补齐的存储原语。

本轮在存储端口上增加事务分支内的有序精确键读取。它是迁移基础，不是将 `SQLiteDurableCoordinatorAuthority` 现有业务逻辑整体迁移到etcd的证据。

## 2. 新增契约

新增不可变操作类型：

- `AuthorityStoreGet(key)`：在已选中的事务分支中读取一个精确键，不执行范围扫描。
- `AuthorityStorePut(key, value, lease_id)`：创建或更新键，可将键附着到有效Lease。
- `AuthorityStoreDelete(key)`：删除一个精确键。

`CoordinatorAuthorityStore.transact(compares, success, failure)` 的两个分支现在都接受上述操作，并保持列表中的操作顺序。事务首先原子评估全部Compare，再且仅执行Success或Failure之一；被选中的分支中，Get/Put/Delete按提交给适配器的顺序执行。

`AuthorityStoreTxnResult` 新增 `reads` 元组，内容仅包含被选中分支内各个Get的结果，并按Get在该分支中的相对顺序排列。不存在的键以 `None` 表示。每条存在的记录继续暴露key/value、create_revision、mod_revision、version和lease_id；事务整体revision通过结果的 `revision` 返回。

### 2.1 顺序语义

例如，分支操作为：

```python
[
    AuthorityStoreGet(b"/authority/scope"),
    AuthorityStorePut(b"/authority/scope", b"new-state"),
    AuthorityStoreGet(b"/authority/scope"),
]
```

第一个Get观察本次事务内写入前的值，第二个Get观察本次事务内写入后的值。若事务发生写入，第二个Get返回记录的mod_revision应等于该事务revision；第一个Get保留原有mod_revision。读取结果并不意味着事务外的另一个调用者可在同一时间窗口中看到中间状态，事务提交仍是整体原子生效。

读取操作可以重复出现；同一事务分支内对同一个键的重复写操作仍然被拒绝，以避免不同适配器对重复写入顺序产生难以审计的解释差异。

## 3. SQLite WAL适配器

`SQLiteCoordinatorAuthorityStore` 在单个 `BEGIN IMMEDIATE` 事务中完成Compare、分支操作和读取结果收集。它按操作顺序读取数据库当前事务视图；Put记录使用该事务将要提交的revision，Get位于Put之后时能够读到新值。整个事务最多推进一次全局revision，多键更新共享同一提交revision。

SQLite WAL仅适用于同一主机上的本地文件系统参考部署。它没有提供多主机共识，不应通过NFS/SMB共享文件来构造分布式Coordinator。该store适配器与原有Admission Coordinator是否共享相同业务数据源，仍需由后续服务迁移显式解决。

## 4. etcd v3适配器

`EtcdV3CoordinatorAuthorityStore` 把事务分支中的Get编码为etcd Txn分支内的 `request_range`，Put和Delete分别编码为 `request_put` 与 `request_delete_range`。Get不是在Txn前后单独发出Range RPC，因此它读取的是被选中Txn分支中的顺序状态。

适配器要求注入式 `EtcdV3Client` 返回与事务请求操作逐项对应的响应序列。它按原分支操作序列提取 `response_range`，只把Get的返回值装入 `reads`。响应数量不匹配、Get缺少Range响应或返回记录不符合精确键约定时，适配器不得猜测状态，应失败关闭。

这里仍然没有实际构造gRPC/JSON Gateway网络客户端。etcd事务的线性一致性、quorum和故障恢复能力，需要真实etcd集群及其驱动通过独立验证来证明。当前 `InMemoryEtcdV3Client` 只在单进程内确定性模拟Txn操作和响应顺序。

## 5. 超时、响应丢失和重读

如果etcd Txn可能已经提交，但客户端在收到完整响应前发生超时或连接中断，适配器继续抛出 `AuthorityStoreOutcomeUnknownError`。这种情况下，调用方没有一个可信的事务返回值，也不能把空的 `reads` 解释为“事务未执行”。

恢复流程必须使用原有幂等键或operation identity进行线性一致重读，核对预期状态、operation digest和revision，再决定继续、确认或保持待人工/上层协调状态。不得通过生成新幂等键盲目重放同一个业务动作。读取能力不会消除OUTCOME_UNKNOWN。

## 6. 对Coordinator领域迁移的意义与限制

这次扩展让底层存储端口具备了事务内有序读取和读写组合能力，可用于后续把Leader、scope和operation ledger逐步迁移为KV记录。但以下关键工作尚未完成：

1. `SQLiteDurableCoordinatorAuthority` 的领域状态机仍直接使用SQLite SQL表；它当前仅结构化满足 `DurableCoordinatorAuthorityBackend`，并未通过 `CoordinatorAuthorityStore` 执行业务状态迁移。
2. 原SQLite流程在同一 `BEGIN IMMEDIATE` 事务中检查 `admission_requests` 活动租约并更新authority状态。迁移到etcd时，Admission lease的权威记录必须由同一个强一致后端管理，并在同一Txn内比较/验证；不能先单独Range Admission lease，再另起Txn更新authority，否则会重新引入TOCTOU窗口。
3. 需要补齐Admission服务对同一存储端口的写入/续租/释放契约，以及leader、scope、operation、pending列表和恢复高水位的键布局与版本化序列化。
4. 需要为CAS竞争建立有界重试和幂等恢复策略，并将事务响应丢失纳入上层服务的OUTCOME_UNKNOWN处理，不可只靠低层适配器返回成功标志。
5. 真实etcd集群、mTLS/RBAC、quorum/网络分区、多主机Leader切换及Provider端到端故障演练均未连接或执行。

## 7. 本轮实现和测试

代码变更：

- `scripts/spare_parts_provider_authority_store.py`：新增 `AuthorityStoreGet`、`AuthorityStoreTxnOperation` 与事务结果 `reads`；SQLite和etcd适配器均按选中分支的操作顺序执行Get/Put/Delete。
- `tests/test_spare_parts_provider_authority_store.py`：新增分支内写前/写后读取，以及Compare失败后从Failure分支读取快照的契约测试。两个测试方法分别由SQLite与内存etcd适配器运行，共新增4次适配器测试执行。

代码提交 `fec104016db56bcd1d841b134d2000f3d9838d4a)，GitHub Actions Run 45772420144通过两个必需Job：全库304项unittest、CH12 143项数值资源测试，strict knowledge lint 0 errors / 5 warnings，知识结构与数据质量0 errors。CI只证明仓库合成测试路径通过，不证明真实etcd服务或企业系统验收。

## 8. 设计验收场景

ASSET-000083列出16项事务读取/写入契约场景。该矩阵全部保持 `PROPOSED_NOT_APPROVED` / `NOT_RUN`；仓库CI运行的单元测试不改变企业场景矩阵的批准或执行状态。

## 9. 参考来源

- SRC-000397：etcd v3 API guarantees与线性一致读取约束。
- SRC-000398：etcd v3 KV Range、Txn和Lease API。
- SRC-000391、SRC-000392：SQLite事务与WAL行为参考。


### 文档同步CI验收

文档同步提交 `a1548dad6ad1c47d4645600a162a866076de6993`；[GitHub Actions Run 45772844275](https://github.com/rexyll/cnc-knowledge/actions/runs/45772844275)两个必需Job均completed/success。全库304项unittest、CH12 143项数值资源测试通过；strict knowledge lint 0 errors / 5 warnings；知识结构与数据质量0 errors。该结果仍不改变ASSET-000083的16条场景 `PROPOSED_NOT_APPROVED / NOT_RUN` 状态。
