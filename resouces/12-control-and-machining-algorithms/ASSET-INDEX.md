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
| test_gantry_joint_drive_solver.py | Python测试 | 24项资源级回归测试：联合质量矩阵、能量/电气输入契约、自由路径积分、规定路径分块方程与零反力一致性、约束力符号、路径输出及输入拒绝、回调快照隔离 | 项目原创 | 2026-11-23 | 原创代码 | 同上 |

上述24项测试尚未执行。CI只验证知识库结构与数据，不运行资源模块或资源测试。

## 联合移动轴—电流环数值验证协议（2026-11-23）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| `gantry-joint-drive-numerical-verification-protocol.md` | Markdown验证规范 | RK4步长收敛、机电功率/能量预算、自由轴与规定轨迹约束参考模型比较、验收与归档口径 | 项目原创 | 2026-11-23 | 原创文档 | 龙门连续移动负载与双向耦合专题 |
| `gantry-joint-drive-verification-matrix.csv` | CSV测试矩阵 | RK4-01～04、ENE-01～03、PATH-01的输入/参考/指标/判据模板；8项均未执行，规定路径参考积分器已实现 | 项目原创 | 2026-11-23 | 原创模板 | 同上 |


## PATH-01自由轴/规定轨迹对照模板（2026-11-23）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| gantry-joint-drive-path-comparison-config-template.json | JSON配置模板 | 空白参数、初始状态、五次静止—静止参考路径、相同控制/外力回调、四档步长和分量容差定义；无机床默认值 | 项目原创 | 2026-11-23 | 原创模板 | 龙门连续移动负载与双向耦合专题 |
| gantry-joint-drive-path-comparison-timeseries-template.csv | CSV时序模板 | 自由/受约束路径、结构状态、负载点、约束反力/功率、储能及输出采样点电流指令/参考限幅/电压饱和字段 | 项目原创 | 2026-11-23 | 原创模板 | 同上 |
| gantry-joint-drive-path-comparison-summary-template.csv | CSV汇总模板 | 路径/结构/负载点误差、lambda峰值/RMS、约束功、能量残差、收敛阶数、逐档/全细化序列RK4限幅门控及验收状态字段 | 项目原创 | 2026-11-23 | 原创模板 | 同上 |

以上为未填写模板，不包含参数、结果或验收通过声明。


## PATH-01执行器和资源测试（2026-11-23）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| gantry_joint_drive_path_comparison.py | Python源码 | PATH-01四档步长自由轴/理想规定路径比较运行器；输出逐点时序、归一化误差、约束反力/约束功、机电能量账本、阶段限幅诊断和运行manifest | 项目原创 | 2026-11-23 | 原创代码 | 龙门连续移动负载与双向耦合专题 |
| test_gantry_joint_drive_path_comparison.py | Python测试 | 13项资源级纯函数测试：五次参考路径、Simpson求积、混合单位归一化、限幅精确比较、阶段计数、末端诊断剔除及全细化序列门控 | 项目原创 | 2026-11-23 | 原创代码 | 同上 |

新增13项运行器资源测试尚未执行；加上求解器原有24项，PATH/求解器资源测试合计37项，仓库CI均不执行。


## PATH-01限幅感知诊断更新（2026-11-23）

运行器在每次电流命令回调中观测电流参考限幅和电压饱和；自由与规定路径两侧分别按RK4阶段计数。规定路径积分器最后一次端点诊断不计入RK4阶段，避免阶段次数偏差。汇总模板新增预期/实际阶段计数、两类限幅计数、任一限幅激活比例、计数一致性和 `smooth_unsaturated_regime`；时序模板新增请求电流命令、限幅后参考值及两类饱和布尔字段。新增3项纯函数测试，资源辅助测试现为10项；连同求解器24项共34项，均未执行。


PATH-01的光滑未限幅门控现覆盖 `h/h2/h4/h8` 全部四档，而非只看 `h/8`。新增字段 `all_refinements_smooth_unsaturated_regime` 写入汇总CSV，manifest中的 `smooth_unsaturated_regime` 表示整个收敛细化序列；任何一档触发限幅或阶段计数异常，均阻止常规工程PASS。辅助测试增至12项（求解器24项，合计36项），均未执行。


电流参考限幅标志在RK4阶段计数和输出网格时序中统一调用精确裁剪比较函数，避免输出采样列因容差而漏掉小幅裁剪。新增相邻浮点数裁剪回归测试；运行器辅助资源测试13项，求解器24项，共37项未执行。


PATH-01 manifest现额外保留 `source_documents_or_measurement_ids`，与 `parameter_source` 一同建立模型参数的来源追溯；配置来源ID必须是去空白、无重复的非空字符串数组。新增3项资源测试，目前运行器16项、求解器24项，共40项均未执行。


## PATH-01电压饱和精确判定与能量求积复核（2026-11-23）

运行器时序限幅标志沿用求解器 `voltage_saturated`，该标志现以裁剪后的电压与原始PI电压精确比较；上下电压轨一ULP越界均有新增资源测试。汇总CSV新增 `free_energy_residual_trapezoid_J`、`prescribed_energy_residual_trapezoid_J` 两列，保留梯形残差与Simpson残差的差异供数值敏感性判读。求解器测试25项、PATH-01辅助测试17项，共42项资源测试均未执行。
