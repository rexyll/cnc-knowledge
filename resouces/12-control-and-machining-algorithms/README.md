# 12. 控制与加工算法 — 资源目录

本目录只存放归属于本章节的图片、动图、视频/音频（如适用）及有权保存的完整文档（Word、PDF、Excel、CSV等），以及本章相关的工程图、测量数据和附件。

## 归档规则

- 资源在正文中必须有引用，并在本章 `ASSET-INDEX.md`（建立后）中登记来源、作者/机构、取得或生成日期、版本、许可/授权状态、关联知识条目和说明。
- 优先保留原始文件；整理版、裁剪版、翻译版必须单独命名并注明与原件的关系。
- 对版权或保密状态不明、无权再分发的资料，不保存副本，仅记录可合法保留的元数据和官方链接。
- 不重复复制同一原始文件；跨章节使用时引用主归属章节的资源路径。

## 本轮新增CSV

- `periodic-disturbance-observer-validation-template.csv`：DOB名义模型/Q滤波、扰动符号、机械/电角度索引、摩擦/谐波/学习控制、基线和补偿后对照、限幅/副作用及SIL/HIL/台架/实机层级记录。
- 来源记录SRC-000323～SRC-000326：PMSM扰动观测电流控制研究、DOB Q滤波综述、鲁棒两自由度/参数观测器转矩波动研究和2026低速PMSM电流平均/谐波电压注入研究。论文实验平台与CNC直驱轴不完全相同，均为算法参考而非机床性能保证。


## 本轮新增合成仿真资产
- servo-dob-identification-simulation.py：Python 3.10+ / NumPy示例，包含惯量/摩擦最小二乘、刚体解析频响和DOB Q截止频率扫描；默认输出摘要，带 --include-raw-data 可输出8,000行合成辨识轨迹。
- servo-inertia-identification-summary.csv：合成轨迹的J/B/Tc/T0回归摘要。
- servo-rigid-body-frf-analytical-example.csv：单惯量刚体理论FRF，不是实测频响。
- dob-q-cutoff-sweep-synthetic.csv：含未建模转矩执行器滞后和命令延迟的DOB敏感性扫描。
- servo-dob-simulation-config.json：合成对象、采样、延迟、噪声、扰动和随机种子。
- 以上资产由项目维护过程于2026-11-22生成，属原创代码/合成数据，不含真实设备或客户数据；不代表实机性能或参数推荐。
- 新增SRC-000331～SRC-000332：DOB鲁棒稳定与未知相对阶次理论研究，数学条件依赖具体对象、因子化和控制结构。


## 本轮多工况模型验证仿真资产
- servo-multicondition-model-selection-simulation.py：Python 3.10+、NumPy、SciPy；生成多工况两/三惯量对象的H1 FRF、相干度、候选模型拟合、交叉验证和AICc模型选择。
- servo-multicondition-frf-model-selection.csv：12组工况/模型阶次拟合与留出验证指标。
- servo-multicondition-plant-configurations.csv：合成负载/冷热/多模态对象的参数配置。
- servo-directional-friction-fit-synthetic.csv：CW/CCW合成速度扫频的方向斜率/截距拟合；截距含摩擦和负载偏置。
- servo-multicondition-model-validation-config.json：参数、随机种子、频率划分、数据分类和限制。
- 可选H1全频点结果：脚本加参数 --include-raw-frf 会另生成340行servo-multicondition-h1-frf-synthetic.csv。
- 以上为项目原创仿真代码/合成数据，不含真实设备或客户数据；不生成数值闭环GM/PM/disk margin，也不代表实机性能或参数建议。
- 新增SRC-000333～SRC-000337，来源边界和适用限制见正文及source JSON记录。


## 本轮新增：多工况伺服级联控制与稳定裕度联合仿真
- servo-cascade-control-robustness-simulation.py：Python 3.10+、NumPy；生成四种两/三惯量合成对象、两组级联控制器和0/0.5/1.0 ms反馈延迟的SISO环路裕度扫描，以及含转矩限幅、反算抗积分饱和、柔性连接、摩擦和负载扰动的时域仿真。
- servo-cascade-control-simulation-config.json：采样/执行器、对象、控制器增益、限幅、扰动、延迟方法与限制。
- servo-cascade-loop-margin-envelope.csv：1.0 ms反馈延迟下8组对象/控制器SISO裕度摘要；脚本运行另生成全量24组扫描CSV，保留检测到的交越频率。
- servo-cascade-step-response-envelope.csv：1.0 ms反馈延迟下保守候选的8组阶跃响应摘要；脚本运行另生成全量24组时域记录。
- 运行：python servo-cascade-control-robustness-simulation.py --output-dir ./generated。脚本仅使用NumPy。
- 全部参数/数据为原创合成示例，不含真实机床/客户数据；非精确离散电机驱动模型、非MIMO/disk margin计算、非实机验证或安全证据。
- 新增SRC-000338～SRC-000340，分别记录抗积分饱和、延迟系统和经典SISO裕度官方文档入口。


## 本轮新增：前馈/滤波联合仿真及模型更正
- servo-cascade-control-robustness-simulation.py：升级为修正刚体惯量后的级联模型，加入速度/加速度前馈、42/70/94 Hz数字陷波、150 Hz速度反馈低通、参考模态纹波与外部负载扰动场景。
- servo-cascade-control-simulation-config.json：更新刚体总惯量/相对扭转约化惯量定义、正确PI增益、滤波器放置点、采样/限幅和仿真限制。
- servo-cascade-loop-margin-envelope.csv：更新32行（两套修正候选×四种对象×四种滤波组合）的SISO全部交越摘要；保留多交越序列，不以单值代替完整判读。
- servo-cascade-step-response-envelope.csv：更新8行修正惯量/两样本反馈延迟下的阶跃回归结果。
- servo-feedforward-filter-co-design.csv：新增56行，覆盖前馈与滤波组合、参考模态纹波、外部负载扰动，以及惯量/阻尼估计匹配和20%低估比较。
- 陷波采用预畸变双线性变换和SOS数字实现；仿真Python 3.10+、NumPy、SciPy。所有参数和数据为合成示例。
- 纠正此前将相对扭转约化惯量误当成刚体总惯量的错误；旧控制器增益及相关频域/阶跃结果已由修正版替代。详细推导见CH08/CH12新增正文。
- 新增SRC-000341～SRC-000345，记录自适应陷波、数字陷波离散化、数字运动控制、低通滞后等MathWorks官方方法入口。


## 本轮新增：双驱龙门 MIMO 合成仿真（2026-11-22）
- `gantry-mimo-simulation.py`：双驱两自由度等效柔性耦合对象、独立PD与差动同步P-D比较；Python 3.10+、NumPy、SciPy。
- `gantry-mimo-simulation-config.json`：合成对象、负载、刚度、阻尼、控制器和评估设置。
- `gantry-mimo-coupling-envelope.csv`：10组负载/耦合刚度组合摘要。
- `gantry-mimo-sync-controller-comparison.csv`：4种同步控制器方案对照。
- 运行脚本还会生成140行频率响应明细CSV；如需长期归档，将输出路径指定到本目录内的 `generated/` 子目录。
- 以上为原创代码和合成数据，不含真实机床、客户或厂商实测参数。最小返回差奇异值与灵敏度峰值是有限频率网格诊断，不是严格multiloop disk margin、mu分析或实机稳定性证明。


## 本轮新增：双驱龙门横梁模态、负载位置与采样延迟（2026-11-22）
- `gantry-modal-delay-study.py`：四广义坐标低阶假设模态、位置相关质量矩阵、ZOH离散对象、整数命令延迟闭环极点扫描、阶跃响应和采样小增益诊断。运行需要Python 3.10+、NumPy、SciPy。
- `gantry-modal-delay-study-config.json`：模型、负载工况、采样/延迟、同步控制候选和适用边界。
- `gantry-mimo-modal-position-envelope.csv`：27组冻结负载位置/质量下的广义模态摘要。
- `gantry-mimo-delay-robustness-envelope.csv`：4类控制器在0～6ms下的27工况离散极点稳定统计。
- `gantry-mimo-discrete-step-comparison.csv`：3组负载位置工况和3种控制器的1ms延迟阶跃比较。
- `gantry-mimo-discrete-small-gain-margin.csv`：中心负载下的采样返回差/灵敏度及全块输出乘性小增益指示量；并非disk margin。
- 完整756行 `gantry-mimo-discrete-delay-sweep.csv` 由脚本在运行输出目录生成，不作为当前仓库静态基线文件。
- 以上代码和CSV均为合成研究资产；负载位置使用冻结快照，不含连续移动质量项；没有有限元、HIL或实机验证。


## 2026-11-22 数值更正与连续移动负载
- 更正 gantry-modal-delay-study.py 中偏航/扭转阻尼交叉项的量纲错误，采用 D_psi_theta=0.03*sqrt(D_psi_psi*D_theta_theta)。原 delay-robustness、discrete-step 和 discrete-small-gain 三份CSV已重算覆盖，旧值作废。
- 新增 gantry-moving-load-study.py、配置JSON、18组模型比较CSV和123组方程核验CSV，包含 M(s(t))、Mdot、速度/加速度输运项、拉格朗日方程残差与质量矩阵正定性检查。全部为假设模态合成模型。
- 脚本默认生成汇总和方程核验记录；--include-timeseries 可生成7,500行选定工况时序；--disk-margin 可选调用 python-control 0.10.2 + Slycot AB13MD 计算两个反馈端口的采样 multiloop disk-margin 估计。缺少Slycot时不生成数值裕度；有限频率网格不构成全频率认证。
- 所有模型/代码/CSV均为项目原创合成数据，不包含真实机床参数。输出路径应位于 resouces/12-control-and-machining-algorithms/。


**代码验证边界（2026-11-22）：** 本目录中的移动负载比较CSV和方程核验CSV是参考计算结果；gantry-moving-load-study.py已入库，但本轮CI不执行资源脚本，精确提交版本尚待独立Python回归核验。请不要将CI通过误解为该脚本已执行。


## 移动负载数据指标口径补充（2026-11-22）
- `gantry-moving-load-model-comparison.csv` 中矩阵/广义项2-范数和广义质量矩阵特征值是按 q=[x(m), yaw(rad), bend(m), torsion(rad)] 计算的数值诊断，不应标注为单一kg、kg/s或N单位。
- `gantry-moving-load-equation-checks.csv` 的误差指标定义为 ||计算值-参考值||2 / max(1, ||参考值||2)，称为归一化偏差；当参考量范数小于1时不应称为严格相对误差。此次只修订字段名/语义，CSV数值不变。


## 本轮新增：龙门自由坐标—电流环联合求解器（2026-11-23）
- gantry_joint_drive_solver.py：NumPy实现联合坐标机械模型、移动负载惯性耦合、运输项、路径摩擦、重力势能梯度、执行器虚功投影及单轴等效RL/连续PI电流环；同时提供自由路径轴积分器和理想规定路径降阶参考积分器，后者计算路径约束广义力 `lambda`。
- test_gantry_joint_drive_solver.py：24项资源级unittest，覆盖原有联合质量矩阵/电气/能量/输入契约，以及规定路径分块方程与自由方程一致性、约束力符号、参考路径位置/速度输出、无效路径输入和回调快照隔离。
- 测试运行：python -m unittest discover -s resouces/12-control-and-machining-algorithms -p 'test_gantry_joint_drive_solver.py' -v
- 模型需要调用方提供M0/D0/K0、轴等效质量、电气参数、限幅与执行器位移映射；不提供伪装成通用机床参数的默认额定值。四坐标正弦几何仅是合成示例。
- `electrical_diagnostics()` 可被直接调用，因此在自身入口检查电流命令有限性，并复用 `pack(state)` 校验状态维数与有限性；这不是额外的硬件电流保护。
- 当前脚本和24项测试均尚未执行；仓库结构CI不执行资源测试。无数值仿真、参数辨识、硬限位/接触、完整PMSM dq、离散采样驱动或实机/HIL证据。

## 联合移动轴—电流环数值验证资产（2026-11-23）

- `gantry-joint-drive-numerical-verification-protocol.md`：步长收敛、机电能量预算和自由路径/规定轨迹对照协议；定义混合量纲状态归一化、观测阶数、功率项、约束反力和结果归档要求。
- `gantry-joint-drive-verification-matrix.csv`：7个RK4/能量工况和1个自由轴对照工况的未执行矩阵，逐项记录输入要求、参考方法、指标和验收规则。
- 当前矩阵8项均为 `NOT_RUN`；规定轨迹降阶参考积分器已实现，PATH-01 尚未进行数值对照。以上文件为验证计划，不含数值结果。

## PATH-01自由轴/规定轨迹对照模板（2026-11-23）

- gantry-joint-drive-path-comparison-config-template.json：空白参数与初值模板，定义解析五次静止—静止路径、相同电流命令/外力回调、四档步长和逐状态容差；机床参数、控制增益、阈值均留空。
- gantry-joint-drive-path-comparison-timeseries-template.csv：按统一输出时间栅格记录参考/自由/受约束路径、结构状态、移动负载点、约束力/功率及储能/功率账本的列定义。
- gantry-joint-drive-path-comparison-summary-template.csv：记录路径误差、混合单位结构差、负载点偏差、约束力峰值/RMS、约束功、能量残差、收敛阶数和验收结论的列定义。
- 三份文件均为空白模板；所有数值字段尚未填写，PATH-01保持 NOT_RUN，不可当作已执行仿真结果。


## PATH-01独立对照运行器（2026-11-23）

- gantry_joint_drive_path_comparison.py：读取已填写的PATH-01配置JSON，构造联合模型、解析五次静止—静止路径、共用确定性PD电流参考回调及恒定外部广义力；依次运行自由轴和规定路径模型的h、h/2、h/4、h/8四档细化。
- 时序CSV按四档网格合并记录路径/结构/负载点、电气端电压、各项功率和储能；汇总CSV记录逐分量归一化误差、自由轴路径误差、约束力峰值/RMS、约束功、能量残差和RK4观测阶数；同时生成包含配置/求解器/运行器SHA与运行环境的JSON manifest。
- 能量账本采用实际限幅端电压v*i、铜耗、结构阻尼、路径摩擦、外部广义力功率、(Kf-Ke)*i*ell_dot常数不匹配项；规定路径模型另加lambda*sdot_ref。PI积分器不计入物理储能。
- 运行器v1仅支持确定性PD电流参考回调、常值前馈电流和常值五维外部广义力；不用前馈或外力时也必须在配置中显式填写数值零，不支持从JSON执行任意代码/用户脚本回调。
- 首先复制配置模板为独立配置文件，填写全部参数和容差；feedforward_current_A、external_generalized_force_constant不可留空。复合Simpson 1/3要求基准区间数为偶数，路径端点必须位于0至几何跨度内。
- 运行命令（从仓库根目录执行，配置文件名为示例占位）：
  python resouces/12-control-and-machining-algorithms/gantry_joint_drive_path_comparison.py --config resouces/12-control-and-machining-algorithms/generated/path-01/config.json --output-dir resouces/12-control-and-machining-algorithms/generated/path-01/results

- 已归档结果独立校验（不需要配置文件，不运行模型）：
  python resouces/12-control-and-machining-algorithms/gantry_joint_drive_path_comparison.py --verify-archive --output-dir resouces/12-control-and-machining-algorithms/generated/path-01/results
- 配置中全部工程验收阈值都填写后才会给出PASS/FAIL；任一阈值为空且收敛筛查成功时状态为COMPLETED_REPORT_ONLY，只做描述性输出；步长收敛筛查失败为FAIL。
- test_gantry_joint_drive_path_comparison.py：34项PATH-01资源级测试，覆盖参考轨迹、Simpson/梯形求积、状态归一化、限幅门控、来源ID、CSV哈希绑定、归档独立校验/篡改识别/路径覆盖拒绝、溢出边界、CLI错误返回和能量有限值边界。测试尚未执行；仓库CI不执行资源模块。


## PATH-01限幅感知诊断补充（2026-11-23）

- 运行器在自由轴与规定路径的每次电流命令回调处采集当前参考限幅和电压饱和标志；计数覆盖每个RK4步的四个阶段。规定路径积分器额外的最终端点诊断从RK4阶段计数中单独剔除。
- 汇总CSV报告两种模型的RK4阶段数、电流参考限幅阶段数、电压饱和阶段数、任一限幅激活阶段数、激活比例及阶段计数一致性；`smooth_unsaturated_regime` 仅在两种模型均未触发限幅且阶段计数完整时为真。
- 时序CSV另记录输出采样点的请求电流命令、裁剪后的电流参考值、电流参考限幅标志和电压饱和标志；这些采样点标志不替代RK4阶段累计计数。
- 观测阶数筛查仍作为数值诊断保留，但若任一积分器在任一RK4阶段触发限幅，或阶段回调数不符，则最终状态最高只能为 `COMPLETED_REPORT_ONLY`，不输出常规光滑工况的工程 `PASS`。若数值收敛筛查失败，仍记 `FAIL`。
- 运行器纯函数辅助资源测试新增3项，现为10项；与原求解器24项合计34项，均未执行。仓库Knowledge Quality CI不执行这些资源测试。


补充说明：光滑未限幅门控覆盖整个 `h/h2/h4/h8` 收敛细化序列，而不只检查最细 `h/8`。因为收敛差值由多档轨迹共同构成，只要任一档位任一模型在任一RK4阶段触发参考限幅或电压饱和，`all_refinements_smooth_unsaturated_regime` 即为假，最多输出 `COMPLETED_REPORT_ONLY`。逐档 `smooth_unsaturated_regime` 和全序列聚合标志分别写入汇总CSV；manifest顶层同样记录聚合结论。新增两项纯函数验收门控测试，运行器辅助测试增至13项；连同求解器24项共37项，仍未执行。


限幅标志口径统一：内部RK4阶段计数与输出采样点时序均通过同一精确裁剪比较判断电流参考是否发生变化，不再使用可能掩盖极小裁剪量的绝对容差。新增相邻浮点数裁剪回归用例；运行器辅助测试13项，连同求解器24项合计37项，均未执行。


PATH-01输入来源追溯：`provenance.source_documents_or_measurement_ids` 必须是字符串数组，元素不得为空或重复；运行器将规范化后的来源/测量标识原样写入JSON manifest。允许显式使用空数组表示没有单独的来源文档ID（例如已在 `parameter_source` 中说明的合成夹具），但不得传入 `null`、数字或空字符串。新增3项来源ID校验用例，运行器辅助测试现为16项，连同求解器24项共40项未执行。


## PATH-01电压饱和与能量求积复核补充（2026-11-23）

- 电压饱和布尔标志改为直接比较限幅后的 `voltage_V` 与未限幅 `raw_voltage_V`；仅相差一个可表示浮点数的越界也会计为限幅，避免门控误漏。
- 求解器新增上下电压轨一ULP越界测试；PATH-01运行器新增能量残差梯形复核值单元测试。
- 汇总CSV新增自由轴/规定路径两列 `*_energy_residual_trapezoid_J`，与现有Simpson残差并列，作为求积敏感性诊断；工程验收仍使用既定Simpson归一化残差，不新增/放宽阈值。
- 求解器资源测试由24项增至25项，PATH-01辅助测试由16项增至17项，共42项资源测试，均未执行。


## PATH-01归档完整性与失败恢复（2026-11-23）

- PATH-01运行manifest使用 schema_version: 2，output_artifacts 分别记录时序CSV/汇总CSV的文件名、SHA-256、字节数、数据行数和列数；哈希只绑定两份CSV，不对manifest自身做自哈希。
- 运行器在输出目录的临时子目录完整写出两份CSV、计算哈希并写出暂存manifest，然后才替换最终文件；manifest最后发布，作为本次输出集的完成标记。
- 暂存失败时不触碰已有输出集；发布阶段中断时manifest缺失，残留CSV不能被视为完整归档。此类目录须检查后用 --force 重跑整套结果，或更换输出目录。
- 新增3项资源测试；PATH-01运行器辅助测试20项、求解器测试25项，共45项均未执行。Knowledge Quality CI不运行这些资源测试；PATH-01仍为 NOT_RUN。


## PATH-01独立归档校验与输入边界（2026-11-23）

- CLI新增 --verify-archive；仅需 --output-dir，不需要原始配置文件，不运行求解器。校验manifest schema/case/status、固定输出文件名、CSV SHA-256、字节数、表头、每行列数、数据行数及manifest中的对应元数据；拒绝manifest指定其他路径。成功返回 VERIFIED，文件缺失或内容不一致返回非零错误。
- 配置schema_version必须是整数1（JSON true不视为1）；来源ID数组必须显式存在，无单独ID时填写[]；可选profile_id若非null必须为非空字符串并会去首尾空白。
- 数值输入转换溢出、duration/base_step非有限、超出平台索引范围或h/8细化后不可表示时，在仿真前作为配置错误拒绝。CLI对文件/JSON/配置/数值溢出/运行异常打印 PATH-01 ERROR 并返回2。
- 新增12项归档验证、配置与数值边界/CLI测试；当时PATH-01运行器资源测试为32项、求解器资源测试25项，共57项。其后资源测试扩展为运行器34项、求解器30项，共64项，全部仍未执行。

## PATH-01数值尺度求解和能量账本边界补充（2026-11-23）

- 自由/规定路径质量矩阵求解改为对角尺度均衡后的Cholesky；在坐标包含m/rad/模态量、矩阵对角量级不同时，先归一化对称正定线性系统并同步缩放RHS，再恢复原广义坐标解。
- 求解器提供 scaled_joint_mass_matrix_condition_number(q, s)，报告单位对角归一化质量矩阵的特征值比。该值仅为无量纲耦合诊断，不是原始混合单位矩阵条件数；不设置通用阈值，不单独构成PASS条件。
- 对质量矩阵、RHS、电气诊断、机械/磁场储能、逐点账本及Simpson/梯形求积增加非有限/溢出防护，错误中包含阶段或采样上下文，避免将Inf/NaN写入归档。
- 新增5项求解器和2项运行器资源测试；现有资源测试总计64项，均未执行。Knowledge Quality CI不运行这些测试，PATH-01仍为NOT_RUN。


## M0构造期正定性检查的尺度一致性（2026-11-23）

- 模型初始化对基准机械质量矩阵M0的正定性检查改为先对角尺度归一化，再执行Cholesky；与自由/规定路径方程的实际求解方法一致。
- 新增两项资源测试，覆盖极端混合单位量级下合法SPD矩阵接受，以及归一化后不定矩阵拒绝。求解器资源测试32项、PATH-01运行器34项，共66项，均未执行。

## 机电功率互易项与约束功符号回归契约（2026-11-23）

- PATH-01账本中的机电不匹配功率为 (Kf-Ke)*i*ell_dot，保留正负号；匹配SI互易常数时为零。该项来自机械执行器功率与电气反电势功率的差，不是非负耗散项。
- 理想规定路径的约束功率为 +lambda*sdot_ref；反向路径速度使功率自然反号。自由路径没有理想路径约束，账本将约束功率固定为零。
- 新增3项资源测试验证上述符号契约；PATH-01运行器测试37项、求解器32项，共69项资源测试均未执行。


## 阻尼耗散与外部广义力功率符号契约（2026-11-24）

- 当前模型的结构阻尼功率为 `q_dot.T @ D0 @ q_dot`，轴向平滑摩擦功率为 `(b*s_dot + Fc*tanh(s_dot/v_eps))*s_dot`；在现有半正定/非负参数约束下，两项理论上非负，路径反向不改变耗散功率符号。
- 外部广义力功率为 `Q_ext.T @ [q_dot, s_dot]`，是有符号输入/输出项，不得记为耗散；速度反向时应自然反号。
- 新增2项PATH-01资源测试；运行器39项、求解器32项，共71项资源测试，均未执行。Knowledge Quality CI不运行这些资源测试。


## ENE-01～03独立瞬时能量率基准（2026-11-24）

- 求解器资源测试新增3项：通过中心差分方向导数 dE/dt，与独立显式功率预算比较，分别覆盖机电互易常数匹配、结构阻尼/轴摩擦耗散、外部广义力功率。
- 基准不调用PATH-01内部能量账本/能量指标函数，但仍使用同一模型的状态方程与储能函数，属于局部一致性测试，不是独立物理模型。
- 当前求解器35项、PATH-01运行器39项，共74项资源测试均未执行；ENE-01～03积分和PATH-01仿真仍未运行。


## ENE多步积分闭合判据（2026-11-24）

ENE-01～03积分结果需按h、h/2、h/4、h/8四档分别计算储能变化、净功率积分、J单位能量残差和归一化残差。归一化定义为 abs(R_E)/max(E_scale, integral(abs(P_net)), E_floor)，能量尺度/地板必须预先声明并在各档保持不变。Simpson 1/3作为主积分，梯形残差仅作求积敏感性诊断。分项功率及实际限幅端电压必须保留；ENE-01为端电压功减铜耗，ENE-02再扣阻尼/摩擦，ENE-03再加有符号外力功。瞬时方向导数通过不代表积分闭合完成；本协议不包含任何预置机床数值或已执行结果。


## ENE-01～03独立积分运行器（2026-11-24）

- 入口：`gantry_joint_drive_energy_closure.py`；配置模板：`gantry-joint-drive-energy-closure-config-template.json`。
- 每次只运行一个ENE用例，自动按h/h/2/h/4/h/8四档从同一初始状态积分。配置采用本目录PATH-01相同的机械/电气/执行器/初始状态字段，另含 `integration`、`controller_and_loads.feedforward_current_A` 与 `metrics`。
- 示例（请先复制模板并填入有来源的参数；当前空白模板不能直接运行）：

```bash
python resouces/12-control-and-machining-algorithms/gantry_joint_drive_energy_closure.py \
  --config path/to/completed-ene-config.json \
  --output-dir resouces/12-control-and-machining-algorithms/generated/ene-01
```

- 归档校验不运行模型：

```bash
python resouces/12-control-and-machining-algorithms/gantry_joint_drive_energy_closure.py \
  --verify-archive --output-dir resouces/12-control-and-machining-algorithms/generated/ene-01
```

- ENE-01要求无阻尼/摩擦/外力；ENE-02强制非零结构阻尼、轴黏性及库仑摩擦且无外力；ENE-03沿用该耗散配置并强制非零五维外力。外力坐标顺序严格校验。三者均要求SI互易常数Kf=Ke。命令当前限定为常值前馈电流；阈值缺失或任一档触发限幅时为报告态。经验残差阶数在未预声明噪声地板和稳定性门控前不计算。输出文件逐个原子替换、manifest最后发布，不构成整包事务原子性。
- 新增4项资源级功率账本测试、4项配置契约测试及4项归档语义测试，当前求解器35项、PATH-01运行器39项、ENE运行器12项，共86项；全部未执行。Knowledge Quality CI不运行资源测试，ENE积分尚未运行。
- 独立性只覆盖功率账本/积分实现；动力学状态方程和储能函数复用原联合模型，不是独立物理模型。


### ENE归档语义校验加固（2026-11-24）

- `--verify-archive` 除哈希/字节数/CSV结构外，进一步核对manifest运行状态、数值结果/资源测试标志、参数来源、时间戳、归一化尺度、阈值及四档限幅阶段报告。
- 对CSV所有数值字段拒绝NaN/Inf/非数值，布尔字段只接受True/False；核对汇总状态与manifest一致、四档区间数/步长/样本数正确、时序网格严格递增且匹配配置时长。
- 根据manifest阈值、限幅门控和最细两档归一化残差重新推导预期状态，拒绝PASS/FAIL/REPORT_ONLY语义不一致的归档。`VERIFIED`仍只表示归档自洽，不表示仿真或物理正确。
- 新增4项归档语义资源测试定义；ENE运行器测试由8项增至12项。

## ENE积分运行器数值完整性与资源上限审查（2026-11-24）

- 四档轨迹合计采样点按NΣ=15N+4计算，配置端和manifest归档校验端均限制为不超过50,000点；极端区间数/步长比值在分配轨迹前拒绝。
- 每个12维状态向量必须全有限；储能变化、每项功积分、绝对净功率积分、Simpson/梯形残差和归一化残差均逐项检查有限性。
- RK4实际阶段回调数不等于理论阶段数时状态为FAIL；阶段完整但发生限幅时仍为COMPLETED_REPORT_ONLY。
- 新增3项ENE资源测试定义；ENE测试15项、求解器35项、PATH-01运行器39项，共89项资源测试全部未执行。未执行ENE积分；Knowledge Quality CI不执行resouces/资源测试。


## ENE功率采样与RK4阶段接口契约（2026-11-24）

- RK4每个区间4次命令回调用于阶段限幅统计；功率/储能在N+1个输出节点取样，两者不可混用。
- 新增回归测试定义：检查两区间8个阶段快照的时间/状态，及同阶段限幅后端电压与RL电流导数、端口功率的一致性。
- ENE资源测试16项，求解器35项、PATH-01运行器39项，共90项均未执行；ENE积分未运行。


## ENE多尺度残差与分项贡献诊断（2026-11-24）

- ENE汇总新增六项功的绝对贡献率、分项绝对积分总量，以及残差相对预声明能量尺度、净功绝对积分、分项绝对积分尺度的三个比率；分母使用正能量地板保护。
- Simpson/梯形净功积分差只作为求积敏感性指标，不是Simpson误差上界。四档细化同时改变RK4状态轨迹和功率求积网格，不能仅凭总残差拆分两类误差。
- 新增3项ENE资源测试定义；资源测试总计93项（求解器35、PATH-01 39、ENE 19），均未执行；ENE积分仍未运行。


## ENE固定轨迹功率求积敏感性诊断（2026-11-24）

- 冻结 `h/8` 轨迹端点净功率样本，按8/4/2/1嵌套节点计算四档Simpson净功/绝对净功积分；不额外运行ODE积分。
- 报告固定轨迹求积网格变化、同网格状态轨迹差、储能端点差及残差差，归档校验器从最细档CSV重算。
- 该分解是条件式数值诊断，不是误差上界；`h/8` 轨迹仍有积分误差，端点采样不能检测步内功率变化。
- 新增3项ENE资源测试定义；总计96项资源测试（求解器35、PATH-01 39、ENE 22）全部未执行，ENE积分未运行。

## ENE RK4阶段功率采样诊断（2026-11-24）

- 新增 gantry-joint-drive-energy-closure-stage-power-timeseries.csv 归档：每个RK4积分区间保存k1/k2/k3/k4阶段功率快照及限幅标志。
- 使用经典RK4权重 (1,2,2,1)h/6 累计分项功、净功和绝对净功，summary增加阶段能量残差及阶段加权净功与端点Simpson净功差。
- --verify-archive 检查阶段行数、阶段索引/顺序、阶段时刻和步长，并重算阶段积分摘要；manifest记录新增CSV哈希、字节数和行列数。
- 新增阶段快照总行数上限200,000；端点样本上限仍为50,000。
- 该诊断使用求解器自身RK4阶段状态，不是独立高精度求积oracle或误差上界。新增3项ENE资源测试定义；总计99项资源测试（求解器35、PATH-01 39、ENE 25）全部未执行，ENE积分未运行。

## ENE h/16参考轨迹与共同节点误差对照（2026-11-24）

- 四档主轨迹之外，自动独立积分一条同模型、同初值、同命令/负载的 `h/16` 参考轨迹；不是精确解或独立物理模型，也不参与原四档PASS阈值。
- 新增参考端点文件 `gantry-joint-drive-energy-closure-reference-h16-timeseries.csv`；h/16 阶段快照加入阶段功率CSV；manifest schema升级至2，并由归档验证器重算参考诊断。
- 共同时间网格按16/8/4/2步幅对照h、h/2、h/4、h/8：报告参考同网格功积分/残差、主轨迹相对参考的功积分/储能变化/残差差、12维状态逐分量最大绝对差/RMS差，以及净功率最大绝对差/RMS差。不同物理单位的状态误差不得合并为单一范数。
- 总样本数 `31N+5`、总阶段数 `124N`；端点样本上限50,000，阶段快照上限200,000，N最大1612且仍须为偶数。
- 参考轨迹复用同一求解器，限幅单独标记，不能作为精确误差界。新增3项资源测试定义；总计103项资源测试（求解器35、PATH-01 39、ENE 29）未执行，ENE积分未运行。

