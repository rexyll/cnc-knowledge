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


## CH17-T004 Provider fencing 契约与 SQLite 安全恢复第二十九轮

- **代码CI完成时间：** 2026-11-26T11:49:23+08:00（由GitHub Actions记录转换为Asia/Shanghai）。
- **分支：** main（未创建其他分支）。
- **代码提交：** 1307ef462b920d9bf745ffb5ff5606e859f3a669。
- **新增代码：** scripts/spare_parts_provider_fencing_contract.py；更新 scripts/spare_parts_provider_admission_sqlite.py。
- **新增测试：** tests/test_spare_parts_provider_fencing_contract.py（8项）；SQLite专项测试新增6项、总计18项。
- **实现内容：** 下游Provider fencing-aware契约，按资源高水位拒绝陈旧token，同token只允许相同幂等键/内容摘要的重放；能力缺失fail-closed。SQLite支持Backup API在线一致性快照、只读完整性/策略/计数器检查，以及要求独立外部fencing高水位和证据引用的“恢复到新库”操作；恢复使旧活动租约失效并清空等待者，不覆盖原库、不自动切换。
- **资源与知识：** 新增KNOW-000043；新增ASSET-000073/000074两份场景矩阵，共16条情景，全部PROPOSED_NOT_APPROVED / NOT_RUN，归档在 resouces/17-operation-maintenance-and-repair/。
- **代码CI：** [Run 45751336613](https://github.com/rexyll/cnc-knowledge/actions/runs/45751336613)，两个必需Job均completed/success；全库217项unittest、CH12资源143项通过，strict lint PASS（0 errors，5 warnings）；SQLite协调器自检PASS，Artifact ID 15084844535。
- **严格边界：** 合成内存Sink不是真实对象存储；BackupStorageAdapter目前没有把lease token贯穿到远端写操作，真实Provider fencing仍未实现或验证。外部高水位必须来自独立、完整且可信的下游状态证据；无法核实时恢复写入必须保持BLOCKED。SQLite快照不等于经过企业批准的灾备系统。
- **状态：** CH17-T004继续IN_PROGRESS；生产备份关闭，governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL，business_rule_assertions=NOT_EVALUATED。


### 第二十九轮文档同步最终验收

- **完成时间：** 2026-11-26T11:57:08+08:00（GitHub Actions Run结束时间，Asia/Shanghai）。
- **文档提交：** 31998e7b087f9270db8d15db430b231e8d817017；随后仅追加本条验收记录，仍在main。
- **最终文档同步CI：** [Run 45752039910](https://github.com/rexyll/cnc-knowledge/actions/runs/45752039910)，head SHA 31998e7b087f9270db8d15db430b231e8d817017；Knowledge structure and data quality 与 CH12 numerical resource tests 两个Job均completed/success。
- **测试结果：** 全库217项unittest通过；CH12数值资源143项通过；strict knowledge lint为PASS（0 errors，5 warnings）；SQLite协调器self-check PASS。
- **Artifacts：** SQLite provider admission Artifact ID 15085349250；Provider backup storage adapter Artifact ID 15085483640；backup governance readiness Artifact ID 15085468691。
- **覆盖登记：** CH17当前23篇KNOW、73个登记实体、67项资源；新增16项测试矩阵场景仍全部PROPOSED_NOT_APPROVED / NOT_RUN。
- **限制未变：** 真实Provider fencing未集成/验证；SQLite restore仅准备新数据库，不自动cutover；生产备份仍关闭，治理门禁BLOCKED_PENDING_ENTERPRISE_APPROVAL。


## CH17-T004 Provider适配器 fencing token 贯穿第三十轮

- **代码实现与测试：** 新增显式 require_provider_fencing=True 严格模式；_bulkhead_slot()向_provider_call()传递当前ProviderAdmissionLease，实际fenced callback获得lease fencing_token及稳定idempotency key。普通payload、multipart begin/part/complete及receipt-last均使用fenced方法；同一备份包共用object_prefix fencing_scope，使旧token不能迟到写入同包的另一object key。
- **合成Provider：** 新增FencedMockObjectStorageProvider，按备份包scope模拟高水位、对象/分块提交、幂等回执及响应丢失；不代表生产/真实云Provider。
- **新增测试：** 适配器专项新增4项unittest，覆盖strict mode fail-closed、payload/multipart/receipt token传递、跨key stale token和multipart complete响应丢失重放。
- **首次CI问题及修复：** 提交 82ca417d380977ef8196fe924a1df89a02ed43f4 的Run 45753100673，在新增旧token测试中因fencing错误类定义重复、实现抛出类型与测试导入类型不一致而NameError；修复提交 b2b5d3f76eff87bb41c12af49959eabacecf311d 统一异常类，Run 45753154675通过，全库221项unittest，CH12 143项。
- **scope收紧及第二次CI问题：** 提交 c9448e64fecf533e42d66387ed79aeaa5efe8687 将高水位 scope 从单object key收紧为整个backup object_prefix，并补充跨key旧写测试；其Run 45753403126因Provider Protocol定义参数替换产生duplicate argument语法错误，导入阶段失败。修复提交 38226d4b48a60dfba7a4b59f2951cf37a570f52c 校正普通PUT与multipart complete协议签名。
- **最终代码CI：** [Run 45753519142](https://github.com/rexyll/cnc-knowledge/actions/runs/45753519142) 两个必需Job均completed/success；全库221项unittest、CH12 143项通过，strict lint PASS（0 errors，5 warnings）；Provider self-check token propagation PASS，Artifact ID 15086063425；SQLite Artifact ID 15086272742。
- **资源与知识：** 新增KNOW-000044与ASSET-000075，12条合成场景全部PROPOSED_NOT_APPROVED / NOT_RUN。CH17覆盖统计更新为24篇KNOW、74个登记实体、68项资源。
- **限制：** 默认兼容模式 require_provider_fencing=False 不提供fencing；严格模式当前仅由FencedMock内存夹具证明。没有真实Provider认证/授权绑定、持久化scope高水位、跨进程远端原子事务或生产环境证据。生产备份关闭，治理门禁BLOCKED_PENDING_ENTERPRISE_APPROVAL，业务断言NOT_EVALUATED。


### 第三十轮文档同步最终验收

- **完成时间：** 2026-11-26T12:18:16.000+08:00（由GitHub Actions Run完成时间转换为Asia/Shanghai）。
- **最终main提交：** 44a60d1136386d0e3c8a0f6248f0c8d8c801a761。
- **最终文档同步CI：** [Run 45754233409](https://github.com/rexyll/cnc-knowledge/actions/runs/45754233409)，两个必需Job Knowledge structure and data quality 与 CH12 numerical resource tests 均completed/success。
- **测试结果：** 全库221项unittest通过；CH12数值资源测试143项通过；knowledge_lint.py --strict为PASS（0 errors，5 warnings）；Provider Mock adapter self-check及SQLite coordinator self-check均PASS。
- **Artifacts：** Provider adapter Artifact ID 15086194048；SQLite coordinator Artifact ID 15086049689；backup governance readiness Artifact ID 15086089278。
- **覆盖登记：** CH17当前24篇KNOW、74个登记实体、68项资源；ASSET-000075的12项场景全部PROPOSED_NOT_APPROVED / NOT_RUN。
- **限制：** strict fencing目前只通过FencedMock单进程内存夹具验证；真实Provider认证/授权绑定、持久scope高水位和跨进程远端原子提交尚未实现/验证。默认兼容模式不启用fencing；生产备份保持关闭。


## CH17-T004 SQLite fenced Provider 服务端原子参考实现第三十一轮

- **实现：** 新增 scripts/spare_parts_provider_sqlite_fenced.py。Provider独立SQLite库使用WAL、synchronous=FULL和BEGIN IMMEDIATE；主体凭据PBKDF2-HMAC-SHA256 verifier，tenant/action/prefix ACL每次事务复查；scope high-water、fenced_operations幂等回执、对象或multipart变更和成功审计同事务提交；拒绝操作尝试独立DENY审计。
- **恢复能力：** 新增online backup、integrity_check/foreign_key_check、SHA-256快照校验和restore_to_new_database。恢复必须提供独立external_fencing_floor与reconciliation reference；会清理未完成multipart、提升已知scope和全局minimum token floor，只创建新DB，不覆盖源库、不自动cutover。
- **测试：** tests/test_spare_parts_provider_sqlite_fenced.py新增20项专项测试，覆盖credential、ACL、tenant isolation、scope containment、cross-key stale write、idempotency、rollback、lost response replay、multipart、multiprocessing race、online backup/restore和strict adapter完整发布。
- **首次测试CI问题及修复：** Run 45754970839 的240项测试中，新增测试遗漏FencingNotSupportedError导入且tenant isolation fixture将object key放在scope之外；修复提交7c3d4305。Run 45755055185在单元测试通过后暴露CLI直接运行时scripts模块导入路径错误；修复提交7ee9166a添加仓库根目录sys.path。最终增加diagnostics ACL探测修复和恢复清理active multipart测试后，以提交59b9945a重新完整验收。
- **最终代码CI：** [Run 45755448153](https://github.com/rexyll/cnc-knowledge/actions/runs/45755448153)两个必需Job completed/success；全库241项unittest、CH12 143项通过；strict knowledge lint PASS（0 errors，5 warnings）；Provider CLI self-check PASS。Artifacts：Provider fenced 15087184041；SQLite coordinator 15087452634；Provider adapter 15087507413。
- **资源：** 新增KNOW-000045和ASSET-000076（22条场景），均为PROPOSED_NOT_APPROVED / NOT_RUN。CH17覆盖更新为25篇KNOW、75个登记实体、69项资源。
- **边界：** 当前为同主机本地SQLite参考Provider，不是云/网络或多主机服务；没有数据静态加密和凭据生命周期管理。Provider尚未验证token来自trusted coordinator的scope-bound签名，授权主体可构造高token导致拒绝服务；正式生产前必须补HMAC/签名attestation。生产备份仍关闭，governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL，business_rule_assertions=NOT_EVALUATED。


### 第三十一轮文档同步最终验收

- **完成时间：** 2026-11-26T12:33:20.000+08:00（GitHub Actions Run 完成时间转换为 Asia/Shanghai）。
- **最终 main 提交：** b3dad1a80217cf9c848777114bbd4c6f95e2f066。
- **文档同步 CI：** [Run 45755807755](https://github.com/rexyll/cnc-knowledge/actions/runs/45755807755)，Knowledge structure and data quality 与 CH12 numerical resource tests 两个必需 Job 均 completed/success。
- **测试结果：** 全库241项unittest通过；CH12数值资源143项通过；knowledge_lint.py --strict为PASS（0 errors，5 warnings）；Provider adapter、SQLite admission coordinator、SQLite fenced Provider三个自检均PASS。
- **Artifacts：** SQLite fenced Provider Artifact ID 15087855945；SQLite admission coordinator Artifact ID 15087626678；Provider adapter Artifact ID 15087721263；backup governance readiness Artifact ID 15087875780。
- **覆盖登记：** CH17当前25篇KNOW、75个登记实体、69项资源；ASSET-000076的22条正式参考场景全部PROPOSED_NOT_APPROVED / NOT_RUN。
- **限制：** SQLite fenced Provider仅同主机本地文件/多进程参考实现；没有真实云/多主机Provider。Provider尚未验证Coordinator token来源的scope-bound HMAC/signature attestation，持有效本地主体凭据的调用方仍可构造高token；生产化前必须补该证明。生产备份仍关闭，治理门禁BLOCKED_PENDING_ENTERPRISE_APPROVAL。


## CH17-T004 Coordinator scope-bound fencing attestation与Provider key rotation第三十二轮

- **代码：** 新增scripts/spare_parts_fencing_attestation.py；SQLite Coordinator支持配置issuer/key ID/HMAC-SHA256 secret，默认15秒proof TTL（最大60秒）。签发前在BEGIN IMMEDIATE事务内复查lease ACTIVE、owner/tenant/domain/token/lease id和未过期；claims固定15项并绑定scope/resource/operation/idempotency。
- **Adapter：** require_provider_fencing路径为payload PUT、multipart begin/part/complete和receipt-last分别签发proof，并将proof与token一起传入Provider。每个新mutation获取独立lease proof，重试保持逻辑幂等键。
- **Provider：** SQLiteFencedObjectStorageProvider.requires_fencing_attestation=True，拒绝无proof调用；验证HMAC签名、版本/kid、tenant/scope/resource/token/domain/operation/idempotency/lease identity及过期时间；事务内重新查trusted_fencing_keys。增加本地admin_register_trusted_attestation_key和admin_set_trusted_attestation_key_status，状态ACTIVE/RETIRING/REVOKED，REVOKED终态，secret只作运行时注入。
- **测试：** Coordinator新增活动/释放lease签发和scope越界测试；Provider新增proof缺失/篡改/租户scope资源幂等绑定/过期proof/密钥轮换测试；Strict Adapter端到端用例验证payload/multipart/receipt proof贯穿。新增KNOW-000046和ASSET-000077（20条场景，均PROPOSED_NOT_APPROVED / NOT_RUN）。
- **中间失败与修复：** Run 45757441125/45757533020/45757637752/45757786191在逐步接入时暴露fixture缺少key ring、coordinator attestations_issued metadata未初始化、fault_hook漏传及self-check重新打开Provider时漏传key ring等问题，已在后续提交修复；最终代码提交f4c26e61由Run 45758028329完整验收。
- **最终代码CI：** [Run 45758028329](https://github.com/rexyll/cnc-knowledge/actions/runs/45758028329)，两个必需Job均success；全库248项unittest、CH12 143项通过；strict lint PASS（0 errors，5 warnings）；Provider self-check PASS。Artifacts：Provider fenced 15087973420；Coordinator 15087604559；Adapter 15087868629。
- **资源：** 新增KNOW-000046、ASSET-000077（20条proof/rotation形式化参考场景），更新KNOW-000045，CH17统计更新为26篇KNOW、76个登记实体、70项资源。
- **剩余限制：** HMAC密钥同时注入Coordinator及本地Provider进程；不能把Python Provider暴露给不可信租户/插件。proof签发后lease release不会即时撤销，默认proof最多仍可活15秒。admin key registry API依赖本地DB文件owner权限。生产远端Provider需非对称签名（Coordinator/KMS私钥、Provider公钥）、在线撤销、时钟同步和真实网络测试；SQLite仍仅同主机本地文件。生产备份仍关闭，governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL。


### 第三十二轮签名证明与密钥轮换最终代码验收

- **最终代码提交：** c3763105bdcfe5028311096a6ad83a58f45c2a8e。
- **最终 CI：** [Run 45758771772](https://github.com/rexyll/cnc-knowledge/actions/runs/45758771772)，两个必需Job均completed/success；全库248项unittest通过，CH12数值资源143项通过，strict lint PASS（0 errors，5 warnings）。
- **测试缺陷修复记录：** 文档首轮CI Run 45758511537的单元测试唯一失败来自tampered signature测试只替换Base64URL签名最后一个字符；该字符有未使用的填充位，某些替换会解码为相同签名字节。修复提交c3763105改为修改签名编码首字符的有效数据位，再次验证验签拒绝路径。修复后Run 45758771772全部248项测试通过。
- **自检：** Provider fenced CLI self-check PASS；scope stale writer拒绝与SQLite对象/fence/receipt原子事务检查PASS。
- **Artifacts：** Provider fenced 15089140399；SQLite admission coordinator 15089115409；Provider adapter 15089015697。
- **知识资源：** KNOW-000046、ASSET-000077（20条formal scenarios，PROPOSED_NOT_APPROVED / NOT_RUN）已写入；CH17统计26篇KNOW、76个登记实体、70项资源。
- **安全限制：** 当前HMAC signer secret需在本机Coordinator与Provider进程分别注入；Provider进程持有对称verify secret；lease释放后已签proof仍可用到expires_at，默认最多15秒。生产远端Provider应使用Coordinator/KMS私钥、Provider公钥的非对称验签，增加在线撤销、同步时钟、TLS/KMS/HSM及真实多主机网络测试。生产备份仍关闭。


## CH17-T004 Ed25519 v2与在线Coordinator lease状态复核第三十三轮

- **实现：** fencing attestation协议新增Ed25519 v2，签名格式v2.ed25519.kid.payload.signature，claims固定16项；HMAC v1保持迁移兼容。新增FencingAttestationSigner/CallbackEd25519Signer和本地Ed25519PrivateKeySigner；Coordinator接受attestation_signer回调，私钥不写入Coordinator SQLite。
- **Provider：** 新增trusted_ed25519_keys表，保存公钥SHA256指纹而非私钥；Provider只注入公钥。支持Ed25519公钥指纹校验和ACTIVE/RETIRING/REVOKED key registry接口。
- **在线撤销：** Coordinator增加is_attestation_active(claims)；Provider配置require_online_attestation_status=True时在Provider写事务中复核lease ACTIVE，Coordinator不可用则fail-closed。测试覆盖lease RELEASED拒绝和Coordinator status故障时无对象提交。
- **限制：** CallbackEd25519Signer只提供KMS/HSM适配接口，没有实际云KMS SDK、凭据或网络调用。在线status-check和Provider commit属于两个独立SQLite事务，检查后到commit之间存在TOCTOU，不是线性一致即时撤销；SQLite仍仅同主机参考。
- **中间CI失败及修复：**
  - Run 45760498433：先增加cryptography导入但workflow未安装依赖，失败为ModuleNotFoundError；新增requirements-ch17-security.txt并在Knowledge Quality workflow安装。
  - Run 45760532361：requirements文件首版把换行误写成字面量\\n，pip拒绝；修正为真正换行。
  - Run 45760704241：Coordinator将issuer_id误判为与Ed25519 signer冲突；修复为允许issuer并从signer读取key ID，只拒绝与HMAC secret混用。
- **最终代码CI：** [Run 45760844653](https://github.com/rexyll/cnc-knowledge/actions/runs/45760844653)两个必需Job completed/success；全库252 tests、CH12 143 tests通过；strict lint 0 errors/5 warnings；Provider CLI self-check PASS。Artifacts：Provider 15089847421，Admission 15089209106，Adapter 15089074481。
- **资产：** 新增KNOW-000047、ASSET-000078（22条参考场景，PROPOSED_NOT_APPROVED / NOT_RUN）。CH17统计从26/76/70更新至27篇KNOW、77个登记实体、71项资源。
- **生产限制：** 未配置/连接AWS/Azure/GCP KMS或HSM；没有真实Provider/远程Coordinator/多主机网络；在线状态复核与对象提交之间尚未原子化；生产备份仍关闭，治理状态BLOCKED_PENDING_ENTERPRISE_APPROVAL。


### 第三十三轮文档同步最终验收

- 最终文档提交前代码验证：[CI Run 45760844653](https://github.com/rexyll/cnc-knowledge/actions/runs/45760844653)，全库252项、CH12 143项、strict lint 0 errors/5 warnings均通过。
- KNOW/README/TaskPlan/TaskHistory/ASSET-000078及覆盖统计文档同步：[CI Run 45761309007](https://github.com/rexyll/cnc-knowledge/actions/runs/45761309007)两个必需Job均completed/success；全库252 tests、CH12 143 tests通过；strict lint 0 errors/5 warnings；Provider、Coordinator和治理自检PASS。
- 主要Artifacts：Provider fenced 15089229555；Coordinator 15089968457；Adapter 15089224709；Backup governance readiness 15089743985。
- 最终资源统计：CH17 27篇KNOW、77个登记实体、71项资源；ASSET-000078的22条规格均PROPOSED_NOT_APPROVED / NOT_RUN。
- 安全限制持续有效：CallbackEd25519Signer没有连接实际云KMS/HSM；在线lease检查与Provider提交分属两个SQLite事务，存在TOCTOU窗口；未完成多主机远程Coordinator/Provider验证。生产备份关闭。

## CH17-T004 SQLite同库原子lease撤销与Provider写入顺序第三十四轮（2026-11-26）

- **缺口：** 第三十三轮的在线lease状态查询和Provider对象commit在两个SQLite数据库/事务中完成，成功查询到commit之间仍有TOCTOU窗口。
- **Coordinator实现：** scripts/spare_parts_provider_admission_sqlite.py 新增 is_attestation_active_in_transaction(connection, claims)，复用Provider持有的sqlite3.Connection；验证活动事务和PRAGMA database_list主库路径，避免另开连接或嵌套事务。
- **Provider实现：** scripts/spare_parts_provider_sqlite_fenced.py 新增 require_atomic_online_attestation_status 严格选项；必须启用在线状态检查、checker具备事务内接口且解析后的Provider/Coordinator数据库路径相同；不满足则启动失败。旧分库模式保持兼容并保留TOCTOU警告。
- **并发顺序：** Provider在BEGIN IMMEDIATE后同连接读取lease并提交对象/multipart、fencing high-water、幂等receipt和audit。Coordinator release使用同一个SQLite文件的写事务，因而在锁层面与Provider mutation串行化。
- **测试：** tests/test_spare_parts_provider_sqlite_fenced.py 新增路径/启用依赖拒绝测试和多线程竞态测试：Provider在事务内状态检查通过后暂停，release线程开始并被写锁阻塞，Provider提交后release完成；使用已释放proof再次提交应被拒绝。测试仅为本地合成SQLite路径。
- **外部来源：** 新增SRC-000391 SQLite Transaction与SRC-000392 SQLite WAL官方文档。新增 KNOW-000048；新增ASSET-000079（12条参考场景，全部PROPOSED_NOT_APPROVED / NOT_RUN），并补齐前轮遗留缺失的ASSET-000078结构化实体记录。
- **提交：** Coordinator 1504a0d8285ddce17bbef792fb58fdcf55e38a17；Provider 3bed9959162858ae5b0d88c18c28408c86b5fa8b；测试 1efa13adab92a87a6b4353b848637ec730d0b95f。
- **当前验收状态：** 最终CI待本轮最后一次main提交运行完成后补录；未将未完成CI表述为PASS。
- **生产边界：** 仅同主机、同一SQLite文件、本地文件系统；WAL不适用于网络文件系统，不支持多主机/远程Coordinator/云Provider。未接入真实KMS/HSM/对象存储，生产备份仍关闭；治理门禁 BLOCKED_PENDING_ENTERPRISE_APPROVAL。

### 第三十四轮最终代码和文档同步CI验收

- **代码/资源CI：** [Run 45762883991](https://github.com/rexyll/cnc-knowledge/actions/runs/45762883991)，两个必需Job均completed/success；全库254项unittest通过，CH12数值资源143项通过；strict knowledge lint PASS（0 errors，5 warnings）；Provider admission、fenced Provider、Adapter及治理readiness自检所在Job成功。
- **文档同步CI：** [Run 45762994591](https://github.com/rexyll/cnc-knowledge/actions/runs/45762994591)，两个必需Job均completed/success；全库254项unittest、CH12 143项通过；strict lint 0 errors/5 warnings，知识结构与数据质量Job PASS（0 errors）。
- **Artifacts：** Provider fenced 15091340011；Admission Coordinator 15090661225；BackupStorageAdapter 15090885721；Backup governance readiness 15089609979；CH12 S-curve synthetic 15090308493。
- **本轮结论：** 实现和仓库质量门禁通过；ASSET-000079的12条形式化验收场景仍全部PROPOSED_NOT_APPROVED / NOT_RUN。CI测试只覆盖仓库合成代码路径，不等于企业批准、真实KMS/HSM、真实对象存储/Provider、多主机或灾备测试。
- **状态：** CH17-T004仍IN_PROGRESS；生产备份维持关闭；governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL。

## CH17-T004 远程Coordinator与对象存储Provider分布式fencing第三十五轮（2026-11-26）

- **目标：** 定义从本机SQLite事务走向远程Coordinator和对象存储Provider的fencing提交协议，避免“先查Coordinator lease、再无条件PUT”的TOCTOU。
- **协议：** 每个tenant+scope使用一个权威control object。control record包含单调high-water token、lease ACTIVE/REVOKED、最新operation sequence、有限receipt及current manifest pointer。大型payload/manifest先写到token及operation专属immutable staging key；staging上传不代表备份已发布。
- **线性化点：** lease activation、manifest publish、lease revoke均以同一个control object的ETag/generation CAS为线性化点。Coordinator只有在activation CAS确认后才能把lease标为ACTIVE；只有revoke CAS确认后才能向调用者报告release完成。Gateway是control object唯一写者，读者只认current manifest pointer。
- **幂等和未知结果：** proof增加operation_sequence、manifest key和manifest SHA-256绑定；近期receipt按sequence/idempotency/operation hash匹配；超出receipt保留窗口的旧请求返回OUTCOME_UNKNOWN，不允许盲目重放。CAS响应丢失后通过强一致重读恢复。
- **实现：** 新增scripts/spare_parts_provider_distributed_fencing.py；实现ConditionalObjectControlStore接口、InMemoryConditionalObjectControlStore合成CAS模型、Ed25519 proof校验、activate/revoke/publish状态机、monotonic token/sequence、receipt窗口和失败关闭。新增tests/test_spare_parts_provider_distributed_fencing.py，覆盖14项场景，包括并发新epoch激活击败旧writer。
- **来源与知识：** 新增SRC-000393～SRC-000396（AWS S3、Google Cloud Storage、Azure Blob官方条件写/并发控制资料），KNOW-000049，ASSET-000080（20条形式化参考场景，全部PROPOSED_NOT_APPROVED / NOT_RUN）。
- **CI：** Commit 430816f0b466a6040cd0a48e4bf1730c7f4afb4c；Run 45767324560两个必需Job success；全库268项unittest通过，CH12 143项通过，strict lint 0 errors/5 warnings，知识结构与数据质量0 errors。
- **没有完成的集成：** 本轮没有AWS/GCS/Azure SDK、远程Coordinator API、KMS/HSM、IAM策略或多主机服务。现有Coordinator API尚未提供fencing:activate/revoke/publish proof签发和持久operation_sequence。单进程内存CAS模型不构成真实对象存储或分布式线性一致性验收。
- **状态：** CH17-T004仍IN_PROGRESS；生产备份仍关闭；governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL；business_rule_assertions=NOT_EVALUATED。

### 第三十五轮最终文档同步CI验收

- **最终文档提交：** 52bab72e401c39254b5c9aff2339e51ca5d36560。
- **最终文档同步CI：** [Run 45767658789](https://github.com/rexyll/cnc-knowledge/actions/runs/45767658789)两个必需Job均completed/success；全库268项unittest通过，CH12数值资源143项通过；strict knowledge lint 0 errors / 5 warnings；知识结构与数据质量0 errors。
- **Artifacts：** CH12 S-curve synthetic 15091879973；BackupStorageAdapter self-check 15093210029；Provider admission 15092029877；SQLite fenced Provider 15092204228；Backup governance readiness 15092980848。
- **验收边界：** ASSET-000080的20条场景全部PROPOSED_NOT_APPROVED / NOT_RUN。本轮没有真实对象存储SDK、远程Coordinator/KMS/HSM/IAM或多主机测试；单进程CAS模型不是生产验收。
- **状态：** CH17-T004继续IN_PROGRESS；production_backup_enabled=false；governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL；business_rule_assertions=NOT_EVALUATED。


## CH17-T004 Coordinator持久权威、Leader切换与故障恢复第三十六轮（2026-11-26）

- **新增模块：** `scripts/spare_parts_provider_coordinator_authority.py`，在同一SQLite WAL数据库中持久化全局Leader lease/epoch、tenant-qualified scope token、publish operation sequence和activation/revoke/publish operation ledger。
- **状态与确认：** activation以PENDING_ACTIVATION起步，只有Provider control object强一致读回确认ACTIVE/token/lease/generation后才转ACTIVE；revoke以REVOKING起步，只有Provider读回REVOKED后完成；publish receipt匹配token、sequence、idempotency key、manifest key和SHA-256后转COMMITTED。
- **隔离与恢复：** scope强制`tenants/<tenant_id>/...`；proof签发前重新校验当前Leader epoch和持久pending operation；旧Leader不能继续写入/签新proof。新Leader接管后可检查pending operation，并基于Provider状态重签相同原操作。数据库恢复要求独立外部token/sequence/Leader epoch floors；不自动重放或cutover。
- **测试：** 新增15项Coordinator authority unittest（基础14项加1项租户scope隔离）；包含本地多实例并发sequence、Leader过期接管、旧Leader签名/确认拒绝、Provider activation提交后Coordinator崩溃恢复。
- **首轮问题修复：** Commit `cc259d2`首轮CI暴露测试manifest key未使用实际整数token目录；改为Provider要求的`<scope>/staging/<token>/...`路径后，Run 45768939343全库282项和CH12 143项通过。随后增加当前Leader proof签发校验及manifest receipt完整匹配；Run 45769230014全库282项和CH12 143项通过。进一步增加tenant-qualified scope拒绝测试；最终代码Run 45769331991已通过。
- **参考文件：** 新增KNOW-000050和ASSET-000081（16条场景）；复用SRC-000391/392。测试及矩阵均为本地合成范围。
- **生产边界：** 仅同机SQLite WAL；无多主机共识、远程Coordinator/KMS/HSM、真实云对象存储/IAM Gateway、真实灾备或企业生产验收。生产备份仍关闭，治理状态BLOCKED_PENDING_ENTERPRISE_APPROVAL，业务断言NOT_EVALUATED。


### 第三十六轮最终代码与文档同步CI验收

- **最终代码提交：** `abb73ebd6e3268d15f149333d904369c5cc1a42d`；[Run 45769331991](https://github.com/rexyll/cnc-knowledge/actions/runs/45769331991)，两个必需Job均completed/success；全库283项unittest、CH12数值资源143项通过；strict knowledge lint 0 errors / 5 warnings；知识结构与数据质量0 errors。
- **最终文档提交：** `262c7fe71f0a436ec1b95686cbb1c6c7448b2575`；[Run 45769584662](https://github.com/rexyll/cnc-knowledge/actions/runs/45769584662)，两个必需Job均completed/success；全库283项unittest、CH12 143项通过；strict lint 0 errors / 5 warnings；知识结构与数据质量0 errors。
- **Artifacts：** SQLite admission Coordinator self-check 15093960081；Provider fenced self-check 15093038669；BackupStorageAdapter self-check 15093925222；治理readiness 15093158182；CH12数值资源与SCURVE-01等模拟结果以Run 45769584662 artifacts为准。上述Provider产物并不是新Coordinator authority的云服务或多主机验收证据。
- **登记：** 新增KNOW-000050、ASSET-000081；矩阵16条均PROPOSED_NOT_APPROVED / NOT_RUN。CH17统计为30篇KNOW、83个登记实体、74项资源、15条去重来源。
- **限制：** 同机SQLite WAL参考；没有多主机共识服务、远程API、真实KMS/HSM、云对象存储/IAM或企业灾备。生产备份仍关闭，治理门禁BLOCKED_PENDING_ENTERPRISE_APPROVAL，business_rule_assertions=NOT_EVALUATED。


## CH17-T004 Coordinator后端契约与etcd v3适配设计第三十七轮（2026-11-26）

- **后端抽象：** 新增`DurableCoordinatorAuthorityBackend`应用服务端口与`CoordinatorAuthorityStore`原子KV/Txn/Lease存储端口。前者覆盖Leader、activation/revoke、sequence、publish、proof授权与恢复；后者定义linearizable_get、条件Txn成功/失败分支和Lease grant/keepalive/revoke。
- **参考适配器：** 新增`scripts/spare_parts_provider_authority_store.py`，包括`SQLiteCoordinatorAuthorityStore`本地WAL适配器、`EtcdV3CoordinatorAuthorityStore`和注入式`EtcdV3Client`协议，以及仅用于单进程测试的`InMemoryEtcdV3Client`。
- **一致性约束：** etcd权威Range调用serializable=false；token、sequence和Leader ownership通过同一Txn Compare/Success/Failure原子更新；每次敏感写必须比较LeaderKey revision/epoch；lease alone不充分，外部Provider仍需scope token/CAS；Watch不能作为授权读取；Txn超时按OUTCOME_UNKNOWN处理。
- **新增测试：** 新增跨适配器存储契约测试，覆盖线性一致读参数、条件CAS、事务单revision、多键、失败分支、lease附着与过期/撤销、旧Leader revision隔离、提交响应丢失和服务端口结构符合性。
- **外部资料：** SRC-000397 API guarantees；SRC-000398 KV Txn/Lease；SRC-000399 Leader election/LeaderKey；SRC-000400 lease/lock不充分性与revision fencing；SRC-000401 quorum/leader failure语义。
- **新增知识：** KNOW-000051；ASSET-000082定义20条分布式一致性场景，全部PROPOSED_NOT_APPROVED / NOT_RUN。
- **限制：** 实际etcd集群、gRPC/JSON Gateway驱动、mTLS/RBAC、quorum/网络分区/多主机和Provider端到端未接入。SQLite领域服务目前仍SQL专用，仅结构化满足应用服务Protocol；低层etcd适配器尚未成为该业务状态机的正式运行后端。


### 第三十七轮最终代码与文档同步CI验收

- **最终代码提交：** `e274067e7e601c026252ddf3dacb87db5971bd63`；[Run 45770717942](https://github.com/rexyll/cnc-knowledge/actions/runs/45770717942)两个必需Job均completed/success，全库300项unittest、CH12 143项测试通过；strict lint 0 errors/5 warnings；结构质量0 errors。
- **最终文档提交：** `3a83763239ec2ecda8607eca0977139c41dd6df9`；[Run 45770955018](https://github.com/rexyll/cnc-knowledge/actions/runs/45770955018)两个必需Job均completed/success，全库300项unittest、CH12 143项测试通过；strict lint 0 errors/5 warnings；结构质量0 errors。
- **资源统计：** CH17更新为31篇KNOW、85个登记实体、76项资源、20条去重来源；新增KNOW-000051、ASSET-000082及SRC-000397～SRC-000401。ASSET-000082的20条场景仍全部PROPOSED_NOT_APPROVED / NOT_RUN。
- **验收边界：** 新增SQLite参考存储与InMemoryEtcdV3Client API替身；EtcdV3Client是注入式客户端协议，无真实etcd server/gRPC/JSON Gateway/mTLS/RBAC/quorum/多主机集群。SQLite领域服务仍直接使用SQL，尚未迁移到通用Store port。没有生产Provider、灾备或企业验收。
- **生产状态：** production_backup_enabled=false；governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL；business_rule_assertions=NOT_EVALUATED。


## CH17-T004 Coordinator事务内有序读取第三十八轮（2026-11-26）

- **目标：** 补齐KNOW-000051的低层Coordinator存储端口，使CAS事务能在已选中的Success/Failure分支内按顺序执行精确键读取与写入。
- **代码：** `scripts/spare_parts_provider_authority_store.py` 新增 `AuthorityStoreGet` / `AuthorityStoreTxnOperation`，`AuthorityStoreTxnResult` 新增 `reads`；SQLite适配器在一个 `BEGIN IMMEDIATE` 事务中处理Get/Put/Delete，etcd适配器把Get编码为事务分支内的 `request_range`，不拆成事务外Range。
- **一致性语义：** Get严格遵循事务操作顺序，写前Get读旧值、写后Get读本次Txn的暂存新值；reads只收集Get并按相对顺序返回，缺失键为None；Compare决定Success/Failure分支后只执行一个分支。响应列表缺项或Get响应类型不符时失败关闭。
- **测试：** `tests/test_spare_parts_provider_authority_store.py` 新增2个跨适配器契约测试方法（SQLite、InMemoryEtcdV3Client各运行一次，共4次适配器测试执行），覆盖写前/写后快照和Compare失败后的Failure读取。
- **知识与资源：** 新增KNOW-000052；新增ASSET-000083矩阵16条场景，全部PROPOSED_NOT_APPROVED / NOT_RUN；复用SRC-000397/398（etcd）与SRC-000391/392（SQLite）。
- **代码CI：** Commit `fec104016db56bcd1d841b134d2000f3d9838d4a`；[Run 45772420144](https://github.com/rexyll/cnc-knowledge/actions/runs/45772420144)两个必需Job均completed/success；全库304项unittest、CH12数值资源143项通过；strict lint 0 errors/5 warnings；知识结构与数据质量0 errors。
- **重要限制：** 这是存储原语扩展，并未把 `SQLiteDurableCoordinatorAuthority` 领域状态机迁移到 `CoordinatorAuthorityStore`。现有Admission lease仍由同一SQLite数据库的 `admission_requests` 表校验；未来etcd迁移必须把Admission lease生产/续租/释放也迁入同一Txn权威源，保证lease比较和authority变更在单个Txn内原子完成。不得采用独立Range后接独立Txn的TOCTOU流程。真实etcd、gRPC/JSON Gateway、mTLS/RBAC、quorum、多主机和Provider故障演练均未接入或执行。
- **生产状态：** `production_backup_enabled=false`；`governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL`；`business_rule_assertions=NOT_EVALUATED`。


### 第三十八轮文档同步CI验收

- **文档提交：** `a1548dad6ad1c47d4645600a162a866076de6993`；[Run 45772844275](https://github.com/rexyll/cnc-knowledge/actions/runs/45772844275)两个必需Job均completed/success。
- **质量结果：** 全库304项unittest、CH12 143项数值资源测试通过；strict knowledge lint 0 errors/5 warnings；知识结构与数据质量0 errors。
- **登记：** KNOW-000052和ASSET-000083已纳入文档与资源索引；矩阵16条均PROPOSED_NOT_APPROVED/NOT_RUN。
- **限制：** SQLite领域状态机仍SQL专用；Admission lease没有迁移到通用Txn存储；未连接真实etcd集群、多主机或生产Provider。


## CH17-T004 Admission Lease Authority统一事务存储第三十九轮（2026-11-26）

- **新增实现：** `scripts/spare_parts_provider_admission_authority_store.py`，新增 `StoreBackedAdmissionLeaseAuthority`，建立后端无关的Admission lease create/renew/release、全局monotonic fencing token与request_id幂等管理。
- **键模型：** 活动lease记录附着底层Store TTL Lease；永久request_id索引保留ACTIVE/RELEASED/EXPIRED记录防止重复使用；全局token counter由mod_revision/version CAS递增。获取Lease在一个Txn中提交counter、active lease和request索引；续租一个Txn将active key迁移到新backend TTL并更新request索引；release一个Txn删除active key并写RELEASED tombstone。
- **原子保护：** 新增 `active_lease_compares()` / `transact_with_active_lease()`，返回Lease记录和request索引的精确值Compare，要求被保护的authority mutation把这些比较与Leader/scope/operation比较放进同一个Store Txn。独立validate后再写入仍不构成原子保护。
- **测试：** 新增5个测试方法，SQLite与InMemoryEtcdV3Client两适配器各执行一次，共10次新增测试执行；覆盖token单调、request_id幂等/冲突/终态、lease TTL、renew迁移、release、同Txn guard及提交后响应丢失恢复。
- **代码CI：** Commit `b9b7f6af6f34fc012fee95c96e77cca10c5e6442`；[Run 45775642132](https://github.com/rexyll/cnc-knowledge/actions/runs/45775642132)两个必需Job均completed/success；全库314项unittest、CH12 143项数值资源测试通过；strict lint 0 errors/5 warnings；知识结构与数据质量0 errors。
- **知识与资源：** 新增KNOW-000053与ASSET-000084；矩阵20条全部PROPOSED_NOT_APPROVED / NOT_RUN；复用SRC-000391/392/397/398。
- **关键限制：** 本轮没有替换 `SQLiteProviderAdmissionCoordinator` 的等待队列、公平调度、global/tenant quota、policy hash和原SQL lease表，也没有把 `SQLiteDurableCoordinatorAuthority` 迁移至store port。不能分库双写或把该组件作为完整Admission scheduler投产。真实etcd、gRPC/JSON Gateway、mTLS/RBAC、quorum、多主机、生产Provider和企业场景均未接入/验收。
- **生产状态：** `production_backup_enabled=false`；`governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL`；`business_rule_assertions=NOT_EVALUATED`。


### 第三十九轮文档同步CI验收

- **文档提交：** `b79aede8a06cc55ac60681cbfc9acf03b1f44a55`；[Run 45776156101](https://github.com/rexyll/cnc-knowledge/actions/runs/45776156101)两个必需Job均completed/success。
- **质量结果：** 全库314项unittest、CH12 143项数值资源测试通过；strict lint 0 errors/5 warnings；知识结构与数据质量0 errors。
- **登记：** KNOW-000053和ASSET-000084已纳入文档与资源索引，ASSET-000084矩阵20条均PROPOSED_NOT_APPROVED/NOT_RUN。
- **限制：** Store-backed lease组件不是完整scheduler；旧SQLite队列/配额及Coordinator状态机尚未迁移。真实etcd和多主机验证未完成。


### 第三十九轮最终元数据CI验收

- **最终元数据提交：** `7209c094079830eb0789fbbe041757ee764e611c`；[Run 45776292616](https://github.com/rexyll/cnc-knowledge/actions/runs/45776292616)两个必需Job均completed/success。
- **质量结果：** 全库314项unittest、CH12 143项测试通过；strict knowledge lint 0 errors/5 warnings；知识结构和数据质量0 errors。
- **状态：** KNOW-000053/ASSET-000084及资源索引、覆盖统计同步；ASSET-000084的20条场景仍PROPOSED_NOT_APPROVED / NOT_RUN。旧Admission scheduler和Coordinator领域服务尚未迁移。


## CH17-T004 Unified Admission Scheduler与配额状态统一事务第四十轮（2026-11-26）

- **目标：** 将旧Admission scheduler中分散在同一SQLite事务的global/tenant quota、waiter、公平调度、fencing token、Lease和request_id幂等，建立为后端无关的单权威Txn参考模型。
- **实现：** 新增 `scripts/spare_parts_provider_unified_admission_store.py` 的 `StoreBackedProviderAdmissionCoordinator`。单一aggregate存储policy hash、global/tenant limits、所有domain活动lease、全局waiter集合、fencing/waiter sequence和指标。活动Lease key附着原生TTL Lease，request索引持久保留ACTIVE/RELEASED/EXPIRED。全局与tenant容量从同一个aggregate活动集合计算，Acquire将aggregate、fencing token、TTL活动Lease和request索引在同一Txn提交。
- **调度：** waiter使用priority + waiting age / aging interval评分，sequence做稳定平局；global max_waiters跨所有domain。timeout和check_task异常会清理waiter；过期lease先通过TTL key状态与精确Compare识别，再在aggregate CAS事务中清除容量占用并记录EXPIRED。
- **Lease与Authority：** renew同步改写aggregate、active key和request index，并切换native TTL Lease；release同Txn从active map移除、删除active key及写RELEASED tombstone。新增active lease exact-value guard，可与Leader/scope/operation比较一起放入被保护的authority Txn。
- **隔离：** 新版本独立使用 `/cnc/admission/unified/v1/`，不与第三十九轮 `/cnc/admission/v1/` standalone lease prototype重叠；不得对同一业务范围并行写入。
- **测试：** 新增6个契约测试方法，SQLite和InMemoryEtcdV3Client各执行一次，共12次适配器测试，覆盖跨实例global/tenant配额、no-oversubscription、priority/aging公平队列、全局waiter上限、过期reclaim、renew/release、authority guard及request幂等竞争。
- **修正记录：** 首轮CI暴露两项测试夹具在同一store上使用不同policy hash；已改为每个策略变体使用独立SQLite/etcd测试store。另将scheduler key namespace与第三十九轮Lease Authority隔离。最终代码提交 `34023050272f41c725396d1737ea4b394c22cf3d`；[Run 45778008494](https://github.com/rexyll/cnc-knowledge/actions/runs/45778008494)两个必需Job均completed/success，全库328项unittest、CH12 143项测试通过，strict knowledge lint 0 errors，知识结构和数据质量0 errors。
- **知识/资源：** 新增KNOW-000054与ASSET-000085；矩阵24条均PROPOSED_NOT_APPROVED / NOT_RUN；复用SRC-000391/392/397/398。
- **重要限制：** 单aggregate状态键导致各domain写入串行及活动集Compare扩张，不是高吞吐生产scheduler。旧 `SQLiteProviderAdmissionCoordinator` 和 `SQLiteDurableCoordinatorAuthority` 仍未迁移，真实etcd及mTLS/RBAC/quorum/multihost/Provider端到端未接入。必须单一权威cutover，禁止双写。
- **生产状态：** `production_backup_enabled=false`；`governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL`；`business_rule_assertions=NOT_EVALUATED`。


### 第四十轮文档同步CI验收

- **文档提交：** `87d749147d2c32da547ce23ed56db69725271a00`；[Run 45778328441](https://github.com/rexyll/cnc-knowledge/actions/runs/45778328441)两个必需Job均completed/success。
- **质量结果：** 全库328项unittest、CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors，报告含5条非阻断warning。
- **登记：** KNOW-000054与ASSET-000085已纳入文档及资源索引；矩阵24条均PROPOSED_NOT_APPROVED/NOT_RUN。
- **限制：** 单aggregate状态键存在全局写串行热点；旧SQLite scheduler/Coordinator状态机仍未迁移；真实etcd集群及多主机验证未完成。


### 第四十轮文档同步CI验收

- **文档提交：** `87d749147d2c32da547ce23ed56db69725271a00`；[Run 45778328441](https://github.com/rexyll/cnc-knowledge/actions/runs/45778328441)两个必需Job均completed/success。
- **质量结果：** 全库328项unittest、CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors（5条非阻断warning）。
- **登记：** KNOW-000054 / ASSET-000085已同步；矩阵24条场景均PROPOSED_NOT_APPROVED / NOT_RUN。
- **限制：** 单aggregate scheduler存在全局写串行热点；旧SQLite scheduler和Coordinator状态机未迁移；真实etcd和多主机验证未完成。


## CH17-T004 Unified Coordinator Authority第四十一轮（2026-11-26）

- **目标：** 把Leader epoch、scope high-water token、ACTIVATE/REVOKE/PUBLISH operation ledger、publish sequence、Provider generation和恢复审查，与Admission quota/queue/lease并入同一事务权威。
- **实现：** 新增 `scripts/spare_parts_provider_unified_coordinator_authority.py` 的 `StoreBackedCoordinatorAuthority`。Unified Admission aggregate升级为schema v2、namespace `/cnc/admission/unified/v2/`；aggregate的coordinator子状态保存Leader、scopes、operations。Leader TTL key与aggregate Leader镜像通过同一Txn更新；scope/operation写入比较aggregate revision、Leader TTL key精确值，且对关联Admission Lease比较活动Lease和持久request索引。
- **Leader：** claim采用单调epoch与TTL互斥；renew同epoch更换TTL Lease；recovery claim需要高于持久epoch的外部floor和reference。旧epoch在takeover后不能授权操作或签名。
- **Scope/Operation：** ACTIVATE/REVOKE/PUBLISH采用两阶段状态机，需Provider read-back才能确认；PUBLISH sequence在scope内CAS单调分配，idempotency key绑定request digest；恢复操作进入RECOVERY_REVIEW，scope进入RECOVERY_REQUIRED，不自动cutover。
- **Proof签名：** `sign_distributed_fencing_proof()`接入backend-neutral authority protocol，授权时重新校验Leader和持久operation身份（含owner、tenant、domain、lease expiry），避免使用篡改过的operation快照签发证明。
- **测试：** 新增8个契约测试方法，SQLite与InMemoryEtcdV3Client各执行一次，共16次适配器测试执行；覆盖本地合成Provider ACTIVATE/PUBLISH/REVOKE完整链、Leader TTL/takeover/recovery floor、tenant scope、幂等、并发序列、restore review、共享aggregate和签名身份篡改拒绝。代码提交 `3d79149c1112550b4fb25efbe02b5f536b08cacd`；[Run 45810737444](https://github.com/rexyll/cnc-knowledge/actions/runs/45810737444)两个必需Job均completed/success，全库344项unittest、CH12 143项测试通过，lint与结构质量0 errors。
- **知识/资源：** 新增KNOW-000055及ASSET-000086，矩阵35条全为PROPOSED_NOT_APPROVED/NOT_RUN；更新KNOW-000054为schema v2，复用SRC-000391/392/397/398。
- **重要限制：** 旧SQLite Admission和Coordinator类仍未替换；v1→v2数据迁移及单一权威cutover未完成；真实etcd及多主机/真实Provider未连接。aggregate单键仍有写串行与operation ledger增长风险。
- **生产状态：** `production_backup_enabled=false`；`governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL`；`business_rule_assertions=NOT_EVALUATED`。


### 第四十一轮文档同步CI验收

- **文档提交：** `706cfcf36204c1bfe996501e65031a21e8536783`；[Run 45811108498](https://github.com/rexyll/cnc-knowledge/actions/runs/45811108498)两个必需Job均completed/success。
- **质量结果：** 全库344项unittest、CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors（5条非阻断warning）。
- **登记：** KNOW-000055与ASSET-000086已同步；矩阵35条场景均PROPOSED_NOT_APPROVED / NOT_RUN。
- **限制：** 旧SQLite Coordinator / Admission尚未迁移；v1→v2生产导入/回滚未完成；真实etcd、多主机和生产Provider未验证。


### 第四十一轮文档同步CI验收

- **文档提交：** `706cfcf36204c1bfe996501e65031a21e8536783`；[Run 45811108498](https://github.com/rexyll/cnc-knowledge/actions/runs/45811108498)两个必需Job均completed/success。
- **质量结果：** 全库344项unittest、CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors（5条非阻断warning）。
- **登记：** KNOW-000055 / ASSET-000086已同步，35条场景均PROPOSED_NOT_APPROVED / NOT_RUN。
- **限制：** 旧SQLite Coordinator及Admission服务未迁移；真实etcd、多主机与外部Provider未验证；aggregate归档/分片容量证明未完成。


### 第四十一轮文档同步CI验收

- 文档提交 `706cfcf36204c1bfe996501e65031a21e8536783`，CI Run 45811108498两个必需Job均completed/success。
- 全库344项unittest、CH12 143项数值资源测试通过；strict lint 0 errors；结构质量0 errors，5条非阻断warning。
- ASSET-000086的35条场景保持PROPOSED_NOT_APPROVED / NOT_RUN；旧SQLite Coordinator尚未替换，v1→v2生产cutover未执行。


## CH17-T004 Unified Coordinator Aggregate容量画像（第四十二轮）

- **实际完成日期：** 2026-11-26（Asia/Shanghai）。
- **分支：** main（未创建新分支）。
- **新增实现：** scripts/spare_parts_coordinator_capacity_probe.py；tests/test_spare_parts_coordinator_capacity_probe.py。
- **新增知识/资源：** KNOW-000056、ASSET-000087、SRC-000402；新增容量模型正文及14条合成profile CSV；同步CH17正文导航、任务计划与资源索引。
- **实现边界：** 只读取内存中生成的合成schema-v2状态，不连接SQLite/etcd/Provider；canonical JSON value字节数精确，完整gRPC/protobuf请求大小及实际延迟/吞吐不测量。50%预算是内部画像假设，不是生产硬阈值。
- **验收状态：** 仓库CI待本轮实现提交触发后确认；ASSET-000087正式场景仍PROPOSED_NOT_APPROVED，未开展真实etcd或企业容量验收。


### 第四十二轮CI验收（2026-11-26）

- **实现提交：** `f52937e1af7b622c11801e2ca502661365e75d05`；分支main。
- **CI：** [GitHub Actions Run 45814052446](https://github.com/rexyll/cnc-knowledge/actions/runs/45814052446)，head SHA与实现提交一致，两个必需Job均completed/success。
- **测试结果：** 全库356项unittest通过（新增容量探针12项全部通过）；CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors，5项为既有非阻断warning。
- **合成范围：** 14个容量profile在CI合成测试中执行，scope/operation索引增长关系与active lease比较项模型检查通过。
- **限制：** 没有连接真实etcd、SQLite生产数据或对象存储Provider；没有测量真实gRPC/protobuf请求大小、Txn延迟/吞吐和多主机quorum。50%只是分析展示预算，不是生产限值。ASSET-000087仍PROPOSED_NOT_APPROVED；真实etcd容量验收NOT_RUN。
- **状态：** CH17-T004继续IN_PROGRESS；未执行生产迁移或cutover。


## CH17-T004 Coordinator Operation Ledger生命周期与安全归档（第四十三轮）

- **完成日期：** 2026-11-26（项目TaskHistory按Asia/Shanghai记日；未接入生产执行环境）。
- **分支：** main；未创建分支。
- **新增知识/来源/资源：** KNOW-000057、ASSET-000088、SRC-000403～SRC-000405；新增归档协议正文及25项CSV场景矩阵。
- **新增代码：** scripts/spare_parts_operation_ledger_archive.py；tests/test_spare_parts_operation_ledger_archive.py，共24个内存参考模型测试方法。
- **关键设计：** immutable put → read-back SHA-256 → authoritative scope-pointer CAS → hot index removal；CAS冲突不删除hot records；idempotency exact lookup跨archive manifest chain；归档不可降低scope fencing/sequence floors。
- **安全边界：** pending activation/revocation/publish/recovery-review操作阻断归档；archive outage/corruption fail-closed；orphan archive objects不在归档事务删除；物理保留与GC需要独立审批。
- **验收状态：** 自动测试待本轮提交CI执行；ASSET-000088的25条正式场景全部PROPOSED_NOT_APPROVED / NOT_RUN。参考模型无真实存储、真实Coordinator、etcd集群或企业归档集成。
- **遗留事项：** 生产实现需先明确归档介质、精确索引、读后写一致性、保留/法律保留、schema v3迁移及回滚、真实多主机/故障测试；生产备份/归档继续关闭。


### 第四十三轮CI验收与修正记录

- **最终测试head：** 4ed91a04138e30ecf2275c07bb947ecc872fadd2；main分支；[GitHub Actions Run 45817146500](https://github.com/rexyll/cnc-knowledge/actions/runs/45817146500)两个必需Job均completed/success。
- **结果：** 全库380项unittest通过（其中24项为新增Operation Ledger archive参考模型测试）；CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors。5项warning来自既有合成夹具数据集DRAFT/企业环境未批准等状态。
- **CI修正：** Run 45816870459发现lost-commit-response测试在归档开始前禁用了scope读取；提交 f8e373411c3612b733d525b475cf64dcd79ed699 将读故障注入移动到权威指针/热索引切换之后。Run 45817037091随后发现测试断言用了错误的统计字段名；提交 4ed91a04138e30ecf2275c07bb947ecc872fadd2 修正。第三次完整CI通过。
- **最终限制：** 纯内存参考模型，不接入当前StoreBackedCoordinatorAuthority，不连接真实etcd、生产SQLite或云对象存储；25条ASSET-000088正式场景仍全部PROPOSED_NOT_APPROVED / NOT_RUN。未启用生产归档、保留策略或schema迁移；CH17-T004继续IN_PROGRESS。


## CH17-T004 Archive Index精确幂等查询与Schema v3迁移/回滚（第四十四轮）

- **日期：** 2026-11-26（Asia/Shanghai）；分支main，未创建新分支。
- **新增知识/资源：** KNOW-000058、ASSET-000089；正文为Archive Index与Schema v3迁移/回滚设计；CSV正式场景矩阵47项，全部PROPOSED_NOT_APPROVED / NOT_RUN；来源沿用SRC-000403～SRC-000405。
- **新增实现：** scripts/spare_parts_operation_archive_index.py（SHA-256精确分片索引、回填/增量、root/shard/batch校验、full-chain audit）；scripts/spare_parts_coordinator_schema_migration.py（v2 freeze、candidate build/verify、fencing/sequence floor guard、cutover、pre-write rollback及rehydrated reverse migration）。
- **新增测试：** tests/test_spare_parts_operation_archive_index.py（21项）；tests/test_spare_parts_coordinator_schema_migration.py（25项）；合计46项参考模型单测。
- **设计原则：** Exact miss必须由完整root/桶索引与Coordinator权威archived count共同证明；v3事务围绕本次scope和operation key，不能按全局active lease数量线性增加Compare；迁移使用冻结写入和控制指针CAS；V3有任何mutation后禁止指向旧v2快照，反向迁移须全量rehydrate并核对容量/floors。
- **范围边界：** 不修改StoreBackedCoordinatorAuthority生产schema-v2；不连接真实etcd/对象存储/SQLite；不执行迁移或cutover；ASSET-000089所有正式场景待批准/未执行。
- **验收：** 自动化CI待本轮提交触发后确认；CH17-T004继续IN_PROGRESS。


### 第四十四轮CI验收记录

- **最终代码/测试head：** `2b66224909d2bcd9b326c1cffcf220bef5d14b7f`；main分支；[GitHub Actions Run 45819520749](https://github.com/rexyll/cnc-knowledge/actions/runs/45819520749)两个必需Job均completed/success。
- **结果：** 全库426项unittest通过，其中本轮Archive Index 21项、Schema v3 Migration 25项，共46项；CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors。5项warning来自既有DRAFT合成夹具及企业批准/执行门禁。
- **CI修正：** Run 45819355334发现两个测试夹具问题：历史pointer读取使用当前archive count；reverse-migration容量测试未进入V3冻结迁移状态。最终测试夹具在提交 `2b66224909d2bcd9b326c1cffcf220bef5d14b7f` 修正，Run 45819520749完整通过。
- **范围限制：** 纯内存参考模型，不接入StoreBackedCoordinatorAuthority生产schema-v2，不连接真实etcd、SQLite生产库或云对象存储；47条ASSET-000089正式场景全部PROPOSED_NOT_APPROVED / NOT_RUN。未执行Schema v3迁移、cutover、回滚或历史数据删除；CH17-T004继续IN_PROGRESS。
