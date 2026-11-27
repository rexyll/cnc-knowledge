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


## CH17-T004 第五十七轮最终验收（2026-11-27）

- Live [Run 45931474359](https://github.com/rexyll/cnc-knowledge/actions/runs/45931474359)整个Disposable three-member etcd v3.7.0 integration Job成功；网络分区测试文件2项测试通过（8.670秒）。观察JSON：read endpoint attempts=`127.0.0.1:23791 -> 127.0.0.1:23792`，linearizable read成功；Txn endpoint只调用`127.0.0.1:23791`一次，结果`OUTCOME_UNKNOWN/ConnectionError`；恢复后Txn key线性一致读回为`not-committed`。
- 该结果证明只读Range在隔离首endpoint后触达健康多数派；Txn未跨endpoint重试；初始未知结果经恢复后读回确认为本次未提交。测试未重放Txn，也未模拟已提交后响应丢失的时间窗。
- Live workflow后续mTLS、short TTL token、auth/quorum isolation、mTLS RBAC member outage/token propagation、诊断采集、Compose/volumes清理与Artifact上传全部成功。Artifact [15168243294](https://github.com/rexyll/cnc-knowledge/actions/runs/45931474359)。
- 默认质量[Run 45931474322](https://github.com/rexyll/cnc-knowledge/actions/runs/45931474322)两个Job成功：529 unittest（504 passed、25 skipped），CH12 143项，strict lint 0 errors/5 warnings，结构/最终自检0 errors。30个SPAT包模拟通过但business_test_status仍NOT_RUN，无外部连接或写入。
- **状态：** 第五十七轮COMPLETED；CH17-T004总任务保持IN_PROGRESS。ASSET-000092正式30项仍PROPOSED_NOT_APPROVED / NOT_RUN；schema-v2唯一生产权威，SQLite Coordinator业务状态机未迁移。



### 第五十八轮任务计划：Lease续租失败、租约到期与Leader Fencing的网络分区验证

- **目标：** 基于第五十六/五十七轮三成员网络分区夹具，验证当持有Lease的协调器只能访问少数派时，KeepAlive不能被误认为成功；在多数派上观察租约到期、authority key删除及新Leader fencing epoch推进。
- **初始状态：** 在多数派建立唯一短TTL Lease，将Leader/authority记录绑定Lease，并记录初始epoch、key和revision；所有key均用唯一临时前缀，测试开始前线性一致读回确认初始状态。
- **分区操作：** 按Compose project/service labels确认etcd1身份，仅从专用测试网络断开etcd1。把Etcd3gwV3Client固定到隔离成员，执行LeaseKeepAlive；记录真实HTTP/Gateway/transport错误和调用结果。不得因请求未抛异常或本地定时器尚未到期而推断续租成功；Store报告Unavailable时，协调器必须按fail-closed语义停止依赖该Lease的leader授权。
- **多数派观察：** 从etcd2/etcd3使用线性一致读取/LeaseTimeToLive观察TTL；不对少数派重复KeepAlive，不以健康endpoint替少数派客户端代发。等候租约自然到期，确认lease-bound authority key消失；用CAS建立更高epoch的新Leader记录，并验证旧epoch的授权写入被拒绝。
- **恢复核对：** finally重新连接etcd1并等待三成员恢复；线性一致确认旧Lease/key不会复活，旧epoch CAS仍失败，新epoch值一致。测试不重放第一次KeepAlive或Leadership Txn。
- **契约测试：** Fake覆盖KeepAlive transport timeout、Gateway明确拒绝、Lease状态到期、authority fail-closed及fencing CAS拒绝；写入/续租请求保持单次发送。准确区分已确认续租、明确失败和结果未知。
- **安全边界：** 仅操作本CI一次性Compose项目/网络/容器；不修改宿主机iptables，不触碰其他容器/网络；所有恢复置于finally；临时凭据和key不得输出；不将本轮工程冒烟测试视作生产Leader HA验收。
- **验收：** live三成员Lease分区场景、Fake契约、全库质量CI、CH12、strict lint和结构校验通过；日志包含隔离endpoint结果、quorum侧TTL/删除时序、新epoch与旧epoch fencing结果。ASSET-000092正式30项仍不得自动批准或标记执行。


### 第五十八轮最终验收结果（2026-11-27）

- Live [Run 45933111643](https://github.com/rexyll/cnc-knowledge/actions/runs/45933111643)完整Job success；新增 `test_minority_cannot_renew_lease_majority_expires_and_fences_old_epoch` 1/1 PASS，耗时14.526秒。一次性三成员etcd v3.7.0环境中，初始Lease TTL=8秒，leader authority key绑定该Lease，epoch=1。
- 网络断开etcd1后，KeepAlive客户端配置全部三个endpoint（23791/23792/23793），但实际只向隔离的首endpoint `127.0.0.1:23791` 发送一次请求；Store返回 `AuthorityStoreUnavailableError`，没有向健康多数派endpoint自动切换。多数派的LeaseTimeToLive从7秒下降至5秒，证明这次失败续租没有重置租约。
- Lease自然到期后，TTL接口报告 `ttl=-1`；测试继续通过多数派线性一致Range等待leader authority key真正删除，epoch key仍保持1。新Leader通过单个CAS事务创建新的Lease-bound leader key并将epoch推进到2。
- 旧Leader以owner/epoch=1提交fencing保护的写事务，比较失败（`succeeded=false`），受保护key没有出现；新Leader以epoch=2执行写入成功。恢复etcd1网络后，在该成员上核实leader owner、新Lease ID、epoch=2及新epoch写入均已收敛，旧fenced key不存在。
- 同一live run中网络分区文件2项测试也通过（只读Range failover、Txn单次发送/OUTCOME_UNKNOWN及基础多数派恢复），mTLS、短TTL Token、auth/quorum隔离、RBAC成员故障与Token传播阶段全部成功。诊断Artifact [15169352034](https://github.com/rexyll/cnc-knowledge/actions/runs/45933111643/artifacts/15169352034)。
- 默认质量 [Run 45933111606](https://github.com/rexyll/cnc-knowledge/actions/runs/45933111606)两个Job均success：全库530项unittest（504 passed、26 skipped），CH12 143项通过，strict knowledge lint 0 errors / 5项既有warning，结构/最终自检0 errors。SPAT 30包仅离线模拟，`business_test_status=NOT_RUN`、无外部连接、无写入。
- **状态：** 第五十八轮工程任务 `COMPLETED`。该证据只证明一次性etcd v3.7.0/etcd3gw 2.7.0集成夹具中的Lease KeepAlive失败关闭、自然过期、authority key删除与KV CAS fencing；不等同于当前SQLite业务Coordinator已迁移或生产Leader HA验收。CH17-T004总任务仍`IN_PROGRESS`，schema-v2仍唯一生产权威。


### 第五十九轮任务计划：少数派分区下LeaseRevoke未知结果与恢复后核对

- **目标：** 验证变更型LeaseRevoke在隔离首endpoint上的单次发送和结果未知语义，确认恢复后通过LeaseTimeToLive与lease-bound authority key状态核对结果；禁止自动跨endpoint重试。
- **初始状态：** 在健康多数派创建唯一短TTL Lease，并将唯一authority key绑定该Lease；记录lease ID、TTL、key revision及三成员状态。
- **分区操作：** 仅从专用CI Compose网络断开etcd1，客户端配置全部三个endpoint且将etcd1置于首位；通过记录型HTTP post捕捉LeaseRevoke真实调用路径。验证请求只触达首endpoint，不会自动转向健康多数派；记录Store返回的OutcomeUnknown/Unavailable或其他实际Gateway分类，不预设错误类型。
- **恢复核对：** finally恢复网络并确认三成员quorum；不重放首次Revoke。通过健康多数派的LeaseTimeToLive和线性一致Range判断原Lease是否仍存在、authority key是否仍绑定；区分“撤销已完成但响应丢失”与“撤销未提交”。如仍存在，只有完成首次结果读取记录后，才由测试显式发起一次新的多数派Revoke清理并验证key删除。
- **契约测试：** 对LeaseGrant/KeepAlive/Revoke增加记录型Fake Gateway断言：每个变更RPC至多一次endpoint dispatch；连接响应丢失映射遵循Store端口的OUTCOME_UNKNOWN/Unavailable定义；HTTP认证、权限与请求错误不伪装为传输超时。
- **安全边界：** 仅操作本CI一次性Compose项目/网络及通过标签校验的容器；不修改宿主机iptables，不接触其他容器；所有网络恢复在finally路径，临时key唯一，日志不得包含凭据。
- **验收：** Live三节点分区测试、Fake契约、全库质量CI、CH12、strict lint与结构校验通过；报告需记录endpoint attempts、首次Revoke结果分类、恢复后Lease/key状态及显式清理动作。ASSET-000092正式30项仍不得自动批准或标记执行。


## 第五十九轮：少数派分区下LeaseRevoke未知结果与恢复后核对（2026-11-27）


### 第五十九轮最终验收结果（2026-11-27）

- **实现提交：** `c8c4d404004ed23eee12feabd31294e53b49ac81`；新增 `tests/test_spare_parts_provider_authority_store_lease_revoke_partition_etcd_integration.py`，并扩展 `tests/test_spare_parts_provider_etcd3gw_driver.py` 中的Fake契约测试。集成Runner续行修复提交：`9c1a91a6c73cb6acb8f9278296667f0c07fa2d44`。
- **Fake契约：** 新增两项测试，分别验证LeaseGrant/KeepAlive/Revoke的传输失败至多派发到一个endpoint，以及Gateway认证、权限和普通请求错误保持其明确类型、不作为传输错误处理。驱动测试方法总数更新为22。
- **Live结果：** [Run 45936468822](https://github.com/rexyll/cnc-knowledge/actions/runs/45936468822)整体Job success。新增 `test_minority_lease_revoke_is_single_dispatch_and_reconciled_after_recovery` 1/1 PASS。测试在健康多数派创建TTL=60秒Lease，将唯一authority key绑定Lease并记录key revision=16；隔离etcd1后，三endpoint客户端的首次Revoke只向 `http://127.0.0.1:23791` 派发一次，Store返回 `AuthorityStoreOutcomeUnknownError`，没有自动failover或重放。
- **恢复核对：** 网络恢复并确认三成员quorum后，测试在线性一致读回中首先确认原authority key仍存在、value/lease ID/revision未变化且Lease TTL仍为正，因此本次首次Revoke被判定为 `revoke-not-committed`。只有记录该结果后，测试才向健康多数派显式发送一次新的Revoke清理；authority key随后删除，revision从16变为17，LeaseTimeToLive最终报告 `ttl=-1`。结构化日志的 `cleanup_action` 为 `one-explicit-revoke-through-healthy-majority`。
- **整体Live阶段：** 普通etcd集成、mTLS、短TTL Token生命周期、auth/quorum隔离、mTLS/RBAC成员故障与Token传播全部成功；诊断采集、Compose容器/volumes清理和Artifact上传全部成功。诊断Artifact [15170653184](https://github.com/rexyll/cnc-knowledge/actions/runs/45936468822/artifacts/15170653184)。
- **默认质量：** [Run 45936468828](https://github.com/rexyll/cnc-knowledge/actions/runs/45936468828)两个Job均success：全库533项unittest（506 passed、27 skipped）；CH12 143项通过；strict knowledge lint 0 errors、5项既有warning；结构校验0 errors。SPAT 30包仅离线模拟校验，`business_test_status=NOT_RUN`、`external_connections=NO`、`writes=NO`。
- **失败修复记录：** 初始代码提交触发的Live Run 45936376325在测试启动前因Runner测试文件列表缺少Bash续行符而失败，未执行场景；CI已清理一次性容器/volumes。修复Runner后重新执行的Run 45936468822成功。该首次语法失败不计作场景测试失败。
- **解释边界：** 本轮验证的是隔离首endpoint下Revoke只发送一次、结果未知时不重试、恢复后能区分本次未提交并显式清理。没有精确注入“etcd已提交Revoke但Gateway响应在返回前丢失”的窗口；该实验不是生产HA或正式业务验收。ASSET-000092仍30项、`PROPOSED_NOT_APPROVED / NOT_RUN`；schema-v2仍是唯一生产权威，SQLite Coordinator业务状态机未迁移，CH17-T004总体保持`IN_PROGRESS`。


### 第六十轮任务计划：Lease-bound authority key Watch删除事件与断流恢复核对

- **目标：** 验证Lease Revoke触发的authority key DELETE事件是否携带完整Watch响应包络和`prev_kv`租约信息，并验证Watch中途断流后通过线性一致快照与`R+1`重建不会遗漏或重复业务删除。
- **正常事件路径：** 在三成员一次性CI集群创建唯一Lease并绑定leader authority key；先执行线性一致Range取得revision R，再从R+1建立Watch，验证created握手、LeaseRevoke后唯一DELETE事件、`prev_kv`中的原value/lease ID/mod_revision，以及事件header revision严格大于R。
- **断流与恢复路径：** 单独覆盖Watch连接建立后stream断开；确认已建立的Watch不会被驱动静默自动重放或切换。恢复quorum后执行线性一致Range快照，记录新revision及key实际存在/不存在，再从快照revision+1恢复Watch；对断流期间已发生的删除以快照结果为准，不重复执行Revoke。
- **边界与契约：** 保持当前HTTP Gateway单向server-stream能力边界；不声称支持双向WatchProgress/WatchCancel。验证Watch iterator关闭、恢复游标、DELETE/prev_kv解码和不自动重放；不将观察到的Watch事件作为独立于KV线性一致状态的权威。
- **安全边界：** 只操作一次性Compose项目/网络及标签验证后的容器；不修改宿主机iptables、不触碰其他容器；finally恢复网络并等待三成员quorum；使用唯一临时key，不输出token/凭据。
- **验收：** Fake Watch契约、三成员Live正常删除事件与断流恢复、全库质量CI、CH12、strict lint及结构校验通过。该测试仍属engineering supporting evidence，不改变ASSET-000092正式30项矩阵审批/执行状态。


## 第六十轮：Lease-bound authority key Watch删除事件与断流恢复（2026-11-27）


### 第六十轮最终验收结果（2026-11-27）

- **实现提交：** `112119448212636698280af5a63313a50a4a3a71`，新增 `tests/test_spare_parts_provider_authority_store_lease_watch_recovery_etcd_integration.py`，包含2项真实集成测试，并注册到 `scripts/etcd-integration/run.sh`。Runner续行修复提交为 `ac1d296e45e19715850c5aee5258ddd6b3a7e617`。
- **Lease Revoke DELETE事件：** [Live Run 45938253313](https://github.com/rexyll/cnc-knowledge/actions/runs/45938253313) 中 `test_lease_revoke_emits_delete_with_previous_lease_bound_kv` 1/1 PASS。线性一致Range基线revision=18，Watch从revision=19建立；Revoke后收到唯一DELETE事件，event/header revision均为19。`prev_kv.mod_revision=18`，`prev_kv.lease_id`与原Lease一致；DELETE当前KV无entry，后续线性一致Range在revision 19确认key不存在。
- **已建立Watch断流与快照重建：** 同一Live Run中 `test_watch_disconnect_rebuilds_from_linearizable_snapshot_plus_one` 1/1 PASS。Watch首次只向etcd1 `http://127.0.0.1:23791`发送建立请求；停止通过Compose project/service标签验证的etcd1容器后，已建立流显式返回 `AuthorityStoreUnavailableError`，未自动切换或重放。随后经etcd2/etcd3多数派撤销Lease，删除revision=21。重启etcd1并确认三成员恢复后，线性一致快照revision=21、key不存在；从revision=22恢复Watch，随后提交的首个新事件为PUT、revision=22，证明旧DELETE没有被重放，恢复后的新Watch正常工作。
- **Live全流程：** Run 45938253313整体success；普通etcd集成（含本轮2项Watch测试）、mTLS、短TTL Token、auth/quorum隔离、mTLS/RBAC成员故障和Token传播阶段全部success；诊断采集、Compose容器/volumes清理及Artifact上传均success。诊断Artifact [15171088378](https://github.com/rexyll/cnc-knowledge/actions/runs/45938253313/artifacts/15171088378)。
- **默认质量门禁：** [Quality Run 45938253249](https://github.com/rexyll/cnc-knowledge/actions/runs/45938253249)两个Job success：全库535项unittest（506 passed、29 skipped）；CH12 143项通过；strict knowledge lint 0 errors、5项既有warning；结构校验0 errors。SPAT 30包仅离线模拟，`business_test_status=NOT_RUN`、`external_connections=NO`、`writes=NO`。
- **失败修复记录：** 初始实现提交触发的Live Run 45938226096因Runner测试文件列表缺少Bash续行符在启动测试前失败，未产生测试场景结论。修复提交 `ac1d296e45e19715850c5aee5258ddd6b3a7e617` 后的Run 45938253313完整通过。
- **解释边界：** 证据仅代表一次性etcd v3.7.0 / etcd3gw 2.7.0三节点CI环境。Watch只提供单向HTTP server-streaming能力，不包含双向WatchProgress/WatchCancel；Watch不是权威状态源，断流后仍必须线性一致Range快照并从R+1恢复。该工程测试不等于生产HA或正式矩阵验收。ASSET-000092仍30项、`PROPOSED_NOT_APPROVED / NOT_RUN`；schema-v2仍是唯一生产权威，SQLite Coordinator业务状态机未迁移，CH17-T004总体保持`IN_PROGRESS`。

### 第六十一轮任务计划：Watch compaction取消、游标失效与快照恢复

- **目标：** 在一次性三节点集群验证Watch请求的起始revision已被etcd compaction覆盖时，服务端返回canceled/compact_revision；上层不得沿失效游标继续消费，必须通过线性一致Range重建快照，再以快照revision+1开启新Watch。
- **压缩路径：** 创建唯一测试key并记录早期revision R；产生后续修订，使用项目标签验证后的etcd容器内etcdctl仅对本次一次性集群执行指定revision的compact；然后尝试从被压缩的旧revision建立Watch，检查created/canceled、compact_revision和cancel_reason字段，并确认没有返回伪造的历史事件。
- **恢复路径：** 读取取消Watch后的线性一致快照，记录snapshot revision、key value/mod_revision；从snapshot revision+1重新Watch；提交唯一新PUT/DELETE marker，验证恢复后仅收到新修订事件，不重放快照之前的事件。
- **契约及安全边界：** 延续Fake Watch对canceled/compact_revision/resume_revision语义的检查；不实现或声称支持双向WatchProgress/WatchCancel。etcdctl只在一次性Compose项目和标签确认的服务容器内执行，不修改宿主机iptables、不接触其他容器；唯一临时key，finally关闭流、清理key/Lease，Runner最后销毁容器和volumes。
- **验收：** Live compaction/canceled响应、线性一致快照和R+1恢复通过；全库质量CI、CH12、strict lint与结构校验通过。仍是supporting engineering evidence，不改变ASSET-000092正式30项矩阵审批/执行状态。

## 第六十一轮：Watch compaction取消与快照恢复（2026-11-27）

- **任务目标：** 验证旧Watch游标被etcd compaction覆盖后，服务端canceled/compact_revision响应、旧resume cursor失效，以及线性一致快照后从R+1恢复。
- **实现提交：** `ffc3421c599720fdf3e1312ed5060fb1fa6d301b`；修复created握手帧处理 `10b0b6f8ed5cbb174afc5e8a2e5bb42cc37a2aca`；调整压缩目标为旧游标之后的revision `6757927ec90ef8e1d060af07e5da41bf9c7d8af4`；兼容无Header取消帧 `ce04581989f1b703a2cbb05445d0b3db114e451d`；保留可选cancel_reason为空的行为 `1afc40393fc9cfa0d901ab385882d0807a657b0f`。均在`main`快进提交。
- **Live：** [Run 45940105118](https://github.com/rexyll/cnc-knowledge/actions/runs/45940105118)整体success，新增compaction恢复用例1/1 PASS；所有普通etcd、mTLS、短TTL Token、auth/quorum、RBAC成员故障阶段和清理步骤均success。诊断Artifact [15172995164](https://github.com/rexyll/cnc-knowledge/actions/runs/45940105118/artifacts/15172995164)，SHA-256 `01ee63687fc67194471e55246412854604314700c2d160870bbff17ca77bed76`。
- **关键观察：** old watch revision=24；etcdctl compact revision=25；服务端先发送created握手，再发送`canceled=true`、`compact_revision=25`、0 events，`resume_revision=None`，cancel_reason为空。线性一致快照revision/mod_revision=25且value为最新值；从revision=26恢复后首个PUT事件revision=26，`prev_kv`值与快照一致，旧事件未重放。
- **Quality：** [Run 45940105074](https://github.com/rexyll/cnc-knowledge/actions/runs/45940105074)success：537 unittest（507 passed、30 skipped），CH12 143项，strict lint 0 errors/5既有warnings，结构校验0 errors；SPAT 30项仅离线模拟，business_test_status=NOT_RUN。
- **工程边界：** Gateway取消帧可能不含Header/可选cancel_reason；仅canceled终止帧允许无Header，缺失revision规范化为0，普通帧仍严格校验。Watch仍是单向server stream，不支持双向WatchProgress/WatchCancel；Watch不是权威状态源。只操作标签核验的一次性etcd容器；Compose容器/volumes清理成功，未改宿主机iptables或其他容器。
- **治理状态：** 以上均为一次性CI supporting evidence；ASSET-000092保持30项、`PROPOSED_NOT_APPROVED / NOT_RUN`；schema-v2仍是唯一生产权威；SQLite Coordinator业务状态机未迁移；CH17-T004总体`IN_PROGRESS`。

## 第六十二轮：Watch progress notification与无事件响应游标语义（2026-11-27）

- **任务目标：** 验证WatchCreate的`progress_notify=true`是否会返回无事件的进度响应，并明确进度revision与线性一致Range快照的职责边界。
- **实现提交：** `7e288e8af31207d32d872b4e3a1d58471611b809`（新增Fake Gateway与Live进度通知测试，并将一次性Compose etcd1的`--watch-progress-notify-interval`设为1s）；`869c38d03c0755458fb52cdbcdb4bac08a708c83`（允许Gateway返回零值watch_id，不假设ID必须大于0）。均快进提交至`main`。
- **Live：** [Run 45944091683](https://github.com/rexyll/cnc-knowledge/actions/runs/45944091683)整体success。compaction/快照恢复和progress通知两个Watch专项均通过；后续mTLS、短TTL Token、auth/quorum、RBAC成员故障、诊断采集、Compose清理及Artifact上传均success。诊断Artifact [15174705258](https://github.com/rexyll/cnc-knowledge/actions/runs/45944091683/artifacts/15174705258)，SHA-256 `52fd565b6eeb804b4ad07e9071c588acf4368ed098e36de6f1d20ca9f1d2f88a`。
- **进度帧实测：** Watch连接一次性集群etcd1 `http://127.0.0.1:23791`。created响应header revision=28、watch_id=0；对被Watch key以外的marker执行写入，marker revision=29。随后收到`is_progress=true`的空响应：watch_id=0、header revision=29、events数量=0、resume_revision=30。created与progress两个响应的watch_id一致；本次HTTP Gateway将该默认ID呈现为0，因此测试不再假设watch_id必须为正数。
- **Range对照：** 随后的线性一致Range快照revision=29，确认被Watch key仍存在且值/mod_revision未变化；本次snapshot revision与progress header revision相等。空进度帧本身不携带KV内容，不能用它判断key值或存在性。该实测仅在健康三节点场景；官方etcd说明progress header revision来自Watch所连接的本地节点，在网络分区时可能低于quorum读revision，故不能将进度帧当作权威快照。参考[etcd v3.7 Watch API](https://etcd.io/docs/v3.7/learning/api/)、[etcd v3.7交互指南的Watch progress说明](https://etcd.io/docs/v3.7/dev-guide/interacting_v3/)及[配置选项](https://etcd.io/docs/v3.7/op-guide/configuration/)。
- **默认质量门禁：** [Quality Run 45944091695](https://github.com/rexyll/cnc-knowledge/actions/runs/45944091695)两个Job success：539 unittest（508 passed、31 skipped）；CH12数值测试143项通过；strict knowledge lint 0 errors、5项既有warning；结构/data检查0 errors。SPAT 30包仅离线模拟，`business_test_status=NOT_RUN`、`external_connections=NO`、`writes=NO`。
- **失败修复记录：** 首次Live Run 45943942778因测试误假设服务端`watch_id>0`而在新用例断言失败，其他既有阶段在该断言前均通过，诊断Artifact上传和一次性Compose清理成功。修复后Run 45944091683完整通过。该初始断言失败不计作Watch行为通过。
- **能力边界：** 本轮验证的是WatchCreate `progress_notify=true`产生的周期性通知；不代表驱动实现双向`WatchProgress`请求或`WatchCancel`。显式双向请求仍不支持；Watch仍是变更提示，权威状态须由线性一致Range确认。以上仅为一次性etcd v3.7.0 / etcd3gw 2.7.0 CI supporting evidence，不是生产HA或业务Coordinator迁移验收。
- **治理状态：** ASSET-000092仍30项、`PROPOSED_NOT_APPROVED / NOT_RUN`；schema-v2仍为唯一生产权威，SQLite Coordinator业务状态机尚未迁移，CH17-T004保持`IN_PROGRESS`。

## 第六十三轮：少数派成员上的Watch progress revision滞后（2026-11-27）

- **任务目标：** 在一次性三节点etcd环境中保持Watch流连接在隔离的单成员上，同时由剩余多数派提交写入；对照本地Progress Notification header revision与quorum线性一致Range revision，并在网络恢复后通过快照+1重建Watch。
- **实现提交：** `c3d3fb6e91e5067da7391ea0274ba51b73bd1d4a`新增Live分区/恢复测试；`6fb4d77e269a01a23f542caf505259d9a362c34c`加入Runner；`b4f23d87619bb4046a3cf2ce37a049d71e175816`修复Runner列表的Bash续行符；`6109e50d4657e711311179178061abb5b4868858`确保Watch start revision已被隔离成员应用；`ed191dca2157e536a585036f28b60dcdb53c2a1d`在恢复时增加最多30秒的只读线性一致Range重试。全部提交到`main`，未创建分支。
- **分区搭建：** 测试在一次性etcd v3.7.0三节点Compose集群中，为标签核验后的etcd1临时增加专用bridge网络，保证Watch连接仍可到达etcd1；再仅将etcd1从Compose peer网络断开，etcd2/etcd3继续构成多数派。恢复时先重新连接peer网络并等待三成员恢复；最终清理临时网络、容器和volumes。没有改宿主机iptables，没有触碰其他容器。
- **关键revision结果：** 被监视key初始PUT revision=31；独立baseline marker revision=32，多数派和etcd1线性一致读取均确认已应用revision=32；Watch从32建立，watch_id=0。隔离etcd1后，多数派连续写入revision=[33,34,35]，quorum线性一致Range revision=35。etcd1连续两次收到空Progress Notification，header revision均为32、events=0、watch_id=0；没有观察到隔离期间的KV事件。日志显示`quorum_revision_exceeds_isolated_progress=true`。
- **恢复结果：** 多数派线性一致快照revision=35；重加入成员经有界只读重试后，线性一致Range也达到revision=35且值匹配。丢弃隔离期间旧Watch游标，从revision=36（snapshot+1）恢复；随后提交的revision=36新PUT只收到一次，prev_kv与快照值一致；下一响应为空Progress帧。观测标志`no_partition_write_replayed=true`。专项测试1/1 PASS，运行6.213秒。
- **Live：** [Run 45946092810](https://github.com/rexyll/cnc-knowledge/actions/runs/45946092810)整体success；普通三节点etcd Watch/compaction/lease类集成、mTLS、短TTL Token、auth/quorum隔离、mTLS RBAC成员故障/Token传播全部success；诊断采集、Compose容器/volumes清理、Artifact上传及post-job cleanup全部success。诊断Artifact [15174961822](https://github.com/rexyll/cnc-knowledge/actions/runs/45946092810/artifacts/15174961822)，SHA-256 `5d72bea9eeb46ea6d9a26b90204f5c350797a393c774852b64792520af6a5364`。
- **Quality：** [Run 45946092822](https://github.com/rexyll/cnc-knowledge/actions/runs/45946092822)两个Job均success：全库540项unittest（32 skipped）；CH12数值资源测试143项通过；strict knowledge lint通过；结构/data校验0 errors（22章节、178 Markdown文件、260实体、240关系、412来源记录）。
- **实验过程中的修正：** 第一版Watch start revision比少数派成员本地已应用revision高一版，watcher尚未同步导致没有progress帧；通过写入独立marker revision=32并由etcd1线性一致读取后再从32建立Watch修复。随后曾因网络刚恢复即执行Range遇到临时不可用；改为只读、有界重试后完整通过。两次中间失败均不作为通过证据。
- **协议解释：** etcd v3.7 Watch进度响应revision反映Watch连接的本地成员进度；成员处于少数派时该revision可以落后于quorum线性一致Range。Progress帧不包含KV状态，因此不能作为权威快照；恢复流程应使用线性一致Range快照并从R+1重建Watch。参考[etcd v3.7 Watch progress说明](https://etcd.io/docs/v3.7/dev-guide/interacting_v3/)及[etcd v3.7 API](https://etcd.io/docs/v3.7/learning/api/)。
- **能力与治理边界：** 本轮验证WatchCreate的周期性`progress_notify=true`通知；未实现或宣称支持双向`WatchProgress`/`WatchCancel`。本结果仅是一次性etcd v3.7.0 / etcd3gw 2.7.0 CI supporting engineering evidence，不代表生产HA或业务Coordinator迁移验收。ASSET-000092正式30项仍`PROPOSED_NOT_APPROVED / NOT_RUN`；schema-v2仍是唯一生产权威；SQLite Coordinator业务状态机未迁移；CH17-T004整体保持`IN_PROGRESS`。


## 第六十四轮：少数派Watch期间多数派Compaction与旧游标恢复（2026-11-27）

- **任务目标：** 在三节点一次性etcd集群中保持Watch连接于被隔离成员，令多数派产生新revision并Compaction旧历史；恢复后验证旧游标被服务端取消，客户端以线性一致快照和snapshot+1安全重建。
- **实现提交：** `cd8730a0ec557722eb55b5c594255dafb209d074`新增Compaction场景；`8bf193dd2b95daa153a9244895fac92067be4eee`把分区期间的写入改到Watch范围外的marker key；`3eaff31fe24f9286bb57deda7116924ee60fb577`配置固定peer IP；`83d3a9f0b8ffecd1f3e7281341542e392d3a48cc`、`4949c7cc22480afda07989bee0ecf94e3cc60fa8`、`abca3f827535d0e8c2b5cf8651bb21ff79f67362`、`3380e204849ddd8cdb760afd4866e67cd51c63b6`修复分区恢复的静态IP重连；`bda3f122c407475b02d2e7980f7f98e6f1679004`补齐Watch恢复finally；`3007cf17576eb82d033c2c018e33ea9d3b549520`最终修正正常恢复步骤并使用quorum快照重建旧游标和新Watch。均在`main`提交，没有创建分支。
- **环境与隔离：** 一次性etcd v3.7.0 / etcd3gw 2.7.0三节点Compose集群，专用peer subnet `172.29.64.0/24`；成员peer IP分别为`.11/.12/.13`。为etcd1增加临时带project/purpose标签的访问bridge网络，保持Watch HTTP流可访问；只断开etcd1的Compose peer网络，etcd2/etcd3保持quorum。恢复时显式指定`docker network connect --ip 172.29.64.11`，并断言静态地址恢复。未修改宿主机iptables或其他容器/网络。
- **版本时序：** 旧Watch从revision=39建立；多数派对未被Watch的独立marker key写入revision=[40,41]，被Watch leader key未变化；etcd2执行`etcdctl compact 41`成功。etcd1网络恢复后，旧HTTP流由客户端关闭；通过健康多数派线性一致Range取得snapshot revision=41。
- **取消控制帧：** 在健康多数派端从旧start_revision=39重新创建Watch，收到`canceled=true`、`compact_revision=41`、events=0、`resume_revision=None`。`cancel_reason`为空字符串，是Gateway可选字段缺失/空值的行为，不能以其有无作为取消判断。随后从snapshot+1=42建立恢复Watch。
- **续接结果：** 之后提交leader key的新PUT revision=42；恢复Watch只投递1条事件，revision=42、`prev_kv`等于snapshot中的初始值、resume_revision=43。日志观测`no_compacted_event_replayed_after_snapshot=true`与`post_snapshot_event_delivered_once=true`，即旧revision 40–41未重放且快照后的revision 42仅一次投递。测试文件两项测试共运行7.292秒并通过。
- **Live：** [Run 45949089875](https://github.com/rexyll/cnc-knowledge/actions/runs/45949089875)整体success。Disposable three-member etcd integration、mTLS、短TTL Token、auth/quorum隔离、mTLS RBAC成员故障/Token传播、诊断采集、容器/volumes清理、Artifact上传和post-job cleanup全部success。Artifact [15176311979](https://github.com/rexyll/cnc-knowledge/actions/runs/45949089875/artifacts/15176311979)，SHA-256 `617e83d2321f82be8396e80bf362638100672d4a32f80ceea4e96b1ddd94ad69`。
- **Quality：** [Run 45949089930](https://github.com/rexyll/cnc-knowledge/actions/runs/45949089930)两个Job success：Knowledge structure and data quality、CH12 numerical resource tests。
- **失败修复说明：** 曾出现Docker断开默认网络后重连未恢复静态peer IP、第六十四轮正常流程漏掉主动重连、以及将成员本地ReadIndex恢复当成快照前置条件等问题。最终实现改为明确恢复peer网络、核验静态IP、通过健康多数派获取权威快照并进行旧游标拒绝/新Watch续接；最终Live完整通过。不能由此推断etcd1刚重连就立即具备ReadIndex能力，也不能声称原Watch流必然自动返回Compaction取消帧。
- **治理状态：** 这是一次性CI supporting evidence，不等于生产HA、生产网络分区演练或业务Coordinator迁移验收。Watch仍不支持双向`WatchProgress`/`WatchCancel`。ASSET-000092仍30项、`PROPOSED_NOT_APPROVED / NOT_RUN`；schema-v2仍是唯一生产权威；SQLite Coordinator业务状态机未迁移；CH17-T004仍`IN_PROGRESS`。

## 第六十五轮：Watch长时间运行、周期性Compaction与客户端状态重建（2026-11-27）

- **目标：** 从单次Compaction恢复验证扩展到单次Live会话内持续事件消费、多轮Compaction、并发写入和客户端缓存重建。缓存是测试内存中的KV投影模型，不新增或声称交付生产Watch缓存功能。
- **实现提交：** `8f261fa4fba33644a1de8a1a42129272a430ef31`新增长运行测试；`391323ec1a9892d027ad71caeea4aaddea3bc2af`使early-failure清理初始化安全；`0afd91fb1cbec35a2e592ac568201ce969239203`将长Watch连接至配置Progress间隔的etcd1并在建流前确认本地线性一致Range已应用snapshot revision；`5eb821aa9c15aa20cac9b59a778d0c1fa41f142e`使用Watch前缀外的marker触发空Progress响应并在finally清理marker。所有提交均位于`main`，未创建分支。
- **测试与数据范围：** 唯一前缀`/cnc-knowledge-it/watch-long-running/{uuid}/state/`，四个KV key；多数派etcd2/3负责线性一致Range snapshot、并发写事务、旧游标Compaction取消探测和恢复后核对；etcd1负责保持长Watch流（Compose配置仅etcd1具有`--watch-progress-notify-interval=1s`）。Compaction只在通过Compose project/service标签校验的本次etcd2容器内执行；没有改变peer网络、宿主机iptables或其他容器。
- **初始基线与Progress：** 初始线性一致Range snapshot revision=38；Watch从revision=39创建。等待1.15秒通知间隔后，多数派提交Watch前缀外progress-marker revision=39，长Watch返回空Progress帧revision=39、events=0；缓存无变化。Progress marker不进入状态前缀，finally中单独删除。
- **第一轮并发更新与压缩：** 两个独立客户端通过Barrier并发写入4个PUT，revision集合`[40,41,42,43]`，实际跨客户端交错顺序`[40,42,41,43]`。事件端按revision消费，并用`(revision,key,event_type)`去重；检查previous KV与PUT值后修改cache。随后quorum Range snapshot revision=43与cache完全一致；关闭旧流并在etcd2执行`compact 43`。旧cursor=39在健康多数派重新Watch收到canceled取消帧，无事件且`resume_revision=None`。
- **快照和新Watch之间的并发窗口：** 后台writer先写key0 revision=44并暂停；quorum snapshot revision=44包含该变更，客户端整体替换cache。snapshot完成后writer被放行，在新Watch建流前再写key1/key2 revision=45、46。新Watch从R+1=45恢复，回放这两项事件；revision=44不重放，因为已经包含在快照中。该窗口同时验证不存在快照前丢失、snapshot覆盖事件重复应用或快照后漏事件。
- **第二轮并发更新与压缩：** 活动Watch期间，两个独立客户端并发提交4次PUT/DELETE，revision集合`[47,48,49,50]`，跨客户端交错顺序`[48,49,47,50]`。消费端核实DELETE的previous KV与cache存在性。quorum snapshot revision=50与缓存完全一致；关闭旧流并执行`compact 50`；旧cursor=45重新Watch后被canceled，无事件且没有可续接cursor。客户端cache再次被revision=50快照整体替换。
- **最终恢复与完整性：** 新Watch从snapshot+1=51建立；提交最后一次PUT revision=51，只收到该事件一次；最终quorum线性一致Range revision=51与cache逐key/value一致。观测`snapshot_revisions=[38,43,44,46,50,50,51]`、`compaction_revisions=[43,50]`、`resume_cursors=[39,45,51]`、`unique_watch_event_count=11`、`duplicate_watch_events=0`、`final_cache_matches_linearizable_range=true`；事件revision为`[40,41,42,43,45,46,47,48,49,50,51]`。Progress帧revision=39，trigger marker revision=39。跨快照窗口`gap_writer_revisions=[44,45,46]`，snapshot后且Watch创建前的45/46被完整回放。
- **Live全流程：** [Run 45975852325](https://github.com/rexyll/cnc-knowledge/actions/runs/45975852325)整体success。Watch minority集成测试文件3项测试通过（9.443秒），包括第63轮少数派Progress lag、第65轮长运行缓存Compaction、第64轮quorum Compaction旧cursor恢复。普通三成员etcd集成、mTLS、短TTL Token、Auth/Quorum隔离、mTLS RBAC成员故障与Token传播、诊断采集、Compose容器和volumes清理、Artifact上传与post-job cleanup全部success。诊断Artifact [15187805125](https://github.com/rexyll/cnc-knowledge/actions/runs/45975852325)，SHA-256 `6bd9f0f1f2ed97ccefc9a819b6230d734ac7eef4be8bc1a64954d5c0057a27a2`。
- **默认质量：** [Quality Run 45975852368](https://github.com/rexyll/cnc-knowledge/actions/runs/45975852368)两个Job success：全库542项unittest（34 skipped，508项通过），CH12数值资源143项通过，strict knowledge lint `0 errors / 5 warnings`，结构/data检查0 errors（178 Markdown files、240 relationship records）。34 skipped为条件跳过项，并不计入通过项。
- **中间失败与修正：** 第一版测试在多数派etcd2/3等待空Progress超时，原因是Compose只在etcd1设置1秒Progress间隔；第二版将Watch改到etcd1后，单纯静默等待仍未收到Progress。最终对照已通过的Progress用例，改为在通知间隔后由多数派对Watch前缀外marker写入revision=39，触发空Progress；同时确保etcd1已通过线性一致Range应用snapshot revision，再建立Watch。最终Live Run 45975852325完整通过。两个失败Run不作为正向验收证据。
- **解释边界：** 本轮“长运行”是单次CI Live内跨两轮Compaction、多条Watch流和多次并发事件，不代表无限期稳定性、生产持续负载、背压/内存上限或SLO。cache只是测试模型，不是生产服务。Watch仍为单向HTTP server-streaming；双向`WatchProgress`/`WatchCancel`未实现。Watch/Progress不能作为KV权威状态；断流或Compaction时需要健康多数派线性一致Range快照，完整替换客户端状态，从R+1续接。
- **治理状态：** ASSET-000092正式30项仍`PROPOSED_NOT_APPROVED / NOT_RUN`；schema-v2仍为唯一生产权威；SQLite Coordinator业务状态机尚未迁移；CH17-T004总体继续`IN_PROGRESS`。

## 第六十六轮：慢消费者、Watch积压与Compaction竞争（2026-11-27）

- **目标：** 验证应用暂停读取Watch流、恢复后慢速消费时的事件完整性；在第二段有限积压期间执行Compaction，分别观察既有活动流排空与旧cursor重新建流的语义。
- **实现提交：** `4413098c1da320108ca6b744d04a728e517c69b8`加入慢消费者/Compaction Live场景；`1f0adfdb1911df4b98323b067c951c4d71bc17b8`修正writer、活动流取消revision及零事件边界断言。均提交至`main`，未创建分支。章节任务计划、技术文章第27节、README和本日志同步第66轮结果。
- **实现结构与范围：** 新增`test_slow_watch_consumer_drains_backlog_or_rebuilds_after_compaction`，复用现有Watch minority集成测试类、`Etcd3gwV3Client`同步pull迭代器及一次性三节点Compose Runner。没有修改驱动的消费线程模型，没有新增客户端无界队列、可配置队列容量、磁盘spill、生产缓存或自动重试/切换功能。使用唯一KV前缀、小型定长value、64+96项有限写入；后台writer各自使用独立Etcd客户端。
- **第一阶段停读：** 多数派前缀线性一致Range snapshot revision=59，包含seed key；etcd1上的Watch从revision=60建立。后台writer提交64个唯一PUT时应用不调用`next(stream)`；writer完成后继续暂停读取0.8秒。恢复时每个Watch响应之间延迟8ms，最终64项全部消费，64个响应，最大每响应1事件，事件revision与写入事务revision集合一致。随后多数派snapshot revision=123与应用cache完全一致。
- **第二阶段积压/Compaction：** 重新从cursor=124建立Watch并读取created帧后暂停消费。多数派提交96个新的唯一PUT，最新revision=219；通过Compose project/service标签核验的etcd2容器执行`etcdctl compact 219`成功。应用恢复读取既有活动HTTP Watch流后，该流完整排空96项积压，收到96个响应、每响应1个事件；**本次活动流没有返回Compaction取消帧**，测试记录`compaction_race_mode=drained`。这证明的是本次有限负载和时序下活动流成功排空，不代表不同负载/网络条件下活动流必然如此。
- **旧cursor取消：** 关闭已排空的活动流后，在健康多数派端再次用原cursor=124创建Watch，服务端返回Compaction取消帧；测试核验`canceled=true`、`compact_revision>=219`、events=0、`resume_revision=None`。因此活动流在Compaction后排空积压，并不意味着它的原start_revision可以作为后续建流cursor继续使用。
- **快照恢复：** 多数派线性一致前缀snapshot revision=219整体替换客户端cache；新Watch从`snapshot+1=220`建立。随后提交的key PUT revision=220仅投递一次；最终snapshot revision=220与cache逐key/value一致。测试累计唯一应用161事件（64+96+1），重复0；`max_events_per_response=1`、`progress_revisions_seen=[]`、`final_cache_matches_linearizable_range=true`。
- **Live全流程：** [Run 45980665924](https://github.com/rexyll/cnc-knowledge/actions/runs/45980665924)整体success。Watch minority测试文件4项通过（13.524秒），包括既有少数派Progress lag、quorum Compaction恢复、第65轮多轮Compaction缓存重建和本轮慢消费者/积压竞争；普通三节点etcd、mTLS、短TTL Token、Auth/Quorum隔离、mTLS RBAC成员故障/Token传播、诊断采集、Compose容器/volumes清理、Artifact上传和post-job cleanup均success。诊断Artifact [15189731260](https://github.com/rexyll/cnc-knowledge/actions/runs/45980665924)，SHA-256 `5b7b2a925a27fad24bdf15cf401aecc22691a1c3f75cb84c918f6c7fb29061d5`。
- **默认质量：** [Quality Run 45980665958](https://github.com/rexyll/cnc-knowledge/actions/runs/45980665958)两个必需Job均success：543项unittest（35 skipped，508项通过）；CH12数值资源测试143项通过；strict knowledge lint 0 errors / 5项warnings；结构/data检查0 errors（260实体、240关系、412来源记录、178 Markdown文件）。
- **解释边界：** 本轮验证应用不拉取时的有限事件积压和恢复消费，不测量服务端watcher队列、Python RSS/heap、TCP socket buffer或带宽；不能由64/96项有限事件推导内存上界、自动背压策略、最大持续吞吐或无限期稳定性。驱动当前仍是同步pull iterator，没有后台消费者线程/显式应用缓冲队列。此次没有Progress帧。恢复权威仍是健康多数派线性一致Range；一旦客户端需要重建状态，旧cursor不能复用，必须整体替换snapshot并从R+1建流。Watch仍为单向HTTP server-streaming，不支持双向`WatchProgress`/`WatchCancel`。
- **治理状态：** 这是一次性etcd v3.7.0 / etcd3gw 2.7.0 CI supporting engineering evidence，不等于生产HA、背压/内存容量或正式业务验收。ASSET-000092正式30项仍`PROPOSED_NOT_APPROVED / NOT_RUN`；schema-v2仍为唯一生产权威；SQLite Coordinator业务状态机尚未迁移；CH17-T004保持`IN_PROGRESS`。
