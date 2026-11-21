# 知识编写与数据模板

| 模板 | 用途 | 正式使用位置 |
|---|---|---|
| KNOWLEDGE-ARTICLE-TEMPLATE.md | 概念、系统、部件、算法、标准和专题正文 | docs/<章节目录>/<专题>.md |
| ASSET-INDEX-TEMPLATE.md | 本章图片、动图及完整资料的资源索引 | docs/<章节目录>/ASSET-INDEX.md |
| CHAPTER-DATA-DICTIONARY-TEMPLATE.csv | 本章实体类型的专属字段定义 | docs/data-model/chapter-dictionaries/CHxx.csv |

## 使用规则

- 复制模板后替换所有占位符；不适用的小节可以删除并说明范围，不可保留伪造值。
- 新建正文时分配KNOW实体ID，并同步创建实体记录、SRC引用和ASSET关联（适用时）。
- 资源文件仍按根TaskPlan归档在resouces对应章节目录。
- 数据字典定义字段语义和校验规则，不是实体实例数据。没有可靠数据时不得用示例值冒充真实数据。
