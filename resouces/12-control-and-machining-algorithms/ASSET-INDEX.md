# CH12 双驱龙门 MIMO 仿真资源索引

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| `gantry-mimo-simulation.py` | Python源码 | 双驱双自由度柔性耦合、独立PD/交叉同步控制与频域诊断 | 项目原创 | 2026-11-22 | 原创代码 | [双驱龙门MIMO专题](../../docs/12-control-and-machining-algorithms/gantry-dual-drive-mimo-synchronization-and-robustness.md) |
| `gantry-mimo-simulation-config.json` | JSON配置 | 合成负载、刚度、阻尼、控制器和采样定义 | 项目原创 | 2026-11-22 | 原创配置 | 同上 |
| `gantry-mimo-coupling-envelope.csv` | CSV数据 | 10组负载/耦合刚度组合摘要 | 脚本生成 | 2026-11-22 | 合成数据 | 同上 |
| `gantry-mimo-sync-controller-comparison.csv` | CSV数据 | 4种同步控制器对照摘要 | 脚本生成 | 2026-11-22 | 合成数据 | 同上 |

完整MIMO频率响应脚本运行时会导出140行采样数据；如需长期保留，请将输出目录设为本目录下的 `generated/`。运行示例（从仓库根目录执行）：

```bash
python resouces/12-control-and-machining-algorithms/gantry-mimo-simulation.py --output-dir resouces/12-control-and-machining-algorithms/generated
```

所有资源均为原创代码和合成数据，不包含真实机床测量、客户数据或厂商保密参数。频率网格奇异值/灵敏度诊断不等同严格multiloop disk margin、结构化mu或实机稳定性证据。

| `gantry-modal-delay-study.py` | Python源码 | 四广义坐标横梁弯曲/扭转假设模态，负载位置相关质量矩阵、精确ZOH冻结工况、整数命令延迟扫描 | 项目原创 | 2026-11-22 | 原创代码 | [横梁模态与延迟专题](../../docs/12-control-and-machining-algorithms/gantry-mimo-modal-load-position-delay-robustness.md) |
| `gantry-modal-delay-study-config.json` | JSON配置 | 模态、负载位置、采样、延迟、同步控制和证据边界 | 项目原创 | 2026-11-22 | 原创配置 | 同上 |
| `gantry-mimo-modal-position-envelope.csv` | CSV数据 | 27组冻结位置/质量对象的广义模态与质量正定性摘要 | 脚本生成 | 2026-11-22 | 合成数据 | 同上 |
| `gantry-mimo-delay-robustness-envelope.csv` | CSV数据 | 4种控制器在7种整数命令延迟下的离散闭环极点统计，共756组测试 | 脚本生成 | 2026-11-22 | 合成数据 | 同上 |
| `gantry-mimo-discrete-step-comparison.csv` | CSV数据 | 3种负载位置工况下1ms延迟阶跃与横梁变形对照 | 脚本生成 | 2026-11-22 | 合成数据 | 同上 |
| `gantry-mimo-discrete-small-gain-margin.csv` | CSV数据 | 中心负载下采样返回差、灵敏度和输出乘性小增益指示量 | 脚本生成 | 2026-11-22 | 合成数据 | 同上 |
