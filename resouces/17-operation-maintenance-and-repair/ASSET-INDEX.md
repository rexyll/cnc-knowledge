# CH17 资源索引 — 操作、维护与维修

| 文件 | 类型 | 来源/作者 | 日期 | 权利状态 | 关联内容 | 说明 |
|---|---|---|---|---|---|---|
| operation-readiness-checklist.csv | CSV模板 / ASSET-000008 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T001 / overview.md / KNOW-000021 | 25项设备识别、开机准备、运行监视和维护维修边界检查项；结果初始为NOT_ASSESSED，不含型号级阈值或周期 |
| repair-work-order-template.csv | CSV模板 / ASSET-000009 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T001 / repair-workflow-and-records.md / KNOW-000021 | 维修工单身份、风险、授权、诊断、维修、备件、参数变更、复验和放行记录字段 |
| post-repair-verification-matrix.csv | CSV模板 / ASSET-000010 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T001 / repair-workflow-and-records.md / KNOW-000021 | 维修影响驱动的系统复验覆盖矩阵；无通用阈值，判据必须绑定OEM/合同/标准 |
| maintenance-task-matrix-template.csv | CSV模板 / ASSET-000011 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T002 / maintenance-management-system.md / KNOW-000022 | 维护任务、触发机制、OEM条款、责任角色和结果字段；周期及阈值留空 |
| maintenance-card-template.csv | CSV模板 / ASSET-000012 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T002 / maintenance-management-system.md / KNOW-000022 | 单项维护执行、测量、耗材和复核记录 |
| maintenance-consumables-register-template.csv | CSV模板 / ASSET-000013 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T002 / maintenance-management-system.md / KNOW-000022 | 润滑剂、冷却液、滤芯等规格、批次、有效期、库存和替代审批追溯 |
| haas-lathe-rd0035-selected-maintenance-examples.csv | 维护计划示例CSV / ASSET-000014 | Haas Automation官方手册摘要 | 2026-11-25 | 事实性有限摘要+官方链接；非手册副本 | CH17-T002 / maintenance-management-system.md / KNOW-000022 | RD0035 Revision A-04/2026精选任务/周期，仅限匹配的Haas车床配置，不得泛化 |
| component-replacement-work-package-template.csv | CSV模板 / ASSET-000015 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T003 / component-replacement-work-package.md / KNOW-000023 | 单次零部件更换的设备身份、OEM依据、作业授权、前置停工点、拆前基线、复装与放行字段 |
| component-tool-and-measurement-register-template.csv | CSV模板 / ASSET-000016 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T003 / component-replacement-work-package.md / KNOW-000023 | 工具、吊装器具、测量和诊断设备身份、能力、检验/校准状态追溯 |
| component-interface-and-replacement-compatibility-template.csv | CSV模板 / ASSET-000017 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T003 / component-replacement-work-package.md / KNOW-000023 | 机械、电气、流体、控制、软件、热/润滑和安全接口的替代兼容性审查 |
| component-family-impact-verification-matrix-template.csv | CSV矩阵模板 / ASSET-000018 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T003 / component-family-impact-assessment-and-verification.md / KNOW-000024 | 九类关键部件共57条影响审查与复验项目；初始待评估/未测试，不是型号级执行SOP |
| spindle-replacement-work-package-template.csv | CSV模板 / ASSET-000019 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T003 / spindle-servo-ballscrew-specialized-replacement-work-packages.md / KNOW-000025 | 主轴单元专项更换工作包，18项检查/35列；OEM值与步骤待机型映射 |
| servo-motor-encoder-replacement-work-package-template.csv | CSV模板 / ASSET-000020 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T003 / spindle-servo-ballscrew-specialized-replacement-work-packages.md / KNOW-000025 | 伺服电机/编码器专项更换工作包，17项检查/35列；无通用换相或参数值 |
| ballscrew-support-bearing-replacement-work-package-template.csv | CSV模板 / ASSET-000021 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T003 / spindle-servo-ballscrew-specialized-replacement-work-packages.md / KNOW-000025 | 滚珠丝杠/支撑轴承专项更换工作包，17项检查/35列；无通用预紧/扭矩值 |
| atc-tool-magazine-turret-replacement-work-package-template.csv | CSV模板 / ASSET-000022 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T003 / atc-chuck-hydraulic-specialized-replacement-work-packages.md / KNOW-000026 | ATC刀库/换刀机械手/刀塔专项工作包，20项检查/35列；OEM步骤与关键值待机型映射 |
| chuck-workholding-replacement-work-package-template.csv | CSV模板 / ASSET-000023 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T003 / atc-chuck-hydraulic-specialized-replacement-work-packages.md / KNOW-000026 | 卡盘/夹持专项工作包，18项检查/35列；夹持力、压力、转速及工件边界无通用值 |
| hydraulic-pneumatic-unit-replacement-work-package-template.csv | CSV模板 / ASSET-000024 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T003 / atc-chuck-hydraulic-specialized-replacement-work-packages.md / KNOW-000026 | 液压/气动动力单元专项工作包，20项检查/35列；介质、压力、蓄能器和设定值待OEM映射 |
| spare-part-master-data-template.csv | CSV模板 / ASSET-000025 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-management-and-lifecycle.md / KNOW-000027 | 备件身份、OEM料号/修订、BOM位号、机型/序列适用性、供应与储存来源字段 |
| spare-part-criticality-assessment-template.csv | CSV模板 / ASSET-000026 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-management-and-lifecycle.md / KNOW-000027 | 安全、生产、质量、冗余、可检测性、修复能力及供应风险评估字段；评分方法由企业批准 |
| spare-part-inventory-and-replenishment-template.csv | CSV模板 / ASSET-000027 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-management-and-lifecycle.md / KNOW-000027 | 库存分桶、需求窗口、交期证据、补货点/安全库存/最小最大量及盘点字段；不预填数值 |
| spare-part-substitution-approval-template.csv | CSV模板 / ASSET-000028 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-management-and-lifecycle.md / KNOW-000027 | 原件/候选件适用范围、机械电气流体软件安全兼容、工程批准和验证记录 |
| spare-part-lifecycle-and-obsolescence-template.csv | CSV模板 / ASSET-000029 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-management-and-lifecycle.md / KNOW-000027 | PCN/EOL、last-time-buy、服务支持、安装基数、替代迁移和缓解计划追踪 |
| repair-spare-consumption-feedback-template.csv | CSV模板 / ASSET-000030 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-management-and-lifecycle.md / KNOW-000027 | 工单、设备实例、拆下/安装件批次、领用/返修、补货和故障反馈关联 |
| spare-parts-enterprise-system-field-mapping-template.csv | CSV模板 / ASSET-000031 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-system-integration-and-data-governance.md / KNOW-000028 | ERP/CMMS/EAM/PLM字段映射、SoR、外部键、单位/代码集、同步、有效期、数据责任和审批字段 |
| spare-parts-data-quality-and-reconciliation-rules.csv | CSV规则目录 / ASSET-000032 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-system-integration-and-data-governance.md / KNOW-000028 | 16条建议数据质量与对账规则；初始PROPOSED，阈值、阻断方式、频率和责任人待企业批准 |
| spare-parts-stock-policy-decision-template.csv | CSV模板 / ASSET-000033 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-system-integration-and-data-governance.md / KNOW-000028 | 按备件/地点/机型配置记录需求、交期、供应风险、策略版本、库存参数审批及复核依据；数值留空 |
| spare-parts-transaction-lifecycle-control-matrix.csv | CSV控制矩阵 / ASSET-000034 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-physical-flow-and-transaction-controls.md / KNOW-000029 | 16个备件生命周期事务控制节点，覆盖触发、前置、证据、审批、状态、库存桶、异常、幂等与冲销字段 |
| spare-parts-raci-approval-matrix-template.csv | CSV矩阵模板 / ASSET-000035 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-physical-flow-and-transaction-controls.md / KNOW-000029 | 16项备件业务活动的建议RACI；角色分配初始PROPOSED，须企业授权制度批准 |
| spare-parts-end-to-end-acceptance-test-matrix.csv | CSV测试场景矩阵 / ASSET-000036 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-end-to-end-acceptance-testing.md / KNOW-000030 | 30个端到端测试用例/24列，覆盖主数据、BOM、采购收货、库存事务、替代、维修消耗、对账、生命周期与数据权限；初始NOT_RUN |
| spare-parts-acceptance-test-execution-record-template.csv | CSV测试执行模板 / ASSET-000037 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-end-to-end-acceptance-testing.md / KNOW-000030 | 30列表头空模板，记录环境/数据版本、预期与实际结果、数量影响、追溯/审计证据、缺陷和复测关联 |
| spare-parts-synthetic-test-dataset-manifest-template.csv | CSV模板 / ASSET-000038 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-synthetic-test-data-and-environment-readiness.md / KNOW-000031 | 29列表头空模板，登记数据集身份/版本、生成器、种子引用、对象域、覆盖用例、冻结、批准、敏感数据扫描与校验值 |
| spare-parts-test-environment-readiness-checklist.csv | CSV检查表 / ASSET-000039 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-synthetic-test-data-and-environment-readiness.md / KNOW-000031 | 22项/11列非生产环境就绪检查，覆盖隔离、权限、秘密管理、备份恢复、mock、事件、日志、安全和清理；全部NOT_ASSESSED |
| spare-parts-test-fixture-cross-reference-template.csv | CSV模板 / ASSET-000040 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-synthetic-test-data-and-environment-readiness.md / KNOW-000031 | 27列表头空模板，以合成ID关联主数据、BOM、采购收货、质量、库存、维修、审批和生命周期事件及其时序 |
| spare-parts-synthetic-fixture-baseline-v1-manifest.csv | CSV数据集清单 / ASSET-000041 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-synthetic-fixture-baseline-v1.md / KNOW-000032 | SPAREPARTS-SYN-BASE-001 v1.0.0元数据；单行清单，当前DRAFT，环境/测试层级未获批准 |
| spare-parts-synthetic-fixture-baseline-v1.csv | CSV合成夹具 / ASSET-000042 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-synthetic-fixture-baseline-v1.md / KNOW-000032 | 89条固定合成记录（67对象+22事件），27列；SYN-/FX-/EVT-虚构标识，测试重置组隔离 |
| spare-parts-synthetic-fixture-test-case-coverage-v1.csv | CSV用例映射 / ASSET-000043 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-synthetic-fixture-baseline-v1.md / KNOW-000032 | SPAT-001～SPAT-030共30行/11列，逐项关联正负夹具和事件；执行状态均NOT_RUN |
| README.md | 资源目录说明 | 项目原创 | 2026-11-25 | 原创 | CH17资源归档规则 | 目录用途、归档和来源登记要求 |

## 外部来源（只登记元数据与官方链接）

| 来源ID | 发布机构 | 文件/页面 | 本章用途 | 使用边界 |
|---|---|---|---|---|
| SRC-000382 | OSHA / U.S. Department of Labor | 29 CFR 1910.147 | 适用场景下危险能量控制/LOTO法规框架 | 美国法规；仅在法定范围内使用 |
| SRC-000383 | ISO | ISO 16090-1:2022 | 铣床/加工中心安全标准范围与版本 | 不复制标准全文；目录显示正在修订 |
| SRC-000384 | ISO | ISO/WD 16090-1 | 第三版工作草案状态 | 工作草案不是已发布标准 |
| SRC-000385 | ISO | ISO 23125:2015 | 车床/车削中心安全标准范围与版本 | 不复制标准全文；目录显示正在修订 |
| SRC-000386 | Haas Automation | Operators Manuals官方索引 | 按产品族检索操作和服务手册 | Haas资料示例，不泛化 |
| SRC-000387 | Haas Automation | Mill Operators Manual — Safety | 操作者维护与专业服务边界示例 | 仅适用对应Haas铣床资料 |
| SRC-000388 | Haas Automation | Lathe Maintenance | 型号/产品族专属维护计划示例 | 仅适用对应Haas车床配置 |

所有外部来源于2026-11-25核验。原始法规、标准和制造商手册未复制到本目录；保存全文需另行核验授权及再分发许可。
