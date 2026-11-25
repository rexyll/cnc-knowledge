# 备件合成测试夹具基线 v1.0.0

**数据集ID：** `SPAREPARTS-SYN-BASE-001`  
**版本：** `1.0.0`  
**状态：** `DRAFT`（未获企业批准，未冻结至任何测试环境）  
**合成属性：** `synthetic_only=TRUE`  
**关联知识：** KNOW-000032；测试规格 KNOW-000030；治理规范 KNOW-000031

## 1. 交付物

- [数据集清单](../../resouces/17-operation-maintenance-and-repair/spare-parts-synthetic-fixture-baseline-v1-manifest.csv)：一条版本化元数据记录。
- [对象与事件夹具](../../resouces/17-operation-maintenance-and-repair/spare-parts-synthetic-fixture-baseline-v1.csv)：89条固定合成记录，包含主数据、配置/BOM、采购收货、质量、库存、替代、维修、生命周期、权限及事件。
- [30项用例映射矩阵](../../resouces/17-operation-maintenance-and-repair/spare-parts-synthetic-fixture-test-case-coverage-v1.csv)：SPAT-001～SPAT-030逐项映射正向/负向夹具和事件，全部保持NOT_RUN。

该夹具包采用固定CSV内容与稳定Fixture ID，不依赖运行时随机数；相同版本、相同测试配置和独立重置组可重复加载。它是一套软件验证示例，不是可直接写入企业ERP/WMS/CMMS的通用数据导入文件。

## 2. 虚构对象域

所有组织、地点、机床实例、BOM、PART、供应方、采购、批次、维修工单、角色和事件标识均使用 `SYN-`、`FX-`、`EVT-` 前缀，且全部标记 `synthetic_only=TRUE`。没有真实OEM、真实机床型号、供应商、人员、客户、采购合同、生产主键、账号或联系方式。

| 范畴 | 虚构样例 | 测试目的 |
|---|---|---|
| 机床配置 | `SYN-MINST-A01` / `SYN-MINST-B01` | 对照配置范围与不匹配 |
| BOM | `SYN-BOM-A-R1` / `SYN-BOM-A-R2` | 生效日期与版本边界 |
| 物料 | `SYN-PART-001/002/003` | 原件、候选替代和负向候选 |
| 采购/收货 | `SYN-PO-001-L1` / `SYN-RECEIPT-001` | 订单10 EA、部分收货4 EA、剩余6 EA |
| 质量 | `SYN-QC-RELEASE-003` / `SYN-QC-HOLD-001` | 4 EA中3 EA放行、1 EA隔离 |
| 单位 | `SYN-BOX-TO-EA` | 合成换算1 BOX=10 EA |
| 维修 | `SYN-WO-001` | 发料2 EA、安装1 EA、未安装余料1 EA另行退回 |
| 权限 | `SYN-ROLE-WAREHOUSE` 等 | 测试角色别名，不关联真人账号 |

上述数量、单位和比例只是易于人工核对的虚构值，不代表库存政策、采购建议、收货容差、行业通用换算、备件规格或真实设备参数。

## 3. 核心算术和隔离组

库存快照的合成字段为 `on_hand_total=20 EA`、`reserved=2 EA`、`allocated=2 EA`、`quarantined=4 EA`，按前序文档的演示公式得到 `available=20-2-2-4=12 EA`。实际企业库存桶语义与公式仍须由数据所有者确认。

采购样例为10 EA，部分收货4 EA，余量6 EA；待检数量不可直接等同可用量。维修样例发料2 EA、安装1 EA、未安装1 EA退回，防止把领料事实误判为安装消耗。

每行通过 `reset_group` 分隔。不同用例的事件和数量差异不得串成一条共享库存流水；执行某个用例前，必须恢复它自己的基线并确认数据集版本。不同库存测试间不能将收货、质量、维修、报废等独立用例的增量相加。

## 4. 事件时序

事件记录包含稳定事件ID、业务时间、接收时间、序号、版本、事件类型和重放/迟到/冲销标识，时间使用带 `+08:00` 偏移的ISO 8601格式。相同收货事件重放、迟到冲销和乱序事件专用独立重置组。原事件不得删除或覆盖，修正应保留关联冲销/补偿事件链。

本时间线仅是固定测试时序，不表示真实业务发生时间。目标系统若使用UTC或不同业务时区，需要另行批准映射与转换策略。

## 5. 30项用例覆盖

[用例映射CSV](../../resouces/17-operation-maintenance-and-repair/spare-parts-synthetic-fixture-test-case-coverage-v1.csv)复用原测试矩阵中的编号、分类、标题、前置条件，逐条关联夹具ID、事件ID和预期断言。覆盖外部键、BOM配置/修订、采购授权、部分收货、质量分桶、幂等、库存分桶/预留/在途PO、单位换算、替代范围、发料与安装、批次追溯、旧件返修/报废、对账、PCN/EOL、角色权限、SoR冲突、数据最小化及事件恢复。

映射完整不代表测试执行完成。每次执行仍须记录环境版本、数据集校验值、实际输出、证据、缺陷和复测链；30项状态不得因夹具可用而从NOT_RUN改成PASS。

## 6. 使用限制与后续步骤

1. 数据集清单状态为DRAFT，批准环境/测试层级均为NONE_NOT_APPROVED；哈希值待仓库提交后单独计算。
2. 在获批的非生产环境使用前，必须先完成ASSET-000039环境就绪检查，包括隔离、身份/权限、端点、秘密管理、快照恢复和清理。
3. 本数据包不会自动连接任何ERP/WMS/CMMS/QMS或生产队列，也不应直接用作企业系统导入文件。
4. 真实机床、CNC控制器、运动轴、主轴、ATC、卡盘、液压/气动和安全回路均不在本包执行范围内。
5. 本轮没有执行自动化、企业SIT/UAT、生产影子运行、HIL或实机验证；全部30项测试仍为NOT_RUN。

后续建议先开发纯本地静态fixture validator：检查CSV列宽、Fixture ID唯一、父/关联引用、30项用例完整覆盖、事件ID/序号/时间一致性及隔离组，然后再申请企业非生产环境批准。

## 7. 纯本地静态校验器

仓库提供 `scripts/spare_parts_fixture_validator.py`，只依赖Python标准库，不连接ERP/WMS/QMS/CMMS/EAM，也不会导入、写入或变更任何业务系统。它检查：

- 三份夹具CSV及源测试矩阵的表头、行宽、数据集ID/版本、合成标记和唯一Fixture/Event ID；
- 父/关联引用、测试用例ID、正向/负向夹具与事件引用，以及夹具声明和用例映射之间的双向一致性；
- SPAT-001～SPAT-030完整覆盖、标题/分类/前置条件/执行状态与原测试矩阵一致；
- BOM修订时间窗的时区、有效期和重叠；事件业务时间/接收时间、正时序号、重复ID、乱序显式标记和重置组内序号。

从仓库根目录执行：

```bash
python scripts/spare_parts_fixture_validator.py --root .
```

输出JSON并写出可归档报告：

```bash
python scripts/spare_parts_fixture_validator.py --root . --json \
  --report-json resouces/17-operation-maintenance-and-repair/generated/spare-parts-fixture-validation-report-v1.json
```

报告包含数据集身份、各项检查结果、记录数、源文件SHA-256、警告和错误。当前数据集DRAFT、无已批准环境以及30项测试尚未执行均以WARNING/状态字段保留；静态校验PASS不代表SIT/UAT通过、数据集获批或机床实机验证。CI的Knowledge Quality Job会自动运行校验器并上传JSON报告Artifact。

## 8. 场景重置配置与本地fixture loader

本地工具 `scripts/spare_parts_fixture_loader.py` 根据 [30项用例映射](../../resouces/17-operation-maintenance-and-repair/spare-parts-synthetic-fixture-test-case-coverage-v1.csv) 和 [30条场景重置配置](../../resouces/17-operation-maintenance-and-repair/spare-parts-synthetic-fixture-reset-profiles-v1.csv) 生成隔离的文件系统场景包。配置中的依赖闭包、重置组和清理策略由源映射与夹具引用确定性推导；loader会重新推导并比对，拒绝不一致的配置。

准备单个场景：

```bash
python scripts/spare_parts_fixture_loader.py --root . \
  --test-case SPAT-017 \
  --output-dir /tmp/ch17-spare-parts-scenarios
```

准备全部30个场景：

```bash
python scripts/spare_parts_fixture_loader.py --root . --all \
  --output-dir /tmp/ch17-spare-parts-scenarios
```

每个场景目录包含：

- `scenario-manifest.json`：数据集/用例/场景身份、来源文件SHA-256、生成文件哈希、纳入夹具ID和状态边界。
- `fixtures.csv`：按父对象在先、子对象在后、事件最后的顺序整理的场景夹具。
- `objects.csv` 与 `events.csv`：对象/事件分离视图；事件按接收时间及序号整理。
- `load-plan.json`：仅说明未来在获批测试适配器中所需的装载步骤；当前适配器状态为NOT_IMPLEMENTED。
- `reset-plan.json`：仅列出该场景的reset group、加载顺序和本地包清理顺序；`PLAN_ONLY`，不执行删除或重置。

工具默认拒绝覆盖已有场景目录，所有操作只写用户指定的本地输出目录，不修改原始夹具、映射或企业系统。CI会对30个场景全部生成包并上传Artifact。

**严格限制：** “loader”在当前版本仅指本地文件场景包生成器，不是数据库导入器，不提供ERP/WMS/CMMS/EAM/QMS或消息队列适配器。即使全部30个包都生成成功，业务测试状态仍为NOT_RUN；数据集仍为DRAFT，必须取得企业数据/系统/安全责任人批准后，才能开发目标系统适配器和执行SIT/UAT。

## 9. 场景包完整性校验与离线事件期望投影

仓库新增 `scripts/spare_parts_scenario_runner.py`。该执行器针对第八轮loader生成的场景包做二次验证和离线期望事件投影，不调用企业系统，也不实现ERP/WMS/CMMS/EAM/QMS业务规则。

在仓库根目录执行全部30项：

```bash
python scripts/spare_parts_fixture_loader.py --root . --all \
  --output-dir /tmp/ch17-spare-parts-scenario-packages
python scripts/spare_parts_scenario_runner.py --root . \
  --packages-dir /tmp/ch17-spare-parts-scenario-packages --all \
  --report-json resouces/17-operation-maintenance-and-repair/generated/spare-parts-offline-simulation-report-v1.json
```

单个用例可使用 `--test-case SPAT-010` 替代 `--all`。报告文件由执行器自动创建其父目录；数据包和原始CSV均保持只读。

执行器检查：
- 场景包六份文件是否与当前数据集、用例映射和重置配置确定性重建结果逐字节一致；检查对象/事件分拆、纯合成标记和manifest边界字段。
- 源文件SHA-256、包内文件身份、依赖闭包、对象/事件分区及目录结构；拒绝缺文件、额外文件、符号链接和任何内容漂移。
- 事件类型必须属于显式离线处理目录；业务时间/接收时间/序号必须有效且顺序一致；无法解释的业务时间倒退被拒绝。
- 重复消息必须引用原始收货事件并声明零数量增量；迟到冲销必须保留原事件关联且在本期望投影中为零增量；显式乱序事件必须确实呈现业务时间回退。
- 事件中声明的期望数量增量以十进制定点数投影至对应库存桶，并严格按 `reset_group` 分开输出；没有初始库存快照和企业口径，因此不会计算期末余额、可用量或跨reset group总量。

**结果语义必须区分：** `simulation_status=PASS` 只表示场景包内部完整、来源一致、事件期望投影符合上述静态约束；`business_rule_assertions=NOT_EVALUATED`、`business_test_status=NOT_RUN`。执行器不会调用真实业务规则，也不会把夹具里的期望数量当成实际账面事务。CI模拟通过不能替代企业SIT/UAT、生产影子、HIL或机床实机验收。

CI会先生成30个场景包，再运行全量离线执行器，并上传 `ch17-spare-parts-offline-simulation` 报告Artifact。用户本地报告应写入本章 `resouces/17-operation-maintenance-and-repair/generated/` 目录；动态报告不默认提交进Git。
## 10. 独立库存状态机内核与转移契约

新增 [库存状态机内核](../../scripts/spare_parts_inventory_state_model.py)、[22类事件转移契约表](../../resouces/17-operation-maintenance-and-repair/spare-parts-inventory-state-transition-contract-v1.csv) 和 [专项单元测试](../../tests/test_spare_parts_inventory_state_model.py)。

内核采用双边转移：每笔内部库存转移必须同时指定来源账户、目标账户、数量和单位；来源账户余额不得为负；成功转移前后总量必须相等；失败操作保持原状态不变。外部收货/报废等事件也必须以显式外部账户作为另一条腿，避免无依据地凭空增加或消失数量。

**当前契约全部为 NOT_APPROVED。** 现有夹具的 expected_inventory_bucket/expected_quantity_delta 只描述单桶期望变化，不足以确定双边分录；快照说明也没有提供物料、批次、库位等可执行的完整期初余额。因此本轮不从事件类型推断来源/目标账户，不生成业务期末库存，也不声称业务规则通过。CI只验证22类事件契约唯一、审批门禁关闭和内核的通用数学性质。

契约只有在企业库存数据所有者确认库存账户字典、物料/批次/库位维度、单位、期初余额、外部账户、预留/分配语义及冲销规则后，逐项填写来源/目标账户并记录批准人和依据，才可进入可执行状态。

## 11. 期初状态、账户分类与库存维度候选模型

本轮新增四项资源：

- [候选库存账户字典](../../resouces/17-operation-maintenance-and-repair/spare-parts-inventory-account-catalog-candidates-v1.csv)：区分实物数量账户、外部对方账户、非实物备忘/承诺账户及仅观察记录。尤其将预留/分配和采购未交承诺与实物库存分开建模，避免在未获批准时重复扣减或重复累计。
- [候选库存维度字典](../../resouces/17-operation-maintenance-and-repair/spare-parts-inventory-dimension-dictionary-candidates-v1.csv)：提出物料、批次、库位、所有权、质量状态、计量单位，以及工单/采购行等候选身份维度；是否必填、适用范围和规范化规则均待企业批准。
- [期初余额空白模板](../../resouces/17-operation-maintenance-and-repair/spare-parts-inventory-opening-balance-template-v1.csv)：仅提供字段表头，不填充示例余额。每条余额需关联数据源、源记录、提取时间、截止时点、时区、SHA-256、单位换算和审批依据。
- [期初状态场景矩阵](../../resouces/17-operation-maintenance-and-repair/spare-parts-inventory-opening-state-scenario-matrix-v1.csv)：针对SPAT-006/008/010/012/017/019/020/021/022/023定义期初输入要求与待审批守恒断言。所有场景保持PROPOSED_NOT_APPROVED和NOT_RUN。

**重要边界：** 账户代码和维度集合只是候选设计，不是企业库存政策。可用、待检、隔离、返修、现场保管、在途、待报废属于候选实物账户；预留/分配和PO未交属于候选非实物承诺；盘点差异属于观察记录。企业可能采用不同账户/子账结构，必须由库存数据所有者确认。当前没有任何可用的企业期初余额数据，本轮不生成库存余额、不激活转移契约、不计算业务期末量。

## 12. 多维库存余额内核与期初快照隔离

新增 [多维库存余额模型测试矩阵](../../resouces/17-operation-maintenance-and-repair/spare-parts-multidimensional-inventory-model-test-cases-v1.csv)（ASSET-000050，18个纯合成断言场景）。

实现位于 [多维库存内核](../../scripts/spare_parts_multidimensional_inventory.py)，专项测试位于 [多维库存测试](../../tests/test_spare_parts_multidimensional_inventory.py)。余额键固定包含账户、物料、批次、库位、所有权、质量状态和计量单位。普通双边转移只允许在同物料/批次/库位/所有权/单位下改变账户或状态；跨库位移动、物料/批次变更和所有权变更必须由独立业务事件建模。不同单位禁止直接转移；只有显式提供包含批准人和批准依据的APPROVED换算记录，才可调用独立换算函数。模型不自动应用换算，也不从BOX/EA示例推断换算。

期初快照装载器只接受 synthetic_only=TRUE 且 snapshot_status=SYNTHETIC_TEST_ONLY 的行，并要求reset_group；企业生产/批准快照不能通过该装载入口。事件回放要求事件ID唯一、序号严格递增；整个批次在全部事件成功前不提交余额，后续事件失败时整批不改变状态。

**边界：** 自检使用虚构数量，仅验证内核数学性质；不加载企业期初快照、不连接ERP/WMS/CMMS、不产生外部写入。自检报告固定为 BLOCKED_PENDING_ENTERPRISE_APPROVAL，业务规则断言为 NOT_EVALUATED。14个专项unittest方法PASS，覆盖17个断言场景不代表企业库存流程验收。

## 13. 不可变库存事件账本、幂等与时点重建

新增 [事件账本测试矩阵](../../resouces/17-operation-maintenance-and-repair/spare-parts-inventory-event-ledger-test-cases-v1.csv)（ASSET-000051，18个纯合成断言场景）。实现位于 [库存事件账本内核](../../scripts/spare_parts_inventory_event_ledger.py)，专项测试位于 [事件账本测试](../../tests/test_spare_parts_inventory_event_ledger.py)。

事件记录携带event_id、business_event_id、source_system_id、idempotency_key、business_time、ingestion_time、event_type、双边维度键、Decimal数量和可选reference_event_id。账本只提供追加接口，记录以不可变tuple视图导出；同幂等键且同载荷的重复投递返回NO_OP，幂等键载荷冲突或event_id跨幂等键重复均拒绝。

迟到/乱序事件仍按接收顺序保留在账本，余额重建按business_time及不可变ledger_sequence排序。可选known_at_cutoff用于还原某个知识时点实际已收到的事件集合。冲销以新的REVERSAL记录表达，必须引用已存在的原TRANSFER、使用完全相反的余额键及相同数量；原记录永不修改。当前模型对每笔原始转移最多允许一次完整冲销，不代表企业部分冲销或多次补偿政策。

重建从调用者显式提供的合成期初余额开始，按截止时点回放事件，并返回事件清单、余额投影和审计计数；不计算跨单位/跨reset group/全局库存总额。失败重建不会修改账本。投影核对接口将重建余额与调用者独立提供的合成期望投影逐维比较，输出匹配/差异键和数量；不代表独立企业SoR对账。

**边界：** 内存账本不是持久化WORM存储，不提供数字签名、权限/职责分离、跨进程并发控制、企业审计留存或消息中间件交付保证。自检报告固定为BLOCKED_PENDING_ENTERPRISE_APPROVAL，business_rule_assertions=NOT_EVALUATED；所有事件均为SYNTHETIC_TEST_ONLY。企业事件语义、部分冲销、事件保留政策及期初快照审批仍待业务所有者确认。


## 14. 库存事件账本完整性链与快照恢复

新增完整性/快照模型（../../scripts/spare_parts_inventory_ledger_integrity.py）、专项测试（../../tests/test_spare_parts_inventory_ledger_integrity.py）和测试场景矩阵（../../resouces/17-operation-maintenance-and-repair/spare-parts-inventory-ledger-integrity-test-cases-v1.csv，ASSET-000052，15个纯合成断言场景）。

规范化序列化明确编码七维余额键、Decimal数量、事件类型/引用、业务时间和接收时间。时间戳统一规范为UTC微秒ISO-8601；Decimal按规范化定点字符串编码。每条事件计算SHA-256内容摘要，并以“前序链头 + 当前事件摘要”构造链哈希；验证器检查序号连续、事件ID/幂等键唯一、事件摘要、前序链和最终链头。

快照包含schema_version、截止ledger_sequence、前序事件链头、业务/知识截止时点、合成期初余额、快照余额和快照摘要。恢复时先校验快照摘要和账本前缀，再回放增量事件，并与从期初余额全量重放的结果逐维比较。任何业务时间不晚于快照截止时点的迟到增量都会拒绝恢复并要求全量重建；截止时点不能倒退。未知版本、前缀链头不符、序号缺口和摘要异常均失败关闭。

**安全限制：** SHA-256链只能检测内容/顺序/链头不一致，不能证明事件来源真实性，也不能抵御有权限者同时重写账本及全部哈希。该实现没有数字签名、外部信任根、WORM/不可变存储、访问控制或跨进程并发保护；不能称为法律意义的防篡改审计账本。CI PASS只表示模型测试通过，business_rule_assertions仍为NOT_EVALUATED，execution_status仍为BLOCKED_PENDING_ENTERPRISE_APPROVAL。


第十四轮CI复验结果：GitHub Actions Run 45629680465 completed/success，Knowledge structure and data quality 与 CH12 numerical resource tests 两个Job均成功；全库87个unittest方法通过，其中新增完整性/快照专项13项通过。账本完整性自检PASS，增量回放1条事件并与全量重放一致；Artifact为ch17-inventory-ledger-integrity-45629680465。该结果只代表合成模型测试通过，业务规则仍NOT_EVALUATED、企业审批门禁仍BLOCKED_PENDING_ENTERPRISE_APPROVAL。


## 15. 库存事件账本本地持久化与故障恢复

新增本地持久化模块（../../scripts/spare_parts_inventory_ledger_persistence.py）、专项测试（../../tests/test_spare_parts_inventory_ledger_persistence.py）和测试矩阵（../../resouces/17-operation-maintenance-and-repair/spare-parts-inventory-ledger-persistence-test-cases-v1.csv，ASSET-000053，11个纯合成场景）。

存储采用版本化代际目录：每代包含ledger.json、snapshot.json和最后写入的COMMIT.json；写入文件后flush/fsync并同步目录，再将暂存目录原子rename为generation目录。最后在同一存储目录写入临时CURRENT指针文件并通过os.replace原子发布。恢复只读取CURRENT指向的代际，验证提交标记、文件SHA-256、账本哈希链、快照摘要和元数据后才重建内存事件账本。未被CURRENT引用的孤立代际和暂存残留不会自动成为已提交版本。

故障注入覆盖账本写入后中断、快照写入后中断、代际目录发布后但CURRENT更新前中断、CURRENT替换前中断；并验证旧CURRENT继续指向上一已提交代际。另覆盖账本文件损坏、提交标记缺失、未知指针版本、路径穿越和重复代际写入。

**持久化边界：** 这是本地文件系统原子发布协议的合成测试实现，不是数据库事务、分布式共识、跨进程锁、WORM或防篡改存储。原子rename/fsync的实际耐久性依赖操作系统、文件系统、挂载选项和存储设备；当前没有多进程并发写保护、保留/清理策略、异机复制、密钥管理、数字签名或外部信任根。测试使用临时目录，不写项目资源目录中的生产状态，也不连接企业系统。业务规则仍NOT_EVALUATED，审批门禁仍BLOCKED_PENDING_ENTERPRISE_APPROVAL。

## 16. 库存账本并发写入控制与多进程恢复一致性

第十六轮扩展本地代际持久化模块（../../scripts/spare_parts_inventory_ledger_persistence.py），新增POSIX advisory flock跨进程排他锁，锁等待支持超时；锁由内核持有，进程异常退出后内核自动释放。锁文件本身可保留，不代表锁仍被占用。所有代际检查、CURRENT读取、代际写入和CURRENT原子替换均在同一写锁临界区内完成。

新增compare-and-swap（CAS）参数expected_current_generation：写入者可声明预期的CURRENT代际；持锁后再次读取实际代际，若已变化则拒绝提交，防止基于过期状态的覆盖。默认值*表示不启用CAS；传入None表示要求CURRENT尚不存在。增加锁超时、CAS冲突、并发写入、进程崩溃后自动释放锁及中断后再次提交测试。

CI多进程自检启动两个独立写进程，以相同的base代际作为前置条件；预期恰好一个提交成功、另一个收到CAS冲突，随后恢复并验证CURRENT指向获胜代际。自检结果：2个并发写入者、1个提交成功、1个陈旧写入冲突、当前代际恢复PASS。全库103个unittest方法通过，新增5个专项测试；CI Run 45635237388两个Job均成功。

**平台与一致性边界：** 当前锁实现使用POSIX fcntl.flock，仅在提供该接口的POSIX环境验证；Windows原生文件锁尚未实现。flock是协作式advisory lock，所有写入者必须遵循协议；不保护绕过模块直接改文件的进程，也不构成分布式锁。网络文件系统的锁语义需单独验证。当前没有读写锁、并发快照清理、跨主机协调或多节点故障切换。仍为临时目录合成测试，无企业系统连接/生产写入；业务断言NOT_EVALUATED，审批门禁BLOCKED_PENDING_ENTERPRISE_APPROVAL。
