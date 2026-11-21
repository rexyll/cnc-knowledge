# 来源记录

每条来源保存为SRC-xxxxxx.json，必须符合docs/data-model/source.schema.json。

来源记录只保存元数据和来源定位，不自动复制原始文件。必须区分authority_tier（来源权威等级）和evidence_kind（证据性质），并填写rights_status。完整资料仅在有合法保存依据时放入resouces对应章节目录。
