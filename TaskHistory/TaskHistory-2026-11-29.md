# 每日任务历史 — 2026-11-29

> 项目时区：Asia/Shanghai（UTC+08:00）

## CNC Knowledge Base — Round 98 结项（Provider Grant Floor 外部单调检查点）

- **实际结项时间：** 2026-11-29T00:02:15+08:00。
- **Repository / branch：** rexyll/cnc-knowledge / main；未创建新分支。
- **前序记录：** [TaskHistory-2026-11-28.md](TaskHistory-2026-11-28.md) 记录了本轮计划登记、第一版实现和当时的IN_PROGRESS状态。本文件记录跨越Asia/Shanghai零点后的CI修正与最终结项，不覆盖前一日历史。
- **首轮CI问题：** Run 46162469651中，全库775项测试运行、40项环境跳过，1项新测试断言失败。失败断言错误地要求checkpoint在setUp注册Provider Receipt key和Coordinator command key后仍等于bootstrap时的记录；正确预期应是两次独立trust registry变更后sequence从1推进到3。实现的状态推进正确，测试预期已修正。
- **代码增强：** 在CAS抛异常/返回不一致结果时，均使用独立checkpoint store精确read-back；只有读回完整记录与预期sequence、authority revision、state digest完全相等才确认成功。新增回归测试覆盖CAS接口已提交但响应内容不匹配的情况。
- **最终交付：**
  - `scripts/spare_parts_provider_grant_floor_checkpoint.py`：完整Floor schema/五张业务表逻辑摘要、外部Checkpoint Store接口、单调CAS测试fake、严格空库bootstrap和受保护wrapper。
  - `tests/test_spare_parts_provider_grant_floor_checkpoint.py`：14项专项测试，覆盖正常FENCE/ACTIVATE、trust registry变化、精确重放、SQLite旧快照恢复、同revision篡改、外部checkpoint回退、bootstrap限制、业务校验失败、CAS冲突/响应丢失/异常返回精确读回及故障fail-closed。
  - 更新CH17外部Floor恢复设计第12节、章节README、根TaskPlan、CH17 TaskPlan。
- **主要新增/修正提交：** 修正断言 `caa025ef0b562d1771f9053b2c7bc6aca79b752c`；CAS异常返回读回 `5f01e384dd9a8cf1ba93857bd20aa2f0fa96691f`；增加异常返回回归测试 `858a44a40a274e50200b4469e389de87671bd4db`。文档结项提交以本文件后续Commit SHA为准。
- **最终CI证据：** [Knowledge Quality Run 46162907743](https://github.com/rexyll/cnc-knowledge/actions/runs/46162907743)，对应最终代码/测试提交 `858a44a40a274e50200b4469e389de87671bd4db`，两个必需Job均completed/success：
  - Knowledge structure and data quality：全库776项unittest运行，40项环境跳过，其余736项通过；strict knowledge lint 0 errors / 5 warnings。
  - CH12 numerical resource tests：143项通过。
- **边界：** 本地CI仅验证单进程SQLite wrapper和in-memory CAS fake。fake不持久化，无法验证自身备份回滚；wrapper不提供跨进程锁。未连接真实etcd、Coordinator、Provider、KMS/HSM、object storage或IAM/RBAC；生产持久化、线性一致的外部checkpoint authority仍需另行实现。Production Unified schema-v2仍为唯一authority；Grant-aware Restore未实现，含Grant历史备份的通用Restore继续fail-closed；未执行候选导入、Restore、应用激活或Cutover。
- **状态：** DONE（2026-11-29；最终主分支Knowledge Quality CI两个必需Job全部成功）。

## CNC Knowledge Base — Round 99（Provider Grant Floor Etcd-native 单事务权威架构设计）

- **实际工作时间：** 2026-11-29T00:07:02+08:00 至 2026-11-29T00:09:11+08:00（Asia/Shanghai）。
- **Repository / branch：** rexyll/cnc-knowledge / main；未创建新分支。
- **前置结论：** Round98证明的只是单进程SQLite wrapper + in-memory CAS fake。SQLite业务事务与外部checkpoint CAS不是共同事务，CAS失败时只能fail-closed；不能将其包装成生产Etcd authority。
- **现有代码审计：**
  - scripts/spare_parts_provider_authority_store.py 已有 CoordinatorAuthorityStore、EtcdV3CoordinatorAuthorityStore、typed Compare/Put/Get/Delete及Txn分支Get；etcd mutating transport timeout归类为 AuthorityStoreOutcomeUnknownError，不自动重试。
  - scripts/spare_parts_provider_etcd3gw_driver.py 提供Etcd v3 Gateway driver，但由调用方注入/配置；本次未连接真实Etcd。
  - DurableCoordinatorAuthorityBackend仍是SQLite业务服务接口，不是Etcd Grant Floor业务状态机；scripts/spare_parts_provider_grant_floor.py仍是SQLite schema v5。
  - InMemoryEtcdV3Client只是契约测试替身，不证明Raft quorum、多节点持久性或生产故障行为。
- **设计交付：**
  - 新增 docs/17-operation-maintenance-and-repair/provider-grant-floor-etcd-native-atomicity-design.md。
  - 定义隔离Etcd namespace /cnc/migration/isolated/{single-id}/provider-grant-floor/v1/ 和meta/scope/operation/Provider key/Coordinator key/event键布局；实体路径由规范化身份摘要派生。
  - 规定FENCE reserve、ACTIVATE reserve、Provider signed Receipt confirm、Coordinator/Provider key lifecycle全部通过Etcd一个Txn进行Compare+Put；meta authority revision、trust revision、event sequence和state-root随业务记录一同原子变化。
  - 对验签时读取的Coordinator/Provider trust row增加Txn VALUE/MOD Compare约束；trust key或scope/operation有并发变化必须重新读取和重新验签。
  - Mutating Txn结果未知时只通过原operation ID和原signed envelope精确读回；完整scope/operation/event/meta/root匹配才确认，部分或不可能组合隔离。
  - 单独定义Etcd snapshot整体回滚边界：Etcd内部revision/state-root无法检测整群旧snapshot恢复。
  - 设计域外witness严格耐久模式：Witness PREPARE、Etcd PREPARE/COMMIT、Witness COMMIT、Etcd FINALIZE；FINALIZE前阻断下一笔写，调用方在Witness已确认且Etcd最终状态读回前不收到成功。明确周期性witness只具备有限RPO，不得表述为零丢失。
- **主要提交：** TaskPlan登记 963106fa606db1a10c478205768b45fa91a315ed / 266b4408bf9d4af6fa1b4bf69e2abd40e8a27299；设计文档 ac7cb81b5992fb7d2793894fd9d736583dcde090；Witness严格提交协议补充 0ff3dc613e3ec001cc9afd6054b95fbabf0c9026。
- **边界：** 本轮只交付架构设计，不实现Etcd-native Grant Floor service或生产witness adapter，不连接真实Etcd/Coordinator/Provider/KMS/HSM，不配置RBAC，不执行SQLite迁移、候选导入、Restore、应用激活或Cutover。Production Unified schema-v2仍为唯一authority；Grant历史通用Restore继续fail-closed。
- **状态：** IN_PROGRESS；待README/TaskHistory同步、全库质量CI和设计审查通过后再结项。
### Round 99 设计审查补充（2026-11-29）

- 新增设计细化提交：c9ccad04ea93a5fcb1df033ad2f286fdebdf6630。
- 补充Witness PREPARE的取消语义：Etcd PREPARE响应未知时，不可仅凭一次线性一致Range尚未发现pending intent就把Witness记录标记ABORTED；必须精确恢复原Txn，或在Etcd明确Compare失败/ABORT事务精确成功后结束intent。Etcd COMMIT确定完成后只能继续Witness COMMIT与Etcd FINALIZE，不允许再ABORT。
- 补充整体Etcd snapshot rollback后的数据恢复边界：witness sequence/root只能检测回滚，不能重建scope/operation/key/event正文；完整事件日志或受信备份/补齐日志缺失时，保持写隔离并逐scope受控重建。
- 明确单一namespace全局meta/event sequence会序列化各scope写入，形成吞吐热点；本轮接受作为v1正确性基线，未来分片必须另行证明root与全序关系。
- Round99仍为架构设计，不实现Etcd-native Floor service，不连接真实Etcd或配置RBAC，不执行迁移/Restore/Cutover；等待全库质量CI通过后再标记DONE。
### Round 99 最终CI与结项（2026-11-29）

- **最终验收：** [Knowledge Quality Run 46163880663](https://github.com/rexyll/cnc-knowledge/actions/runs/46163880663)，对应设计/TaskPlan/README/TaskHistory同步提交 head SHA d8cec4bf4d75f1701411d7dd71a352e2cb71fcf1，两个必需Job均completed/success。
- Knowledge structure and data quality：全库776项unittest运行，40项环境跳过，其余736项通过；knowledge lint 0 errors / 5 warnings；结构/data检查0 errors；CH17离线场景模拟30项、failed=0，明确business_test_status=NOT_RUN、external_connections=NO、writes=NO。
- CH12 numerical resource tests：143项通过。
- **结论：** Round99 Etcd-native Provider Grant Floor原子权威与域外Witness架构设计完成（DONE）。Etcd-native业务状态机、生产Witness持久服务、实际Etcd/RBAC/KMS/HSM、真实多节点和快照恢复演练均未实施；Production Unified schema-v2仍为唯一authority；Grant-aware Restore/Cutover仍不允许执行。