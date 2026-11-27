# 17. 操作、维护与维修

**English:** Operation, Maintenance and Repair  
**范围：** 机床操作规范、开停机、加工准备、日常保养、计划维护、零部件拆装更换、备件策略和维修记录。

## 本章覆盖内容

- 操作面板、运行模式、程序装载、工件/刀具准备和状态监控
- 每日/每周/每月/年度维护、润滑、冷却液、过滤和清洁
- 部件拆卸、更换、复装、校准、参数备份和复验
- 备件管理、维修工单、保养记录、维护周期和寿命管理

## 本章任务计划

[打开本章 TaskPlan](../TaskPlan/17-operation-maintenance-and-repair/TaskPlan.md)

本章知识内容按任务计划逐步研究，不预填未经核实的技术参数或结论。第一版框架见 [机床操作、维护与维修总览](overview.md)；维修闭环见 [数控机床维修工作流、工单与维修后复验](repair-workflow-and-records.md)；计划维护体系见 [数控机床计划维护体系与维护任务管理](maintenance-management-system.md)；部件更换工作包见 [数控机床零部件更换工作包与复验框架](component-replacement-work-package.md)。 关键部件族审查见 [关键部件更换影响分析与复验矩阵](component-family-impact-assessment-and-verification.md)。 主轴/伺服/丝杠专项模板见 [主轴、伺服与滚珠丝杠专项更换工作包](spindle-servo-ballscrew-specialized-replacement-work-packages.md)。开机准备检查、维修工单、维修后复验矩阵、维护任务矩阵、维护卡和耗材登记均位于本章resouces目录。

## 建议正文结构

- `overview.md`：章节总览、概念和分类。
- `architecture.md` / `principles.md`：结构、原理和系统关系（适用时）。
- `specifications.md`：参数、型号、接口和指标（适用时）。
- `procedures/`：设计、制造、安装、操作或维护专题（适用时）。
- `cases/`：工程案例、测试和故障分析（适用时）。
- `ASSET-INDEX.md`：本章在 `resouces/17-operation-maintenance-and-repair/` 中的资源索引。

## 相关资源

本章图片、动图和有权保存的完整文档统一放在 [`resouces/17-operation-maintenance-and-repair/`](../../resouces/17-operation-maintenance-and-repair/README.md)。正文使用相对链接引用资源。外部版权受限资料只记录合法元数据和官方链接。

## 来源与审查

事实性内容需记录来源、版本、适用机型/系统、核验日期和证据等级；未知项显式标记待核实。安全、版权和保密要求遵循根目录 `TaskPlan.md`。


本轮新增 [刀库/换刀、卡盘夹持与液压气动专项更换工作包](atc-chuck-hydraulic-specialized-replacement-work-packages.md)，对应三份CSV模板位于本章 `resouces/17-operation-maintenance-and-repair/`。


备件管理与数据闭环见 [数控机床备件管理、替代审批与生命周期闭环](spare-parts-management-and-lifecycle.md)，六份备件主数据、关键度、库存补货、替代审批、生命周期及维修消耗反馈模板位于本章 `resouces/17-operation-maintenance-and-repair/`。


备件跨系统数据治理见 [数控机床备件系统集成、字段映射与数据治理](spare-parts-system-integration-and-data-governance.md)，字段映射、数据质量/对账规则和库存策略决策模板位于本章 `resouces/17-operation-maintenance-and-repair/`。


备件实物流转及事务控制见 [数控机床备件实物流转、事务控制与责任矩阵](spare-parts-physical-flow-and-transaction-controls.md)，包括生命周期控制矩阵和企业待批准的RACI责任矩阵，资源位于本章 `resouces/17-operation-maintenance-and-repair/`。


备件验收与测试证据见 [数控机床备件端到端验收场景与测试证据规范](spare-parts-end-to-end-acceptance-testing.md)，包含30个未执行测试规格和每次测试的证据记录模板；资源归档于本章 `resouces/17-operation-maintenance-and-repair/`。

备件测试数据与环境准备见 [数控机床备件合成测试数据集与环境就绪规范](spare-parts-synthetic-test-data-and-environment-readiness.md)，配套包含数据集清单、22项环境就绪检查和合成夹具对象/事件交叉引用模板；环境检查初始均为NOT_ASSESSED，不能视作已获企业授权。

备件合成测试夹具基线见 [备件合成测试夹具基线 v1.0.0](spare-parts-synthetic-fixture-baseline-v1.md)：包括89条静态对象/事件记录和SPAT-001～SPAT-030逐项映射。该数据集当前为DRAFT，所有测试仍NOT_RUN，不可视作已获企业环境批准。

备件合成夹具基线附带 [本地静态校验工具](../../scripts/spare_parts_fixture_validator.py) 和 [单元测试](../../tests/test_spare_parts_fixture_validator.py)。工具只读取本地CSV，不连接企业系统；CI会生成JSON验证报告Artifact。

备件合成夹具现提供 [30项场景重置配置](../../resouces/17-operation-maintenance-and-repair/spare-parts-synthetic-fixture-reset-profiles-v1.csv) 与 [本地场景包生成器](../../scripts/spare_parts_fixture_loader.py)。该工具仅在指定目录生成文件系统场景包和PLAN_ONLY重置计划，不连接或写入企业数据库；CI会生成全部30个场景包供审查。

备件合成夹具增加 [离线场景包校验与事件期望投影工具](../../scripts/spare_parts_scenario_runner.py)。它逐场景验证包哈希/依赖/事件顺序，并按reset_group独立列出夹具声明的数量增量。模拟结果PASS仅代表静态包和期望事件投影一致；业务规则未执行，30项测试仍NOT_RUN。

库存状态机内核见 [独立双边转移模型](../../scripts/spare_parts_inventory_state_model.py)，配套 [22类事件转移契约](../../resouces/17-operation-maintenance-and-repair/spare-parts-inventory-state-transition-contract-v1.csv) 当前均未获批准，CI只验证内核性质与审批门禁，不代表业务状态机已激活。

新增 [候选库存账户字典](../../resouces/17-operation-maintenance-and-repair/spare-parts-inventory-account-catalog-candidates-v1.csv)、[候选维度字典](../../resouces/17-operation-maintenance-and-repair/spare-parts-inventory-dimension-dictionary-candidates-v1.csv)、[期初余额空白模板](../../resouces/17-operation-maintenance-and-repair/spare-parts-inventory-opening-balance-template-v1.csv) 和 [期初状态场景矩阵](../../resouces/17-operation-maintenance-and-repair/spare-parts-inventory-opening-state-scenario-matrix-v1.csv)。这些资源只提出候选分类与数据字段，不预设企业库存账户、维度或期初数量；全部业务语义须经企业库存数据所有者批准。

新增 [多维库存余额模型测试矩阵](../../resouces/17-operation-maintenance-and-repair/spare-parts-multidimensional-inventory-model-test-cases-v1.csv)；模型实现位于 [spare_parts_multidimensional_inventory.py](../../scripts/spare_parts_multidimensional_inventory.py)，专项测试位于 [test_spare_parts_multidimensional_inventory.py](../../tests/test_spare_parts_multidimensional_inventory.py)。模型仅接受显式合成测试快照，不自动换算单位，不跨库位/物料/批次/所有权转移；企业业务规则未获批准时保持阻断。

新增 [不可变库存事件账本测试矩阵](../../resouces/17-operation-maintenance-and-repair/spare-parts-inventory-event-ledger-test-cases-v1.csv)；模型实现位于 [spare_parts_inventory_event_ledger.py](../../scripts/spare_parts_inventory_event_ledger.py)，专项测试位于 [test_spare_parts_inventory_event_ledger.py](../../tests/test_spare_parts_inventory_event_ledger.py)。事件账本仅驻留内存，使用合成事件；重复投递幂等、迟到事件保留、按业务时间重建、冲销以新事件追加；不提供企业数据库/API连接。


新增库存事件账本完整性与恢复模型（../../scripts/spare_parts_inventory_ledger_integrity.py），配套15项测试场景矩阵及专项测试。该模型用于纯合成完整性检测与增量快照回放，不是签名/WORM存储或生产审计系统。


库存账本持久化新增 [读取一致性、并发读取与旧代际回收](spare-parts-synthetic-fixture-baseline-v1.md#17-库存账本读取一致性并发读取与代际生命周期)：recover_current() 通过POSIX共享锁保护代际加载，GC默认dry-run、至少保留CURRENT与最近N代，并要求显式 --gc-apply 删除。该功能仅用于合成数据的本地临时存储验证。


库存账本新增 [可验证备份与隔离恢复演练](spare-parts-synthetic-fixture-baseline-v1.md#18-库存账本可验证备份与隔离恢复演练)：提供备份导出、清单/文件SHA-256校验和空白隔离目录恢复接口；不覆盖既有目标存储，备份目录必须与源存储分离。该实现仅通过本地POSIX合成测试。


库存备份治理与灾备就绪规范见 [备件库存账本备份治理、RPO/RTO与恢复验收](spare-parts-inventory-backup-governance.md)（KNOW-000033）；包含保留/删除、RPO/RTO、安全密钥、异地存储和10项恢复演练验收条件，企业政策数值均留空待批准。

- [库存账本备份存储适配器契约与Mock验证](spare-parts-inventory-backup-storage-adapter.md)（KNOW-000034）

- [库存账本备份 Provider 身份权限、分块续传与孤儿回收治理](spare-parts-inventory-backup-provider-security-and-resilience.md)（KNOW-000035）

- [备份 Provider 重试、一致性与模糊提交恢复](spare-parts-inventory-backup-provider-retry-consistency-and-recovery.md)（KNOW-000036）

- [备份 Provider 熔断、半开探测、舱壁与总重试预算](spare-parts-inventory-backup-provider-circuit-breaker-bulkhead-and-budget.md)（KNOW-000037）

- [备份Provider公平调度、租户配额与任务取消/截止时间](spare-parts-inventory-backup-provider-fair-scheduling-and-tenant-isolation.md)（KNOW-000038）；配套15项合成测试场景矩阵位于本章 `resouces/`。

- [备份Provider多实例共享协调、租户配额与租约恢复](spare-parts-inventory-backup-provider-shared-coordination-and-lease-recovery.md)（KNOW-000039）；配套24项共享协调模拟场景矩阵位于本章 `resouces/`。


- [备份Provider协调器故障注入、失败关闭与恢复](spare-parts-inventory-backup-provider-shared-coordination-and-lease-recovery.md)（KNOW-000040）；与KNOW-000039共用ASSET-000070矩阵，覆盖协调器不可用、响应丢失、租约校验/释放失败及恢复路径；全部合成场景NOT_RUN。


- [备份 Provider 准入队列容量保护与恢复](spare-parts-inventory-backup-provider-admission-queue-bounds-and-recovery.md)（KNOW-000041）；新增7项本地/共享队列上限、故障中断和恢复后重新准入合成场景（ASSET-000071），全部NOT_RUN。


- [备份 Provider 持久化准入协调器与幂等租约](spare-parts-inventory-backup-provider-sqlite-persistent-admission-coordinator.md)（KNOW-000042）；使用SQLite WAL/BEGIN IMMEDIATE验证同主机多进程原子准入、租约恢复、request_id幂等和持久fencing序列；新增10条合成验收场景（ASSET-000072）。


- [备份 Provider fencing 契约与 SQLite 安全恢复](spare-parts-inventory-backup-provider-fencing-and-sqlite-recovery.md)（KNOW-000043）；定义下游原子陈旧写入防护与本地SQLite在线备份/新库恢复门禁，配套16条合成场景（ASSET-000073/000074），均未批准/未执行。


- [备份 Provider 适配器 fencing token 贯穿与备份包范围原子提交](spare-parts-inventory-backup-provider-adapter-fencing-integration.md)（KNOW-000044）；显式严格模式下覆盖payload、multipart与receipt-last写入，ASSET-000075定义12条合成场景，均未批准/未执行。


- [备件库存备份 SQLite fenced Provider 参考实现、主体授权与恢复门禁](spare-parts-inventory-backup-provider-sqlite-fenced-reference.md)（KNOW-000045）；同主机SQLite事务内原子提交scope高水位、对象/multipart及幂等回执，ASSET-000076定义22条形式化参考场景，均未批准/未执行。

- [Coordinator签发的scope-bound fencing attestation、Provider验签与密钥轮换](spare-parts-inventory-backup-provider-fencing-attestation-and-key-rotation.md)（KNOW-000046）；默认15秒HMAC proof绑定lease/tenant/scope/resource/operation/idempotency；ASSET-000077定义20条形式化参考场景，均未批准/未执行。

- [Provider Ed25519 公钥验签、KMS 签名回调与在线租约状态检查](spare-parts-inventory-backup-provider-ed25519-and-online-revocation.md)（KNOW-000047）；Ed25519 v2签名与本地Coordinator在线lease状态检查已实现，在线检查不可用时fail-closed；跨数据库status check到Provider commit仍有TOCTOU竞态。ASSET-000078定义22条参考验收场景，均未批准/未执行。
- [SQLite 同库原子 lease 撤销与 Provider 写入顺序](spare-parts-inventory-backup-provider-atomic-lease-revocation.md)（KNOW-000048）；可选同库事务模式复用Provider BEGIN IMMEDIATE连接校验lease，使Coordinator release与对象/multipart写入串行化；要求同一主机、本地SQLite文件。ASSET-000079定义12条形式化场景，均未批准/未执行。代码CI Run 45762883991与文档同步Run 45762994591均两个必需Job success，全库254项和CH12 143项测试通过，strict lint 0 errors/5 warnings。
- [远程 Coordinator 与对象存储 Provider 的分布式 fencing 提交协议](spare-parts-inventory-backup-provider-distributed-fencing.md)（KNOW-000049）；以同一个scope control object的ETag/generation CAS作为activation、revoke和manifest publish线性化点；payload先不可变staging，最终通过manifest pointer发布。ASSET-000080定义20条参考场景，均未批准/未执行。当前仅有内存CAS模型，未接入真实云SDK或远程Coordinator。


- [备件库存备份 Coordinator 持久权威、Leader 切换与故障恢复](spare-parts-inventory-backup-provider-coordinator-durable-authority-and-recovery.md)（KNOW-000050）；在本地SQLite WAL参考层持久分配租户scope token与publish operation sequence，增加Leader epoch门禁、activation/revocation两阶段Provider确认及崩溃恢复；ASSET-000081为16条场景，全部未批准/未执行。非多主机共识实现。


- 第三十六轮新增 [Coordinator 持久权威、Leader 切换与故障恢复](spare-parts-inventory-backup-provider-coordinator-durable-authority-and-recovery.md)（KNOW-000050）。代码Run 45769331991、文档同步Run 45769584662均通过；全库283项测试和CH12 143项测试通过。ASSET-000081的16条场景仍未批准/未执行；当前实现仅为同机SQLite WAL参考，不是多主机协调服务。


- [Coordinator 权威存储后端契约与 etcd v3 适配设计](spare-parts-inventory-backup-provider-coordinator-backend-contract-and-etcd-v3.md)（KNOW-000051）；定义线性一致Get、CAS多键Txn和Lease端口，提供SQLite参考适配器与注入式etcd v3接口；ASSET-000082包含20条待批准/未执行场景。没有真实etcd多主机集群接入。


- 第三十七轮新增 [Coordinator 权威存储后端契约与 etcd v3 适配设计](spare-parts-inventory-backup-provider-coordinator-backend-contract-and-etcd-v3.md)（KNOW-000051）。代码Run 45770717942与文档Run 45770955018均通过（全库300项、CH12 143项）；但etcd仅为注入式driver适配器，无真实集群连接。ASSET-000082的20条场景仍未批准/未执行。


Coordinator 权威状态迁移基础见 [事务内有序读取与状态快照](spare-parts-inventory-backup-provider-coordinator-transactional-read-batches.md)（KNOW-000052）：新增Txn分支内精确键Get/Put/Delete有序读取契约；ASSET-000083包含16条待批准/未执行场景。现有SQLite业务状态机和Admission lease仍未迁移到通用Store，etcd仅为注入式driver适配器。

第三十八轮文档同步CI Run 45772844275（提交 a1548dad6ad1c47d4645600a162a866076de6993）两个必需Job均completed/success：304项全库unittest、CH12 143项测试、strict lint 0 errors/5 warnings、知识结构质量0 errors。ASSET-000083场景仍待批准/未执行。


Admission lease 统一事务参考模型见 [Admission Lease Authority 与Coordinator统一事务存储](spare-parts-inventory-backup-provider-admission-lease-authority-store.md)（KNOW-000053）：提供基于CoordinatorAuthorityStore的lease创建、续租、释放、单调fencing token及可纳入authority Txn的双键guard；ASSET-000084包含20条待批准/未执行场景。该组件尚未替代旧SQLite Admission排队/全局与租户配额调度器，也未接入SQLite Coordinator领域状态机。

第三十九轮文档同步CI Run 45776156101（提交 b79aede8a06cc55ac60681cbfc9acf03b1f44a55）两个必需Job均completed/success：314项全库unittest、CH12 143项测试、strict lint 0 errors/5 warnings、知识结构质量0 errors。ASSET-000084场景仍待批准/未执行。

第三十九轮最终元数据CI Run 45776292616两个必需Job均completed/success：314项全库unittest、CH12 143项测试、strict lint 0 errors/5 warnings、知识结构质量0 errors。生产备份关闭，企业场景仍待批准/执行。


Admission调度与配额统一事务参考模型见 [Unified Admission Scheduler 与配额状态统一事务模型](spare-parts-inventory-backup-provider-unified-admission-scheduler-and-quota-state.md)（KNOW-000054）：将global/tenant quota、跨domain公平等待队列、fencing token和活动Lease收敛到一个revisioned aggregate Txn；ASSET-000085有24条待批准/未执行场景。单aggregate存在全局写入串行热点；旧SQLite Admission及Coordinator服务尚未切换，真实etcd未连接。

第四十轮文档同步CI Run 45778328441（提交 87d749147d2c32da547ce23ed56db69725271a00）两个必需Job均completed/success：328项全库unittest、CH12 143项测试、strict lint 0 errors、知识结构与数据质量0 errors（5条非阻断warning）。ASSET-000085场景仍待批准/未执行。

第四十轮文档同步CI Run 45778328441（提交 87d749147d2c32da547ce23ed56db69725271a00）两个必需Job均completed/success：328项全库unittest、CH12 143项测试、strict lint 0 errors、知识结构与数据质量0 errors（5条非阻断warning）。ASSET-000085场景仍待批准/未执行。


Coordinator统一事务参考见 [Unified Coordinator Authority：Leader、Scope Fencing与Operation Ledger](spare-parts-inventory-backup-provider-unified-coordinator-authority.md)（KNOW-000055）：Leader TTL/epoch、tenant scope高水位token和ACTIVATE/REVOKE/PUBLISH操作账本已纳入Admission aggregate schema v2。ASSET-000086为35条待批准/未执行场景。旧SQLite Coordinator尚未替换，真实etcd与生产Provider未验证。

第四十一轮最终代码提交 `3d79149c1112550b4fb25efbe02b5f536b08cacd`；[CI Run 45810737444](https://github.com/rexyll/cnc-knowledge/actions/runs/45810737444)两个必需Job均completed/success：344项全库unittest、CH12 143项数值资源测试通过，strict lint 0 errors，结构质量0 errors。ASSET-000086的35条场景仍PROPOSED_NOT_APPROVED/NOT_RUN。

第四十一轮文档同步CI Run 45811108498（提交 706cfcf36204c1bfe996501e65031a21e8536783）两个必需Job均completed/success：344项全库unittest、CH12 143项测试、strict lint 0 errors、知识结构与数据质量0 errors（5条非阻断warning）。ASSET-000086场景仍待批准/未执行。

第四十一轮文档同步CI Run 45811108498（提交 706cfcf36204c1bfe996501e65031a21e8536783）两个必需Job均completed/success：344项全库unittest、CH12 143项测试、strict lint 0 errors、知识结构与数据质量0 errors（5条非阻断warning）。ASSET-000086场景仍待批准/未执行。

第四十一轮文档同步CI Run 45811108498两个必需Job均completed/success：344项全库unittest、CH12 143项测试通过，strict lint与结构质量均0 errors（5条非阻断warning）。ASSET-000086的35条场景尚未批准或执行。


## CH17-T004 Unified Coordinator Aggregate容量画像（第四十二轮）

容量模型见 [备件库存备份 Unified Coordinator Aggregate 容量模型与观测边界](spare-parts-inventory-backup-provider-coordinator-capacity-model.md)（KNOW-000056）：新增离线合成容量探针，复用schema-v2真实记录构造和canonical JSON编码，统计aggregate、scope、operation索引字节数，并给出活动Admission lease对应的Coordinator比较项模型。ASSET-000087定义14个合成场景。该轮不设置写入硬阈值，不连接真实etcd或生产Provider，不代表生产容量/性能验收。


第四十二轮离线容量探针代码提交 `f52937e1af7b622c11801e2ca502661365e75d05`；[CI Run 45814052446](https://github.com/rexyll/cnc-knowledge/actions/runs/45814052446)两个必需Job均completed/success。全库356项unittest、CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors（5项既有非阻断warning）。14个容量profile在CI合成测试中通过；真实etcd容量与性能仍未验证。


## CH17-T004 Operation Ledger生命周期与安全归档（第四十三轮）

新增 [Coordinator Operation Ledger 生命周期与安全归档协议](spare-parts-inventory-backup-provider-operation-ledger-archival.md)（KNOW-000057），明确终态候选筛选、未决操作保护、内容寻址不可变归档、manifest链、scope指针CAS、跨归档精确幂等和fail-closed恢复。配套25项企业待批准场景矩阵为ASSET-000088。新增脚本仅是纯内存协议参考模型，未接入当前StoreBackedCoordinatorAuthority或真实etcd/对象存储。


第四十三轮归档协议参考模型及CI验收：最终测试head提交 4ed91a04138e30ecf2275c07bb947ecc872fadd2；CI Run 45817146500 两个必需Job均completed/success。全库380项unittest、CH12 143项数值资源测试通过；strict knowledge lint 0 errors；结构与数据质量0 errors。新增24个归档参考模型测试全部通过；ASSET-000088的25条正式场景仍PROPOSED_NOT_APPROVED / NOT_RUN，未接入真实etcd/对象存储或生产Coordinator。


## CH17-T004 Archive Index精确幂等查询与Schema v3迁移/回滚（第四十四轮）

新增 [Archive Index精确幂等查询与Coordinator Schema v3迁移/回滚设计](spare-parts-inventory-backup-provider-archive-index-and-schema-v3-migration.md)（KNOW-000058），包含16/256/4096桶的不可变精确分片索引、旧manifest链回填、增量更新、authoritative count绑定和完整链审计；另定义V2写冻结、候选V3对象构造、source/Leader/fencing floor校验、控制指针CAS，以及V3写入前后不同回滚路径。配套ASSET-000089含47项正式待批准/未执行场景。两个脚本均为纯内存参考模型，未接入生产Coordinator、真实etcd或对象存储。


第四十四轮最终代码/测试head：`2b66224909d2bcd9b326c1cffcf220bef5d14b7f`；[CI Run 45819520749](https://github.com/rexyll/cnc-knowledge/actions/runs/45819520749)两个必需Job均completed/success。全库426项unittest、CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors（5项既有非阻断warning）。新增精确索引/Schema v3迁移模型46项单测通过；ASSET-000089的47项正式场景仍PROPOSED_NOT_APPROVED / NOT_RUN，未连接真实etcd/对象存储，未执行生产迁移。


Coordinator V3分片准入与事务预算设计见 [备件库存备份 Coordinator Schema v3：分片准入、配额槽位与 etcd 分布式事务预算](spare-parts-inventory-backup-provider-coordinator-v3-sharded-admission-and-transaction-budget.md)（KNOW-000059）。提出global/tenant双slot原子占位、Tenant队列分片、跨Tenant轮转、分区fencing token区间和Txn预算模型；配套54条场景矩阵ASSET-000090。模型仅为内存参考，V2公平调度语义差异须企业批准，真实etcd/生产切换未完成。


第四十五轮最终代码/测试head：`a035cdf1f82e6ea9274195b2872953e9f12e83ba`；[CI Run 45823628905](https://github.com/rexyll/cnc-knowledge/actions/runs/45823628905)两个必需Job均completed/success。全库462项unittest及CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors（5项既有非阻断warning）。本轮36项分片准入/事务预算参考模型测试通过；ASSET-000090的54项正式场景仍PROPOSED_NOT_APPROVED / NOT_RUN。未连接真实etcd或多主机Dispatcher，schema-v2仍是唯一生产权威。


第四十五轮最终修正版：分区 Fencing Leader 在仍持有活动 Token 区间时若观察到更高 external high-water，会废弃尚未使用的区间，再从预留高水位以上申请新范围。修正提交 e8a4fb4c91bac3b279c5a0f8a06d3ae121da75a1；[最终 CI Run 45824510175](https://github.com/rexyll/cnc-knowledge/actions/runs/45824510175)两个必需Job均成功。全库463项unittest（本轮37项）、CH12 143项测试通过；strict lint和结构质量均0 errors，5项既有非阻断warning。

## CH17-T004 etcd Watch、Range恢复与多实例故障注入（第四十六轮）

新增 [Coordinator etcd v3 Watch、Range恢复与多实例故障注入契约](spare-parts-inventory-backup-provider-coordinator-etcd-watch-range-recovery-and-multi-client-fault-injection.md)（KNOW-000060）。在既有Etcd v3 KV/Txn/Lease端口上增量添加可选Watch和线性一致前缀Range能力，定义created/PUT/DELETE/progress/fragment/compaction语义及Range snapshot + R+1断线恢复；共享fake backend由两个独立adapter实例执行多客户端CAS、Txn/Lease响应丢失测试。新增ASSET-000091的30条正式场景矩阵，全部PROPOSED_NOT_APPROVED / NOT_RUN。没有真实etcd driver/集群或多主机quorum测试。


第四十六轮最终代码head：`cdaff0dc43834b3250d8803efb0591a8656c363d`；[CI Run 45826709629](https://github.com/rexyll/cnc-knowledge/actions/runs/45826709629)两个必需Job均completed/success。全库484项unittest（含本轮21项Watch/多客户端契约测试）、CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors（5项既有非阻断warning）。真实etcd/gRPC driver、Raft quorum和多主机测试未执行；ASSET-000091的30项正式场景仍PROPOSED_NOT_APPROVED / NOT_RUN。


## CH17-T004 etcd3gw 驱动与三节点集成环境（第四十七轮）

新增 [Coordinator 真实 etcd v3 Gateway 驱动与三节点集成环境](spare-parts-inventory-backup-provider-coordinator-etcd3gw-driver-and-three-node-integration.md)（KNOW-000061）。新增可选etcd3gw 2.7.0驱动实现Range/Txn/Lease，限定只读endpoint failover与写操作unknown outcome；三节点etcd v3.7.0 Compose环境和5项opt-in真实集成测试通过显式脚本运行。由于高层Watch helper不提供完整WatchResponse envelope，驱动不实现Watch/WatchProgress。新增ASSET-000092的30条正式验证场景，全部PROPOSED_NOT_APPROVED / NOT_RUN。


- **最终CI：** `871fe0d2673fb1b39502236568dc7dd57ad3bef0`；[Run 45832644686](https://github.com/rexyll/cnc-knowledge/actions/runs/45832644686)两个必需Job均completed/success。全库499项unittest完成，494项通过、5项跳过（5项需ETCD_INTEGRATION=1的live etcd集成测试）；CH12 143项数值测试通过；strict knowledge lint 0 errors；独立的CH17合成夹具校验为0 errors、5 warnings。5项均为既有治理门禁提示：数据集仍为DRAFT、未批准企业测试环境、未批准企业测试级别、30项SPAT源测试案例仍NOT_RUN、manifest checksum pending；并非etcd驱动测试失败。
- **限制：** 本轮未启动真实三节点etcd；5项live integration tests只是skip，不代表通过；ASSET-000092的30项正式场景均PROPOSED_NOT_APPROVED / NOT_RUN。未验证mTLS/RBAC/Raft quorum或多主机故障；SQLite Coordinator业务服务未迁移，schema-v2仍为唯一生产权威；CH17-T004继续IN_PROGRESS。

## CH17-T004 etcd 单成员故障与多数派读写验证（第四十八轮）

新增真实集成测试`tests/test_spare_parts_provider_authority_store_member_outage_etcd_integration.py`：在一次性三成员etcd v3.7.0集群中停止etcd1，验证linearizable Range的失效endpoint failover、剩余2/3节点的Txn写入与读回，并恢复etcd1。最终[Live CI Run 45839556952](https://github.com/rexyll/cnc-knowledge/actions/runs/45839556952)的6项集成测试全部通过（6/6），诊断Artifact 15127610627；[默认质量CI Run 45839557095](https://github.com/rexyll/cnc-knowledge/actions/runs/45839557095)的两个Job也全部成功。

这只是一次性集成冒烟测试，不是企业生产验收。ASSET-000092的30项正式场景仍PROPOSED_NOT_APPROVED / NOT_RUN；未覆盖双节点故障/失去quorum、长时间网络分区、性能、TLS/mTLS、RBAC或多主机；schema-v2仍是唯一生产权威。
## CH17-T004 etcd 双成员故障与 quorum 恢复验证（第四十九轮）

新增测试`tests/test_spare_parts_provider_authority_store_quorum_loss_etcd_integration.py`：在一次性三成员etcd v3.7.0集群中停止两个成员，验证唯一存活节点不能完成线性一致读写；恢复第二个成员后重新形成多数派，并检查无多数派期间的目标写入没有提交，恢复后新的CAS事务成功。[Live CI Run 45840903997](https://github.com/rexyll/cnc-knowledge/actions/runs/45840903997)共7项集成测试全部通过（7/7）；[默认质量CI Run 45840904137](https://github.com/rexyll/cnc-knowledge/actions/runs/45840904137)的两个Job也全部成功。

该测试是一次性集成验证，不等于任意网络分区或生产HA验收。ASSET-000092的30项正式场景仍PROPOSED_NOT_APPROVED / NOT_RUN；未覆盖磁盘故障、非对称网络分区、延迟/吞吐、TLS/mTLS、RBAC或多主机；schema-v2仍是唯一生产权威。
## CH17-T004 etcd Watch Gateway 流式包络保真（第五十轮）

更新 KNOW-000061：驱动现已增加低层 HTTP server-streaming Watch 支持，完整保留 created/canceled/compact_revision/cancel_reason/fragment/header 和事件 KV/prev_kv；HTTP 双向 WatchProgress/Cancel 仍不支持，主动取消通过关闭 HTTP 流。真实三节点 CI [Run 45842517310](https://github.com/rexyll/cnc-knowledge/actions/runs/45842517310) 8/8 通过；默认质量 CI [Run 45842517156](https://github.com/rexyll/cnc-knowledge/actions/runs/45842517156) 两个 Job 成功（505 项测试，497 通过、8 项 opt-in skip；CH12 143 项通过；strict lint 0 errors）。ASSET-000092 正式 30 项场景仍 PROPOSED_NOT_APPROVED / NOT_RUN。

## CH17-T004 etcd Gateway mTLS 双向证书与信任链验证（第五十一轮）

新增一次性三成员 etcd v3.7.0 TLS Compose 拓扑和临时证书 runner。真实 [Run 45918152363](https://github.com/rexyll/cnc-knowledge/actions/runs/45918152363)成功，mTLS 3/3：有效双向证书成员发现/CAS写入/线性一致读回、缺失客户端证书拒绝、错误CA拒绝；诊断Artifact 15163390323。默认质量 [Run 45918152436](https://github.com/rexyll/cnc-knowledge/actions/runs/45918152436)成功（508项unittest、CH12 143项、strict lint 0 errors、结构/数据0 errors/5项既有warning）。临时证书和私钥已由runner清理。该结果不等于企业PKI/RBAC/生产密钥管理验收；ASSET-000092正式30项仍PROPOSED_NOT_APPROVED / NOT_RUN，schema-v2仍唯一生产权威。


## CH17-T004 etcd Gateway RBAC + mTLS 最小权限验证（第五十二轮）

Etcd3gwV3Client现支持显式auth_token并对每个endpoint session注入Authorization header。真实 [Run 45919206834](https://github.com/rexyll/cnc-knowledge/actions/runs/45919206834)成功：mTLS suite 8/8通过（基础mTLS 3项 + RBAC 5项），reader仅能读取授权prefix、writer仅能读写授权prefix，跨prefix访问和无token/错误密码均被拒绝；普通三节点live suite 8项通过。Artifact 15163741056。默认 [Run 45919206886](https://github.com/rexyll/cnc-knowledge/actions/runs/45919206886)成功：515项unittest（499通过、16项opt-in skip）、CH12 143项、strict lint 0 errors、结构/数据0 errors/5项既有warning。Gateway mTLS客户端证书不使用CN映射用户，RBAC由认证token独立承载。token自动刷新、企业IAM/审计/生产凭据管理尚未验证；ASSET-000092正式30项仍PROPOSED_NOT_APPROVED / NOT_RUN。


## CH17-T004 etcd Gateway Token 生命周期（第五十三轮）

新增显式token替换接口与短TTL集成测试入口：`Etcd3gwV3Client.set_auth_token()`可统一更新/清除各endpoint session的Authorization header，Watch复用相同session；driver不保存密码、不自动认证或刷新。etcd v3.7配置参考中的simple token默认TTL为300秒（`--auth-token-ttl`），JWT TTL独立配置；simple token为有状态开发/测试机制。短TTL测试单独启动临时mTLS集群，避免缩短既有RBAC套件token寿命。实时CI结果待验收补记。知识条目见[备件Coordinator etcd Gateway驱动与三节点集成](spare-parts-inventory-backup-provider-coordinator-etcd3gw-driver-and-three-node-integration.md)，来源SRC-000410～SRC-000412。

实时验收补记：[Run 45920726761](https://github.com/rexyll/cnc-knowledge/actions/runs/45920726761)成功，基础三节点suite 6项、mTLS/RBAC suite 8项、短TTL token生命周期1项全部通过；Artifact 15164208273（SHA-256 `0b66c69eb7f1ecc12e0d8bfbbf80ab0bf51de739ec31d8d2e9f3db878619e476`）。默认质量CI [Run 45920726730](https://github.com/rexyll/cnc-knowledge/actions/runs/45920726730)成功：518项unittest（501通过、17项opt-in skip）、CH12 143项、strict lint 0 errors。simple token TTL=10秒的旧token过期拒绝、显式重新认证、全部endpoint session更新、KV Range和Watch created握手均通过。自动刷新仍未实现。


### 第五十四轮补充：Gateway认证错误与quorum故障隔离

- 驱动将Gateway 401/code16映射为AuthenticationError、403/code7映射为PermissionDeniedError，明确的错误密码消息也映射为AuthenticationError；普通参数错误归类为GatewayRequestError。只有连接/超时可触发只读endpoint failover。
- Live Run 45922792420：基础三节点/成员故障/quorum suite 8项、mTLS/RBAC suite 12项、短TTL token 1项、认证/quorum隔离1项通过。多数派丢失时有效token Range和重新认证都超时；恢复多数派后旧token Range成功。
- 默认CI Run 45922792429：526项unittest（504通过、22项opt-in skip），CH12 143项，strict lint 0 errors；结构/数据0 errors，5项既有治理warning。
- 认证错误结构化只在当前Gateway协议和etcd3gw 2.7.0范围内验证；生产IAM、自动token刷新、网络分区和认证服务HA仍未验证。正式ASSET-000092状态不变。


## CH17-T004 etcd mTLS/RBAC 单成员故障与Token恢复（第五十五轮）

- 新增专项live测试：`tests/test_spare_parts_provider_authority_store_member_outage_auth_etcd_integration.py`。覆盖Token即时/收敛传播、停止单成员后的2/3 quorum读访问、Driver transport failover、健康成员直接Token接受、节点重启后的旧Token行为和显式重新认证恢复。
- Live [Run 45927091505](https://github.com/rexyll/cnc-knowledge/actions/runs/45927091505)五个阶段全部成功：基础etcd 6项、mTLS/RBAC 12项、短TTL生命周期1项、auth/quorum隔离1项、member outage/token传播1项；诊断Artifact [15167295428](https://github.com/rexyll/cnc-knowledge/actions/runs/45927091505/artifacts/15167295428)，SHA-256 `2f06dbcea1b1e69bf9dfcf2666bfedff3811321aa8a8dd1474181c88b75e7aff`。
- 实测：签发后立即和等待传播后3/3成员接受旧Token；停止etcd1时Driver failover成功，etcd2/3均HTTP 200；重启etcd1后旧Token返回HTTP 401；从健康成员重新认证得到的新Token在3/3成员可用，Driver恢复读取。
- 默认质量[Run 45927138505](https://github.com/rexyll/cnc-knowledge/actions/runs/45927138505)成功：527项unittest（504 passed、23 skipped）、CH12 143项、strict lint 0 errors、fixture validator 0 errors/5项既有warning，知识结构22章/178 Markdown/260实体/240关系/412来源/584内部链接。
- 边界：不自动刷新/重新认证、不匿名回退；simple Token重启后401只代表本次etcd v3.7.0实验，不外推JWT或生产环境。ASSET-000092正式30项仍PROPOSED_NOT_APPROVED / NOT_RUN。


## CH17-T004 etcd 多数派网络分区与隔离成员恢复（第五十六轮）

- 新增真实集成测试 `tests/test_spare_parts_provider_authority_store_network_partition_etcd_integration.py`，通过Compose标签校验隔离对象，仅断开一次性CI集群etcd1与专用网络的连接。
- [Live Run 45929955634](https://github.com/rexyll/cnc-knowledge/actions/runs/45929955634)成功；少数派本地线性一致Range/Put失败，多数派etcd2/etcd3完成Coordinator Store CAS写入和读回；finally恢复网络后，etcd1读到多数派提交的数据。专项测试1/1 PASS（8.248秒），Artifact [15168271744](https://github.com/rexyll/cnc-knowledge/actions/runs/45929955634/artifacts/15168271744)。
- [Knowledge Quality Run 45930090004](https://github.com/rexyll/cnc-knowledge/actions/runs/45930090004)两个Job成功：528项unittest（504通过、24跳过）、CH12 143项、strict lint 0 errors/5项既有warning，结构/最终自检0 errors。
- 该证据只覆盖一次性etcd v3.7.0/Compose三成员网络分区，不覆盖Driver层的少数派endpoint failover及Txn `OUTCOME_UNKNOWN` 语义；后续第五十七轮专门验证。ASSET-000092正式30项仍 `PROPOSED_NOT_APPROVED / NOT_RUN`。
