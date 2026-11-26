# 数控机床备件库存备份 Coordinator Operation Ledger 生命周期与安全归档协议

**知识编号：** KNOW-000057  
**章节：** CH17 操作、维护与维修  
**状态：** 归档协议参考模型与测试已建立；尚未接入生产 Coordinator / etcd / 对象存储  
**关联知识：** KNOW-000051、KNOW-000054、KNOW-000055、KNOW-000056  
**关联资源：** ASSET-000088

## 1. 背景与问题边界

第四十一轮将 Coordinator Leader、scope fencing 和 ACTIVATE/REVOKE/PUBLISH Operation Ledger 放入统一 Admission aggregate schema v2。该设计把关键业务权威集中在同一个 revisioned aggregate 中，避免跨权威状态源双写；代价是 coordinator.operations 会持续增长，所有 aggregate 写入都需要处理完整状态值。

第四十二轮已建立容量画像探针，量化 scope/operation 数量对应的 canonical JSON 大小。本轮继续解决历史记录生命周期，但不直接修改生产实现：先定义可验证的归档协议，并建立纯内存参考模型，避免在尚未证明归档幂等与故障恢复之前删除现有记录。

## 2. 首要区分：etcd MVCC compaction 不是业务账本归档

etcd 的 MVCC compaction 清除的是指定 revision 之前的旧版本和历史事件；当前 revision 下仍然存在的键值不会因为 compaction 自动从应用状态中消失。应用若把全部历史操作继续编码在当前 aggregate value 内，etcd compaction 并不会替应用删除这些 operation 记录。参考 SRC-000404。

因此本章把两件事严格分开：

- **存储后端 MVCC compaction：** etcd 管理员对 etcd revision 历史的维护。
- **应用层 Operation Ledger archive/compaction：** Coordinator 明确选取已完成的业务 operation，将完整记录写入独立归档介质，再由 Coordinator 权威状态原子切换归档指针并从热索引移除这些记录。

不得把执行 etcdctl compaction 当作清理业务 Operation Ledger 的方案，也不得因 etcd 的存储版本已压缩就认定历史操作已归档。

## 3. 归档协议的核心不变量

### 3.1 未决操作不得归档

以下状态始终留在 hot ledger：

- PENDING_ACTIVATION
- REVOKING
- PENDING_PUBLISH
- RECOVERY_REVIEW

当前 scope 仍处于 ACTIVE 且其 lease_id + fencing_token 与 ACTIVATE operation 一致时，该 ACTIVATE 记录也必须保留。只有当旧 ACTIVATE 已被更高 scope token / 新 lease 取代，或 scope 已退出 ACTIVE 状态，并且该 scope 没有任何未决/恢复审查操作时，才可进入候选归档集合。

COMMITTED、REVOKED 是明确终态候选；仍需满足经批准的最短保留期、批次大小和其他组织政策。当前仓库没有已批准的保留期、法规留存期限或归档时限，因此参考模型要求调用方显式传入最短年龄、最大记录数和最大批次字节数，不填充生产默认值。

### 3.2 归档对象必须先于权威切换持久化

一次归档按以下顺序执行：

1. 读取当前 scope、aggregate revision、Leader 与 Admission lease 保护条件，并确定一批候选记录。
2. 使用规范化序列化生成归档批次；记录 scope、generation、前序 manifest digest、完整 operation 记录及 operation index key。
3. 以 SHA-256 内容地址执行 immutable put（目标对象已存在时，只允许字节完全相同）。
4. 重新读取归档对象，逐字节和 SHA-256 校验；不能读回或摘要不匹配时，任何 hot ledger 删除都不得发生。
5. 重新检查 Coordinator aggregate revision、Leader、scope archive head 和相关 Admission lease 条件；只有全部匹配才提交新的 archive manifest pointer，并从 hot ledger 移除本批次记录。
6. 若提交响应丢失，必须线性一致读回权威 scope pointer。只有 generation + manifest SHA-256 与本次预期完全匹配，才能判定已提交；读回不可用时报告 outcome unknown，不推断回滚或成功。

归档对象先写后切换意味着 CAS 冲突时可能留下未被引用的 orphan object。Orphan 不影响热账本权威，但不得在同一归档事务中立即删除；后续 GC 必须单独盘点所有 scope manifest、备份副本、恢复点、法律保留和保留策略，并获得企业批准。

### 3.3 幂等必须跨越 hot/archive 边界

归档后，旧 idempotency_key 不能被当成“不存在”。否则历史请求重放可能再次分配 scope token 或 publish sequence，造成重复业务操作。

每个归档 manifest 必须提供确定性的精确索引，至少以 sha256(scope + NUL + idempotency_key) 定位原始 operation，并保留：

- operation kind 与原始 request digest；
- scope、tenant、owner、domain、lease identity；
- fencing token 与 operation sequence（若适用）；
- manifest key/digest、Provider generation、原始终态；
- 创建/更新时间及可追溯批次位置。

重放时按以下优先级查询：

1. hot ledger 中的精确 operation key；
2. Coordinator 权威 scope pointer 指向的归档 manifest/index 链；
3. 只有得到完整、确定的 exact-not-found 结果，才允许新建该 idempotency key。

如果 scope 已有 archive pointer，但 archive store、manifest 或索引不可读/不完整，必须 fail-closed：不能把不可读误当成 not-found，不能分配新的 token/sequence，也不能继续签发对应 Provider proof。Bloom filter 等概率结构不可单独作为“确定不存在”的依据。

相同 idempotency key + 相同 request digest 返回原 operation；相同 key + 不同 kind/digest 必须拒绝。该规则覆盖 archive 链所有代际，而不是只检查最近一批。

## 4. Manifest 链与 scope 权威状态

每个 scope 独立维护一个 append-only archive chain。建议 manifest 字段：

| 字段 | 含义 |
|---|---|
| schema_version | 归档格式版本 |
| scope | 完整 tenant scope |
| generation | 从 1 单调递增的归档批次代际 |
| previous_batch_sha256 | 前一批 manifest 的内容摘要 |
| records | 有序 operation index key 与完整 operation record |
| object SHA-256 | 当前 manifest 内容地址，由内容计算 |

Coordinator scope 权威状态增加 archive metadata 时，至少需要：

- archive_generation
- archive_head_sha256
- archived_operation_count

这些字段只记录归档链位置与累计数量；不得替代或重置现有 high_water_token、latest_operation_sequence、lease state、Provider generation 或 pending operation 审查状态。

每批归档限制由调用方或经批准的运行策略显式传入 max_records 和 max_batch_bytes。批次过大时分批归档，不允许为清理历史而放宽后端请求限制或一次执行无限量删除。etcd v3.7 配置文档中 --max-txn-ops 默认 128、--max-request-bytes 默认 1,572,864 字节，二者均可按部署配置调整；它们是后端配置边界参考，不是本项目的生产预算。参考 SRC-000403。

当前 schema-v2 把全部操作放在一个 aggregate value 中；参考协议只模拟“一个 archive object + 一个权威 aggregate CAS”交接，不实现跨对象存储和 etcd 的分布式事务。未来若将 operation 拆为独立 KV keys，必须重新设计在目标 etcd max-txn-ops、request-size 和 Compare/Then/Else 数量约束下的提交算法，不能照搬当前单 aggregate 的事务假设。etcd Txn 的 If/Then/Else 原子性见 SRC-000405。

## 5. 恢复、审计与保留

- 归档对象应使用内容寻址并具备经过批准的冗余/备份策略；是否启用 WORM、对象锁、签名、加密和密钥托管由企业安全/合规责任方批准。
- 恢复时先验证 manifest 内容哈希、scope、generation 连续性、前序链接、operation key、累计记录数和 exact idempotency index，再允许读取对应历史 operation。
- Coordinator 恢复仍须执行既有外部 Provider high-water token 与 operation sequence floor 对账；归档链不得降低或代替外部 fencing floor。
- 归档不能把 RECOVERY_REVIEW 自动升级成 ACTIVE / COMMITTED，也不能据此重新绑定旧 Admission lease。
- 归档记录的物理删除、密钥销毁、跨区域副本清理和保留期到期处置不在本轮实现范围；没有企业审批与完整引用盘点时不删除。
- 审计查询必须可以从 hot record 或 manifest 链取得相同 operation identity 和终态语义；若归档服务不可用，应明确报告审计查询不完整。

## 6. 参考实现与测试范围

新增 scripts/spare_parts_operation_ledger_archive.py 与 tests/test_spare_parts_operation_ledger_archive.py。这是纯内存协议模型，使用 InMemoryImmutableOperationArchiveStore 模拟不可变对象存储；没有连接真实 etcd、SQLite、云对象存储或生产 Coordinator。

模型覆盖：终态/未决筛选、当前 ACTIVATE 保护、最短保留年龄、记录数/字节上限、内容寻址、put/read-back、CAS 冲突、lost-response reconciliation、manifest 前序链、归档幂等重放、payload 冲突、archive outage fail-closed、fencing/sequence floor 保留和不执行物理删除。

资源 spare-parts-coordinator-operation-ledger-archive-test-matrix-v1.csv（ASSET-000088）列出25项正式场景，全部 PROPOSED_NOT_APPROVED / NOT_RUN。CI 单元测试只验证内存参考模型的代码行为，不等于企业批准、对象存储持久化、多主机一致性或真实 Coordinator 集成验收。

## 7. 当前实现与迁移边界

本轮不修改：

- StoreBackedCoordinatorAuthority 当前 /cnc/admission/unified/v2/ schema；
- 现有 operation key 生成、prepare/confirm/signing/recovery 方法；
- SQLite/etcd authority store port、Leader TTL 和 Admission lease 生命周期；
- 生产 backup enabled 状态或任何企业归档/保留配置。

在生产实现前仍需完成：归档对象存储接口与部署选择、读后写一致性/不可变性契约、精确索引格式及容量设计、aggregate schema v3 迁移/回滚、archive pointer CAS 与现有 Leader/Admission guard 集成、真实故障注入、RPO/RTO/保留/法律保留审批、归档恢复演练和真实 etcd 多主机测试。

## 8. 来源

- SRC-000403：etcd v3.7 configuration options，max-txn-ops 与 max-request-bytes 默认值/可配置性。
- SRC-000404：etcd v3.7 data model，MVCC revisions 与 compaction 语义。
- SRC-000405：etcd v3.7 API，Txn Compare/Then/Else 的原子性与请求结构。
- KNOW-000055 / KNOW-000056：统一 Coordinator schema-v2 与容量画像。


## 9. CI验收记录

- **最终代码/测试head：** 4ed91a04138e30ecf2275c07bb947ecc872fadd2（main）。初始实现提交为 e0c168864826389bfd6bcfe2740a0069e1b063fe；随后修正了未知提交结果的故障注入时点，以及对应测试断言字段名。
- **CI：** [GitHub Actions Run 45817146500](https://github.com/rexyll/cnc-knowledge/actions/runs/45817146500)，head SHA与最终main提交一致，两个必需Job均completed/success。
- **测试结果：** 全库380项unittest通过（其中新增24项归档模型测试）；CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors。既有合成夹具验证报告有5项非阻断warning，内容仍为DRAFT/未获企业环境批准/业务用例NOT_RUN。
- **验收边界：** CI验证的是纯内存归档协议参考模型，不是实际对象存储持久性、真实etcd事务、多主机Coordinator、生产archive lookup或企业保留/法律保留验收。ASSET-000088的25条场景仍PROPOSED_NOT_APPROVED / NOT_RUN。
