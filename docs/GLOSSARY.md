# 数控机床行业术语表

本文件维护跨章节共用的术语、英文原词、缩写、定义和来源。章节可提供专题术语，但同一术语的主定义集中维护在此处。

| 术语ID | 中文术语 | 英文/缩写 | 定义 | 适用语境 | 来源 | 相关条目 | 状态 |
|---|---|---|---|---|---|---|---|
| TERM-0001 | 数控机床 | CNC machine tool | 由数字控制系统控制加工运动和/或辅助功能的机床；具体定义以适用标准为准 | 全库 | 待补充权威定义 | CH01、CH02 | 待核验 |
| TERM-0002 | 知识实体 | Knowledge Entity | 在知识库中具有独立身份、稳定ID和规范主记录的对象 | 全库数据模型 | 本项目内部数据模型 v1.0 | KNOWLEDGE-MODEL.md | 内部定义 |
| TERM-0003 | 实体关系 | Entity Relationship | 通过有向主体、受控谓词和客体表达的实体间事实或语义连接 | 全库数据模型 | 本项目内部数据模型 v1.0 | RELATIONSHIP-MODEL.md | 内部定义 |
| TERM-0004 | 规范名称 | Canonical Name | 实体主记录中用于展示和检索的首选名称；其他名称保留在别名字段 | 全库数据模型 | 本项目内部数据模型 v1.0 | ENTITY-REGISTRY.md | 内部定义 |
| TERM-0005 | 来源记录 | Source Record | 描述信息来源的发布主体、标题、版本、日期、链接、定位和权利状态的记录 | 全库溯源 | 本项目内部数据模型 v1.0 | data-model/source.schema.json | 内部定义 |
| TERM-0006 | 资源文件记录 | Asset Record | 描述实际归档文件的路径、类型、校验值、许可状态和章节归属的记录 | 全库资源管理 | 本项目内部数据模型 v1.0 | ENTITY-REGISTRY.md | 内部定义 |
| TERM-0007 | 机床型号 | Machine Model | 厂商定义的整机产品型号或系列；不代表一台具体物理机床 | 产品档案 | 本项目内部数据模型 v1.0 | MACHINE实体 | 内部定义 |
| TERM-0008 | 机床实物实例 | Machine Instance | 具有实际交付、安装或运行记录的一台物理机床，可通过资产标识或序列信息追踪 | 生命周期/维护/案例 | 本项目内部数据模型 v1.0 | MINST实体 | 内部定义 |
| TERM-0009 | 关系限定条件 | Relationship Qualifier | 用于说明实体关系成立所需的机型、配置、版本、时间、地区或工况条件 | 全库数据模型 | 本项目内部数据模型 v1.0 | RELATIONSHIP-MODEL.md | 内部定义 |
| TERM-0010 | 生命周期状态 | Lifecycle Status | 表示实体记录处于候选、有效、废弃、合并或归档等管理阶段的字段 | 全库数据模型 | 本项目内部数据模型 v1.0 | KNOWLEDGE-MODEL.md | 内部定义 |
| TERM-0011 | 核验状态 | Verification Status | 表示实体或关系记录的证据核验进度与争议状态，不等同于生命周期状态 | 全库数据模型 | 本项目内部数据模型 v1.0 | KNOWLEDGE-MODEL.md | 内部定义 |
| TERM-0012 | 机床工具行业 | Machine tool industry | 围绕机床整机、控制与功能部件、刀具夹具、制造装配、系统集成、分销服务和终端加工应用形成的产业生态；本知识库按直接支撑数控机床的环节界定范围。 | 全库行业范围 | SRC-000001、SRC-000002、SRC-000004、SRC-000006 | industry-map.md | 有来源支持 |
| TERM-0013 | 机床整机厂/机床制造商 | Machine tool builder / OEM | 负责机床整机设计、制造、装配、集成或以自有品牌提供整机产品的组织；制造、品牌运营和经销服务角色应分别核验。 | 行业角色 | SRC-000004、SRC-000005 | industry-map.md | 有来源支持 |
| TERM-0014 | 加工中心 | Machining center | 面向多工序数控切削的机床类别；具体自动换刀、轴配置和工艺能力以具体型号规格为准。 | 机床分类 | SRC-000001、SRC-000004 | machine-tool-classification.md | 有来源支持 |
| TERM-0015 | 多任务/车铣复合机床 | Multi-tasking / mill-turn machine | 在同一平台集成两种或多种加工工艺（典型如车削与铣削）的设备；它是工艺集成维度，不是互斥的单一切削类别。 | 机床分类 | SRC-000011、SRC-000012、SRC-000013 | machine-tool-classification.md | 有来源支持 |
| TERM-0016 | 柔性制造单元 | Flexible Manufacturing Cell (FMC) | 由一台或多台机床及工件/托盘搬运、控制和相关辅助设备组成的自动化制造单元；具体边界依系统设计定义。 | 自动化与生产系统 | SRC-000004 | industry-map.md | 行业目录语境 |
| TERM-0017 | 柔性制造系统 | Flexible Manufacturing System (FMS) | 由多台可重配置加工设备、物料搬运和控制组成，能够在一定范围内适应产品或工艺变化的制造系统。 | 自动化与生产系统 | SRC-000004 | industry-map.md | 行业目录语境 |
| TERM-0018 | 机床附件与相关装备 | Machine-tool accessories and related equipment | 支持机床加工、装夹、刀具管理、测量、冷却、排屑、自动化和维护的附件/周边设备；统计分类中可能与机床主机分列。 | 产业链 | SRC-000003、SRC-000004 | industry-map.md | 有来源支持 |
| TERM-0019 | 数控系统 | Computerized Numerical Control (CNC) system | 将数控程序、插补/运动控制、逻辑控制、人机交互及相关接口结合起来的控制系统；具体功能边界因架构和产品等级而异。 | 控制系统 | SRC-000021、SRC-000022、SRC-000023、SRC-000024 | representative-ecosystem.md | 厂商产品语境 |

## 维护规则

- 为每个术语分配稳定ID；名称变化不复用或随意更改ID。
- 英文缩写首次出现时给出完整名称；同缩写多义时分别定义。
- 正式定义优先引用标准或权威来源，并记录版本和适用范围。
- 不将厂商特定命名直接当作行业通用术语。
