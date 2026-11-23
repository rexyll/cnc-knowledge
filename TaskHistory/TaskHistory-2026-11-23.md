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


## 规定路径降阶参考积分器切片CI验收（2026-11-23）

- **代码提交：** `a5c97addf57aa25a88e2f0e45565de371d8883bc`；GitHub Actions [Run 45160152219](https://github.com/rexyll/cnc-knowledge/actions/runs/45160152219) success。
- **文档/矩阵提交：** `ecb4639d44e6012ed42ad187c789fe8df2479466`；GitHub Actions [Run 45160363257](https://github.com/rexyll/cnc-knowledge/actions/runs/45160363257) success。
- **CI边界：** 两轮均为仓库 `Knowledge Quality` 工作流成功；CI不执行 `resouces/` 下的24项求解器资源测试。
- **实现状态：** 规定路径降阶参考积分器已具备，PATH-01由 `BLOCKED` 变为 `NOT_RUN`；验证矩阵8项全部 `NOT_RUN`。
- **未完成验证：** 24项资源测试、RK4步长收敛、机电能量预算、自由轴/规定路径数值对照、约束反力与约束功的独立数值验证均未执行；没有真实机床参数辨识或HIL/实机结果。
- **任务状态：** CH12-T003继续 `IN_PROGRESS`。


## PATH-01工况和结果归档模板（2026-11-23）

- **任务ID：** CH12-T003（自由轴/规定路径对照验证准备）
- **工况定义：** 固定解析五次静止—静止参考轨迹 s_ref=s0+(s1-s0)*(10u^3-15u^4+6u^5)，并使用解析速度、加速度；起止位置、持续时间、模型参数、初始结构状态、外环控制增益、外载、四档步长和全部分量容差由实际执行配置填写。
- **输入一致性：** 自由与规定路径模型共用同一确定性电流命令回调定义和外部广义力回调；规定路径侧跟踪误差按约束状态自然变化，理想路径所需额外力 lambda 独立记录，不混入外力或电机电流。
- **比较指标：** 自由路径位置/速度误差、结构坐标逐分量归一化差、移动负载点差、约束力峰值/RMS、约束功，以及包含 lambda*sdot_ref 的受约束能量残差。未预先给出工程阈值时只能描述性报告。
- **新增模板：** gantry-joint-drive-path-comparison-config-template.json、gantry-joint-drive-path-comparison-timeseries-template.csv、gantry-joint-drive-path-comparison-summary-template.csv；均为空白模板，不含默认机床参数或数值结果。
- **状态：** PATH-01维持 NOT_RUN；本切片未执行资源测试或数值仿真。另将协议中“复跑全部18项”的旧表述纠正为24项。


## PATH-01配置与结果模板归档CI验收及链接修正（2026-11-23）

- **模板提交：** `d9aca86ce0b8a40a65aecdb22a68a2d9898b6eea`；[Run 45169802109](https://github.com/rexyll/cnc-knowledge/actions/runs/45169802109) success。
- **首轮文档提交：** `2853347c3a841c21710318636cfa7d81d2eb955f`；[Run 45169914782](https://github.com/rexyll/cnc-knowledge/actions/runs/45169914782) failure。日志定位为6条Markdown相对链接的目录上跳层级过多，越过仓库根目录；仓库既有单元测试5/5成功，strict lint有6个链接错误。
- **修复提交：** `0fc31fa0589ce0c8358d2c6e2291817fe1a947a4`，将6条链接由 `../../../resouces/...` 修正为 `../../resouces/...`。
- **修复后CI：** [Run 45170044496](https://github.com/rexyll/cnc-knowledge/actions/runs/45170044496) success；仓库既有单元测试5/5成功，strict knowledge lint PASS。
- **验收边界：** PATH-01 JSON配置模板及两份CSV模板均为占位模板，机械/电气参数、外环增益、积分步长、容差和验收阈值未填写，未产生数值数据。PATH-01保持 `NOT_RUN`；CI不运行 `resouces/` 下24项资源测试。
- **任务状态：** CH12-T003继续 `IN_PROGRESS`。


## PATH-01独立对照运行器与结果生成工具（2026-11-23）

- **新增运行器：** resouces/12-control-and-machining-algorithms/gantry_joint_drive_path_comparison.py；读取完成的PATH-01 JSON配置，自动建立自由轴与理想规定路径对照，执行h/h2/h4/h8四档RK4，并生成时序CSV、汇总CSV和JSON运行manifest。
- **控制/载荷接口：** 共用确定性PD电流参考回调、显式常值前馈电流和常值五维外部广义力；不执行JSON任意代码。未启用前馈或无外载时必须显式配置零值。路径端点限制在几何跨度内，外力分量顺序固定。
- **数值指标：** 逐分量容差归一化、自由路径位置/速度误差、结构坐标差、负载点差、约束力峰值/RMS、Simpson/梯形约束功，以及两种模型独立步长收敛筛查。
- **能量账本：** 包含实际限幅端电压功率、铜耗、结构阻尼、路径摩擦、外部广义力功率、(Kf-Ke)*i*ell_dot互易常数不匹配项；受约束模型另计lambda*sdot_ref。
- **新增测试：** test_gantry_joint_drive_path_comparison.py含7项纯函数资源测试；与原求解器24项合计31项资源测试。均未执行，仓库CI不运行resouces/资源测试。
- **限制：** v1只支持常值前馈和常值广义力，不支持任意控制回调代码；工程阈值不完整时输出COMPLETED_REPORT_ONLY，而不是PASS。运行器与测试尚未运行，PATH-01仍为NOT_RUN，无数值结果、实机参数或HIL结论。


## PATH-01运行器与文档CI验收（2026-11-23）

- **运行器/测试/配置模板提交：** `076ab8290f9bf772e9551b7d50b80dcb17a93a00`；[Run 45171976920](https://github.com/rexyll/cnc-knowledge/actions/runs/45171976920) success。
- **资源README、ASSET-INDEX与专题正文提交：** `0ce4a852aa7c78971b83912705603f1941ca625d`；[Run 45172483718](https://github.com/rexyll/cnc-knowledge/actions/runs/45172483718) success。
- **协议/矩阵/TaskPlan提交：** `0632571f46c4be7c80a22e24677cf3530e14e896`；[Run 45172703500](https://github.com/rexyll/cnc-knowledge/actions/runs/45172703500) success。
- **运行器实施历史提交：** `260c5d82ffec4ffff40a033d8c18d867c5e2576d`；[Run 45172789219](https://github.com/rexyll/cnc-knowledge/actions/runs/45172789219) success。
- **CI内容：** 上述仓库Knowledge Quality工作流均成功，既有单元测试5/5通过，strict knowledge lint成功。该CI不运行资源目录下的求解器/运行器代码或31项资源测试。
- **静态核对：** 路径时序/汇总模板字段分别为65/56列，与运行器字段名称及顺序一致；配置的模型参数、初始值、前馈、外载、容差、能量尺度和验收阈值仍保留待填写值。
- **验收边界：** PATH-01运行器与新增7项辅助测试尚未执行；原24项求解器资源测试仍未执行；无步长收敛、能量残差、路径误差、约束反力或实机/HIL数值结果。PATH-01保持 `NOT_RUN`，CH12-T003继续 `IN_PROGRESS`。


## PATH-01运行器CI补录与最终状态（2026-11-23）

- **计划/历史补录前提交：** `574c5e8c1fdf3e04e4aba6b9c1341f744ffa9736`；[Run 45172904724](https://github.com/rexyll/cnc-knowledge/actions/runs/45172904724) success。
- **仓库CI：** 既有单元测试5/5通过；strict knowledge lint PASS。此结果只覆盖仓库Knowledge Quality工作流，不运行resouces下的Python资源脚本与资源测试。
- **静态核对：** PATH-01运行器与两份CSV模板字段数/顺序一致（时序65列、汇总56列）；配置模板所有机床/合成参数、控制参数、初始值、绝对/相对容差、能量尺度和工程验收阈值均保持待填写。
- **资源测试状态：** 求解器24项和运行器7项，共31项，均未执行。无PATH-01数值轨迹、步长收敛、能量残差、路径误差、约束力/约束功结果。
- **验证矩阵：** RK4/ENE/PATH共8项全部 `NOT_RUN`，0项 `BLOCKED`。CH12-T003保持 `IN_PROGRESS`。


## PATH-01限幅感知收敛适用域与阶段诊断（2026-11-23）

- **任务ID：** CH12-T003（联合移动轴/电流环模型数值验证准备）。
- **审查发现：** PATH-01原有四档步长收敛筛查仅分析误差递减和观测阶数；未区分电流参考值限幅与PI电压饱和，也未检查限幅是否在内部RK4阶段发生。输出网格采样会漏掉网格之间的瞬时限幅切换。
- **处理：** 运行器在自由轴和规定路径模型的每次电流命令回调中调用电气诊断并累计两类限幅标志，同时统计任一限幅激活次数；以每积分步四个回调核对预期RK4阶段数。规定路径积分器在最后额外执行的一次末端诊断从阶段计数剔除。
- **时序CSV：** 新增自由/规定路径请求电流命令、裁剪后电流参考值、电流参考限幅标志和电压饱和标志，反映输出采样点快照。
- **汇总CSV：** 新增预期/实际RK4阶段数、两类限幅计数、任一限幅激活阶段数/比例、阶段数匹配，以及 `smooth_unsaturated_regime`。两种模型必须都完整计数且所有阶段均未触发限幅，才被标记为光滑未限幅工况。
- **状态门控：** 数值收敛筛查失败仍记 `FAIL`；收敛筛查通过但出现任一限幅阶段或阶段数不匹配，限定为 `COMPLETED_REPORT_ONLY`，不再允许常规光滑工况的工程 `PASS`。该诊断不代表电流状态硬限幅或硬件过流保护。
- **新增测试：** 运行器资源测试新增3项，现为10项；与求解器24项合计34项。所有资源测试均未执行。
- **同步归档：** `gantry_joint_drive_path_comparison.py`、`test_gantry_joint_drive_path_comparison.py`、两份CSV模板、资源README、ASSET-INDEX、数值验证协议5.3节、专题正文7.6.12节与本TaskPlan。
- **验证边界：** 本次完成代码/测试/文档写入与静态审查；时序CSV模板/运行器均为73列，汇总CSV模板/运行器均为70列，字段名称与顺序一致；运行器测试方法数10项。提交 `7ceda93f04edb8ffffd7ce6c365d16d1db868816` 对应GitHub Actions [Run 45181996783](https://github.com/rexyll/cnc-knowledge/actions/runs/45181996783) success，既有仓库单元测试5/5通过，strict knowledge lint success。该CI不运行 `resouces/` 下34项资源测试；这些资源测试仍未执行，PATH-01模拟也未执行。矩阵8项仍全部 `NOT_RUN`，CH12-T003保持 `IN_PROGRESS`。


## PATH-01全细化序列限幅门控修正（2026-11-23）

- **二次审查发现：** 上一轮新增的 `smooth_unsaturated_regime` 是逐档标志，但最终验收门控只读取最细 `h/8`。收敛阶数由 `h`、`h/2`、`h/4`、`h/8` 共同构造；若粗档触发限幅而最细档未触发，原门控仍可能允许对含非光滑切换的观测阶给出工程 `PASS`。
- **处理：** 新增 `all_refinements_smooth_unsaturated_regime`，必须四档的自由轴和规定路径模型均有正确RK4阶段回调计数，且所有阶段无电流参考限幅、电压饱和，才可作为光滑工况通过工程验收的前置条件。逐档标志继续保留，manifest顶层标志改为全序列聚合。
- **回归用例：** 新增两项纯函数测试，验证粗档/任一细化档限幅仍返回 `COMPLETED_REPORT_ONLY`，以及收敛筛查失败优先返回 `FAIL`。运行器测试现为12项；与求解器24项合计36项，全部未执行。
- **同步文件：** 运行器、运行器测试、汇总CSV模板、资源README、ASSET-INDEX、数值验证协议5.4节、专题正文7.6.13节、TaskPlan与本历史。
- **CI验收：** 提交 `95cd8b149d8d628f8ab59064aee33ec110d249cc` 对应 [Run 45183631562](https://github.com/rexyll/cnc-knowledge/actions/runs/45183631562) success；单元测试与strict knowledge lint均成功。PATH-01模拟和全部36项资源测试均未执行，矩阵8项仍 `NOT_RUN`，CH12-T003继续 `IN_PROGRESS`。


## PATH-01电流参考限幅输出口径统一（2026-11-23）

- **复核发现：** RK4阶段计数使用裁剪后参考值与请求指令是否完全不同作为限幅标志，而输出网格能量账本曾采用 `1e-12` 绝对容差比较；小于该阈值的真实裁剪可能被时序CSV漏记。
- **处理：** 新增 `_current_reference_was_limited()` 并同时用于阶段统计和时序能量账本，确保所有数据输出口径一致。
- **回归测试：** 新增相邻浮点数裁剪判断用例：`nextafter(1,+inf)` 被裁剪回1时仍标记为限幅；相同值不标记限幅。运行器辅助测试由12项增至13项；求解器24项不变，共37项资源测试未执行。
- **同步：** 运行器、测试、README、ASSET-INDEX、数值验证协议、专题正文、TaskPlan和本历史记录。
- **CI验收：** 提交 `a93a9dadf03be2d31d2a8d7124a602cb6a759cf4` 对应 [Run 45183921384](https://github.com/rexyll/cnc-knowledge/actions/runs/45183921384) success；单元测试与strict knowledge lint均成功。PATH-01仍 `NOT_RUN`，没有新增数值仿真或HIL结果。


## PATH-01来源文档/测量ID验证与manifest追溯（2026-11-23）

- **复核发现：** PATH-01模板的 `provenance.source_documents_or_measurement_ids` 未经过结构校验，具体ID也没有写入运行manifest；配置SHA虽然能唯一绑定配置文件，但不能直接在manifest中查看来源ID。
- **实现：** 新增 `_source_document_ids()`，要求JSON字符串数组、每项为去空白后非空字符串、标识不重复；空数组允许用于没有独立来源ID的明确合成夹具。`parameter_source` 也规范化首尾空白。manifest加入 `source_documents_or_measurement_ids` 同名字段。
- **测试：** 新增3项纯函数测试：拒绝非数组，拒绝空/非字符串元素，检查去空白与重复检测。运行器资源测试从13项增至16项；求解器24项不变，共40项均未执行。
- **文档：** 同步资源README、ASSET-INDEX、数值验证协议5.6节、专题正文7.6.15节、TaskPlan与本历史。
- **CI验收：** 提交 `35b25251666da1ab302f1da9b8771d6e1f58a39b` 对应 [Run 45184190958](https://github.com/rexyll/cnc-knowledge/actions/runs/45184190958) success；单元测试与strict knowledge lint均成功。PATH-01仍 `NOT_RUN`，没有新增运行结果或实机/HIL结论。


## PATH-01限幅/来源追溯阶段CI汇总（2026-11-23）

- **门控修正提交：** `95cd8b149d8d628f8ab59064aee33ec110d249cc`；[Run 45183631562](https://github.com/rexyll/cnc-knowledge/actions/runs/45183631562) success。
- **限幅标志口径提交：** `a93a9dadf03be2d31d2a8d7124a602cb6a759cf4`；[Run 45183921384](https://github.com/rexyll/cnc-knowledge/actions/runs/45183921384) success。
- **参数来源ID提交：** `35b25251666da1ab302f1da9b8771d6e1f58a39b`；[Run 45184190958](https://github.com/rexyll/cnc-knowledge/actions/runs/45184190958) success。
- **CI步骤：** 三轮均为仓库Knowledge Quality工作流成功，既有单元测试步骤与strict knowledge lint步骤均成功；不运行 `resouces/` 下的资源脚本和测试。
- **静态核对：** 时序CSV 73列、汇总CSV 71列，字段名及顺序分别与运行器一致；PATH-01运行器纯函数测试16项，求解器测试24项，共40项资源测试全部未执行。
- **状态：** PATH-01仍 `NOT_RUN`；验证矩阵8项全部 `NOT_RUN`；无新增数值仿真、能量残差或实机/HIL结果。CH12-T003继续 `IN_PROGRESS`。


## PATH-01电压饱和精度与能量残差梯形复核输出（2026-11-23）

- **审查发现一：** 求解器 `voltage_saturated` 使用1e-12绝对容差，可能漏掉电压上/下限外侧一个可表示浮点数的真实裁剪，导致RK4阶段限幅计数失真。
- **处理一：** 将标志改为 `voltage_V != raw_voltage_V`；新增求解器资源测试，一次覆盖正、负电压轨一ULP越界。
- **审查发现二：** PATH-01 `_energy_metrics()` 已返回梯形能量残差，但 `_step_metrics()` 没有把它放进摘要，导致计算结果没有被CSV/manifest持久化。
- **处理二：** 汇总字段和模板新增 `free_energy_residual_trapezoid_J`、`prescribed_energy_residual_trapezoid_J`；保留Simpson 1/3残差为主指标、梯形残差作为求积敏感性对照，不调整工程验收阈值。新增运行器资源测试验证两种求积结果。
- **资源测试：** 求解器25项、PATH-01运行器17项，总计42项，均未执行。
- **同步归档：** 求解器及测试、PATH-01运行器及测试、汇总模板、资源README、ASSET-INDEX、协议5.7节、专题正文7.6.16节、TaskPlan及本历史。
- **CI验收：** 内容提交 `5c24dcbcfeb8be4543dbef44dd81f333c63635d1` 对应 [Run 45188707292](https://github.com/rexyll/cnc-knowledge/actions/runs/45188707292) success，既有仓库单元测试步骤与strict knowledge lint步骤均成功；该CI不运行资源级测试。
- **静态核对：** 求解器25项、PATH-01辅助测试17项，共42项资源测试均未执行；汇总CSV模板与运行器均为73列，字段顺序一致。
- **验证边界：** PATH-01依旧 `NOT_RUN`，没有新的数值仿真或HIL结果。


### CH12-T003 PATH-01归档哈希绑定与发布中断恢复（2026-11-23）

- **审查发现：** PATH-01此前虽已记录配置、求解器与运行器SHA，但没有绑定最终时序/汇总CSV内容；CSV又直接写入最终路径，失败后可能留下无法区分完整/不完整的归档文件。
- **实现：** manifest升级到 schema_version 2，新增 output_artifacts，绑定时序CSV与汇总CSV的SHA-256、字节数、数据行数和列数。manifest自身不参与自哈希。
- **输出发布：** 所有文件先在输出目录内的临时子目录暂存；完整计算两份CSV哈希并序列化暂存manifest后，先移除旧manifest，再发布时序CSV、汇总CSV，最后发布新manifest。暂存阶段失败保持既有结果集不变；发布中断时manifest缺失，避免旧manifest错误背书部分新旧混合文件。
- **失败恢复：** 运行器发现CSV存在但manifest缺失时明确提示前次发布可能中断；检查目录后使用 --force 重跑完整输出集，或切换新目录。不能仅补写缺失文件，也不能把无manifest目录认作完整结果。
- **测试用例：** 新增3项PATH-01资源测试，覆盖SHA/大小/行列绑定、暂存失败保留旧归档、发布中断移除完成标记并支持整套重试。运行器测试20项、求解器测试25项，共45项，全部未执行。
- **同步文件：** PATH-01运行器、运行器测试、资源README、ASSET-INDEX、数值验证协议5.8节、专题正文7.6.17节、本章TaskPlan及本历史。
- **CI验收：** 内容提交 e063555b9b48104e29f83a25ed8e258f0bc1a734 对应 GitHub Actions [Run 45190354624](https://github.com/rexyll/cnc-knowledge/actions/runs/45190354624) success；仓库单元测试与strict knowledge lint步骤均成功。该CI不执行resouces资源测试。
- **静态核对：** PATH-01运行器测试方法20项、求解器测试25项，共45项资源测试均未执行；时序CSV和汇总CSV均为73列，字段名及顺序分别与模板一致。代码静态顺序检查确认发布步骤为旧manifest移除→时序CSV→汇总CSV→新manifest。
- **验证边界：** PATH-01仿真未执行，验证矩阵8项仍全部 NOT_RUN，无数值仿真或HIL结果；CH12-T003继续 IN_PROGRESS。


### CH12-T003 PATH-01独立归档校验与配置/CLI异常边界强化（2026-11-23）

- **缺口一：** manifest已保存两份CSV SHA-256，但此前没有独立验证命令；现在新增 `--verify-archive --output-dir`，无需原始配置文件，也不运行模型。
- **归档校验实现：** 核对manifest schema_version=2、case/status、固定文件名映射；逐个CSV核对SHA-256、字节数、表头、每行列数与数据行数，并防止manifest把校验目标改指向其他路径。输出状态 `VERIFIED` 并额外给出manifest记录的真实运行状态，避免把文件完整性误解为工程PASS。
- **输入配置修正：** schema_version只接受JSON整数1；明确要求来源ID数组存在，无独立ID使用 `[]`；非null profile ID不允许为空字符串/空白。
- **CLI/数值错误修正：** 捕获超大整数float转换溢出；拒绝非有限或超出平台范围的duration/base_step比值，并校验h/8细化后区间计数；CLI增加无配置归档校验模式，对已知I/O、JSON、配置、溢出及运行错误返回2并显示原因。
- **测试用例：** PATH-01运行器测试由20项增加到32项，新增覆盖归档正常验证、同大小文件篡改、manifest状态类型/路径覆盖、配置schema/source-ID要求、数值转换和细化索引边界、CLI verify与缺失配置错误。求解器测试25项保持不变，共57项资源级测试全部未执行。
- **同步文件：** PATH-01运行器及测试、资源README、ASSET-INDEX、数值验证协议5.9节、专题正文7.6.18节、本章TaskPlan与本历史。
- **CI验收：** 内容提交 `decf6ce69653d9fb82f5a88fc1c548becd4eb76f` 对应 [Run 45199785490](https://github.com/rexyll/cnc-knowledge/actions/runs/45199785490) success；既有仓库单元测试步骤与strict knowledge lint步骤均成功。Knowledge Quality CI不执行 `resouces/` 资源测试。
- **验证边界：** 本轮没有执行PATH-01仿真或57项资源测试；验证矩阵8项仍全部 `NOT_RUN`，没有生成轨迹/收敛/能量数值或HIL证据。CH12-T003保持 `IN_PROGRESS`。

### CH12-T003 联合质量矩阵尺度均衡求解与能量账本极端值防护（2026-11-23）

- **审查发现：** 自由路径和规定路径动力学分别用通用 np.linalg.solve 求解理论SPD质量矩阵；广义坐标含m/rad/模态坐标，原始量纲和等效惯量可能造成对角量级差异。能量/功率由有限输入计算后仍可能溢出为Inf/NaN，原异常可能延迟到求积或JSON写入。
- **质量矩阵处理：** 新增对角尺度归一化 _diagonal_scaled_symmetric_matrix() 和 _scaled_spd_solve()，构造单位对角对称矩阵、对RHS同步缩放、执行Cholesky并恢复解；自由路径5×5和规定路径4×4结构方程共用该实现。加入模型接口 scaled_joint_mass_matrix_condition_number(q, s)，返回归一化矩阵特征值比；该量不是原始混合单位矩阵条件数，不设通用PASS门限，也未接入验收门控。
- **极端值处理：** 质量矩阵/右端项、电气诊断、机械与磁场储能、逐样本能量账本、Simpson/梯形积分和能量指标均检查非有限结果；梯形求积增加输入形状、有限性和时间单调性校验，能量账本错误包含样本序号与时间上下文。
- **回归用例：** 求解器资源测试增加5项、PATH-01运行器测试增加2项；现分别30项和34项，共64项，全部未执行。时序/汇总CSV字段结构没有改变。
- **内容提交：** 7420db400200fd2722445c35a56859f8802bb68e；GitHub Actions [Run 45203091144](https://github.com/rexyll/cnc-knowledge/actions/runs/45203091144) success（仓库既有单元测试与strict knowledge lint均成功）；该CI不运行64项资源测试。
- **验证边界：** 本切片无模型参数、实际条件数、数值求解误差或能量残差结果；未执行PATH-01仿真，验证矩阵8项仍全部 NOT_RUN，CH12-T003继续 IN_PROGRESS。
### CH12-T003数值求解/能量边界文档同步与CI验收（2026-11-23）

- **文档提交：** f544a08ee49bc40490e2451ddec6f85617e748e3；更新数值验证协议5.10、专题正文7.6.19、资源README/ASSET-INDEX及TaskPlan/TaskHistory，补充尺度均衡方程、归一化条件指标解释限制、能量溢出边界和64项资源测试未执行的状态。
- **CI验收：** GitHub Actions [Run 45203542953](https://github.com/rexyll/cnc-knowledge/actions/runs/45203542953) success；仓库既有单元测试与strict knowledge lint均成功。该CI不运行resouces目录下64项资源测试。
- **静态状态：** 求解器测试30项、PATH-01运行器测试34项，共64项均未执行；没有实际工况条件数、求解误差、能量残差或仿真结果。PATH-01与矩阵8项继续 NOT_RUN，CH12-T003保持 IN_PROGRESS。


### CH12-T003 M0构造期正定性预检尺度一致性（2026-11-23）

- **审查发现：** 质量矩阵实际求解已做对角尺度归一化，但模型初始化仍对原始混合单位M0使用np.linalg.eigvalsh的最小特征值判定正定；当平移与转角/模态惯量数量级差异大时，该预检可能受矩阵尺度影响，与后续求解器不一致。
- **修正：** M0构造期校验统一采用对角归一化并在归一化矩阵上执行Cholesky；仅针对M0严格正定约束，不修改D0/K0半正定定义。
- **测试：** 新增两项资源级回归用例，验证跨多个数量级的合法SPD矩阵能够通过初始化，以及缩放后仍然不定的矩阵会被拒绝。求解器资源测试32项、PATH-01运行器34项，合计66项，全部未执行。
- **协议同步：** 数值验证协议5.11、专题正文7.6.20、资源README、ASSET-INDEX、TaskPlan和本历史均已更新；第6节执行清单当前总数修正为66项。
- **验证边界：** 本轮不执行资源测试或仿真，无新增条件数/求解误差/能量残差结果；PATH-01和验证矩阵8项仍NOT_RUN。


### CH12-T003 M0尺度一致性切片CI验收（2026-11-23）

- **代码提交：** `039d9f7b53dcfb9ed57beb1d92947fa5b64c829f`；GitHub Actions [Run 45206627681](https://github.com/rexyll/cnc-knowledge/actions/runs/45206627681) success，仓库既有单元测试步骤及strict knowledge lint均成功。
- **文档提交：** `2a35bc405a0276cf2685bc350ef2f3587c14e285`；GitHub Actions [Run 45206901778](https://github.com/rexyll/cnc-knowledge/actions/runs/45206901778) success，仓库既有单元测试步骤及strict knowledge lint均成功。
- **状态边界：** 两次CI均不覆盖 `resouces/` 下资源测试；目前求解器32项、PATH-01运行器34项，共66项仍全部未执行。PATH-01与矩阵8项继续NOT_RUN，CH12-T003保持IN_PROGRESS。
