# 跨章节实体关系模型

> 模型版本：1.0  
> 机器可读定义：data-model/relationship.schema.json  
> 受控谓词目录：data-model/relation-types.csv

## 1. 关系记录结构

每条关系采用有向三元组：

**subject_id — predicate → object_id**

并附加限定条件、来源证据、核验状态、置信等级和有效期。

| 字段 | 说明 |
|---|---|
| relation_id | 稳定关系ID，格式REL-六位序号 |
| subject_id | 关系主体实体ID |
| predicate | 受控关系谓词，表达明确语义和方向 |
| object_id | 关系客体实体ID |
| qualifiers | 型号、配置、版本、工况、地区、数量、安装位置和有效期等限定条件 |
| source_ids | 支撑这条关系的来源ID |
| verification_status | unverified / in_review / verified / disputed / rejected |
| confidence | high / medium / low / unknown；表示现有证据强弱，不是统计概率 |
| valid_from / valid_to | 关系事实的有效时间范围 |
| notes | 额外解释、争议或待核实信息 |

## 2. 核心关系类别

### 2.1 机型、产品和组织

- MODEL_OF：整机型号归属某机床类型。
- INSTANCE_OF：一台实物机床属于某整机型号。
- MANUFACTURED_BY：产品/零件由组织制造。
- BRANDED_AS：产品使用某品牌。
- SUPPLIED_BY：部件/产品由供应商供货。
- DISTRIBUTED_BY：产品通过经销/代理组织分销。

### 2.2 整机、子系统和部件

- HAS_SUBSYSTEM：整机或系统包含某子系统。
- HAS_PART / PART_OF：表达部件组成关系；尽量选择一个规范方向记录，避免重复边。
- USES_MATERIAL：零部件采用某材料，需注明材料状态或应用部位。
- PROCESSED_BY：零件/材料经过某制造或加工过程。

### 2.3 控制、软件与通信

- EXPOSES_INTERFACE：设备、子系统或软件提供某接口。
- CONNECTS_TO：两个接口之间具有物理或逻辑连接/兼容关系。
- USES_PROTOCOL：软件、设备或子系统使用某通信协议。
- IMPLEMENTS：软件/产品实现某算法或协议。
- CARRIES_SIGNAL：接口承载某信号/数据点。
- CONTROLS：软件或控制子系统控制执行对象。
- DEPENDS_ON：软件、算法或产品依赖其他软件/协议/接口。

### 2.4 参数、性能和验证

- HAS_PARAMETER：系统或软件具有参数定义。
- HAS_METRIC：机床/产品具有某性能指标定义或声明。
- MEASURES：仪器/系统测量某性能指标。
- CONFORMS_TO：对象符合或声称符合某标准；必须说明是厂商声明、认证、测试还是评估。
- VERIFIED_BY：对象或关系由测试方法、测量记录、文档或案例提供验证证据。

### 2.5 文档、资源、维护和故障

- DOCUMENTED_BY：对象由某文档说明。
- REPRESENTED_BY / HAS_ASSET：文档或实体关联仓库内资源文件。
- HAS_FAULT_MODE：机型/部件/子系统存在某故障模式。
- INDICATED_BY：故障模式可能由报警/诊断码指示；报警通常不唯一指向根因。
- CAUSED_BY：故障可能由某部件、子系统、工艺或条件导致，必须有证据。
- RESOLVED_BY：故障可按某维护程序或案例处理。
- APPLIES_TO：程序、测试、标准、案例或算法适用于某机型/产品/子系统。
- SUPERSEDES：新版本/型号/标准替代旧对象，保留历史。
- DERIVED_FROM：当前记录从文档、测量、案例或其他实体派生。

完整的主体/客体限制和使用说明以relation-types.csv为准。

## 3. 关系使用规则

1. 优先使用具体谓词；禁止用语义含糊的“关联”“相关”或自由文本关系替代受控谓词。
2. 关系必须有明确方向；不得因自然语言语序而反转主客体。
3. 兼容、制造、供货、认证和故障根因等容易被误读的关系，必须提供来源和适用条件。
4. 一个事实适用于特定机型、配置、软件版本或工况时，将限定条件写入qualifiers。
5. 同一事实有多个来源时可引用多个SRC；来源冲突时将状态标为disputed并说明冲突。
6. 不以关系存在推断未记录的反向关系；如需反向查询，应由程序按谓词方向推导。
7. CAUSED_BY、CONFORMS_TO、CONNECTS_TO、SUPERSEDES等关系默认不自动标为verified。
8. 删除或纠正错误关系时保留变更记录；必要时将旧关系标为rejected或失效，不静默抹除。
9. 避免关系爆炸：只有能支持检索、选型、结构理解、诊断或溯源的关系才建立。
10. 所有关系目标必须能解析到唯一实体ID；尚未建档的目标先创建candidate实体或列为待补充事项。

## 4. 典型跨章节查询路径

- 机床型号 → 类型 → 结构子系统 → 零部件 → 材料 → 制造工艺 → 供应商 → 资源文档。
- 机床型号 → CNC/PLC/驱动产品 → 通信协议 → 接口 → 信号/参数 → 测试/性能指标。
- 故障模式 → 报警码 → 可能部件/子系统 → 诊断证据 → 维护程序 → 维修案例。
- 性能指标 → 测试方法 → 测量记录 → 适用标准 → 对应机床型号/配置。

## 5. 交付状态

关系谓词目录和关系Schema已建立。具体厂商、机型、部件、协议和故障关系需在各章节研究过程中逐条录入并核验；模型初始化不代表真实实体关系已经填充。
