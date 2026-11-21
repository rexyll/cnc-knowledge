# 核心实体登记表

本文件定义知识库核心实体的稳定ID和主记录位置。详细属性可在章节数据文件中维护，避免跨章节重复录入。

| 实体类型 | ID前缀 | 示例ID | 主记录位置 |
|---|---|---|---|
| 知识条目 | KNOW | KNOW-000001 | 对应知识章节 |
| 机床类型 | MTYPE | MTYPE-000001 | 02-machine-types-and-products |
| 整机/机型 | MACHINE | MACHINE-000001 | 02 / 22 |
| 厂商 | VENDOR | VENDOR-000001 | 19-manufacturers-products-and-supply-chain |
| 产品型号 | PRODUCT | PRODUCT-000001 | 19-manufacturers-products-and-supply-chain |
| 子系统 | SUBSYS | SUBSYS-000001 | 对应技术章节 |
| 零部件 | PART | PART-000001 | 04-components-materials-and-manufacturing |
| 材料 | MAT | MAT-000001 | 04-components-materials-and-manufacturing |
| 标准 | STD | STD-000001 | 15-standards-safety-and-compliance |
| 协议 | PROTO | PROTO-000001 | 10-drives-fieldbus-and-communications |
| 故障 | FAULT | FAULT-000001 | 18-fault-diagnosis-and-reliability |
| 案例 | CASE | CASE-000001 | 22-case-studies-and-reference-machines |
| 资源文件 | ASSET | ASSET-000001 | 对应 `resouces/<章节目录>/ASSET-INDEX.md` |

## ID规则

- ID创建后保持稳定，不因标题或文件路径调整而重用。
- 一个实体只有一个主记录；其他章节使用链接和ID引用。
- 记录实体类型、标准名称、别名、来源、状态和最后核验日期。
- 尚未核验的实体可登记为候选，但状态必须标为待核验。
