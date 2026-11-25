# 17. 操作、维护与维修 — 资源目录

本目录只存放归属于本章节的图片、动图、视频/音频（如适用）及有权保存的完整文档（Word、PDF、Excel、CSV等），以及本章相关的工程图、测量数据和附件。

## 归档规则

- 资源在正文中必须有引用，并在本章 `ASSET-INDEX.md`（建立后）中登记来源、作者/机构、取得或生成日期、版本、许可/授权状态、关联知识条目和说明。
- 优先保留原始文件；整理版、裁剪版、翻译版必须单独命名并注明与原件的关系。
- 对版权或保密状态不明、无权再分发的资料，不保存副本，仅记录可合法保留的元数据和官方链接。
- 不重复复制同一原始文件；跨章节使用时引用主归属章节的资源路径。


## CH17-T001 机床操作准备检查模板（2026-11-25）

- operation-readiness-checklist.csv：项目原创空白检查表，组织设备识别、开机前、防护/报警、润滑冷却与压力系统、刀具工件/程序准备、运行监视、停机、维护维修前置和记录归档共25项。
- 检查结果初始为NOT_ASSESSED；不预置具体型号、维护周期、润滑剂牌号、压力/温度/浓度或合格限值。
- 使用前需绑定具体机床型号、配置、软件版本、现行制造商手册、现场风险评估及责任人员；该模板不是可直接执行的通用SOP。
- 来源登记见ASSET-INDEX.md及docs/data/sources/SRC-000382.json～SRC-000388.json；外部原始法规、标准和制造商手册仅保留官方链接。


## CH17-T001 维修工单与维修后复验模板（2026-11-25）

- `repair-work-order-template.csv`：原创维修工单字段模板，覆盖设备实例、控制系统版本、报修现象、报警原文、工况证据、危险能量/能量控制程序引用、人员授权、OEM手册版本、诊断记录、根因状态、维修动作、替换件批次、参数/配置变更、复验结果和放行关闭。
- `post-repair-verification-matrix.csv`：原创复验覆盖矩阵，按维修影响覆盖安全功能、电气/驱动、进给轴/反馈、主轴、ATC、液压气动、润滑冷却、几何定位、CNC/PLC参数、趋势和首件质量。
- 两份模板均不包含具体拆装步骤、能量隔离步骤、参数设定值、维护周期或统一验收阈值；实际工单和测试记录需保存在企业受控系统。
- 来源登记见ASSET-INDEX.md及docs/data/sources/SRC-000382.json～SRC-000390.json；外部标准和制造商文件仅保留官方链接与元数据。


## CH17-T002 计划维护模板与OEM实例（2026-11-25）

- `maintenance-task-matrix-template.csv`：维护任务分类与计划字段模板，包含日历/运行时间/循环/状态/事件触发类型、OEM依据、配置适用性、授权、判据和结果记录；具体周期/阈值留空。
- `maintenance-card-template.csv`：单项维护作业卡，记录设备身份、到期依据、手册修订、风险/能量控制、工具仪表、耗材批次、测量结果、复核和下次到期信息。
- `maintenance-consumables-register-template.csv`：润滑剂、冷却液、滤芯、油脂等耗材登记模板；仅有类别示例，所有OEM规格和料号待核实。
- `haas-lathe-rd0035-selected-maintenance-examples.csv`：Haas车床官方交互式服务手册RD0035 Revision A-04/2026的有限精选摘要。其任务周期仅适用于匹配的Haas车床产品配置，不能作其他机床默认值。
- 来源见 `docs/data/sources/SRC-000388.json` 与 `SRC-000389.json`；不归档受版权保护的标准/完整服务手册。


## CH17-T003 部件更换工作包与兼容性模板（2026-11-25）

- component-replacement-work-package-template.csv：单次更换工作包字段模板，关联设备实例、拆换部件身份、OEM手册版本、风险/能量控制程序、授权、基线备份、兼容性审核、校准、复验和放行证据。
- component-tool-and-measurement-register-template.csv：登记专用工装、吊装器具、量具和诊断设备的型号/序列号、量程/能力、校准与检验状态；未定义通用量程或精度。
- component-interface-and-replacement-compatibility-template.csv：覆盖机械、电气、液压/气动、润滑冷却、控制软件、固件、热环境和安全接口；每项兼容性须指向OEM或批准工程证据。
- 三份表均为原创空白模板，不是执行许可证，也未填入机型级紧固值、预紧量、吊装参数、介质规格、补偿或验收阈值。缺失关键资料时工作包保持BLOCKED。
- 来源登记见本目录 ASSET-INDEX.md、docs/data/sources/SRC-000382.json 与 SRC-000390.json。


## CH17-T003 关键部件族影响分析与复验矩阵（2026-11-25）

- component-family-impact-verification-matrix-template.csv：九类关键部件族的结构化审查矩阵，共57条记录、20列，涉及拆前基线、替代兼容性、OEM程序、风险/能量控制、维修后验证、方法/判据来源和责任专业。
- 每行初始适用性TO_BE_ASSESSED、结果NOT_TESTED；需要按具体机床序列号/配置裁剪。OEM程序或接受准则缺失时不得判定通过，应保持工作包BLOCKED。
- 矩阵是审查提示，不提供拆装顺序、吊装参数、紧固/预紧数值、介质规格或通用验收限值；真实记录存放在企业受控系统。
- 关联正文：docs/17-operation-maintenance-and-repair/component-family-impact-assessment-and-verification.md；实体KNOW-000024、ASSET-000018。


## CH17-T003 主轴、伺服与滚珠丝杠专项工作包模板（2026-11-25）

- spindle-replacement-work-package-template.csv：主轴总成、电机、反馈/定向、刀具夹持、润滑冷却、吊装/支撑、安装基准、参数恢复和性能复验等18个检查项，35列。
- servo-motor-encoder-replacement-work-package-template.csv：轴身份、电机/驱动配套、反馈协议/安装、制动器、联轴器、电缆/接地、伺服基线、参数恢复、定位与安全复验等17个检查项，35列。
- ballscrew-support-bearing-replacement-work-package-template.csv：轴系身份、丝杠/螺母/支撑轴承成套关系、几何基线、预紧来源、润滑、重力/搬运风险、安装和定位复验等17个检查项，35列。
- 所有模板均默认TO_BE_ASSESSED/NOT_TESTED；OEM程序、关键值与接受准则字段待具体机床文件填写。无OEM依据时保持BLOCKED，不能当作可直接执行的SOP。
- 关联正文：docs/17-operation-maintenance-and-repair/spindle-servo-ballscrew-specialized-replacement-work-packages.md；实体KNOW-000025、ASSET-000019～ASSET-000021。


## CH17-T003 刀库/换刀、卡盘夹持与液压气动专项工作包模板（2026-11-25）

- `atc-tool-magazine-turret-replacement-work-package-template.csv`：ATC刀库、刀套、换刀机械手、凸轮/链传动、刀塔/动力刀具、I/O反馈、安全互锁及受控功能验证，共20项、35列。
- `chuck-workholding-replacement-work-package-template.csv`：卡盘/夹持接口、卡爪/软爪/筒夹、拉杆、夹紧执行缸、旋转接头、夹持确认、工件边界和受控动态测试，共18项、35列。
- `hydraulic-pneumatic-unit-replacement-work-package-template.csv`：泵阀、执行器、管路接头、过滤/介质、蓄能器、残压、保护阀、传感器校准、泄漏与功能复验，共20项、35列。
- 三份模板均为项目原创，默认TO_BE_ASSESSED/NOT_TESTED；不包含通用换刀动作、泄压/蓄能器操作、压力/夹持力/转速/流量/温度或验收值。必须依据具体设备OEM受控文件和现场安全程序填写。
- 关联正文：`docs/17-operation-maintenance-and-repair/atc-chuck-hydraulic-specialized-replacement-work-packages.md`；实体KNOW-000026、ASSET-000022～ASSET-000024。


## CH17-T004 备件管理与生命周期闭环模板（2026-11-25）

- `spare-part-master-data-template.csv`：每个零件/修订/适用范围一条，记录OEM/内部料号、BOM位置、机型序列适用性及技术/储存来源。
- `spare-part-criticality-assessment-template.csv`：按指定设备范围记录安全、生产、质量、冗余、可检测性、修复能力和供应风险；评分方法/权重须采用企业批准规则。
- `spare-part-inventory-and-replenishment-template.csv`：按零件/仓库/库位/批次记录库存分桶、需求窗口、交期证据、补货参数和盘点差异；所有库存阈值留空。
- `spare-part-substitution-approval-template.csv`：记录原件与候选件范围、接口/材料/电气/流体/软件/安全证据、工程和OEM审批及验证结果。
- `spare-part-lifecycle-and-obsolescence-template.csv`：记录PCN/EOL、last-time-buy、最后发货、服务支持、安装基数、替代迁移和缓解计划。
- `repair-spare-consumption-feedback-template.csv`：将维修工单、设备实例、旧/新件批次、库存事务、复验结果、补货请求和故障反馈关联。
- 所有文件为项目原创空白模板，不含真实料号、供应商、库存、价格、交期、阈值、批准的替代件或现场维修数据。
- 关联正文：`docs/17-operation-maintenance-and-repair/spare-parts-management-and-lifecycle.md`；实体KNOW-000027、ASSET-000025～ASSET-000030。


## CH17-T004 备件系统集成与数据治理第二轮（2026-11-25）

- `spare-parts-enterprise-system-field-mapping-template.csv`：27列空白模板，逐字段记录源系统对象/字段、规范对象/字段、数据类型与单位、外部键作用域、字段级SoR、转换/空值/有效期规则、同步方向、质量规则、敏感等级和审批。
- `spare-parts-data-quality-and-reconciliation-rules.csv`：16条项目建议规则，覆盖源键唯一、引用完整性、BOM配置适用性、修订有效期、单位转换、库存分桶、事务数量守恒、幂等、采购在途、批次追溯、替代审批、PCN/EOL、工单消耗、状态权限、来源审计和敏感数据最小化。所有规则均为PROPOSED，不能未经企业批准直接作为生产阻断规则。
- `spare-parts-stock-policy-decision-template.csv`：35列表头空模板，收集需求窗口、消耗与安装基数来源、供应商交期证据、关键度、策略方法版本、库存参数、适用配置、审批和复核字段；没有预填安全库存、订货点、最小/最大量、MOQ或周期。
- 关联正文：`docs/17-operation-maintenance-and-repair/spare-parts-system-integration-and-data-governance.md`；实体KNOW-000028、ASSET-000031～ASSET-000033。
- 本轮不代表企业ERP/CMMS/EAM/PLM接口已建立；实际映射与规则启用需取得授权数据，并由业务、工程、质量、采购、仓储和信息化责任角色批准。


## CH17-T004 备件实物流转与事务控制第三轮（2026-11-25）

- `spare-parts-transaction-lifecycle-control-matrix.csv`：23列表头、16个控制节点，覆盖需求提出、技术/配置确认、采购下单、收货、检验放行、上架、盘点、预留、发料、现场转运、安装消耗、旧件回收、返修处置、报废、库存对账和PCN/EOL评估。记录前置条件、身份键、证据、审批、物理/系统状态、库存桶影响、异常处置、幂等键和冲销规则；节点均为PROPOSED。
- `spare-parts-raci-approval-matrix-template.csv`：16列表头、16项活动，按资产所有者、维修、工程、质量、安全、采购、仓储、OEM授权服务、数据所有者和IT集成角色预置建议RACI；每项活动有一个建议A和至少一个R，但所有分配都需企业正式批准。
- 关联正文：`docs/17-operation-maintenance-and-repair/spare-parts-physical-flow-and-transaction-controls.md`；实体KNOW-000029、ASSET-000034～ASSET-000035。
- 不代表已建立企业流程、接口或授权。真实状态、系统SoR、事务和审批需结合企业制度与受控设备资料确认。


## CH17-T004 备件端到端验收与测试证据第四轮（2026-11-25）

- `spare-parts-end-to-end-acceptance-test-matrix.csv`：24列、30个测试规格，覆盖外部键/BOM适用性、采购/收货/质量放行、库存数量/在途、单位换算、重复事件幂等、替代范围、发料与安装、批次追溯、旧件返修报废、盘点、PCN/EOL、权限、SoR、敏感数据和事件恢复。所有执行状态初始为NOT_RUN。
- `spare-parts-acceptance-test-execution-record-template.csv`：30列表头空模板，记录测试环境/版本、合成数据集、角色、预期/实际业务结果、库存影响、追溯/审计、结果状态、缺陷、证据和复测链。
- 关联正文：`docs/17-operation-maintenance-and-repair/spare-parts-end-to-end-acceptance-testing.md`；实体KNOW-000030、ASSET-000036～ASSET-000037。
- 本轮仅定义测试规格，未执行企业SIT/UAT、生产影子运行或实机测试。正式执行前必须获得非生产环境授权，冻结SoR/字段映射并批准测试数据集。

## CH17-T004 备件合成测试数据集与环境就绪第五轮（2026-11-25）

- `spare-parts-synthetic-test-dataset-manifest-template.csv`：29列表头空模板，登记数据集ID/语义版本、生成器和种子引用、对象域/测试用例、冻结审批、敏感数据扫描、保留策略和校验值。
- `spare-parts-test-environment-readiness-checklist.csv`：22项/11列检查，覆盖环境与租户识别、身份/网络/数据隔离、测试账号/最小权限、秘密管理、数据集冻结、备份恢复、mock端点、时钟/事件回放、日志、HIL边界、清理及证据。所有状态初始NOT_ASSESSED。
- `spare-parts-test-fixture-cross-reference-template.csv`：27列表头空模板，用合成夹具ID关联MACHINE/MINST/BOM/PART等静态对象以及PO、收货、质检、库存、预留、工单、审批和PCN/EOL事件；事务夹具不因此成为知识库静态实体。
- 关联正文：`docs/17-operation-maintenance-and-repair/spare-parts-synthetic-test-data-and-environment-readiness.md`；实体KNOW-000031、ASSET-000038～ASSET-000040。
- 本轮不含真实企业数据/ID/账号/凭证；22项就绪检查均未评估，30个端到端测试场景仍为NOT_RUN。L2/L3执行需企业批准的隔离非生产环境和冻结数据集。

## CH17-T004 备件合成测试夹具基线第六轮（2026-11-25）

- `spare-parts-synthetic-fixture-baseline-v1-manifest.csv`：SPAREPARTS-SYN-BASE-001 v1.0.0元数据，单行/29列，状态DRAFT，未获企业批准。
- `spare-parts-synthetic-fixture-baseline-v1.csv`：89条/27列固定合成对象与事件记录，包括67个对象及22个事件；所有标识为虚构SYN-/FX-/EVT-，按reset_group隔离。
- `spare-parts-synthetic-fixture-test-case-coverage-v1.csv`：30行/11列，覆盖全部SPAT-001～SPAT-030，列出正向/负向夹具、事件和预期断言；全部NOT_RUN。
- 关联正文：`docs/17-operation-maintenance-and-repair/spare-parts-synthetic-fixture-baseline-v1.md`；实体KNOW-000032、ASSET-000041～ASSET-000043。
- 所有数量、BOM日期与单位换算只是虚构测试值，不代表真实机床、企业库存政策或产品规格。当前未批准/冻结数据集，未执行企业SIT/UAT或现场测试。

## CH17-T004 合成夹具静态校验报告

运行 `python scripts/spare_parts_fixture_validator.py --root .` 可在本地只读校验数据集；运行以下命令可在资源目录生成机器可读JSON报告：

```bash
python scripts/spare_parts_fixture_validator.py --root . \
  --report-json resouces/17-operation-maintenance-and-repair/generated/spare-parts-fixture-validation-report-v1.json
```

报告会记录输入文件SHA-256、检查项、数据集身份、计数、警告和错误。CI同样执行校验并把本次报告以Artifact归档。生成报告不修改夹具CSV，也不会将DRAFT数据集升级为APPROVED/FROZEN；提交生成报告时需按项目规则另行登记资源实体。

## CH17-T004 场景重置配置与本地包生成器第八轮（2026-11-25）

- `spare-parts-synthetic-fixture-reset-profiles-v1.csv`：30行/15列场景重置配置，逐用例登记正向/负向夹具、事件、依赖闭包、reset group、稳定幂等键、装载顺序和本地包清理范围；执行范围固定为FILESYSTEM_STAGING_ONLY。
- `scripts/spare_parts_fixture_loader.py`：纯Python标准库本地场景包生成器。只读取源数据，校验配置与依赖后，在用户指定目录写入单场景或全部30场景包；若目标场景目录已存在则拒绝覆盖。
- 每个场景包包括scenario-manifest.json、fixtures.csv、objects.csv、events.csv、load-plan.json和reset-plan.json；reset计划固定PLAN_ONLY，清理范围仅限生成的本地包。
- 不连接数据库/API/队列，不执行导入、业务事务、企业环境重置或删除。目标系统适配器NOT_IMPLEMENTED；生成场景包不改变源测试用例的NOT_RUN状态。
- CI单元测试和静态夹具校验已完成；全量30场景打包和Artifact归档已纳入CI。

## CH17-T004 场景包离线校验与期望事件投影第九轮（2026-11-25）

- `scripts/spare_parts_scenario_runner.py`：独立重建场景包并对六份文件逐字节校验，复核来源数据和SHA-256、纯合成属性、对象/事件分区、依赖闭包与时间/序号顺序；拒绝内容漂移、缺失/额外文件和符号链接。
- 离线事件处理目录明确登记22类合成事件：数量增量事件按期望库存桶投影；重复消息要求保留原始收货事件关联且零增量；迟到冲销保留原事件；乱序必须显式标记；取消PO、权限拒绝、PCN/EOL、SoR和数据导出等非库存事件不得改变库存桶。
- 数量增量使用Decimal并按reset_group分别输出；不跨组求和，不计算期末库存/可用量（缺少获批期初余额及企业库存口径）。
- 新增 `tests/test_spare_parts_scenario_runner.py` 11项测试，包含全30包、包篡改、缺失文件、重复事件零增量、非库存事件零变更、冲销/乱序关联和CLI JSON报告；CI当前全量单测33项通过。
- CI在生成30个场景包后运行离线执行器；本轮日志确认30/30模拟完成、0失败。报告Artifact与包Artifact分别归档。
- **严格状态边界：** 模拟PASS仅是包完整性与期望事件投影一致，不等于业务规则正确；`business_rule_assertions=NOT_EVALUATED`、30项企业业务测试仍NOT_RUN。数据集DRAFT、22项环境检查NOT_ASSESSED，未连接/修改任何企业系统。

## CH17-T004 库存状态机内核与转移契约第十轮（2026-11-25）

- `spare-parts-inventory-state-transition-contract-v1.csv`：22类事件契约，全部NOT_APPROVED；未猜测库存桶之间的转移关系。
- `scripts/spare_parts_inventory_state_model.py`：独立双边转移内核，使用Decimal、来源余额非负、双边数量守恒、失败原子性；没有企业系统连接或写入能力。
- 当前数据仅支持单桶期望增量投影，尚不足以构建企业业务期望状态；须先批准账户字典、维度、期初余额和预留/分配/冲销语义。

## CH17-T004 期初状态与库存维度候选模型第十一轮（2026-11-25）

- `spare-parts-inventory-account-catalog-candidates-v1.csv`：新增候选资源；13类账户候选，明确实物账户与备忘/观察账户不可混算。
- `spare-parts-inventory-dimension-dictionary-candidates-v1.csv`：新增候选资源；列出物料、批次、库位、所有权、状态、单位及工单/采购行候选维度。
- `spare-parts-inventory-opening-balance-template-v1.csv`：新增候选资源；仅有表头，不含预填余额；要求来源记录、截止时点、时区、哈希和批准依据。
- `spare-parts-inventory-opening-state-scenario-matrix-v1.csv`：新增候选资源；映射9个代表性场景的期初输入和守恒断言，全部未批准且未执行。

所有账户、维度和场景均为讨论候选，未获得企业批准，不得据此过账或生成业务期末库存。

## CH17-T004 多维库存余额模型第十二轮（2026-11-25）

- spare-parts-multidimensional-inventory-model-test-cases-v1.csv（ASSET-000050）：17项纯合成数学性质测试，覆盖多维余额键、同单位守恒、跨库位/物料/批次/所有权拒绝、单位换算审批、期初快照隔离、事件ID/序号及整批回放原子性。
- 模型代码：scripts/spare_parts_multidimensional_inventory.py；专项测试：tests/test_spare_parts_multidimensional_inventory.py。
- CI自检报告：Artifact ch17-multidimensional-inventory-self-check。自检仅验证虚构余额上的数学性质，execution_status固定为BLOCKED_PENDING_ENTERPRISE_APPROVAL。

## CH17-T004 第十三轮：不可变库存事件账本与时点重建

- `spare-parts-inventory-event-ledger-test-cases-v1.csv`（ASSET-000051）：18个纯合成断言场景，覆盖事件追加、幂等键、重复/迟到/乱序、业务时间与知识时间、冲销和重建一致性。
- 模型：`../../scripts/spare_parts_inventory_event_ledger.py`；测试：`../../tests/test_spare_parts_inventory_event_ledger.py`。
- CI报告：Artifact `ch17-inventory-event-ledger-self-check`。只验证纯合成数学性质，业务断言保持NOT_EVALUATED。


## CH17-T004 库存事件账本完整性链与快照恢复第十四轮（2026-11-25）

- 新增规范化事件序列化、逐事件SHA-256、前序链哈希、连续序号/唯一身份校验。
- 新增版本化合成快照：记录账本截止序号、链头、业务/知识截止时点、期初余额、快照余额和摘要；恢复时校验前缀并增量回放，与全量重放逐维比较。
- 对影响快照历史窗口的迟到事件、向后移动的业务截止时点、链头不匹配、摘要损坏及未知版本失败关闭；迟到事件要求全量重建。
- 新增ASSET-000052、15个纯合成断言场景及13个专项unittest方法；首轮CI中全库87项测试通过，但self-check入口因缺少仓库根目录导入路径失败，已定位并修复，需复跑确认。
- **安全边界：** 哈希链不是数字签名或WORM；无法抵御有权限者同时重写数据与哈希。无外部信任根、企业权限/职责分离、持久化、并发或生产连接。CH17-T004继续IN_PROGRESS。


## CH17-T004 库存事件账本完整性链与快照恢复第十四轮验收

- ASSET-000052：15个纯合成断言场景；新增13个unittest方法。
- GitHub Actions Run 45629680465：completed/success；Knowledge structure and data quality、CH12 numerical resource tests两个Job均success；全库87个unittest方法通过。
- 完整性self-check：PASS；2条事件进入哈希链；快照后增量回放1条事件；与全量重放结果一致。
- Artifact：ch17-inventory-ledger-integrity-45629680465。
- 业务断言保持NOT_EVALUATED；审批状态保持BLOCKED_PENDING_ENTERPRISE_APPROVAL；无企业系统连接或数据库/API写入。
