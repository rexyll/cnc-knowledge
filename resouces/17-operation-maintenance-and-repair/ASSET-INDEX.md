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
| spare-parts-inventory-state-transition-contract-v1.csv | CSV状态转移契约 / ASSET-000045 | 项目原创 | 2026-11-25 | 原创，待企业库存数据所有者批准映射 | CH17-T004 / spare-parts-synthetic-fixture-baseline-v1.md / KNOW-000032 | 22类事件的双边账户转移契约；来源/目标账户和审批证据均留空，状态NOT_APPROVED，不可用于业务过账 |
| spare-parts-synthetic-fixture-reset-profiles-v1.csv | CSV场景重置配置 / ASSET-000044 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-synthetic-fixture-baseline-v1.md / KNOW-000032 | 30行/15列，逐用例登记直接夹具、依赖闭包、reset group、父先子后装载、反向本地包清理、幂等键和NOT_RUN状态；FILESYSTEM_STAGING_ONLY |
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
| spare-parts-inventory-account-catalog-candidates-v1.csv | CSV候选账户字典 / ASSET-000046 | 项目原创 | 2026-11-25 | 原创，候选分类待企业批准 | CH17-T004 / KNOW-000032 | 13类实物、外部对方、备忘承诺及观察账户候选；全部PROPOSED_NOT_APPROVED，不构成生产账户定义 |
| spare-parts-inventory-dimension-dictionary-candidates-v1.csv | CSV候选维度字典 / ASSET-000047 | 项目原创 | 2026-11-25 | 原创，候选维度待企业批准 | CH17-T004 / KNOW-000032 | 物料、批次、库位、所有权、状态、单位、工单、采购行维度候选；全部PROPOSED_NOT_APPROVED |
| spare-parts-inventory-opening-balance-template-v1.csv | CSV空白模板 / ASSET-000048 | 项目原创 | 2026-11-25 | 原创空白模板 | CH17-T004 / KNOW-000032 | 期初余额模板仅含表头，不含任何预填数量或库存快照 |
| spare-parts-inventory-opening-state-scenario-matrix-v1.csv | CSV场景矩阵 / ASSET-000049 | 项目原创 | 2026-11-25 | 原创，场景预期待批准 | CH17-T004 / KNOW-000032 | 9个场景的期初输入需求、账户候选和守恒断言；全部PROPOSED_NOT_APPROVED/NOT_RUN |
| spare-parts-multidimensional-inventory-model-test-cases-v1.csv | CSV模型测试矩阵 / ASSET-000050 | 项目原创 | 2026-11-25 | 原创纯合成测试定义 | CH17-T004 / KNOW-000032 | 17项多维库存余额模型数学性质测试；不构成企业业务验收证据 |
| spare-parts-inventory-event-ledger-test-cases-v1.csv | CSV事件账本测试矩阵 / ASSET-000051 | 项目原创 | 2026-11-25 | 原创纯合成测试定义 | CH17-T004 / KNOW-000032 | 17个事件账本断言场景；不构成企业业务验收证据 |
| spare-parts-inventory-ledger-integrity-test-cases-v1.csv | CSV完整性/快照测试矩阵 / ASSET-000052 | 项目原创 | 2026-11-25 | 原创纯合成测试定义 | CH17-T004 / KNOW-000032 | 15个断言场景，覆盖规范化序列化、事件SHA-256链、篡改/缺失/乱序检测、版本化快照、前缀校验、增量恢复与全量重放对比；不构成生产审计证据 |
| spare-parts-inventory-ledger-persistence-test-cases-v1.csv | CSV本地持久化/故障恢复测试矩阵 / ASSET-000053 | 项目原创 | 2026-11-25 | 原创纯合成测试定义 | CH17-T004 / KNOW-000032 | 11个故障场景，覆盖代际目录、原子CURRENT发布、崩溃中断、旧代际恢复、文件损坏、COMMIT缺失、版本与路径安全；不构成生产持久化验收证据 |
| spare-parts-inventory-ledger-concurrency-test-cases-v1.csv | CSV并发写入/多进程恢复测试矩阵 / ASSET-000054 | 项目原创 | 2026-11-25 | 原创纯合成测试定义 | CH17-T004 / KNOW-000032 | 10个场景，覆盖POSIX跨进程锁、锁超时、CAS冲突、并发唯一胜者、进程崩溃释放锁和恢复；不构成跨主机/生产并发验收证据 |

| spare-parts-inventory-ledger-read-gc-test-cases-v1.csv | CSV读取一致性与代际回收测试矩阵 / ASSET-000055 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-synthetic-fixture-baseline-v1.md / KNOW-000032 | 10个纯合成场景，覆盖共享读锁、writer/GC协调、CURRENT保护、dry-run、最近N代与最短年龄保留、异常清理恢复和读写回收压力；不构成跨平台/生产删除验收证据 |

| spare-parts-inventory-ledger-backup-restore-test-cases-v1.csv | CSV备份完整性与隔离恢复测试矩阵 / ASSET-000056 | 项目原创 | 2026-11-25 | 原创，可在项目内使用 | CH17-T004 / spare-parts-synthetic-fixture-baseline-v1.md / KNOW-000032 | 10个纯合成场景，覆盖版本化备份清单、负载SHA-256/长度校验、账本链与快照验证、篡改拒绝、源代际回收后的独立恢复及中断恢复；不构成异地/生产灾备验收 |

| spare-parts-inventory-backup-retention-policy-template.csv | CSV空白模板 / ASSET-000057 | 项目原创 | 2026-11-26 | 原创，可在项目内使用 | CH17-T004 / spare-parts-inventory-backup-governance.md / KNOW-000033 | 备份保留策略空白模板；所有期限、法律/合同依据及审批字段留空。 |
| spare-parts-inventory-backup-rpo-rto-requirements-template.csv | CSV空白模板 / ASSET-000058 | 项目原创 | 2026-11-26 | 原创，可在项目内使用 | CH17-T004 / spare-parts-inventory-backup-governance.md / KNOW-000033 | RPO/RTO目标空白模板；数值、时钟边界、测量方法和审批待企业BIA与责任人确定。 |
| spare-parts-inventory-backup-security-key-management-template.csv | CSV空白模板 / ASSET-000059 | 项目原创 | 2026-11-26 | 原创，可在项目内使用 | CH17-T004 / spare-parts-inventory-backup-governance.md / KNOW-000033 | 安全/密钥管理空白评估模板；禁止录入任何密钥或秘密，控制值及审批待安全责任方确认。 |
| spare-parts-inventory-backup-offsite-storage-assessment-template.csv | CSV空白模板 / ASSET-000060 | 项目原创 | 2026-11-26 | 原创，可在项目内使用 | CH17-T004 / spare-parts-inventory-backup-governance.md / KNOW-000033 | 异地存储供应商评估空白模板；不指定厂商、区域、合同条款或服务等级。 |
| spare-parts-inventory-backup-restore-drill-acceptance-matrix-v1.csv | CSV测试矩阵 / ASSET-000061 | 项目原创 | 2026-11-26 | 原创，可在项目内使用 | CH17-T004 / spare-parts-inventory-backup-governance.md / KNOW-000033 | 10个恢复演练场景；全部PROPOSED_NOT_APPROVED / NOT_RUN，不构成真实灾备测试结果。 |

| spare-parts-inventory-backup-storage-provider-capability-matrix-template.csv | CSV能力评估模板 / ASSET-000062 | 项目原创 | 2026-11-26 | 原创，可在项目内使用 | CH17-T004 / spare-parts-inventory-backup-storage-adapter.md / KNOW-000034 | 供应商中立的对象存储能力评估空白表；条件创建、版本控制、对象锁、加密、TLS、读后写一致性、区域、SLA和证据均待实测/批准。 |
| spare-parts-inventory-backup-storage-adapter-test-cases-v1.csv | CSV测试矩阵 / ASSET-000063 | 项目原创 | 2026-11-26 | 原创，可在项目内使用 | CH17-T004 / spare-parts-inventory-backup-storage-adapter.md / KNOW-000034 | 12个纯合成场景覆盖Provider条件创建、回执最后提交、失败续传、内容篡改、版本固定、路径安全和隔离恢复；不代表真实云Provider验收。 |

| spare-parts-inventory-backup-provider-identity-access-review-template.csv | CSV空白模板 / ASSET-000064 | 项目原创 | 2026-11-26 | 原创，可在项目内使用 | CH17-T004 / spare-parts-inventory-backup-provider-security-and-resilience.md / KNOW-000035 | Provider主体身份、动作与前缀授权、租户隔离、凭据托管、审计和审批评估模板；无默认权限方案。 |
| spare-parts-inventory-backup-orphan-inventory-reclamation-review-template.csv | CSV空白模板 / ASSET-000065 | 项目原创 | 2026-11-26 | 原创，可在项目内使用 | CH17-T004 / spare-parts-inventory-backup-provider-security-and-resilience.md / KNOW-000035 | 未提交对象/分块会话只读盘点和回收审批记录模板；不执行删除，不预设保留期。 |
| spare-parts-inventory-backup-provider-resilience-test-matrix-v1.csv | CSV测试矩阵 / ASSET-000066 | 项目原创 | 2026-11-26 | 原创，可在项目内使用 | CH17-T004 / spare-parts-inventory-backup-provider-security-and-resilience.md / KNOW-000035 | 14项Mock合成测试场景，覆盖最小权限、租户隔离、分块续传、故障恢复和孤儿对象审查；不代表真实云验收。 |

| spare-parts-inventory-backup-provider-retry-consistency-test-matrix-v1.csv | CSV测试矩阵 / ASSET-000067 | 项目原创 | 2026-11-26 | 原创，可在项目内使用 | CH17-T004 / spare-parts-inventory-backup-provider-retry-consistency-and-recovery.md / KNOW-000036 | 13条合成场景，覆盖限流退避、写成功响应丢失、延迟可见、重试耗尽、版本切换/缺失、分块响应丢失及永久错误不重试；不代表真实云Provider验收。 |

| spare-parts-inventory-backup-provider-circuit-breaker-bulkhead-test-matrix-v1.csv | CSV测试矩阵 / ASSET-000068 | 项目原创 | 2026-11-26 | 原创，可在项目内使用 | CH17-T004 / spare-parts-inventory-backup-provider-circuit-breaker-bulkhead-and-budget.md / KNOW-000037 | 14条合成场景，覆盖熔断打开/半开/恢复、探测配额、读写域隔离、舱壁容量/释放、任务级总重试预算与并发任务隔离；不代表分布式/生产Provider验收。 |

| spare-parts-inventory-backup-provider-fair-scheduling-test-matrix-v1.csv | CSV测试矩阵 / ASSET-000069 | 项目原创 | 2026-11-26 | 原创，可在项目内使用 | CH17-T004 / spare-parts-inventory-backup-provider-fair-scheduling-and-tenant-isolation.md / KNOW-000038 | 15项纯合成场景覆盖优先级、aging防饥饿、租户配额、排队取消、任务deadline和公平舱壁观测；不代表分布式/生产Provider验收。 |

| spare-parts-inventory-backup-provider-shared-coordination-test-matrix-v1.csv | CSV测试矩阵 / ASSET-000070 | 项目原创 | 2026-11-26 | 原创，可在项目内使用 | CH17-T004 / spare-parts-inventory-backup-provider-shared-coordination-and-lease-recovery.md / KNOW-000039 | 24项同进程多Adapter共享并发、租户配额、令牌桶、租约过期/续期/fencing、异常路径outcome_unknown及协调服务故障注入模拟场景；不代表跨进程/生产协调验收。 |
| spare-parts-inventory-backup-provider-admission-queue-bound-test-matrix-v1.csv | CSV测试矩阵 / ASSET-000071 | 项目原创 | 2026-11-26 | 原创，可在项目内使用 | CH17-T004 / spare-parts-inventory-backup-provider-admission-queue-bounds-and-recovery.md / KNOW-000041 | 7条合成场景覆盖本地/共享等待队列上限、超额拒绝、零等待配置、协调器等待中故障清理与恢复后重新准入；不代表跨进程/生产容量验收。 |
| spare-parts-inventory-backup-provider-sqlite-coordinator-test-matrix-v1.csv | CSV测试矩阵 / ASSET-000072 | 项目原创 | 2026-11-26 | 原创，可在项目内使用 | CH17-T004 / spare-parts-inventory-backup-provider-sqlite-persistent-admission-coordinator.md / KNOW-000042 | 10条合成场景覆盖本地SQLite多进程原子准入、重启租约恢复、持久fencing、request_id幂等、响应丢失、续租、策略绑定和等待队列共享；不代表多主机/生产协调器验收。 |
