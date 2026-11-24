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
- 新增3项ENE资源测试定义：噪声底值/来源契约；高于噪声底同号单调序列与噪声/跨零/非单调/限幅门控；manifest噪声底来源完整性。ENE资源测试38项、求解器35项、PATH-01 39项，共112项资源测试均未执行。
- 配置schema升至3，manifest schema升至5；配置模板中的噪声底及来源字段全部留空。仅完成代码/文档/测试定义与静态检查；未执行任何resouces测试、ENE积分或数值仿真。验证矩阵保持NOT_RUN，CH12-T003保持IN_PROGRESS。

- **仓库CI（ENE残差噪声底与经验阶数门控实现）：** 实现提交 `e2e10e867e5166d507c30c6d0d6b6a2f2c250cc8` 对应 [Run 45377309267](https://github.com/rexyll/cnc-knowledge/actions/runs/45377309267) success；`Knowledge structure and data quality` job中的既有单元测试与repository knowledge lint均成功。该CI不执行 `resouces/` 下112项资源测试，也不运行ENE积分。CH12-T003保持 `IN_PROGRESS`，ENE验证矩阵继续 `NOT_RUN`。
