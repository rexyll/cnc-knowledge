# 关系记录

每条关系保存为REL-xxxxxx.json，必须符合docs/data-model/relationship.schema.json。

记录方向为subject_id → predicate → object_id。谓词及主体/客体语义以docs/data-model/relation-types.csv为准。关键事实必须填写source_ids、核验状态及适用限定条件；不要使用含糊的自由文本谓词。
