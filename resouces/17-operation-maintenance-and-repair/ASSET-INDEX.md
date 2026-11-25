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
