# TaskHistory — 2026-11-26

## CH17-T001 机床操作、维护与维修第一轮框架

- **实际完成时间：** 2026-11-26T01:00:00+08:00（Asia/Shanghai）
- **分支：** main（未创建其他分支）
- **实施提交：** 031a257996a9a45766ee30f4a5bb3fe4ce131621
- **新增正文：** docs/17-operation-maintenance-and-repair/overview.md
- **新增资源：** resouces/17-operation-maintenance-and-repair/operation-readiness-checklist.csv（25项空白检查模板）、ASSET-INDEX.md；更新资源README和章节README。
- **新增来源：** SRC-000382～SRC-000388，覆盖美国OSHA危险能量控制法规、ISO 16090-1/ISO 23125官方标准目录、Haas官方手册索引/安全说明/车床维护计划。
- **内容结论：** 建立操作、操作者日常维护、计划/状态维护、故障维修/服务四类责任边界；梳理开机准备、运行监视、正常停机、维修前风险识别和维修后复验的数据结构。
- **验收边界：** 检查模板结果初始均为NOT_ASSESSED；未填入型号级维护周期、润滑剂/冷却液牌号、压力/扭矩/温度限值。OSHA来源只作为美国法规适用场景，ISO工作草案不作为已发布标准，Haas资料不泛化到其他品牌。未复制受版权保护的标准或手册全文。
- **当前状态：** CH17-T001为IN_PROGRESS；缺少用户指定的目标机床型号/控制系统/选件及对应现行手册，故尚不能形成型号级SOP或维护周期表。CH17-T002～T004保持TODO。
- **后续工作：** 选定一个目标机床系列，获取现行官方操作/维护手册，将25项模板逐项映射到制造商条款、适用周期和判定依据。


## CH12-T003 SCURVE-01 标量三阶七段限跃度S曲线参考运行

- **完成时间：** 2026-11-26（Asia/Shanghai）
- **CI：** [GitHub Actions Run 45517202862](https://github.com/rexyll/cnc-knowledge/actions/runs/45517202862)，两个Job均success；CH12资源测试143/143，仓库测试和strict lint通过。
- **运行范围：** 标量静止—静止三阶七段S曲线，合成距离0.25m，最大速度0.2m/s、最大加速度1m/s²、最大跃度10m/s³，采样周期0.001s。
- **结果：** 总时间1.55s，巡航0.95s，峰值速度/加速度/跃度0.2m/s、1m/s²、10m/s³，终点位置0.25m、速度/加速度为0；七段、1551个采样点。manifest状态COMPLETED_REPORT_ONLY，acceptance_decision=DESCRIPTIVE_ONLY。
- **归档：** `resouces/12-control-and-machining-algorithms/generated/scurve-01-synthetic/`，包括时序CSV 1551×8、分段CSV 7×12、汇总CSV 1×19和manifest；CI确认archive=VERIFIED。
- **来源ID恢复：** 登记SCURVE原有引用SRC-000375～SRC-000378，分别对应S曲线阶次/段数论文、五轴CNC轴空间/笛卡尔空间约束论文、LinuxCNC路径控制与look-ahead官方文档。CH17七条来源统一顺延为SRC-000382～SRC-000388。
- **边界：** 仅为合成标量参考，不是多轴CNC规划器；不包含逆运动学、块段look-ahead算法实现、拐角混合、Snap限制、伺服动力学或机床验收。CH12-T003仍IN_PROGRESS。


## CH17-T004 库存备份治理、RPO/RTO与灾备就绪第十九轮（2026-11-26）

- **所在分支：** main；未创建新分支。
- **新增知识：** KNOW-000033《数控机床备件库存账本备份治理、RPO/RTO与灾备验收》；包含备份对象/职责、保留与删除、RPO/RTO测量边界、加密与密钥生命周期、异地存储评估和恢复演练生产启用门禁。
- **新增资源：** ASSET-000057备份保留策略空白模板；ASSET-000058 RPO/RTO目标空白模板；ASSET-000059加密与密钥管理空白模板；ASSET-000060异地存储供应商评估空白模板；ASSET-000061恢复演练验收矩阵（10项，全部PROPOSED_NOT_APPROVED/NOT_RUN）。
- **自动门禁：** 新增scripts/spare_parts_backup_governance_validator.py与tests/test_spare_parts_backup_governance_validator.py，校验五份CSV精确列结构、行宽、唯一ID、审批枚举、APPROVED记录的审批人/审批引用/带时区批准时间和关键字段；RPO必须非负、RTO必须为正；固定10条演练ID和未批准/未执行状态。纳入Knowledge Quality CI并归档JSON readiness Artifact。
- **治理状态：** validator PASS只表示结构和审批证据可解析；治理就绪状态固定BLOCKED_PENDING_ENTERPRISE_APPROVAL，production_backup_enabled=false；业务断言NOT_EVALUATED。
- **严格边界：** 未设默认保留期限、RPO/RTO、加密算法、云厂商或区域；未实施KMS/HSM、密钥操作、远端存储/复制或真实删除；不连接企业系统或生产账户、不保存密钥。所有恢复演练仍NOT_RUN，CH17-T004继续IN_PROGRESS。


### 第十九轮CI最终验收补记

- **main最终实现提交：** 9e8e3e0b19d7052b2899515575747f1c0b100834。
- **GitHub Actions：** Run 45732010499，Knowledge structure and data quality、CH12 numerical resource tests两个Job均completed/success。
- **测试与lint：** 全库127个unittest方法通过；治理校验器RESULT: PASS（0 errors）；strict knowledge lint RESULT: PASS（0 errors）。
- **治理readiness Artifact：** ch17-backup-governance-readiness-45732010499，Artifact ID 15076713318。5个CSV文件schema全部PASS，4份企业政策模板均无记录，10条恢复演练均为PROPOSED_NOT_APPROVED / NOT_RUN；governance_readiness保持BLOCKED_PENDING_ENTERPRISE_APPROVAL，production_backup_enabled=false。
- **提交序列：** 治理实现/模板 095deffdbf173c70f973d15844033b7a0deeaa7b / Run 45731635763两个Job成功；知识文档/实体登记 32fa8aa889350398539945620df7ad418e9e46a5 / Run 45731937638两个Job成功；恢复演练矩阵定义和校验加强 9e8e3e0b19d7052b2899515575747f1c0b100834 / Run 45732010499两个Job成功。
- **遗留：** 未批准企业保留、RPO/RTO、密钥和供应商政策；未实现KMS/HSM/远端存储/加密或真实灾备测试；CH17-T004仍IN_PROGRESS，业务断言NOT_EVALUATED。


## CH17-T004 供应商中立备份存储适配器与Mock验证第二十轮（2026-11-26）

- **所在分支：** main；未创建新分支。
- **新增代码：** `scripts/spare_parts_backup_storage_adapter.py`，定义ObjectStorageProvider最小契约（capabilities / put_if_absent / get_object），实现FileSystemStorageProvider、MockObjectStorageProvider和BackupStorageAdapter；无delete/list接口。
- **提交协议：** 上传BACKUP.json、COMMIT.json、ledger.json、snapshot.json四个负载后，最后发布BACKUP-RECEIPT.json作为提交标记；回执包含负载键、版本ID、长度、SHA-256和原始manifest摘要。半途失败无回执，不是完整备份；同内容可续传，不同内容冲突。
- **验证/恢复：** 验证回执自摘要、对象键集合、负载长度/摘要/版本和原备份语义；通过后才恢复到空白隔离目录。
- **新增资源：** ASSET-000062 Provider能力评估矩阵；ASSET-000063 12项适配器测试矩阵。新增KNOW-000034和独立知识文档。
- **CI：** Knowledge Quality新增Mock适配器self-check与报告Artifact；初始CI发现版本读取和测试篡改样本问题，已修复并提交新版本。最终Run和Job状态待确认后补录。
- **边界：** 仅本地临时目录/内存Mock，无真实云网络、账户/凭据、KMS/HSM、加密、对象锁、远端副本或删除操作。Mock声明不是真实供应商能力证据；企业备份启用门禁保持BLOCKED_PENDING_ENTERPRISE_APPROVAL。


### 第二十轮最终CI验收补记

- **最终main代码提交：** 2b95bca7741efa359bd287ffec16dc9c98f131c7。
- **GitHub Actions：** [Run 45732798249](https://github.com/rexyll/cnc-knowledge/actions/runs/45732798249)，Knowledge structure and data quality、CH12 numerical resource tests两个Job均completed/success。
- **自动测试：** 全库140个unittest通过；新增13个适配器专项unittest；strict knowledge lint `RESULT: PASS (0 errors)`；Provider/备份治理校验流程均通过。
- **适配器Artifact：** `ch17-backup-storage-adapter-45732798249`，Artifact ID 15076314703。报告显示Mock对象上传、回执发布、完整性验证与隔离恢复PASS；无外部连接、凭据/密钥、网络和删除操作。
- **CI修复过程：** Run 45732501248发现两项对象版本读取错误和一项无效篡改测试；Run 45732585785修复后140个单测通过，但脚本直接运行时repo import path仍缺失；最终提交2b95bca7741efa359bd287ffec16dc9c98f131c7补齐路径初始化，Run 45732798249全部成功。
- **统计与边界：** CH17当前14篇KNOW、59个实体、56项资源。13个新增unittest与12条资源场景定义分别统计。无真实云Provider/网络/凭据/KMS/HSM/加密/对象锁/异地复制；CH17-T004保持IN_PROGRESS、business_rule_assertions=NOT_EVALUATED、production_backup_enabled=false。


## CH17-T004 备份Provider安全与分块可靠性第二十一轮（2026-11-26）

- **分支：** main；未创建新分支。
- **代码：** Provider能力声明扩展身份认证、授权模型、租户隔离、审计、multipart和前缀范围盘点。Mock Provider实现principal/action/prefix授权检查、租户命名空间隔离模拟和不含负载的元数据审计。
- **分块协议：** 新增MultipartObjectStorageProvider，确定性upload ID、分块SHA-256、分块序号/总长度/总摘要校验、重复分块幂等、内容冲突拒绝、断点续传；abort仅清理尚未完成分块会话。
- **孤儿盘点：** 新增ScopedInventoryProvider前缀范围对象元数据与multipart session盘点，区分UNCOMMITTED_ORPHAN_CANDIDATE、PUBLISHED_VERIFIED、PUBLISHED_PACKAGE_INCOMPLETE_OR_UNEXPECTED_OBJECTS、PUBLISHED_INVALID和未完成分块会话。回收建议只读、PROPOSED_NOT_APPROVED且不可执行；无已完成对象delete API。
- **测试：** 新增10个unittest方法；全库150个unittest通过。最终CI Run 45737732766两个Job success；strict knowledge lint 0 errors；Provider Artifact `ch17-backup-storage-adapter-45737732766`（ID 15079009952）。
- **资源：** KNOW-000035、ASSET-000064～000066。身份/权限和孤儿回收模板为空白；14项可靠性测试矩阵全部PROPOSED_NOT_APPROVED / NOT_RUN。
- **未完成：** 未接真实IAM/云账号/凭据/网络；未实现真实加密、KMS/HSM、对象锁、云端审计或已完成对象删除；未批准保留期/回收策略，生产备份保持关闭。


### 第二十一轮最终CI与资源格式验收补记

- **实现提交：** Provider ACL/multipart/只读盘点实现 `a958c95d7a25e149aa884f72528cc414b1fbed64`；新增10个专项测试的提交 `08adad0f35fd3528121b5bc9ca424d12c558f757`。
- **实现CI：** [Run 45737732766](https://github.com/rexyll/cnc-knowledge/actions/runs/45737732766)，两个Job均completed/success；全库150个unittest通过；strict knowledge lint 0 errors；适配器Artifact `ch17-backup-storage-adapter-45737732766`，ID 15079009952。
- **知识/资源提交：** 文档和实体登记 `d3049ce70e27369fd8bec8caeed47fd75d8d184b`；可靠性矩阵11列/14行修正 `540ab361a59dd54a2eb078e58257da4d4d8238dd`。
- **最终记录CI：** [Run 45738063901](https://github.com/rexyll/cnc-knowledge/actions/runs/45738063901)，两个Job均completed/success；全库150个unittest通过，Knowledge Quality 0 errors；适配器Artifact ID 15080002233。
- **资源格式复核：** 身份权限评估模板26列、孤儿盘点/回收审批模板30列、Provider可靠性测试矩阵11列/14条数据行，数据行列宽一致。
- **最终边界：** 主分支main；15篇KNOW、63个实体、59项资源；孤儿回收候选均未批准且不可执行。无真实云/IAM/凭据/密钥/网络/加密/已完成对象删除，生产备份未启用。


## CH17-T004 备份Provider重试与一致性第二十二轮（2026-11-26）

- **实现代码：** `scripts/spare_parts_backup_storage_adapter.py`新增ProviderTransientError和outcome_unknown，提供只对瞬态错误生效的有界指数退避（默认max_attempts=4、base=0.1s、max=2s、sleep可注入）。
- **Mock故障注入：** 服务端已写入对象/分块/完成对象后故意丢失响应；延迟读可见、瞬态GET故障、历史版本切换与历史版本不可用。
- **幂等恢复：** 使用原对象键、backup ID、upload ID、分块序号和相同字节重试；已提交对象/分块复用；重试预算耗尽不返回PUBLISHED/VERIFIED，永久错误不重试。
- **版本：** receipt固定历史版本；当前版本切换时仍读取历史版本；历史版本缺失时失败关闭，不回退latest。
- **测试：** 新增9项专项unittest，Provider专项合计31个，当前全库159个unittest通过。最终代码Run 45738812474两个Job均success；扩展self-check CI Run 45738938023待最终确认。
- **自检Artifact：** 自检增加commit timeout、read-after-write延迟、瞬态读取及历史版本切换的组合路径；Artifact及最终Run待CI结束后记录。
- **资源：** 新增KNOW-000036与ASSET-000067（12条重试/一致性故障场景）；全部PROPOSED_NOT_APPROVED / NOT_RUN。
- **边界：** 没有真实云端限流、Retry-After、读一致性、版本生命周期、HTTP/SDK超时验证；无网络/凭据/KMS/HSM/加密/对象锁/生产备份。


### 第二十二轮重试与一致性测试扩展补记

- 新增Retry-After处理测试：Provider提示10秒时，以配置的2秒最大延迟封顶；Provider专项unittest由31增至32，全库由159增至160。
- ASSET-000067由12条扩展为13条场景，新增PRC-013（Retry-After提示与本地延迟上限）。所有场景仍为PROPOSED_NOT_APPROVED / NOT_RUN。
- 第二十一轮和第二十二轮三个Provider测试矩阵已修复状态列顺序：synthetic_only=TRUE、approval_status=PROPOSED_NOT_APPROVED、execution_status=NOT_RUN、notes最后列。


### 第二十二轮最终代码与故障自检CI验收补记

- **代码/测试：** [Run 45739249726](https://github.com/rexyll/cnc-knowledge/actions/runs/45739249726)，Knowledge structure and data quality与CH12 numerical resource tests两个Job均completed/success；全库160个unittest通过，新增10项Provider专项测试，适配器专项合计32项。
- **组合自检：** [Run 45738938023](https://github.com/rexyll/cnc-knowledge/actions/runs/45738938023)，两个Job均completed/success；Mock self-check中的普通对象/回执提交、写成功响应超时恢复、读可见性/瞬态GET重试、历史版本切换后的固定版本验证及隔离恢复均PASS；Artifact `ch17-backup-storage-adapter-45738938023`，ID 15079098689。
- **矩阵列顺序修复：** [Run 45739179773](https://github.com/rexyll/cnc-knowledge/actions/runs/45739179773)两个Job均success。ASSET-000063/066/067均已复核状态字段列顺序及行宽，13条本轮场景均为TRUE / PROPOSED_NOT_APPROVED / NOT_RUN。
- **参数边界：** 默认retry_max_attempts=4、base=0.1s、max=2s是代码默认而非生产推荐；Retry-After 10s的Mock用例按本地cap 2s封顶。当前无随机jitter；生产接入需重新评审限流语义、jitter、deadline与全局重试预算。


## CH17-T004 熔断、舱壁与任务重试预算第二十三轮（2026-11-26）

- **代码：** 新增四域CircuitBreaker（read/write/multipart/inventory）、CLOSED/OPEN/HALF_OPEN状态机、冷却后半开探测、单探测并发配额及快速OPEN拒绝。
- **舱壁：** 各域BoundedSemaphore默认read=4/write=2/multipart=2/inventory=1；默认0秒等待，满载抛ProviderBulkheadFullError；成功和异常路径均释放槽位。
- **任务级RetryBudget：** ContextVar将一个顶层备份/验证/恢复/盘点操作的嵌套Provider调用累计到同一预算，默认20；并发线程/任务预算隔离，耗尽抛RetryBudgetExceededError。
- **测试：** 新增9个专项unittest；全库169个unittest通过，Run 45740068529两个Job均success。自检扩展Run 45740213445待最终确认。
- **资源：** 新增KNOW-000037、ASSET-000068；14条熔断/舱壁/预算场景定义，全部TRUE / PROPOSED_NOT_APPROVED / NOT_RUN。
- **边界：** 控制仅限单Adapter实例/进程，不构成分布式熔断、全局QPS或集群公平性控制；所有默认参数均待生产测量和审批。


## 第二十三轮最终CI验收补记（2026-11-26）

- **实现/测试提交：** Provider CircuitBreaker、Bulkhead、RetryBudget代码提交 `507ac0f39d97700b9019f1533e46f8091c4db5ba`；新增9项专项unittest提交 `2d0ac86484e3a1829eb97d26ee24dc0030bf04f3`。
- **代码/测试CI：** [Run 45740068529](https://github.com/rexyll/cnc-knowledge/actions/runs/45740068529)，Knowledge structure and data quality与CH12 numerical resource tests两个Job均completed/success；全库169个unittest通过。
- **增强Mock自检：** [Run 45740213445](https://github.com/rexyll/cnc-knowledge/actions/runs/45740213445)，两个Job均completed/success；熔断OPEN/快速拒绝/HALF_OPEN恢复、零总预算失败关闭和既有备份上传/验证/隔离恢复均PASS；Artifact `ch17-backup-storage-adapter-45740213445`，ID 15081155445。
- **知识/资源最终同步：** [Run 45740530720](https://github.com/rexyll/cnc-knowledge/actions/runs/45740530720)，两个Job均completed/success；全库169个unittest通过，strict knowledge lint 0 errors；Provider Artifact `ch17-backup-storage-adapter-45740530720`，ID 15080399203。
- **资源：** KNOW-000037、ASSET-000068；14条熔断/舱壁/预算测试场景均TRUE / PROPOSED_NOT_APPROVED / NOT_RUN。
- **最终仓库：** main；17篇KNOW、67个登记实体、61项资源。无真实云账号/网络/凭据/密钥；控制器不跨Adapter实例/进程分布式共享；生产备份关闭。


## CH17-T004 Provider公平调度与任务控制第二十四轮（2026-11-26）

- 在 `scripts/spare_parts_backup_storage_adapter.py` 中新增 `ProviderTaskContext`、`ProviderFairBulkhead`、任务取消/截止时间终止异常和按操作域公平队列。
- 调度规则：调用方显式传入优先级（数值越大越优先），同有效优先级FIFO；等待时间按老化间隔提升effective priority，降低长期任务饥饿风险。无默认恢复/备份/盘点业务优先级映射。
- 新增每租户、每操作域的并发额度；加入排队期间取消、Provider边界取消/deadline及退避期间deadline检查。所有控制器本地单Adapter/进程生效。
- 新增5项专项unittest；新增ASSET-000069，15项合成调度/取消/deadline测试场景，全部PROPOSED_NOT_APPROVED / NOT_RUN。
- 代码、测试与知识/资源登记已纳入本次提交；CI状态待本提交触发后核实。未访问真实Provider/云账户/身份服务，不做跨进程或生产负载声称；生产备份维持关闭，企业治理门禁仍阻断。


## CH17-T004 Provider公平调度与任务控制第二十四轮最终验收（2026-11-26）

- **首次CI问题及修复：** Run 45741995037执行174个测试时，两项新增测试在断言处因未导入 `ProviderTaskCancelledError` 与 `ProviderTaskDeadlineExceededError` 发生NameError；调度相关的优先级、aging及租户配额测试均已通过。提交 `dc2deced6db5138a6880f71df190dd9a6549d45b` 补齐测试导入。
- **最终代码/测试CI：** [Run 45742134721](https://github.com/rexyll/cnc-knowledge/actions/runs/45742134721)，Knowledge structure and data quality与CH12 numerical resource tests两个Job均completed/success；全库174个unittest通过，其中Provider适配器专项46个。
- **静态质量与Mock自检：** `knowledge_lint.py --strict` 为PASS（0 errors）；`spare_parts_backup_storage_adapter.py --self-check`为PASS。Provider Artifact [ch17-backup-storage-adapter-45742134721](https://github.com/rexyll/cnc-knowledge/actions/runs/45742134721/artifacts/15081747151)，ID 15081747151。
- **交付：** KNOW-000038、ASSET-000069；15条公平调度/租户配额/任务取消/deadline场景规格全部保持TRUE / PROPOSED_NOT_APPROVED / NOT_RUN；main提交包含功能实现 `177033b417884f5ddea4812879cb30536e068b8a`、测试import修复 `dc2deced6db5138a6880f71df190dd9a6549d45b`。
- **当前限制：** 本地单Adapter/进程隔离；同步Provider在途请求无法强制取消；无跨进程/跨容器/真实Provider/生产负载证据。生产备份仍关闭、治理门禁BLOCKED_PENDING_ENTERPRISE_APPROVAL、业务断言NOT_EVALUATED。


## CH17-T004 Provider多Adapter共享协调与租约恢复第二十五轮（2026-11-26）

- 新增 `ProviderAdmissionCoordinator` 抽象与同进程 `InMemoryProviderAdmissionCoordinator`；多个Adapter可共享一份并发配额、租户配额、等待队列与令牌桶状态。
- 新增共享read/write/multipart/inventory并发上限和每租户域内配额；跨实例公平排队使用priority aging/FIFO。共享令牌桶按域速率/burst控制Provider尝试，限流抛出 `ProviderRateLimitExceededError`，不被误归类为Provider瞬态故障。
- 新增带owner/tenant/domain/expiry/fencing token的租约；支持续租、匹配释放、有效性检查、到期回收和旧租约fencing。调用结束时若租约已失效，`ProviderAdmissionLeaseLostError.outcome_unknown=True`，不返回成功。
- 新增7项专项unittest；ASSET-000070定义16个合成多实例/租户/限流/租约场景，全部PROPOSED_NOT_APPROVED / NOT_RUN。
- **限制：** 该Mock仅同一Python进程共享，不是跨进程/跨机器协调服务；无持久化、自动心跳、网络分区/主备/quorum/下游fencing。远端请求可能在本地租约过期后仍生效，必须以Provider硬超时、幂等对象键和提交状态盘点处理。
- 所有工作仅改动main；不连接真实云、身份系统或企业存储。生产备份维持关闭，治理门禁仍BLOCKED_PENDING_ENTERPRISE_APPROVAL，业务断言NOT_EVALUATED。


## 第二十五轮首轮CI问题与租约异常路径加固（2026-11-26）

- 首轮Run 45743739362中，新增181个全库unittest有2个错误：测试模块未导入 `ProviderTaskContext`，导致两个直接协调器租约测试在NameError处停止；其他共享准入测试已通过。
- 同时复核发现Provider callback抛出异常时，context manager原先会跳过退出前的租约有效性检查。已加固为成功/异常退出路径均检查租约；若租约已失效，统一抛 `ProviderAdmissionLeaseLostError`，避免瞬态错误路径继续自动重试。
- 新增回归测试验证租约到期时，Provider永久异常和瞬态/outcome_unknown异常均不触发第二次尝试；测试import补齐 `ProviderTaskContext`。
- 测试规格ASSET-000070扩为17条；总测试预期182项，Provider专项54项。修复后CI待重新执行。


## CH17-T004 Provider多Adapter共享协调第二十五轮最终验收（2026-11-26）

- **首轮CI问题及修复：** Run 45743739362中，2个直接租约测试因测试文件遗漏导入 `ProviderTaskContext` 产生NameError。提交 `a77a4b51723fe9f2e01109cca0496cd00d843a37` 补齐导入。
- **异常路径加固：** Provider callback无论正常返回或抛出异常，Adapter在共享租约配置下都检查租约是否仍有效；租约已失效时统一以 `ProviderAdmissionLeaseLostError.outcome_unknown=True` 失败关闭，瞬态错误不会触发第二次重试。新增回归验证永久异常/瞬态异常两类路径。
- **最终CI：** [Run 45743927996](https://github.com/rexyll/cnc-knowledge/actions/runs/45743927996)，两个Job均completed/success；全库182个unittest通过，Provider适配器专项54项；strict knowledge lint PASS（0 errors）。
- **Mock Artifact：** [ch17-backup-storage-adapter-45743927996](https://github.com/rexyll/cnc-knowledge/actions/runs/45743927996/artifacts/15081984380)，ID 15081984380；self-check PASS。
- **交付：** KNOW-000039、ASSET-000070；17条同进程多Adapter共享协调场景均TRUE / PROPOSED_NOT_APPROVED / NOT_RUN；CH17统计19篇KNOW、69个实体、63项资源。
- **限制：** 同一Python进程的多个Adapter对象共享Mock；不证明跨进程/主机、真实Provider、网络分区、协调服务高可用、自动心跳或下游fencing。生产备份仍关闭，治理门禁BLOCKED_PENDING_ENTERPRISE_APPROVAL，业务断言NOT_EVALUATED。


## CH17-T004 Provider共享协调器故障注入与fail-closed第二十六轮（2026-11-26）

- **分支：** main；未创建新分支。
- **实现：** InMemoryProviderAdmissionCoordinator新增协调器可用状态和六阶段一次性故障注入（acquire、acquire_response、renew、release、validate、snapshot）；新增ProviderCoordinatorUnavailableError与ProviderCoordinatorStateUnknownError。
- **安全语义：** 协调器准入前不可用时fail-closed且Provider callback不执行；acquire响应丢失时允许协调器保留未返回给调用方的TTL租约，但Provider不执行；Provider已执行后validate/release失败或协调分区时，结果按未知处理并阻止自动重试。未实现fail-open。
- **测试/资源：** 新增6项Provider专项unittest；共享协调故障矩阵扩展到24条，全部TRUE / PROPOSED_NOT_APPROVED / NOT_RUN；新增KNOW-000040，扩展ASSET-000070。
- **限制：** 故障注入仅为同进程Mock，不是真实网络分区/服务故障；未实现跨进程共享、自动心跳、协调器主备/quorum、恢复抖动/限速、队列上限或下游fencing。生产备份仍关闭。
- **实现提交与CI修复：** 首轮实现提交 fdac7308f23f4e4ab656174be92f57b987d559fc；Run 45745264278失败，原因是acquire故障钩子误插入本地ProviderFairBulkhead，导致AttributeError。修复提交 1a9a623e52475059872d8662fb64ee8956b973c2 将检查移至InMemoryProviderAdmissionCoordinator.acquire()。
- **最终CI：** [Run 45745399203](https://github.com/rexyll/cnc-knowledge/actions/runs/45745399203)，Knowledge structure and data quality、CH12 numerical resource tests两个Job均completed/success；全库188个unittest通过，本轮新增6项Provider故障注入测试已包含在内。
- **专项状态：** Provider专项测试共60项；knowledge_lint.py --strict为PASS（0 errors）；Provider Mock self-check PASS，Artifact [15083022622](https://github.com/rexyll/cnc-knowledge/actions/runs/45745399203/artifacts/15083022622)；备份治理readiness Artifact 15082588660。self-check Artifact不是独立的协调器故障矩阵验收报告。
- **资产/覆盖：** KNOW-000040；ASSET-000070共24条场景，全部PROPOSED_NOT_APPROVED / NOT_RUN；CH17统计20篇KNOW、70个实体、63项资源。
- **最终分支与提交：** main，代码修复提交1a9a623e52475059872d8662fb64ee8956b973c2；未创建分支。
- **限制：** 以上均为GitHub Actions中的同进程Mock/合成测试；没有真实协调服务、跨进程/主机、真实网络分区、自动心跳、下游fencing或生产备份验证。治理状态仍BLOCKED_PENDING_ENTERPRISE_APPROVAL。


## CH17-T004 Provider准入队列容量保护与恢复期背压第二十七轮（2026-11-26）

- **分支：** main；未创建新分支。
- **实现：** ProviderFairBulkhead与InMemoryProviderAdmissionCoordinator新增max_waiters；Adapter提供bulkhead_max_waiters参数。默认256仅为实现基线，0允许立即准入但不接受排队。
- **失败关闭：** 队列满抛ProviderAdmissionQueueFullError（区分local_bulkhead/shared_coordinator），不移除已有等待者；共享协调器在等待循环内重新检查可用性，排队过程中失效时返回acquire阶段CoordinatorUnavailable并清理等待者。
- **恢复：** 旧等待请求不会自动重放；恢复后需以原业务任务身份重新检查与提交。令牌桶burst可限制单次突发，但未实现jitter、预热、动态扩容或持久队列。
- **测试：** 新增3项Provider专项unittest：本地队列超额拒绝、共享队列超额拒绝、排队中协调器故障清理与恢复；并补充负数/布尔队列配置校验。全库191项通过；Provider适配器测试文件共64个测试方法定义（按文件中 `test_` 方法统计），完整测试集由CI执行。
- **资源：** 新增KNOW-000041与ASSET-000071，7项场景全部TRUE / PROPOSED_NOT_APPROVED / NOT_RUN。
- **限制：** 所有新增队列与故障测试为同进程合成测试；没有真实协调服务、跨进程/主机、网络分区、恢复风暴、生产容量或Provider验证。生产备份仍关闭，governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL，business_rule_assertions=NOT_EVALUATED。
- **最终提交：** 功能/测试提交 `a691f7eaedafdf96892c9613f3ae304e85f7047c`，分支 `main`；未创建新分支。
- **CI验收时间：** 2026-11-26 11:03（Asia/Shanghai）。[Run 45746342659](https://github.com/rexyll/cnc-knowledge/actions/runs/45746342659) 两个必需Job `Knowledge structure and data quality`、`CH12 numerical resource tests` 均 `completed/success`；全库 `unittest` 191项通过，CH12数控资源测试143项通过。
- **知识质量：** `knowledge_lint.py --strict` 为 `RESULT: PASS (0 errors)`。
- **Provider Mock自检：** `spare_parts_backup_storage_adapter.py --self-check` 返回 `PASS`；Artifact [ch17-backup-storage-adapter-45746342659](https://github.com/rexyll/cnc-knowledge/actions/runs/45746342659/artifacts/15083925258)，ID 15083925258。该自检报告不单独覆盖新增队列回归；本轮新增3项队列/故障测试由全库191项unittest执行。
- **资源状态：** KNOW-000041、ASSET-000071；7项矩阵场景仍为 `TRUE / PROPOSED_NOT_APPROVED / NOT_RUN`。Provider适配器测试文件包含64个测试方法定义；这不是单独的64项测试子任务运行报告。
- **限制：** 仍是同进程Mock/合成测试；没有跨进程/主机真实协调服务、真实网络分区、真实Provider、生产容量/恢复风暴或现场灾备验证。未实现随机jitter、恢复预热/速率斜坡、持久队列、自动心跳与下游fencing。生产备份关闭，`governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL`，`business_rule_assertions=NOT_EVALUATED`。


## CH17-T004 Provider持久化准入协调器与幂等租约第二十八轮（2026-11-26）

- **分支：** main；未创建新分支。
- **实现提交：** `3867b6c2ad3a3ab8832cf518b1c3b27db056bd6f`。
- **持久化后端：** 新增 `scripts/spare_parts_provider_admission_sqlite.py`，采用SQLite WAL、synchronous FULL、BEGIN IMMEDIATE；活动租约、等待队列、请求终态和持久化fencing序列保存于同一本地数据库。
- **接口集成：** ProviderAdmissionCoordinator.acquire增加可选request_id；InMemory与SQLite均实现相同请求身份幂等。Adapter每个准入尝试生成UUID request_id；Coordinator acquire响应未知时异常暴露该ID，可用同一身份和ID重放获取原租约。
- **跨进程竞争：** 新增multiprocessing.spawn测试：两个操作系统子进程在barrier同步后同时申请同一SQLite数据库的read容量1，断言恰好一个得到租约、另一个被拒绝。另测试租约/等待队列跨协调器实例可见、进程重启后的持久状态、租约续期与单调fencing。
- **自动化测试：** 新增11个协调器专项unittest；CI [Run 45748405672](https://github.com/rexyll/cnc-knowledge/actions/runs/45748405672) 两个必需Job均completed/success；全库201个unittest通过，CH12资源测试143项通过，strict knowledge lint PASS（0 errors）。Provider旧Mock self-check PASS，Artifact ID 15084965462。
- **资源：** 新增KNOW-000042和ASSET-000072；10条持久化协调测试规格均TRUE / PROPOSED_NOT_APPROVED / NOT_RUN。
- **限制：** 仅为GitHub Linux runner同主机SQLite多进程合成验证；无真实部署、跨主机/NFS/SMB/HA、数据库损坏/灾备、静态加密、外部QPS限流、自动心跳、下游fencing或生产容量验证。request终态记录目前不自动压缩；SQLite lease expiry依赖Unix wall-clock秒数。
- **状态：** 生产备份关闭；governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL，business_rule_assertions=NOT_EVALUATED。


### 第二十八轮最终CI验收与CLI导入修复补记（2026-11-26）

- **代码实现提交：** 3867b6c2ad3a3ab8832cf518b1c3b27db056bd6f；新增SQLite WAL持久化协调器、request_id幂等租约、持久fencing token和同主机多进程竞争测试。首次代码Run 45748405672两个必需Job均completed/success，全库201项unittest通过，CH12资源143项通过，strict lint 0 errors。
- **文档/续租测试/CI自检同步提交：** 8f7211c213131f4ceb972fcbb3228daa2b6b21f4；SQLite测试文件新增续租持久化回归，并将SQLite CLI自检接入工作流。
- **首轮文档同步CI失败：** Run 45748616308的全库202项unittest均通过，但SQLite CLI阶段因脚本直接执行时sys.path未包含仓库根目录，触发ModuleNotFoundError: No module named 'scripts'；该失败不是SQLite测试断言失败。
- **修复提交：** 8d2a36b6240f20b1968a7e2ef148dcc02e745f88；SQLite CLI入口显式把仓库根目录加入sys.path，保留包模块导入方式。
- **最终CI：** [Run 45748707053](https://github.com/rexyll/cnc-knowledge/actions/runs/45748707053)，两个必需Job Knowledge structure and data quality、CH12 numerical resource tests均completed/success；全库202项unittest通过，CH12资源测试143项通过，knowledge_lint.py --strict为PASS（0 errors）。
- **SQLite独立自检：** CLI返回PASS，Artifact [ch17-provider-admission-sqlite-45748707053](https://github.com/rexyll/cnc-knowledge/actions/runs/45748707053/artifacts/15084821221)，ID 15084821221。Provider Mock self-check Artifact [15084277008](https://github.com/rexyll/cnc-knowledge/actions/runs/45748707053/artifacts/15084277008)。
- **资源状态：** KNOW-000042、ASSET-000072；10条测试矩阵场景仍全部TRUE / PROPOSED_NOT_APPROVED / NOT_RUN。SQLite同主机多进程测试只代表GitHub Linux runner本机SQLite合成测试。
- **严格边界：** 不支持多主机/NFS/SMB/HA；未验证文件系统故障/数据库损坏/灾备还原/静态加密；无自动心跳、QPS令牌桶、下游fencing enforcement或生产容量测量。生产备份关闭，governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL，business_rule_assertions=NOT_EVALUATED。


### 第二十八轮附加诊断指标修复（2026-11-26）

- 在最终验收复核中发现SQLite队列满时rejected_queue计数随准入事务回滚的问题；调整为独立事务持久计数。
- 新增1项unittest：队列满返回ProviderAdmissionQueueFullError，现有活动租约不受影响，等待队列不残留，rejected_queue从0增至1。
- ASSET-000072扩展为11条场景，全部TRUE / PROPOSED_NOT_APPROVED / NOT_RUN；新增测试需由下一次CI验证。


### 第二十八轮最终附加修复与验收（2026-11-26）

- **队列诊断修复：** 提交 331fe25d4dd966e0e2c97b51d12f9db05c935696 修复SQLite队列满时rejected_queue计数随准入事务异常回滚的问题；计数改在事务回滚后由独立事务提交，并新增队列溢出回归测试。
- **首轮回归CI问题：** Run 45749038281在全库203项测试中，仅新增测试因漏导入 ProviderAdmissionQueueFullError 出现NameError；测试尚未进入队列断言。修复提交 b4dcebb5249546954090a50a1c7dff809796345c 补齐测试导入。
- **最终CI：** [Run 45749107843](https://github.com/rexyll/cnc-knowledge/actions/runs/45749107843)，两个必需Job均completed/success；全库203项unittest通过，CH12数控资源143项通过，knowledge_lint.py --strict为PASS（0 errors）。
- **回归证据：** test_queue_overflow_is_fail_fast_and_rejection_counter_persists通过；验证队列满抛出ProviderAdmissionQueueFullError、现有活动租约不变、waiting队列清零、rejected_queue持久增加1。
- **SQLite自检：** Artifact [ch17-provider-admission-sqlite-45749107843](https://github.com/rexyll/cnc-knowledge/actions/runs/45749107843/artifacts/15083979275)，ID 15083979275；Provider Mock adapter self-check Artifact ID 15084203674。
- **资源：** ASSET-000072扩展为11条场景，全部TRUE / PROPOSED_NOT_APPROVED / NOT_RUN；SQLite协调器专项unittest共12项。
- **限制：** SQLite仅支持同主机受支持本地文件系统上的多进程共享；未验证多主机/NFS/SMB/HA、真实存储端fencing、数据库灾备/静态加密、生产QPS或真实Provider。生产备份关闭，治理门禁BLOCKED_PENDING_ENTERPRISE_APPROVAL，业务断言NOT_EVALUATED。
