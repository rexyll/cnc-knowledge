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


## CH17-T004 Provider准入队列容量保护第二十七轮

- 新增 `spare-parts-inventory-backup-provider-admission-queue-bound-test-matrix-v1.csv`（ASSET-000071）：7条队列容量、协调器等待中失效与恢复后重新准入合成场景；全部TRUE / PROPOSED_NOT_APPROVED / NOT_RUN。
- 新增KNOW-000041：本地与共享准入队列的最大等待者上限；0允许无等待的即时准入。默认256是实现基线，不是生产容量建议。


### 第二十七轮最终验收补记（2026-11-26）

- 提交：`a691f7eaedafdf96892c9613f3ae304e85f7047c`（main）。
- CI Run [45746342659](https://github.com/rexyll/cnc-knowledge/actions/runs/45746342659)两个Job均completed/success；全库191项unittest通过，CH12数控资源测试143项通过。
- `knowledge_lint.py --strict` 为PASS（0 errors）；Provider Mock self-check PASS，Artifact ID 15083925258。
- Provider适配器测试文件含64个测试方法定义；7条SAQ场景仍PROPOSED_NOT_APPROVED / NOT_RUN。没有真实Provider、跨进程协调或生产恢复风暴证据。


## CH17-T004 Provider持久化准入协调器第二十八轮

- 新增 `spare-parts-inventory-backup-provider-sqlite-coordinator-test-matrix-v1.csv`（ASSET-000072）：10条SQLite持久化准入、request_id幂等、多进程竞争和租约恢复场景；全部TRUE / PROPOSED_NOT_APPROVED / NOT_RUN。
- 新增KNOW-000042及SQLite协调器实现；仅验证同主机多进程共享本地数据库，不支持多主机或HA。


### 第二十八轮最终验收补记（2026-11-26）

- 修复提交 8d2a36b6240f20b1968a7e2ef148dcc02e745f88 对应CI Run [45748707053](https://github.com/rexyll/cnc-knowledge/actions/runs/45748707053)两个Job均completed/success；全库202项unittest、CH12资源143项通过，strict lint 0 errors。
- SQLite持久化协调器CLI self-check PASS，Artifact ID 15084821221；Provider Mock self-check PASS，Artifact ID 15084277008。
- 首轮文档同步Run 45748616308的SQLite CLI导入路径问题已在上述提交修复；新增11项SQLite协调测试全部包含于202项全库测试。ASSET-000072的10项场景仍未批准/未执行。


### 第二十八轮队列拒绝计数附加验收（2026-11-26）

- SQLite队列满时rejected_queue计数改在准入事务回滚后单独提交；新增回归保证活动租约不变、等待者无残留、拒绝计数递增。
- 最终Run [45749107843](https://github.com/rexyll/cnc-knowledge/actions/runs/45749107843)两个Job均completed/success；全库203项unittest、CH12资源143项通过，strict lint 0 errors。
- SQLite self-check Artifact ID 15083979275；Provider Mock self-check Artifact ID 15084203674。
- ASSET-000072现11条场景，全部PROPOSED_NOT_APPROVED / NOT_RUN。


## CH17-T004 Provider fencing 与 SQLite 备份恢复第二十九轮（2026-11-26）

- spare-parts-inventory-backup-provider-fencing-contract-test-matrix-v1.csv（ASSET-000073）：8条下游fencing合成场景，验证陈旧token拒绝、同token幂等/冲突和Provider能力缺失时fail-closed。
- spare-parts-inventory-backup-provider-sqlite-backup-restore-test-matrix-v1.csv（ASSET-000074）：8条本地SQLite备份/恢复合成场景，覆盖在线一致性快照、损坏拒绝、旧租约失效、等待者清理、外部高水位门禁与禁止覆盖。
- 两个矩阵的状态均为PROPOSED_NOT_APPROVED / NOT_RUN。内存Sink并非真实Provider；SQLite restore只准备新库，不覆盖原库、不执行切换；生产备份继续关闭。
- 配套正文：docs/17-operation-maintenance-and-repair/spare-parts-inventory-backup-provider-fencing-and-sqlite-recovery.md（KNOW-000043）。


## CH17-T004 Provider 适配器 fencing token 贯穿第三十轮（2026-11-26）

- spare-parts-inventory-backup-provider-adapter-fencing-test-matrix-v1.csv（ASSET-000075）：12条严格fencing合成场景，覆盖启动门禁、payload写入、multipart begin/part/complete、receipt-last、同备份包跨key scope和响应丢失幂等重放。
- 场景全部为PROPOSED_NOT_APPROVED / NOT_RUN。代码单元测试证明本地FencedMock集成，不构成真实Provider/供应商/生产验收。
- 严格模式启用参数为 BackupStorageAdapter(require_provider_fencing=True)；默认兼容模式不启用下游fencing。配套正文及知识条目：docs/17-operation-maintenance-and-repair/spare-parts-inventory-backup-provider-adapter-fencing-integration.md（KNOW-000044）。


## CH17-T004 SQLite fenced Provider 服务端参考实现第三十一轮（2026-11-26）

- 参考实现：scripts/spare_parts_provider_sqlite_fenced.py，配套 KNOW-000045。
- ASSET-000076：22条主体凭据、租户/前缀授权、原子fencing、multipart、恢复等参考验收场景，均PROPOSED_NOT_APPROVED / NOT_RUN。
- 数据库使用SQLite WAL/BEGIN IMMEDIATE，仅支持同主机本地文件和多进程共享；不支持NFS/SMB/多主机，也不是云Provider。
- 当前不验证Coordinator token来源签名；持有效Provider主体凭据的应用仍能构造高token。生产化前需scope-bound HMAC/signature attestation。恢复需要外部可信fencing floor，只准备新库，不自动切换。


## CH17-T004 Coordinator签名证明与密钥轮换第三十二轮

- 新增KNOW-000046 / scripts/spare_parts_fencing_attestation.py：Coordinator在活动lease下签发15秒默认TTL HMAC-SHA256 proof，绑定tenant、lease、scope、resource key、token、operation和idempotency key。
- Provider要求签名证明，并在写事务内检查trusted key registry；本地admin API支持新key登记、旧key RETIRING设置截止时间、REVOKED立即撤销。key secret不写SQLite。
- ASSET-000077：20条签名证明/密钥轮换参考场景，全部PROPOSED_NOT_APPROVED / NOT_RUN。
- CI Run 45758028329：全库248项、CH12 143项通过，strict lint 0 errors/5 warnings，Provider self-check PASS。
- HMAC为同机参考方案：Coordinator和Provider共享运行时secret；已签proof在lease release后仍有效至expiry（默认最多15秒）。生产远端Provider应改为非对称KMS签名并提供在线撤销。生产备份继续关闭。


## CH17-T004 Ed25519公钥验签与在线租约状态检查第三十三轮

- 新增KNOW-000047 / Ed25519 v2 fencing proof：Coordinator签名端可注入CallbackEd25519Signer，为KMS/HSM适配留出回调接口；未接入任何实际云KMS。
- Provider仅注入Ed25519公钥，数据库仅保存公钥SHA-256指纹和key状态，HMAC v1保留迁移兼容。
- Provider新增require_online_attestation_status和Coordinator lease状态checker；lease释放、过期或Coordinator状态查询故障时，Provider fail-closed。
- 在线状态查询和Provider写入使用两个不同SQLite数据库/事务，检查后到commit仍有TOCTOU窗口，不是线性一致即时撤销。
- ASSET-000078：22条Ed25519/在线撤销参考验收场景，均PROPOSED_NOT_APPROVED / NOT_RUN。
- 依赖cryptography==50.0.2；CI Run 45760844653全库252项、CH12 143项通过，strict lint 0 errors/5 warnings，Provider self-check PASS。
- 真实KMS/HSM、远程状态API、多主机和生产Provider未接入；生产备份继续关闭。

## CH17-T004 同库原子 lease 撤销与 Provider 写入顺序第三十四轮（2026-11-26）

- 新增KNOW-000048：SQLite Provider通过require_atomic_online_attestation_status启用同库原子在线lease状态检查。
- Coordinator在Provider已持有的BEGIN IMMEDIATE事务connection上检查lease；Provider对象/multipart、fencing high-water、幂等receipt和audit仍共享同一事务。
- Coordinator release使用同一SQLite文件时由单写事务锁串行化；Provider先持锁则先完成写入，release先提交则Provider拒绝已释放lease。
- SQLite官方依据登记为SRC-000391 Transaction和SRC-000392 WAL；WAL需要同机共享内存，不支持网络文件系统。
- ASSET-000079：12条场景全部PROPOSED_NOT_APPROVED / NOT_RUN；新增矩阵文件已归档于本目录。
- ASSET-000078的结构化实体记录本轮补齐；ASSET-000079实体记录同步建立。
- 本地参考实现不等于远程多主机/生产Provider验收；KMS/HSM与生产备份仍未启用。

### 第三十四轮CI最终验收补记

- 代码/资源Run 45762883991、文档同步Run 45762994591两个必需Job均completed/success。
- 全库254项unittest、CH12数值资源143项通过；strict knowledge lint 0 errors/5 warnings；知识结构与数据质量检查0 errors。
- Provider fenced Artifact 15091340011；Admission Coordinator Artifact 15090661225；Adapter Artifact 15090885721；治理readiness Artifact 15089609979。
- 仍属本机合成参考实现；ASSET-000079的12条形式化场景未批准/未执行，生产备份继续关闭。

## CH17-T004 远程Coordinator与对象存储Provider分布式fencing第三十五轮（2026-11-26）

- 新增KNOW-000049：一个scope control object保存monotonic fencing high-water、lease状态、operation sequence、receipt和当前manifest指针。
- payload先写入token/operation专属immutable staging key；只有control object通过ETag/generation CAS更新current manifest pointer才构成已发布备份。
- activation、revoke、manifest publish使用同一个control object CAS排序；CAS结果未知时强一致重读并按idempotency/receipt恢复。
- 新增ASSET-000080：20条形式化参考场景，全部PROPOSED_NOT_APPROVED / NOT_RUN。
- SRC-000393～SRC-000396分别登记S3 Conditional Writes、GCS Request Preconditions、Azure Blob ETag concurrency及跨Blob事务边界官方资料。
- 本轮仅有单进程InMemoryConditionalObjectControlStore参考模型；无真实AWS/GCS/Azure SDK、远程Coordinator、KMS/HSM或多主机验证。

### 第三十五轮最终文档CI验收

- [Run 45767658789](https://github.com/rexyll/cnc-knowledge/actions/runs/45767658789)两个必需Job success；全库268项unittest、CH12 143项测试通过；strict lint 0 errors/5 warnings；知识结构与数据质量0 errors。
- Artifacts：CH12 S-curve 15091879973；Adapter 15093210029；Admission 15092029877；SQLite Provider 15092204228；治理readiness 15092980848。
- ASSET-000080 20条场景仍PROPOSED_NOT_APPROVED / NOT_RUN；无真实云SDK/远程Coordinator/多主机验收，生产备份继续关闭。


## CH17-T004 Coordinator持久权威与故障恢复第三十六轮（2026-11-26）

- `spare-parts-inventory-backup-provider-coordinator-authority-test-matrix-v1.csv`（ASSET-000081）：16条本地合成参考场景，涵盖租户scope命名空间、token/operation sequence单调与幂等、activation/revocation两阶段Provider读回、完整publish receipt、Leader epoch接管、旧Leader拒绝及外部恢复高水位；全部PROPOSED_NOT_APPROVED / NOT_RUN。
- 新增代码参考位于`scripts/spare_parts_provider_coordinator_authority.py`，专项测试位于`tests/test_spare_parts_provider_coordinator_authority.py`。代码与测试不是实物资源/企业测试报告；SQLite WAL仅支持同机本地文件系统，不支持NFS/SMB多主机。
- 关联正文：`docs/17-operation-maintenance-and-repair/spare-parts-inventory-backup-provider-coordinator-durable-authority-and-recovery.md`；实体KNOW-000050、ASSET-000081；来源复用SRC-000391/392。


- 第三十六轮代码/文档同步CI Run 45769331991 / 45769584662均通过；全库283项unittest、CH12 143项数值资源测试通过，strict lint 0 errors/5 warnings，结构质量0 errors。ASSET-000081场景仍全部未批准/未执行；CI自检不等于多主机、云Provider或企业灾备验收。


## CH17-T004 Coordinator 后端契约与 etcd v3 适配第三十七轮（2026-11-26）

- `spare-parts-inventory-backup-provider-coordinator-backend-conformance-matrix-v1.csv`（ASSET-000082）：20条合成参考场景，覆盖linearizable Range、Txn Compare/Then/Else、Lease、LeaderKey revision fencing、quorum loss、Watch、OUTCOME_UNKNOWN和Provider CAS；全部PROPOSED_NOT_APPROVED / NOT_RUN。
- 代码：`scripts/spare_parts_provider_authority_store.py`；测试：`tests/test_spare_parts_provider_authority_store.py`。EtcdV3Client仅为注入式客户端协议，InMemoryEtcdV3Client是单进程测试替身；未连接etcd server。
- 关联正文：`docs/17-operation-maintenance-and-repair/spare-parts-inventory-backup-provider-coordinator-backend-contract-and-etcd-v3.md`；实体KNOW-000051、ASSET-000082；来源SRC-000397～SRC-000401。


- 第三十七轮最终代码/文档CI Run 45770717942 / 45770955018均通过：全库300项unittest、CH12 143项数值资源测试通过，strict lint 0 errors/5 warnings，知识结构质量0 errors。ASSET-000082矩阵20条场景仍PROPOSED_NOT_APPROVED / NOT_RUN；没有真实etcd、多主机/quorum或云Provider证据。


## CH17-T004 Coordinator 事务内有序读取（第三十八轮）

- `spare-parts-inventory-backup-provider-coordinator-transactional-read-matrix-v1.csv`（ASSET-000083）：16条合成契约场景，覆盖Txn分支内Get/Put/Delete顺序、失败分支读取、etcd Txn响应对齐、revision、Lease和OUTCOME_UNKNOWN；全部 `PROPOSED_NOT_APPROVED / NOT_RUN`。
- 代码位于 `scripts/spare_parts_provider_authority_store.py`，专项测试位于 `tests/test_spare_parts_provider_authority_store.py`。新增2个测试方法并分别在SQLite与内存etcd test double上执行，共4次适配器测试执行。
- 关联正文KNOW-000052；复用SRC-000397/398（etcd API）与SRC-000391/392（SQLite Transaction/WAL）。该轮未连接真实etcd集群，未迁移SQLite领域状态机及Admission lease数据源。


- 第三十八轮文档同步CI Run 45772844275两个必需Job均completed/success（提交 a1548dad6ad1c47d4645600a162a866076de6993）；全库304项unittest、CH12 143项数值资源测试通过，strict lint 0 errors/5 warnings，知识结构与数据质量0 errors。ASSET-000083的16项场景仍PROPOSED_NOT_APPROVED / NOT_RUN。


## CH17-T004 Admission Lease Authority统一事务存储（第三十九轮）

- `spare-parts-inventory-backup-provider-admission-lease-authority-matrix-v1.csv`（ASSET-000084）：20条合成参考场景，覆盖单调fencing token、request_id幂等、backend TTL、续租迁移、释放tombstone、authority同Txn guard和OUTCOME_UNKNOWN；全部 `PROPOSED_NOT_APPROVED / NOT_RUN`。
- 代码：`scripts/spare_parts_provider_admission_authority_store.py`；测试：`tests/test_spare_parts_provider_admission_authority_store.py`；关联知识KNOW-000053，复用SRC-000391/392/397/398。
- 该组件仅负责Admission lease lifecycle，不是完整Admission scheduler；旧SQLite等待队列、fair scheduling、全局/租户capacity quota及SQLite Coordinator领域表尚未迁移，不可分库双写。


- 第三十九轮文档同步CI Run 45776156101两个必需Job均completed/success（提交 b79aede8a06cc55ac60681cbfc9acf03b1f44a55）；全库314项unittest、CH12 143项数值资源测试通过，strict lint 0 errors/5 warnings，知识结构与数据质量0 errors。ASSET-000084的20项场景仍PROPOSED_NOT_APPROVED / NOT_RUN。


- 第三十九轮最终元数据CI Run 45776292616两个必需Job均completed/success；全库314项unittest、CH12 143项数值资源测试通过，strict lint 0 errors/5 warnings，知识结构与数据质量0 errors。ASSET-000084的20项场景仍PROPOSED_NOT_APPROVED / NOT_RUN。


## CH17-T004 Unified Admission Scheduler与配额状态统一事务（第四十轮）

- `spare-parts-inventory-backup-provider-unified-admission-scheduler-matrix-v1.csv`（ASSET-000085）：24条合成参考场景，覆盖单aggregate CAS、global/tenant quota、跨domain waiter公平调度、max_waiters、TTL、renew/release、同Txn authority guard和迁移边界；全部 `PROPOSED_NOT_APPROVED / NOT_RUN`。
- 代码：`scripts/spare_parts_provider_unified_admission_store.py`；专项测试：`tests/test_spare_parts_provider_unified_admission_store.py`；新增6个测试方法，SQLite与InMemoryEtcdV3Client分别运行，共12次适配器测试执行。
- 关联正文KNOW-000054；复用SRC-000391/392/397/398。统一scheduler使用独立 `/cnc/admission/unified/v1/` namespace；不能与旧SQLite scheduler或第三十九轮独立Lease Authority对同一业务范围并行写入。


- 第四十轮文档同步CI Run 45778328441两个必需Job均completed/success（提交 87d749147d2c32da547ce23ed56db69725271a00）；全库328项unittest、CH12 143项数值资源测试通过，strict lint 0 errors，知识结构与数据质量0 errors（5条非阻断warning）。ASSET-000085的24项场景仍PROPOSED_NOT_APPROVED / NOT_RUN。


- 第四十轮文档同步CI Run 45778328441两个必需Job均completed/success（提交 87d749147d2c32da547ce23ed56db69725271a00）；全库328项unittest、CH12 143项数值资源测试通过，strict lint 0 errors，知识结构与数据质量0 errors（5条非阻断warning）。ASSET-000085的24项场景仍PROPOSED_NOT_APPROVED / NOT_RUN。


## CH17-T004 Unified Coordinator Authority统一事务（第四十一轮）

- `spare-parts-inventory-backup-provider-unified-coordinator-authority-matrix-v1.csv`（ASSET-000086）：35条场景覆盖Leader TTL/epoch、recovery floor、tenant scope fencing、ACTIVATE/REVOKE/PUBLISH、publish sequence、proof授权和Admission同事务比较；全部 `PROPOSED_NOT_APPROVED / NOT_RUN`。
- 代码：`scripts/spare_parts_provider_unified_coordinator_authority.py`；测试：`tests/test_spare_parts_provider_unified_coordinator_authority.py`；8个测试方法在SQLite与InMemoryEtcdV3Client各执行一次，共16次适配器测试执行。
- 关联KNOW-000055；统一Admission aggregate升级为schema v2，namespace `/cnc/admission/unified/v2/`。旧SQLite Coordinator/Admission仍未迁移，禁止双写。


- 第四十一轮最终代码提交 `3d79149c1112550b4fb25efbe02b5f536b08cacd`，CI Run 45810737444两个必需Job均completed/success；全库344项unittest、CH12 143项数值资源测试通过，strict lint与结构质量均0 errors。ASSET-000086的35条场景仍PROPOSED_NOT_APPROVED / NOT_RUN。


- 第四十一轮文档同步CI Run 45811108498两个必需Job均completed/success（提交 706cfcf36204c1bfe996501e65031a21e8536783）；全库344项unittest、CH12 143项数值资源测试通过，strict lint 0 errors，知识结构与数据质量0 errors（5条非阻断warning）。ASSET-000086的35项场景仍PROPOSED_NOT_APPROVED / NOT_RUN。


- 第四十一轮文档同步CI Run 45811108498两个必需Job均completed/success（提交 706cfcf36204c1bfe996501e65031a21e8536783）；全库344项unittest、CH12 143项数值资源测试通过，strict lint 0 errors，知识结构与数据质量0 errors（5条非阻断warning）。ASSET-000086的35项场景仍PROPOSED_NOT_APPROVED / NOT_RUN。


- 第四十一轮文档同步CI Run 45811108498两个必需Job均completed/success：344项全库unittest、CH12 143项数值资源测试通过，strict lint与结构质量均0 errors（5条非阻断warning）。ASSET-000086的35项场景仍PROPOSED_NOT_APPROVED / NOT_RUN。


## CH17-T004 Unified Coordinator Aggregate容量画像（第四十二轮）

- 新增 spare-parts-coordinator-capacity-profile-v1.csv（ASSET-000087），包含14条合成负载定义，覆盖scope、operation、active lease、waiter和混合负载。
- 离线探针位于 scripts/spare_parts_coordinator_capacity_probe.py；运行后只向stdout输出JSON，不修改仓库文件，不连接任何store或etcd集群。
- CSV是合成输入矩阵，不是实测报告；ASSET-000087保持PROPOSED_NOT_APPROVED，自动化测试也不替代企业批准或真实etcd容量验收。


第四十二轮离线容量探针实现提交 `f52937e1af7b622c11801e2ca502661365e75d05`；CI Run 45814052446两个必需Job均通过。全库356项unittest、CH12 143项数值资源测试通过，strict lint与结构质量均0 errors（5项非阻断warning）。14个profile已在CI合成测试中执行；CSV本身不含真实性能测量，ASSET-000087仍待企业批准，真实etcd容量验收未执行。


## CH17-T004 Operation Ledger生命周期与安全归档（第四十三轮）

- 新增 spare-parts-coordinator-operation-ledger-archive-test-matrix-v1.csv（ASSET-000088），包含25条待批准/未执行场景，覆盖归档准入、pending保护、幂等、CAS、manifest链、恢复及物理删除边界。
- 协议正文位于 docs/17-operation-maintenance-and-repair/spare-parts-inventory-backup-provider-operation-ledger-archival.md（KNOW-000057）；纯内存参考模型位于 scripts/spare_parts_operation_ledger_archive.py，单元测试位于 tests/test_spare_parts_operation_ledger_archive.py。
- CSV是形式化场景定义，不包含企业执行结果；ASSET-000088保持PROPOSED_NOT_APPROVED / NOT_RUN。参考模型不连接真实etcd或对象存储，不启用生产归档。


第四十三轮归档协议参考模型最终测试head 4ed91a04138e30ecf2275c07bb947ecc872fadd2；[CI Run 45817146500](https://github.com/rexyll/cnc-knowledge/actions/runs/45817146500)两个必需Job均通过。全库380项unittest、CH12 143项数值资源测试通过，strict lint和知识结构质量均0 errors。新增24项归档模型测试通过；ASSET-000088的25项正式场景仍待企业批准/执行，不等同于生产归档验收。


## CH17-T004 Archive Index与Schema v3迁移/回滚（第四十四轮）

- 新增 spare-parts-coordinator-archive-index-schema-v3-migration-matrix-v1.csv（ASSET-000089），包含47项待企业批准/执行场景，覆盖精确索引回填/增量/hit/miss、完整性故障、V2冻结、V3候选校验、cutover和写入前后回滚。
- 文档为 docs/17-operation-maintenance-and-repair/spare-parts-inventory-backup-provider-archive-index-and-schema-v3-migration.md（KNOW-000058）。
- 参考实现：scripts/spare_parts_operation_archive_index.py 与 scripts/spare_parts_coordinator_schema_migration.py；对应测试均为内存模型。ASSET-000089仍PROPOSED_NOT_APPROVED / NOT_RUN，不表示真实集群迁移已获批准。


第四十四轮精确Archive Index与Schema v3迁移/回滚参考模型最终head `2b66224909d2bcd9b326c1cffcf220bef5d14b7f`；[CI Run 45819520749](https://github.com/rexyll/cnc-knowledge/actions/runs/45819520749)两个必需Job均通过。全库426项unittest、CH12 143项数值资源测试通过，strict lint和结构质量均0 errors。本轮新增46项内存参考模型单测已通过；ASSET-000089的47项正式场景仍待企业批准/执行，未连接真实etcd或对象存储。


## CH17-T004 Coordinator Schema v3分片准入与事务预算（第四十五轮）

- 设计文档：docs/17-operation-maintenance-and-repair/spare-parts-inventory-backup-provider-coordinator-v3-sharded-admission-and-transaction-budget.md（KNOW-000059）。
- 参考实现：scripts/spare_parts_provider_admission_partition_model.py；36项测试：tests/test_spare_parts_provider_admission_partition_model.py。
- 新增正式场景矩阵：spare-parts-coordinator-v3-sharded-admission-transaction-matrix-v1.csv（ASSET-000090），54项均PROPOSED_NOT_APPROVED / NOT_RUN。
- 新增来源SRC-000406记录etcd Lease到期或撤销时附着key被删除的语义。所有内容仍是纯内存/设计参考，未连接真实etcd或生产多主机Coordinator。


第四十五轮分片准入与事务预算参考模型最终head \`a035cdf1f82e6ea9274195b2872953e9f12e83ba\`；[CI Run 45823628905](https://github.com/rexyll/cnc-knowledge/actions/runs/45823628905)两个必需Job均通过。全库462项unittest、CH12 143项数值资源测试通过；strict lint与结构质量均0 errors。本轮36项内存参考模型单测通过；ASSET-000090的54项正式场景仍待企业批准/执行，未连接真实etcd或多主机Dispatcher。


第四十五轮最终 Fencing floor 补强提交 e8a4fb4c91bac3b279c5a0f8a06d3ae121da75a1；同一有效Leader观察到更高external high-water时，废弃未使用的token range并从新高水位之后重新分配。最终 [CI Run 45824510175](https://github.com/rexyll/cnc-knowledge/actions/runs/45824510175)通过：全库463项、CH12 143项测试全部通过，strict lint和结构质量0 errors；本轮37项参考模型测试已通过。真实etcd/多主机验收未执行，54项正式场景仍待批准/执行。


## CH17-T004 etcd Watch、Range恢复与多客户端故障注入（第四十六轮）

- 设计：docs/17-operation-maintenance-and-repair/spare-parts-inventory-backup-provider-coordinator-etcd-watch-range-recovery-and-multi-client-fault-injection.md（KNOW-000060）。
- 实现增量：scripts/spare_parts_provider_authority_store.py，补充可选Watch和linearizable_range；保留原KV/Txn/Lease接口。
- 测试：tests/test_spare_parts_provider_authority_store_watch.py，21项新增测试，使用共享单进程InMemoryEtcdV3WatchClient和两个独立EtcdV3CoordinatorAuthorityStore实例。
- 资源：spare-parts-coordinator-etcd-watch-multi-client-fault-injection-matrix-v1.csv（ASSET-000091），30条正式场景均PROPOSED_NOT_APPROVED / NOT_RUN；SRC-000407记录etcd v3.7 Watch API revision/compaction/fragment语义。
- 未连接真实etcd、未构造gRPC driver、未验证Raft quorum或多主机故障；Watch只用于通知，权威读取仍必须线性一致Range/Txn。


第四十六轮Watch/Range与多客户端故障注入参考模型最终head `cdaff0dc43834b3250d8803efb0591a8656c363d`；[CI Run 45826709629](https://github.com/rexyll/cnc-knowledge/actions/runs/45826709629)两个必需Job均通过：全库484项unittest、CH12 143项数值资源测试通过，strict lint和结构质量0 errors。本轮21项新增测试通过；真实etcd/多主机验证未执行，30项正式场景仍待批准/执行。


## CH17-T004 etcd3gw驱动与三节点集成（第四十七轮）

- 技术正文：docs/17-operation-maintenance-and-repair/spare-parts-inventory-backup-provider-coordinator-etcd3gw-driver-and-three-node-integration.md（KNOW-000061）。
- 驱动：scripts/spare_parts_provider_etcd3gw_driver.py；requirements-ch17-etcd-integration.txt固定etcd3gw 2.7.0；仅实现KV Range/Txn/Lease，不开放Watch。
- 测试：tests/test_spare_parts_provider_etcd3gw_driver.py（10项fake gateway契约测试）；tests/test_spare_parts_provider_authority_store_etcd_integration.py（5项基础真实测试）+ tests/test_spare_parts_provider_authority_store_member_outage_etcd_integration.py（1项单成员故障真实测试）；第四十八/四十九轮已在Run 45839556952与45840903997执行；当前7项live集成测试在Run 45840903997全部通过（含单成员故障、双成员失去quorum及恢复）。
- 集成环境：scripts/etcd-integration/compose.yaml、run.sh；etcd v3.7.0三节点可丢弃拓扑，已由Run 45835646908与45839556952在CI实际启动并在结束时清理。
- 矩阵：spare-parts-coordinator-etcd-driver-integration-matrix-v1.csv（ASSET-000092），30项均PROPOSED_NOT_APPROVED / NOT_RUN。


- **最终CI：** `871fe0d2673fb1b39502236568dc7dd57ad3bef0`；[Run 45832644686](https://github.com/rexyll/cnc-knowledge/actions/runs/45832644686)两个必需Job均completed/success。全库499项unittest完成，494项通过、5项跳过（5项需ETCD_INTEGRATION=1的live etcd集成测试）；CH12 143项数值测试通过；strict knowledge lint 0 errors；独立的CH17合成夹具校验为0 errors、5 warnings。5项均为既有治理门禁提示：数据集仍为DRAFT、未批准企业测试环境、未批准企业测试级别、30项SPAT源测试案例仍NOT_RUN、manifest checksum pending；并非etcd驱动测试失败。
- **第四十八轮实测：** [Live CI Run 45839556952](https://github.com/rexyll/cnc-knowledge/actions/runs/45839556952)在真实三成员etcd v3.7.0临时集群上执行7项live测试，7/7 PASS；其中单成员停机后剩余多数派完成线性一致Range/Txn写入/读回，节点重启后恢复三成员。诊断Artifact 15127610627。
- **默认CI：** [Run 45839557095](https://github.com/rexyll/cnc-knowledge/actions/runs/45839557095)全库500项unittest（494通过、6项live opt-in测试按默认策略skip），CH12 143项通过，strict lint 0 errors。
- **边界：** ASSET-000092的30项正式场景仍PROPOSED_NOT_APPROVED / NOT_RUN；本轮仅覆盖一次性环境下单成员故障，未覆盖2成员失去quorum/网络分区、性能、mTLS/RBAC或多主机；SQLite Coordinator未迁移，schema-v2仍为唯一生产权威；CH17-T004继续IN_PROGRESS。

## CH17-T004 etcd 单成员故障与多数派读写实测（第四十八轮，2026-11-26）

- 新增真实故障集成测试：`tests/test_spare_parts_provider_authority_store_member_outage_etcd_integration.py`。
- 运行过程：停止etcd1；使用[Run 45839556952](https://github.com/rexyll/cnc-knowledge/actions/runs/45839556952)验证不可达首endpoint的linearizable Range failover、剩余2/3多数派事务写入及线性一致读回；重启etcd1并确认三成员恢复。
- 结果：6项live integration测试全部PASS（6/6），0失败、0跳过；CI成功清理临时容器、volume和network。诊断Artifact [15127610627](https://github.com/rexyll/cnc-knowledge/actions/runs/45839556952/artifacts/15127610627)，SHA-256 `74b04904535cce72b7a08fdf6265020bcb9086b43003106ab4eb4271847869f2`。
- 默认回归[Run 45839557095](https://github.com/rexyll/cnc-knowledge/actions/runs/45839557095)通过：全库500项unittest（494通过、6项opt-in skip），CH12 143项数值测试通过，strict lint 0 errors。
- 这只是一次性CI集成验证，正式矩阵ASSET-000092的30项场景仍PROPOSED_NOT_APPROVED / NOT_RUN；没有验证2成员同时故障、网络分区、吞吐/延迟、mTLS/RBAC、生产Coordinator或多主机部署。
## CH17-T004 etcd 双成员故障、失去多数派与恢复实测（第四十九轮，2026-11-26）

- 新增真实故障集成测试：`tests/test_spare_parts_provider_authority_store_quorum_loss_etcd_integration.py`。
- 在一次性三成员集群停止etcd1和etcd2，验证etcd3单独存活但没有quorum时线性一致读失败关闭、Txn不报告成功；随后恢复两个节点，确认成员数与Leader恢复、目标key仍不存在，再成功执行CAS写入和线性一致读回。
- [Live CI Run 45840903997](https://github.com/rexyll/cnc-knowledge/actions/runs/45840903997)：7/7真实集成测试PASS，0 failures、0 skips；容器、volume、network清理成功。诊断Artifact [15128755397](https://github.com/rexyll/cnc-knowledge/actions/runs/45840903997/artifacts/15128755397)，SHA-256 `d326119ddda7cc64a1cf3e14fbefc83e21d4693b25d2b9d870604bbee28747b8`。
- 默认回归[Run 45840904137](https://github.com/rexyll/cnc-knowledge/actions/runs/45840904137)：全库501项unittest（494通过、7项opt-in live测试按默认策略skip），CH12 143项数值测试通过，strict lint 0 errors，fixture validator 0 errors/5项既有warning。
- 边界：仅验证这套一次性三成员环境下的受控双成员停止/恢复；不代表长时间网络分区、非对称分区、磁盘损坏、生产可用性/性能、TLS/RBAC或多主机Coordinator验收。ASSET-000092的30项正式场景继续PROPOSED_NOT_APPROVED / NOT_RUN。
## CH17-T004 etcd Watch Gateway 流式包络保真（第五十轮，2026-11-26）

- 驱动：`scripts/spare_parts_provider_etcd3gw_driver.py` 增加 `Etcd3gwV3Client.watch()` 和可关闭的响应迭代器；通过当前配置的 HTTP session 访问 `/v3/watch`，增量解码任意 chunk 边界的 JSON 流。
- 字段保真：header revision、watch_id、created/canceled、compact_revision、cancel_reason、fragment、PUT/DELETE 事件与 KV/prev_kv；缺省 proto3 event type 按默认 PUT 处理。WatchCreate 支持 progress_notify，但没有后续双向 WatchProgress/WatchCancel 消息；close 只关闭 HTTP 流，不伪造 cancel ack。
- Fake Gateway 测试：`tests/test_spare_parts_provider_etcd3gw_driver.py` 现 13 项契约测试，覆盖拆帧、全字段、二进制、prev_kv、启动 failover、断线和资源释放。
- Live 测试：`tests/test_spare_parts_provider_authority_store_etcd_integration.py` 新增真实 Watch 事件测试；连同原 5 项、单成员故障、双成员 quorum-loss 场景合计 8 项。真实 [Run 45842517310](https://github.com/rexyll/cnc-knowledge/actions/runs/45842517310) 在一次性三成员 etcd v3.7.0 集群 8/8 PASS；诊断 Artifact [15128407498](https://github.com/rexyll/cnc-knowledge/actions/runs/45842517310/artifacts/15128407498)，SHA-256 `9c45a263c409f9f7eb808670df14c5a7f7455f8cea85ad0cadec5d053699ccb9`。
- 默认 CI：[Run 45842517156](https://github.com/rexyll/cnc-knowledge/actions/runs/45842517156) 全库 505 项 unittest，497 通过、8 项 live 测试按默认策略 skip；CH12 143 项通过；strict knowledge lint 0 errors；结构/数据校验 0 errors、5 项既有 warning。
- 边界：不支持双向 WatchProgress/WatchCancel 和服务端 cancel 确认；未测试 mTLS/RBAC、长期流背压、网络分区、性能或多主机；ASSET-000092 的 30 项正式场景仍 PROPOSED_NOT_APPROVED / NOT_RUN。


## 第五十一轮：etcd Gateway mTLS（2026-11-27）

- 新增`scripts/etcd-integration/compose-mtls.yaml`及`run-mtls.sh`，使用临时CA/server/client证书启动独立三成员TLS集群；证书和私钥只存在runner临时目录，job结束清理。
- Live CI [Run 45918152363](https://github.com/rexyll/cnc-knowledge/actions/runs/45918152363)：mTLS 3/3 PASS（有效证书成员发现+CAS写读、无客户端证书拒绝、错误CA拒绝）；Artifact 15163390323，SHA-256 `91014d3f47cf09152dd81488231494fdc04afc675b428cdad3e0556cf00aac74`。
- 默认 CI [Run 45918152436](https://github.com/rexyll/cnc-knowledge/actions/runs/45918152436)：508项unittest、CH12 143项通过；strict lint 0 errors；结构/数据0 errors、5项既有warning。
- 边界：不是企业PKI、证书轮换/吊销、生产密钥托管或RBAC验收；ASSET-000092的30项正式场景仍PROPOSED_NOT_APPROVED / NOT_RUN。


## 第五十二轮：etcd Gateway RBAC 与最小权限（2026-11-27）

- 新增`tests/test_spare_parts_provider_authority_store_rbac_mtls_etcd_integration.py`；Etcd3gwV3Client可显式接收auth_token并将Authorization头应用于每个endpoint session。
- Live [Run 45919206834](https://github.com/rexyll/cnc-knowledge/actions/runs/45919206834)：普通三成员suite 8项通过；mTLS suite 8/8（基础mTLS 3 + RBAC 5）通过，覆盖reader只读prefix、writer读写prefix、越权访问拒绝、无token/错误密码失败。Artifact 15163741056，SHA-256 `b7e7476a08e1e9c4a77e4bb02e2b80727dd09e1baadc1b66866b6a54b72c8ee0`。
- Gateway client cert采用无CN证书，仍由CA签名并强制mTLS；RBAC用户名/密码认证换取token，避免使用Gateway不支持的证书CN用户映射。
- 默认 [Run 45919206886](https://github.com/rexyll/cnc-knowledge/actions/runs/45919206886)：515项unittest（499通过、16项opt-in skip），CH12 143项，strict lint 0 errors，结构/数据0 errors、5项既有warning。
- 限制：token自动刷新/续期、企业IAM、审计、生产密钥托管未验证；ASSET-000092正式30项仍PROPOSED_NOT_APPROVED / NOT_RUN。



## 第五十三轮：etcd Authentication Token 生命周期（2026-11-27）

- 本轮没有新增需长期归档的证书、密钥或第三方文档副本；官方资料采用链接元数据方式登记为SRC-000410（v3.7配置与simple token TTL）、SRC-000411（认证设计与simple/JWT差异）、SRC-000412（RBAC范围与Gateway限制）。
- 短TTL集成环境在CI runner临时生成CA/客户端证书/密码/token，运行结束清理；不得将这些临时凭据或日志中的敏感值复制到资源目录。
- 本轮代码交付为显式token更新接口和短TTL测试，不代表生产自动刷新、企业IAM或凭据轮换已实现。


### 第五十三轮 CI 验收结果（2026-11-27）

- [Live Run 45920726761](https://github.com/rexyll/cnc-knowledge/actions/runs/45920726761)成功：基础三成员suite 6项、mTLS/RBAC suite 8项、独立10秒simple-token生命周期测试1项均通过；Artifact [15164208273](https://github.com/rexyll/cnc-knowledge/actions/runs/45920726761/artifacts/15164208273)，SHA-256 `0b66c69eb7f1ecc12e0d8bfbbf80ab0bf51de739ec31d8d2e9f3db878619e476`。
- [Quality Run 45920726730](https://github.com/rexyll/cnc-knowledge/actions/runs/45920726730)两个Job成功：全库518项unittest（501 passed、17项opt-in skip），CH12 143项通过，strict knowledge lint 0 errors。
- token过期后请求拒绝、重新认证获取新token、同步更新所有endpoint Authorization header、KV Range和Watch created握手通过；runner清理临时证书、token及Compose volumes。
- 本轮只提供显式token更新，不包含自动刷新；ASSET-000092正式30项仍PROPOSED_NOT_APPROVED / NOT_RUN。


### 第五十四轮验证记录（2026-11-27）

- Live [Run 45922792420](https://github.com/rexyll/cnc-knowledge/actions/runs/45922792420)成功：基础三节点/成员故障/quorum suite 8项、mTLS/RBAC suite 12项、短TTL token 1项、认证/quorum隔离1项全部通过；Artifact 15165755534，SHA-256 `c3b8d8e25e91cc7bff7e3d2893a55688de0b2567836052a20cb887fd2bcc7608`。
- 多数派丢失期间，已有token的线性一致Range超时，重新认证RPC也超时；恢复成员和多数派后，旧token再次成功Range。不能将该结果解读为认证服务在无quorum时独立可用。
- 默认质量[Run 45922792429](https://github.com/rexyll/cnc-knowledge/actions/runs/45922792429)成功：526项unittest（504通过、22项opt-in skip），CH12 143项，strict lint 0 errors，fixture validator 0 errors/5项既有warning。
- 所有凭据、token、证书和Compose volumes均由runner临时创建并清理；没有提交密钥。


### 第五十五轮：mTLS/RBAC 单成员故障与Token恢复证据

- 测试源文件：`tests/test_spare_parts_provider_authority_store_member_outage_auth_etcd_integration.py`；CI工作流：`.github/workflows/ch17-etcd-live-integration.yml`。
- Live [Run 45927091505](https://github.com/rexyll/cnc-knowledge/actions/runs/45927091505)全部阶段成功；新增单成员故障测试1/1通过。Artifact [15167295428](https://github.com/rexyll/cnc-knowledge/actions/runs/45927091505/artifacts/15167295428)，SHA-256 `2f06dbcea1b1e69bf9dfcf2666bfedff3811321aa8a8dd1474181c88b75e7aff`。
- 观测：Token签发后即时和收敛后均3/3成员接受；停止etcd1时只读Range经transport failover成功；重启后旧Token在etcd1返回401；从etcd2显式重新认证后新Token在3/3成员接受。
- runner已将mTLS Compose成员日志/状态写入runner临时诊断目录并纳入Artifact；临时证书、私钥、密码、Token和Compose volumes在runner退出时清理。
- 默认质量[Run 45927138505](https://github.com/rexyll/cnc-knowledge/actions/runs/45927138505)通过：527项unittest（504 passed、23 skipped）、CH12 143项、strict lint 0 errors；正式ASSET-000092 30项仍PROPOSED_NOT_APPROVED / NOT_RUN。


## CH17-T004 etcd 多数派网络分区与隔离成员恢复（第五十六轮）

- 新增真实集成测试 `tests/test_spare_parts_provider_authority_store_network_partition_etcd_integration.py`，通过Compose标签校验隔离对象，仅断开一次性CI集群etcd1与专用网络的连接。
- [Live Run 45929955634](https://github.com/rexyll/cnc-knowledge/actions/runs/45929955634)成功；少数派本地线性一致Range/Put失败，多数派etcd2/etcd3完成Coordinator Store CAS写入和读回；finally恢复网络后，etcd1读到多数派提交的数据。专项测试1/1 PASS（8.248秒），Artifact [15168271744](https://github.com/rexyll/cnc-knowledge/actions/runs/45929955634/artifacts/15168271744)。
- [Knowledge Quality Run 45930090004](https://github.com/rexyll/cnc-knowledge/actions/runs/45930090004)两个Job成功：528项unittest（504通过、24跳过）、CH12 143项、strict lint 0 errors/5项既有warning，结构/最终自检0 errors。
- 该证据只覆盖一次性etcd v3.7.0/Compose三成员网络分区，不覆盖Driver层的少数派endpoint failover及Txn `OUTCOME_UNKNOWN` 语义；后续第五十七轮专门验证。ASSET-000092正式30项仍 `PROPOSED_NOT_APPROVED / NOT_RUN`。


## CH17-T004 少数派分区下Driver读取故障转移与Txn结果核验（第五十七轮）

- Live [Run 45931474359](https://github.com/rexyll/cnc-knowledge/actions/runs/45931474359)成功；网络分区测试文件2项PASS（8.670秒）。只读Range从隔离etcd1 endpoint `127.0.0.1:23791`切换到健康多数派`127.0.0.1:23792`成功；少数派CAS Txn只发送一次，结果`OUTCOME_UNKNOWN/ConnectionError`。
- 网络恢复后线性一致读回为`not-committed`，未重放事务。Live后续mTLS、Token生命周期、quorum隔离、RBAC成员故障/Token传播和清理步骤全部成功；Artifact [15168243294](https://github.com/rexyll/cnc-knowledge/actions/runs/45931474359/artifacts/15168243294)。
- Quality [Run 45931474322](https://github.com/rexyll/cnc-knowledge/actions/runs/45931474322)成功：529 unittest（504通过、25跳过），CH12 143项，strict lint 0 errors/5 warnings，结构自检0 errors。
- 工程测试没有模拟已提交后响应丢失的精确窗口；ASSET-000092正式30项仍`PROPOSED_NOT_APPROVED / NOT_RUN`。下一轮验证少数派下Lease KeepAlive、自然到期和Leader fencing。


## CH17-T004 少数派Lease KeepAlive失败、自然过期与Leader fencing（第五十八轮）

- Live [Run 45933111643](https://github.com/rexyll/cnc-knowledge/actions/runs/45933111643)整体成功；Lease专项1/1 PASS（14.526秒）。KeepAlive客户端配置全部3个endpoint，但隔离后只触达etcd1 `127.0.0.1:23791` 一次，Store返回`AuthorityStoreUnavailableError`，没有自动切换多数派续租。
- 多数派Lease TTL从7秒降至5秒；Lease自然过期后TTL=-1，线性一致Range确认旧authority key已删除。新Leader epoch从1提升至2；旧epoch fencing CAS失败，新epoch写成功，恢复成员读到epoch 2。
- 诊断Artifact [15169352034](https://github.com/rexyll/cnc-knowledge/actions/runs/45933111643/artifacts/15169352034)。
- Quality [Run 45933111606](https://github.com/rexyll/cnc-knowledge/actions/runs/45933111606)成功：530 unittest（504通过、26跳过），CH12 143项，strict lint 0 errors/5项既有warning，结构自检0 errors。
- 此证据只验证一次性etcd集群和KV compare fencing，不证明SQLite业务Coordinator已经迁移或生产HA验收。ASSET-000092正式30项仍`PROPOSED_NOT_APPROVED / NOT_RUN`。下一轮验证LeaseRevoke未知结果与恢复后核对。


## CH17-T004 LeaseRevoke少数派分区与恢复核对（第五十九轮）

- [Live Run 45936468822](https://github.com/rexyll/cnc-knowledge/actions/runs/45936468822)成功；新增LeaseRevoke分区测试1/1 PASS。首个Revoke请求只触达隔离的etcd1 `127.0.0.1:23791`一次，Store返回`AuthorityStoreOutcomeUnknownError`，没有failover或重放。
- 恢复网络后，多数派首次核对发现原Lease和authority key仍存在、key revision仍为16，判定首次请求未提交；记录结果后显式通过健康多数派Revoke清理，key删除revision推进至17，TTL最终为-1。Artifact [15170653184](https://github.com/rexyll/cnc-knowledge/actions/runs/45936468822/artifacts/15170653184)。
- [Quality Run 45936468828](https://github.com/rexyll/cnc-knowledge/actions/runs/45936468828)：533 unittest（506 passed、27 skipped），CH12 143项，strict lint 0 errors/5既有warning，结构校验0 errors。SPAT 30项仅离线模拟、business_test_status仍NOT_RUN。
- supporting evidence不代表精确的“撤销已提交但响应丢失”窗口或生产HA验收；ASSET-000092正式30项仍`PROPOSED_NOT_APPROVED / NOT_RUN`。


## CH17-T004 Lease-bound Watch删除事件与断流恢复（第六十轮）

- [Live Run 45938253313](https://github.com/rexyll/cnc-knowledge/actions/runs/45938253313)成功；新增两项Watch测试通过。Lease Revoke DELETE事件revision/header=19，`prev_kv.mod_revision=18`且Lease ID正确；线性一致Range确认key删除。
- 已建立Watch在etcd1停止后返回`AuthorityStoreUnavailableError`，只请求初始endpoint一次。多数派删除revision=21；恢复后线性一致快照revision=21/key不存在，从revision=22恢复Watch，首个新事件是PUT revision=22，旧DELETE未重放。Artifact [15171088378](https://github.com/rexyll/cnc-knowledge/actions/runs/45938253313/artifacts/15171088378)。
- [Quality Run 45938253249](https://github.com/rexyll/cnc-knowledge/actions/runs/45938253249)：535 unittest（506 passed、29 skipped），CH12 143项，strict lint 0 errors/5既有warning，结构校验0 errors；SPAT 30项仅离线模拟、business_test_status仍NOT_RUN。
- 该结果是一次性CI supporting evidence；Watch仍不支持双向WatchProgress/WatchCancel；正式ASSET-000092仍`PROPOSED_NOT_APPROVED / NOT_RUN`。
