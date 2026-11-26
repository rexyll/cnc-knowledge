# 备件库存备份 Unified Coordinator Aggregate 容量模型与观测边界

**知识编号：** KNOW-000056  
**章节：** CH17 操作、维护与维修  
**状态：** 离线合成容量画像工具与测试已建立；真实存储性能和部署容量仍待验证  
**关联知识：** KNOW-000051、KNOW-000054、KNOW-000055  
**关联资源：** ASSET-000087

## 1. 本轮目标

第四十轮和第四十一轮把 Admission 调度状态及 Coordinator Leader、scope fencing、operation ledger 集中到一个 revisioned aggregate。统一状态避免多个权威状态源之间的双写窗口，但也产生两个需要量化的约束：

- 每次状态变化需要重新序列化并写回整个 aggregate；scope 与 operation ledger 随业务历史增长。
- Coordinator 写入还需要比较 aggregate revision、活动 Admission lease/request 索引及当前 Leader key。活动 lease 数量增加时，比较项也随之增加。

本轮新增离线探针 scripts/spare_parts_coordinator_capacity_probe.py，用当前 schema-v2 字段形状构造纯合成负载，统计状态体积和比较项模型。探针不连接 SQLite、etcd、对象存储或任何企业系统，不执行写入。

## 2. 可精确测量的内容

工具复用当前实现的 _initial_state()、Coordinator scope/operation 记录构造函数和 canonical JSON encoder，报告：

| 指标 | 含义 |
|---|---|
| aggregate_value_bytes | schema-v2 aggregate 完整 JSON value 的UTF-8字节数，按仓库当前canonical JSON编码精确计算 |
| coordinator_subtree_bytes | coordinator子树的JSON字节数 |
| scope_index_bytes | scopes索引的JSON字节数 |
| operation_index_bytes | operations索引的JSON字节数 |
| scope_count / operation_count | 合成scope及operation记录数量 |
| active_lease_count / waiter_count | Admission活动lease与等待项数量 |
| coordinator_compare_count_estimate | 按当前代码结构计算的Coordinator事务比较项模型 |

对于当前非过期活动lease快照，比较项模型为：

\[
N_{\mathrm{compare}} = 1 + 2N_{\mathrm{active}} + 1
\]

其中第一项是aggregate revision比较，活动lease的lease key与request key各一项，最后一项是当前Leader key精确值比较。该模型不包含具体adapter额外的传输/服务端实现行为；expired cleanup会增加写操作，不能把比较项数量直接等同于完整RPC请求大小或延迟。

## 3. etcd请求大小参考与预算解释

etcd v3.7官方系统限制文档说明：默认单个客户端请求上限为1.5 MiB（1,572,864字节），该限制可以通过服务端 --max-request-bytes 配置调整；文档同时指出etcd面向小型键值元数据，大请求可能增加其他请求的延迟。来源：SRC-000402。

本工具默认以1,572,864字节作为**文档参考值**，并用其50%（786,432字节）作为画像展示用的内部目标预算。50%是项目分析假设，不是etcd默认限制、官方建议值、生产门禁或跨部署通用阈值。用户可用CLI参数更改参考上限与目标占比，以便匹配经过核实的部署配置。

aggregate_value_bytes只是写入请求中状态value自身的精确字节数，也是完整请求负载的下界。实际请求还包含key、事务比较条件、成功/失败分支操作和协议封装等开销。因此，不能仅凭JSON value占比判断真实请求一定能被服务器接受。

## 4. 合成画像场景

资源 spare-parts-coordinator-capacity-profile-v1.csv（ASSET-000087）定义14个纯合成场景，分别隔离scope增长、operation增长、活动lease比较项增长、waiter增长及混合负载。

运行：

~~~bash
python -m scripts.spare_parts_coordinator_capacity_probe
~~~

可指定经核实的部署请求上限和分析预算：

~~~bash
python -m scripts.spare_parts_coordinator_capacity_probe \
  --max-request-bytes 1572864 \
  --target-utilization 0.50
~~~

命令只向stdout输出JSON画像；不会写入资源目录或远端存储。所有数据均由工具生成的 synthetic-* 标识构成。

## 5. 解读与决策边界

- scope/operation字节统计用于识别aggregate增长来源；它不是数据库文件大小、磁盘占用或内存占用。
- 比较项模型用于理解活动lease规模对Coordinator事务的影响；不是etcd server实际执行次数、Txn耗时或吞吐率测量。
- 本轮没有设置硬性容量阈值，没有拒绝任何现有状态写入，也没有改变schema、namespace、lease生命周期或业务状态机。
- 本轮没有实测真实etcd配置、真实gRPC/protobuf请求大小、Txn latency、p50/p95/p99、吞吐量、磁盘WAL、compaction或多节点quorum。
- SQLite/InMemoryEtcdV3Client测试不能证明真实etcd的容量及网络分区行为；50%画像预算不构成生产可用性承诺。

在任何生产上线或容量门禁之前，应先冻结目标etcd版本和服务端参数，连接隔离的真实etcd测试集群，以代表性但脱敏/合成的工作负载进行请求编码、Txn大小、比较项/操作项数量、端到端延迟和故障恢复测量。阈值须由系统所有者结合实际配置、SLO、备份/归档策略和容量测试证据批准。

## 6. 测试与验收

新增 tests/test_spare_parts_coordinator_capacity_probe.py，覆盖canonical JSON字节对齐、scope/operation增长单调性、活动lease比较项模型、waiter只读报告、预算参数校验、输入边界、矩阵唯一性及场景增长关系。

所有场景仅为 SYNTHETIC_TEST_ONLY。自动化测试通过只证明探针输入构造、统计和边界校验正确，不代表真实etcd性能或企业业务验收。

## 7. 来源

- SRC-000402：etcd v3.7官方System limits页面；请求大小默认值及可配置性。
- KNOW-000054、KNOW-000055：统一Admission及Unified Coordinator schema-v2状态结构。
