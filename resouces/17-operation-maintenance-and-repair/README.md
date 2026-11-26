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


## CH17-T004 库存事件账本本地持久化与故障恢复第十五轮（2026-11-25）

- 新增版本化代际目录与原子CURRENT指针持久化模型；账本、快照、COMMIT清单分别落盘，恢复校验文件摘要、哈希链、快照摘要和代际元数据。
- 11个故障场景覆盖写入中断、代际孤立、旧版本保持、文件篡改、提交标记缺失、版本不兼容和路径安全。
- CI Run 45631566264：两个Job均成功，全库98个unittest方法通过；Artifact ch17-inventory-ledger-persistence-45631566264。
- 所有测试使用临时目录；不连接企业系统、不写生产状态。原子rename/fsync依赖操作系统和文件系统，不等于数据库事务、WORM或防篡改存储。

## CH17-T004 库存账本并发写入控制与多进程恢复第十六轮（2026-11-25）

- 新增POSIX flock跨进程写锁及CURRENT compare-and-swap（CAS），防止协作式写入者基于过期CURRENT覆盖新代际。
- 新增10个合成测试场景；5个新增unittest方法覆盖两个进程竞争、陈旧写入、锁超时、进程崩溃后内核释放锁及中断恢复。
- CI Run 45635237388：两个Job成功，全库103个unittest通过；自检为2个写入进程、1个提交成功、1个CAS冲突，恢复CURRENT成功。
- Artifact：ch17-inventory-ledger-concurrency-45635237388。
- 平台限制：POSIX flock，Windows原生锁未实现；网络文件系统和分布式锁语义未验证。测试只使用临时目录，不连接企业系统。


## CH17-T004 库存账本读取一致性与代际回收第十七轮（2026-11-25）

- spare-parts-inventory-ledger-read-gc-test-cases-v1.csv（ASSET-000055）：10个纯合成场景，覆盖读者共享锁、writer/GC锁顺序、CURRENT保护、dry-run、保留最近N代、最短保留时间、未验证代际保留、异常清理trash恢复和多进程压力。
- 实现：scripts/spare_parts_inventory_ledger_persistence.py；专项测试：tests/test_spare_parts_inventory_ledger_persistence.py。
- GC默认dry-run；CLI只有显式 --gc-apply 才会删除。按POSIX advisory lock协作，保留CURRENT、最近N个已验证代际和未达到最短年龄的代际。
- 所有测试只操作本地临时目录。Windows原生锁、网络文件系统、跨主机并发、企业留存/备份/删除审批均未验证；不连接企业系统或生产目录。


## CH17-T004 库存账本备份、完整性验证与隔离恢复第十八轮（2026-11-25）

- spare-parts-inventory-ledger-backup-restore-test-cases-v1.csv（ASSET-000056）：10个纯合成场景，覆盖备份创建、清单/文件长度和SHA-256、账本/快照语义校验、备份损坏、备份源代际GC后恢复、非空目标拒绝覆盖和恢复中断。
- scripts/spare_parts_inventory_ledger_persistence.py 提供 create_backup()、verify_backup()、restore_backup() 及对应CLI。
- 备份包包含BACKUP.json、COMMIT.json、ledger.json、snapshot.json；清单自校验并记录各负载哈希。备份路径必须与源账本存储分离；恢复只允许新建/空白目标目录。
- 当前为本地POSIX临时目录合成演练，不是异地备份、加密备份、WORM或企业灾备验收；无外部系统连接或生产写入。


## CH17-T004 库存备份治理与灾备就绪第十九轮（2026-11-26）

- 新增四份空白治理模板：备份保留策略、RPO/RTO目标、加密/密钥管理、异地存储供应商评估（ASSET-000057～ASSET-000060）。
- 新增恢复演练验收矩阵（ASSET-000061），10个场景全部PROPOSED_NOT_APPROVED / NOT_RUN，不预设RPO/RTO、供应商SLA、加密算法或保留期限。
- 新增 scripts/spare_parts_backup_governance_validator.py 与 tests/test_spare_parts_backup_governance_validator.py；校验schema、行宽、唯一ID、审批状态及已批准记录证据；CI输出readiness报告。
- 校验器PASS只代表结构/审批证据完整性；治理就绪与production_backup_enabled继续BLOCKED_PENDING_ENTERPRISE_APPROVAL / false。
- 未接入KMS/HSM、云对象存储或远端账户，不配置或使用密钥，不发起备份/删除操作；企业BIA、保留政策、安全评审和真实恢复演练仍待批准。


## CH17-T004 备份存储适配器与Mock Provider第二十轮（2026-11-26）

- 新增 `scripts/spare_parts_backup_storage_adapter.py`：供应商中立的ObjectStorageProvider契约、FileSystemStorageProvider和内存MockObjectStorageProvider；使用put_if_absent/get_object，不提供delete/list。
- 多对象备份按负载先写、BACKUP-RECEIPT.json最后提交；回执记录负载SHA-256、长度及版本ID。半途失败没有回执，不视为已提交；同内容可重试，不同内容冲突，不自动删除孤儿对象。
- 验证先校验回执和对象摘要，再调用原备份包校验；恢复只写空白隔离目录。
- Mock只模拟行为和能力声明，不访问网络/云服务，不使用凭据/密钥，不实现真实加密、对象锁或异地耐久存储。

- 专项测试数量：13个unittest方法；ASSET-000063矩阵定义12个测试场景。最终Run 45732798249两个Job成功，全库140个unittest通过，Mock适配器self-check PASS。


## CH17-T004 Provider安全与分块可靠性第二十一轮（2026-11-26）

- 新增 `scripts/spare_parts_backup_storage_adapter.py` Provider能力：身份认证/授权模型、租户隔离、审计边界、分块上传和前缀范围只读盘点声明。
- Mock Provider加入principal/action/prefix ACL模拟与仅记录元数据的审计轨迹；不使用真实IAM/凭据。
- 增加确定性multipart upload ID、分块SHA-256、序号连续性、同块幂等、冲突拒绝、断点续传和仅清理未完成分块会话的abort边界。
- 增加prefix-scoped inventory，返回元数据而非对象正文；分类未提交对象、已验证备份、缺失/异常对象和未完成分块会话。回收候选始终PROPOSED_NOT_APPROVED且不可执行；无已完成对象delete API。
- 新增KNOW-000035及3份资源（ASSET-000064～000066）；全库150个unittest通过，最终CI Run 45737732766两个Job success，适配器Artifact ID 15079009952。


## CH17-T004 Provider安全与分块可靠性第二十一轮（2026-11-26）

- 新增 `spare-parts-inventory-backup-provider-identity-access-review-template.csv`（ASSET-000064）：身份、权限、租户、凭据托管与审计审批空白模板。
- 新增 `spare-parts-inventory-backup-orphan-inventory-reclamation-review-template.csv`（ASSET-000065）：对象/分块只读盘点及受控回收审批记录。
- 新增 `spare-parts-inventory-backup-provider-resilience-test-matrix-v1.csv`（ASSET-000066）：14条合成测试场景定义，状态PROPOSED_NOT_APPROVED / NOT_RUN。
- 新增KNOW-000035；新增Provider ACL、Multipart、prefix inventory能力；不实现真实IAM/云凭据、已完成对象删除或自动回收。

- 最终资源格式复核：ASSET-000064 26列空白模板、ASSET-000065 30列空白模板、ASSET-000066 11列/14条测试矩阵；CI Run 45738063901两个Job success，150个unittest通过，Artifact 15080002233。


## CH17-T004 Provider瞬态故障与模糊提交恢复第二十二轮（2026-11-26）

- 新增 `ProviderTransientError`：显式区分可重试瞬态错误以及outcome_unknown提交结果未知错误；永久权限/冲突/完整性错误不自动重试。
- `BackupStorageAdapter`新增可配置最大尝试次数、基础/最大延迟及sleep注入，采用有界指数退避并合并Provider Retry-After提示；当前Mock不使用随机抖动。
- Mock故障注入包括写入成功但响应超时、分块写后响应超时、分块完成后响应超时、读取可见性延迟、瞬态读故障和历史版本切换/缺失。
- 对象写入、回执写入、分块和读取均以原key/backup ID/upload ID/part number和相同内容幂等重试；重试耗尽不得标记成功。
- 自检覆盖提交超时、延迟可见、瞬态读取、当前版本切换和固定历史版本隔离恢复；全库160个unittest通过。


## CH17-T004 Provider重试与一致性第二十二轮（2026-11-26）

- 新增ProviderTransientError与outcome_unknown分类；只重试可明确归类的瞬态错误，永久错误不重试。
- 新增可配置有界指数退避：默认最多4次尝试、base 0.1s、max 2s，可注入sleep函数；Mock测试不真实等待且不启用随机抖动。
- 模拟PUT提交成功但响应丢失、multipart part写后超时、multipart complete已提交但响应丢失、对象读后写延迟和瞬态GET限流；所有重试固定同一请求身份/对象键/内容。
- 支持Mock历史版本集合与版本切换；历史版本仍在时依回执固定版本读取，版本缺失时失败关闭，不回退到最新版本。
- 新增ASSET-000067，定义12条重试/一致性合成场景。实现及测试全库159个unittest通过；第二十二轮组合self-check还需最终CI确认。


## CH17-T004 Provider熔断、半开探测、舱壁与总重试预算第二十三轮（2026-11-26）

- 新增按read/write/multipart/inventory四个操作域隔离的CircuitBreaker，状态CLOSED/OPEN/HALF_OPEN；达到连续瞬态失败阈值后快速熔断，冷却后执行受限探测，成功关闭、失败重开。
- 新增同域Bulkhead有界并发槽位；read/write/multipart/inventory默认容量4/2/2/1；默认满载快速失败，调用结束/异常后释放槽位。
- 新增ContextVar任务级RetryBudget：一个顶层备份/验证/恢复/盘点的所有嵌套Provider调用共享总预算，并发线程/任务彼此隔离；默认20次重试预算。
- 配置默认值仅为代码基线，不构成生产容量、熔断阈值或RTO建议；控制状态仅在单Adapter实例/进程内，不是分布式限流。
- 新增9项专项unittest，代码与测试提交全库169个unittest通过，CI Run 45740068529两个Job success；自检扩展CI Run 45740213445两个Job success，Artifact 15081155445；最终文档同步CI Run 45740530720两个Job success，Artifact 15080399203。


## CH17-T004 Provider熔断与资源隔离第二十三轮（2026-11-26）

- 新增CircuitBreaker按read/write/multipart/inventory操作域隔离，默认连续瞬态失败阈值3、冷却30s、半开最多1个探测。
- 新增Bulkhead按域限制并发，默认read=4/write=2/multipart=2/inventory=1，满载快速失败，不排无限队。
- 新增顶层RetryBudget，默认20次总重试，任务上下文内所有Provider调用共享；并发线程/任务预算隔离。
- 新增9项专项unittest；全库169个unittest通过；自检覆盖熔断open/half-open恢复和总预算耗尽，最终CI Run 45740530720两个Job success。
- 新增ASSET-000068，14条熔断/舱壁/任务预算合成场景，状态PROPOSED_NOT_APPROVED / NOT_RUN。
- 严格边界：熔断/舱壁只单Adapter实例/进程生效，不是分布式控制；未进行真实云、跨容器或生产容量测试。



## 第二十四轮新增资源

- `spare-parts-inventory-backup-provider-fair-scheduling-test-matrix-v1.csv`（ASSET-000069）：15项公平调度、租户并发配额、任务取消和deadline合成场景；全部PROPOSED_NOT_APPROVED / NOT_RUN，不构成生产调度验收。


## 第二十五轮新增资源

- `spare-parts-inventory-backup-provider-shared-coordination-test-matrix-v1.csv`（ASSET-000070）：17项同进程多Adapter共享配额、令牌桶、租约恢复和异常路径结果未知场景；全部PROPOSED_NOT_APPROVED / NOT_RUN，不构成跨进程或生产分布式协调验收。


## CH17-T004 Provider协调器故障模型第二十六轮

- 扩展共享协调测试矩阵（ASSET-000070）：新增SAC-018～SAC-024，合计24项。新增场景覆盖协调服务不可用、准入响应丢失后孤儿租约TTL回收、Provider执行中协调分区、validate/release故障、服务恢复和诊断/续租故障。
- 所有场景仍为纯合成规格，TRUE / PROPOSED_NOT_APPROVED / NOT_RUN；不代表真实网络分区、跨进程或生产故障演练。
- 新增 KNOW-000040；本轮新增6项Provider专项unittest。实现仍仅针对同进程Mock协调器。


### 第二十六轮最终CI验收补记

- 修复提交：1a9a623e52475059872d8662fb64ee8956b973c2；CI Run 45745399203两个Job均completed/success。
- 全库188个unittest通过；knowledge_lint.py --strict为PASS（0 errors）。
- Provider Mock self-check PASS，Artifact ID 15083022622；备份治理readiness Artifact ID 15082588660，生产备份仍关闭。
- 本轮仅验证同进程Mock协调故障合同；ASSET-000070的24条场景仍全部PROPOSED_NOT_APPROVED / NOT_RUN。
