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
