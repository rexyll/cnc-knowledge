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
- gantry_joint_drive_solver.py：NumPy实现联合坐标机械模型、移动负载惯性耦合、运输项、路径摩擦、重力势能梯度、执行器虚功投影及单轴等效RL/连续PI电流环；自由路径坐标s与结构坐标q同一步联合求解。
- test_gantry_joint_drive_solver.py：13项资源级unittest，覆盖联合质量矩阵对称正定、零负载极限、虚功功率、零速RL衰减、限幅/anti-windup、无输入静止极限、机电能量/铜耗平衡、自由路径状态积分、几何维数契约、参数数组快照/只读、非有限状态拒绝、非有限电流指令与非有限外力拒绝。
- 测试运行：python -m unittest discover -s resouces/12-control-and-machining-algorithms -p 'test_gantry_joint_drive_solver.py' -v
- 模型需要调用方提供M0/D0/K0、轴等效质量、电气参数、限幅与执行器位移映射；不提供伪装成通用机床参数的默认额定值。四坐标正弦几何仅是合成示例。
- 当前脚本和13项测试均尚未执行；仓库结构CI不执行资源测试。无数值仿真、参数辨识、硬限位/接触、完整PMSM dq、离散采样驱动或实机/HIL证据。