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
