# 核心实体登记表

本文件是全库实体类型与ID前缀的权威目录。每个实际实体只有一个主记录，跨章节通过稳定ID和关系记录引用。模型说明见KNOWLEDGE-MODEL.md，机器可读定义见data-model目录。

## 1. 受控实体类型

| 实体类型 | ID前缀 | 主归属章节 | 定义/身份边界 |
|---|---|---|---|
| 知识条目 | KNOW | 所有章节 | 可独立引用的知识主题或技术条目；正式正文以KNOW-六位ID登记，attributes记录document_path、article_version、reviewed_on和content_scope。模板中的KNOW-000001只是格式示例，不代表真实知识条目。 |
| 术语 | TERM | 01 | 术语、缩写、同义词或术语定义记录。 |
| 机床类型 | MTYPE | 02 | 按加工方法、结构、用途或轴数定义的机床分类实体。 |
| 整机型号 | MACHINE | 02/22 | 厂商定义的数控机床产品型号或系列；不代表某一台实物设备。 |
| 机床实物实例 | MINST | 16/17/18/22 | 具有序列号、资产号或项目标识的一台具体物理机床实例。 |
| 组织/厂商 | VENDOR | 19 | 制造商、供应商、经销商、集成商或服务组织；组织角色用属性区分。 |
| 品牌 | BRAND | 19 | 产品品牌身份，与拥有品牌的法人组织分开管理。 |
| 部件/系统产品 | PRODUCT | 19 | CNC控制器、驱动器、电机、主轴、轴承、导轨、刀具等商品化产品型号。 |
| 子系统 | SUBSYS | 03/06-11 | 整机中的功能或物理子系统，如主轴单元、进给轴、电气柜、润滑系统。 |
| 零部件 | PART | 04 | 具有物料号、图号、规格或可独立管理的物理零件/装配件。 |
| 材料 | MAT | 04 | 材料牌号、材料规范或特定材料状态记录。 |
| 工艺/过程 | PROCESS | 04/13/16 | 零件制造、热处理、表面处理、切削加工或工艺过程。 |
| 刀具/工具 | TOOL | 05 | 切削刀具、刀柄、刀具组件或专用维修工具。 |
| 工装夹具 | FIXTURE | 05 | 用于工件定位、夹紧、支承或检测的工装实体。 |
| 软件/固件 | SOFTWARE | 07-11/21 | CNC软件、PLC程序包、嵌入式OS、驱动、固件或应用软件及其版本。 |
| 算法 | ALGO | 11/12/21 | 可描述输入、输出、假设和验证方法的控制或加工算法。 |
| 通信协议 | PROTO | 10/21 | 现场总线、工业以太网、上层互操作或数据通信协议。 |
| 接口 | INTERFACE | 06-11/21 | 电气、机械、通信、软件或人机接口及其规范/实现。 |
| 信号/变量 | SIGNAL | 06-11 | I/O点、总线过程数据、状态量、控制信号或数据变量定义。 |
| 参数 | PARAM | 07-12 | CNC、PLC、驱动、OS或算法中的可配置参数定义。 |
| 性能指标 | METRIC | 12/14 | 精度、效率、刚度、动态响应、可靠性等指标的定义和评价口径。 |
| 标准/法规 | STD | 15 | 标准、法规、规范或强制性技术要求的元数据记录。 |
| 测试方法 | TEST | 14/15 | 测试、测量、校准、验收或验证方法定义。 |
| 测量/验证记录 | MEAS | 14/18/22 | 具体设备、条件、时间和方法下得到的测量或测试结果。 |
| 物料清单 | BOM | 20 | 特定机型、配置或版本的整机、子系统或备件物料清单。 |
| 文档记录 | DOC | 20 | 手册、规格书、图纸、技术报告、工艺卡或标准等文档的元数据记录。 |
| 资源文件 | ASSET | 对应主归属章节 | 仓库中实际归档的图片、动图、图纸、PDF、Office文档、CSV及其他附件。 |
| 作业程序 | PROC | 16/17/18 | 安装、调试、操作、保养、维修、校准或检查的程序/指导。 |
| 故障模式 | FAULT | 18 | 可复用的故障现象、失效模式或根因分类记录。 |
| 报警/诊断码 | ALARM | 07/08/10/18 | 厂商或控制系统定义的报警、诊断代码及其版本语义。 |
| 工程案例 | CASE | 22 | 有明确对象、条件、证据、处理过程和结论的工程案例。 |
| 应用场景 | APP | 13/21/22 | 数控机床加工、生产管理、联网或智能化的具体应用场景。 |

| 主轴单元专题术语 | TERM-000050～TERM-000054 | CH01 | 主定义归CH01术语表；CH03使用时通过related_chapters和关系索引引用。 |

## 2. ID分配规则

- 格式：PREFIX加六位十进制序号，例如PART-000123。
- 同一前缀独立递增；分配前检索本登记表和所有实体记录，确保唯一。
- ID不得包含名称、厂商、型号、年份、状态或章节路径等可变信息。
- 一经分配永久保留，不因改名、停产、迁章、合并或删除页面而复用。
- 重复记录合并时保留旧ID，并将生命周期状态设为merged，记录主记录跳转目标。
- 尚未核实的记录可设为candidate，但不得把候选属性或关系当作已确认事实。
- 关系记录独立使用REL-000001序号；来源记录使用SRC-000001序号。REL和SRC是辅助记录命名空间，不属于实体类型枚举，也不能作为entity_id。
- 文档示例ID仅用于说明格式，不代表已登记真实产品。

## 3. 关键实体边界

### 3.1 整机型号与实物实例

- MACHINE记录厂商定义的机床型号/产品系列及其公开规格，不代表单台实物机床。
- MINST记录有实际交付、安装、调试、维护或故障历史的具体机床实例。
- MTYPE记录抽象机床类型。不得把机床类型、产品型号和实物机床混为同一记录。

### 3.2 组织、品牌与产品

- VENDOR表示组织实体；制造商、供应商、经销商、集成商和服务商是组织角色属性。
- BRAND表示品牌身份，可与拥有/运营品牌的法人组织建立关系。
- MACHINE和PRODUCT表示产品型号；整机型号与通用部件/系统产品分开管理。
- 同一法人在多个业务角色下仍是同一VENDOR实体。

### 3.3 文档来源与文件资源

- SRC记录发布主体、标题、版本、日期、链接、定位信息和权利状态。
- DOC记录技术文档本身的元数据，例如手册编号、版本和适用型号。
- ASSET记录仓库中实际归档的文件及相对路径、校验值和许可状态。
- 外部文档可以有DOC/SRC记录但没有本地ASSET；保存文件也不代表自动拥有公开分发权。

## 4. 通用字段

通用实体字段遵循data-model/entity.schema.json：

- 标识与名称：entity_id、entity_type、canonical_name、english_name、aliases。
- 定义与分类：description、primary_chapter、related_chapters、classification_path、tags。
- 生命周期与核验：lifecycle_status、verification_status、created_at、updated_at、verified_at、valid_from、valid_to。
- 溯源：source_ids、notes。
- 类型专属字段：attributes对象；字段语义、单位、允许值、适用条件和来源由所属章节数据字典定义。

## 5. 常见类型的扩展字段建议

| 类型 | 建议attributes字段（按适用情况取用） |
|---|---|
| MACHINE | manufacturer_id、brand_id、machine_type_id、model_code、series、axis_configuration、controller_product_ids、configuration_options、published_specs |
| MINST | machine_model_id、serial_number_or_asset_ref、commissioning_date、site_ref、configuration_snapshot、maintenance_status；敏感字段受权限控制 |
| VENDOR | legal_name、registered_country、website、organization_roles、parent_organization_id、official_contact_page |
| BRAND | brand_name、owner_vendor_id、brand_scope、validity_period |
| PRODUCT | manufacturer_id、brand_id、model_code、product_family、hardware_revision、firmware_versions、key_specs、interfaces |
| SUBSYS | subsystem_type、parent_machine_or_subsystem_id、function、interfaces、operating_conditions |
| PART | part_number、drawing_number、revision、quantity_unit、installation_location、function、material_id、manufacturer_id、supplier_ids、replacement_models |
| MAT | standard_system、grade、material_condition、heat_treatment、chemical_composition、mechanical_properties、physical_properties、test_conditions |
| PROCESS | process_category、input_material_or_part、process_steps、process_window、equipment、quality_checks |
| SOFTWARE | vendor_id、product_name、version、build、supported_platforms、dependencies、license、release_date |
| PROTO | issuing_organization、specification_version、communication_layers、topologies、timing_characteristics、conformance_profiles |
| PARAM | parameter_name、unit、data_type、range、default_value、applicability、software_or_drive_version |
| METRIC | definition、unit、measurement_method_id、test_conditions、acceptance_criteria、uncertainty |
| STD | standard_number、title、issuing_body、edition、publication_date、status、scope、official_catalog_url |
| TEST | method、equipment、procedure、environmental_conditions、calculation_method、uncertainty |
| MEAS | subject_entity_id、metric_id、value、unit、method_id、test_conditions、measured_at、operator_or_lab_role |
| BOM | bom_type、parent_entity_id、revision、configuration、effective_from、line_items |
| DOC | document_number、title、revision、language、document_type、applicable_models、publisher、rights_status、official_url |
| ASSET | file_path、file_name、media_type、mime_type、sha256、file_size、source_id、license_status、chapter_owner |
| FAULT | symptom、failure_mode、affected_subsystems、possible_causes、diagnostic_evidence、severity、occurrence_conditions |
| ALARM | alarm_code、controller_vendor、controller_family、software_version、message、possible_triggers、reset_conditions |
| CASE | case_context、machine_id、configuration、symptom、evidence、analysis、action_taken、verification_result |
| PROC | procedure_type、applicability、prerequisites、hazards、required_tools、steps_reference、verification_points |

扩展字段是建议字段而非全部强制字段。正式录入时应由对应章节定义字段语义和校验规则，不得只因字段存在就填入猜测值。

## 6. 登记与变更流程

1. 检索规范名称、英文名称、别名、型号、图号和制造商，排查已有记录。
2. 确认实体边界及类型，区分类型、型号、产品、实例、组织、品牌、文档和文件。
3. 分配ID并创建主记录；缺失字段显式留空或标记待核实。
4. 记录来源SRC，并按明确谓词添加REL关系；每条关键关系需有证据。
5. 迁移、合并、停产或改名时更新生命周期和关系，不删除/复用ID。
6. 定期核验厂商、产品、软件版本、标准状态和供应信息。

## 7. 机器可读文件

- entity-types.csv：实体类型、ID前缀、主归属和身份边界。
- relation-types.csv：关系谓词、方向和语义约束。
- entity.schema.json：实体JSON Schema。
- relationship.schema.json：关系JSON Schema。
- source.schema.json：来源记录JSON Schema。

- `KNOW-000017` — 数控机床材料数据库：标准体系、牌号与性能数据规则（CH04）。

- `KNOW-000018` — 双驱龙门轴的 MIMO 耦合同步控制与鲁棒性评估（CH12）。
- `KNOW-000019` — 双驱龙门轴的横梁模态、变位置负载与离散延迟鲁棒性（CH12）。

- KNOW-000020 — 龙门连续移动负载时变模型与MIMO多回路disk margin（CH12）。

- KNOW-000020 — 龙门移动负载时变模型与MIMO多回路disk margin（CH12，含电气驱动接口解析扩展）。
