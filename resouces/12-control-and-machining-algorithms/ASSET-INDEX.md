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
| test_gantry_joint_drive_solver.py | Python测试 | 32项资源级回归测试：联合质量矩阵、尺度均衡Cholesky、归一化惯性耦合条件指标、M0跨尺度正定预检、能量/电气有限值边界、自由路径积分、规定路径分块方程与零反力一致性、约束力符号、路径输出及输入拒绝、回调快照隔离 | 项目原创 | 2026-11-23 | 原创代码 | 同上 |

上述32项测试尚未执行。CI只验证知识库结构与数据，不运行资源模块或资源测试。

## 联合移动轴—电流环数值验证协议（2026-11-23）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| `gantry-joint-drive-numerical-verification-protocol.md` | Markdown验证规范 | RK4步长收敛、机电功率/能量预算、自由轴与规定轨迹约束参考模型比较、验收与归档口径 | 项目原创 | 2026-11-23 | 原创文档 | 龙门连续移动负载与双向耦合专题 |
| `gantry-joint-drive-verification-matrix.csv` | CSV测试矩阵 | RK4-01～04、ENE-01～03、PATH-01的输入/参考/指标/判据；RK4-01为合成报告态完成，其余7项仍NOT_RUN | 项目原创 | 2026-11-23 | 原创模板/状态记录 | 同上 |


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
| test_gantry_joint_drive_path_comparison.py | Python测试 | 37项资源级测试：五次参考路径、Simpson/梯形求积与有限值边界、机电功率互易与约束功符号、混合单位归一化、限幅精确比较、来源ID校验、CSV哈希绑定、归档校验/篡改识别/路径覆盖拒绝、溢出边界与CLI错误返回 | 项目原创 | 2026-11-23 | 原创代码 | 同上 |

当前PATH-01运行器资源测试37项、求解器资源测试32项，共69项，均未执行；仓库CI不执行resouces资源测试。


## PATH-01限幅感知诊断更新（2026-11-23）

运行器在每次电流命令回调中观测电流参考限幅和电压饱和；自由与规定路径两侧分别按RK4阶段计数。规定路径积分器最后一次端点诊断不计入RK4阶段，避免阶段次数偏差。汇总模板新增预期/实际阶段计数、两类限幅计数、任一限幅激活比例、计数一致性和 `smooth_unsaturated_regime`；时序模板新增请求电流命令、限幅后参考值及两类饱和布尔字段。新增3项纯函数测试，资源辅助测试现为10项；连同求解器24项共34项，均未执行。


PATH-01的光滑未限幅门控现覆盖 `h/h2/h4/h8` 全部四档，而非只看 `h/8`。新增字段 `all_refinements_smooth_unsaturated_regime` 写入汇总CSV，manifest中的 `smooth_unsaturated_regime` 表示整个收敛细化序列；任何一档触发限幅或阶段计数异常，均阻止常规工程PASS。辅助测试增至12项（求解器24项，合计36项），均未执行。


电流参考限幅标志在RK4阶段计数和输出网格时序中统一调用精确裁剪比较函数，避免输出采样列因容差而漏掉小幅裁剪。新增相邻浮点数裁剪回归测试；运行器辅助资源测试13项，求解器24项，共37项未执行。


PATH-01 manifest现额外保留 `source_documents_or_measurement_ids`，与 `parameter_source` 一同建立模型参数的来源追溯；配置来源ID必须是去空白、无重复的非空字符串数组。新增3项资源测试，目前运行器16项、求解器24项，共40项均未执行。


## PATH-01电压饱和精确判定与能量求积复核（2026-11-23）

运行器时序限幅标志沿用求解器 `voltage_saturated`，该标志现以裁剪后的电压与原始PI电压精确比较；上下电压轨一ULP越界均有新增资源测试。汇总CSV新增 `free_energy_residual_trapezoid_J`、`prescribed_energy_residual_trapezoid_J` 两列，保留梯形残差与Simpson残差的差异供数值敏感性判读。求解器测试25项、PATH-01辅助测试17项，共42项资源测试均未执行。


## PATH-01输出文件哈希绑定与失败恢复（2026-11-23）

PATH-01运行器的manifest采用 schema_version: 2，并在 output_artifacts 中分别记录时序CSV和汇总CSV的SHA-256、字节数、数据行数与列数。运行器先把完整输出写入输出目录下的暂存子目录，再发布两份CSV，manifest最后发布作为完成标记。暂存失败时保留原归档；发布中断时manifest缺失，该目录不能视为完整结果，须检查后以 --force 重跑整套输出。新增3项资源级测试，运行器辅助测试20项、求解器25项、合计45项，全部未执行。


## PATH-01独立归档校验与配置/CLI边界（2026-11-23）

运行器新增 --verify-archive，无需原始配置、不运行求解器；对manifest schema/case/status、固定CSV文件名、内容SHA-256、字节数、列名、每行列宽、数据行数与manifest元数据进行核对，成功返回 VERIFIED。路径覆盖、哈希不一致、缺文件或CSV结构错误均会失败。配置校验要求schema_version为整数1、来源ID数组显式存在；拒绝浮点转换溢出、非有限步长比值，以及h/8细化后超过平台索引范围的区间数。CLI对I/O、JSON/配置、数值溢出与运行异常返回2。PATH-01辅助测试34项、求解器32项，共66项，均未执行。

## PATH-01质量矩阵求解与能量账本数值边界（2026-11-23）

联合求解器的自由/规定路径惯性方程现使用对角尺度均衡Cholesky；新增归一化惯性耦合条件指标接口但不设通用阈值。求解器与PATH-01运行器对质量矩阵、机械/电气储能、功率项和两种求积结果增加非有限/溢出检查。资源测试现为求解器32项、运行器34项，合计66项，均未执行。

## 机电功率互易与约束功符号测试（2026-11-23）

运行器资源测试新增3项：检查 (Kf-Ke)*i*ell_dot 在互易常数相等/不等时的零值和正负号、规定路径 lambda*sdot_ref 在正/反向的符号，以及自由路径约束功始终为零。PATH-01运行器37项、求解器32项，合计69项，均未执行。


## 阻尼耗散与外部广义力功率符号测试（2026-11-24）

PATH-01运行器测试新增2项，验证结构阻尼与平滑轴摩擦在正反向运动时均为非负耗散功率，以及外部广义力功率在同向/反向/正交三种情况下分别为正/负/零。当前PATH-01运行器资源测试39项、求解器资源测试32项，共71项，均未执行；仓库Knowledge Quality CI不覆盖这些资源级测试。


## ENE-01～03独立能量率基准测试（2026-11-24）

求解器资源测试新增3项，采用储能函数沿状态方程向量场的中心差分方向导数，与显式解析功率预算对照；覆盖Kf=Ke端口互易、结构阻尼/轴摩擦耗散和外部广义力功率。该方法不复用PATH-01账本，但仍基于同一模型实现。求解器35项、PATH-01运行器39项，共74项资源测试全部未执行；Knowledge Quality CI不覆盖这些资源测试。


## ENE独立瞬时能量率oracle更新（2026-11-24）

求解器35项资源测试中的ENE-01～03采用双步长中心差分方向导数（1e-5 s、5e-6 s）与二阶Richardson外推，并将细步长估计一并与显式解析功率预算比较。该增强仅用于局部差分步长敏感性控制；35项求解器测试与39项PATH-01运行器测试均未执行。


## ENE多步积分能量闭合协议（2026-11-24）

协议5.15定义四档积分的储能变化、功率积分、能量残差与归一化残差；Simpson为主、梯形为敏感性诊断。预声明能量尺度/地板及最细两档残差阈值；跨零或噪声地板主导时不强行报告残差阶数。该协议未执行ENE积分。


## ENE-01～03独立积分运行器（2026-11-24）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| `gantry_joint_drive_energy_closure.py` | Python源码 | ENE-01～03单用例四档RK4积分；独立功率账本、Simpson/梯形能量残差、限幅阶段统计、CSV/manifest哈希归档与归档校验 | 项目原创 | 2026-11-24 | 原创代码 | 龙门连续移动负载与双向耦合专题 |
| `test_gantry_joint_drive_energy_closure.py` | Python测试 | 49项ENE运行器资源测试，覆盖功率账本、输入/坐标契约、归档语义、嵌套求积、阶段功率、h/16参考、状态尺度、噪声预算与ENE-01/02/03集成/归档回归 | 项目原创 | 2026-11-24 | 原创代码 | 同上 |
| `gantry-joint-drive-energy-closure-config-template.json` | JSON配置模板 | ENE-01/02/03参数/来源/初值/积分/能量尺度和阈值模板；不含默认机床参数 | 项目原创 | 2026-11-24 | 原创模板 | 同上 |

当前求解器35项、PATH-01运行器39项、ENE运行器4项，共78项资源测试均未执行。该运行器尚未执行任何ENE积分；Knowledge Quality CI不覆盖资源代码/测试。


## ENE积分运行器配置契约与判读门控加固（2026-11-24）

- ENE运行器新增4项配置契约测试：ENE-02必须有非零结构阻尼、轴黏性摩擦和库仑摩擦；ENE-03必须有非零外部广义力；外力坐标顺序必须严格匹配五维广义坐标定义。
- ENE资源测试由4项增至12项；连同求解器35项和PATH-01运行器39项，共86项资源测试，全部未执行。
- 经验残差阶数在噪声地板与稳定性门控尚未进入配置前不计算；输出归档采用staging及逐文件原子替换，manifest最后发布，不表示多文件事务原子性。

| `gantry_joint_drive_energy_closure.py` | Python运行器 | ENE归档校验：manifest状态/限幅报告、数值有限性、CSV时间网格和验收状态一致性校验 | 项目原创 | 2026-11-24 | 原创代码 | 同上 |


## ENE运行器数值完整性与资源规模门控（2026-11-24）

- gantry_joint_drive_energy_closure.py增加四档合计50,000采样点上限、manifest端同口径检查、12维状态有限性检查和所有分项积分/残差有限性检查。
- RK4阶段数与理论值不符现在判为FAIL；限幅但阶段完整仍为COMPLETED_REPORT_ONLY。
- test_gantry_joint_drive_energy_closure.py新增3项资源测试定义；ENE运行器测试15项，求解器35项、PATH-01运行器39项，共89项资源测试均未执行。


## ENE与RK4阶段接口一致性回归测试（2026-11-24）

- `test_gantry_joint_drive_energy_closure.py` 新增1项：验证两区间8个RK4阶段回调的时刻/状态快照，以及功率账本端电压与状态方程电流导数、端口输入功率的一致性。
- ENE测试16项，求解器35项、PATH-01运行器39项，共90项资源测试全部未执行；ENE积分未运行。


## ENE多尺度残差诊断更新（2026-11-24）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| `gantry_joint_drive_energy_closure.py` | Python源码 | ENE汇总增加六类功绝对贡献率、三种残差尺度比率及Simpson/梯形积分差敏感性指标 | 项目原创 | 2026-11-24 | 原创代码 | 龙门连续移动负载与双向耦合专题 |
| `test_gantry_joint_drive_energy_closure.py` | Python测试 | 新增3项分项贡献率/零尺度保护/求积敏感性资源测试定义 | 项目原创 | 2026-11-24 | 原创代码 | 同上 |

当前求解器35项、PATH-01运行器39项、ENE运行器19项，共93项资源测试全部未执行；ENE积分未运行。


## ENE固定轨迹功率求积诊断更新（2026-11-24）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| `gantry_joint_drive_energy_closure.py` | Python源码 | 新增冻结h/8轨迹的嵌套Simpson求积诊断、轨迹/求积变化代数分解和归档重算 | 项目原创 | 2026-11-24 | 原创代码 | 龙门连续移动负载与双向耦合专题 |
| `test_gantry_joint_drive_energy_closure.py` | Python测试 | 新增3项固定轨迹求积嵌套网格、分解恒等式和有限性测试定义 | 项目原创 | 2026-11-24 | 原创代码 | 同上 |

当前求解器35项、PATH-01运行器39项、ENE运行器22项，共96项资源测试全部未执行；ENE积分未运行。

## ENE RK4阶段功率快照资源登记（2026-11-24）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| gantry_joint_drive_energy_closure.py | Python源码 | 新增RK4阶段功率快照CSV、经典RK4加权分项功/净功积分、阶段残差及归档重算校验 | 项目原创 | 2026-11-24 | 原创代码 | 龙门连续移动负载与双向耦合专题 |
| test_gantry_joint_drive_energy_closure.py | Python测试 | 新增3项RK4阶段加权积分、阶段顺序/数量和非有限功率测试定义 | 项目原创 | 2026-11-24 | 原创代码 | 同上 |

新增归档文件由ENE运行器在未来实际执行时生成，当前未生成任何仿真结果文件。ENE运行器测试定义25项、求解器35项、PATH-01运行器39项，共99项资源测试均未执行。

## ENE h/16参考轨迹资源登记（2026-11-24）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| `gantry_joint_drive_energy_closure.py` | Python源码 | 新增h/16同模型参考积分、共同节点状态/功率/能量闭合对照、参考轨迹限幅统计及归档重算 | 项目原创 | 2026-11-24 | 原创代码 | 龙门连续移动负载与双向耦合专题 |
| `test_gantry_joint_drive_energy_closure.py` | Python测试 | 新增4项h/16参考对照/非嵌套网格/非有限值/manifest完整性测试定义 | 项目原创 | 2026-11-24 | 原创代码 | 同上 |

运行器未来运行时生成 `gantry-joint-drive-energy-closure-reference-h16-timeseries.csv`；当前未生成仿真结果文件。ENE测试定义29项、求解器35项、PATH-01运行器39项，共103项资源测试均未执行。

## ENE相邻细化轨迹诊断资源登记（2026-11-24）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| `gantry_joint_drive_energy_closure.py` | Python源码 | 新增h/h2/h4/h8/h16相邻轨迹共同粗网格差值、逐分量状态误差、净功/储能/残差对照与归档重算 | 项目原创 | 2026-11-24 | 原创代码 | 龙门连续移动负载与双向耦合专题 |
| `test_gantry_joint_drive_energy_closure.py` | Python测试 | 新增3项相邻轨迹嵌套样本、逐分量差/同网格净功和有限性测试定义 | 项目原创 | 2026-11-24 | 原创代码 | 同上 |

当前ENE测试定义32项、求解器35项、PATH-01运行器39项，共106项资源测试全部未执行。未产生ENE运行归档。

## ENE逐分量特征尺度资源登记（2026-11-24）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| `gantry_joint_drive_energy_closure.py` | Python源码 | 新增12维状态特征尺度来源校验、逐分量无量纲相邻轨迹差异、manifest v4字段/单位/来源校验 | 项目原创 | 2026-11-24 | 原创代码 | 龙门连续移动负载与双向耦合专题 |
| `test_gantry_joint_drive_energy_closure.py` | Python测试 | 新增3项状态特征尺度完整性、来源可追溯性、归档尺度一致性测试定义 | 项目原创 | 2026-11-24 | 原创代码 | 同上 |

ENE测试定义35项，求解器35项、PATH-01 39项，共109项资源测试均未执行。配置模板的12项特征尺度和来源继续留空，未创建仿真产物。


## ENE残差噪声底和经验阶数门控资源登记（2026-11-24）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| `gantry_joint_drive_energy_closure.py` | Python源码 | 新增预声明残差数值噪声底契约、五层残差门控、条件式相邻经验指数及manifest/CSV重算校验；配置schema 3、manifest schema 5 | 项目原创 | 2026-11-24 | 原创代码 | 龙门连续移动负载与双向耦合专题 |
| `test_gantry_joint_drive_energy_closure.py` | Python测试 | 新增噪声底来源契约、噪声底/符号/单调/限幅门控和manifest噪声底完整性测试定义 | 项目原创 | 2026-11-24 | 原创代码 | 同上 |
| `gantry-joint-drive-energy-closure-config-template.json` | JSON配置模板 | 增加噪声底数值、方法、来源说明和来源ID字段；保持空值，不提供未经分析的默认噪声界 | 项目原创 | 2026-11-24 | 原创配置模板 | 同上 |

ENE运行器测试定义38项，求解器35项、PATH-01运行器39项，共113项资源测试全部未执行。噪声底模板仍为空，未生成ENE仿真归档。


## ENE门控阶数null归档一致性修正（2026-11-24）

- 嵌套manifest诊断比较器增加JSON null精确匹配分支；门控抑制阶数时，四个pairwise指数的null必须与独立重算结果逐项一致。
- 新增1项ENE资源测试定义，ENE运行器39项、求解器35项、PATH-01 39项，共113项资源测试均未执行；ENE积分仍未运行。



## ENE残差数值预算输入与自动推导资源登记（2026-11-24）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| `gantry_joint_drive_energy_closure.py` | Python源码 | 新增binary64 gamma-k Simpson累加/残差减法前向误差预算、最小噪声底自动推导、预算下界门控及manifest v6重算 | 项目原创 | 2026-11-24 | 原创代码 | 龙门连续移动负载与双向耦合专题 |
| `test_gantry_joint_drive_energy_closure.py` | Python测试 | 新增误差预算分项/网格尺度、浮点假设/界缺失拒绝和低于预算底线拒绝测试定义 | 项目原创 | 2026-11-24 | 原创代码 | 同上 |
| `gantry-joint-drive-energy-closure-config-template.json` | JSON配置模板 | 新增7个外部误差预算输入界、binary64格式及roundTiesToEven舍入声明；保持数值界为空、算术确认标志未确认 | 项目原创 | 2026-11-24 | 原创配置模板 | 同上 |

ENE运行器测试定义42项（自动预算测试包括预算报告精确数值比较回归），求解器35项、PATH-01 39项，共116项资源测试全部未执行。尚无已确认的设备参数、预算来源界或仿真产物。

预算manifest报告及残差阶数诊断使用精确JSON数值核对；对应资源回归测试已定义但未执行。
## RK4-01合成步长收敛筛查资源（2026-11-24）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| `gantry_joint_drive_rk4_screen.py` | Python源码 | RK4-01～04共用四级h/h2/h4/h8积分runner；支持恒定电流和五次时间标度PD电流命令，记录12维状态、参考轨迹/误差、阶段次数/限幅、相邻网格分量差异与有限层级观测阶数；不判定机器工程精度 | 项目原创 | 2026-11-24 | 原创代码 | 龙门连续移动轴—电流环联合模型数值验证协议 |
| `gantry-joint-drive-rk4-01-synthetic-config.json` | JSON配置 | RK4-01低速平滑合成夹具；参数和状态特征尺度显式标记SYNTHETIC_FIXTURE | 项目原创 | 2026-11-24 | 原创合成配置 | 同上 |
| `test_gantry_joint_drive_rk4_screen.py` | Python测试 | 11项运行器资源测试，覆盖合成来源/12维特征尺度契约、四级积分、RK4-02正向/RK4-03反向/RK4-04非零载荷混合符号耦合工况、RK4-04逐分量数值门槛与路径误差诊断、归档完整性和单位字段一致性 | 项目原创 | 2026-11-24 | 原创代码 | 同上 |
| `generated/rk4-01-synthetic/rk4-01-synthetic-timeseries.csv` | CSV时序 | 四档固定步长积分的604行状态时序，12维状态按原单位记录 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/rk4-01-synthetic/rk4-01-level-summary.csv` | CSV汇总 | h/h2/h4/h8四档积分区间、步长、样本数、RK4阶段数、限幅计数和有限性标志 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/rk4-01-synthetic/rk4-01-adjacent-differences.csv` | CSV差异 | 三组相邻细化网格的12状态分量最大/RMS差、归一化差异和有限层级观测阶数 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/rk4-01-synthetic/rk4-01-run-manifest.json` | JSON运行清单 | 配置/源码SHA-256、执行环境、数值筛查、限幅和阶段统计、三个CSV文件校验元数据 | 脚本生成 | 2026-11-24 | 合成运行记录 | 同上 |

运行状态：RK4-01～04、ENE-01～03均为`COMPLETED_REPORT_ONLY`；PATH-01仍`NOT_RUN`。上述完成状态仅表示合成模型数值/软件筛查，不是机床实测或性能验收。


## RK4-02正向自由路径数值筛查资源（2026-11-24）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| `gantry-joint-drive-rk4-02-synthetic-config.json` | JSON配置 | RK4-02正向自由坐标合成工况；五次静止—静止参考0.72m→0.735m，连续PD电流回调；对象参数、增益和状态尺度均为合成夹具 | 项目原创 | 2026-11-24 | 原创合成配置 | 龙门连续移动轴—电流环联合模型数值验证协议 |
| `generated/rk4-02-synthetic/rk4-02-synthetic-timeseries.csv` | CSV时序 | 604行四级积分状态、参考位置/速度、电流需求及限幅/饱和诊断 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/rk4-02-synthetic/rk4-02-level-summary.csv` | CSV汇总 | 四档积分区间/阶段数、实际净位移、参考路径误差RMS/峰值/端点和饱和统计 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/rk4-02-synthetic/rk4-02-adjacent-differences.csv` | CSV差异 | 三组相邻网格的12状态分量最大/RMS差、归一化差异和有限层级观测阶数 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/rk4-02-synthetic/rk4-02-run-manifest.json` | JSON运行清单 | 运行参数、12维状态单位/特征尺度、四档诊断、相邻差/观测阶数及三个CSV的SHA-256/尺寸/行列数 | 脚本生成 | 2026-11-24 | 合成运行记录 | 同上 |
| `docs/data/sources/SRC-000373.json` | JSON来源记录 | Modern Robotics开源软件实现对五次静止—静止时间标度公式及端点速度/加速度条件的来源说明 | NxRLab / Modern Robotics | 2026-11-24 | 仅记录链接 | 同上 |

RK4-01和RK4-02均为`COMPLETED_REPORT_ONLY`。RK4-02的自由轴在模拟时长内仅向正方向移动约5.45mm，最细档终点比0.735m参考终点低约9.55mm；没有预设跟踪容差，因此不属于轨迹跟踪验收。RK4-03/04、ENE-01/02/03和PATH-01仍`NOT_RUN`。


## RK4-03反向自由路径数值筛查资源（2026-11-24）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| `gantry-joint-drive-rk4-03-synthetic-config.json` | JSON配置 | RK4-03反向自由坐标合成工况；五次静止—静止参考0.72m→0.705m，负前馈电流和连续PD电流回调；全部机械/电气参数、增益与尺度均为合成夹具 | 项目原创 | 2026-11-24 | 原创合成配置 | 龙门连续移动轴—电流环联合模型数值验证协议 |
| `generated/rk4-03-synthetic/rk4-03-synthetic-timeseries.csv` | CSV时序 | 604行四级积分状态、反向参考位置/速度、负电流需求及限幅/饱和诊断 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/rk4-03-synthetic/rk4-03-level-summary.csv` | CSV汇总 | 四档积分区间/阶段数、实际负向净位移、参考路径误差RMS/峰值/端点和饱和统计 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/rk4-03-synthetic/rk4-03-adjacent-differences.csv` | CSV差异 | 三组相邻网格的12状态分量最大/RMS差、归一化差异和有限层级观测阶数 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/rk4-03-synthetic/rk4-03-run-manifest.json` | JSON运行清单 | 反向运行参数、12维状态单位/特征尺度、四档诊断、相邻差/观测阶数及三个CSV的SHA-256/尺寸/行列数 | 脚本生成 | 2026-11-24 | 合成运行记录 | 同上 |

RK4-03为`COMPLETED_REPORT_ONLY`。最细档实际负向移动约5.451mm，较0.705m参考终点仍有约+9.549mm偏差；未设置跟踪容差，不属于反向轨迹验收。

## RK4-04结构与路径轴混合非零状态数值筛查资源（2026-11-24）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| `gantry-joint-drive-rk4-04-synthetic-config.json` | JSON配置 | 非零结构坐标/速度、路径速度、电流及积分器状态；非零合成载荷和恒定电流命令。15 kg载荷及全部机械、电气和外载数据均为合成夹具 | 项目原创 | 2026-11-24 | 原创合成配置 | 龙门连续移动轴—电流环联合模型数值验证协议 |
| `generated/rk4-04-synthetic/rk4-04-synthetic-timeseries.csv` | CSV时序 | 604行/22列，四级积分12维状态、电流命令和电气限幅诊断 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/rk4-04-synthetic/rk4-04-level-summary.csv` | CSV汇总 | 4行/23列，四档步长/阶段计数、有限性、饱和统计和自由路径净位移 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/rk4-04-synthetic/rk4-04-adjacent-differences.csv` | CSV差异 | 3行/58列，12状态逐分量最大/RMS绝对差和归一化差，以及相邻层级有限网格观测阶数 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/rk4-04-synthetic/rk4-04-run-manifest.json` | JSON运行清单 | 运行参数/环境、输入SHA-256、四档数值指标、12分量门槛及CSV SHA-256/尺寸/行列校验元数据 | 脚本生成 | 2026-11-24 | 合成运行记录 | 同上 |

RK4-04为`COMPLETED_REPORT_ONLY`。相邻归一化RMS差=1.5932818829959823e-05、6.326497700114816e-07、3.121036304213065e-08；观测阶数=4.654450664538402、4.341310011850346；12个状态分量的h/4到h/8最大归一化差均低于预声明的1e-3合成回归门槛。h/8实际路径净位移约-1.448mm，未设置路径参考；不得将其解读为轨迹跟踪结果。GitHub Actions Run 45408964085通过127/127项资源测试并归档结果，归档提交为`96bdbb3c89ad0b38783b5c6679400f7755425e0f`。ENE-01为`COMPLETED_REPORT_ONLY`；PATH-01仍`NOT_RUN`。


## ENE-01理想单端口机电能量闭合运行资源（2026-11-24）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| `gantry-joint-drive-ene-01-synthetic-config.json` | JSON配置 | ENE-01理想单端口合成夹具；零结构阻尼/轴摩擦/外力、Kf=Ke；机械、电气、初始状态、积分参数、12维特征尺度与能量噪声界均预先声明 | 项目原创 | 2026-11-24 | 原创合成配置 | 龙门连续移动轴—电流环联合模型能量验证协议 |
| `generated/ene-01-synthetic/gantry-joint-drive-energy-closure-timeseries.csv` | CSV时序 | 604行/33列，四档积分12维状态、能量、各项功率/积分、残差与电气诊断 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/ene-01-synthetic/gantry-joint-drive-energy-closure-stage-power-timeseries.csv` | CSV阶段功率 | 4960行/20列，h～h/8及h/16参考的RK4阶段功率快照 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/ene-01-synthetic/gantry-joint-drive-energy-closure-reference-h16-timeseries.csv` | CSV参考时序 | 641行/33列，h/16更细网格参考轨迹及状态/储能/功率诊断 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/ene-01-synthetic/gantry-joint-drive-energy-closure-summary.csv` | CSV汇总 | 4行/58列，四级积分能量预算、Simpson/梯形残差、分项功、阶段完整性和归一化诊断 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/ene-01-synthetic/gantry-joint-drive-energy-closure-run-manifest.json` | JSON运行清单 | config/solver/PATH support/runner SHA-256、噪声底和浮点预算、h/16参考、四档限幅/阶段报告及CSV校验元数据 | 脚本生成 | 2026-11-24 | 合成运行记录 | 同上 |
| `docs/data/sources/SRC-000374.json` | JSON来源记录 | Higham与Mary (2019) 对常规gamma_n浮点舍入误差界的来源记录；不支持ENE配置中的外部储能/功率传播假设 | 学术出版物 | 2026-11-24 | 仅记录链接/引用信息 | 同上 |

ENE-01为`COMPLETED_REPORT_ONLY`。四档Simpson残差h～h/8为2.2950317094e-5/1.1152803970e-6/6.2608904835e-8/3.7119108308e-9J；h/16参考残差2.2588146978e-10J。有限网格观测阶数4.36304/4.15489/4.07613/4.03852；残差高于预声明1e-11J噪声地板，噪声预算自动推导底线5.71379e-12J。工程阈值为null，不判定PASS。GitHub Actions Run 45412967222通过130/130项资源测试并归档五件套，归档提交9e9371c83be66b35b476b29407972f220bb1976a。PATH-01仍`NOT_RUN`；CH12-T003保持`IN_PROGRESS`。

## ENE-02结构阻尼与路径轴摩擦耗散积分资源（2026-11-24）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| `gantry-joint-drive-ene-02-synthetic-config.json` | JSON配置 | ENE-02耗散扩展合成夹具：正定结构阻尼矩阵、非零轴黏性/平滑库仑摩擦、零外力、Kf=Ke；参数和12维状态尺度、能量噪声界预先声明 | 项目原创 | 2026-11-24 | 原创合成配置 | 龙门连续移动轴—电流环联合模型能量验证协议 |
| `generated/ene-02-synthetic/gantry-joint-drive-energy-closure-timeseries.csv` | CSV时序 | 604行/33列，四档积分12维状态、储能、各项功率/累计功、残差与电气诊断 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/ene-02-synthetic/gantry-joint-drive-energy-closure-stage-power-timeseries.csv` | CSV阶段功率 | 4960行/20列，四档及h/16参考各RK4阶段功率快照 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/ene-02-synthetic/gantry-joint-drive-energy-closure-reference-h16-timeseries.csv` | CSV参考时序 | 641行/33列，h/16较细网格参考状态/储能/功率诊断 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/ene-02-synthetic/gantry-joint-drive-energy-closure-summary.csv` | CSV汇总 | 4行/58列，端口输入功、铜耗、结构阻尼、路径摩擦、残差、细化阶数和阶段门控 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/ene-02-synthetic/gantry-joint-drive-energy-closure-run-manifest.json` | JSON运行清单 | config/solver/PATH support/runner SHA-256、噪声预算、h/16参考、逐档阶段/限幅诊断和输出CSV校验元数据 | 脚本生成 | 2026-11-24 | 合成运行记录 | 同上 |

ENE-02为`COMPLETED_REPORT_ONLY`。h/8结构阻尼损失约3.61875e-3J、路径轴摩擦损失约2.044996e-2J，均为正；Simpson残差h～h/8为2.3119731307e-5/1.1233566654e-6/6.3061176673e-8/3.7386620850e-9J，h/16参考为2.2750655201e-10J；四组观测阶数4.36324/4.15492/4.07616/4.03854。预声明噪声地板1e-11J，浮点最低预算5.7137932863e-12J；阈值null，不判定工程PASS。GitHub Actions Run 45416172656通过132/132项资源测试并归档五件套，归档提交97e4f43785902ec32ec682f7003c36ef64347ff1。PATH-01仍`NOT_RUN`；CH12-T003保持`IN_PROGRESS`。
## ENE-03外部广义力输入功率耗散联合积分资源（2026-11-24）

| 文件 | 类型 | 说明 | 来源/作者 | 生成日期 | 权利状态 | 关联知识 |
|---|---|---|---|---|---|---|
| `gantry-joint-drive-ene-03-synthetic-config.json` | JSON配置 | ENE-03合成夹具：沿用ENE-02结构阻尼/轴摩擦，增加常值非零五维外部广义力；全部数值、状态尺度、噪声界均为分析者预声明合成输入 | 项目原创 | 2026-11-24 | 原创合成配置 | 龙门连续移动轴—电流环联合模型能量验证协议 |
| `generated/ene-03-synthetic/gantry-joint-drive-energy-closure-timeseries.csv` | CSV时序 | 604行/33列，四档积分状态、储能、端口功率、耗散、外部功与残差诊断 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/ene-03-synthetic/gantry-joint-drive-energy-closure-stage-power-timeseries.csv` | CSV阶段功率 | 4960行/20列，四档和h/16参考各RK4阶段功率及有符号外部功快照 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/ene-03-synthetic/gantry-joint-drive-energy-closure-reference-h16-timeseries.csv` | CSV参考时序 | 641行/33列，h/16细网格参考状态、储能和能量率 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/ene-03-synthetic/gantry-joint-drive-energy-closure-summary.csv` | CSV汇总 | 4行/58列，输入功、铜耗、阻尼/摩擦耗散、外部广义力功、残差和阶段诊断 | 脚本生成 | 2026-11-24 | 合成数据 | 同上 |
| `generated/ene-03-synthetic/gantry-joint-drive-energy-closure-run-manifest.json` | JSON运行清单 | 输入SHA-256、噪声预算、h/16参考、四档限幅/阶段报告及CSV哈希/尺寸/行列 | 脚本生成 | 2026-11-24 | 合成运行记录 | 同上 |

ENE-03为`COMPLETED_REPORT_ONLY`。h/8外部广义力功=+4.2078931032e-3J，结构阻尼损失=3.6791157486e-3J，路径轴摩擦损失=2.0885147980e-2J；Simpson残差h～h/8为2.3101603200e-5/1.1224940887e-6/6.3012923828e-8/3.7358090553e-9J，h/16参考2.2733322429e-10J；观测阶数4.36321/4.15492/4.07616/4.03854。噪声地板1e-11J，自动浮点底线5.7137932863e-12J，工程阈值null。Actions Run 45417667115通过134/134项资源测试并归档五件套，归档提交de53f2f57c6afca75c62e4bdc980bd6927e2b19b。PATH-01仍`NOT_RUN`；CH12-T003保持`IN_PROGRESS`。