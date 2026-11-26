# 数控机床备件库存备份 Provider 适配器 fencing token 贯穿与备份包范围原子提交

**知识ID：** KNOW-000044  
**章节：** CH17 操作、维护与维修  
**状态：** IN_PROGRESS / Provider 契约与合成集成验证

## 1. 严格模式与兼容模式

此前协调器能签发租约 fencing token，但适配器调用 Provider 时没有传递 token。只在 Provider 调用前后执行 lease validate，无法阻止已发出、延迟到达或暂停后恢复的旧写入请求。

本轮在 BackupStorageAdapter 增加显式安全模式：

- 默认 require_provider_fencing=False，保留旧 Provider 调用兼容性；该模式不能声称下游 fencing 已启用。
- 显式设置 require_provider_fencing=True 时，构造器要求配置 admission coordinator、Provider 声明 supports_fencing=True，并具备当前能力路径所需的 fenced 方法。
- 严格模式缺少协调器、能力声明或必需方法时，在启动/调用前 fail-closed；不回退到普通 PUT 或 multipart 写方法。
- 每个实际写 Provider 调用从 _bulkhead_slot 获得对应 ProviderAdmissionLease，并将 lease.fencing_token 交给 fenced Provider 方法。每次重试会重新申请租约和更新 token，但同一逻辑操作继续使用确定性 idempotency key，以便恢复不确定结果。

## 2. 统一备份包 fencing scope

若每个 object key 各自维护 token，高水位只保护同一个 key：旧写入者仍可能把迟到对象写入同一备份包中一个尚未写过的新 key。

因此，本轮把 fencing_scope 定义为适配器生成的备份包逻辑前缀 object_prefix。同一备份发布事务中的 payload 对象条件创建、multipart session begin、每一个 part 写入、multipart complete，以及最后发布的 BACKUP-RECEIPT.json 提交标记全部共用该 scope。

Provider 必须为 scope 保存持久且单调的高水位。任何一个写入成功推进高水位后，该包内其他 object key 上 token 更小的迟到写入也必须被拒绝。普通读取及 multipart parts list 不修改对象，不推进高水位。

该 scope 不是整个 Provider 帐户级别的全局 fencing：不同 backup_id 有各自的 package scope。若企业业务还需要保护当前唯一有效备份指针、跨备份版本替换或租户级共享对象，应把该逻辑对象/指针纳入另一个经批准的 fencing scope，并定义对应一致性事务。

## 3. Provider 方法合同

严格模式使用以下 fenced 方法：put_if_absent_fenced、begin_multipart_upload_fenced、put_multipart_part_fenced、complete_multipart_upload_fenced。每项写操作都携带 key、fencing_scope、fencing_token 和 idempotency_key；multipart 方法还携带 session、part 或完成摘要信息。

Provider 需在同一原子边界内完成：校验调用者身份及写入授权；读取该 scope 当前高水位；拒绝小于高水位的 token；验证同一幂等键的请求身份和内容摘要；提交对象/分块/完成标记；持久化新的高水位和操作回执。

相同幂等请求重放时可以返回原结果；同一 token 不允许覆盖不同操作或不同内容。更小 token 始终拒绝，即使它声称是同一请求。

## 4. 身份、权限与 token 可信性要求

fencing token 是并发顺序标识，不是身份认证凭据，也不是签名。真实 Provider 不得允许任意未授权客户端自行提交一个极大的整数来永久提高 scope 高水位。

生产合同还必须确保：只有经过认证且获准写入该租户/前缀的适配器主体可调用 fenced 方法；token 由受信任协调器签发，并通过受控服务端路径传入；Provider 对 scope 与 object key 的映射进行规范化和授权检查；审计记录 actor、scope、token、操作身份、内容摘要及结果；不能证明身份、scope 授权或原子条件更新时 fail-closed。

## 5. 本轮代码和测试

- BackupStorageAdapter(require_provider_fencing=True)：仅在显式启用时走严格 fencing 路径；未配置 coordinator 或 Provider 能力不完整立即拒绝。
- _bulkhead_slot()：向内部调用者交付当前 admission lease；_provider_call() 将对应 fencing token 传递给 fenced callback。
- _upload_payload() 与 publish_backup()：统一使用 backup package prefix 作为 fencing scope，覆盖对象、multipart begin/part/complete 和 receipt-last 提交。
- FencedMockObjectStorageProvider：合成原子操作夹具，按 package scope 维护高水位、幂等回执和写入日志。普通 MockObjectStorageProvider 和本地文件 Provider 不因此宣称支持 fencing。
- 新增4项适配器集成 unittest：严格模式启动门禁、payload/multipart/receipt token 传递、同 scope 跨 key 与 multipart 陈旧写拒绝、multipart complete 响应丢失后的幂等重放。

测试只证明本地合成 Provider 和当前适配器路径的合同行为。Mock 的锁保护是单进程内存原子性；并非数据库事务、远端条件 PUT、分布式锁或供应商认证机制。

## 6. CI 验收及范围边界

最终代码提交 38226d4b48a60dfba7a4b59f2951cf37a570f52c 对应 [GitHub Actions Run 45753519142](https://github.com/rexyll/cnc-knowledge/actions/runs/45753519142)：

- 全库221项 unittest 通过；
- CH12数值资源测试143项通过；
- knowledge_lint.py --strict：PASS（0 errors，5 warnings）；
- Provider self-check 字段 downstream_fencing_token_propagation_payload_multipart_receipt=PASS；
- Provider adapter Artifact ID 15086063425；SQLite coordinator Artifact ID 15086272742。

ASSET-000075定义12条额外合成验收场景，全部仍为 PROPOSED_NOT_APPROVED / NOT_RUN。测试报告不是供应商验收、渗透验证或企业业务测试。

尚未完成：真实云/本地生产 Provider 实现上述fenced方法；服务端高水位持久化、加密/签名、访问控制、权限/身份绑定、token伪造防护、真实网络超时和对象锁语义验证；跨机/跨区域 fencing；当前唯一有效备份指针的全局事务；生产数据恢复演练。

默认模式仍不具备下游 fencing。即使启用严格模式，只有真实 Provider 已证明这些方法真正原子实现并通过企业审批后，才能把对应资源域标记为生产可用。生产备份继续关闭，governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL，business_rule_assertions=NOT_EVALUATED。
