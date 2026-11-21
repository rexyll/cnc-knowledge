# 关系记录

每条关系保存为REL-xxxxxx.json，必须符合docs/data-model/relationship.schema.json。

记录方向为subject_id → predicate → object_id。谓词及主体/客体语义以docs/data-model/relation-types.csv为准。关键事实必须填写source_ids、核验状态及适用限定条件；不要使用含糊的自由文本谓词。



## 知识文章索引关系

`DERIVED_FROM`可用于表达知识条目对其他结构化实体的明确索引/内容派生关系。使用时应在qualifiers中写明article_path、article_version、reference_role和relationship_scope，并在notes中限定其仅表示内容导航与溯源。不得将该关系解释为制造、供货、组成、适用、兼容或标准符合性事实。
