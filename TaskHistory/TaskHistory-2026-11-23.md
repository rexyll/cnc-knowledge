# 龙门联合求解器参数数组所有权加固（2026-11-23）

## 实际完成记录

- **任务ID：** CH12-T003（联合移动轴/电流环模型实现的静态接口加固切片）
- **任务名称：** 参数数组私有快照与只读约束
- **实际完成时间：** 2026-11-23T14:00:31+08:00（Asia/Shanghai）
- **分支：** `main`
- **交付文件：**
  - `resouces/12-control-and-machining-algorithms/gantry_joint_drive_solver.py`
  - `resouces/12-control-and-machining-algorithms/test_gantry_joint_drive_solver.py`
  - `docs/12-control-and-machining-algorithms/gantry-continuous-moving-load-and-multiloop-disk-margin.md`
  - `resouces/12-control-and-machining-algorithms/README.md`
  - `resouces/12-control-and-machining-algorithms/ASSET-INDEX.md`
  - `docs/TaskPlan/12-control-and-machining-algorithms/TaskPlan.md`

## 问题与处理

Python 的 `frozen=True` 不会递归冻结 NumPy 数组。若求解器持有外部传入数组的同一引用，调用方可在构造阶段参数校验后继续修改质量、阻尼、刚度、重力或执行器系数，令已检查的不变量失效。

求解器改为在构造时复制这些数组，并将内部副本设为只读；测试夹具改为在模型构造时显式提供零重力参数，新增资源测试验证原始数组后续修改不会影响模型，以及模型内部参数数组拒绝写入。

## 验收与限制

- **静态审查：** 已检查构造路径、参数引用关系、原测试对参数数组的修改行为及文档/资源索引的一致性。
- **资源测试：** 新增后共13项，尚未执行；当前未取得可用的授权Python/NumPy运行结果。
- **内容提交SHA：** d48f8f3bdc69b2b780c330f6582c279212643175。
- **GitHub CI：** [Run 45121368649](https://github.com/rexyll/cnc-knowledge/actions/runs/45121368649) success；仓库现有测试5/5通过；strict knowledge lint PASS（0 errors）。
- **CI扫描统计：** 22章、130个Markdown文件、407条内部链接、143个实体、240条关系、371条来源、660处章节来源引用。
- **边界：** 该CI没有执行 `resouces/` 下的13项求解器测试。
- **遗留事项：** 运行13项资源测试；补做RK4步长收敛、机械/电气能量平衡独立核验、规定轨迹与自由轴模型交叉比较；真实驱动器参数辨识和HIL/实机验证仍未完成。
- **任务状态：** CH12-T003保持 `IN_PROGRESS`。


## 参数数组只读契约再次加固（2026-11-23）

- **实际完成时间：** 2026-11-23T14:30:00+08:00（Asia/Shanghai）
- **分支：** `main`
- **问题：** NumPy 对自有内存的只读数组可允许调用方通过 `setflags(write=True)` 重新开启写权限，前一提交的 `write=False` 只能防止直接赋值，不能充分保证只读。
- **处理：** `_readonly_float_array` 改为将浮点快照序列化为不可变 `bytes` 缓冲区，再以 `np.frombuffer` 生成数组视图；资源测试逐一检查 `M0/D0/K0`、重力向量和执行器系数数组无法恢复写权限。
- **交付文件：** `resouces/12-control-and-machining-algorithms/gantry_joint_drive_solver.py`、`resouces/12-control-and-machining-algorithms/test_gantry_joint_drive_solver.py`、`docs/12-control-and-machining-algorithms/gantry-continuous-moving-load-and-multiloop-disk-margin.md`、本章 TaskPlan 与本历史记录。
- **内容提交SHA：** `00f84c647e8d212b67b43c54dee7fb6dbf53f00a`。
- **GitHub CI：** [Run 45124730690](https://github.com/rexyll/cnc-knowledge/actions/runs/45124730690) success；仓库原有单元测试5/5通过，strict knowledge lint PASS（0 errors）。
- **CI扫描统计：** 22章、130个Markdown文件、407条内部链接、143个实体、240条关系、371条来源、660处章节来源引用。
- **验收边界：** 该CI不运行资源级测试；13项资源测试仍未执行。
- **遗留事项：** 运行13项资源测试、RK4步长收敛和独立能量平衡核验；真实机床参数辨识与HIL/实机验证未完成。CH12-T003保持 `IN_PROGRESS`。


## RK4时间栅格一致性修正（2026-11-23）

- **实际完成时间：** 2026-11-23T14:30:00+08:00（Asia/Shanghai）
- **分支：** `main`
- **问题：** `simulate()` 对时长/步长比值执行浮点容差内的整数步数判定，但返回时间向量由 `duration_s` 均分，RK4阶段使用原始 `step_s`，边界情形下阶段时间和返回栅格不完全一致。
- **处理：** 采用 `h=duration_s/count` 作为实际RK4有效步长；新增测试核对每步 (k_4) 时间与下一步 (k_1) 时间，资源测试由13项增至14项。
- **交付文件：** 求解器、资源测试、联合模型专题、资源README、ASSET-INDEX、CH12 TaskPlan和本历史文件。
- **内容提交SHA：** `cba6a39e55dc981a42c2ea30d72141cd25134e1b`。
- **GitHub CI：** [Run 45125109149](https://github.com/rexyll/cnc-knowledge/actions/runs/45125109149) success；仓库既有测试5/5通过，strict knowledge lint PASS（0 errors）。
- **CI扫描统计：** 22章、130个Markdown文件、407条内部链接、143个实体、240条关系、371条来源、660处正文引用。
- **验收边界：** 14项资源测试仍未执行；本次未生成积分或步长收敛数值结果。
- **遗留事项：** 执行资源测试；开展RK4步长收敛、独立能量平衡核验、规定轨迹/自由轴交叉比较和实机参数辨识。CH12-T003保持 `IN_PROGRESS`。


## 电流参考限幅与硬件过流保护边界澄清（2026-11-23）

- **实际完成时间：** 2026-11-23T14:44:45+08:00（Asia/Shanghai）
- **分支：** `main`
- **审查发现：** `current_limit_A` 实际裁剪的是电流指令参考值，并不瞬时限制状态电流；模型也不含硬件过流比较器、故障关断/锁存和热降额。先前测试名称“电流参考和电压限值”容易被误读为实际电流受到了硬保护。
- **处理：** 在参数说明与电气诊断处明确“参考限幅”语义；增强现有限幅测试，断言参考值和电压饱和；新增超限状态电流仍按RL方程变化的测试；专题正文、资源README、ASSET-INDEX和CH12计划同步澄清。
- **交付文件：** 求解器、资源测试、专题正文、资源README、ASSET-INDEX、CH12 TaskPlan和本历史文件。
- **内容提交：** `d9b9afbc2948f7b6f9a1e7a148fca96f67026db3`（代码/文档/计划/资源说明）；该提交的仓库CI [Run 45126336210](https://github.com/rexyll/cnc-knowledge/actions/runs/45126336210) success。
- **测试补正提交：** `49e52d14c51fb6d2378fb85254f97d35716ff787`；GitHub Actions [Run 45126386640](https://github.com/rexyll/cnc-knowledge/actions/runs/45126386640) success。实际测试文件核对为15个 `test_` 方法。
- **仓库CI结果：** 既有测试5/5通过；strict knowledge lint PASS（0 errors）；扫描22章、130 Markdown、407内部链接、143实体、240关系、371来源、660处正文来源引用。
- **验收边界：** 两次CI均不运行 `resouces/` 下资源测试；15项资源测试仍未执行。该模型不构成驱动器过流保护、安全限值或热保护验证。
- **遗留事项：** 独立执行资源测试；继续RK4收敛、能量平衡和自由轴交叉验证；取得具体驱动器保护参数并在授权测试环境验证。CH12-T003保持 `IN_PROGRESS`。


## 提交装配更正：补齐电流参考限幅边界测试（2026-11-23）

- **说明：** 参数边界澄清的首个内容提交 `d9b9afbc2948f7b6f9a1e7a148fca96f67026db3` 已更新求解器注释、专题文档、资源说明和计划，但提交对象核对发现配套测试文件未随同写入新增测试方法。
- **更正：** 本次单独补交测试文件，强化指令参考上限/电压饱和断言，并增加 `test_current_reference_limit_does_not_hard_clamp_state_current`，确保资源测试方法数实际达到15项。
- **验收边界：** 测试仍未执行；仓库CI不运行 `resouces/` 下的测试。该修正不构成硬件过流保护验证。
- **分支与提交：** `main`；更正提交 `49e52d14c51fb6d2378fb85254f97d35716ff787`。


## RK4阶段回调状态快照隔离（2026-11-23）

- **任务ID：** CH12-T003（联合移动轴/电流环模型静态接口加固）
- **审查发现：** simulate() 在每个RK4阶段把同一 JointState 实例先后传递给电流指令回调和外部力回调。数据类虽然冻结，但内部NumPy数组可变；第一个回调原地修改数组会改变第二个回调看到的状态，产生回调执行顺序相关的隐藏耦合。
- **处理：** 电流指令与外部力回调分别接收从当前RK4阶段向量独立解包得到的状态快照。回调修改不会跨回调共享，也不改变积分状态。新增 test_simulation_callbacks_receive_independent_stage_state_snapshots，专门让两个回调改写坐标数组并检查隔离行为。
- **资源测试：** 由15项增至16项；**未执行**。仓库知识结构CI不运行 resouces/ 下的资源测试。
- **验证边界：** 本次仅完成静态代码审查、实现和测试用例编写；没有数值仿真、步长收敛、能量平衡或真实驱动器/HIL验证。CH12-T003继续 IN_PROGRESS。

## RK4阶段回调状态快照隔离切片CI验收（2026-11-23）

- **内容提交：** `61835e5043e32e639f56366ba7a311d660dab03d`，更新求解器、16项资源测试、专题正文、资源README、ASSET-INDEX、本章TaskPlan和历史记录。
- **GitHub Actions：** [Run 45128932385](https://github.com/rexyll/cnc-knowledge/actions/runs/45128932385) success；单元测试步骤和 strict knowledge lint 步骤均成功。
- **验收边界：** CI未执行 resouces/ 下的16项求解器测试。该结果不等于新资源测试通过，不代表资源仿真、步长收敛、能量平衡、参数辨识或实机/HIL验证完成。
- **任务状态：** CH12-T003继续 `IN_PROGRESS`。

## 电气诊断公开入口输入校验（2026-11-23）

- **任务ID：** CH12-T003（联合移动轴/电流环模型静态接口加固）
- **审查发现：** `electrical_diagnostics()` 是可直接调用的公开方法，但此前有限值检查主要位于 `derivative()`。外部直接传入NaN/Inf电流命令或非有限状态时，可能得到包含非有限值的诊断字典。
- **处理：** 在 `electrical_diagnostics()` 入口拒绝非有限电流命令，并复用 `pack(state)` 校验状态坐标维数及全部状态值有限性；PI/电压限幅和动力学方程保持不变。
- **资源测试：** 新增非有限电流命令（NaN、正/负Inf）与非有限状态两项用例，测试方法由16项增至18项；**未执行**。
- **交付文件：** 求解器、资源测试、联合移动负载/电流环专题、资源README、ASSET-INDEX、CH12 TaskPlan和本历史文件。
- **验证边界：** 仅完成静态审查、实现与测试编写；没有资源测试运行、数值仿真、能量平衡、步长收敛、驱动器参数辨识或HIL/实机验证。CH12-T003继续 `IN_PROGRESS`。


## 电气诊断公开入口校验切片CI验收（2026-11-23）

- **内容提交：** `8fcbbbbd2aae2c2974ffda64782ff19b8a6042d3`（公开 `electrical_diagnostics()` 的有限值/状态输入校验，新增两项资源测试）。
- **GitHub Actions：** [Run 45155665754](https://github.com/rexyll/cnc-knowledge/actions/runs/45155665754) success；仓库既有单元测试步骤和 strict knowledge lint 步骤均成功。
- **资源测试边界：** 文件包含18个测试方法，但该次CI没有运行 `resouces/` 下的18项资源级测试；它们仍未执行。
- **验证边界：** CI成功不等于电气诊断资源测试已运行，也不代表数值仿真、步长收敛、能量平衡、硬件过流保护或HIL/实机验证完成。
- **任务状态：** CH12-T003继续 `IN_PROGRESS`。


## 联合移动轴—电流环数值验证协议归档（2026-11-23）

- **任务ID：** CH12-T003（联合移动轴/电流环模型数值验证准备）
- **新增文档：** `docs/12-control-and-machining-algorithms/gantry-joint-drive-numerical-verification-protocol.md`。
- **新增资源：** `resouces/12-control-and-machining-algorithms/gantry-joint-drive-verification-matrix.csv`；定义RK4-01～04、ENE-01～03、PATH-01共8项验证工况，其中7项为 `NOT_RUN`，PATH-01因规定轨迹降阶参考积分器尚未实现而为 `BLOCKED`。
- **协议要点：** 混合单位状态误差使用分量绝对/相对容差归一化；RK4用四档细化和观测阶数判定；能量预算显式包含实际端电压功率、铜耗、结构阻尼、路径摩擦和外部广义力功率；规定轨迹约束参考模型单独计算路径约束广义力与约束功。
- **验证边界：** 仅完成协议、矩阵和索引归档；没有执行18项资源测试，没有运行数值仿真或能量平衡测试，没有建立真实机床参数。CH12-T003继续 `IN_PROGRESS`。


## 联合求解器数值验证协议CI验收及格式修正（2026-11-23）

- **协议/矩阵内容提交：** `020be49b00ea9ba3436718d691d19dcc7625e638`。
- **GitHub Actions：** [Run 45157109891](https://github.com/rexyll/cnc-knowledge/actions/runs/45157109891) success；仓库原有单元测试和 strict knowledge lint 步骤均成功。
- **格式修正：** 回读发现协议内22处行内代码标记包含多余反斜杠，现已修正为标准Markdown代码标记。
- **验收边界：** 该CI未执行18项资源测试；验证矩阵7项为 `NOT_RUN`、PATH-01为 `BLOCKED`。无新增数值仿真或实机/HIL结果；CH12-T003继续 `IN_PROGRESS`。


## 规定路径降阶参考积分器实现（2026-11-23）

- **任务ID：** CH12-T003（联合移动轴/电流环模型数值验证准备）
- **实现内容：** 新增 `prescribed_path_derivative()`，将完整质量矩阵按 `q/s` 分块，计算规定 `s_ddot_ref` 下的结构加速度和路径约束广义力；新增 `simulate_prescribed_path()`，以 `[q, q_dot, i, x_i]` 为降阶积分状态，规定路径由确定性回调在每个RK4阶段给出 `(s_ref, sdot_ref, sddot_ref)`。
- **返回契约：** 时间向量、与自由求解器排列一致的完整状态矩阵，以及输出网格上的约束反力 `lambda`；初始状态路径位置/速度须与路径回调一致。约束力以 `+e_s * lambda` 加在系统方程右端。
- **资源测试：** 新增6项回归测试，覆盖自由方程零反力一致性、约束力符号、路径输出、路径初值/有限值校验与回调状态隔离；资源测试由18项增至24项，**未执行**。
- **验证矩阵：** PATH-01 已从 `BLOCKED` 更新为 `NOT_RUN`，但尚无自由轴/规定路径数值对照、步长收敛或约束功结果。
- **交付文件：** 求解器、资源测试、数值验证协议、验证矩阵、联合移动负载专题、资源README、ASSET-INDEX、CH12 TaskPlan和本历史文件。
- **验收边界：** 仅完成代码实现、静态方程推导和测试用例编写；未执行资源测试或数值仿真，不代表真实伺服轴跟踪能力、驱动器推力能力、硬限位/接触或HIL/实机验证。CH12-T003继续 `IN_PROGRESS`。
