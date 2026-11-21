# 实体记录

实体文件路径：<PREFIX>/<ENTITY-ID>.json。

示例路径结构：PART/PART-000123.json。目录按实体ID前缀建立；正式记录需符合docs/data-model/entity.schema.json，并通过ID唯一性检查。

实体主记录负责名称、分类、生命周期、核验状态和类型专属属性。实体之间的组成、制造、供货、接口、兼容、故障等关联使用relationships目录中的独立关系记录。
