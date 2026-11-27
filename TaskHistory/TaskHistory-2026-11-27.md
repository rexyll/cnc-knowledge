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
