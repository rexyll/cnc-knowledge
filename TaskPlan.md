# CNC Knowledge 总体任务计划

> 项目范围：数控机床及其直接相关产业链的完整工程知识体系。  
> 计划版本：v1.0（初始化）  
> 建立日期：2026-11-21  
> 规则优先级：本文件的 Guide 与 Limit 高于所有章节计划；章节计划不得擅自削弱或覆盖本文件规则。

## 1. 项目愿景与目标

建设一个长期维护、可验证、可追溯、结构化且可扩展的数控机床行业知识库。知识库覆盖从机床类型和整机架构，到机械零件、材料、电气电子、CNC、伺服驱动、嵌入式平台、通信、算法、加工工艺、测试标准、制造装配、使用维护、故障诊断、厂商供应链及数字化应用的全链路知识。

最终成果不仅是文章集合，还应形成彼此关联的知识资产：机型档案、厂商/产品档案、零部件与材料数据库、接口与协议资料、BOM、图纸和手册索引、性能指标字典、标准目录、维护作业指导、故障案例、图片/动图/文档资源和典型整机拆解档案。

## 2. 范围边界

### 2.1 纳入范围

- 各类数控机床及其整机、机械、电气、电子、液压、气动、润滑、冷却、排屑和防护系统。
- CNC控制器、PLC、伺服/主轴驱动、电机、反馈元件、I/O、传感器、工业通信和相关实时控制系统。
- 数控机床专用或直接使用的操作系统、嵌入式平台、驱动、软件架构、数据模型、算法、HMI和上层应用。
- 刀具、刀柄、刀库、夹具、工件装夹、加工工艺、CAD/CAM/后处理及测量系统。
- 整机制造、零部件制造、材料、热处理、表面处理、装配、安装、调试、检测、维护、维修和备件。
- 产品规格、性能指标、国家/行业/国际标准、法规、安全、EMC、可靠性和验收要求。
- 整机厂、数控系统厂、部件厂、刀具厂、供应商、代理服务网络、型号、产品、替代关系和供应风险。
- 机床联网、数据采集、MES/ERP/SCADA集成、能耗管理、状态监测、预测性维护和数字孪生。
- 与数控机床有明确关系的跨行业技术。必须说明其在数控机床中的具体用途和边界。

### 2.2 排除或严格限定

- 与数控机床没有直接关系的通用机器人、自动驾驶、消费电子、通用云平台和普通工业自动化知识，不作为独立知识板块。
- 工业机器人、上下料系统、工厂物流和整线自动化，仅收录与数控机床上下料、加工单元或生产线集成直接相关的接口和应用。
- 通用材料、数学、操作系统、网络通信等基础知识，只收录理解或实现数控机床技术所必要的内容，避免无限扩张。
- 纯营销宣传、无出处排行榜、投资预测和与技术知识无关的商业内容不纳入主体知识库。

## 3. Guide（全库必须遵循）

### G-01 分支与版本控制

1. **默认只允许在 `main` 分支进行读取、创建、修改、提交和维护。**
2. **除非用户明确提出创建新分支，否则严禁创建任何其他分支。** 不得因“开发习惯”、并行任务、试验或自动化流程而擅自分支。
3. 不得擅自改写历史、强制推送、重置或删除远端分支。确需执行高风险 Git 操作，必须先取得用户明确授权。
4. 每次提交使用清晰、可检索的提交信息；提交前检查修改范围和文件路径。

### G-02 目录与章节组织

1. 知识正文统一放在 `docs/<章节目录>/`，每个章节以 README 或专题文档组织内容。
2. 每个知识章节在 `docs/TaskPlan/<章节目录>/TaskPlan.md` 有且仅有一份对应的章节任务计划。
3. 全库多媒体资源统一放在根目录 `resouces/`，按知识章节建立同名章节目录。目录名和章节映射以本文件第 5 节为准。
4. **所有在项目过程中展示、生成、收集、引用或整理的图片、动图，以及完整文档文件（包括但不限于 Word、PDF、Excel、CSV），都必须保存到 `resouces/` 下对应章节目录。** 其他媒体类型（视频、音频、CAD/工程图、原始测量文件等）如被纳入，也按同一规则归档。
5. 不得将图片、动图或完整资料散放在 `docs/`、仓库根目录或其他章节目录。知识正文通过相对路径引用 `resouces/` 中的资源。
6. 各资源文件必须附带来源/作者、取得或生成日期、版本、许可/使用权状态、关联章节和对应知识条目；适用时记录校验值、型号和文件说明。
7. 本项目按用户明确指定使用目录名 **`resouces`**（保留该拼写），不得另建 `resources` 造成双重归档。

### G-03 资料来源与证据等级

1. 优先来源：标准发布机构/法规官网、机床及部件原厂官网和官方手册、官方规格书/图纸、学术论文、权威技术出版物、公开检测报告和可追溯的工程记录。
2. 经销商、论坛、博客、视频和社区内容可作为线索或经验来源，关键事实应尽可能由更高等级来源交叉验证。
3. 每项关键技术事实尽量记录来源标题、发布机构/作者、原始链接、发布日期/版本、访问或核验日期、适用型号/软件版本和页码/章节。
4. 明确区分：标准或官方定义、厂商声明、第三方测试、实测数据、公开案例、工程经验、推断和待核实信息。
5. 来源互相冲突时并列记录差异、各自版本和适用条件，不擅自选择一个结论掩盖冲突。
6. 不能取得可靠证据时，明确标记“待核实”，不得将猜测写成事实。

### G-04 内容质量与技术表达

1. 以中文为主，保留必要英文原词、缩写、标准原名和厂商术语；首次出现时解释。
2. 使用统一SI单位和明确符号；涉及转速、转矩、精度、频率、功率、温度等参数时注明单位、测量条件和统计口径。
3. 明确区分额定值、最大值、典型值、选配值、实验值和实际工况值。不同型号或版本数据不得混为一谈。
4. 关键术语、系统边界、接口、数据结构和实体命名尽可能统一，并链接到术语表和实体登记表。
5. 文章应回答“是什么、做什么、如何工作、如何选型/集成、如何验证、有哪些限制和风险”，按主题复杂度取舍。
6. 公式须定义所有变量、单位、坐标方向、假设和边界条件；示例须说明适用机型和控制系统。
7. 图片/图表应有标题、说明、来源/作者和许可状态；结构图须标注视图方向、编号、部件名称和必要图例。
8. 结论、建议和方案对比要说明前提、证据、优缺点和适用边界，不作无依据的绝对化结论。

### G-05 机型、部件、材料与性能数据规范

1. 整机、系统、零件、材料、厂商、产品型号、标准、协议、故障和案例使用稳定且唯一的实体标识；名称变化时保留别名。
2. 零部件至少记录：唯一ID、标准名称、别名、类别、功能、安装位置、所属机型/子系统、型号/图号、数量/单位、材质、关键规格、原厂/供应商、来源和状态。
3. 材料性能必须记录标准体系/牌号、材料状态、热处理、适用厚度/试样条件、指标值、单位和测试/标准依据；不得只保存孤立数值。
4. 性能参数必须记录适用机型及配置、单位、测试方法、环境条件、数据属性（额定/典型/实测等）、来源和版本。
5. BOM应支持整机/子系统/部件的层级、数量、位号、替代件、选配件、有效版本和配置差异。
6. 供应商和产品信息应记录核验日期、原厂与代理关系、型号、官方资料地址和可验证的兼容条件；价格和供应状态如无法核实则不填写。

### G-06 标准、法规与知识产权

1. 记录标准编号、名称、发布机构、版本/发布日期、状态、适用范围和官方检索入口；定期检查废止、替代和修订状态。
2. 标准全文、付费手册、厂商图纸和受版权限制的资料，不得未经授权复制、上传或再分发。
3. 只有在用户提供、公开许可、明确授权或其他合法依据允许保存的情况下，才将完整文档副本存入 `resouces/`。否则保存可合法记录的元数据、摘要、引用信息和官方链接，不得以“统一归档”为由侵犯版权或保密义务。
4. 资源记录应注明许可证/授权范围；不确定时标注“权利状态待确认”，在确认前不得公开分发。
5. 不得提交客户机密、供应商保密资料、个人隐私、密钥、凭证或未经授权的商业数据。

### G-07 安全与工程责任

1. 涉及高速旋转部件、高压电、储能、液压/气压、吊装、夹紧、刀具更换和维修的内容，必须提示危险源、隔离/锁定挂牌（LOTO）和人员资质要求。
2. 任何操作、安装、维修、调试步骤均应以具体设备制造商手册、适用法规/标准和现场安全程序为准。
3. 不提供绕过防护门、急停、限位、联锁、超速保护或其他安全功能的操作指导；不鼓励带电/带压/带运动维修。
4. 安全参数、功能安全等级和验收限值不得臆造；不确定时明确标注并要求查阅原厂文件或由合格人员评估。
5. 涉及工业网络时以资产保护、隔离、加固、监测和恢复为目的，不编写对现实设备进行未授权攻击或破坏的操作指南。

### G-08 资源归档与多媒体管理

1. 图片、动图和完整文档归档到 `resouces/<章节目录>/`；一个资料涉及多个章节时，选择主归属章节保存，其他章节使用链接引用，避免重复副本。
2. 推荐命名：`<实体ID或型号>_<主题>_<版本或日期>_<语言>.<扩展名>`；原厂文件名有追溯价值时可保留，并在资源清单中记录规范名称。
3. 下载/收集的资料不得去除水印、版权声明或来源信息；不对原始资料做会改变技术含义的编辑。编辑副本需另存并标注“整理版/译文/裁剪版”。
4. 展示给用户的生成图、流程图、技术示意图或整理后的动图也要作为文件归档；对无法合法存储的外部图片只保留出处链接和必要说明。
5. 每章可维护 `ASSET-INDEX.md`，记录文件路径、说明、来源、许可、版本、关联条目和校验信息。

### G-09 任务执行和验收

1. 任何新增知识工作必须先对应根计划中的阶段任务或章节 `TaskPlan.md` 中的任务节点；若没有对应任务，先补充计划再执行。
2. 每个任务节点必须包含编号、目标、范围、依赖、交付物、验收标准和状态；任务拆分到可在一次或少数几次工作中清晰完成的粒度。
3. 状态仅使用：`TODO`、`IN_PROGRESS`、`BLOCKED`、`DONE`、`DEFERRED`、`OUT_OF_SCOPE`。完成必须有实际交付物和验收证据。
4. 不得仅因创建空目录、模板或标题就宣称知识研究任务完成；脚手架完成与内容研究完成必须区分。
5. 标记 `DONE` 前检查内容完整性、引用来源、链接有效性、资源归档、交叉链接和技术审查；对需实机验证的内容明确标记验证层级。
6. 每日任务明细记入 `TaskHistory/TaskHistory-YYYY-MM-DD.md`，根计划只维护里程碑状态和索引，不复制每日长篇日志。
7. 遇到任务范围冲突、资料权利不明、关键事实无法核实或安全边界不清时，暂停相应部分并记录阻塞原因。

### G-10 章节计划与规则继承

1. `docs/TaskPlan/<章节目录>/TaskPlan.md` 与对应 `docs/<章节目录>/`、`resouces/<章节目录>/` 一一对应。
2. 章节任务计划只写本章目标、任务拆解、依赖、交付物和验收标准；不重复编写本文件的 Guide 与 Limit。
3. 章节计划无权豁免本文件规则。若特殊章节确实无法受现有 Guide/Limit 约束，必须先向用户说明原因并获得确认，之后才能增加章节特例。
4. 跨章节知识只建立权威主条目和链接，不无意义复制；各章节需明确主归属。

### G-11 每日历史记录

1. 每个有任务完成的日期创建 `TaskHistory/TaskHistory-YYYY-MM-DD.md`，日期使用项目统一时区 `Asia/Shanghai`。
2. 每一条完成记录至少包含：任务ID、任务名称、实际完成时间（ISO 8601，含 `+08:00`）、所在分支（默认 `main`）、交付文件/资源、来源或证据、验收结果、提交SHA（提交后补齐）和遗留事项。
3. 只将已经实际完成并通过相应验收的任务标记为完成；未完成工作写入“进行中/阻塞/后续任务”。
4. 历史记录按日追加，不覆盖既有记录；更正时保留更正说明。

### G-12 维护和演进

1. 为厂商型号、产品规格、软件版本、标准状态和供应信息记录最近核验日期，避免将过时资料展示为当前状态。
2. 对重大版本变更、标准替代、产品停产和已知勘误进行差异记录。
3. 目录可以扩展，但新增章节必须有明确边界，并同步更新总目录、章节计划索引和资源映射。
4. 定期进行链接检查、重复文件检查、术语一致性检查、未引用资源检查和章节覆盖度审查。

## 4. Limit（严格禁止事项）

- **禁止未经用户明确要求创建新分支**；禁止以任何默认工作流、并行便利或临时实验为由偏离 `main`。
- 禁止在 `resouces/` 之外保存或提交本项目展示/整理的图片、动图和完整文档副本；禁止新建拼写不同的资源根目录。
- 禁止编造机床参数、材料指标、零件型号、供应商、标准条款、报警代码、故障原因、安装步骤、测试数据或来源。
- 禁止将厂商宣传数据当作独立实测；禁止把模拟、仿真、台架和实机验证混为一谈。
- 禁止收录与数控机床没有直接关系的主题作为独立内容；禁止将本库扩展成无边界的通用制造/自动化百科。
- 禁止未经授权复制或分发受版权、商业秘密、保密协议限制的文档、图纸、标准全文和照片。
- 禁止未经授权公开个人信息、客户/供应商机密、账户凭证、令牌、私钥和内部网络细节。
- 禁止提供或鼓励旁路安全防护、急停、联锁、限位和保护机制的操作；禁止将未经验证的危险操作写成标准作业指导。
- 禁止在章节计划中擅自增加/修改全局 Guide 或 Limit，禁止用章节规则弱化全局规则。
- 禁止将空模板、待核实信息、未经审查的AI生成文本或单一来源推断标记为已完成的可靠知识。
- 禁止重复存储同一原始资源；禁止修改原始资料而不保留来源和版本关系。
- 禁止随意大规模删除、重命名或重写现有知识和资源；涉及结构性迁移时必须保留映射及历史可追溯性。

## 5. 章节目录与资源映射

| 编号 | 知识章节目录（docs） | 任务计划路径 | 资源路径 |
|---|---|---|---|
| 01 | `docs/01-industry-and-fundamentals/` | `docs/TaskPlan/01-industry-and-fundamentals/TaskPlan.md` | `resouces/01-industry-and-fundamentals/` |
| 02 | `docs/02-machine-types-and-products/` | `docs/TaskPlan/02-machine-types-and-products/TaskPlan.md` | `resouces/02-machine-types-and-products/` |
| 03 | `docs/03-system-architecture-and-mechanics/` | `docs/TaskPlan/03-system-architecture-and-mechanics/TaskPlan.md` | `resouces/03-system-architecture-and-mechanics/` |
| 04 | `docs/04-components-materials-and-manufacturing/` | `docs/TaskPlan/04-components-materials-and-manufacturing/TaskPlan.md` | `resouces/04-components-materials-and-manufacturing/` |
| 05 | `docs/05-tooling-fixtures-and-workholding/` | `docs/TaskPlan/05-tooling-fixtures-and-workholding/TaskPlan.md` | `resouces/05-tooling-fixtures-and-workholding/` |
| 06 | `docs/06-electrical-electronic-systems/` | `docs/TaskPlan/06-electrical-electronic-systems/TaskPlan.md` | `resouces/06-electrical-electronic-systems/` |
| 07 | `docs/07-cnc-controller-and-plc/` | `docs/TaskPlan/07-cnc-controller-and-plc/TaskPlan.md` | `resouces/07-cnc-controller-and-plc/` |
| 08 | `docs/08-servo-spindle-and-motion-control/` | `docs/TaskPlan/08-servo-spindle-and-motion-control/TaskPlan.md` | `resouces/08-servo-spindle-and-motion-control/` |
| 09 | `docs/09-os-embedded-platforms/` | `docs/TaskPlan/09-os-embedded-platforms/TaskPlan.md` | `resouces/09-os-embedded-platforms/` |
| 10 | `docs/10-drives-fieldbus-and-communications/` | `docs/TaskPlan/10-drives-fieldbus-and-communications/TaskPlan.md` | `resouces/10-drives-fieldbus-and-communications/` |
| 11 | `docs/11-software-architecture-and-interfaces/` | `docs/TaskPlan/11-software-architecture-and-interfaces/TaskPlan.md` | `resouces/11-software-architecture-and-interfaces/` |
| 12 | `docs/12-control-and-machining-algorithms/` | `docs/TaskPlan/12-control-and-machining-algorithms/TaskPlan.md` | `resouces/12-control-and-machining-algorithms/` |
| 13 | `docs/13-cad-cam-programming-and-process/` | `docs/TaskPlan/13-cad-cam-programming-and-process/TaskPlan.md` | `resouces/13-cad-cam-programming-and-process/` |
| 14 | `docs/14-performance-metrology-and-acceptance/` | `docs/TaskPlan/14-performance-metrology-and-acceptance/TaskPlan.md` | `resouces/14-performance-metrology-and-acceptance/` |
| 15 | `docs/15-standards-safety-and-compliance/` | `docs/TaskPlan/15-standards-safety-and-compliance/TaskPlan.md` | `resouces/15-standards-safety-and-compliance/` |
| 16 | `docs/16-manufacturing-assembly-installation/` | `docs/TaskPlan/16-manufacturing-assembly-installation/TaskPlan.md` | `resouces/16-manufacturing-assembly-installation/` |
| 17 | `docs/17-operation-maintenance-and-repair/` | `docs/TaskPlan/17-operation-maintenance-and-repair/TaskPlan.md` | `resouces/17-operation-maintenance-and-repair/` |
| 18 | `docs/18-fault-diagnosis-and-reliability/` | `docs/TaskPlan/18-fault-diagnosis-and-reliability/TaskPlan.md` | `resouces/18-fault-diagnosis-and-reliability/` |
| 19 | `docs/19-manufacturers-products-and-supply-chain/` | `docs/TaskPlan/19-manufacturers-products-and-supply-chain/TaskPlan.md` | `resouces/19-manufacturers-products-and-supply-chain/` |
| 20 | `docs/20-bom-drawings-and-technical-documents/` | `docs/TaskPlan/20-bom-drawings-and-technical-documents/TaskPlan.md` | `resouces/20-bom-drawings-and-technical-documents/` |
| 21 | `docs/21-digitalization-and-smart-manufacturing/` | `docs/TaskPlan/21-digitalization-and-smart-manufacturing/TaskPlan.md` | `resouces/21-digitalization-and-smart-manufacturing/` |
| 22 | `docs/22-case-studies-and-reference-machines/` | `docs/TaskPlan/22-case-studies-and-reference-machines/TaskPlan.md` | `resouces/22-case-studies-and-reference-machines/` |

跨章节公共资料：术语表放在 `docs/GLOSSARY.md`；实体登记放在 `docs/ENTITY-REGISTRY.md`；总入口放在 `docs/README.md`。公共资源应选择主要知识归属章节保存，再从其他章节链接。

## 6. 项目阶段与总任务

| 阶段 | 任务ID | 目标 | 状态 |
|---|---|---|---|
| P0 初始化 | INIT-001 | 建立main分支首个提交及仓库入口 | DONE |
| P0 初始化 | INIT-002 | 建立总体规则、章节结构、章节任务计划、资源目录和每日历史机制 | DONE（本次初始化提交完成后生效） |
| P1 知识模型 | CORE-001 | 完成实体分类、唯一ID、术语和跨章节关系模型 | DONE |
| P1 知识模型 | CORE-002 | 完成文章模板、引用规范、资源清单和数据字段规范 | DONE |
| P1 知识模型 | CORE-003 | 建立全库质量检查、链接检查和覆盖度审查清单 | DONE |
| P2 行业地图 | MAP-001 | 完成行业、机型、厂商、系统及供应链全景图 | DONE |
| P3 核心技术 | TECH-001 | 完成机械、电气、CNC、伺服、通信和嵌入式核心知识 | TODO |
| P4 软件与工艺 | APP-001 | 完成软件架构、算法、编程、CAM和应用知识 | TODO |
| P5 规范与工程 | ENG-001 | 完成性能检测、标准、安全、制造、安装和维护知识 | TODO |
| P6 运营与案例 | OPS-001 | 完成故障诊断、供应链、BOM、数字化和典型机床档案 | TODO |
| P7 持续维护 | MAINT-001 | 持续核验版本、补齐覆盖面并维护过期内容 | TODO |

> 总任务只记录里程碑；每个章节具体节点和每日完成明细分别维护在章节 TaskPlan 和 TaskHistory 中。

## 7. 通用知识条目模板

每个专题按实际适用范围选择字段，至少尽可能包含：
- 标题、知识条目ID、章节、关键词、别名、摘要、适用机型/系统/版本。
- 定义与功能、结构与工作原理、接口/参数/单位、配置与选型、使用或维护方法。
- 图纸/图片/动图及资源相对路径、BOM/部件/材料关联、相关标准和安全注意事项。
- 来源清单（机构/作者、标题、版本/日期、URL、页码/章节、核验日期、证据等级）。
- 限制、差异、待确认事项、验证等级、最后更新日期和相关条目链接。

## 8. 完成定义（Definition of Done）

任务必须同时满足适用的以下条件才能标记为 `DONE`：
1. 交付物真实存在，内容与任务目标一致，不只是空目录或标题。
2. 事实性陈述有可靠来源；不确定部分已显式标记。
3. 参数、单位、版本、适用机型和测试条件齐全（适用时）。
4. 图片/动图/完整资料已按规则归档在正确的 `resouces/` 章节目录并正确引用。
5. 版权、许可、安全和保密检查通过。
6. 相关术语、实体、BOM、标准、厂商和其他章节的交叉链接已补齐（适用时）。
7. 进行技术与编辑审查，检查链接、文件命名、重复内容和资料完整性。
8. TaskPlan 状态、每日历史记录和提交信息同步更新。

## 9. 初始化后建议执行顺序

1. CORE-001～CORE-003、MAP-001及CH01-T001～T003均已完成；行业地图、分类体系、代表性厂商生态、基础原理和跨章节实体关系索引已建立首轮可追溯内容。
2. CH01-T004、CH02-T004与CH19-T004已完成；CH02已建立机型分类、主要机型档案、典型型号库和工程选型比较方法；CH19已建立整机与CNC/驱动平台厂商档案、关键部件供应商目录及供应链比较/风险管理框架。下一步推进CH03-T001（整机功能架构）。
3. 按各章依赖关系推进CH01～CH22；跨章节术语、实体身份、结构化属性和来源语义必须保持统一。
4. 优先形成高价值、可证据化的核心档案，再扩展到型号、零件、材料、供应商和案例的细粒度数据。
5. 持续维护TaskHistory、资源索引、来源有效性和版本核验日期。

## 10. 当前状态

- 仓库初始化完成，默认分支为 `main`；当前仓库仅保留main分支。
- 已建立22个知识章节的正文入口、章节任务计划和resouces资源归档目录。
- CORE-001～CORE-003、MAP-001及CH01-T001～T004、CH02-T001～T004及CH19-T001～T003已完成；CH01已建立行业地图、基础原理、文章实体主记录和关系索引，补齐16条基础术语实体及CH01字段字典，并完成22章范围/边界审查；CH19已建立整机/系统厂商档案、关键部件供应商和产品族目录，以及兼容性证据、替代矩阵、生命周期风险、地区供应/售后核验和采购决策框架。
- 全库当前结构统计：22章、97条实体记录、176条关系记录、71条来源记录；实体包含10条KNOW知识条目记录，关系包含130条知识文章索引边和46条分类/型号/制造事实关系。自动质量门禁已实跑通过。本统计是当前已录入内容，不代表22章均已完成研究。
- 后续每次继续工作均从本文件和对应章节TaskPlan读取状态，完成任务后更新章节计划、覆盖矩阵及当日TaskHistory。
