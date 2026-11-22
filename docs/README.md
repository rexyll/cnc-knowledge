# 知识正文目录

本目录存放数控机床各知识板块的正文、技术专题和结构化数据说明。当前初始化提交只建立章节入口；技术内容必须按根目录 `TaskPlan.md` 和对应章节任务计划逐项研究后补充。

## 章节导航

- [01. 行业概况与基础知识](./01-industry-and-fundamentals/README.md) — 数控机床行业边界、产业链、发展历程、基本原理、术语和知识分类。
- [02. 数控机床分类与产品](./02-machine-types-and-products/README.md) — 数控车床、铣床、加工中心、磨床、齿轮加工、特种加工、复合加工及专用机床的分类、结构和产品特征。
- [03. 整机架构与机械结构](./03-system-architecture-and-mechanics/README.md) — 整机功能架构、床身与基础件、运动部件、导轨丝杠、主轴、传动、润滑、冷却、防护和排屑等机械系统。
- [整机功能架构与子系统接口](03-system-architecture-and-mechanics/architecture.md)
- [数控机床主要机械结构、导向与进给传动](03-system-architecture-and-mechanics/major-mechanical-structures.md)
- [04. 零部件、材料与制造工艺](./04-components-materials-and-manufacturing/README.md) — 机床零部件目录、零件规格、材料牌号与性能、热处理、表面处理、加工制造工艺及部件可替代关系。
- [05. 刀具、工装与工件装夹系统](./05-tooling-fixtures-and-workholding/README.md) — 刀具、刀柄、接口、刀库、自动换刀、夹具、卡盘、工作台、工件定位夹紧、测头和刀具/工件测量。
- [06. 电气与电子系统](./06-electrical-electronic-systems/README.md) — 电气柜、供配电、保护、电机与执行器接线、传感器、继电器、接触器、I/O、电路板、电气原理图和电气安全接口。
- [07. 数控系统、控制器与 PLC](./07-cnc-controller-and-plc/README.md) — CNC数控装置、插补控制、PLC逻辑、HMI控制接口、I/O、机床参数、宏程序、通道和数控系统配置。
- [08. 伺服、主轴与运动控制](./08-servo-spindle-and-motion-control/README.md) — 伺服驱动器、电机、主轴电机/驱动、编码器、反馈链、轴控制、同步控制和运动性能。
- [09. 操作系统与嵌入式平台](./09-os-embedded-platforms/README.md) — 数控系统所使用的实时/通用操作系统、嵌入式硬件平台、启动链、实时调度、驱动框架和系统维护。
- [10. 驱动、现场总线与工业通信](./10-drives-fieldbus-and-communications/README.md) — 驱动接口、工业以太网、现场总线、实时通信、设备配置、网络拓扑、诊断和互操作。
- [11. 软件架构与接口设计](./11-software-architecture-and-interfaces/README.md) — 数控软件总体架构、模块边界、进程/线程、API、数据模型、配置、日志、诊断、升级和软件工程实践。
- [12. 控制与加工算法](./12-control-and-machining-algorithms/README.md) — 插补、轨迹规划、加减速、前瞻、坐标变换、误差补偿、主轴/进给控制、加工优化和算法验证。
- [13. CAD/CAM、数控编程与加工工艺](./13-cad-cam-programming-and-process/README.md) — CAD/CAM/CAPP、NC程序、G/M代码、工艺规划、切削参数、后处理、仿真和加工应用。
- [14. 性能指标、计量检测与验收](./14-performance-metrology-and-acceptance/README.md) — 几何精度、定位精度、重复定位、动态特性、主轴性能、热特性、加工精度、可靠性及测试验收方法。
- [15. 行业标准、安全与合规](./15-standards-safety-and-compliance/README.md) — 数控机床相关国家/行业/国际标准、机械安全、电气安全、功能安全、EMC、环境要求和合规管理。
- [16. 制造、装配、安装与调试](./16-manufacturing-assembly-installation/README.md) — 机床制造流程、精密装配、安装基础、运输就位、精度恢复、电气接线、上电、调试和交付。
- [17. 操作、维护与维修](./17-operation-maintenance-and-repair/README.md) — 机床操作规范、开停机、加工准备、日常保养、计划维护、零部件拆装更换、备件策略和维修记录。
- [18. 故障诊断与可靠性](./18-fault-diagnosis-and-reliability/README.md) — 机械、电气、数控、伺服、通信、软件和加工质量故障，以及根因分析、可靠性、可维护性和故障统计。
- [19. 厂商、产品与供应链](./19-manufacturers-products-and-supply-chain/README.md) — 数控机床整机厂、数控系统、伺服驱动、主轴、导轨丝杠、轴承、刀具、传感器及备件供应商和产品目录。
- [20. BOM、图纸与工程技术文档](./20-bom-drawings-and-technical-documents/README.md) — 整机/子系统BOM、零件清单、电气BOM、图纸、规格书、手册、技术变更、文档版本和数据关联。
- [21. 数字化、联网与智能制造](./21-digitalization-and-smart-manufacturing/README.md) — 数控机床联网、数据采集、状态监测、工业信息模型、MES/ERP集成、能耗、预测性维护、数字孪生和网络安全。
- [22. 典型机床、工程案例与系统拆解](./22-case-studies-and-reference-machines/README.md) — 典型机床整机档案、系统拆解、配置分析、方案对比、制造/使用案例和经验证的工程实践。

## 全库知识模型与公共资料

- [统一知识实体模型](KNOWLEDGE-MODEL.md)
- [跨章节实体关系模型](RELATIONSHIP-MODEL.md)
- [数据模型与JSON Schema目录](data-model/README.md)

## 行业地图与代表性厂商

- [数控机床行业全景图](01-industry-and-fundamentals/industry-map.md)
- [数控机床基本原理、坐标系与运动链](01-industry-and-fundamentals/cnc-machine-fundamentals.md)
- [行业实体与关系索引](01-industry-and-fundamentals/entity-relationship-index.md)
- [数控机床分类体系](02-machine-types-and-products/machine-tool-classification.md)
- [主要数控机床类型技术档案](02-machine-types-and-products/machine-type-technical-archives.md)
- [典型数控机床产品与型号规格目录](02-machine-types-and-products/representative-model-catalog.md)
- [数控机床选型方法与工程比较矩阵](02-machine-types-and-products/machine-tool-selection-methodology.md)
- [代表性厂商与系统生态图](19-manufacturers-products-and-supply-chain/representative-ecosystem.md)
- [整机与数控系统厂商档案](19-manufacturers-products-and-supply-chain/machine-tool-oem-and-system-vendor-profiles.md)
- [关键部件供应商与产品目录](19-manufacturers-products-and-supply-chain/key-component-suppliers-and-products.md)
- [供应链比较、替代验证与风险管理](19-manufacturers-products-and-supply-chain/supply-chain-comparison-and-risk-management.md)

## 质量门禁与覆盖度

- [质量门禁与章节覆盖度规范](QUALITY-GATES.md)
- [22章覆盖度矩阵](coverage/CHAPTER-COVERAGE.csv)

## 写作、引用与资源模板

- [统一知识文章模板](templates/KNOWLEDGE-ARTICLE-TEMPLATE.md)
- [资源索引模板](templates/ASSET-INDEX-TEMPLATE.md)
- [章节数据字段字典模板](templates/CHAPTER-DATA-DICTIONARY-TEMPLATE.csv)
- [来源与引用规范](REFERENCE-GUIDE.md)
- [结构化数据记录路径](data/README.md)

## 全库公共资料

- [术语表](./GLOSSARY.md)
- [核心实体登记表](./ENTITY-REGISTRY.md)
- [章节任务计划索引](./TaskPlan/README.md)

## 正文组织约定

章节内容尽量按“基础概念 / 结构与原理 / 参数与规格 / 设计与选型 / 操作与维护 / 故障与案例 / 来源与参考”组织。大篇幅资料拆分为主题文档；结构化数据使用可审查的CSV/JSON/表格格式，并记录字段含义和数据来源。任何图片、动图或完整资料文件均存放在对应的 `resouces/<章节目录>/`，正文通过相对路径引用。
