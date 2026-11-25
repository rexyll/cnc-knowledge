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
