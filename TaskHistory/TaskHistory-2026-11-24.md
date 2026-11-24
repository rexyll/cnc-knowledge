# TaskHistory — 2026-11-24

## CH12-T003 阻尼耗散与外部广义力功率符号审查

- **结构阻尼：** 动力学方程使用 D0*q_dot 作为阻尼广义力，账本扣除 q_dot.T @ D0 @ q_dot。模型校验 D0 对称半正定，因此该耗散功率理论上非负。
- **轴向摩擦：** 动力学方程使用 b*s_dot + Fc*tanh(s_dot/v_eps)，账本扣除摩擦力与速度的乘积。b、Fc 非负且 v_eps 正，路径反向时摩擦力与速度同时反号，功率仍非负；零速度时为零。
- **外部广义力：** 自由和规定路径动力学均将 Q_ext 加到广义力右端。账本以 Q_ext.T @ [q_dot,s_dot] 计算外部功率；其符号由力与速度方向决定，不应当作耗散项。
- **新增测试：** PATH-01运行器新增2项资源测试，覆盖正反向结构/轴摩擦耗散非负，以及外部广义力功率正/负/零。运行器39项、求解器32项，共71项资源测试。
- **测试提交：** `451ca951ff54b8eb9377f09e44f08abb8fa9ecb4`。
- **CI：** GitHub Actions [Run 45307608288](https://github.com/rexyll/cnc-knowledge/actions/runs/45307608288) success；仓库Knowledge Quality工作流通过。该CI不执行 `resouces/` 下资源测试。
- **本轮边界：** 资源测试仍未执行；未执行ENE-02/03积分或PATH-01仿真，没有新增数值能量残差或HIL/实机结论。验证矩阵8项继续 `NOT_RUN`，CH12-T003保持 `IN_PROGRESS`。


## CH12-T003 ENE-01～03独立瞬时能量率基准

- 方法：新增中心差分方向导数基准。先由状态方程求 f(x)，再计算储能函数 E(x±epsilon*f(x))，估计 dE/dt；参考功率由电气端口、机械阻尼/摩擦本构、外部广义力虚功显式构造，不调用PATH-01能量账本函数。
- ENE-01：在 Kf=Ke、无阻尼/摩擦/外力条件下，检查机电端口功率相消，剩余储能率为铜耗。
- ENE-02：增加结构阻尼与轴向平滑摩擦，核对耗散项。
- ENE-03：增加五维外部广义力，核对有符号外部功率。
- 独立性边界：该方法独立于运行器账本实现，但仍使用同一求解器状态方程与储能函数，属于局部能量率一致性核验，不是独立物理模型或实测。
- 资源测试：求解器35项、PATH-01运行器39项，共74项；全部未执行。
- 代码提交/CI：371b22c402ab54dd7f579fc5fceb629dd2b51142；GitHub Actions Run 45310814342 success。该CI不执行 resouces/ 资源测试。
- 验证边界：ENE-01～03数值积分及PATH-01四级步长收敛仍未运行，验证矩阵继续 NOT_RUN，CH12-T003保持 IN_PROGRESS。


## CH12-T003 ENE瞬时能量率方向导数步长敏感性加固

- 将ENE-01～03中心差分方向导数由单一步长改为1e-5 s与5e-6 s双步长估计，并以二阶Richardson外推 (4*D(h/2)-D(h))/3 作为主观测值。
- 同时保留细步长估计并独立与解析功率预算比较，避免仅依赖一个任意差分尺度。
- 此改动只增强局部差分截断误差控制，不代表时间积分收敛或物理独立验证。
- 资源测试仍为求解器35项、PATH-01运行器39项，共74项，均未执行；ENE积分、RK4细化、PATH-01均NOT_RUN。

- **提交/CI：** `17448b6e7d82df433a74fa186c1761abd5b7ae0c`；GitHub Actions [Run 45316278632](https://github.com/rexyll/cnc-knowledge/actions/runs/45316278632) success，Knowledge structure and data quality job成功。CI不执行 `resouces/` 下74项资源测试。


## CH12-T003 ENE多步积分能量闭合判据（2026-11-24）

- 新增协议5.15与专题7.6.24，明确ENE-01～03四档积分每档独立计算储能变化、净功率积分、J单位残差与归一化残差。
- 固定归一化定义：rho_E=abs(R_E)/max(E_scale, integral(abs(P_net)), E_floor)；E_scale/E_floor必须运行前声明且四档一致。Simpson为主积分，梯形为敏感性对照。
- 功率项：ENE-01端电压输入功减铜耗；ENE-02再扣结构阻尼与路径摩擦；ENE-03再加有符号外部广义力。要求分项归档，不以命令电压替代限幅后端电压。
- 判读：最细两档满足预声明阈值才可称达到闭合容差；跨零或噪声地板主导时不强行给出残差阶数，不机械套用状态误差p>=3。
- 本轮仅定义协议，没有运行资源测试或数值积分；74项资源测试、RK4、ENE、PATH-01仍未完成。

- **仓库CI：** 文档/矩阵更新提交 `d505bf2b485627d71c654ea5a99a8ba1a5559e8d` 对应 [Run 45317927852](https://github.com/rexyll/cnc-knowledge/actions/runs/45317927852) success；`Knowledge structure and data quality` job成功。该工作流不执行 `resouces/` 下74项资源测试，也不运行ENE积分。


## CH12-T003 ENE独立积分运行器初版（2026-11-24）

- 新增 `gantry_joint_drive_energy_closure.py`，按ENE-01/02/03单用例配置分别执行h、h/2、h/4、h/8四档自由路径RK4积分。
- 能量功率账本独立于PATH-01的 `_energy_ledger()` / `_energy_metrics()`，逐点记录实际限幅后端电压、端口功率、铜耗、结构阻尼、轴摩擦、外部广义力功率、机电失配项、储能和净功率；每档输出Simpson主残差与梯形敏感性残差。
- 配置模板无任何机床默认数值；要求参数来源、Kf=Ke、ENE用例约束和预声明归一化尺度/地板/阈值。未填写阈值只产生COMPLETED_REPORT_ONLY；限幅阶段阻止常规光滑未限幅PASS。
- 增加4项功率账本资源测试。资源测试总计78项：求解器35、PATH-01运行器39、ENE运行器4；全部未执行。未运行任何ENE积分。
- 独立性边界：仅功率账本与积分核算独立，状态方程和储能函数仍复用同一联合模型；不代表独立物理模型、实机或HIL验证。


- **仓库CI：** 运行器代码提交 `e345fa7c26311ff1029d0b0cc6660ea31e26fac7` 对应 [Run 45320569139](https://github.com/rexyll/cnc-knowledge/actions/runs/45320569139) success；文档/索引/矩阵提交 `d0fd57d95a4a66d6077d5c02e74ca54b4ac22264` 对应 [Run 45320847709](https://github.com/rexyll/cnc-knowledge/actions/runs/45320847709) success，job为Knowledge structure and data quality。CI未执行78项资源测试或ENE积分。


## CH12-T003 ENE运行器静态审查与配置边界修正

- 修正ENE用例退化：ENE-02要求非零D0、轴黏性和库仑摩擦；ENE-03要求上述耗散配置并至少一个非零外部广义力分量。
- 强制外力顺序字段精确匹配 [Q_x_common,Q_yaw,Q_bending,Q_torsion,Q_s]。
- 因配置尚无预声明残差噪声地板/稳定性门控，经验残差阶数固定不报告，避免对跨零或噪声主导残差误判。
- 归档语义明确为staging后逐文件原子替换、manifest最后发布；不宣称三文件整体事务原子性。
- 新增4项配置契约资源测试，ENE运行器资源测试8项；总计82项资源测试（求解器35、PATH-01 39、ENE 8）均未执行。ENE积分未执行，验证矩阵保持NOT_RUN，CH12-T003保持IN_PROGRESS。
- **仓库CI：** `ce86d8d75afca8bc00497f80377e16bc52e17a3e` 对应 [Run 45326460371](https://github.com/rexyll/cnc-knowledge/actions/runs/45326460371) success，单元测试与repository knowledge lint成功；CI不执行 `resouces/` 下82项资源测试，也不运行ENE积分。


## CH12-T003 ENE归档语义校验加固

- `--verify-archive` 新增manifest语义、RK4阶段统计、CSV数值有限性、布尔字段、四档时序网格、汇总/manifest验收状态一致性校验。
- 新增4项归档语义资源测试定义；ENE资源测试12项，资源测试总计86项，全部未执行。未执行ENE积分。

- 静态复核补充：归档校验同时约束电流参考/电压限幅计数与任一限幅计数的集合关系，并强制经验残差阶数列保持空值。

- **仓库CI：** `d00d0a6fc5274b2f1399903a7551952989b1cd56` 对应 [Run 45333058677](https://github.com/rexyll/cnc-knowledge/actions/runs/45333058677) success；单元测试与repository knowledge lint成功。CI不执行 `resouces/` 下86项资源测试，也不运行ENE积分。


## CH12-T003 ENE运行器资源边界与积分完整性复核（2026-11-24）

- 资源上限：原区间数只限制在平台整数范围，不能防止内存型轨迹/逐行CSV归档出现不可执行的巨大工作量。新增四档总采样点上限50,000，配置端和manifest验证端同口径检查；超限在积分前拒绝。
- 有限性：每个状态向量严格要求12维且所有分量有限；每档对储能变化、所有分项功积分、净功率/绝对净功率积分、Simpson/梯形残差和归一化残差逐项检查。
- 阶段门控：RK4实际阶段回调数不匹配理论值属于执行完整性失败，状态改为FAIL；阶段数完整但发生限幅仍为COMPLETED_REPORT_ONLY。归档校验同步采用同一判读。
- 测试定义：新增3项ENE资源测试（超大采样规模拒绝、阶段计数异常、非有限状态拒绝）；ENE测试15项，求解器35项、PATH-01运行器39项，共89项资源测试，全部未执行。
- 验证边界：未执行任何resouces/测试或ENE积分；Knowledge Quality CI不覆盖这些资源测试。CH12-T003保持IN_PROGRESS，验证矩阵维持NOT_RUN。


- **仓库CI（ENE资源/完整性门控修正）：** 提交 `211c2923d5134bec6019af5898ed09e392a6182c` 对应 [Run 45338509123](https://github.com/rexyll/cnc-knowledge/actions/runs/45338509123) success；`Knowledge structure and data quality` job中的单元测试与repository knowledge lint均成功。该CI不执行 `resouces/` 下89项资源测试，也不运行ENE积分。


## CH12-T003 ENE功率采样与RK4阶段接口一致性审查（2026-11-24）

- **阶段采样：** 静态核对自由路径RK4每区间k1/k2/k3/k4四次命令回调，阶段时刻为t、t+h/2、t+h/2、t+h。ENE限幅计数采样这些阶段状态；能量/功率账本在N+1个输出节点采样，二者语义独立。
- **电气接口：** `tracked()` 与 `derivative()` 对同一阶段状态及常值命令使用同一电气诊断函数；账本的限幅后端电压与RL电流导数一致，端口输入功率为v*i。当前实现仅支持常值电流前馈，未发现阶段状态/电压接口错位。
- **测试定义：** 新增1项回归测试，检查两区间8次阶段回调的时刻与状态，以及端电压、电流导数、端口功率一致性。ENE测试16项、求解器35项、PATH-01运行器39项，总计90项资源测试全部未执行。
- **验证边界：** 未运行资源测试或ENE积分；仓库Knowledge Quality CI不覆盖 `resouces/` 测试。CH12-T003保持 `IN_PROGRESS`，ENE验证矩阵保持 `NOT_RUN`。


- **仓库CI（ENE RK4阶段/功率接口回归测试定义）：** 提交 `da8aa1b107b02e98d6e457ac1228ff3912768bd6` 对应 [Run 45341856376](https://github.com/rexyll/cnc-knowledge/actions/runs/45341856376) success；Knowledge structure and data quality job中的单元测试与repository knowledge lint均成功。该CI不执行 `resouces/` 下90项资源测试，也不运行ENE积分。


## CH12-T003 ENE多尺度残差与分项功贡献诊断

- 静态审查确认：ENE运行器已经逐项积分端口输入、铜耗、结构阻尼、轴摩擦、外部广义力及机电失配功，但此前汇总缺少分项绝对贡献率和残差多尺度比率。
- 新增六项绝对贡献率，以分项绝对功积分之和与预声明能量地板的较大者为分母；新增残差相对 E_scale、净功绝对积分和分项绝对积分尺度的比率，以及Simpson/梯形净功积分差。
- 归档校验根据summary分项积分、manifest能量尺度/地板和残差重算上述指标，拒绝字段语义不一致的归档。
- 新增3项资源测试定义：分项贡献率和残差尺度、零分母地板保护、Simpson/梯形差的敏感性语义。ENE资源测试19项，求解器35项、PATH-01运行器39项，共93项资源测试。
- 误差解释边界：当前四档细化同时改变RK4状态轨迹与功率求积网格，残差不能独立归因；Simpson/梯形差不是严格误差上界。固定参考轨迹功率求积细化尚未实现。
- 本轮只做代码/文档/测试定义和静态审查；未执行 resouces/ 资源测试或ENE积分。Knowledge Quality CI不覆盖资源测试。CH12-T003保持 IN_PROGRESS，ENE验证矩阵保持 NOT_RUN。


- **仓库CI：** `544221f583457cd17039380c7800ce86c32ed235` 对应 GitHub Actions [Run 45345390717](https://github.com/rexyll/cnc-knowledge/actions/runs/45345390717) success；Knowledge structure and data quality job成功。该CI不执行 `resouces/` 下93项资源测试，也不运行ENE积分。


## CH12-T003 固定最细轨迹的嵌套功率求积诊断

- 研究方案：利用四档区间数 (N,2N,4N,8N) 的嵌套结构，冻结 (h/8) 状态轨迹端点功率样本，按8/4/2/1步幅抽取四套节点，分别执行Simpson净功与绝对净功积分；不增加ODE积分。
- 运行器新增固定轨迹求积积分、相对最细固定轨迹的求积差、同网格自身轨迹与固定轨迹的净功差、储能端点变化差、残差差。净功积分相对最细参考的变化满足“固定轨迹求积差 + 同网格状态轨迹差”的代数分解。
- 归档校验器从最细档时序CSV重新计算诊断字段并逐项核对summary，避免仅依赖哈希而放过字段语义篡改。
- 新增3项资源测试定义：嵌套节点/代数分解、非嵌套区间拒绝、非有限样本拒绝。ENE资源测试22项、求解器35项、PATH-01 39项，总计96项资源测试均未执行。
- 局限：参考轨迹仍是h/8 RK4轨迹，端点功率采样不能捕获步内变化；诊断不构成严格误差上界或物理验证。未增加更细参考积分，也未运行ENE积分。
- 本轮未执行任何 `resouces/` 资源测试或数值积分；Knowledge Quality CI不覆盖资源测试。ENE验证矩阵仍为 `NOT_RUN`，CH12-T003保持 `IN_PROGRESS`。


- **仓库CI：** `0d644cf15407a9221dc498eb23b9b9c44d5b3b3e` 对应 GitHub Actions [Run 45352911112](https://github.com/rexyll/cnc-knowledge/actions/runs/45352911112) success；Knowledge structure and data quality job成功。该CI不执行 `resouces/` 下96项资源测试，也不运行ENE积分。

- **仓库CI：** 阶段功率快照实现与归档语义加固提交 `40c65ac9eaa593effa584896f13d6af146ed7f59` 对应 GitHub Actions [Run 45357974206](https://github.com/rexyll/cnc-knowledge/actions/runs/45357974206) success；Knowledge structure and data quality job中的既有单元测试与repository knowledge lint均成功。该CI不执行 `resouces/` 下99项资源测试，也不运行ENE积分。

**新增执行切片（2026-11-24）：ENE h/16参考轨迹共同节点对照。** 当前四档步长细化同时改变状态轨迹与功率求积网格，h/8固定轨迹只能提供条件式求积敏感性。本轮为每个ENE配置增加同一求解器的独立h/16完整参考积分，并在共同节点按16/8/4/2步幅与四档主轨迹比较。参考轨迹增加独立端点CSV；h/16的k1/k2/k3/k4阶段快照并入阶段功率CSV。诊断内容包括h/16自身完整网格能量闭合指标、四个主档网格上的参考功/绝对功/残差，以及主轨迹相对参考的净功积分、储能变化、能量残差差值；12个状态分量逐项最大绝对差/RMS差和净功率最大绝对差/RMS差。混合单位状态分量不合成为综合范数。

资源预算改为端点总样本 `31N+5`、RK4阶段总数 `124N`，分别受50,000和200,000限制，基础区间数最大1612且仍须为偶数。归档manifest schema升为2，新增h/16端点文件元数据、阶段报告及共同节点诊断；归档验证器从参考和主轨迹CSV重算指标。h/16参考复用相同状态方程/参数/命令负载，不是精确解或独立物理模型；参考限幅单独报告，所有h/16参考诊断均不改变原四档主PASS判据。新增4项ENE测试定义，ENE 29项、求解器35项、PATH-01 39项，共103项资源测试全部未执行。ENE积分未执行，CH12-T003保持IN_PROGRESS。



- **仓库CI（h/16参考轨迹与共同节点误差对照）：** 实现提交 `ff2a9e7cb66c6dc72286ce3806b2f8b9e4eb9063` 对应 [Run 45365141994](https://github.com/rexyll/cnc-knowledge/actions/runs/45365141994) success；`Knowledge structure and data quality` job中的既有单元测试与repository knowledge lint均成功。该CI不执行 `resouces/` 下103项资源测试，也不运行ENE积分。CH12-T003保持 `IN_PROGRESS`。

- **仓库CI（h/16文档记录与计数清理）：** 提交 `93231b47e7d7f848a73a5b2d0373f776cc4033cc` 对应 [Run 45365432150](https://github.com/rexyll/cnc-knowledge/actions/runs/45365432150) success；`Knowledge structure and data quality` job中的既有单元测试与repository knowledge lint均成功。该CI不执行 `resouces/` 下103项资源测试，也不运行ENE积分。CH12-T003保持 `IN_PROGRESS`。

- **仓库CI（h/16文档记录收尾）：** 提交 `ffc728dd72a85b1297b26bf3f0bcf63ed175216d` 对应 [Run 45365579897](https://github.com/rexyll/cnc-knowledge/actions/runs/45365579897) success；`Knowledge structure and data quality` job中的既有单元测试与repository knowledge lint均成功。该CI不执行 `resouces/` 下103项资源测试，也不运行ENE积分。CH12-T003保持 `IN_PROGRESS`。

**追加执行切片（2026-11-24）：ENE相邻细化轨迹共同节点对照。** 在同一求解器h/16数值参考的基础上增加四组相邻层级对照：h/h2、h2/h4、h4/h8、h8/h16。所有细/粗轨迹都按每对较粗轨迹的公共节点进行比较；将细轨迹按每两个节点抽样，再计算12维状态逐分量最大绝对差/RMS差、净功率最大绝对差/RMS差、两轨迹在粗网格的Simpson净功积分差、储能变化差和能量残差差。每组还带两条路径均未限幅的标志。

新增诊断不会合并混合单位状态误差，不推导经验阶数、误差上界或PASS；它只提供相邻细化的原始轨迹差异，并将功率求积统一到较粗网格，以免混入不同节点求积影响。若任一轨迹发生限幅，不作经典光滑RK4阶数解释。Manifest schema升级为3，新增相邻细化诊断并由归档验证器重算。新增3项ENE测试定义，ENE32项、求解器35项、PATH-01 39项，总计106项资源测试均未执行；ENE积分未执行，CH12-T003保持IN_PROGRESS。

- **仓库CI（相邻细化轨迹共同节点诊断）：** 实现提交 `102d473bfe01750ff447a3c4689cd86e882c6c42` 对应 [Run 45366368115](https://github.com/rexyll/cnc-knowledge/actions/runs/45366368115) success；`Knowledge structure and data quality` job中的既有单元测试与repository knowledge lint均成功。该CI不执行 `resouces/` 下106项资源测试，也不运行ENE积分。CH12-T003保持 `IN_PROGRESS`。

- **仓库CI（相邻细化轨迹文档同步）：** 提交 `353c51aceffecd3a12fda25dc6f2ca0b9ac6bbf4` 对应 [Run 45366448936](https://github.com/rexyll/cnc-knowledge/actions/runs/45366448936) success；`Knowledge structure and data quality` job中的既有单元测试与repository knowledge lint均成功。该CI不执行 `resouces/` 下106项资源测试，也不运行ENE积分。

- **仓库CI（相邻轨迹测试夹具修正）：** 提交 `775e7f37197552dc115f6bc8e45f3288d82c570d` 对应 [Run 45366553735](https://github.com/rexyll/cnc-knowledge/actions/runs/45366553735) success；该改动仅修正资源测试夹具的层级偏移构造。CI不执行 `resouces/` 下106项资源测试，也不运行ENE积分。CH12-T003保持 `IN_PROGRESS`。

- **仓库CI（相邻细化诊断版本沿革修正）：** 提交 `db166a00a4dbc7f460b50099fc0b9ee3d3b00f83` 对应 [Run 45366754776](https://github.com/rexyll/cnc-knowledge/actions/runs/45366754776) success；`Knowledge structure and data quality` job中的既有单元测试与repository knowledge lint均成功。该CI不执行 `resouces/` 下106项资源测试，也不运行ENE积分。CH12-T003保持 `IN_PROGRESS`。

**追加执行切片（2026-11-24）：ENE逐分量状态特征尺度。** 相邻轨迹差异的12个状态分量具有不同单位，现要求配置schema v2显式提供每个状态字段的正/有限特征尺度、来源说明和至少一个唯一来源ID。尺度应在运行前基于机床规格、轴行程/速度包络、驱动/控制器设计或批准工况包络确定；不得从本次轨迹观测结果反向拟合。对PI积分器电压状态，需要控制器设计/调试包络专门支撑。

每对相邻轨迹继续保留原始单位下的最大绝对差/RMS差，并新增按12个固定尺度逐项归一化后的最大差/RMS差数组。无量纲结果仅帮助比较各分量相对于其工程特征幅值的大小，不是验收容差、安全限值或PASS门槛；禁止将12维混合单位结果进一步合并为综合分数。Manifest升级至schema v4，记录12个尺度、来源信息、顺序及单位，归档验证时重新计算这些数值。新增3项资源测试定义；ENE35项、求解器35项、PATH-01 39项，总计109项资源测试均未执行；ENE积分未执行，CH12-T003保持IN_PROGRESS。

- **仓库CI（有来源的状态特征尺度）：** 实现提交 `2bfa53fc9c8bfc14a3849748581d934dd4220152` 对应 [Run 45372572329](https://github.com/rexyll/cnc-knowledge/actions/runs/45372572329) success；`Knowledge structure and data quality` job中的既有单元测试与repository knowledge lint均成功。该CI不执行 `resouces/` 下109项资源测试，也不运行ENE积分。CH12-T003保持 `IN_PROGRESS`。

- **仓库CI（状态特征尺度文档同步）：** 文档提交 `ac8eb8c8c8f63fb0ff0ca5fc3d194b35ee263bf3` 对应 [Run 45372659983](https://github.com/rexyll/cnc-knowledge/actions/runs/45372659983) success；`Knowledge structure and data quality` job中的既有单元测试与repository knowledge lint均成功。该CI不执行 `resouces/` 下109项资源测试，也不运行ENE积分。CH12-T003保持 `IN_PROGRESS`。

- **仓库CI（状态特征尺度文档最终同步）：** 提交 `bdd0c36bd20da8db270ecac8b45ef7b081885143` 对应 [Run 45372748872](https://github.com/rexyll/cnc-knowledge/actions/runs/45372748872) success；`Knowledge structure and data quality` job中的既有单元测试与repository knowledge lint均成功。该CI不执行 `resouces/` 下109项资源测试，也不运行ENE积分。CH12-T003保持 `IN_PROGRESS`。

- **仓库CI（状态特征尺度最终文档记录）：** 文档提交 `8afb88f0c9e868f2cb20c1149eb734ec7405a3ee` 对应 [Run 45372844907](https://github.com/rexyll/cnc-knowledge/actions/runs/45372844907) success；`Knowledge structure and data quality` job中的既有单元测试与repository knowledge lint均成功。该CI不执行 `resouces/` 下109项资源测试，也不运行ENE积分。CH12-T003保持 `IN_PROGRESS`。


## CH12-T003 ENE残差数值噪声底与经验阶数门控（2026-11-24）

- ENE运行器新增预运行残差噪声底契约：要求正有限J值、方法、来源说明及唯一来源ID。噪声底针对储能端点差、净功Simpson求积和残差相减的完整数值路径；要求来源材料说明浮点格式、操作/累加路径、求积节点与权重、数值范围/抵消和执行环境。明确与能量归一化分母地板分离；不允许仅用machine epsilon乘能量尺度或本次仿真残差倒推。
- 对h、h/2、h/4、h/8、h/16五层残差实施条件门控：五档阶段完整无任何限幅、残差均高于噪声底、同号且绝对值严格递减时才输出四组相邻经验指数；否则输出具体门控状态并抑制全部指数。
- 前三个经验指数分别写入h/2、h/4、h/8 summary行；h/8→h/16指数与五层残差/门控写入manifest。归档校验从summary残差、h/16参考残差、限幅报告与预声明噪声底重新计算门控和指数。
- 新增3项ENE资源测试定义：噪声底值/来源契约；高于噪声底同号单调序列与噪声/跨零/非单调/限幅门控；manifest噪声底来源完整性。ENE资源测试38项、求解器35项、PATH-01 39项，共113项资源测试均未执行。
- 配置schema升至3，manifest schema升至5；配置模板中的噪声底及来源字段全部留空。仅完成代码/文档/测试定义与静态检查；未执行任何resouces测试、ENE积分或数值仿真。验证矩阵保持NOT_RUN，CH12-T003保持IN_PROGRESS。

- **仓库CI（ENE残差噪声底与经验阶数门控实现）：** 实现提交 `e2e10e867e5166d507c30c6d0d6b6a2f2c250cc8` 对应 [Run 45377309267](https://github.com/rexyll/cnc-knowledge/actions/runs/45377309267) success；`Knowledge structure and data quality` job中的既有单元测试与repository knowledge lint均成功。该CI不执行 `resouces/` 下113项资源测试，也不运行ENE积分。CH12-T003保持 `IN_PROGRESS`，ENE验证矩阵继续 `NOT_RUN`。


ENE归档null一致性补充（2026-11-24）：runner比较器支持严格JSON null匹配；新增1项ENE测试定义。ENE39项、求解器35项、PATH-01 39项，共113项资源测试仍未执行。

- **仓库CI（噪声底门控文档记录同步）：** 提交 `7bb780bb6f28d598ee2f379a913ab341021a36cf` 对应 [Run 45377481837](https://github.com/rexyll/cnc-knowledge/actions/runs/45377481837) success；`Knowledge structure and data quality` job中的既有单元测试与repository knowledge lint均成功。该CI不执行 `resouces/` 下112项资源测试，也不运行ENE积分。
- **仓库CI（门控阶数null归档比较修正）：** 实现/文档修正提交 `554ac5116d87c43c5bddab60b8ae8cc310e1920e` 对应 [Run 45377757508](https://github.com/rexyll/cnc-knowledge/actions/runs/45377757508) success；`Knowledge structure and data quality` job中的既有单元测试与repository knowledge lint均成功。该CI不执行 `resouces/` 下113项资源测试，也不运行ENE积分。CH12-T003保持 `IN_PROGRESS`，ENE验证矩阵保持 `NOT_RUN`。



## CH12-T003 ENE残差噪声底的可复算前向误差预算（2026-11-24）

- 对当前实现做算术路径核对：`composite_simpson_13()` 从首个时间差取h，对奇数与偶数内部样本分别调用`np.sum`，再以端点项、4/2权重、三次外层加法以及h/3缩放形成净功；储能残差随后执行端点储能相减和储能变化减净功。
- ENE配置schema升级为4、manifest schema升级为6。增加误差预算输入：最大储能/最大净功率包络、储能/净功率单次函数评估误差界、RK4状态舍入传播对能量/功率输出的影响界、时间栅格积分影响界，以及binary64算术/无溢出和无subnormal前提确认。
- runner自动以binary64 (u=2^{-53}) 及 (gamma_k=ku/(1-ku)) 计算，并在运行时检查 `sys.float_info.rounds==1`最细h/16奇/偶分组求和、外层加法、Simpson乘除、端点能量差、最终残差减法与正数预算汇总保护；把自动最低界写入manifest，并要求用户预声明噪声底不低于该值。归档验证器重算并逐项比对输入预算与报告。
- 重要边界：代码只自动推导当前Simpson/减法链路的浮点执行项；外部给出的函数评估、RK4状态传播、工况包络和时间栅格影响界必须由独立分析/资料支撑。该自动核算不证明外部界、平台libm精度或浮点运行假设真实成立；不涵盖RK4截断误差、模型参数不确定性和物理模型误差。
- 新增3项ENE资源测试定义（预算计算/网格尺度且包含manifest小量级数字精确比较、算术假设或预算缺项拒绝、噪声底低于预算界拒绝）。ENE资源测试定义42项，求解器35项、PATH-01 39项，总计116项资源测试仍全部未执行；ENE积分/仿真未执行，验证矩阵NOT_RUN，CH12-T003保持IN_PROGRESS。

- 归档预算报告和残差阶数诊断改用递归精确JSON数值比较，避免1e-12通用绝对容差掩盖小量级舍入界差异；该检查已包含在自动预算资源测试中（ENE42项）。

- **仓库CI（ENE预算运行时舍入模式门控）：** 实现修正提交 `b4d70c68009cabc058383deae9e8644117ab5670` 对应 [Run 45381515561](https://github.com/rexyll/cnc-knowledge/actions/runs/45381515561) success；`Knowledge structure and data quality` job中的既有单元测试与repository knowledge lint均成功。该CI不执行 `resouces/` 下116项资源测试，也不运行ENE积分或数值仿真。ENE-01/02/03验证矩阵继续 `NOT_RUN`，CH12-T003保持 `IN_PROGRESS`。

## CH12资源级测试接入GitHub Actions（2026-11-24）

- **目标：** 让CH12核心数值资源测试在CI中实际执行，避免仅凭仓库知识结构检查推断求解器、路径比较和能量闭合模块可运行。
- **工作流变更：** 更新 `.github/workflows/knowledge-quality.yml`，保留原 `Knowledge structure and data quality` job，新增独立 `CH12 numerical resource tests` job；使用Python 3.12，安装 `numpy>=1.26,<3`，执行 `python -m unittest discover -s resouces/12-control-and-machining-algorithms -p 'test_gantry_joint_drive_*.py' -v`。
- **覆盖范围：** 当前匹配三组资源测试文件：联合求解器35项、PATH-01运行器39项、ENE能量闭合运行器42项，共116项。该Job不执行ENE积分、RK4步长收敛或PATH-01数值对照；这些仍需使用完整且来源可追溯的配置单独运行。
- **分支与提交：** 仅更新 `main`；提交 `556d603ae3543cd455b6b8060b76e6fcfd937beb`（`ci(ch12): run numerical resource tests`）。
- **验收状态：** 已核对工作流差异、测试文件命名和NumPy依赖。当前GitHub连接可读取提交，但可用的提交状态接口对该SHA返回空状态列表，不能据此确认Actions Job成功或失败；当前运行环境也无法解析github.com，未在本地克隆仓库执行测试。因此116项测试结果仍为待CI核验，不得标记通过。
- **遗留事项：** 核验本次Actions运行的两个Job结果；如资源测试失败，按具体失败定位修正并复跑。通过资源测试后，再依据数值验证协议准备经来源确认的参数/误差预算，分开运行ENE-01～03、RK4和PATH-01；没有工程阈值或真实设备数据时，只允许标注合成回归或 `COMPLETED_REPORT_ONLY`，不得生成实机通过结论。
- **实际完成时间：** 2026-11-24T19:13:15+08:00（GitHub提交时间，Asia/Shanghai）
- **交付文件：** `.github/workflows/knowledge-quality.yml`；本记录文件。
- **验收证据：** GitHub提交 [556d603ae3543cd455b6b8060b76e6fcfd937beb](https://github.com/rexyll/cnc-knowledge/commit/556d603ae3543cd455b6b8060b76e6fcfd937beb)；CI运行结果尚待核验。
## CH12资源级测试首次执行、失败归因与复验通过（2026-11-24）

- **首次资源CI：** 新增工作流后，Run [45382162709](https://github.com/rexyll/cnc-knowledge/actions/runs/45382162709) 与后续文档提交 Run [45382486802](https://github.com/rexyll/cnc-knowledge/actions/runs/45382486802) 均执行116项资源测试，结果为2 FAIL、2 ERROR；两个Run的原有仓库质量Job均success。
- **失败归因与修正范围：**
  1. 混合尺度SPD解测试构造的物理坐标解与`1e-6/1/1e6`尺度造成右端项舍入后小分量信息不可恢复；测试改为在对角均衡坐标中构造均衡解，保留原高动态范围与严格数值断言。
  2. 零速度RL测试把零电流指令误当作零PI电压；由于PI比例项非零，实际电压为负。测试改为命令等于当前电流，显式确认端电压为零后检查纯RL衰减。
  3. RK4阶段时间测试在最后一个区间仍访问“下一步k1”，造成索引越界；改为只比较非末端区间的k4/k1，并单独核验最终k4与输出终点及阶段数量。
  4. ENE h/16拒绝测试的无效参考网格在构造夹具时先触发Simpson奇数区间异常；改为先生成有效夹具，再仅缩短参考网格，以直接验证“至少32个参考区间”的目标前置条件。
- **生产代码边界：** 本轮只修复两个资源测试文件，不修改联合求解器、ENE运行器或PATH-01生产实现；不降低求解器数值断言、不改变动力学方程或运行器验收门控。
- **修正提交：** 求解器资源测试 `6862981116ee0eefdc9cbb18049d604df9b32e4a`；ENE资源测试 `ce0ea5a68234efc1d325b3ee78822f4f548ee40b`。均直接提交到`main`。
- **最终CI：** GitHub Actions [Run 45384191326](https://github.com/rexyll/cnc-knowledge/actions/runs/45384191326) success。`Knowledge structure and data quality`与`CH12 numerical resource tests`两个Job均success。
- **测试结果：** Python 3.12.16、NumPy 2.5.5；116/116通过，其中ENE 42/42、PATH-01 39/39、联合求解器35/35；日志为`Ran 116 tests in 0.082s`、`OK`。原仓库单元测试与strict knowledge lint同样通过。
- **验收边界：** 该结果仅证明当前资源单元测试在该CI环境中通过。没有运行ENE-01/02/03积分、RK4-01～04实际步长收敛或PATH-01自由/规定轨迹数值对照；验证矩阵这些条目继续`NOT_RUN`。没有真实设备参数、HIL或实机验证结论。
- **实际完成时间：** 2026-11-24T19:26:36+08:00（GitHub Actions完成日志，Asia/Shanghai）
- **交付文件：** `.github/workflows/knowledge-quality.yml`；`resouces/12-control-and-machining-algorithms/test_gantry_joint_drive_solver.py`；`resouces/12-control-and-machining-algorithms/test_gantry_joint_drive_energy_closure.py`。
- **所在分支：** `main`
## CH12-T003 RK4-01低速平滑工况四级步长收敛筛查（2026-11-24）

- **新增方法来源：** SRC-000372，Mississippi State University数学系《Numerical Analysis using Matlab and Maple》Chapter 5 §5.3.2，记录经典RK4更新及局部/全局误差阶数；该来源仅支持通用数值方法，不证明机床对象参数或物理有效性。
- **新增实现：** `resouces/12-control-and-machining-algorithms/gantry_joint_drive_rk4_screen.py`；配置`gantry-joint-drive-rk4-01-synthetic-config.json`；资源回归测试`test_gantry_joint_drive_rk4_screen.py`（5项）。CI已将该测试计入CH12资源测试，并在单测通过后运行RK4-01及上传结果。
- **参数边界：** 完全合成SYNTHETIC_FIXTURE，不包含真实机床/驱动器参数；工况为低速平滑耦合状态、恒定电流参考和零外部广义力。时长0.2 s，步长h/h2/h4/h8分别0.005/0.0025/0.00125/0.000625 s，对应区间数40/80/160/320。12个状态特征尺度预先声明用于不同单位归一化，不是工程容差或机床限值。
- **CI首次调用问题：** Run [45385287387](https://github.com/rexyll/cnc-knowledge/actions/runs/45385287387)中的121项资源测试通过，但RK4运行步骤因YAML shell换行参数未正确传递`--output-dir`而退出2；不是模型积分失败。已将CLI调用改为单行命令，后续Run完成实际积分。
- **实际结果：** Run [45385379794](https://github.com/rexyll/cnc-knowledge/actions/runs/45385379794) success；两个Job均success，资源测试121/121通过（含solver35、PATH-01 39、ENE42、RK4 runner 5），仓库单元测试和strict knowledge lint通过。四档状态有限、阶段回调计数与理论值匹配，电流参考限幅及电压饱和计数均为0。
- **相邻差异：** 归一化RMS差（h/h2、h2/h4、h4/h8）=2.4669535331394685e-05、9.795609168099331e-07、4.832443317361703e-08，严格下降；两组可计算观测阶数=4.654451518041637、4.341310498009402，均超过预设数值筛查下限3.0。该有限层级比值不证明渐近误差界。
- **状态与边界：** RK4-01=`COMPLETED_REPORT_ONLY`，没有设置或检验任何应用级容差/定位精度指标；非机床性能认证。RK4-02～04、ENE-01～03积分和PATH-01自由/规定路径对照继续`NOT_RUN`。真实参数辨识、台架、HIL和实机均未进行。
- **归档：** 结果包`generated/rk4-01-synthetic/`内四个结果文件（604行时序CSV、4行步长汇总CSV、3组相邻差异CSV、运行manifest）已由CI归档到main；manifest记录各CSV的SHA-256/尺寸/行列数。CI上传的临时Artifact ZIP为Artifact ID `14915203518`，保留14天；外层ZIP SHA-256=`6bfd6a2c51b05fe38f8abd5ef526110985e62e0e6c2d991eb3921bc6451b1c02`。
- **代码/文档提交：** SRC-000372 `c27dc76e4c6a4c2a36645fc77f848ff703de3f89`；runner `09976e335f9922cc32e9fd573093e143bfd49af4`；fixture `1ed5c0ed33466ec7438c1bb4042c18514c1a6357`；tests `7a8ddfbf881f12c2e17cbe14ae5f56c48323081d`；workflow调用更正 `8fde470984328eec30c004f401fd70798cbe4d6b`；矩阵 `50c7bdf36ecad9211746356593c0bfb56ecd2087`；协议 `4fbd8cdbf813c1dcf65fbfc2ffe35bbea31247ae`；资源README `86978b201850c4b4d411114e8d60ce1bf34a52db`；ASSET-INDEX `805b9e10f58ccd277bf19390200d0daf165138af`；自动结果归档工作流提交`6fe753ddf841df6af296be3ca8c3dfe70ac33e4c`；实际结果文件归档提交`4dd4737f06a14ec8157c4afc6008e1f143fecca1`（[commit](https://github.com/rexyll/cnc-knowledge/commit/4dd4737f06a14ec8157c4afc6008e1f143fecca1)）。Run [45385940534](https://github.com/rexyll/cnc-knowledge/actions/runs/45385940534)两个Job和Persist RK4-01 results to main步骤均success。
- **分支：** 全部操作只在`main`。
## CH12 RK4结果自动归档并发控制与最终CI复验（2026-11-24）

- **首次持久归档：** Run [45385940534](https://github.com/rexyll/cnc-knowledge/actions/runs/45385940534)两个Job及`Persist RK4-01 results to main`步骤success，四个结果文件由自动归档提交`4dd4737f06a14ec8157c4afc6008e1f143fecca1`写入`resouces/12-control-and-machining-algorithms/generated/rk4-01-synthetic/`。
- **并发问题：** 随后的多次文档提交并行触发Actions，不同运行同时尝试把各自生成的manifest/CSV推送到`main`；GitHub对非快进更新予以拒绝。检查日志确认资源测试、RK4-01积分、原仓库测试和strict lint均通过，失败仅在归档push竞争阶段。
- **修正：** `.github/workflows/knowledge-quality.yml`增加按ref串行的workflow concurrency；CH12 main push运行显式checkout最新`refs/heads/main`；新增归档输入SHA比较，只在配置、求解器、PATH支持或RK4运行器SHA变化时提交新结果。文档变动导致的重复计算不再重写相同模型结果；归档提交仍使用`[skip ci]`避免循环触发。新增GITHUB_OUTPUT换行格式修正。
- **修正提交：** 串行/按源码SHA门控 `894020eda8bb1da74c59c97a35422fcb30993e97`；GITHUB_OUTPUT分隔符修正 `5b67c82e148ff41bfec7b02f5ddd816e86e93d56`。
- **最终复验：** Run [45386401202](https://github.com/rexyll/cnc-knowledge/actions/runs/45386401202)和Run [45386439266](https://github.com/rexyll/cnc-knowledge/actions/runs/45386439266)均success；最近一次运行确认两个Job完成，121项资源测试通过、RK4-01数值筛查步骤通过、知识结构测试和Strict Lint通过。由于当前模型/配置/运行器SHA未变化，最近运行的持久化步骤按预期跳过，不产生重复提交。
- **main归档复核：** `generated/rk4-01-synthetic/`下存在`rk4-01-synthetic-timeseries.csv`、`rk4-01-level-summary.csv`、`rk4-01-adjacent-differences.csv`和`rk4-01-run-manifest.json`四个文件；matrix的RK4-01状态为`COMPLETED_REPORT_ONLY`，其他7项仍`NOT_RUN`。分支列表仅有`main`。
- **验收边界：** 该工作流证明测试与合成RK4筛查可重复执行，不能代替ENE误差预算/积分、RK4-02～04、PATH-01、真实参数辨识、台架/HIL/实机。


## CH12-T003 RK4-02正向自由路径工况四级步长收敛筛查（2026-11-24）

- **方法来源：** 新增SRC-000373，Modern Robotics / NxRLab Chapter 9 `QuinticTimeScaling.m`。用于五次静止—静止时间标度 (10τ^3-15τ^4+6τ^5) 及其端点速度/加速度约束。该源只支持通用运动学参考函数，不涉及CNC参数、伺服增益、限值或性能保证。
- **运行器扩展：** `gantry_joint_drive_rk4_screen.py`增加RK4-01～04工况ID白名单、多工况输出命名、五次路径/PD电流命令支持、参考轨迹和电流诊断时序字段、自由路径跟踪误差RMS/峰值/端点统计。运行器可分别处理恒定电流与五次参考PD两种连续时间命令。
- **RK4-02输入：** 全部为合成夹具；(s_0=0.72m)、(s_1=0.735m)、(T=0.2s)、初始(dot s=0)、(i_{ff}=0.08A)、(K_p=200A/m)、(K_d=30A·s/m)、零外部广义力。所有值不代表目标机床/驱动器设置。
- **首次回归问题：** Run [45387474002](https://github.com/rexyll/cnc-knowledge/actions/runs/45387474002)中RK4-02实际积分及数值筛查通过，但archive verifier仍读取固定的`rk4-01-run-manifest.json`，导致123项资源测试中的1项ERROR；非积分/收敛失败。修复提交`5940adb2e7e1d957205d1e24a26c422b019a2268`后，归档验证器按单一工况manifest文件读取。
- **CI复验：** GitHub Actions [Run 45387608094](https://github.com/rexyll/cnc-knowledge/actions/runs/45387608094)最终success。123/123项资源测试通过；RK4-01与RK4-02运行步骤success；归档push success；工作流最终success。
- **四档结果：** 区间数40/80/160/320，步长0.005/0.0025/0.00125/0.000625s，阶段评估次数160/320/640/1280。所有状态有限，阶段数匹配；电流参考限幅及电压饱和计数均为0。
- **收敛指标：** 相邻归一化RMS差（h/h2、h2/h4、h4/h8）为1.401131964624969e-04、6.750725089870764e-06、3.690347602559821e-07；两组有限层级观测阶数为4.375406561974051、4.193213850529427，均超过3.0数值筛查下限。
- **自由轴实际运动：** 最细档实际终点(s(T)=0.7254507489963524m)，相对初值净正向位移约0.00545074899635245m；参考终点0.735m，带符号端点误差为-0.0095492510036476m。路径误差RMS/峰值/端点均仅作为描述字段，未设置应用误差限，因此不宣称跟踪精度通过或完整到达目标终点。
- **结果归档：** 四个CSV/JSON文件由Actions提交至`generated/rk4-02-synthetic/`，归档提交`44a386005f8fb73835265c31492236c92b020d71`。时序604行/22列；层级汇总4行/23列；相邻差异3行/58列；manifest记录每份CSV的SHA-256、字节数、行数/列数及源码/config SHA。RK4-01亦由同一CI重新生成并更新输出列结构。
- **提交与边界：** runner与配置/测试/workflow提交`8c9c5ac79f3baf58b2d3ebfe0f1f39a3d60fc6e8`；归档校验修复提交`5940adb2e7e1d957205d1e24a26c422b019a2268`；结果归档提交`44a386005f8fb73835265c31492236c92b020d71`。全部仅在`main`。RK4-02为`COMPLETED_REPORT_ONLY`；RK4-03/04、ENE-01/02/03积分和PATH-01仍`NOT_RUN`；无真实设备参数、台架、HIL或实机验证，CH12-T003保持`IN_PROGRESS`。


## RK4-02路径误差诊断、来源schema修正与最终CI复验（2026-11-24）

- **路径误差诊断补强：** 对自由轴s(t)与参考路径s_ref(t)增加按各级实际输出栅格计算的误差RMS、绝对峰值和带符号端点误差。指标写入四行步长汇总CSV和manifest；不参与RK4数值收敛screen pass门控，不代替应用级路径容差。
- **h/8实际结果：** 参考路径误差RMS=0.007321842561068045m，峰值=0.010953049796999736m，端点误差=-0.009549251003647563m；实际终点0.7254507489963524m，参考终点0.735m。明确说明本模型未完整到达参考终点，且无应用容差可以判定跟踪精度合格。
- **首次schema lint问题：** 在提交`01b474a094df9f6fa10c9c92406b664d676cb486`后，Run [45388107854](https://github.com/rexyll/cnc-knowledge/actions/runs/45388107854)的CH12资源Job 123/123、RK4-01/02数值步骤和结果归档均success；全工作流因SRC-000373中的source_type/evidence_kind取值不属于仓库source schema枚举而失败。将来源分类改为允许的`other`和`official_documentation`。
- **最终复验：** 来源schema修正后的Run [45388234987](https://github.com/rexyll/cnc-knowledge/actions/runs/45388234987)全工作流success；资产索引状态补正提交`cce7a3024c2b85fc871c9e09b720426af6377e6b`对应Run [45388357235](https://github.com/rexyll/cnc-knowledge/actions/runs/45388357235)再次success。后者两Job均success，资源测试123/123、RK4-01/02运行、根仓库5项单测和strict knowledge lint全部通过；归档检查识别源码/配置输入未变化，跳过重复结果写入。
- **归档与状态：** 初始RK4-02四文件提交`44a386005f8fb73835265c31492236c92b020d71`；包含路径误差RMS/峰值/端点字段的最新结果提交`74812389cf5a8b73d1246265448004eb34788603`。资产索引与矩阵将RK4-01、RK4-02标记为`COMPLETED_REPORT_ONLY`；RK4-03/04、ENE-01/02/03和PATH-01仍`NOT_RUN`。所有提交仅在`main`；CH12-T003保持`IN_PROGRESS`。
