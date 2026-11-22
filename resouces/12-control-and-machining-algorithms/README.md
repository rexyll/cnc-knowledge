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
