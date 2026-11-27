# Task History — 2026-11-27

## CH17-T004：etcd Gateway RBAC 与最小权限账户验证（全局第五十二轮）

- 先更新根计划和CH17专项计划，明确RBAC/mTLS验收目标、授权前缀边界、认证token安全和正式矩阵状态保护。
- Etcd3gwV3Client新增可选auth_token参数，对每个endpoint的底层HTTP session设置Authorization header；新增Fake Gateway token传播、跨endpoint和空token配置检查。
- 新增 tests/test_spare_parts_provider_authority_store_rbac_mtls_etcd_integration.py，使用临时root/reader/writer用户与角色，验证etcd原生Authentication/RBAC。
- 第一次联测发现Gateway拒绝带非空CommonName的mTLS客户端证书；采用无CN但仍由临时CA签名的客户端证书，TLS客户端证书认证和CA校验继续强制，RBAC身份通过用户名/密码认证取得token。
- 真实集成：[Run 45919206834](https://github.com/rexyll/cnc-knowledge/actions/runs/45919206834)成功；明文三成员suite 8项通过，mTLS suite 8项通过（既有mTLS 3项 + RBAC 5项）。RBAC覆盖reader只读授权prefix、writer读写授权prefix、跨prefix拒绝、无token/错误密码失败。Artifact 15163741056，SHA-256 b7e7476a08e1e9c4a77e4bb02e2b80727dd09e1baadc1b66866b6a54b72c8ee0。
- 默认质量CI：[Run 45919206886](https://github.com/rexyll/cnc-knowledge/actions/runs/45919206886)两个Job成功：515项unittest（499通过、16项opt-in live skip）、CH12 143项通过、strict knowledge lint 0 errors、结构/数据0 errors和5项既有治理warning。
- 凭据、token、CA和证书私钥仅存在runner临时目录/内存，Compose volumes及证书目录在结束时清理。token本轮显式注入，无自动刷新/续期；企业IAM、凭据轮换、审计、生产密钥托管未验证。
- ASSET-000092的30项正式场景仍为 PROPOSED_NOT_APPROVED / NOT_RUN；本轮工程冒烟测试不改变正式审批或执行状态。schema-v2仍为唯一生产权威，SQLite Coordinator未迁移，CH17-T004保持IN_PROGRESS。


## CH17-T004：etcd Gateway Token 生命周期与显式更新（全局第五十三轮）

- 实际执行时间：2026-11-27T09:06:44.620+08:00；分支：main。
- 先完成根TaskPlan与CH17专项计划，确定simple/JWT token区分、TTL实测、显式重新认证、跨endpoint更新、Watch session一致性及失败关闭范围。
- 新增SRC-000410～SRC-000412，登记etcd v3.7官方配置、认证设计和RBAC文档；确认simple token默认TTL为300秒，JWT TTL通过JWT token选项独立配置。
- Etcd3gwV3Client新增set_auth_token(token|None)，允许调用方显式替换或清除全部endpoint session的Authorization头；driver不保存用户名/密码、不自动认证/刷新。Watch复用同一session。
- Fake Gateway新增token更新/清除和认证异常不得触发endpoint failover测试。
- mTLS Compose增加simple token TTL参数；run-mtls.sh支持TTL与测试文件选择；新增独立10秒TTL live suite，覆盖旧token过期拒绝、重新认证、新token跨endpoint更新、KV读取及Watch创建握手；CI工作流增加独立短TTL job步骤。
- 更新KNOW-000061、ASSET-000092支持性证据、正文第13节、章节README、资源README和ASSET索引。ASSET-000092正式审批状态保持PROPOSED_NOT_APPROVED，执行状态保持NOT_RUN。
- 本轮live与默认CI最终验收通过，详见下方验收补记。遗留：自动刷新未实现；企业IAM、JWT密钥托管、生产撤销/轮换/审计未验证。


### 第五十三轮最终验收补记（2026-11-27T09:09:20.880+08:00）

- 代码最终验收提交：`5a8e4bf6cf7afe804866a92b5031ed54093d8860`（main）。修正token lifecycle live test在默认单元测试发现阶段导入可选requests依赖的问题，将requests导入延迟到opt-in setUpClass；默认环境不安装CH17可选依赖时仍可正常发现/跳过live suite。
- Live CI：[Run 45920726761](https://github.com/rexyll/cnc-knowledge/actions/runs/45920726761)成功；普通三节点suite 6项、mTLS/RBAC suite 8项、独立10秒simple-token生命周期suite 1项通过。过期token请求被拒绝，重新认证后的新token同步更新所有endpoint session，KV Range和Watch created握手成功。Artifact 15164208273，SHA-256 `0b66c69eb7f1ecc12e0d8bfbbf80ab0bf51de739ec31d8d2e9f3db878619e476`。runner清理证书、token和Compose volumes。
- 默认质量CI：[Run 45920726730](https://github.com/rexyll/cnc-knowledge/actions/runs/45920726730)两个Job成功：518项unittest（501 passed、17项opt-in skip），CH12 143项通过，strict knowledge lint 0 errors；结构数据统计：22章、178个Markdown文件、260条实体、240条关系、409条来源、584条内部链接。
- 第五十三轮任务验收通过。自动token刷新仍未实现；JWT私钥管理、企业IAM、生产token轮换/撤销/审计和HA认证服务未验证。ASSET-000092正式30项继续PROPOSED_NOT_APPROVED / NOT_RUN；schema-v2仍唯一生产权威，SQLite Coordinator未迁移，CH17-T004保持IN_PROGRESS。


- 最终文档头质量复验：[Run 45920942863](https://github.com/rexyll/cnc-knowledge/actions/runs/45920942863)两个Job成功：518项unittest（501 passed、17项opt-in skip），CH12 143项，strict knowledge lint 0 errors，fixture validator 0 errors/5项既有治理warning；22章、178个Markdown、260实体、240关系、409来源、584内部链接。
- 错误分类边界：当前仅确保etcd3gw通用非传输异常不触发endpoint failover；未将HTTP 401/403结构化为独立Unauthenticated/PermissionDenied类型，认证服务不可用/多数派丢失与已有token继续有效的分离故障未验证，明确留作后续任务。该限制不影响本轮simple token TTL过期/重新认证测试结论。


## CH17-T004：etcd Gateway 认证错误分类与多数派故障隔离（全局第五十四轮，2026-11-27）

- 先更新根TaskPlan和CH17专项计划，明确HTTP Gateway错误语义、认证/授权/请求/传输分类、只读failover约束及quorum loss观测范围。
- 新增SRC-000413（etcd v3.6+ Gateway错误响应格式）、SRC-000414（etcd rpctypes错误码）、SRC-000415（etcd3gw 2.7.0 HTTP错误映射实现）。
- 驱动增加Etcd3gwAuthenticationError、Etcd3gwPermissionDeniedError、Etcd3gwRequestError；从etcd3gw通用Etcd3Exception的JSON载荷中识别HTTP 401/gRPC code16、HTTP403/code7及明确的HTTP400错误密码消息；普通参数错误保持RequestError。保留原始cause，Watch HTTP建立错误也规范化。
- Failover仅针对真实连接/超时错误的只读Range/status/member调用；Authentication/PermissionDenied/Request错误不触达第二endpoint，Txn/Lease写操作仍只发送一次。
- Fake契约覆盖401/16、403/7、400错误密码、普通400、畸形JSON、cause保留、Watch 403和无错误failover；驱动测试20项。
- 新增一次性mTLS三成员认证/quorum隔离live测试：在两成员停止时，已有token的线性一致Range超时，显式重新认证请求也超时；恢复成员/多数派后，旧token再次成功Range。真实观测值AUTH_REAUTH_RESULT_DURING_QUORUM_LOSS=timeout。没有把quorum loss下认证API独立可用作为假设。
- Live [Run 45922792420](https://github.com/rexyll/cnc-knowledge/actions/runs/45922792420)成功：基础三节点/成员故障/quorum suite 8项、mTLS/RBAC suite 12项、10秒token生命周期1项、认证/quorum隔离1项通过。Artifact 15165755534，SHA-256 c3b8d8e25e91cc7bff7e3d2893a55688de0b2567836052a20cb887fd2bcc7608。
- 默认质量[Run 45922792429](https://github.com/rexyll/cnc-knowledge/actions/runs/45922792429)成功：526项unittest（504通过、22项opt-in skip），CH12 143项，strict knowledge lint 0 errors，fixture validator 0 errors/5项既有warning；22章、178 Markdown、260实体、240关系、412来源、584内部链接。
- 更新CH17技术正文第14节、章节README、资源README/ASSET索引、KNOW-000061、ASSET-000092。正式ASSET-000092 30项继续PROPOSED_NOT_APPROVED / NOT_RUN；schema-v2仍唯一生产权威，SQLite Coordinator未迁移，CH17-T004保持IN_PROGRESS。
- 遗留：自动token刷新、企业IAM/JWT密钥管理、生产token轮换/撤销/审计、网络分区、认证服务HA未验证；未验证多节点simple token状态传播的长期行为。该轮不是企业生产认证方案验收。


## CH17-T004：mTLS + RBAC 单成员故障与跨成员 Token 传播（全局第五十五轮，进行中）

- 先更新根目录 `TaskPlan.md` 与CH17专项 `TaskPlan.md`，明确真实单成员停机、有效reader token跨成员接受、只读failover和成员恢复的验证边界；继续仅在`main`分支操作。
- 新增 `tests/test_spare_parts_provider_authority_store_member_outage_auth_etcd_integration.py`：在临时三成员mTLS集群配置最小权限reader，分别记录认证后立即的token接受状态与收敛状态；停止etcd1后，通过首个endpoint为故障成员的driver验证Range transport failover，并直接访问etcd2/etcd3区分token传播与驱动切换；恢复etcd1后验证旧token恢复访问。
- 更新 `.github/workflows/ch17-etcd-live-integration.yml`，增加独立的mTLS/RBAC member-outage live阶段；测试只由 `ETCD_INTEGRATION=1` 和 `ETCD_MTLS_MEMBER_OUTAGE=1` 显式启用，默认测试发现不应启动Docker集群。
- 当前代码/计划提交：`ae791eb2eaaa48036bdcc39517ec8afb0c36f9fb`（根计划）、`f876ea6697438c8d04c92571ec670dfaa9e802a0`（章节计划）、`9f3e6298d277923a1f7810b1710eb82d13a3eb77`（live测试初版）、`200420220858da98855b102a162eb2aa594c1cce`（CI阶段）、`b5ca86322f703c3001e298858cd82965adc9d2fb`（立即/收敛状态分别记录）。
- **尚未验收：** 当前尚未取得本轮live workflow和默认质量CI的可核验运行结果；不将测试实现或workflow配置描述为测试通过。后续必须补齐运行证据、更新技术正文/README/KNOW-000061/ASSET-000092 supporting evidence和资源索引，再决定任务状态。
- **治理边界：** 本轮工程测试不改变ASSET-000092正式30项PROPOSED_NOT_APPROVED / NOT_RUN状态；schema-v2仍唯一生产权威，SQLite Coordinator未迁移，CH17-T004保持IN_PROGRESS。


### 第五十五轮首次 live 结果与修正（2026-11-27）

- 首次 live workflow： [45926442698](https://github.com/rexyll/cnc-knowledge/actions/runs/45926442698)，结论失败；失败只发生在新增测试的重启成员旧 Token 恢复断言。
- 已验证通过的部分：
  - 认证后立即 Token 观测：member1/member2/member3 均 accepted。
  - 等待传播后：三个成员均 accepted。
  - 停止 etcd1 后，Driver 从故障 endpoint 发生 transport failover，Range 成功。
  - etcd2/etcd3 直接访问旧 Token 均 HTTP 200。
  - quorum isolation、基础 mTLS、short-TTL token lifecycle 之前置阶段均成功。
- 首次失败证据：重启 etcd1 后，原 reader simple Token 返回 HTTP 401；旧 Token 恢复轮询最终得到 `http-401`。这与 Token TTL=300秒的过期时间无关（单次测试约92秒），但仍需在下一次 live run 验证 fresh re-auth 行为。
- 修正：新增重启后旧 Token 状态的明确断言；随后从健康成员 etcd2 重新认证 reader，验证 fresh token 是否在三个成员都能访问，并验证 Driver 使用 fresh token 可读取。对 HTTP 401 立即停止恢复轮询，避免无意义等待90秒。
- 质量 CI： [45926442759](https://github.com/rexyll/cnc-knowledge/actions/runs/45926442759) 在提交 `f2e6ae20a73412e48ba149ba65af20fee0e4cb2e` 成功；全库 unittest 527项（504 passed、23 skipped），CH12数值测试143项通过，strict knowledge lint 0 errors，fixture validator 0 errors / 5 warnings。fixture 仍明确标记30个正式场景NOT_RUN。
- 增强诊断：修改 `run-mtls.sh` 将每轮mTLS Compose日志保存在runner临时目录，并纳入workflow artifact，避免下一轮仅有最终断言而缺少etcd成员日志。
- 后续提交：测试修正 `022c538f`、`57cb1553`；计划补充 `042a1884`、`1406f9ad`；诊断归档 `cd8c891c`、`412f5636`。待新 live workflow 和最新 HEAD quality CI 完成后再判定任务状态。


### 第五十五轮最终验收（2026-11-27）

- 最终Live [Run 45927091505](https://github.com/rexyll/cnc-knowledge/actions/runs/45927091505)成功，五个阶段全部完成：普通三节点etcd 6项、mTLS/RBAC 12项、10秒simple-token生命周期1项、认证/quorum隔离1项、单成员故障与Token传播1项；第五十五轮专项测试1/1 PASS。
- 实测结果：reader Token签发后立即3/3成员接受，等待传播后仍3/3；停止etcd1后只读Range从故障首endpoint transport failover成功；etcd2/3直接访问旧Token均HTTP 200；重启etcd1后旧simple Token HTTP 401；从健康成员etcd2显式重新认证取得的新Token在3/3成员均accepted，Driver读取恢复成功。
- Live诊断Artifact [15167295428](https://github.com/rexyll/cnc-knowledge/actions/runs/45927091505/artifacts/15167295428)，SHA-256 2f06dbcea1b1e69bf9dfcf2666bfedff3811321aa8a8dd1474181c88b75e7aff。mTLS runner的Compose日志/状态已加入Artifact归档；临时证书、密钥、密码、token和volumes均清理。
- 最终文档head质量CI [Run 45927138505](https://github.com/rexyll/cnc-knowledge/actions/runs/45927138505)成功：527项unittest（504 passed、23 skipped），CH12 143项通过，strict knowledge lint 0 errors，fixture validator 0 errors/5项既有治理warning，22章、178 Markdown、260实体、240关系、412来源、584内部链接。
- 已同步CH17技术正文第15节、章节README、资源README、ASSET索引、KNOW-000061、ASSET-000092 supporting evidence。ASSET-000092正式场景数量仍30，审批状态PROPOSED_NOT_APPROVED，执行状态NOT_RUN，未因工程冒烟测试改变。
- 本轮状态：COMPLETED。重要限制：当前Etcd3gwV3Client不自动重新认证/刷新；旧simple Token在本次etcd v3.7.0成员重启实验中返回401，显式重新认证后新Token恢复3/3成员访问。该现象不外推为JWT或其他版本行为。schema-v2仍唯一生产权威，SQLite Coordinator业务状态机未迁移，CH17-T004仍IN_PROGRESS。


- 最终CH17专项TaskPlan状态更新为COMPLETED后，文档头质量复验 [Run 45928045386](https://github.com/rexyll/cnc-knowledge/actions/runs/45928045386) completed/success；该run针对最终任务计划head `b76b487b48c6653cc66fbdc23c1e56c69e9d3bb7`，两个必需Job均成功。KNOW-000061和ASSET-000092的latest_default_ci_run已指向该最终复验；正式矩阵30项PROPOSED_NOT_APPROVED / NOT_RUN未改变。


## CH17-T004 第五十六轮：etcd 多数派网络分区与隔离成员恢复（进行中）

- 本轮先补充根TaskPlan与CH17专项TaskPlan，定义真实网络分区的测试边界：只允许操作本CI创建的三成员Compose默认网络，不修改宿主机iptables，不触碰其他容器/网络。
- 下一步新增opt-in live test：隔离etcd1网络，分别验证etcd2/etcd3多数派的linearizable Range/Txn与etcd1少数派的失败关闭/OUTCOME_UNKNOWN；在finally恢复网络，检查三成员恢复和多数派写入收敛。
- **当前状态：** 计划已登记，live测试和CI证据尚未完成；不得标记DONE。ASSET-000092正式30项仍PROPOSED_NOT_APPROVED / NOT_RUN；schema-v2仍唯一生产权威，SQLite Coordinator未迁移。


### 第五十六轮实现进展（2026-11-27）

- 新增 `tests/test_spare_parts_provider_authority_store_network_partition_etcd_integration.py`：通过Compose项目/服务标签校验etcd1容器身份，将其从专用默认网络断开；使用容器内etcdctl验证少数派线性一致读写失败；通过etcd2/etcd3多数派执行Coordinator Store CAS事务和线性一致读回；finally重连网络并等待三成员恢复，再验证多数派提交值在etcd1可读。
- 更新 `scripts/etcd-integration/run.sh`，将新测试加入一次性三节点集成套件。工作流已有对 `tests/test_*etcd_integration.py` 与runner路径的push触发规则，无需创建分支或新增第二套workflow。
- 代码提交：测试 `00cef471bb5fb247b9def0511534ba8546d0a3fd`；runner `50c5127e6cacac0a8df833c3404bdb8213c4399d`；测试导入清理 `77c4d450582dd149a2a6984ee5286ab7d61d1d22`。
- **待验收：** 本轮live workflow与最新默认质量CI尚无可核验结果；不得将测试代码存在等同于网络分区场景通过。需检查少数派行为、finally网络恢复及全库质量门禁后，再更新知识正文/实体/资源索引并决定任务状态。


### 第五十六轮 Runner 缺陷修复（2026-11-27）

- 复核 `scripts/etcd-integration/run.sh` 时发现 quorum-loss 测试路径缺少 Bash 行续接符，导致新网络分区测试未进入循环。已在 `ca2ce5f115193a51f974e7cb18ab240e6a27e8a7` 修复，并重新检查完整for列表，四个专项测试文件现均处于同一循环中。
- 已对照 `EtcdV3CoordinatorAuthorityStore.transact()` 核实返回契约：`AuthorityStoreTxnResult.succeeded/revision` 与测试断言匹配；etcdctl默认线性一致读，隔离成员本地请求用于验证少数派无法取得Raft quorum。
- 当前最新head为 `ca2ce5f115193a51f974e7cb18ab240e6a27e8a7`。GitHub combined status查询尚未返回可核验的CI status；本轮live网络分区与默认质量门禁仍标记待验收，不宣称通过。


### 第五十六轮最终验收（2026-11-27）

- **实时集成：** [CH17 Live Run 45929955634](https://github.com/rexyll/cnc-knowledge/actions/runs/45929955634)在修复后的代码提交 `ca2ce5f115193a51f974e7cb18ab240e6a27e8a7` 上完成，Disposable three-member etcd v3.7.0 integration Job及所有后续阶段均为 success。
- **网络分区专项：** `test_minority_partition_fails_closed_and_majority_recovers` 实际执行并通过，测试耗时8.248秒。将etcd1从专用Compose网络隔离后，容器内本地etcdctl线性一致Range和Put均以非零退出码失败；etcd2/etcd3多数派通过Coordinator Store执行CAS写事务并线性一致读回；finally重新连接网络、等待三成员恢复，并从etcd1读回多数派提交的同一值。诊断Artifact [15168271744](https://github.com/rexyll/cnc-knowledge/actions/runs/45929955634/artifacts/15168271744)。
- **Runner修复：** 早期两次live run的失败原因为 `scripts/etcd-integration/run.sh` 测试文件列表缺少Bash续行符，出现line 63语法错误，并非网络分区断言失败。修复提交为 `ca2ce5f...`；修复后的Run 45929955634日志明确包含网络分区专项PASS。测试实现提交为 `00cef471bb5fb247b9def0511534ba8546d0a3fd`。
- **质量门禁：** [Knowledge Quality Run 45930090004](https://github.com/rexyll/cnc-knowledge/actions/runs/45930090004)两个必需Job均success：全库528项unittest（504 passed、24 skipped），CH12数值资源测试143项通过，strict knowledge lint 0 errors / 5项既有治理warning，结构和最终自检0 errors。合成SPAT夹具阶段报告30个包模拟PASS、failed=0，但明确 `business_test_status=NOT_RUN`、无外部连接、无写入；这不构成正式业务场景执行。
- **专项状态：** 第五十六轮工程任务标记为 `COMPLETED`。本次证明的是一次性CI Compose三成员环境中的1节点少数派隔离、2节点多数派线性一致写入以及恢复收敛；未验证Etcd3gw Driver从少数派endpoint开始时的只读failover分类，也未验证Coordinator Store对少数派Txn超时的 `OUTCOME_UNKNOWN` 语义、非对称分区、多机房或生产网络故障演练。
- **治理边界：** ASSET-000092正式30项仍为 `PROPOSED_NOT_APPROVED / NOT_RUN`；本轮只新增supporting engineering evidence，不修改审批/执行字段。schema-v2仍为唯一生产权威，SQLite Coordinator业务状态机尚未迁移；CH17-T004总状态继续 `IN_PROGRESS`。全部改动只在 `main` 分支。



### 第五十七轮任务计划：Coordinator Driver在少数派网络分区下的读取故障转移与写入未知结果核验

- **目标：** 在已通过的三成员网络分区夹具上，将验证从etcdctl/多数派Store调用推进到Etcd3gwV3Client与EtcdV3CoordinatorAuthorityStore调用层，明确少数派endpoint响应、只读failover、Txn单次发送和结果恢复语义。
- **只读路径：** 构造endpoint顺序包含隔离etcd1及健康多数派成员的客户端；分别记录单endpoint请求与多endpoint请求的实际响应类别、endpoint尝试次数和最终结果。只有连接/超时等真实transport异常允许只读Range尝试其他endpoint；HTTP认证/授权/请求错误及协议错误不得触发failover。不得先验假定少数派Gateway必然表现为TCP断连，需记录etcd v3.7.0实际返回的HTTP/gRPC错误。
- **写入路径：** 通过EtcdV3CoordinatorAuthorityStore对隔离少数派发起唯一一次CAS Txn，捕获实际异常或Txn结果；核对驱动仅发送一次、不跨endpoint重放。只有在适配层将传输不确定性分类为结果未知时，才断言 `OUTCOME_UNKNOWN`；若Gateway返回明确拒绝，则按实测协议错误记录，不将其伪装为未知提交。
- **恢复核对：** 在finally中恢复专用Compose网络并确认三成员健康；禁止重放第一次写请求。用原始key/幂等标识对多数派和恢复成员执行线性一致读取，区分“未提交”“已提交但响应丢失”和明确失败；验证不存在重复写入。
- **契约测试：** 增加Fake Gateway/记录型transport测试，证明read-only transport failover可用、认证/权限/请求错误不failover、Txn/Lease变更请求恰好发送一次、超时结果按既有存储端口契约保留。Live测试只报告真实etcd观测，不用Fake结果替代Raft证据。
- **安全和隔离：** 仅操作本CI创建的 `cnc-knowledge-etcd-itest` Compose项目与网络；容器须通过Compose project/service标签复核；不修改宿主机iptables、不接触其他容器/网络；使用唯一临时key，不输出token、密码和证书私钥；所有网络恢复必须位于finally路径。
- **验收：** Fake契约、真实三节点live测试、默认质量CI及CH12/strict lint/结构校验均通过；报告明确区分HTTP/gRPC响应、transport错误、Txn已知结果和 `OUTCOME_UNKNOWN`。本轮仍为工程supporting evidence，不批准或执行ASSET-000092正式30项。
