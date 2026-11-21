# 数据模型目录

本目录存放全库受控数据类型、关系谓词和JSON Schema。该数据模型属于本知识库内部约定，不代表行业标准。

## 文件

| 文件 | 用途 |
|---|---|
| entity-types.csv | 实体类型、ID前缀、主归属和身份边界 |
| relation-types.csv | 关系谓词、主体/客体类型和语义约束 |
| entity.schema.json | 实体记录JSON Schema，Draft 2020-12 |
| relationship.schema.json | 有向关系记录JSON Schema |
| source.schema.json | 来源证据记录JSON Schema |
| templates/ | 新建实体、关系和来源记录的占位模板 |

## 数据存储约定

- JSON用于单实体、关系、来源等有嵌套属性的数据记录。
- CSV用于固定列、规则扁平的数据目录和批量清单，采用UTF-8并保持稳定列名。
- Markdown用于人类可读的技术解释、模型治理和案例描述。
- 图片、动图和完整文档仍须保存在resouces对应章节目录；这里的Schema/CSV是知识库自身的文本结构文件，不是外部媒体附件。

## 校验要求

录入实体、关系或来源记录前，使用对应Schema校验JSON语法、必填字段、类型和枚举。JSON Schema无法代替业务规则校验，仍需检查ID唯一性、跨文件引用完整性、主体/客体类型兼容性、关系证据和章节归属。
