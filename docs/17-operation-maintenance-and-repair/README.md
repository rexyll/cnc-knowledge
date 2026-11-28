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


## CH17-T004 少数派分区下Driver读取故障转移与Txn结果核验（第五十七轮）

- Live [Run 45931474359](https://github.com/rexyll/cnc-knowledge/actions/runs/45931474359)成功；网络分区测试文件2项PASS（8.670秒）。只读Range从隔离etcd1 endpoint `127.0.0.1:23791`切换到健康多数派`127.0.0.1:23792`成功；少数派CAS Txn只发送一次，结果`OUTCOME_UNKNOWN/ConnectionError`。
- 网络恢复后线性一致读回为`not-committed`，未重放事务。Live后续mTLS、Token生命周期、quorum隔离、RBAC成员故障/Token传播和清理步骤全部成功；Artifact [15168243294](https://github.com/rexyll/cnc-knowledge/actions/runs/45931474359/artifacts/15168243294)。
- Quality [Run 45931474322](https://github.com/rexyll/cnc-knowledge/actions/runs/45931474322)成功：529 unittest（504通过、25跳过），CH12 143项，strict lint 0 errors/5 warnings，结构自检0 errors。
- 工程测试没有模拟已提交后响应丢失的精确窗口；ASSET-000092正式30项仍`PROPOSED_NOT_APPROVED / NOT_RUN`。下一轮验证少数派下Lease KeepAlive、自然到期和Leader fencing。


## CH17-T004 少数派Lease KeepAlive失败、自然过期与Leader fencing（第五十八轮）

- Live [Run 45933111643](https://github.com/rexyll/cnc-knowledge/actions/runs/45933111643)整体成功；Lease专项1/1 PASS（14.526秒）。KeepAlive客户端配置全部3个endpoint，但隔离后只触达etcd1 `127.0.0.1:23791` 一次，Store返回`AuthorityStoreUnavailableError`，没有自动切换多数派续租。
- 多数派Lease TTL从7秒降至5秒；Lease自然过期后TTL=-1，线性一致Range确认旧authority key已删除。新Leader epoch从1提升至2；旧epoch fencing CAS失败，新epoch写成功，恢复成员读到epoch 2。
- 诊断Artifact [15169352034](https://github.com/rexyll/cnc-knowledge/actions/runs/45933111643/artifacts/15169352034)。
- Quality [Run 45933111606](https://github.com/rexyll/cnc-knowledge/actions/runs/45933111606)成功：530 unittest（504通过、26跳过），CH12 143项，strict lint 0 errors/5项既有warning，结构自检0 errors。
- 此证据只验证一次性etcd集群和KV compare fencing，不证明SQLite业务Coordinator已经迁移或生产HA验收。ASSET-000092正式30项仍`PROPOSED_NOT_APPROVED / NOT_RUN`。下一轮验证LeaseRevoke未知结果与恢复后核对。


## CH17-T004 LeaseRevoke少数派分区与恢复核对（第五十九轮）

- [Live Run 45936468822](https://github.com/rexyll/cnc-knowledge/actions/runs/45936468822)成功；新增LeaseRevoke分区测试1/1 PASS。首个Revoke请求只触达隔离的etcd1 `127.0.0.1:23791`一次，Store返回`AuthorityStoreOutcomeUnknownError`，没有failover或重放。
- 恢复网络后，多数派首次核对发现原Lease和authority key仍存在、key revision仍为16，判定首次请求未提交；记录结果后显式通过健康多数派Revoke清理，key删除revision推进至17，TTL最终为-1。Artifact [15170653184](https://github.com/rexyll/cnc-knowledge/actions/runs/45936468822/artifacts/15170653184)。
- [Quality Run 45936468828](https://github.com/rexyll/cnc-knowledge/actions/runs/45936468828)：533 unittest（506 passed、27 skipped），CH12 143项，strict lint 0 errors/5既有warning，结构校验0 errors。SPAT 30项仅离线模拟、business_test_status仍NOT_RUN。
- supporting evidence不代表精确的“撤销已提交但响应丢失”窗口或生产HA验收；ASSET-000092正式30项仍`PROPOSED_NOT_APPROVED / NOT_RUN`。


## CH17-T004 Lease-bound Watch删除事件与断流恢复（第六十轮）

- [Live Run 45938253313](https://github.com/rexyll/cnc-knowledge/actions/runs/45938253313)成功；新增两项Watch测试通过。Lease Revoke DELETE事件revision/header=19，`prev_kv.mod_revision=18`且Lease ID正确；线性一致Range确认key删除。
- 已建立Watch在etcd1停止后返回`AuthorityStoreUnavailableError`，只请求初始endpoint一次。多数派删除revision=21；恢复后线性一致快照revision=21/key不存在，从revision=22恢复Watch，首个新事件是PUT revision=22，旧DELETE未重放。Artifact [15171088378](https://github.com/rexyll/cnc-knowledge/actions/runs/45938253313/artifacts/15171088378)。
- [Quality Run 45938253249](https://github.com/rexyll/cnc-knowledge/actions/runs/45938253249)：535 unittest（506 passed、29 skipped），CH12 143项，strict lint 0 errors/5既有warning，结构校验0 errors；SPAT 30项仅离线模拟、business_test_status仍NOT_RUN。
- 该结果是一次性CI supporting evidence；Watch仍不支持双向WatchProgress/WatchCancel；正式ASSET-000092仍`PROPOSED_NOT_APPROVED / NOT_RUN`。


## CH17-T004 Watch compaction取消与快照恢复（第六十一轮）

- [Live Run 45940105118](https://github.com/rexyll/cnc-knowledge/actions/runs/45940105118)成功；旧游标revision=24已被compact revision=25覆盖，Watch先返回created再返回canceled=true/compact_revision=25，无事件且resume_revision=None。
- 取消后线性一致快照revision=25、mod_revision=25且值正确；从revision=26恢复Watch，首个PUT事件revision=26，prev_kv与快照值一致，旧事件未重放。cancel_reason在Gateway响应中为空字符串。
- 诊断Artifact [15172995164](https://github.com/rexyll/cnc-knowledge/actions/runs/45940105118/artifacts/15172995164)。[Quality Run 45940105074](https://github.com/rexyll/cnc-knowledge/actions/runs/45940105074)：537 unittest（507通过、30跳过），CH12 143，strict lint 0 errors/5既有warning，结构0 errors。
- 本轮为一次性CI supporting evidence；Watch仍为单向HTTP server-stream、不支持双向WatchProgress/WatchCancel；ASSET-000092仍30项、`PROPOSED_NOT_APPROVED / NOT_RUN`。


## CH17-T004 Watch progress notification与Range权威性（第六十二轮）

- [Live Run 45944091683](https://github.com/rexyll/cnc-knowledge/actions/runs/45944091683)通过progress专项；etcd1 `127.0.0.1:23791`上Watch created header revision=28、watch_id=0；无关marker revision=29后，收到同watch_id=0的空progress帧，header revision=29、events=0、resume_revision=30。
- 线性一致Range快照revision=29，确认被Watch key仍存在且value/mod_revision不变。progress帧不携带KV内容；健康测试中revision相等不证明分区时也一致。官方etcd说明progress revision属于本地成员，可能落后quorum Range。
- [Quality Run 45944091695](https://github.com/rexyll/cnc-knowledge/actions/runs/45944091695)：539 unittest（508 passed、31 skipped），CH12 143，strict lint 0 errors/5 warning，结构/data 0 errors；SPAT 30项仅离线模拟。
- 一次性CI supporting evidence；显式双向WatchProgress/WatchCancel仍不支持；ASSET-000092仍30项、`PROPOSED_NOT_APPROVED / NOT_RUN`。


## CH17-T004 少数派Watch progress滞后与快照恢复（第六十三轮）

- [Live Run 45946092810](https://github.com/rexyll/cnc-knowledge/actions/runs/45946092810)整体success；新增少数派分区和恢复测试1/1 PASS（6.213秒）。etcd1通过临时专用网络保持Watch连接、同时与etcd2/etcd3隔离；多数派写入revision 33、34、35时，etcd1两次空Progress Notification的header revision均为32，events=0、watch_id=0。多数派线性一致Range revision=35，确认本地progress watermark不能当作quorum最新revision。
- 网络恢复后，多数派快照revision=35，etcd1线性一致读达到revision=35；新Watch从revision=36（snapshot+1）恢复，只收到revision=36的新PUT一次，prev_kv与快照值匹配；下一响应为空Progress帧，revision 33–35未重放。诊断Artifact [15174961822](https://github.com/rexyll/cnc-knowledge/actions/runs/45946092810/artifacts/15174961822)，SHA-256 `5d72bea9eeb46ea6d9a26b90204f5c350797a393c774852b64792520af6a5364`。
- Live流水线中普通etcd、mTLS、短TTL Token、auth/quorum、RBAC成员故障/Token传播、诊断采集及临时Compose容器/volumes清理全部success。测试只操作经标签核验的一次性容器与临时Docker网络，没有修改宿主机iptables或其他容器。
- [Quality Run 45946092822](https://github.com/rexyll/cnc-knowledge/actions/runs/45946092822)两个Job均success：540 unittest（32 skipped），CH12数值测试143项通过，strict knowledge lint通过，结构/data检查0 errors。
- Progress revision取自Watch连接的本地成员；少数派时可能低于quorum线性一致Range。恢复后必须通过线性一致快照确定权威状态，并从R+1续接。当前仍只验证周期性`progress_notify=true`，不代表双向WatchProgress/WatchCancel已实现。
- 本轮是一次性etcd v3.7.0 / etcd3gw 2.7.0 supporting evidence；ASSET-000092正式30项仍`PROPOSED_NOT_APPROVED / NOT_RUN`，schema-v2仍为唯一生产权威，SQLite Coordinator业务状态机未迁移，CH17-T004仍`IN_PROGRESS`。


## CH17-T004 少数派Watch Compaction与旧游标快照恢复（第六十四轮）

- 新增Live场景：etcd1上的Watch从revision=39建立并与peer网络隔离；etcd2/etcd3多数派更新独立marker revision=40、41，并执行`compact 41`。被Watch的leader key保持原值，确保旧游标保持落后。
- 恢复后显式以静态IP `172.29.64.11`将etcd1接回Compose peer网络；由健康多数派取得线性一致快照revision=41，再以旧游标39重建Watch，服务端返回`canceled=true`、`compact_revision=41`、0 events、`resume_revision=None`。原HTTP Watch流是否自动取消不作为前置假设。
- 新Watch从snapshot+1=42在健康多数派建立；快照后的新PUT revision=42仅投递一次，`prev_kv`匹配快照值；revision 40–41未重放。观测标志`no_compacted_event_replayed_after_snapshot=true`、`post_snapshot_event_delivered_once=true`。
- Compose三节点Raft peer使用固定地址`172.29.64.11/.12/.13`；所有分区恢复路径显式恢复etcd1静态IP，避免Docker断开/重连后动态地址与Raft peer advertisement不一致。
- [Live Run 45949089875](https://github.com/rexyll/cnc-knowledge/actions/runs/45949089875)整体success；watch minority测试文件2项通过（7.292s），普通网络/Lease分区、mTLS、短TTL Token、auth/quorum和RBAC成员故障阶段均success；诊断Artifact [15176311979](https://github.com/rexyll/cnc-knowledge/actions/runs/45949089875/artifacts/15176311979)。[Quality Run 45949089930](https://github.com/rexyll/cnc-knowledge/actions/runs/45949089930)两个Job均success。
- 本轮是一次性etcd v3.7.0 / etcd3gw 2.7.0 CI supporting evidence，不代表生产HA或正式矩阵验收；ASSET-000092仍`PROPOSED_NOT_APPROVED / NOT_RUN`，schema-v2仍为唯一生产权威，SQLite Coordinator业务状态机尚未迁移，CH17-T004整体`IN_PROGRESS`。

## CH17-T004 长运行Watch缓存周期Compaction重建（第六十五轮）

- 新增Live测试`test_long_running_watch_rebuilds_client_cache_across_periodic_compactions`，在一次三节点etcd Live会话内连续消费Watch事件，并完成两轮真实Compaction、旧cursor取消、quorum Range快照整体替换和snapshot+1续接。长流连接配置了1秒Progress间隔的etcd1；多数派负责权威快照、过期cursor探测和并发写入。
- 初始snapshot revision=38，Watch从39建立；前缀外marker revision=39后收到空Progress帧。第一轮并发PUT revision=[40,41,42,43]，snapshot/compact=43，旧cursor39被取消。后台写入跨快照边界：revision44在snapshot=44前写入并被快照覆盖，revision45、46在快照后、Watch重建前写入，由新Watch从45完整回放。第二轮并发PUT/DELETE revision=[47,48,49,50]，snapshot/compact=50，旧cursor45被取消；最后从51恢复并收到revision51新事件一次。
- 最终观察：`compaction_revisions=[43,50]`、`resume_cursors=[39,45,51]`、Watch唯一事件11条、重复0；`watch_event_revisions=[40,41,42,43,45,46,47,48,49,50,51]`。revision44仅由快照覆盖，45/46均成功补齐；最终客户端缓存与quorum线性一致Range逐key/value一致。
- [Live Run 45975852325](https://github.com/rexyll/cnc-knowledge/actions/runs/45975852325)整体success；本轮Watch专项文件3项测试通过（9.443秒）；普通etcd、mTLS、短TTL Token、Auth/Quorum、RBAC成员故障/Token传播、诊断Artifact上传及一次性Compose容器/volumes清理全部success。Artifact [15187805125](https://github.com/rexyll/cnc-knowledge/actions/runs/45975852325/artifacts/15187805125)。[Quality Run 45975852368](https://github.com/rexyll/cnc-knowledge/actions/runs/45975852368)两个Job均success：542项unittest（34 skipped）、CH12 143项、strict lint 0 errors/5 warnings、结构/data检查0 errors。
- 此处cache仅为测试投影，不是生产Watch缓存功能；“长运行”仅覆盖单次Live内的多轮Compaction与重建，不证明无限期稳定性、背压/内存上限或生产SLO。Watch仍为单向HTTP server-streaming，不支持双向WatchProgress/WatchCancel；旧cursor/Compaction/断流恢复必须以健康多数派线性一致Range快照为准并从R+1恢复。ASSET-000092仍30项`PROPOSED_NOT_APPROVED / NOT_RUN`；schema-v2仍唯一生产权威；SQLite Coordinator业务状态机尚未迁移；CH17-T004保持`IN_PROGRESS`。

## CH17-T004 慢消费者Watch积压与Compaction竞争（第六十六轮）

- 新增Live测试`test_slow_watch_consumer_drains_backlog_or_rebuilds_after_compaction`。第一阶段应用暂停读取0.8秒，多数派提交64个PUT，再以每响应8ms延迟消费；64个事件全部到达，64个响应，最大每响应1个事件；quorum snapshot revision=123与cache一致。
- 第二阶段Watch从cursor=124建立，暂停读取期间多数派提交96个PUT，etcd2执行`compact 219`。恢复读取时当前活动Watch完整排空96项积压（96个响应），没有观察到该流被取消；随后在多数派重新使用旧cursor=124建Watch，收到Compaction取消帧。多数派snapshot revision=219整体替换cache，新Watch从220恢复，revision=220的新PUT只投递一次，最终Range与cache一致。
- 最终观察：`compaction_revision=219`、`compaction_race_mode=drained`、`compaction_race_events_before_cancel_or_drain=96`、`recovery_cursor=220`、`unique_applied_event_count=161`、`duplicate_applied_events=0`、`final_cache_matches_linearizable_range=true`。最大单响应1项；Progress帧未在该有限测试窗口中出现。
- [Live Run 45980665924](https://github.com/rexyll/cnc-knowledge/actions/runs/45980665924)整体success；Watch minority测试文件4项测试通过（13.524s），普通Etcd、mTLS、短TTL Token、Auth/Quorum、RBAC成员故障/Token传播、诊断、容器/volumes清理及Artifact上传全部success。诊断Artifact [15189731260](https://github.com/rexyll/cnc-knowledge/actions/runs/45980665924/artifacts/15189731260)。[Quality Run 45980665958](https://github.com/rexyll/cnc-knowledge/actions/runs/45980665958)两个Job均success：543项unittest（35 skipped）、CH12 143项、strict lint 0 errors/5 warnings、结构/data 0 errors。
- 这只证明一次性etcd v3.7.0 / etcd3gw 2.7.0环境下有限64/96事件的停读与消费行为，不证明自动背压、内存/队列上限、TCP窗口或无限期稳定性。活动流排空不意味着旧cursor可用于重建；重新建流时旧cursor仍会被Compaction拒绝，必须以健康多数派线性一致Range快照恢复并从R+1续接。Watch仍为单向HTTP server-streaming，不支持双向WatchProgress/WatchCancel。
- ASSET-000092正式30项仍`PROPOSED_NOT_APPROVED / NOT_RUN`；schema-v2仍唯一生产权威，SQLite Coordinator业务状态机尚未迁移，CH17-T004保持`IN_PROGRESS`。

## CH17-T004 Watch意外EOF与部分投影快照恢复（第六十七轮）

- 驱动现在区分服务端显式`canceled`终止响应与HTTP流意外EOF：前者后续正常结束；没有取消响应的EOF转换为`AuthorityStoreUnavailableError`。Fake契约新增覆盖，既有Lease断流Live用例不再接受裸`StopIteration`。
- 新增部分投影恢复Live场景：etcd1 Watch已消费revision 25；etcd1停止期间多数派提交revision 26/27/28（覆盖更新、删除、新增）；恢复后以quorum snapshot revision 28整体替换投影，从revision 29重新Watch并仅收到新事件一次；最终revision 29投影与线性一致Range一致。
- 原Watch只尝试etcd1 endpoint，没有自动跨endpoint切换。恢复依据是健康多数派线性一致Range，不复用断流前cursor。
- [Live Run 45982644017](https://github.com/rexyll/cnc-knowledge/actions/runs/45982644017)整体success；Lease Watch recovery文件3项测试（3.930s）和Watch minority文件4项测试（13.314s）均通过。诊断Artifact [15190500314](https://github.com/rexyll/cnc-knowledge/actions/runs/45982644017/artifacts/15190500314)，SHA-256 `364c70b27a0ac0cca5da2d2c1930513885cefe2706a09ddcdfc2e41adce2e04e`。
- [Quality Run 45982644355](https://github.com/rexyll/cnc-knowledge/actions/runs/45982644355)两个Job均success：545项unittest（36 skipped）、CH12 143项、strict lint 0 errors / 5 warnings、结构/data检查0 errors（260实体、240关系、412来源、178 Markdown）。SPAT 30包只完成离线模拟，`business_test_status=NOT_RUN`。
- 证据只适用于一次性etcd v3.7.0 / etcd3gw 2.7.0三节点Compose实验；不代表生产网络耐久性、代理超时、长尾延迟、背压或内存容量验收。Watch仍为单向HTTP server-streaming；ASSET-000092仍`PROPOSED_NOT_APPROVED / NOT_RUN`，schema-v2仍唯一生产权威，SQLite Coordinator业务状态机未迁移，CH17-T004保持`IN_PROGRESS`。

## CH17-T004 Watch空闲Progress、读超时与访问路径失联（第六十八轮）

- `Etcd3gwV3Client`新增可选`watch_read_timeout`，默认`None`保持旧行为；启用后设置HTTP Watch response的read inactivity timeout，异常映射为`AuthorityStoreUnavailableError`，不自动重连/failover。
- 初始snapshot revision=38，Watch从39建立，read timeout=4秒。全局无revision推进时没有收到Progress；在`4.0045s`后返回Unavailable，但etcd1仍running、仍在Raft网络且Quorum健康，目标prefix完全未变。这证明读取超时是流静默阈值，不是节点健康判断。
- prefix外marker写revision 39、40后，Watch收到空Progress header revision 39、39，未收到prefix KV事件。第二个marker已推进到40但Progress仍为39，故Progress不能作为quorum最新revision或权威快照。
- 断开etcd1专用客户端访问bridge、保留节点及Raft网络后，既有HTTP Watch在`4.0045s`后被识别为Unavailable；etcd1仍运行且Quorum恢复健康。该实验不是WAN/NAT/代理的真实TCP半开验收。
- [Live Run 45987534125](https://github.com/rexyll/cnc-knowledge/actions/runs/45987534125)整体success；Watch minority测试文件5项通过（24.605s），所有后续mTLS、Token、auth/quorum、RBAC阶段及容器/volumes清理成功。Artifact [15192246652](https://github.com/rexyll/cnc-knowledge/actions/runs/45987534125/artifacts/15192246652)，SHA-256 `e9f2dbb141dc55a60f3988876df8eaa86eb02b4b26dda3f43c76f0a4a0b30663`。
- [Quality Run 45987533954](https://github.com/rexyll/cnc-knowledge/actions/runs/45987533954)两个Job success：548 unittest（37 skipped）、CH12 143项、strict lint 0 errors / 5 warnings、结构/data 0 errors（260实体、240关系、412来源、178 Markdown）。
- 运维边界：未配置read timeout时仍可能无限等待；完全静默的Watch若配置read timeout会被判为Unavailable，不能在没有可靠心跳的前提下盲目启用。ASSET-000092仍`PROPOSED_NOT_APPROVED / NOT_RUN`，schema-v2仍唯一生产权威，SQLite Coordinator业务状态机未迁移，CH17-T004保持`IN_PROGRESS`。

## CH17-T004 Watch连接健康分层与存活检测策略（第六十九轮）

- 新增独立决策记录：[Watch连接健康与存活检测策略决策记录](watch-connection-health-and-liveness-decision-record.md)，比较Progress、TCP Keepalive、HTTP/2 gRPC PING、独立线性一致Range和Lease-backed应用心跳。
- 决策采用分层健康模型：Watch流事件/Progress/断流衡量流维度；进程级共享线性一致Range探测衡量Quorum-read能力；可选Lease心跳只用于明确的端到端Watch交付SLO。Progress header是Watch本地revision，不能代表Quorum最新revision。
- 当前驱动使用Requests访问`/v3/watch`，没有原生gRPC双向Watch控制流；HTTP/2 gRPC PING不能直接套用于当前Requests客户端。`status()`的`/maintenance/status`也不替代线性一致Range探测。
- `watch_read_timeout`继续默认None；在没有可靠且有界的流量间隔前，不为长时间静默Watch设置生产超时。TCP Keepalive、后台Quorum Scheduler、应用心跳写入和自动恢复状态机均未实现。
- 本轮为设计决策记录，不新增生产代码或Live验收。后续实现需先明确生产网络/代理、消费调度模型、权限范围和SLO，再分别验证连接探测与Quorum探测。CH17-T004保持`IN_PROGRESS`。


## CH17-T004 Watch Supervisor 与 Quorum Probe 生产接入边界审查（第七十轮）

- 完成业务服务、KV/Txn/Lease端口、可选Watch端口、etcd适配器与HTTP Gateway驱动的代码路径审查；第七十轮初版遗漏了第41轮已有的Store-backed Unified Coordinator实现，已由第七十一轮更正。
- 当前已有`StoreBackedCoordinatorAuthority`与`StoreBackedProviderAdmissionCoordinator`，二者通过Unified schema-v2 aggregate和同一个`CoordinatorAuthorityStore`事务协调业务状态；旧SQLite表迁移/冻结/回滚/cutover仍未完成。
- Watch仍没有业务服务级生命周期owner；不提前新增后台Supervisor、共享Quorum探测或自动重连。
- 详细门禁：[Watch Supervisor与Quorum Probe生产接入边界审查](watch-supervisor-integration-readiness-review.md)。

## CH17-T004 Unified Coordinator 真实 etcd 适配器与业务契约验证（第七十一轮）

- 已有的`StoreBackedCoordinatorAuthority`与`StoreBackedProviderAdmissionCoordinator`继续复用Unified schema-v2 aggregate；不重新实现或绕过现有事务边界。
- 新增真实三节点etcd Live测试：ACTIVATE→PUBLISH→REVOKE、Admission Lease释放后拒绝新操作、两个独立HTTP客户端并发分配8个唯一sequence并幂等重放、Lease TTL到期后的Leader epoch接管和旧Leader fencing。新测试3/3通过。
- 修正Leader claim/renew使用后端实际Granted TTL记录`expires_at`，不再假设服务端授予TTL必然等于请求TTL；Live测试轮询确认TTL key确已删除。
- [Live Run 45993192615](https://github.com/rexyll/cnc-knowledge/actions/runs/45993192615)与[Quality Run 45993192694](https://github.com/rexyll/cnc-knowledge/actions/runs/45993192694)均success。40项Live测试成功；Quality 554 unittest（40 skipped）、CH12 143项、strict lint 0 errors/5 warnings、结构/data 0 errors。
- 详细说明：[Unified Coordinator 真实 etcd 业务契约验证](spare-parts-inventory-backup-provider-unified-coordinator-authority.md)。
- **边界：** 本轮未迁移旧SQLite数据，未执行生产cutover，synthetic Provider非真实对象存储；ASSET-000092仍待批准/未运行，schema-v2仍唯一生产权威。

## CH17-T004 旧 SQLite Coordinator / Admission 迁移审计与切换设计（第七十二轮）

- 新增[旧SQLite→Unified schema-v2迁移审计与切换设计](sqlite-to-unified-coordinator-migration-design.md)，审计Admission meta/request/waiter表及Coordinator leader/scope/operation表。
- 两组来源状态必须作为一个逻辑整体导入同一Unified schema-v2 aggregate；保留request/operation幂等历史、waiter顺序、fencing/sequence/Leader epoch floors、Provider generation和manifest。
- 活动Lease按冻结时剩余TTL转换；不得重置完整TTL。后端Granted TTL若超过来源deadline，必须拒绝或由应用绝对deadline兜底。
- 定义只读盘点、隔离预演、旧端写冻结、WAL一致快照、候选导入、精确对账、单权威cutover和业务写入后的反向迁移门禁。
- **边界：** 本轮仅代码审计与设计；未连接生产SQLite、未实现迁移工具、未冻结或切换生产authority。schema-v2仍唯一生产权威，ASSET-000092仍PROPOSED_NOT_APPROVED / NOT_RUN。


## CH17-T004 SQLite 迁移只读盘点工具（第七十三轮）

- 新增`scripts/spare_parts_sqlite_migration_inventory.py`，使用SQLite URI `mode=ro`与`PRAGMA query_only=ON`，只读盘点Admission/Coordinator两组来源表。
- 默认输出inventory manifest，包含schema/列、行数、状态分布、规范化行SHA-256、Admission fencing floor、Coordinator scope token/sequence floor、pending/孤儿operation、SQLite完整性检查及DB/WAL扫描前后指纹。
- 通过`--records-output`显式输出完整逻辑记录JSON；文件按0600权限创建，包含业务标识的数据不得提交Git。
- 工具不实例化业务Coordinator，不触发expiry cleanup，不切换WAL，不写源库，不访问Provider/etcd；它不是SQLite物理备份，也不代表生产迁移授权。
- 专用unittest随[Knowledge Quality Run 46000363197](https://github.com/rexyll/cnc-knowledge/actions/runs/46000363197)通过；CH12数值资源Job也通过。
- 用法和检查边界详见[迁移设计第10节](sqlite-to-unified-coordinator-migration-design.md)。


## CH17-T004 Unified schema-v2 候选导入包生成器（第七十四轮）

- 新增`scripts/spare_parts_sqlite_candidate_importer.py`及专用unittest，验证MIG-03 manifest/records、逐表行数与SHA-256、snapshot digest和显式Admission策略policy hash。
- 候选映射保留全局/逐scope fencing与sequence floors、终态request幂等索引、scope/operation历史、Provider generation/manifest引用和可映射计数器；旧Leader只转为epoch恢复下限，必须重新claim。
- 工具要求来源已排空ACTIVE request、waiter和pending operation；过期但仍标记ACTIVE的数据拒绝导入。非IDLE/REVOKED scope进入RECOVERY_REQUIRED。
- 外部Provider fencing floor不从SQLite推测，保持REQUIRED/null；终态request backend_lease_id使用明确标注的非活动占位符，不代表原生Lease。
- **验证：** [Knowledge Quality Run 46004441510](https://github.com/rexyll/cnc-knowledge/actions/runs/46004441510)成功：566项unittest（40 skipped）、CH12数值资源Job通过；候选导入器专用用例包含在全库unittest中。
- **严格边界：** 本阶段只生成候选包，不写etcd/CoordinatorAuthorityStore。目标Store当前namespace前缀固定，隔离namespace注入和目标Lease/Txn/checkpoint/未知结果恢复仍待实现；候选包不可直接导入生产。MIG-04保持IN_PROGRESS，MIG-05/06 TODO，MIG-07 BLOCKED。

## CH17-T004 Unified Store 隔离命名空间注入（第七十五轮）

- `StoreBackedProviderAdmissionCoordinator`新增可选`namespace_prefix`；省略时沿用原有`/cnc/admission/unified/v2/`，保持既有业务实例的键路径兼容。
- 自定义namespace限定为`/cnc/migration/isolated/{单一标识}/`；拒绝生产namespace、空标识、多级路径和路径穿越。Scheduler State、Admission Lease/Request索引均从实例前缀派生。
- `StoreBackedCoordinatorAuthority`的Leader TTL key现在从scheduler实例前缀派生，避免业务状态隔离但Leader key仍写入默认生产前缀。
- 新增单元测试验证默认前缀、隔离前缀与非法输入；Coordinator测试验证Leader key只存在于指定隔离前缀。
- **边界：** 仅完成键空间隔离能力，不会自动创建隔离namespace，不写候选导入包、不创建业务Lease、不执行导入Txn；Txn容量、批处理checkpoint、未知结果恢复和临时真实etcd迁移演练仍待完成。等待Quality CI确认。

## CH17-T004 隔离namespace空空间预检（第七十六轮）

新增`scripts/spare_parts_migration_namespace.py`，提供`validate_isolated_namespace()`与`preflight_empty_namespace()`。预检只接受`/cnc/migration/isolated/{single-id}/`格式，并通过`EtcdV3CoordinatorAuthorityStore.linearizable_range()`对完整prefix执行线性一致Range；发现任何键即报错，后端不可用也会fail-closed。成功结果记录prefix、Range revision与0个已存在键。

同时扩展`InMemoryEtcdV3Client.range()`的prefix Range语义，确保测试不会把精确键Range误当成整个prefix Range。新增测试覆盖空namespace、已占用namespace、相邻namespace隔离和后端不可用。

**安全说明：** 预检不是锁。Range返回后仍可能有其他客户端写入，因此后续必须配合一次性临时etcd集群或服务端RBAC，确保没有其他写入者。此轮没有执行任何etcd写操作，也没有导入候选数据。

## CH17-T004 单 Txn 候选导入容量规划（第七十七轮）

新增只读工具 `scripts/spare_parts_sqlite_candidate_import_plan.py`。它验证候选bundle摘要与Unified schema-v2状态结构，检查终态request键派生、scope fencing/sequence高水位和恢复门禁，并针对显式隔离namespace构建单Txn写集合估算。

计划中的单个Txn同时比较Scheduler aggregate、每条终态request索引和Coordinator Leader TTL key均为不存在，再原子Put aggregate与全部终态request索引。Leader key只比较不写入；旧Leader不恢复；本阶段不需要原生Admission Lease Grant，因为候选不含活动Lease。终态request中的backend Lease ID值1仍只是终态记录哨兵。

调用者必须显式传入最大Txn操作数和字节预算。操作预算按compare+put保守计数；字节估算按Base64编码的紧凑HTTP Gateway JSON请求加安全余量计算，不等于已探测到的服务端限制。任一预算超限，工具标记容量超限并退出，不会静默拆批或跳过索引。

**安全边界：** 规划器不连接etcd、不执行Range/Txn/Lease/RBAC操作。后续真实写入前仍需线性一致空prefix复检、一次性临时集群/服务端RBAC排他、应用身份访问屏障、写后读回验证，以及Provider外部fencing floor独立核对。超出单Txn预算时必须先另行设计并演练checkpoint/未知结果恢复和应用启动隔离协议；本工具不实现批量导入，也不授权生产写入。

## CH17-T004 分阶段request索引导入与最终发布协议（第七十八轮）

新增只读协议模型 `scripts/spare_parts_sqlite_staged_import_protocol.py` 与专用测试。其核心顺序是：初始化checkpoint；按操作数/字节预算分批写入终态request索引，每批将request Put与checkpoint推进放在同一Txn；所有索引完成并线性一致读回后，最后单独发布 `scheduler/state`。

每批Txn比较本批request key不存在、checkpoint精确等于预期前驱、Scheduler state与Leader key仍不存在。checkpoint维护plan digest、已完成批次/记录数、最近batch digest和累积progress SHA-256。单个Scheduler aggregate仍不可拆分；它无法适配最终发布Txn时，协议在staging之前就拒绝。

未知Txn结果必须读回checkpoint与目标值，分类为COMMITTED、NOT_COMMITTED_RETRY_SAME_TXN或INCONSISTENT_QUARANTINE。etcd Txn不应出现合法部分提交；读到部分request key即隔离调查。此轮只提供协议与分类，不含实际etcd writer/自动续跑。

**应用访问门禁：** staging期间应用身份无权访问namespace；应用可能在state缺失时自动初始化空Scheduler，因此绝不能提前启动。导入完成后先读回最终state与Leader key，再撤销迁移写身份，只向应用身份开放业务所需精确键范围，并排除 `staging/`；随后才允许启动新Leader claim。Provider业务仍须独立完成外部fencing floor核验。

**第七十八轮验证：** [Knowledge Quality Run 46029534619](https://github.com/rexyll/cnc-knowledge/actions/runs/46029534619) success：594 unittest（40 skipped），CH12数值资源测试143项通过，knowledge lint 0 errors/5 warnings，结构检查0 errors。该轮只验证协议模型与仓库质量门禁，没有真实etcd写入/故障注入。

## CH17-T004 分阶段导入执行契约与故障注入模拟（第七十九轮）

进一步收紧 `classify_batch_unknown()`：读回checkpoint必须逐字节匹配当前不可变计划中当前批次或某一后续批次的预期checkpoint。`plan_sha256`、完成计数和request值即使各自看似正确，也不能代替对完整checkpoint链的精确验证；计划外checkpoint一律QUARANTINE。

新增 `tests/test_spare_parts_sqlite_staged_import_execution.py`，通过现有 `EtcdV3CoordinatorAuthorityStore` 适配器与 `InMemoryEtcdV3Client` 直接执行checkpoint初始化、request批次Txn和最终state发布。场景覆盖：提交后响应丢失并读回判定COMMITTED、提交前中断并仅重试相同Txn、模拟执行进程重建后从checkpoint续跑、竞争writer先写入目标key导致CAS整批失败，以及最终publish响应丢失后的精确读回确认。

这些测试验证现有adapter与内存fake上的事务/恢复契约，不是etcd服务端或三节点共识实验；不覆盖真实网络分区、节点掉电、跨主机并发、磁盘持久性、服务端Txn配置和RBAC。仍不包含真实writer或自动resume程序，本轮不触碰生产namespace。

**第七十九轮验证：** [Knowledge Quality Run 46092128612](https://github.com/rexyll/cnc-knowledge/actions/runs/46092128612) success：600 unittest（40 skipped，560 passed），CH12数值资源测试143项通过，knowledge lint 0 errors/5 warnings，结构/data检查0 errors。此结果证明当前内存adapter模拟和仓库质量门禁通过，不构成真实etcd三节点或生产迁移验收。

## CH17-T005 Unified schema-v2 运行时互操作与Leader epoch floor保真（第八十轮）

迁移候选包现把旧Leader epoch floor保存在统一aggregate内部的固定失效历史标记中。对旧epoch大于0的快照，marker严格为 \`leader_id="migration-epoch-floor"\`、\`epoch=旧epoch\`、\`expires_at=0.0\`、\`backend_lease_id=0\`。旧Leader真实身份和 \`coordinator/leader\` TTL key不恢复，也不为该marker创建原生Lease；它只用于让既有 \`claim_leadership()\` 在新Leader claim时自动推进至旧floor+1。若旧epoch为0，aggregate中的leader仍为 \`None\`，第一次claim为epoch 1。

候选bundle格式升级为 \`ch17-sqlite-unified-candidate-v2\`。Planner对marker进行完整字段精确校验，并拒绝旧v1候选包；修改前生成的v1 bundle必须从新的只读Inventory/Export重新构建，不能直接沿用。Coordinator runtime仅允许这个精确marker使用backend_lease_id=0；正常活动Leader记录仍必须持有正数Lease ID。

新增运行时互操作测试：分阶段写入终态request索引并最终发布aggregate后，用标准Unified Admission和Coordinator runtime读入。测试检查scope fencing/sequence floor、COMMITTED operation历史以及终态request幂等拒绝；终态request无论相同身份重放还是不同owner复用，都不得创建Admission Lease；正常Leader claim不传显式恢复floor也能从旧epoch 8推进至新epoch 9。epoch-zero测试则确保不会人为抬高floor。

**证据边界：** 互操作测试仅使用 \`InMemoryEtcdV3Client\` 和现有Store adapter。它验证运行时schema解析与应用逻辑，不证明真实etcd Raft/Quorum、磁盘耐久性、Lease超时精度、网络分区、跨进程并发或RBAC。没有在真实etcd上写入、Grant/Revoke Lease、修改RBAC、启动应用、触碰生产namespace或执行cutover。


## CH17-T006 外部Provider fencing floor只读对账门禁（第八十一轮）

新增脚本 spare_parts_sqlite_provider_fencing_reconciliation.py，对候选 v2 与操作员提供的Provider只读证据执行fail-closed逐scope对账。要求Provider证据覆盖候选全部scope且无多余scope；provider_generation必须精确匹配；Provider观察到的fencing token和operation sequence floor必须分别不高于候选floor。若Provider floor更高，则当前候选不能安全导入，必须先重新盘点并重建候选。

证据必须包含Provider ID、观察时间和固定schema，默认最多接受300秒内的采样。缺少scope、未知字段、generation不匹配、过期/未来采样及非法floor均会拒绝。成功结果包含canonical evidence SHA-256和逐scope比较明细。

**安全边界：** 该工具只验证调用方传入的数据，不连接真实Provider、不验证证据签名或身份、不写入Provider控制记录，也不授予应用访问或Provider mutation权限。采样后发生的Provider写入会使结果失效。真实可信采样、签名认证、写冻结和生产审批仍未完成。



## CH17-T006 Provider fencing 签名证据验签（第八十二轮）

新增 `scripts/spare_parts_sqlite_provider_fencing_signed_evidence.py`。该入口接受固定格式的签名信封和调用方提供的Ed25519公钥信任库；签名覆盖带域分离前缀的规范化完整证据JSON。仅当key_id在信任库中、算法/编码/长度合法且签名验证成功时，才继续调用第八十一轮只读对账器。

验签后仍执行原有300秒新鲜度、完整scope集合、provider_generation、fencing high-water token及operation sequence floor检查。输出增加签名验证状态、签名key ID和信任库SHA-256；application activation与Provider operation授权仍为false。

**安全边界：** 信任库本身的来源、审批、保护和轮换必须由外部可信流程负责；工具不连接KMS或Provider、不做真实采样、不写控制记录。签名只证明证据快照由对应私钥签署，不证明Provider在采样后持续冻结。当前离线工具没有持久化nonce/replay ledger，不能阻止有效旧快照在有效期内被重放。此功能不构成生产切换或应用启用授权。



## CH17-T006 Provider 冻结声明与防重放参考门禁（第八十三轮）

新增 `scripts/spare_parts_sqlite_provider_freeze_attestation.py`。签名声明必须绑定Provider ID、freeze ID/generation、UUID evidence ID、Coordinator challenge nonce、freeze时间窗、Coordinator Leader ID/epoch/native Lease ID及其期限，并携带逐scope Provider generation、fencing high-water token和operation sequence。

验证器还要求调用方提供近期Coordinator快照（默认最大年龄5秒）。签名声明中的Leader/epoch/Lease身份和有效期必须与该快照精确一致；快照scope floors必须与冻结证据逐scope相同；证据仍必须满足原有300秒新鲜度和候选floor上限。签名和所有绑定检查通过后，才将证据一次性写入replay ledger。

新增 `SQLiteProviderFreezeEvidenceReplayLedger` 作为单机参考实现：数据库文件权限0600，SQLite FULL同步，使用 `BEGIN IMMEDIATE` 原子插入，并通过唯一约束阻止同一Provider下的 evidence ID、challenge nonce 或 freeze ID/generation 再次消费。校验失败不消耗标识；ledger写入异常必须fail-closed。

**关键安全边界：** 此模块只验证Provider签名声明，不连接Provider或确认实际对象/数据写入路径已被锁住。因此 `provider_write_freeze_enforced` 仍为false，应用启用和Provider操作权限也始终为false。Coordinator快照当前是调用方输入，生产接入必须改为认证的线性一致权威读取。SQLite replay ledger仅适合同机演练，不具备跨主机共识，也无法防止可信管理员回滚数据库备份；生产多实例需使用共享线性一致、具备耐久性与CAS语义的账本（例如隔离etcd Txn），并将challenge nonce的签发与消费绑定在同一权威生命周期内。此轮未触碰真实Provider/KMS/etcd、生产数据或RBAC。



## CH17-T006 共享 etcd Provider freeze 防重放账本（第八十四轮）

新增 `scripts/spare_parts_provider_freeze_etcd_replay_ledger.py`，并将其接入既有 `validate_provider_freeze_attestation()`。此实现使用现有 `CoordinatorAuthorityStore` 的线性一致Get和原子Txn端口，目标namespace只接受隔离迁移路径 `/cnc/migration/isolated/{single-id}/`。

每次冻结证据消费会原子创建四个永久唯一键：Provider/evidence UUID、Provider/challenge nonce digest、Provider/freeze generation、Provider/freeze ID。Txn将四个键的VERSION=0比较与四个Put一次提交，键不附着Coordinator Leader Lease。与防重放键写入同一Txn的还有对 `scheduler/state` 和 `coordinator/leader` 的VALUE/MOD精确比较。写入前读取并校验Leader ID、epoch、native Lease ID及TTL attachment、expires_at，以及Coordinator aggregate中的逐scope floors；任何竞态更新都会让CAS失败。

Txn响应未知时先线性一致读回全部唯一键：四个值全部逐字节匹配才确认已提交；四个键全部不存在时，重新确认Coordinator binding后只重试完全相同的Txn；部分写入、冲突或持续未知均fail-closed/QUARANTINE，不自动修补。

**证据边界：** 自动化测试使用 `EtcdV3CoordinatorAuthorityStore` 与 `InMemoryEtcdV3Client`，证明当前客户端Txn映射、CAS竞态和未知结果分类契约；它不提供etcd Raft/Quorum、磁盘耐久性、跨主机故障或真实RBAC保证。namespace虽然限定为isolated路径，但真实部署仍须用一次性临时集群及服务端最小权限RBAC。SQLite ledger仍只适用于同机参考，生产多实例需真实etcd验证；Provider实际对象/multipart写路径是否真正冻结仍未验证，授权输出继续全部为false。


## CH17-T006 Provider-native持久化写冻结门（第八十五轮）

新增 `scripts/spare_parts_provider_write_freeze_gate.py`，定义与既有fencing proof分离的Ed25519签名控制命令协议。命令绑定issuer、Provider ID、tenant、scope、动作、freeze ID、generation和短有效期；Provider验证签名后，还在同一个SQLite控制事务中检查数据库可信key registry、算法、key fingerprint、状态和有效时间。

扩展 `scripts/spare_parts_provider_sqlite_fenced.py`：
- 新增可选Provider identity配置；未配置identity的实例不能应用freeze命令。
- 数据库schema从v2升级到v3，新增 `provider_write_freeze_scopes`，保存每个tenant+scope的单调generation、freeze ID、FROZEN/OPEN状态、命令摘要和更新时间。已有v2数据库启动时执行加法迁移。
- 新增 `apply_write_freeze_command()` 和只读 `write_freeze_state()`。每个scope只接受连续的下一代命令；同一精确命令可幂等重放；UNFREEZE必须匹配当前活动freeze ID。旧代次、跳号、相同generation不同内容、错误freeze ID、错误Provider/tenant和无效签名均拒绝。
- 普通对象fenced PUT、multipart begin、part、complete均在现有 `BEGIN IMMEDIATE` 事务中检查冻结状态。FROZEN立即拒绝；UNFREEZE后写proof必须携带当前 `provider_freeze_generation`，旧proof无法复用。只读路径保持可用，unfenced mutation仍不可用。
- Provider备份校验要求v3 schema和冻结表，备份/恢复准备会保留freeze generation和状态；缺少冻结表的旧v2备份不被当作可验证恢复输入。

**边界：** 这证明的是同机SQLite写事务中的Provider参考门禁与事务排序，不是云对象存储或远程Provider服务的冻结保证。签名控制命令目前由本地Provider类接收，尚无远程Gateway、KMS/HSM、服务端RBAC或跨主机CAS。独立的Provider freeze attestation验证器仍将 `provider_write_freeze_enforced=false`，因为它没有查询真实Provider部署状态。


#### 第八十六轮补充：Freeze命令未知结果恢复

- 新增 provider_write_freeze_commands 持久化命令收据表，完整签名envelope digest为主键；收据与scope generation/state变更在同一个 BEGIN IMMEDIATE 事务中写入。
- 任意历史精确命令重放都返回 ALREADY_APPLIED，包括scope已经经历后续UNFREEZE/新generation的情况；返回历史结果与当前scope状态，重放不产生任何状态迁移。
- 新增只读 write_freeze_command_status()，Coordinator可按原envelope digest查询历史提交收据；收据随SQLite backup/restore保留。
- 未查到收据不是跨网络未知请求的最终“未提交”证明；远程Provider必须提供等价的线性一致receipt查询与幂等控制端点。

#### 第八十七轮补充：Freeze命令与Coordinator Leader绑定

- Freeze命令协议升级v2，签名绑定Coordinator namespace、Leader ID、Leader epoch、native Lease ID及Lease expiry；命令expiry必须不晚于Leader Lease expiry。
- Provider schema v4新增每scope Leader epoch high-water表及每命令Leader审计表。命令收据、freeze scope状态、Leader floor及审计记录在同一SQLite写事务中提交。
- 已观察更高epoch后拒绝较低epoch的新命令；相同epoch不允许更换Leader ID或native Lease ID；namespace在scope生命周期内固定。更高epoch可接管现有freeze，但UNFREEZE仍必须匹配active freeze ID。
- 历史精确命令receipt仍优先解析，旧命令重放只返回ALREADY_APPLIED，不回滚当前状态。
- **限制：** Provider本地只验证签名声明的Lease expiry，不在线查询真实etcd Lease是否存在、是否附着或是否提前撤销。未观察新epoch前的旧Leader有效窗口仍存在；生产必须增加线性一致在线Leader/Lease检查或等价撤销机制。

- 追加防回退：Coordinator namespace必须为规范绝对前缀；同一epoch/Lease ID的Lease expiry不得低于Provider已观察值。

- v4备份校验强制要求freeze scope、command receipt、Leader floor和command-Leader审计四类表全部存在；备份恢复保留Leader epoch/Lease绑定。


## CH17-T004 Provider Freeze 在线 Leader 校验（第八十八轮）

- 新增[Provider Freeze 在线 Coordinator Leader / Native Lease 校验](provider-online-coordinator-leader-verification.md)。
- 新增在线只读校验器：通过单次线性一致前缀Range同时读取Scheduler aggregate和Leader TTL key，验证Leader ID、epoch、native Lease ID、key的Lease attachment与expiry。
- Provider增加可选 `require_online_leader_status=True`。新命令在线校验失败或store不可用时fail closed；精确历史receipt重放仍优先返回历史结果。
- **重要限制：** etcd Range与Provider SQLite commit没有共同事务，仍存在检查后撤销的TOCTOU窗口。本轮不是跨系统原子fencing，不代表生产接入或stale-Leader风险彻底消除。
- 测试使用合成store/fake checker；真实三节点etcd、真实Provider和网络分区联合验证仍未执行。


## CH17-T006 Provider 可撤销授权与撤销屏障架构（第八十九轮）

新增[Provider 可撤销授权与撤销屏障架构设计](provider-revocation-barrier-architecture.md)，用于处理第八十八轮在线Leader/Native Lease检查仍存在的跨系统TOCTOU。

核心结论：etcd线性一致Range与Provider SQLite commit没有共同事务；将Range移入SQLite事务也不能阻止etcd Lease在Range之后变化。Provider mutation必须在最终提交事务或Provider原生条件写边界内检查可撤销grant/epoch。推荐评估Provider参与的FENCE屏障：旧grant撤销与实际mutation共享Provider线性化顺序，持久化receipt，只有屏障receipt可验证后才允许新epoch grant激活。

**语义限制：** Provider FENCE提交是Provider侧撤销的线性化点，不是etcd Lease物理过期的同一瞬间。若业务要求跨独立系统零窗口撤销，必须具备共享事务权威或Provider原生原子条件写；单纯在线Range、签名expiry或异步Watch均不能证明这一点。

本轮为架构决策文档，不包含grant/FENCE实现、真实Provider/etcd联调、RBAC变更或生产迁移。


## CH17-T006 Provider-native Revocable Grant / FENCE Barrier（第九十轮）

第九十轮新增`scripts/spare_parts_provider_revocable_grant.py`，定义独立Ed25519签名的FENCE/ACTIVATE命令；扩展`scripts/spare_parts_provider_sqlite_fenced.py`，增加按tenant/scope隔离的Provider grant状态与完整命令receipt。

状态转换采用两步：
1. **FENCE：** 更换Leader/Lease身份时必须由更高Coordinator Leader epoch发起；同epoch仅允许完全相同Leader/Lease主动撤销其ACTIVE grant。FENCE将scope推进至FENCED，旧grant立即不能再通过Provider本地mutation gate。
2. **ACTIVATE：** 必须引用已提交FENCE命令的精确SHA-256 receipt，并保持Coordinator namespace、Leader ID/epoch、native Lease和grant ID完全一致，才能创建ACTIVE grant。

Provider schema升级至v6，新增`provider_scope_grants`与`provider_grant_commands`；每条Grant回执另外保存规范化完整`envelope_json`与`signer_public_key_base64`。备份校验重算完整envelope SHA-256、核对公钥指纹、重新验证Ed25519签名，并检查ACTIVATE/FENCE同一Provider/tenant/scope/grant绑定、代次连续、回执时间顺序及当前scope状态；断链、签名错误或信任表缺失时拒绝备份。运行时每个受保护mutation也在Provider事务内重新验签当前FENCE和ACTIVATE receipt。旧v5回执缺少原始envelope和签名公钥材料，升级后被视为legacy-unverifiable，不能放行mutation或通过backup验证。配置`require_revocable_grant=True`时，Provider必须同时配置Provider ID、Ed25519命令信任公钥和在线Coordinator Leader checker；缺少任一项即初始化失败；在线checker返回inactive或抛出异常时，FENCE/ACTIVATE fail-closed且不得创建/推进grant状态。proof必须签署Grant ID与generation，Provider在object PUT、multipart begin、part、complete各自实际写事务内校验ACTIVE、期限和代次，并通过FENCE receipt核对Provider ID，防止同一SQLite文件跨Provider身份复用。Freeze/Unfreeze与Grant命令应用均不接受调用方注入时间；获得SQLite写锁后和在线Leader读取后再次校验签名命令时间窗，避免等待锁期间过期命令落库。在线Leader检查只作为FENCE/ACTIVATE命令的前置门禁，不能被描述为跨系统原子授权。FENCE与mutation共用同一SQLite `BEGIN IMMEDIATE`事务，因此本地参考实现中的两个操作具有可观察的串行顺序。

命令收据按完整envelope digest持久化；ACTIVATE签发时间不得早于FENCE回执的Provider本地提交时间，FENCE/ACTIVATE命令及ACTIVE Grant的绝对有效期最多5分钟（并且不能晚于native Lease expiry），以限制Provider暂时无法收到新FENCE时旧Grant的残余使用窗口。提交后模拟响应丢失时可按原digest读回并判定ALREADY_APPLIED。备份会验证并保留完整FENCE/ACTIVATE回执链，但只要备份包含Grant状态或命令历史，通用Restore会fail-closed拒绝执行，因为当前恢复接口没有独立Provider Grant generation/Leader epoch floor；不能通过恢复旧备份或新命令猜测重试。

**证据边界：** 这是同机SQLite参考模型，不是远程对象存储/Provider写路径证明，不证明跨主机一致性或etcd与Provider跨系统原子fencing。Provider FENCE提交是Provider侧撤销屏障的线性化点；它不等于独立etcd Lease物理过期的同一瞬间。当前实现没有连接真实etcd、Provider、KMS/HSM或IAM/RBAC，也未启用生产授权。


## CH17-T006 Provider Grant 外部单调 Floor 与 Restore 对账（第九十一轮）

新增[Provider Grant 外部单调 Floor 与 Restore 对账设计](provider-grant-external-floor-and-restore-reconciliation-design.md)，补足第九十轮暴露的备份回滚边界：Provider Grant generation、Leader epoch 和 receipt 当前只存在 Provider SQLite 备份域内，旧备份无法证明自身是最新版本。

设计提出独立 ProviderGrantFloorAuthority，按Provider/tenant/scope保存单调generation、Leader epoch、FENCE/ACTIVATE pending operation、command digest和Provider receipt digest；FENCE/ACTIVATE采用外部预留、Provider本地提交、外部精确回执确认的双边协议。专用Restore必须在线性一致外部floor上对账，pending或unknown状态不能靠猜测重试。

**当前强制门禁：** 通用 restore_to_new_database() 仍拒绝任何包含Grant scope或command history的备份。只有独立floor authority及专用Restore对账实现并验收后，才可设计恢复放行；本轮文档不是放行依据。


### 15.17 第九十二轮：Provider Grant 外部 Floor 本地参考适配器

新增 scripts/spare_parts_provider_grant_floor.py，提供独立文件 SQLiteProviderGrantFloorAuthority 参考适配器和 ProviderGrantFloorAuthority 端口基类；新增 tests/test_spare_parts_provider_grant_floor.py，包含20个测试方法定义，覆盖FENCE/ACTIVATE外部预留和回执确认、scope revision CAS、operation ID幂等、未知结果重启查询、Leader epoch/namespace/native Lease expiry单调性及scope隔离。

该适配器使用独立SQLite文件，按Provider/tenant/scope保存generation与Leader epoch floor、pending operation、命令摘要和Provider回执摘要。FENCE/ACTIVATE分别通过reserve→Provider commit→confirm推进；同一operation ID只能绑定完全相同的命令，未知结果只能查回或重试原operation。特别注意：FENCE_PENDING只是外部预留，不会立即撤销Provider旧ACTIVE Grant；旧Grant在Provider FENCE真正提交前仍可能被接受（受当前最多300秒有效期限制）。Provider事务内FENCE提交才是数据面撤销线性化点。

**边界：** 这是单机SQLite事务参考，不是etcd线性一致/多节点/quorum实现；SQLite自身不能证明数据库文件未从旧快照回滚，只有与该数据库独立保存的可信revision checkpoint才能用于检测回退。适配器不验证Provider回执签名/真实性，也尚未接入Provider命令应用路径或Unified schema-v2 authority。当前没有Grant-aware Restore；通用Restore对任何Grant历史备份仍必须拒绝。测试方法定义数量不是测试执行结果。

Provider Grant 外部 Floor 本地参考适配器见 [外部单调 Floor 与 Grant-aware Restore 对账设计](provider-grant-external-floor-and-restore-reconciliation-design.md)：实现文件为 [spare_parts_provider_grant_floor.py](../../scripts/spare_parts_provider_grant_floor.py)，专项测试为 [test_spare_parts_provider_grant_floor.py](../../tests/test_spare_parts_provider_grant_floor.py)。本地 SQLite 适配器仅接受 `/cnc/migration/isolated/{single-id}/` namespace，是单机事务/CAS参考模型，不是 etcd quorum、线性一致生产 authority 或自身防回滚存储。Provider Receipt 签名协议和外部 Floor 验签已在第九十五轮实现；第九十六轮又将 Provider 本地 FENCE/ACTIVATE 同事务 Receipt 持久化和按 command digest 查询接入 SQLite 参考实现。生产 Provider、KMS/HSM、外部 trust control plane 与专用 Grant-aware Restore 仍未实现。

Provider Grant 回执来源认证的协议设计见 [Provider Grant Floor 回执来源认证与签名证据设计](provider-grant-receipt-authentication-design.md)；本地实现见 [Receipt 协议模块](../../scripts/spare_parts_provider_grant_receipt.py)、[外部 Floor schema v5、Coordinator/Provider 双签名验签门禁](../../scripts/spare_parts_provider_grant_floor.py) 及其 [Floor 测试](../../tests/test_spare_parts_provider_grant_floor.py) / [协议测试](../../tests/test_spare_parts_provider_grant_receipt.py)。Floor 本地验签仍依赖独立 Provider key registry；Provider SQLite 本地实现会在 FENCE/ACTIVATE 同一写事务内生成并持久化 signed Receipt，并提供按 exact command digest 查询。但两者仍是单机 SQLite 参考模型：Provider 回执公钥副本只用于本地自洽校验，外部 Floor registry 才是签名者信任锚；真实 Provider/KMS/HSM/production trust plane 与 Grant-aware Restore 尚未实现。

### 第九十五轮：Provider Grant Receipt 协议模块与 Floor schema v4

新增 [Provider Grant Receipt 协议模块](../../scripts/spare_parts_provider_grant_receipt.py) 与 [专项协议测试](../../tests/test_spare_parts_provider_grant_receipt.py)，将外部 Floor 从接收裸摘要改为校验独立 Provider Ed25519 signed envelope；Floor 保存完整 canonical Receipt digest、signer fingerprint/trust revision，并将 Provider applied time 与 Coordinator command issue/expiry 固定到 reservation。

外部 Floor schema 由 v1 迁移至 v4，提供 Provider receipt key 显式注册、RETIRING/REVOKED 生命周期与历史记录兼容迁移；旧裸摘要保留为未认证历史，不自动升级。完整设计和限制见 [Provider Grant Floor 回执来源认证与签名证据设计](provider-grant-receipt-authentication-design.md)。

**严格边界：** Provider Receipt 在本地 SQLite FENCE/ACTIVATE 事务中原子生成并持久化，但签名私钥仍通过进程内合成 Ed25519 key 注入；这不是远程 Provider、KMS/HSM 或多主机安全证明。Floor 不独立验证 Coordinator command signature；Reservation 中的 command digest/claims 可信来源仍由上游 Coordinator 调用链负责。Provider 数据文件和 Floor/trust registry 都不能检测自身旧快照回滚，必须依赖备份域外可信 checkpoint。真实 Provider/KMS/HSM/etcd/生产 trust registry 未连接，Grant-aware Restore 未实现，通用 Restore 仍 fail-closed。

- **第九十五轮当前代码验收：** [Knowledge Quality Run 46155354641](https://github.com/rexyll/cnc-knowledge/actions/runs/46155354641) 两个必需 Job 均 success；全库 737 项测试运行、40 项按环境跳过；CH12 数值资源 143 项通过；knowledge lint 0 errors / 5 warnings，结构/数据检查 0 errors。此Run验证的是代码与专项测试提交；随后计划/README/TaskHistory最终同步仍需以其自身CI为准。
- **第九十五轮最终文档同步验收：** [Knowledge Quality Run 46155719334](https://github.com/rexyll/cnc-knowledge/actions/runs/46155719334) 两个必需 Job 均 success，覆盖根/CH17 TaskPlan、设计文档、README、TaskHistory和代码；无测试失败。


### 第九十六轮：Provider SQLite 同事务 Signed Receipt 与 Floor 联调

- Provider `spare_parts_provider_sqlite_fenced.py` 升级至 schema v7，保留 Coordinator 命令 envelope 字段并新增独立 Provider Receipt envelope、digest、signer key ID 和公钥副本字段。
- FENCE/ACTIVATE 验证完 Coordinator 命令并获得 Provider SQLite 写锁后，在同一事务中更新 Grant state、保存 Coordinator command receipt、构造 Provider Receipt claims、使用与 Coordinator key 不同的 Ed25519 private key 签名并保存 canonical envelope/digest；事务提交前不对外可见。
- `provider_grant_receipt_signing_required` policy 会被持久化，启用后后续 Provider 实例不能静默降级。strict 模式中当前 ACTIVE Grant 的 FENCE 和 ACTIVATE Receipt 必须存在且能独立验签，否则拒绝所有受保护 object/multipart mutation。
- 新增 `get_provider_grant_receipt(provider_id, tenant_id, command_sha256)` 按 exact Provider/Tenant/command digest 查询；同一 command 重复执行会验证并返回已存 Receipt，不能改变 digest 或重复推进 generation；commit 后响应丢失可按原 digest 恢复。
- Provider backup validation 现在验证 Provider Receipt 完整 canonical digest、签名、与原 Coordinator signed command 逐字段绑定、FENCE/ACTIVATE generation 与时间链；仅当前 strict Grant 链必须具备签名 Receipt。旧历史命令可保留但不会被自动补签或提升为当前授权证据。
- Provider→Floor 端到端测试使用实际本地 Provider 签名输出 FENCE 和 ACTIVATE receipt，由 Round95 外部 Floor 独立 Provider key registry 验签并推进 FENCED/ACTIVE；同时覆盖事务提交前故障全回滚、response loss、重启/幂等、精确 lookup、schema v6→v7、strict policy 不可降级、receipt digest 及伪造 signature 篡改和备份拒绝。
- **验证：** [Knowledge Quality Run 46157250066](https://github.com/rexyll/cnc-knowledge/actions/runs/46157250066) 两个必需 Job 均 success；全库 745 项测试运行、40 项按环境跳过；CH12 数值资源 143 项通过；knowledge lint 0 errors / 5 warnings，结构/数据检查 0 errors。

**第九十六轮结束时的信任缺口（已由第九十七轮本地实现补齐）：** 当时外部 Floor reserve API 仍接受调用方传入的 Coordinator command digest 和 claims。第九十七轮现已让 Floor 直接接收并验证 Coordinator signed command envelope。剩余生产边界仍包括：Provider Receipt 公钥副本只用于 Provider 本地自洽签名检查，独立 Floor key registry 才承担 Provider signer 信任；当前仍没有生产密钥管理、KMS/HSM、独立多节点 authority 或 Grant-aware Restore。


### 第九十七轮：External Floor Coordinator Signed Command Trust（schema v5）

- 外部 Floor `scripts/spare_parts_provider_grant_floor.py` 升级至 SQLite schema v5，新增独立 Coordinator Ed25519 command key registry，按 issuer/key ID保存public key、SHA-256 fingerprint、ACTIVE/RETIRING/REVOKED、not_before/not_after、retiring/revocation effective time、reason及trust revision。
- 新Floor默认启用 `coordinator_command_auth_required=1`；v1–v4历史数据库迁移到v5后也默认strict。只有显式创建的本地测试/兼容库可配置 `allow_legacy_unsigned_reservations=True` 使用原始digest/claims参数式API；严格Floor不可降级。
- 新增显式本地owner key注册/退役/撤销管理API。新reservation只接受ACTIVE Coordinator key；RETIRING/REVOKED key不能创建新reservation。已受信任的operation保存Coordinator signer key ID、key fingerprint和trust revision，作为不可伪造补写的审计字段。
- 新增 `reserve_fence_from_command(operation_id, key, command_envelope, expected_revision)` 和 `reserve_activate_from_command(...)`。调用方必须显式传入预期 `ProviderGrantScopeKey`；Floor把签名claims内Provider/Tenant/scope与调用方目标逐字段匹配，不允许signed command自行切换scope。
- Floor在同一SQLite `BEGIN IMMEDIATE`事务内拒绝重复JSON key/非有限常量，使用Coordinator原签名canonicalization重新计算完整command digest，独立查询Coordinator trust registry并验Ed25519签名；校验issuer、Provider/Tenant/scope、FENCE/ACTIVATE action、Grant ID、generation、Coordinator namespace、Leader epoch/native Lease、issued/expiry时间和FENCE digest。command generation必须等于Floor下一generation，ACTIVATE必须引用最近一次已确认FENCE。
- 所有签名/identity/lifecycle/time/generation/CAS校验完成前，不推进scope revision或authority revision，不创建scope、不写pending operation。`confirm_provider_receipt()`仍要求Round95 Provider signed Receipt；严格模式下旧迁移PENDING operation若无Coordinator signer ID/fingerprint/trust revision，不能只凭Provider Receipt被补认证并确认。
- Provider→Floor集成测试改为先注册独立Coordinator command public key及Provider receipt public key，再将真实Provider输出的FENCE/ACTIVATE command envelope传入Floor signed-command API；Floor验签后再通过Provider signed Receipt确认状态。专项测试覆盖命令签名篡改、未知/撤销key、key rotation、重复JSON key、跨Provider/Tenant/scope、wrong generation、时间/native Lease上限、裸claims拒绝、strict no-downgrade、v1→v5迁移、legacy PENDING fail-closed和失败不推进revision。
- **验证：** [Knowledge Quality Run 46159157703](https://github.com/rexyll/cnc-knowledge/actions/runs/46159157703) 两个必需Job均success；全库757项测试运行、40项按环境跳过；CH12数值资源143项通过；knowledge lint 0 errors / 5 warnings；结构/数据检查0 errors。该Run覆盖Floor Coordinator trust实现、专项测试和legacy pending门禁。后续README/设计文档/TaskHistory完整同步以最终文档提交CI为准。
- **最终扩展回归验收：** [Knowledge Quality Run 46159590900](https://github.com/rexyll/cnc-knowledge/actions/runs/46159590900) 两个必需Job均success；全库762项测试运行、40项按环境跳过；CH12数值资源143项通过；knowledge lint 0 errors / 5 warnings；结构/数据检查0 errors。该Run还覆盖目标Provider/Tenant/scope绑定、命令expiry/native Lease边界、exact operation重放及strict Floor旧PENDING不追认门禁。

**保留限制：** 当前只证明单机SQLite Floor和合成Ed25519 key。Coordinator key注册表是本地数据库owner管理入口，不含生产审批/远程KMS/HSM、多节点发布或外部防回滚checkpoint；Floor SQLite文件和trust registry自身仍可被旧快照覆盖。没有接入真实Coordinator/etcd/Provider/object storage/IAM/RBAC，不实现Grant-aware Restore，不解除含Grant历史备份的通用Restore fail-closed门禁。Production Unified schema-v2仍为唯一authority。



### 第九十八轮：Provider Grant Floor 外部检查点与快照回滚检测

新增 [外部 Floor checkpoint 保护模块](../../scripts/spare_parts_provider_grant_floor_checkpoint.py) 与 [专项测试](../../tests/test_spare_parts_provider_grant_floor_checkpoint.py)。

- `ProviderGrantFloorCheckpointStore` 定义独立 checkpoint 读取与单调 CAS 接口；checkpoint 同时绑定独立 sequence、Floor authority revision 和完整逻辑数据库 SHA-256。
- `calculate_floor_checkpoint_state()` 对 SQLite schema、metadata、scope、operation 以及 Provider/Coordinator trust registry 全量摘要；检测同一 authority revision 下的内容变化，而不只比较 revision 数字。
- `CheckpointedSQLiteProviderGrantFloorAuthority` 包装所有公开读写 API，读写前核验外部 checkpoint，写入改变状态后 CAS 推进；严格空库 bootstrap，非空未锚定库拒绝自动接管。
- SQLite 提交后 checkpoint 更新不确定时，不自动回滚或猜测；只有预期 checkpoint 的精确 read-back 才能确认成功，否则后续操作 fail-closed。
- 测试包含正常 FENCE/ACTIVATE、trust-key 变化、精确重放、SQLite 旧快照恢复、同 revision 内容篡改、checkpoint 回退、CAS 响应丢失和后端故障。

**边界：** 当前仅为单进程 SQLite wrapper + in-memory CAS fake；fake 不持久、不防回滚，wrapper 不提供跨进程锁。没有实现生产外部 checkpoint service 或共同事务域，也没有接入真实 etcd/KMS/HSM/Provider。Grant-aware Restore 尚未实现，含 Grant history 的通用 Restore 仍 fail-closed。

- **最终验证：** [Knowledge Quality Run 46162907743](https://github.com/rexyll/cnc-knowledge/actions/runs/46162907743) 两个必需Job均成功；全库776项测试运行、40项环境跳过；CH12数值资源143项通过；knowledge lint 0 errors / 5 warnings。Round98专项测试14项全部通过。

### 第九十九轮：Provider Grant Floor Etcd-native 单事务权威架构

新增 [Etcd-native Floor 原子权威设计](provider-grant-floor-etcd-native-atomicity-design.md)。本轮审计发现，仓库现有 CoordinatorAuthorityStore / EtcdV3CoordinatorAuthorityStore 是KV/Txn primitive，而应用级 DurableCoordinatorAuthorityBackend仍是SQLite服务；不能把Etcd primitive adapter误称为已实现的生产Grant Floor状态机。

- 设计以Etcd Txn为Provider Grant Floor唯一运行期权威；scope、operation、Coordinator/Provider trust metadata、append-only event、authority revision、event sequence与state-root必须在同一Txn Compare+Put。
- 签名验签使用的Coordinator/Provider trust row必须通过同一Txn的VALUE/MOD Compare固定，避免key在验签后、提交前被并发撤销或轮换。
- Etcd Txn timeout按OUTCOME_UNKNOWN处理；只有原operation ID、原signed envelope和完整meta/scope/operation/event精确读回匹配时才能确认，部分/冲突状态隔离。
- 将Etcd集群snapshot整体回滚与正常运行期Txn原子性分开；Etcd内部revision/state-root不能自证没有整体回滚。设计域外witness，并定义逐笔PREPARE → Etcd PREPARE/COMMIT → Witness COMMIT → Etcd FINALIZE严格耐久模式。

**边界：** 本轮只有架构设计；Etcd-native业务服务、生产witness持久化与RBAC、真实Etcd多节点/网络分区/快照恢复验证未实现。Production Unified schema-v2仍为唯一生产authority；未执行迁移、Grant-aware Restore或Cutover。
- Witness取消语义已细化：Etcd PREPARE结果未知时不能只凭一次未发现pending的Range就标记ABORTED；COMMIT/ABORT必须由同intent compare竞争，Etcd COMMIT确定后不可回退。
- Rollback witness只保存sequence/root时只能检测整体snapshot回滚，不足以重建数据；若无域外事件正文或可信备份，必须维持写隔离并逐scope受控重建。v1全局meta/event root意味着写入全局串行化，吞吐需后续实测。