# Provider Grant Floor Etcd-native 原子权威设计

> CH17 / Round 99（2026-11-29）
>
> 状态：DESIGN_COMPLETE / IMPLEMENTATION_NOT_STARTED。本文冻结Etcd-native Floor的目标模型与实施规格；不代表生产Etcd集群已连接、RBAC已配置或生产Restore已获准。

## 1. 决策摘要

Round98的CheckpointedSQLiteProviderGrantFloorAuthority证明了单进程本地SQLite wrapper可以在每次操作前后核验外部CAS checkpoint，但它仍然跨越两个独立提交域：Provider Grant Floor的SQLite事务与外部checkpoint服务。SQLite已经提交而外部CAS不能确认时，只能fail-closed，不能回滚或推测结果。

仓库已经提供etcd v3的KV/Txn primitive adapter，但这并不意味着应用级Provider Grant Floor服务已经使用Etcd事务。当前DurableCoordinatorAuthorityBackend在authority store模块中明确仍代表SQLite业务服务；EtcdV3CoordinatorAuthorityStore则只是底层KV/Txn port adapter。

因此生产目标不是给SQLite wrapper换一个checkpoint backend，而是新增一个直接基于CoordinatorAuthorityStore的Etcd-native ProviderGrantFloorAuthority实现。所有一次状态变更涉及的scope、operation、trust metadata、authority meta、event和state-root checkpoint必须在同一个Etcd Txn中Compare+Put。

**本轮架构决策：**
1. Etcd是Provider Grant Floor运行期间的单一权威；不保留“SQLite业务写成功后再更新Etcd checkpoint”的双写流程。
2. 每个FENCE/ACTIVATE reserve、Provider Receipt confirm和trust-key lifecycle mutation必须对应一个不可拆分Txn。
3. Etcd Txn timeout按OUTCOME_UNKNOWN处理；只有完整、精确的线性一致读回才能证明已提交。
4. Etcd内部sequence/state-root用于运行期一致性审计，不是Etcd集群自身snapshot rollback的独立信任锚。
5. Etcd snapshot恢复前必须与备份域外witness checkpoint比较；witness能力、更新频率和RPO必须显式声明。未达恢复点要求时，不开放Grant mutation或生产服务写入。

## 2. 现有代码边界审计

### 2.1 已存在的基础设施

- `scripts/spare_parts_provider_authority_store.py` 定义 `CoordinatorAuthorityStore` primitive port：线性一致精确读取、Compare、Txn分支和Lease API。Etcd adapter通过 `EtcdV3CoordinatorAuthorityStore` 把typed Compare/Put/Get/Delete翻译为etcd v3请求。
- `EtcdV3CoordinatorAuthorityStore.transact()` 原子执行Compare和单一success/failure分支；支持事务分支内的有序Get。传输超时被归类为 `AuthorityStoreOutcomeUnknownError`，不会自动换operation identity重试。
- `scripts/spare_parts_provider_etcd3gw_driver.py` 提供Etcd gRPC-gateway Driver，单次Mutating Txn请求不自动重发；认证/权限错误与transport error有不同错误类型。
- `InMemoryEtcdV3Client` 可用于契约测试，但不提供Raft quorum、持久化或多主机线性一致证明。
- `scripts/spare_parts_provider_grant_floor.py` 仍是单机SQLite Floor schema v5，内含Provider Receipt和Coordinator signed command trust registries。
- `scripts/spare_parts_provider_grant_floor_checkpoint.py` 仍是SQLite + 单进程wrapper；内存CAS仅用于测试，不是生产checkpoint backend。

### 2.2 禁止的错误等同

`CoordinatorAuthorityStore` 是KV/Txn primitive，不是已经迁移的业务状态机。当前 `DurableCoordinatorAuthorityBackend` 文档接口仍明确指向SQLite authority service。因此：

- 不能仅仅构造 `EtcdV3CoordinatorAuthorityStore` 就宣称Grant Floor状态机已运行在Etcd。
- 不能把SQLite提交与Etcd checkpoint CAS顺序执行称为原子事务。
- 不能把InMemoryEtcdV3Client测试结果写成Etcd多节点或quorum验收。
- 不能把Etcd的header revision、mod_revision或内部state-root描述为能够识别Etcd自身旧snapshot恢复的机制。

## 3. Etcd数据模型与隔离键布局

### 3.1 Namespace

Round93已经把当前本地Grant Floor参考模型的Coordinator namespace严格收敛为：

`/cnc/migration/isolated/{single-id}/`

Etcd-native演练adapter本轮只使用以下专属子树：

`/cnc/migration/isolated/{single-id}/provider-grant-floor/v1/`

其中 `single-id` 必须是一个合法且不可变的单路径段。该演练前缀不得被用于声称生产Unified schema-v2路径已经迁移。生产命名空间需要独立批准和RBAC设计，不在本轮扩展命名规则。

所有实体ID、scope和key ID先按既定规范做严格类型校验，再参与canonical identity encoding；Etcd key path只使用其SHA-256派生的十六进制标识，禁止直接将调用方字符串拼接为路径。Value中必须保留原始Provider/Tenant/scope/issuer/key ID，并在读回时验证其与派生键精确一致，不能仅因hash路径命中就接受记录。

### 3.2 Key layout

| Key suffix | Value | 写入规则 |
|---|---|---|
| `meta/state` | schema version、namespace ID、authority revision、trust revision、event sequence、state-root digest、policy flags | 每个状态变更Txn更新一次 |
| `scopes/{scope-key-sha256}` | Provider/Tenant/scope identity、generation floor、Leader epoch/native Lease、FENCE/ACTIVATE状态、pending operation、receipt digest和scope revision | 每个scope状态变更Txn更新 |
| `operations/{operation-id-sha256}` | operation ID、action、command digest、Grant/generation、签名者审计字段、状态、Receipt digest及revision | operation ID创建后不可更换身份；状态转移通过CAS |
| `provider-keys/{provider-id-sha256}/{key-id-sha256}` | Provider Receipt signer public key、fingerprint、状态生命周期、trust revision | 仅owner治理入口写入 |
| `coordinator-keys/{issuer-id-sha256}/{key-id-sha256}` | Coordinator command signer public key、fingerprint、状态生命周期、trust revision | 仅owner治理入口写入 |
| `events/{sequence-20-digit}` | 不可变状态转移事件、operation ID、涉及key摘要、previous root、next root和证据摘要 | 每次成功状态变更追加；不原地覆盖 |

Scope、operation和trust-key value采用受限schema和规范化JSON编码；拒绝重复字段、未知关键字段、非有限数字、超出SQLite/Etcd应用预算的长度和无效身份。签名命令与Provider Receipt继续沿用其现有canonicalization与domain-separated Ed25519协议，不得由Etcd适配器重新解释签名输入。

### 3.3 Meta与state-root

`meta/state`最少保存：
- `schema_version`、`namespace_id`、`coordinator_command_auth_required`；
- `authority_revision`：所有Floor业务/信任状态变更单调递增；
- `trust_revision`：Provider/Coordinator key注册、轮换、退役、撤销时递增；
- `event_sequence`：每个成功状态变更递增；
- `state_root_sha256`：追加式事件链摘要；
- 必需的policy version与key-schema version。

事件链摘要采用带domain separator的规范化结构：

`next_root = SHA256(domain || previous_root || canonical_event_bytes)`

Event要覆盖operation identity、action/state transition、scope identity hash、command digest、receipt digest、Signer trust revision、写入前后scope revision和event sequence。所有state-changing路径必须先生成同一规范事件，再在一个Txn里同时写scope/operation/meta/event。不能有绕过event/meta更新而直接Put业务key的应用写路径；Etcd RBAC只允许授权的Floor服务身份写该隔离前缀。

该state-root是应用状态机的审计链，不是独立签名，也不是Etcd snapshot的域外防回滚证明。攻击者若可以将Etcd集群及其所有KV一起恢复到旧snapshot，meta和event chain也会一并回退。

## 4. 一次状态转移的Etcd事务协议

### 4.1 通用Compare集合

每个状态变更先对需要参与判定的exact keys做线性一致读取，解析并验证所有记录和签名。随后在一个Txn中精确Compare刚才读取的版本：
- meta：对完整value或mod_revision进行Compare；
- scope：IDLE新建使用VERSION=0；已有scope使用其精确mod_revision或完整value；
- operation：新operation使用VERSION=0；已有operation必须匹配相同operation ID和原始command digest；
- Coordinator/Provider trust key：对验签时读取的trust record value/mod_revision做Compare，防止验签和Txn提交之间key被并发撤销或轮换；
- event：新sequence对应的event key必须VERSION=0。

任何Compare失败都不能复用上一次读取时的签名/claims验证结论；必须重新线性一致读取相关scope、operation、meta和trust records，再决定是否可用同一个operation ID与完全相同Envelope重试。

### 4.2 FENCE reservation

一个FENCE reserve Txn至少原子完成：
1. Compare当前meta、目标scope不存在/当前revision、operation key不存在、Coordinator signer trust row精确值；
2. Put更新后的scope（FENCE_PENDING、下一代generation、Leader/Lease绑定、pending operation ID）；
3. Put不可变身份的operation记录（PENDING、完整signed command digest、Coordinator signer fingerprint/trust revision和claims binding）；
4. Put更新meta（authority_revision + 1、event_sequence + 1、next state root）；
5. Put对应append-only event。

任何一个Compare失败，success分支所有Put都不执行。不能先reserve scope再单独补写operation或checkpoint。

### 4.3 ACTIVATE reservation

ACTIVATE reserve同样一个Txn完成：
- Compare scope必须处于FENCED，且引用最近一次已确认FENCE的精确command/receipt digest；
- Compare generation、Coordinator epoch、Leader ID/native Lease ID、namespace和Lease expiry完全匹配；
- Compare Coordinator signing key仍是验签时读取的ACTIVE trust row；
- Put ACTIVATE_PENDING scope、operation、meta和event。

ACTIVATE不得由FENCE_PENDING或RECOVERY_REQUIRED scope发出。不能把Provider Receipt已签名与Floor已确认混为一谈。

### 4.4 Provider Receipt confirm

confirm Provider Receipt时：
- Floor首先解析Receipt envelope，重算canonical digest，依据Floor自己的Provider trust registry验签；
- 确认Receipt绑定原Coordinator command digest和operation的全部Provider/Tenant/scope/action/Grant/generation/FENCE/Leader/native Lease/command-time claims；
- 同时Compare当前operation、scope、meta以及Receipt signer trust row；
- 一个Txn原子推进operation确认状态、scope state、meta sequence/root和append-only event。

如Receipt signer在验签后、Txn前被撤销，trust row Compare失败；不得依据之前的验签继续确认。Signer lifecycle的历史回执规则必须沿用Round95已冻结的ACTIVE/RETIRING/REVOKED有效时间语义，不能由Etcd adapter另行放宽。

### 4.5 Trust key lifecycle

Coordinator与Provider trust key注册/轮换/退役/撤销都属于Floor authority state mutation：
- 新key注册要求目标key不存在且owner治理输入完整；
- ACTIVE → RETIRING → REVOKED只允许单向推进；
- key row更新、trust_revision、authority_revision、event_sequence和state-root必须在同一个Txn；
- command/receipt操作的签名验证快照通过Txn Compare固定；
- 已接受operation保留当时key ID、fingerprint和trust revision，不伪造后补信任记录。

## 5. Unknown outcome与精确恢复

Etcd Mutating Txn超时/transport失联一律视为 `OUTCOME_UNKNOWN`。禁止由底层driver自动发出第二笔使用新operation ID的Txn。

恢复按原Txn计划及原signed Envelope处理：
1. 使用一个只读Txn（多个exact Get位于同一分支）或等价同revision线性一致读取，读取meta、scope、operation、event及必要的trust row。
2. **确认已提交：** operation ID、command digest、scope identity/generation、预期state transition、event sequence、previous/next root和meta全部精确匹配计划结果；返回原结果，不分配新generation。
3. **确认未提交：** operation key仍不存在，scope仍等于原状态，信任key仍有效且meta可以安全重新读取；以原operation ID和同一signed Envelope重新计算当前Compare并重试。若只有其他scope的meta/root已推进，不能沿用旧meta compare，但可在验证目标scope与trust row未改变后重建相同operation的Txn。
4. **发生后续状态：** 如果operation row和immutable event已确认存在，但scope已由后续合法operation推进，则按历史operation精确读回返回原operation结果/当前scope状态，不重新执行历史状态转移。
5. **部分、冲突或无法判定：** Etcd单Txn不应产生部分写集；若读到不可能组合，视为完整性异常并隔离。禁止补写缺失key、猜测revision、重用不同digest或跳过pending状态。

若用事务failure branch执行Get，必须在同一个Txn中返回一致失败分支快照；不能把若干独立Range结果拼成一份“同一时刻”的状态。现有AuthorityStoreTxnResult和Etcd adapter已经有事务分支Get模型，但新Floor service仍需编写专用精确readback逻辑和回归测试。

## 6. Bootstrap、迁移与隔离

- 新演练namespace必须先做线性一致prefix Range，检查无既有键；随后通过meta VERSION=0 Compare原子写入初始meta/event root。Range空读只是预检，不是锁；写权限必须由Etcd RBAC限制为专用Floor service，所有合法writer都必须遵循meta sentinel compare。
- 已有SQLite Floor不能被自动转换为Etcd权威。迁移必须先建立只读一致性快照、导出scope/operation/trust rows、验证所有签名和历史链、生成确定性导入manifest，再进入独立隔离namespace。
- 迁移候选导入必须检查每个目标key VERSION=0，导入批次、checkpoint与最终publish的协议应与本Floor schema的原子语义协调；不得把半导入前缀开放给运行时Coordinator。
- 生产Unified schema-v2仍为唯一生产authority。当前Round99不创建生产namespace、不更改既有Coordinator写路径、不配置RBAC或真实集群。
- Etcd事务最大compare数、operations数和request bytes必须由部署版本/集群配置及应用预算共同确认。Round99不硬编码未经现场确认的服务端上限。单个scope mutation超过明确预算时拒绝，不把scope/operation/meta/event拆成多个Txn。

## 7. Etcd snapshot rollback与域外witness

Etcd自身的header revision、mod_revision、meta sequence和state-root都存储在同一个Etcd snapshot回滚域中。把整个集群恢复到旧snapshot会同时恢复这些字段；它们不能证明自身没有回滚。

恢复治理必须使用Etcd备份域之外的可信witness/checkpoint，最少绑定：
- 最后被治理确认的Etcd header revision；
- Provider Grant Floor event_sequence / authority_revision；
- state_root_sha256与namespace/schema identity；
- checkpoint生成者身份、签名/凭据版本、记录时间和备份/恢复事件ID。

恢复前通过线性一致读取当前Etcd meta，与域外witness比较：
- current sequence/root等于或高于witness且事件链可验证，才能进入后续逐scope审查；
- current header revision、sequence或root低于最近可信witness，必须拒绝写入并进入恢复审查；
- witness不可达、损坏、签名未知或checkpoint链不连续时，不能把Etcd内部meta当作替代信任锚。

**RPO限制必须说清楚：** 如果witness只在备份/维护窗口更新，rollback检测只能覆盖到最后已确认witness点，不能证明其后的所有提交均未丢失。若要求每个已确认Floor mutation都不能在Etcd整群snapshot rollback后消失，则需要每次mutation都纳入可恢复的外部witness两阶段提交/持久intent协议，处理witness准备成功而Etcd失败、Etcd成功而witness确认失败及双方响应丢失；这属于独立的跨系统提交协议，不能由一个普通after-commit CAS实现。本轮不宣称已解决该两阶段协议。

### 7.1 每笔写入的域外Witness确认模式（严格耐久模式）

若业务要求“已向调用方确认成功的Grant Floor变更不能因Etcd整群恢复旧snapshot而丢失”，周期性备份witness不足以给出该保证。需要把域外witness纳入每笔写入的可恢复提交协议。推荐如下严格模式；它是设计规格，不是本轮实现：

1. **Witness PREPARE：** 在独立witness CAS中登记唯一intent ID、namespace、expected previous sequence/root、拟提交的新sequence/root、operation ID/command digest、canonical event digest和协议版本。一个namespace同一时刻只允许一个PREPARED intent。
2. **Etcd PREPARE：** 通过Txn Compare当前meta仍指向previous sequence/root且pending intent为空；在meta中写入pending intent ID和expected next sequence/root。此Txn不修改scope或operation业务状态。
3. **Etcd COMMIT：** 通过Txn Compare pending intent ID、previous root和相关scope/operation/trust records；原子写入scope、operation、event、meta sequence和next root，但保留pending intent ID，阻断后续写操作。
4. **Witness COMMIT：** Witness使用intent ID和expected previous sequence执行CAS，把同一intent从PREPARED推进为COMMITTED；记录next sequence/root。只有外部witness已COMMITTED，才允许认为本次变更满足严格耐久确认条件。
5. **Etcd FINALIZE：** 再通过Txn Compare pending intent ID、已提交的next sequence/root及witness intent ID，清除pending intent并记录last witnessed sequence/root。新业务写入只有在pending intent为空且Etcd meta与witness头部一致时才可开始。
6. **调用方确认：** 只有Etcd COMMIT已精确确认、Witness COMMIT已精确确认、Etcd FINALIZE已精确确认后，才向调用方返回最终成功。任一阶段响应丢失都保持operation ID不变并执行该阶段的精确read-back；不生成新intent或新generation。

### 7.2 Witness协议未知结果与恢复矩阵

| 故障位置 | 恢复判定 | 允许动作 |
|---|---|---|
| Witness PREPARE响应未知 | 按intent ID读取witness；若精确PREPARED已存在则继续，否则仅可重放同intent CAS | 不创建第二个intent |
| Etcd PREPARE响应未知 | 线性一致读meta；pending ID精确匹配则继续，仍为空则重放同一Etcd PREPARE | pending ID为其他值时隔离 |
| Etcd COMMIT响应未知 | 同revision读取scope、operation、event和meta；完整next state/root匹配则进入Witness COMMIT，仍为完整previous state且pending ID匹配则重放同一Txn | 不接受部分结果或替代command |
| Witness COMMIT响应未知 | 按intent ID精确读witness；COMMITTED且next sequence/root匹配则继续，否则仅能重放同intent CAS | witness头部发生冲突时隔离 |
| Etcd FINALIZE响应未知 | 线性一致读meta；pending清空且last-witnessed sequence/root精确匹配则确认，否则同intent重试 | pending ID不匹配或root不一致时隔离 |
| Etcd snapshot回退 | Etcd当前sequence/root低于witness COMMITTED头部 | 禁止写入；进入受控恢复/重新FENCE流程 |

Etcd与Witness不共享物理事务，因此此协议仍不是跨系统单Txn。安全性来自：域外PREPARED intent先持久化、Etcd事务具备明确pending intent、任何阶段未知结果都可精确恢复、FINALIZE前禁止下一笔写、调用方在witness确认前不收到最终成功。它牺牲写入可用性和延迟，换取明确的跨系统确认边界。

**重要限制：**
- 如果witness只提供周期性checkpoint而非每笔COMMIT，则必须按最近一次witness COMMITTED sequence计算并公开RPO；不能宣称零已确认提交丢失。
- Witness自身必须有独立的持久化、权限隔离和备份回滚检测。把Witness文件放在Etcd snapshot相同的回滚域会使该设计失效。
- Etcd恢复旧snapshot后，PREPARED/COMMITTED intent不能仅由服务自动猜测。必须冻结旧client写入、确认所有旧Txn不再可能到达，再依据Etcd状态和witness状态执行专用恢复操作；不确定时永久保持写隔离并升级人工审查。
- 对外最终成功响应必须发生在Witness COMMITTED与Etcd FINALIZE之后。PREPARED或Etcd COMMIT但未完成witness/finalize的operation只能报告PENDING/OUTCOME_UNKNOWN，不能报告ACTIVE已确认。

## 8. 安全、运维与观测要求

- Etcd服务身份只对专属Floor前缀拥有必要KV读写权限；普通Coordinator调用身份不得直接写scope/meta/event或trust key。
- Provider/Coordinator公钥只通过审批后的owner控制面注册；command/receipt envelope自身永远不能自动建立信任。
- 日志/指标记录Txn operation ID、compare结果、Etcd header revision、scope revision、event sequence、root digest前缀和unknown-outcome恢复分类；不记录私钥、Bearer token或敏感secret。
- Watch只能做缓存失效/唤醒提示，不能代替线性一致读取或CAS；compaction/disconnect后必须重建快照。
- Store不可用、RBAC拒绝、Compare失败、Txn结果未知、witness不可达和state-root mismatch必须是不同的可观测分类；所有影响写安全的未知分类fail-closed。
- 实际Etcd server版本、max-txn-ops、max-request-bytes、maintenance/snapshot restore流程和备份/witness RPO必须通过生产部署清单与现场验证确定。

## 9. 未来实现与验收矩阵

下一实现轮次应新增Etcd-native Floor service与测试，而不是修改Round98 SQLite wrapper来模拟跨节点行为。至少覆盖：

1. 单scope FENCE/ACTIVATE正常事务、单Txn revision一致性、operation与event原子性。
2. Coordinator签名key在验签与Txn之间被撤销/轮换，Compare必须阻止旧trust snapshot继续写入。
3. Provider Receipt key并发撤销、Receipt field tamper、wrong Provider/Tenant/scope/generation/FENCE digest和applied-time chronology。
4. 两个client同scope同revision竞争，只能一个reserve成功；不同scope并发时meta/event序号仍单调。
5. Mutating Txn提交前超时、提交后响应丢失、exact readback成功、确认未提交后的同operation retry、后续operation已推进时的历史读回。
6. operation ID复用不同signed envelope、相同envelope幂等回放、event key冲突、meta root/hash链断裂。
7. trust lifecycle变更与业务mutation同时竞争；未经授权的直接Etcd写路径被RBAC拒绝。
8. namespace空前缀bootstrap竞争、生产namespace拒绝、隔离前缀互不相交、路径hash与value身份不匹配拒绝。
9. txn compare/op/byte预算边界与超限fail-closed，不拆分业务状态转移。
10. 整体Etcd snapshot恢复到旧revision时，域外witness预检拒绝服务恢复；witness不可用/签名错误/旧值回滚均fail-closed。

**验证边界：** 本设计基于仓库已有KV/Txn接口审计，不代表上述Etcd-native Floor service已实现。Round99不连接真实Etcd、不运行多节点故障演练、不配置生产RBAC/KMS/HSM、不执行SQLite迁移、候选导入、Restore、应用激活或Cutover。Round98 SQLite参考实现继续保留；含Provider Grant history的通用Restore继续fail-closed。

## 10. 外部Witness PREPARE的取消语义与并发仲裁

前述严格耐久模式还必须明确PREPARED intent如何安全终止，不能因一次线性一致读暂时未发现pending key就直接把外部intent标成ABORTED。Etcd客户端超时不等于服务端一定没有继续处理原Txn。

### 10.1 Witness PREPARE之后、Etcd PREPARE之前或响应未知

- 若Etcd PREPARE返回明确的Compare-failed结果，必须检查同Txn failure branch返回的meta：pending intent仍为空，previous sequence/root/revision与本次intent完全一致。只有这一确定失败证据才能把Witness PREPARED通过CAS转为ABORTED。
- 若Etcd PREPARE transport timeout或响应丢失，不能仅凭一次独立Range读到pending为空就取消Witness intent；原Txn仍可能在服务端提交。只能以相同intent ID、相同previous meta和相同新root重试同一个Compare/Txn，或继续精确读回，直到得到成功或明确的Compare-failed结论。
- 如果读回meta发现pending intent等于本intent，则Etcd PREPARE已提交，进入Etcd COMMIT或经严格Compare竞争的取消过程；若发现其他intent或previous root已经变化，立即隔离。

### 10.2 Etcd PREPARE成功后、业务Etcd COMMIT之前

- 可发起Etcd ABORT Txn：Compare pending intent ID、previous meta root/sequence及scope/operation仍保持预期旧状态；success分支只清除pending intent并记录abort marker，不写业务scope/operation。
- Etcd COMMIT与ABORT必须比较同一个pending intent和同一previous state。二者在Etcd里串行化，最多一个Txn成功：COMMIT先成功则ABORT compare失败并必须继续Witness COMMIT/Etcd FINALIZE；ABORT先成功则COMMIT compare失败。
- 只有ABORT Txn得到确定成功，且其完整结果精确读回后，Witness才能将对应PREPARED intent转为ABORTED。若ABORT响应未知，继续以原intent精确读回；不能新建替代intent。

### 10.3 Etcd COMMIT之后

Etcd业务COMMIT一旦确定完成，不得再把Witness intent标成ABORTED。即使Witness不可达或响应未知，也必须保持pending intent并阻断后续写；恢复后只能完成同一intent的Witness COMMIT与Etcd FINALIZE。这样不会出现业务数据已推进、witness却被取消的分叉。

## 11. Etcd整体回滚后的检测与重建不是同一能力

域外witness只保存最近可信sequence/root，可以识别Etcd当前状态低于witness，但单独一个root digest无法重建丢失的scope、operation、trust key和事件正文。恢复设计必须选择并明确一种数据重建来源：

1. **完整外部事件日志：** 在Witness COMMITTED边界之外，持久保存每个已确认event的canonical正文和签名/摘要链，并定期生成可验证快照。恢复时从受信快照加事件日志重建Etcd隔离前缀，然后逐scope重新验签和对账。
2. **受信Etcd备份 + 外部事件补齐：** Etcd snapshot只作为基线，必须验证snapshot revision/root不高于witness，并使用域外持久事件记录补齐到witness已确认sequence/root；只有完全匹配才可以重新开放。
3. **不具备重建材料：** 若只有witness sequence/root、没有可信事件正文或可验证备份，则只能检测回滚，不能声称可自动恢复。保持写隔离，通过Provider只读状态、已签Receipt和人工审批逐scope重建/重新FENCE；在重建完成前Grant Floor不可用。

任何重建路径都必须使用新隔离namespace，不能把旧snapshot中低于witness的ACTIVE Grant直接恢复为ACTIVE。Coordinator/Provider key trust状态、key lifecycle事件和pending operation也必须一并恢复；无法确认的scope进入RECOVERY_REQUIRED。

## 12. 全局Meta序列化与吞吐权衡

本设计v1让同一隔离namespace的所有写入竞争一个meta revision/event sequence/state-root，以换取简单且可验证的全序事件链。这会让不同scope的写操作也在meta Compare上串行化，形成潜在吞吐热点。Round99接受该取舍作为首个正确性基线，不据此宣称高吞吐或无限扩展。

未来如果需要分片，必须设计每分片sequence/root与上层汇总root的原子/可验证关系，明确跨分片查询和witness顺序；不得简单删除全局meta Compare而让事件顺序出现分叉。任何分片改造都应先有负载模型和并发/故障演练。

## 13. 本轮设计审查清单

- Etcd KV/Txn primitive与应用服务端口边界已明确；没有把当前SQLite DurableCoordinator业务服务称为Etcd生产实现。
- 普通Floor状态转移使用单Etcd Txn原子写scope、operation、trust audit、event和meta root。
- 签名验证依赖的trust rows在同一Txn中精确Compare，阻止验签与提交间的key lifecycle竞态。
- OUTCOME_UNKNOWN只使用原intent/operation ID和原signed envelope精确恢复；不得更换身份猜测重试。
- 外部Witness严格耐久模式已定义PREPARE、Etcd PREPARE/COMMIT、Witness COMMIT、Etcd FINALIZE及ABORT的相互竞争语义。
- 明确witness digest可以检测Etcd整群snapshot回滚，但不提供event正文，不单独具备状态重建能力。
- 明确v1全局meta的串行化性能代价；txn容量限制不允许拆分单个状态转移。
- 真实Etcd、RBAC、KMS/HSM、生产Coordinator、Provider与Grant-aware Restore均未实现或验收。