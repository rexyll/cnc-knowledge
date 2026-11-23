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


## 连续移动负载与MIMO disk-margin接口（2026-11-22）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| gantry-modal-delay-study.py | Python源码 | 更正阻尼交叉项量纲，原脚本闭环延迟/阶跃/小增益结果已重算 | 项目原创 | 2026-11-22 | 原创代码 | 横梁模态专题 |
| gantry-modal-delay-study-config.json | JSON配置 | 记录正确的广义阻尼交叉项定义和数值更正 | 项目原创 | 2026-11-22 | 原创配置 | 同上 |
| gantry-mimo-delay-robustness-envelope.csv | CSV数据 | 28行更正后延迟稳定性摘要 | 脚本生成 | 2026-11-22 | 合成数据 | 同上 |
| gantry-mimo-discrete-step-comparison.csv | CSV数据 | 9行更正后阶跃/变形对照 | 脚本生成 | 2026-11-22 | 合成数据 | 同上 |
| gantry-mimo-discrete-small-gain-margin.csv | CSV数据 | 16行更正后有限网格小增益诊断量，非disk margin | 脚本生成 | 2026-11-22 | 合成数据 | 同上 |
| gantry-moving-load-study.py | Python源码 | 预设轨迹、时变质量矩阵、移动点链式速度/加速度项、方程核验与可选MIMO disk-margin接口 | 项目原创 | 2026-11-22 | 原创代码 | 连续移动负载专题 |
| gantry-moving-load-study-config.json | JSON配置 | 模型坐标、几何、载荷轨迹、控制器、离散步长和数值边界 | 项目原创 | 2026-11-22 | 原创配置 | 同上 |
| gantry-moving-load-model-comparison.csv | CSV数据 | 18组独立/同步控制器×完整移动/仅变质量/冻结位置模型比较 | 脚本生成 | 2026-11-22 | 合成数据 | 同上 |
| gantry-moving-load-equation-checks.csv | CSV数据 | 123组质量矩阵导数、加速度链式法则、拉格朗日残差和正定性核验 | 脚本生成 | 2026-11-22 | 合成数据 | 同上 |

7,500行选定工况原始时序由 --include-timeseries 可选生成；可选disk-margin结果只有在安装python-control 0.10.2和Slycot并成功计算后才会输出。

> **复现状态：** gantry-moving-load-study.py已归档，CSV来自已完成的参考计算导出；该精确提交版脚本尚未在本轮CI执行，需单独Python回归。disk-margin可选分支因依赖未安装未产生数值文件。


> **指标单位约定：** gantry-moving-load-study 的矩阵/广义力数值范数和特征值按混合m/rad广义坐标直接计算，只能视为声明坐标单位下的数值诊断；不具有单一kg、kg/s或N单位。方程残差字段为 max(1,参考量2-范数) 分母下的归一化偏差，不保证是严格相对误差。


## 联合移动轴与电流环实现资源（2026-11-23）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| gantry_joint_drive_solver.py | Python源码 | 自由路径坐标、单点移动负载联合质量矩阵/运输项、执行器虚功与连续RL/PI电流环 | 项目原创 | 2026-11-23 | 原创代码 | 龙门连续移动负载与双向耦合专题 |
| test_gantry_joint_drive_solver.py | Python测试 | 15项资源级回归测试：联合质量矩阵、零负载、虚功、RL衰减、电流参考限幅/电压饱和、超限状态电流不硬裁剪、静止极限、机电能量平衡、自由路径坐标积分、RK4时间栅格一致性、几何维数契约、参数数组不可逆只读、非有限输入拒绝 | 项目原创 | 2026-11-23 | 原创代码 | 同上 |

上述15项测试尚未执行。CI只验证知识库结构与数据，不运行资源模块或资源测试。