# 12. 控制与加工算法 — 章节任务计划

**章节编号：** CH12  
**英文名称：** Control and Machining Algorithms  
**对应正文：** `docs/12-control-and-machining-algorithms/`  
**资源归档：** `resouces/12-control-and-machining-algorithms/`  
**章节范围：** 插补、轨迹规划、加减速、前瞻、坐标变换、误差补偿、主轴/进给控制、加工优化和算法验证。

> 本文件只拆解本章知识建设任务，统一继承根目录 `TaskPlan.md` 的全部 Guide、Limit、质量标准、资源规则、版权要求和安全要求。

## 1. 章节目标

建立本章节系统化、可验证、可检索且能够与其他知识板块关联的技术资料。按“概念分类—原理结构—参数与型号—工程应用—测试/维护—案例”逐步完善，避免只堆积无上下文的链接或参数表。

## 2. 覆盖范围

- 直线/圆弧/样条插补、多轴插补和高阶曲线
- 速度规划、加速度/跃度约束、前瞻和拐角平滑
- 坐标变换、刀具半径/长度补偿、RTCP和运动学变换
- 螺距/反向间隙/直线度/垂直度/热误差补偿
- 振动抑制、切削参数优化、负载监测和加工误差分析

## 3. 任务节点

### CH12-T001 — 建立算法分类与数学基础

- **目标：** 明确数控算法分类、输入输出、坐标与单位约定及相关数学基础。
- **工作范围：** 直线/圆弧/样条插补、多轴插补和高阶曲线；速度规划、加速度/跃度约束、前瞻和拐角平滑；坐标变换、刀具半径/长度补偿、RTCP和运动学变换；螺距/反向间隙/直线度/垂直度/热误差补偿；振动抑制、切削参数优化、负载监测和加工误差分析。
- **交付物：** 算法目录、符号表、坐标约定。
- **验收标准：** 变量定义、坐标方向、单位和适用轴型一致且可追溯。
- **依赖：** CH07、CH08
- **状态：** `TODO`

### CH12-T002 — 研究插补与轨迹生成

- **目标：** 整理基本插补、多轴联动、样条曲线和轨迹离散方法。
- **工作范围：** 直线/圆弧/样条插补、多轴插补和高阶曲线；速度规划、加速度/跃度约束、前瞻和拐角平滑；坐标变换、刀具半径/长度补偿、RTCP和运动学变换；螺距/反向间隙/直线度/垂直度/热误差补偿；振动抑制、切削参数优化、负载监测和加工误差分析。
- **交付物：** 原理说明、公式推导、伪代码/示例。
- **验收标准：** 数学推导经过检查，明确误差、连续性和实时计算约束。
- **依赖：** 本章任务1
- **状态：** `TODO`

### CH12-T003 — 研究速度规划与误差补偿

- **目标：** 整理速度前瞻、S曲线、跃度限制、几何/热误差补偿方法。
- **工作范围：** 直线/圆弧/样条插补、多轴插补和高阶曲线；速度规划、加速度/跃度约束、前瞻和拐角平滑；坐标变换、刀具半径/长度补偿、RTCP和运动学变换；螺距/反向间隙/直线度/垂直度/热误差补偿；振动抑制、切削参数优化、负载监测和加工误差分析。
- **交付物：** 算法专题、参数定义、对比分析。
- **验收标准：** 注明模型前提、标定方法、边界条件及适用场景。
- **依赖：** 本章任务1、2、CH14
- **状态：** `IN_PROGRESS`


**追加执行切片（2026-11-22）：直接驱动回转轴扰动观测与周期转矩补偿。** 新增 `disturbance-observer-and-periodic-torque-compensation.md`，覆盖扰动分类、名义对象、DOB/Q滤波、机械角/电角度周期表、摩擦补偿、谐波前馈、重复控制/迭代学习与多工况回归；明确补偿不得掩盖机械/反馈缺陷。新增SRC-000323～SRC-000326；CH12数据字典新增8项算法/验证字段；新增扰动观测与周期补偿验证模板。该切片只涉及周期扰动和伺服补偿，不完成速度规划/几何热误差补偿的全部CH12-T003范围；CH12-T003保持IN_PROGRESS。



**追加执行切片（2026-11-22）：DOB鲁棒稳定性与伺服对象数值仿真。** 新增 servo-model-and-dob-robustness-simulation.md，研究实际/名义对象相对阶次、Q滤波可实现性、乘性不确定性建模和按真实互连结构进行Nyquist/小增益/极点审查；明确不能把未经推导的单一范数不等式当作通用DOB判据。新增SRC-000331～SRC-000332；CH12数据字典新增5项DOB稳定性审查、Q敏感性扫描、伺服对象不确定性及仿真配置/结果字段。新增可复现Python合成仿真脚本、配置JSON、惯量辨识摘要、刚体解析FRF和DOB截止频率扫描CSV。仿真含4 ms转矩执行器滞后和2 ms未建模命令延迟；结果仅说明这组模型的有限时域敏感性，不是稳定性证明、机床实测或参数推荐。内容提交 f39c40297d543823c766d312bc02e791a8c2f179 的GitHub Actions [Run 45016439988](https://github.com/rexyll/cnc-knowledge/actions/runs/45016439988) success；5/5单元测试通过；strict lint PASS（0 errors）。该切片只完成CH12-T003的一部分，CH12-T003保持IN_PROGRESS。



**追加执行切片（2026-11-22）：多工况模型交叉验证与闭环稳定裕度边界。** 新增 servo-model-cross-validation-and-robust-margins.md，覆盖H1/幅值平方相干度、留出验证、残差诊断、AICc/BIC模型复杂度、多工况模型集合/不确定性包络，以及GM/PM/disk margin的闭环互连计算边界。新增SRC-000333～SRC-000337；CH12数据字典新增5项交叉验证、FRF质量、模型阶次、不确定性包络和闭环裕度字段。新增多工况两/三惯量合成仿真脚本、配置JSON、模型选择CSV、模型参数配置CSV和CW/CCW方向斜率/截距CSV。结果选择三种两惯量工况的2惯量模型和三模态参考对象的3惯量模型；仿真未设计控制器，因此不生成GM/PM/disk margin数值。内容提交 f84386e3e2885fa6f19339a66a7d810298eb0426 的GitHub Actions [Run 45018271186](https://github.com/rexyll/cnc-knowledge/actions/runs/45018271186) success；5/5单元测试通过；strict lint PASS（0 errors）。CH12-T003保持IN_PROGRESS。

### CH12-T004 — 建立算法验证基准

- **目标：** 设计数值测试、轨迹仿真、极限工况和实机验证的分级测试集。
- **工作范围：** 直线/圆弧/样条插补、多轴插补和高阶曲线；速度规划、加速度/跃度约束、前瞻和拐角平滑；坐标变换、刀具半径/长度补偿、RTCP和运动学变换；螺距/反向间隙/直线度/垂直度/热误差补偿；振动抑制、切削参数优化、负载监测和加工误差分析。
- **交付物：** 测试数据集、指标和验证报告模板。
- **验收标准：** 每个结论标明验证层级；仿真结果不得宣称为机床实测精度。
- **依赖：** 本章任务2、3、CH14
- **状态：** `TODO`


## 4. 章节级交付物

- 章节分类树、术语和知识条目索引。
- 经过来源核验的专题文档及必要的参数/接口/型号数据。
- 与本章相关的图片、动图和完整资料资源，以及资源索引。
- 与机型、零部件、材料、厂商、标准、BOM、算法或故障的跨章节关联。
- 未解决问题、待核验数据和后续研究建议。

## 5. 章节完成验收

本章节只有在任务节点均完成或明确标记延后/不适用，并且至少完成以下检查后，才可整体标记完成：知识覆盖与边界清楚；关键结论有可追溯来源；参数具备单位、版本和适用条件；资源归档和引用正确；跨章节关联建立；安全、版权及保密检查通过；遗留问题有记录。


**跨章节索引/计划补录最终CI核验（2026-11-22）：** 提交 `65f2ec178a443652272d5f76f9b6a821df531eeb` 的GitHub Actions [Run 45013716276](https://github.com/rexyll/cnc-knowledge/actions/runs/45013716276) success；5/5单元测试通过；strict lint PASS（0 errors）。本轮统计：22章、112个Markdown文件、375条内部链接、140条实体、240条关系、326条来源、582处正文来源引用。CH12-T003保持IN_PROGRESS。


**追加执行切片（2026-11-22）：多工况级联闭环裕度与限幅联合仿真。** 新增 multicondition-cascade-robust-stability-and-saturation-simulation.md，定义电机速度内环与负载位置外环两个SISO断点；对四种两/三惯量对象、两套候选控制器及0/0.5/1.0 ms反馈延迟执行24组频域扫描，并保留多交越频率。新增转矩/电流执行器一阶近似、0.5 ms采样、±1 N·m转矩限幅、±1.5 rad/s速度参考限幅、反算抗积分饱和、柔性轴系、摩擦和负载扰动的24组时域测试。新增SRC-000338～SRC-000340；CH12字典新增环路裕度扫描、采样延迟模型、限幅/anti-windup验证3项字段。资源包括servo-cascade-control-robustness-simulation.py、配置JSON、环路裕度摘要CSV和阶跃响应摘要CSV。合成结果中，1 ms反馈延迟下激进候选在重载冷态位置外环PM/GM约14.97°/2.98 dB，保守候选约36.81°/6.54 dB；0.25 rad阶跃时重载冷态/热态分别出现约1.83%/0.93%转矩饱和样本。频域延迟含半采样ZOH等效近似；极点检查不含延迟/摩擦/饱和；GM/PM为经典SISO指标，不是MIMO disk margin或稳定性证明。内容提交 b095839e3c2114c82c60dd978d2e864bbc000cdc，GitHub Actions [Run 45021742754](https://github.com/rexyll/cnc-knowledge/actions/runs/45021742754) success；5/5单元测试通过，strict lint PASS（0 errors）。CH12-T003继续 IN_PROGRESS。


**追加执行切片（2026-11-22）：伺服前馈、陷波与低通联合仿真。** 新增 servo-feedforward-notch-lowpass-co-design.md，对前馈轨迹跟踪、参考模态纹波、外部负载转矩扰动和多交越SISO稳定裕度进行区分验证。修正既有两惯量刚体惯量定义及阶跃反馈缓存长度；速度PI候选按名义Jrigid=0.030 kg·m²计算，保守候选Kp=2.26195、Ki=56.84892，激进候选Kp=3.01593、Ki=113.69784。新增SRC-000341～SRC-000345；CH12字典新增前馈跟踪、陷波失谐敏感性、低通相位/噪声权衡3项字段。仿真对象模态约为名义冷态72.934 Hz、重载冷态68.223 Hz、热态参数变体64.722 Hz、三惯量参考41.906/94.079 Hz。固定42/70/94 Hz陷波可降低部分对象参考模态纹波，但热态失谐后效果弱；控制器转矩通道陷波可能削弱外部扰动抑制。150 Hz速度反馈低通带来与频率相关的相位滞后，必须同时评估全交越裕度。新增修正后的环路裕度CSV、阶跃响应CSV和前馈/滤波联合摘要CSV；脚本扩展为生成完整组合结果。内容提交 4fa9406b3476b6b3d4acda2b81c2eea190e82e99；GitHub Actions [Run 45024433308](https://github.com/rexyll/cnc-knowledge/actions/runs/45024433308) success；5/5单元测试通过；strict lint PASS（0 errors）。本轮所有数据仍是合成模型，不是实机稳定性证明或整定建议；CH12-T003保持 IN_PROGRESS。


**更正补录（2026-11-22）：替换上一版级联控制裕度/阶跃表中的过期数值。** 前序补录虽已声明旧惯量定义和阶跃缓存错误，但原CH12稳定裕度专题仍残留旧表格。本次已把旧表实际替换为刚体惯量修正后的多交越PM/GM序列及1 ms反馈延迟、两样本缓存下的阶跃结果；详细滤波组合见 servo-feedforward-notch-lowpass-co-design.md 和资源CSV。更正提交 e95ed502e940105adf6b2ebfb45fc3233a6fddf3；GitHub Actions [Run 45024670605](https://github.com/rexyll/cnc-knowledge/actions/runs/45024670605) success，5/5单元测试通过，strict lint PASS（0 errors）。CH12-T003继续 IN_PROGRESS；这些数据仍是合成SISO模型，不能作为真实机床稳定性证据。


**追加执行切片（2026-11-22）：双驱龙门MIMO耦合同步与鲁棒性诊断。** 新增 gantry-dual-drive-mimo-synchronization-and-robustness.md，构建左右轴差动弹簧/阻尼二自由度对象，比较独立PD与差动同步P-D；说明机械交叉通道、同步误差、MIMO返回差/灵敏度和严格multiloop disk margin之间的区别。新增SRC-000346～SRC-000351、KNOW-000018；CH12数据字典新增MIMO返回差诊断、多回路disk margin分析记录、交叉耦合同步控制器记录3项字段。资源脚本生成10组负载/耦合配置和140个频率采样点；仓库保存脚本、配置及两个摘要CSV。合成不对称负载/0.5 MN/m案例中，独立PD同步误差峰值60.61 μm，同步P-D候选约33.98 μm；峰值灵敏度由1.112升至1.209、最小返回差奇异值由0.900降至0.827，体现同步性能和鲁棒性指标的权衡。未计算严格multiloop disk margin/μ，也无真实设备/HIL验证。内容提交 `6cf618bda16ca8ef45e77d2eac903a459c45dcb0`，纠正提交 `0750805592e174171e03383c9b05b78dbc469d42` 对应GitHub Actions [Run 45027868840](https://github.com/rexyll/cnc-knowledge/actions/runs/45027868840) success；5/5单元测试通过、strict lint PASS（0 errors）。CH12-T003继续IN_PROGRESS，本切片不代表速度规划/热误差补偿等整个任务完成。


**追加执行切片（2026-11-22）：横梁弯曲/扭转假设模态、位置相关负载与离散同步延迟鲁棒性。** 新增 `gantry-mimo-modal-load-position-delay-robustness.md`。使用4广义坐标 (q=[x_c,\psi,\eta_b,\theta_t]^T)，通过 (M(\xi,m_p)=M_0+m_p g(\xi)g(\xi)^T) 表达冻结负载位置引入的平移/偏航/弯曲/扭转交叉惯性项；负载质量5/15/30kg，位置0.1～0.9，共27个冻结快照。每个对象以1ms采样周期精确ZOH离散化，并把0～6ms命令延迟FIFO并入闭环状态矩阵，执行4种控制器×27工况×7延迟=756组离散极点测试。
- 模态频率范围：20.12～26.85Hz、27.14～49.02Hz、74.16～76.43Hz。3ms时独立PD和全部同步候选均为0/27稳定；2ms时独立PD 27/27稳定，低同步P-D 10/27、中同步P-D 5/27、同步P-only 9/27。结果显示交叉同步环节改变了延迟稳定边界，不能把上一专题连续模型结论直接外推到离散网络闭环。
- 1ms延迟下三个阶跃样例中，5kg/边缘同步误差54.89→53.02μm、横梁弯曲32.19→32.96μm；15kg/中心42.08→36.73μm、弯曲205.37→205.93μm；30kg/边缘239.34→228.43μm、弯曲99.58→110.78μm（独立PD到中同步P-D）。同步误差改善与结构挠曲改善不是同一件事。
- 中心15kg工况的采样小增益指示量 (1/\max\bar\sigma(T))：独立PD在0/1/2ms为0.6773/0.3539/0.0315；同步低P-D为0.6402/0.3026，2ms名义闭环已不稳定；同步中P-D为0.6071/0.2566，2ms已不稳定。该量由1024点频率网格估计，不是连续频率严格H∞上界，也不是disk margin。
- 新增SRC-000352～SRC-000360（柔性H型龙门、负载移动同步控制、数据驱动动力学分解、采样/计算延迟和disk margin方法），KNOW-000019；CH08/CH12字典各新增3项。资源包括模型脚本、配置、27行模态摘要、28行延迟鲁棒性摘要、9行阶跃摘要和12行小增益摘要；完整756行离散极点明细可由脚本重新生成。
- 本地运行参考实现脚本完成 `py_compile` 和模型计算，生成上述结果；仓库中的资源脚本采用相同状态方程/延迟队列结构。GitHub Actions仅执行知识库单元测试和lint，不执行资源仿真脚本。
- 内容提交 `c51f68ed9003e168e2cda47d66986f81e2d5a784`；GitHub Actions [Run 45033980670](https://github.com/rexyll/cnc-knowledge/actions/runs/45033980670) success，5/5单元测试通过，strict lint PASS（0 errors）。
- 结构统计：22章、123个Markdown文件、399条内部链接、142条实体、240条关系、360条来源、642处正文来源引用。CH12-T003继续IN_PROGRESS，本轮不完成速度规划/几何或热误差补偿的其他任务。


**更正与新增执行切片（2026-11-22）：冻结位置模型阻尼更正、连续移动负载与MIMO多回路disk margin端口。**

- 更正原 gantry-modal-delay-study.py 偏航/扭转交叉阻尼：旧式使用刚度矩阵K量纲，改为 \(D_{\psi\theta}=0.03\sqrt{D_{\psi\psi}D_{\theta\theta}}\)。已替换冻结模型正文和三份受影响CSV。修正后，0/1/2/3ms稳定工况数（27个冻结工况）为：独立PD 27/27、27/27、27/27、3/27；同步低P-D 27/27、27/27、27/27、0/27；同步中P-D 27/27、27/27、10/27、0/27；同步P-only 27/27、27/27、27/27、0/27。原旧数值作废；未阻尼模态频率不变。
- 新增 [连续移动负载时变模型专题](../../12-control-and-machining-algorithms/gantry-continuous-moving-load-and-multiloop-disk-margin.md)，用动能与拉格朗日方程推导移动点速度/加速度链式项、\(M(s(t))\)、\(\dot M\)、速度交叉项与路径输运项；明确 \(s(t)\) 是规定轨迹，当前没有负载轴自由度和双向耦合。
- 新增18组模型/控制器/负载比较、123组方程检查。方程最大归一化偏差（分母max(1,参考量2-范数)）：Mdot 2.49e-10、移动点加速度链式法则4.35e-7、q行Euler–Lagrange残差8.89e-10。模型比较显示冻结起点快照明显低估移动过程负载点误差；本例运输项数值贡献较小，不对其他速度/结构做普遍外推。
- 定义MIMO两通道disk-margin的对象输出端口 \(PC\) 与对象输入端口 \(CP\)，脚本提供python-control/Slycot AB13MD可选接口。当前未安装依赖，**没有数值disk margin结果**；有限频率网格估计不能当作全频率认证。
- 资源脚本已入库，但CI只检查库结构，不执行脚本；参考计算导出的CSV已归档，精确提交版脚本仍需独立Python回归验证。不得把CI成功表述为脚本运行成功。
- 来源增加SRC-000361～SRC-000364，KNOW-000020登记；新增资源、数据字典字段及审查边界。详情见 [本轮历史附录](../../../TaskHistory/Appendix-2026-11-22-gantry-modal-correction-moving-load.md)。
- 内容提交 c2f624767c85202e2520932245611eea163f0da3 对应Run [45036988333](https://github.com/rexyll/cnc-knowledge/actions/runs/45036988333) success；5/5单元测试通过、strict lint PASS（0 errors）。CH12-T003继续 IN_PROGRESS。


**计划/历史补录CI验收（2026-11-22）：** 提交 1abcbc4ae1d4400586b49fd7767f61f020ec5362 对应GitHub Actions [Run 45037385127](https://github.com/rexyll/cnc-knowledge/actions/runs/45037385127) success；5/5单元测试通过，strict lint PASS（0 errors）。该提交扫描统计22章、126个Markdown文件、406条内部链接、143条实体、240条关系、364条来源、649处正文引用。CH12-T003继续IN_PROGRESS。


**追加静态审查更正（2026-11-22）：** 移动负载模型脚本/CSV字段统一明确混合m/rad广义坐标下矩阵/广义力范数无单一SI单位；方程检查误差分母为max(1,参考量2-范数)，字段不再误称严格相对误差。并将阻尼交叉项的矩阵非对角符号写为负值，标量幅值保持正。当前脚本仍需独立Python执行回归，本次只完成静态审查与语义更正。


**追加执行切片（2026-11-23）：移动轴自由坐标与横梁双向耦合解析推导。** 在现有预设轨迹移动负载模型之外，新增自由路径坐标 \(s\) 与结构坐标 \(q\) 的联合广义坐标，构造 \(\mathcal M_z=\operatorname{diag}(M_0,m_{s0})+m_pJ^TJ\)，并推导结构行/移动轴行耦合方程。说明等效驱动力、电流/力闭环接口、线性电机与滚珠丝杠折算、摩擦、行程约束、接触自由度及机械侧能量平衡。新增SRC-000365～SRC-000367，并在CH12字典增加双向耦合模型/能量核验记录。**本次为解析推导，不包含联合求解器、资源脚本或数值仿真**；原18组结果仍是预设 \(s(t)\) 的单向时变模型，不能宣称已验证双向耦合。CH12-T003继续 IN_PROGRESS。


### CH12-T003 双向耦合解析切片CI验收（2026-11-23）

- 内容提交 e665db824dbe730908ad8cd7e3d77b2c1dad1483（自由路径坐标/结构耦合方程解析推导）与接口澄清提交 f45ac78b90dc82ba3e0cbfd03a20a928193821c3 均通过 GitHub Actions：Run 45045633287、45045811445；两次均为5/5单元测试通过、strict lint 0 errors。
- 全库扫描统计22章、127 Markdown、407内部链接、143实体、240关系、367来源、653处正文来源引用。
- 新增知识仍为解析方法研究，KNOW-000020保持in_review；CH12-T003继续IN_PROGRESS，等待联合模型代码实现、能量平衡回归和独立数值验证。


**追加执行切片（2026-11-23）：进给轴驱动链与惯量折算。** 在自由路径坐标双向耦合解析推导后，补充旋转伺服—滚珠丝杠的导程/传动比运动学、正向推力换算、反向回馈效率区分和转动惯量等效到路径坐标的折算公式；补充直线电机推力常数、反电势以及峰值/RMS、相/线测量定义。新增SRC-000368～SRC-000369，CH12字典新增进给轴传动折算记录。**本切片不写入实际机型参数、不新增数值仿真**；所有公式作为元件模型接口，具体值须来自所选电机、驱动器、丝杠目录/辨识。CH12-T003继续 IN_PROGRESS。


### CH12-T003 进给轴传动折算切片CI验收（2026-11-23）

- 内容提交 b6d4a481f987fb72cf5b0eca95ece94c98a6e317 对应GitHub Actions [Run 45046562655]通过；5/5单元测试通过，strict lint PASS（0 errors）。
- 最新扫描：22章、127 Markdown、407内部链接、143实体、240关系、369来源、655处正文引用。
- 新增SRC-000368～SRC-000369和进给轴传动链折算字典记录。所有关系式是接口推导，不含具体丝杠/电机参数；正反向效率、惯量折算和目录常数口径均需按实际器件确认。
- CH12-T003保持IN_PROGRESS，当前没有电机/滚珠丝杠参数标定或驱动器联合仿真。


**追加执行切片（2026-11-23）：龙门自由路径坐标—电流环联合求解器代码实现。** 新增 gantry_joint_drive_solver.py，将 \(q,\dot q,s,\dot s,i,x_i\) 统一为状态向量；按 \(\mathrm{diag}(M_0,m_{s0})+m_pJ^TJ\) 构造对称联合质量矩阵，加入移动点运输项、路径摩擦、重力势能梯度、执行器相对位移雅可比虚功，以及单轴等效RL/连续PI电流环和电压/电流命令限幅。新增 test_gantry_joint_drive_solver.py 共8项资源级测试，包括质量矩阵/零负载、虚功、RL衰减、限幅、静止极限、匹配SI常数下机电储能—铜耗平衡及自由路径状态积分。模型仍为四坐标合成几何与调用方参数化接口；未配置具体机床参数，未实现硬限位、碰撞接触、丝杠扭振/间隙、完整PMSM dq或离散驱动采样。**本切片的资源测试已编写但未执行，不产生任何数值仿真或能量平衡“通过”结论。** CH12-T003继续 IN_PROGRESS。

### CH12-T003 联合求解器资源提交的仓库CI验收（2026-11-23）

- 内容提交 c6e7852048d04487d045e5ff05894fdda8051af7 对应 GitHub Actions [Run 45112047320](https://github.com/rexyll/cnc-knowledge/actions/runs/45112047320) success。
- 仓库现有单元测试 5/5 通过；knowledge_lint strict PASS（0 errors）。该CI仅执行 tests/ 与 scripts/knowledge_lint.py，不运行 resouces/ 下新建的8项联合求解器测试。
- 实际扫描统计：22章、128个Markdown文件、407条内部链接、143条实体、240条关系、371条来源、660处章节正文来源引用。
- 内容提交 SHA：c6e7852048d04487d045e5ff05894fdda8051af7；后续计划/历史补录与测试覆盖完善仍需再次经过CI。
- CH12-T003保持 IN_PROGRESS；本次只完成第一版资源代码/测试编写及仓库静态质量验收，不代表资源脚本已执行、物理模型已验证或实机/HIL通过。


### CH12-T003 联合求解器实现补录CI验收（2026-11-23）

- 计划/历史补录提交 37000932735058741172c70fb663f4a854b5b9c7 对应 GitHub Actions [Run 45112280173](https://github.com/rexyll/cnc-knowledge/actions/runs/45112280173) success；仓库原有单元测试5/5通过，strict lint PASS（0 errors）。
- 本次扫描22章、129 Markdown、407内部链接、143实体、240关系、371来源、660处正文来源引用。
- 测试文件扩展为8项，包含匹配SI常数下机电能量/铜耗平衡与自由路径状态积分；但它们仍未执行。不能将知识结构CI解释为资源代码验证。
- CH12-T003继续 IN_PROGRESS。


**追加执行切片（2026-11-23）：联合求解器静态接口契约补强。** 明确四坐标正弦几何与求解器维度契约，在构造阶段拒绝非四维广义坐标，并增加参数数组/标量、初始状态和积分时长/步长的有限值校验。资源测试由8项扩展为10项，新增维数不匹配与NaN状态拒绝测试；README、ASSET-INDEX和专题正文同步。GitHub Actions Run 45113662565 success（仓库既有测试5/5、strict lint 0 errors），但未执行10项资源测试，不产生仿真/能量平衡结果。CH12-T003继续 IN_PROGRESS。


### CH12-T003 静态接口契约补强补录CI验收（2026-11-23）

- 提交 bd9cb6bf5ebddaac9c804e2bb4fa6eaffae86dc6 对应 GitHub Actions Run 45113772002 success；仓库原有测试5/5通过，strict lint 0 errors。
- 最终扫描：22章、129 Markdown、407内部链接、143实体、240关系、371来源、660处正文来源引用。
- 该CI没有执行10项资源级测试，亦没有生成联合仿真/能量平衡/步长收敛结果；CH12-T003保持 IN_PROGRESS。


**追加执行切片（2026-11-23）：联合求解器运行时输入校验与方程静态核查。** 静态核对联合惯性矩阵、移动点运输项、重力势能梯度与电气反电势/机械执行器功率方向，在本模型理想单端口假设下未发现符号不一致；该结论不等同数值能量验证。增加状态解包、时间戳、电流命令、外部广义力的有限值检查，并修正执行器系数维数检查对数组接口的假设。资源测试增至12项，新增非有限电流指令/外部广义力拒绝测试。Run 45116144419 success（仓库原有测试5/5、strict lint 0 errors），资源测试仍未执行；CH12-T003继续 IN_PROGRESS。


### CH12-T003 运行时输入校验补录最终CI验收（2026-11-23）

- 补录提交 ac731a7d3e80575930f23f55d2848415cd263111 对应 GitHub Actions Run 45116216363 success；仓库现有测试5/5，strict lint 0 errors。
- CI扫描统计22章、129 Markdown、407内部链接、143实体、240关系、371来源、660正文引用。
- 本次资源测试12项仍未实际执行；CH12-T003继续 IN_PROGRESS。


**追加静态审查切片（2026-11-23）：模型参数数组所有权与构造后不可变性。** 发现 `frozen=True` 数据类中的 NumPy 数组仍可被原地修改，可能使模型构造时完成的矩阵对称性/正定性、有限值校验在运行期失效。求解器现对 `M0/D0/K0`、重力向量和执行器坐标系数创建私有浮点快照并设为只读；原零重力测试改为在构造参数中传入零向量，避免测试通过非法原地改参改变模型。资源测试扩展至13项，新增调用方数组修改隔离及模型内部数组只读契约；同步更新专题正文、资源README与ASSET-INDEX。该切片尚未执行资源测试；CH12-T003继续 IN_PROGRESS。


### CH12-T003 参数数组所有权加固切片CI验收（2026-11-23）

- 内容提交 `d48f8f3bdc69b2b780c330f6582c279212643175` 对应 GitHub Actions [Run 45121368649](https://github.com/rexyll/cnc-knowledge/actions/runs/45121368649) success。
- 仓库现有单元测试5/5通过；strict knowledge lint PASS（0 errors）。
- CI扫描：22章、130 Markdown、407内部链接、143实体、240关系、371来源、660处正文来源引用。
- 13项资源级求解器测试未由CI执行；本次无新增数值仿真、参数标定或实机/HIL结果。CH12-T003继续 `IN_PROGRESS`。


**追加静态审查细化（2026-11-23）：不可逆参数数组只读存储。** 复查发现 NumPy 对自有内存的只读数组可能允许通过 `setflags(write=True)` 恢复写权限，因此前一提交的 `write=False` 不是足够强的只读契约。现将模型内部数组构造为不可变 `bytes` 缓冲区的视图，并将资源测试改为逐一验证质量、阻尼、刚度、重力与执行器系数数组不能重新开启写权限。该项仍未实际执行资源测试；CH12-T003继续 IN_PROGRESS。


### CH12-T003 不可逆参数数组只读加固CI验收（2026-11-23）

- 内容提交 `00f84c647e8d212b67b43c54dee7fb6dbf53f00a` 对应 GitHub Actions [Run 45124730690](https://github.com/rexyll/cnc-knowledge/actions/runs/45124730690) success。
- 仓库现有单元测试5/5通过；strict knowledge lint PASS（0 errors）。
- CI扫描：22章、130 Markdown、407内部链接、143实体、240关系、371来源、660处正文来源引用。
- 测试文件中的只读检查已覆盖质量、阻尼、刚度、重力与执行器系数五类数组；资源级13项测试仍未执行。CH12-T003继续 `IN_PROGRESS`。


**追加静态审查切片（2026-11-23）：RK4请求步长与输出时间轴一致性。** `simulate()` 允许 `duration_s/step_s` 在浮点容差内舍入为整数步数，但先前返回时间轴以总时长均分，RK4阶段却使用原始请求步长；现在统一使用 `h=duration_s/count` 作为有效步长。新增回归用例检查每步 (k_4) 时间与下一步 (k_1) 时间一致，资源测试从13项增至14项。资源测试尚未执行；CH12-T003继续 IN_PROGRESS。


### CH12-T003 RK4时间栅格修正CI验收（2026-11-23）

- 内容提交 `cba6a39e55dc981a42c2ea30d72141cd25134e1b` 对应 GitHub Actions [Run 45125109149](https://github.com/rexyll/cnc-knowledge/actions/runs/45125109149) success。
- 仓库既有单元测试5/5通过；strict knowledge lint PASS（0 errors）。
- CI扫描：22章、130 Markdown、407内部链接、143实体、240关系、371来源、660处正文来源引用。
- 新增的RK4时间栅格边界用例属于资源测试，未由该CI执行；14项资源测试均未执行。CH12-T003继续 `IN_PROGRESS`。


**追加模型边界澄清（2026-11-23）：电流指令参考限幅不等同实际电流硬限幅。** 当前 `current_limit_A` 只裁剪电流指令参考值，模型没有把状态电流 `current_A` 瞬时裁剪，也没有模拟驱动器硬件过流比较器、关断、故障锁存或热降额。更新参数/接口说明和专题限制，强化原参考限幅测试，并新增超限状态电流按RL动态变化的回归用例；资源测试由14项增至15项。测试尚未执行；CH12-T003继续 IN_PROGRESS。


### CH12-T003 电流参考限幅边界切片CI验收（2026-11-23）

- 代码/文档提交 `d9b9afbc2948f7b6f9a1e7a148fca96f67026db3` 对应 GitHub Actions [Run 45126336210](https://github.com/rexyll/cnc-knowledge/actions/runs/45126336210) success；测试文件补正提交 `49e52d14c51fb6d2378fb85254f97d35716ff787` 对应 [Run 45126386640](https://github.com/rexyll/cnc-knowledge/actions/runs/45126386640) success。
- 两轮仓库既有测试均5/5通过，strict knowledge lint均PASS（0 errors）；CI扫描统计22章、130 Markdown、407内部链接、143实体、240关系、371来源、660处正文引用。
- 实际资源测试文件包含15个测试方法，但资源级测试未由仓库CI执行；没有验证实际驱动器的硬件过流保护。CH12-T003继续 `IN_PROGRESS`。


**追加静态审查切片（2026-11-23）：RK4阶段回调状态快照隔离。** 发现 simulate() 在同一RK4阶段将同一个可变 JointState 对象依次传给电流指令和外部力回调；回调对内部NumPy数组的原地修改可能串扰后续回调。现分别构造独立阶段快照，回调侧修改不会传给另一回调，也不会回写积分状态。新增资源级回归用例，资源测试由15项增至16项；同步更新联合求解器专题、README与ASSET-INDEX。**资源测试尚未执行，仓库CI不运行资源测试**；CH12-T003继续 IN_PROGRESS。

### CH12-T003 RK4阶段回调状态快照隔离切片CI验收（2026-11-23）

- 内容提交 `61835e5043e32e639f56366ba7a311d660dab03d` 对应 GitHub Actions [Run 45128932385](https://github.com/rexyll/cnc-knowledge/actions/runs/45128932385) success；单元测试步骤与 strict knowledge lint 步骤均成功。
- 仓库CI没有执行 resouces/ 下的16项求解器资源测试；本次结果只证明现有知识库质量工作流通过，不构成资源脚本运行、数值仿真、步长收敛、能量平衡或真实机床/HIL验证。
- 当前资源测试文件包含16个 test 方法，全部仍标记为待独立执行；CH12-T003继续 `IN_PROGRESS`。

**追加静态审查切片（2026-11-23）：电气诊断公开入口输入校验。** 复查发现 `electrical_diagnostics()` 可被外部直接调用，但此前只在 `derivative()` 路径上拒绝非有限电流命令/状态；直接调用可能将NaN/Inf扩散至PI、电压和电流变化率诊断结果。现于公开入口独立校验电流命令有限性，并复用 `pack(state)` 验证状态维数和所有状态字段有限性。新增两项资源级回归测试，分别覆盖NaN/Inf命令与NaN状态；资源测试由16项增至18项。同步更新联合求解器专题、README和ASSET-INDEX。**18项资源测试尚未执行，仓库CI不运行资源测试**；CH12-T003继续 IN_PROGRESS。


### CH12-T003 电气诊断公开入口校验切片CI验收（2026-11-23）

- 内容提交 `8fcbbbbd2aae2c2974ffda64782ff19b8a6042d3` 对应 GitHub Actions [Run 45155665754](https://github.com/rexyll/cnc-knowledge/actions/runs/45155665754) success；仓库既有单元测试步骤与 strict knowledge lint 步骤均成功。
- 测试文件当前包含18个 `test_` 方法；该次CI未执行 `resouces/` 下的18项求解器资源测试，资源级测试仍未执行。
- 本次结果只证明仓库既有质量工作流通过，不构成电流诊断运行时回归、数值仿真、步长收敛、能量平衡、驱动器保护或HIL/实机验证。
- CH12-T003继续 `IN_PROGRESS`。


**追加执行切片（2026-11-23）：联合移动轴—电流环数值验证协议与测试矩阵。** 新增独立协议，明确混合量纲状态分量容差、RK4四档步长收敛与观测阶数、实际限幅端电压下的机电功率预算、匹配 (K_f=K_e) 时的能量抵消条件，以及自由路径轴与理想规定轨迹约束模型的拉格朗日乘子/约束功对照方法。资源目录新增7个RK4/能量工况与1个自由轴对照的CSV验证矩阵，7项均标记 `NOT_RUN`；PATH-01 因规定轨迹降阶参考积分器尚未实现而标记 `BLOCKED`。本切片只完成验证规范与空白矩阵归档，没有运行资源测试或仿真，也没有生成任何数值结论。CH12-T003继续 IN_PROGRESS。


### CH12-T003 联合求解器数值验证协议CI验收（2026-11-23）

- 协议/矩阵归档提交 `020be49b00ea9ba3436718d691d19dcc7625e638` 对应 GitHub Actions [Run 45157109891](https://github.com/rexyll/cnc-knowledge/actions/runs/45157109891) success；仓库既有单元测试步骤与 strict knowledge lint 步骤均成功。
- 本次CI只验证仓库既有质量工作流；18项资源级测试没有执行，RK4/ENE验证矩阵7项 `NOT_RUN`，PATH-01仍为 `BLOCKED`。
- 协议只定义验证方法和验收口径，不产生仿真、能量平衡或实机/HIL结论；CH12-T003继续 `IN_PROGRESS`。


**追加执行切片（2026-11-23）：规定路径降阶参考积分器。** 联合求解器新增 `prescribed_path_derivative()` 与 `simulate_prescribed_path()`：通过调用方提供的确定性 `(s_ref, sdot_ref, sddot_ref)` 路径函数，在RK4阶段只积分结构坐标与电流状态，并按完整质量矩阵分块方程输出约束反力 `lambda`。增加自由方程零反力一致性、约束力符号、路径位置/速度输出、无效初值/非有限路径和回调状态隔离测试，资源测试由18项增至24项。验证矩阵PATH-01由 `BLOCKED` 改为 `NOT_RUN`；积分器实现不代表数值对照通过。资源测试未执行，RK4步长收敛、能量账本和自由/规定路径对照均未运行；CH12-T003继续 `IN_PROGRESS`。


### CH12-T003 规定路径参考积分器切片CI验收（2026-11-23）

- 代码提交 `a5c97addf57aa25a88e2f0e45565de371d8883bc` 对应 GitHub Actions [Run 45160152219](https://github.com/rexyll/cnc-knowledge/actions/runs/45160152219) success。
- 文档/验证矩阵提交 `ecb4639d44e6012ed42ad187c789fe8df2479466` 对应 GitHub Actions [Run 45160363257](https://github.com/rexyll/cnc-knowledge/actions/runs/45160363257) success。
- 两轮均为仓库 `Knowledge Quality` 工作流成功；该工作流不执行 `resouces/` 下的24项求解器资源测试。
- PATH-01 参考积分器已实现，验证矩阵8项均为 `NOT_RUN`；未产生数值对照、步长收敛、约束反力/约束功或能量账本结果。
- CH12-T003继续 `IN_PROGRESS`；真实机床参数辨识与HIL/实机验证未完成。


追加执行切片（2026-11-23）：PATH-01工况、控制输入与结果归档定义。固定五次静止—静止参考轨迹，明确位置/速度/加速度解析表达式；规定自由/理想约束两侧共用同一确定性电流命令回调和外力回调，约束侧额外反力由 lambda 单独记账。定义逐坐标混合单位归一化误差、自由轴路径误差、负载点位置差、约束反力峰值/RMS、约束功和加入 lambda*sdot_ref 的受约束能量账本。新增空白配置JSON、时序CSV与汇总CSV模板，参数和验收阈值全部留空；PATH-01仍为 NOT_RUN。同步纠正验证协议中复测测试数量的旧文字（18更正为24）。


### CH12-T003 PATH-01配置/结果模板CI验收（2026-11-23）

- 模板提交 `d9aca86ce0b8a40a65aecdb22a68a2d9898b6eea` 对应 [Run 45169802109](https://github.com/rexyll/cnc-knowledge/actions/runs/45169802109) success。
- 首轮文档链接提交 `2853347c3a841c21710318636cfa7d81d2eb955f` 的 [Run 45169914782](https://github.com/rexyll/cnc-knowledge/actions/runs/45169914782) 失败，原因为6条Markdown相对链接使用三级上跳并越出仓库根目录；仓库原有单元测试5/5成功，strict lint报告6个链接错误。
- 修复提交 `0fc31fa0589ce0c8358d2c6e2291817fe1a947a4` 将6条路径统一改为两级上跳；[Run 45170044496](https://github.com/rexyll/cnc-knowledge/actions/runs/45170044496) success，单元测试5/5成功，strict knowledge lint PASS。
- PATH-01配置/结果模板已归档，参数/阈值保持空值；PATH-01仍为 `NOT_RUN`。仓库CI不运行 `resouces/` 下的24项求解器资源测试。
- CH12-T003继续 `IN_PROGRESS`。


追加执行切片（2026-11-23）：PATH-01独立对照运行器。新增 gantry_joint_drive_path_comparison.py，将填写后的JSON配置转换为自由轴/规定路径两套求解器的同一几何、机械、电气、初始状态、确定性PD电流回调和常值五维外载；自动执行 h/h2/h4/h8 四档并生成时序CSV、汇总CSV及运行manifest。能量账本拆分端电压功率、铜耗、结构阻尼、轴摩擦、外部功率、(Kf-Ke)*i*ell_dot 与约束功 lambda*sdot_ref。明确v1只支持常值前馈与常值外载，不执行任意JSON代码。增加7项辅助资源测试；24项求解器测试与7项运行器测试均未执行。路径配置、步长、容差、能量尺度和工程阈值均保持待填写，PATH-01继续 NOT_RUN。


### CH12-T003 PATH-01运行器与文档CI验收（2026-11-23）

- 运行器/测试/模板提交 `076ab8290f9bf772e9551b7d50b80dcb17a93a00` 对应 [Run 45171976920](https://github.com/rexyll/cnc-knowledge/actions/runs/45171976920) success。
- 资源README、ASSET-INDEX与专题正文提交 `0ce4a852aa7c78971b83912705603f1941ca625d` 对应 [Run 45172483718](https://github.com/rexyll/cnc-knowledge/actions/runs/45172483718) success。
- PATH-01协议/矩阵/计划提交 `0632571f46c4be7c80a22e24677cf3530e14e896` 对应 [Run 45172703500](https://github.com/rexyll/cnc-knowledge/actions/runs/45172703500) success。
- 运行器实施记录提交 `260c5d82ffec4ffff40a033d8c18d867c5e2576d` 对应 [Run 45172789219](https://github.com/rexyll/cnc-knowledge/actions/runs/45172789219) success。
- 各轮仓库既有单元测试5/5通过、strict knowledge lint成功；CI不执行资源目录下的24项求解器测试和7项运行器测试。
- PATH-01运行器尚未执行，配置参数/容差/能量归一化尺度/工程阈值均留待填写；验证矩阵8项仍为 `NOT_RUN`。CH12-T003继续 `IN_PROGRESS`。


### CH12-T003 PATH-01运行器最终补录CI验收（2026-11-23）

- 最新补录提交 `574c5e8c1fdf3e04e4aba6b9c1341f744ffa9736` 对应 GitHub Actions [Run 45172904724](https://github.com/rexyll/cnc-knowledge/actions/runs/45172904724) success。
- 单元测试步骤5/5通过；strict knowledge lint成功。此前运行器提交、资源说明、协议/矩阵与TaskPlan提交对应的CI Run 45171976920、45172483718、45172703500和45172789219也均成功。
- 运行器输入/输出契约已补入TaskPlan；资源运行器和7项辅助资源测试未执行，原24项求解器资源测试未执行；矩阵8项仍为 `NOT_RUN`。CH12-T003保持 `IN_PROGRESS`。


### CH12-T003 PATH-01限幅感知收敛适用域与诊断补强（2026-11-23）

- **审查问题：** 原有 h/h2/h4/h8 观测阶数筛查未区分电流参考限幅和PI输出电压饱和。若非光滑限幅切换发生在RK4内部阶段，只查看输出时间网格会漏检，可能将限幅工况错误地解释为光滑右端项的经典RK4收敛表现。
- **实现：** 运行器在自由/规定路径两种模型的每次电流命令回调中调用电气诊断，累计每次回调的电流参考限幅、电压饱和与任一限幅标志；按4次/积分步校验RK4阶段数。规定路径积分器结束时额外进行一次终点诊断，该回调从RK4阶段统计中剔除。
- **时序输出：** 新增请求电流命令、限幅后电流参考值、电流参考限幅布尔值和电压饱和布尔值；这些字段为输出采样点快照。
- **汇总输出：** 新增预期/实际RK4阶段数、两类限幅激活阶段数、任一限幅激活阶段数、激活比例、阶段计数一致性与 `smooth_unsaturated_regime`。
- **验收门控：** 既有收敛筛查仍报告数值误差/观测阶；只有两侧阶段计数完整且所有阶段均无参考限幅/电压饱和，才具备常规光滑工况下继续评估工程PASS的资格。若收敛筛查通过但检测到限幅或阶段数不完整，状态限定为 `COMPLETED_REPORT_ONLY`；若收敛筛查失败仍为 `FAIL`。此统计不表示硬件过流保护。
- **资源测试：** 运行器辅助测试新增3项，方法数从7增至10；求解器24项不变，资源测试合计34项，全部未执行。仓库Knowledge Quality CI不运行这些资源测试。
- **同步文件：** 运行器、运行器测试、两份CSV模板、资源README、ASSET-INDEX、数值验证协议第5.3节、龙门联合模型专题第7.6.12节。
- **状态：** PATH-01仍为 `NOT_RUN`，没有新数值轨迹、步长收敛、能量残差或工程验收结论；CH12-T003继续 `IN_PROGRESS`。本切片提交 `7ceda93f04edb8ffffd7ce6c365d16d1db868816` 对应 GitHub Actions [Run 45181996783](https://github.com/rexyll/cnc-knowledge/actions/runs/45181996783) success；仓库既有单元测试5/5通过，strict knowledge lint success。该CI不运行 `resouces/` 下34项资源测试。


### CH12-T003 PATH-01全细化序列限幅门控修正（2026-11-23）

- **复核发现：** 上一版 `smooth_unsaturated_regime` 在单档汇总中表示该档是否未触发限幅，但最终 `_acceptance_decision()` 只读取最细 `h/8` 的单档标志。由于观测阶数由四档 `h/h2/h4/h8` 共同计算，这会允许粗档限幅却最细档无饱和时误判为具备光滑收敛解释资格。
- **修改：** 新增 `all_refinements_smooth_unsaturated_regime`，要求四个细化档的自由/规定路径两模型阶段计数全部准确，且所有RK4阶段均无电流参考限幅和电压饱和。最终验收门控与manifest聚合字段均使用全序列标志；逐档标志仍保留在汇总CSV。
- **测试：** 新增两项验收门控纯函数测试，分别验证粗细档任一处限幅均禁止工程PASS，以及收敛筛查失败仍优先FAIL。运行器辅助资源测试由10项增至12项；连同求解器24项共36项，均未执行。
- **输出：** 汇总CSV模板新增全序列聚合列；资源README、ASSET-INDEX、协议第5.4节与专题正文第7.6.13节同步说明。
- **CI验收：** 提交 `95cd8b149d8d628f8ab59064aee33ec110d249cc`；GitHub Actions [Run 45183631562](https://github.com/rexyll/cnc-knowledge/actions/runs/45183631562) success，仓库单元测试与strict knowledge lint均成功。此CI不执行资源级测试。


### CH12-T003 PATH-01限幅标志口径一致性（2026-11-23）

- **审查发现：** RK4内部阶段的指令参考裁剪判断采用精确比较，而输出时序/能量账本采用 `1e-12` 绝对容差，极小裁剪可能只出现在阶段汇总、却未在输出采样列呈现。
- **处理：** 新增 `_current_reference_was_limited()` 统一函数，阶段计数和输出网格时序使用同一精确比较：裁剪后参考值与请求电流命令数值不同即为限幅。
- **测试：** 新增相邻IEEE浮点数裁剪用例，覆盖仅一个可表示浮点间隔的裁剪以及相等值不算裁剪。PATH运行器测试由12项增至13项，连同求解器24项共37项，均未执行。
- **同步：** 运行器、测试、资源README、ASSET-INDEX、数值验证协议5.5节、专题正文7.6.14节与本章TaskPlan/History。
- **CI验收：** 提交 `a93a9dadf03be2d31d2a8d7124a602cb6a759cf4`；GitHub Actions [Run 45183921384](https://github.com/rexyll/cnc-knowledge/actions/runs/45183921384) success，仓库单元测试与strict knowledge lint均成功。此CI不执行资源级测试。


### CH12-T003 PATH-01输入来源追溯补强（2026-11-23）

- **审查发现：** 空白配置模板含 `provenance.source_documents_or_measurement_ids`，但运行器未验证该字段类型、空项/重复项，也没有将具体来源ID写进manifest；仅记录 `parameter_source` 与配置SHA，不便于执行结果反查参数依据。
- **处理：** 新增 `_source_document_ids()`，要求JSON字符串数组、每项非空、trim后不重复；允许空数组（如明确标识合成夹具、无独立来源ID）。manifest保留规范化后的 `source_documents_or_measurement_ids` 数组。
- **测试：** 新增3项纯函数测试，覆盖非数组、空白/非字符串项，以及去空白与重复值拒绝。运行器辅助测试16项；求解器24项，合计40项资源测试均未执行。
- **同步：** 运行器、资源测试、README、ASSET-INDEX、数值验证协议5.6节、专题正文7.6.15节与本章TaskPlan/History。
- **CI验收：** 提交 `35b25251666da1ab302f1da9b8771d6e1f58a39b`；GitHub Actions [Run 45184190958](https://github.com/rexyll/cnc-knowledge/actions/runs/45184190958) success，仓库单元测试与strict knowledge lint均成功。此CI不执行资源级测试。


### CH12-T003 PATH-01限幅与来源追溯静态审查阶段汇总（2026-11-23）

- **最新代码提交：** `35b25251666da1ab302f1da9b8771d6e1f58a39b`，保留参数来源ID并增加配置输入校验。
- **相关CI：** `95cd8b1` / [Run 45183631562](https://github.com/rexyll/cnc-knowledge/actions/runs/45183631562)、`a93a9da` / [Run 45183921384](https://github.com/rexyll/cnc-knowledge/actions/runs/45183921384)、`35b2525` / [Run 45184190958](https://github.com/rexyll/cnc-knowledge/actions/runs/45184190958) 均 success；每次仓库既有单元测试步骤与 strict knowledge lint 步骤均成功。
- **静态核对：** PATH-01时序字段73列、汇总字段71列，均与对应CSV模板字段名/顺序一致；运行器辅助测试16项，求解器测试24项，共40项资源测试均未执行。
- **验收状态：** 验证矩阵8项全部 `NOT_RUN`；PATH-01没有数值运行结果；真实机床参数辨识、HIL/实机验证未完成。CH12-T003保持 `IN_PROGRESS`。


### CH12-T003 PATH-01电压饱和精度与能量残差求积输出（2026-11-23）

- **电压限幅缺陷：** `electrical_diagnostics()` 原用 `np.isclose(voltage, raw_voltage, atol=1e-12)` 生成 `voltage_saturated`，极小的真实裁剪可能被漏标，进而干扰四档全细化序列限幅门控。现精确比较裁剪后 `voltage_V` 与 `raw_voltage_V`，任何可表示数值差均标记饱和；新增正/负电压轨一ULP越界测试。
- **能量输出缺项：** `_energy_metrics()` 已返回梯形积分能量残差，但汇总层未使用该字段。新增 `free_energy_residual_trapezoid_J` 与 `prescribed_energy_residual_trapezoid_J` 两列，作为Simpson 1/3主残差的求积敏感性对照；验收阈值与主残差定义不变。
- **资源测试数量：** 求解器测试从24增至25项，运行器测试从16增至17项，共42项资源测试，均未执行。
- **同步文件：** 求解器、求解器测试、PATH-01运行器/测试、汇总CSV模板、资源README、ASSET-INDEX、数值验证协议5.7节、专题正文7.6.16节、本章TaskPlan与本历史。
- **CI验收：** 内容提交 `5c24dcbcfeb8be4543dbef44dd81f333c63635d1` 对应 [Run 45188707292](https://github.com/rexyll/cnc-knowledge/actions/runs/45188707292) success；仓库单元测试步骤与strict knowledge lint步骤均成功。该CI不运行资源级测试。
- **静态核对：** 求解器25项、PATH-01辅助测试17项，共42项资源测试未执行；汇总CSV模板/运行器字段均为73列，名称与顺序一致。
- **状态：** PATH-01仍未模拟、验证矩阵8项仍 `NOT_RUN`，CH12-T003继续 `IN_PROGRESS`。


### CH12-T003 PATH-01结果归档哈希绑定与失败恢复（2026-11-23）

- **审查发现：** 运行manifest此前记录配置SHA、求解器/运行器SHA与Git SHA，但未记录时序CSV和汇总CSV自身的内容摘要；CSV直接写入最终路径，写入/发布中途失败可能留下不完整结果，并阻碍后续无覆盖重跑。
- **完整性绑定：** manifest升级为 schema_version: 2，新增 output_artifacts；对两份CSV分别记录最终文件名、SHA-256、字节数、数据行数和列数。哈希在暂存文件完整写出后计算；manifest不对自身做自哈希。
- **发布与恢复：** 两份CSV和manifest先在输出目录内临时子目录完整暂存。暂存阶段发生异常时，已有归档不会被触碰；发布前先删除旧manifest，再逐个替换CSV，最后发布新manifest作为完成标记。发布阶段中断时不保留旧manifest，目录内残留CSV不构成完整归档；运行器识别“CSV存在但manifest缺失”，提示检查后通过 --force 重跑整套结果或改用新目录。
- **回归用例：** 新增3项资源测试，分别校验CSV哈希/字节数/行列数、暂存失败保护旧归档，以及发布中断时manifest失效并可整套重跑。PATH-01运行器辅助测试由17项增至20项；求解器25项不变，共45项资源测试均未执行。
- **同步归档：** PATH-01运行器与测试、资源README、ASSET-INDEX、数值验证协议5.8节、专题正文7.6.17节、本TaskPlan与本历史。
- **静态审查边界：** 仅完成代码/测试用例/文档的静态更新；没有执行资源测试或PATH-01模拟，没有新增数值结果。多文件发布不是跨文件整体事务；只有manifest存在且两份CSV元数据/哈希校验一致时，才可将该输出集视为已发布归档。
- **CI验收：** 内容提交 e063555b9b48104e29f83a25ed8e258f0bc1a734 对应 [Run 45190354624](https://github.com/rexyll/cnc-knowledge/actions/runs/45190354624) success；仓库单元测试步骤与strict knowledge lint均成功，该CI不执行资源级测试。
- **静态核对：** PATH-01辅助测试方法20项、求解器测试25项，共45项资源测试均未执行；时序/汇总CSV运行器字段均为73列，分别与模板名称及顺序一致；输出发布顺序为移除旧manifest、替换两份CSV、最后发布新manifest。
- **状态：** CH12-T003继续 IN_PROGRESS；PATH-01与验证矩阵8项维持 NOT_RUN。


### CH12-T003 PATH-01独立归档校验与配置/CLI边界强化（2026-11-23）

- **归档校验缺口：** 原manifest虽保存CSV摘要，但没有独立CLI验真入口。新增 `--verify-archive --output-dir <dir>`，无需原配置、不构造模型、不执行仿真。
- **校验内容：** 固定时序/汇总文件名与manifest映射、manifest schema_version 2/case/status、两份CSV SHA-256/字节数/数据行数/列数、精确表头及每行列宽；拒绝manifest路径覆盖。返回 `VERIFIED` 时同时保留原运行 `recorded_run_status`，明确其只表示归档元数据一致，不代表数值或工程验收有效。
- **配置边界：** 要求schema_version为整数1（拒绝布尔true）；来源文档/测量ID数组必须显式存在，无ID时填空数组；非null验收profile ID必须为非空字符串并规范化。
- **异常边界：** 超大整数转float溢出转为配置错误；步长比值必须有限且落在平台索引范围，并确保h/8细化后的区间数可表示。CLI增加无配置归档校验模式，对文件/JSON/配置/溢出/模型运行异常显示 `PATH-01 ERROR` 并返回2。
- **回归用例：** PATH-01运行器测试由20项增至32项，涵盖归档校验、同尺寸哈希篡改、manifest状态类型、路径覆盖拒绝、配置schema/source ID、数值溢出/细化索引及CLI成功/失败路径；求解器测试25项不变，共57项资源测试全部未执行。
- **同步文件：** PATH-01运行器/测试、资源README、ASSET-INDEX、数值验证协议5.9节、专题正文7.6.18节与本章TaskPlan/History。
- **CI验收：** 内容提交 `decf6ce69653d9fb82f5a88fc1c548becd4eb76f` 对应 [Run 45199785490](https://github.com/rexyll/cnc-knowledge/actions/runs/45199785490) success；仓库单元测试和strict knowledge lint均成功。该CI不运行resouces资源测试。
- **静态核对：** 运行器测试方法32项；验证器拒绝manifest路径覆盖并核对SHA/字节数/表头/行列，CLI独立验证不需要配置；schema/来源ID/数值边界检查在积分前执行。
- **状态与边界：** PATH-01仍为 `NOT_RUN`，验证矩阵8项仍全部 `NOT_RUN`；没有执行57项资源测试或任何数值仿真，亦无实机/HIL结论。CH12-T003继续 `IN_PROGRESS`。

### CH12-T003 联合质量矩阵尺度均衡求解与能量账本极端值防护（2026-11-23）

- **质量矩阵求解：** 自由路径5×5联合质量矩阵和规定路径4×4结构主子块统一使用对角尺度均衡Cholesky；同步缩放RHS并恢复原变量，校验矩阵/RHS有限性、尺度化后的对称性及Cholesky可分解性。新增 scaled_joint_mass_matrix_condition_number(q, s)，报告单位对角归一化矩阵的特征值比，仅作惯性耦合诊断，不设通用PASS阈值。
- **能量极端值：** 机械储能、磁场储能、电气诊断、逐采样点能量账本、Simpson/梯形积分与最终能量指标对NaN/Inf/溢出显式失败；梯形求积校验数组形状、样本有限性和时间单调性。
- **资源回归用例：** 求解器新增5项（混合坐标量级求解、尺度归一化条件指标、非SPD拒绝、模型条件指标、有限输入引起的储能溢出）；PATH-01新增2项（能量账本非有限输入拒绝、梯形输入契约），现分别为30项与34项，共64项资源测试，全部未执行。
- **内容提交与仓库CI：** 7420db400200fd2722445c35a56859f8802bb68e；GitHub Actions [Run 45203091144](https://github.com/rexyll/cnc-knowledge/actions/runs/45203091144) success。CI既有单元测试与strict knowledge lint成功，但不运行resouces资源测试。
- **验证边界：** 未执行资源测试、PATH-01数值仿真或能量平衡实验；未给出任何实际工况条件数、求解误差或能量残差数值。PATH-01和矩阵8项继续 NOT_RUN，CH12-T003保持 IN_PROGRESS。
- **文档同步CI：** 协议5.10节、专题7.6.19节、资源README、ASSET-INDEX、TaskPlan与TaskHistory同步提交 `f544a08ee49bc40490e2451ddec6f85617e748e3`；GitHub Actions [Run 45203542953](https://github.com/rexyll/cnc-knowledge/actions/runs/45203542953) success，既有单元测试与strict knowledge lint均成功。该工作流不执行64项资源测试。


### CH12-T003 M0构造期正定性预检尺度一致性（2026-11-23）

- **问题：** 动力学方程已采用对角尺度归一化Cholesky，但构造期M0正定性仍基于原始混合单位矩阵的最小特征值，预检和求解算法尺度口径不一致。
- **修正：** M0正定性检查与实际求解共用对角归一化方法，在归一化矩阵上执行Cholesky。只调整M0严格正定预检，不改变D0/K0半正定要求。
- **回归用例：** 新增跨多个数量级的合法SPD矩阵接受测试，以及尺度归一化后不定矩阵拒绝测试。求解器测试32项、PATH-01运行器34项，共66项资源测试，全部未执行。
- **验证边界：** 本轮为代码/测试定义与静态审查，未执行资源测试或PATH-01仿真；验证矩阵8项继续NOT_RUN。

- **M0预检提交/CI：** 代码提交 `039d9f7b53dcfb9ed57beb1d92947fa5b64c829f` 对应 [Run 45206627681](https://github.com/rexyll/cnc-knowledge/actions/runs/45206627681) success；既有单元测试与strict knowledge lint均成功。协议/资源索引/计划历史提交 `2a35bc405a0276cf2685bc350ef2f3587c14e285` 对应 [Run 45206901778](https://github.com/rexyll/cnc-knowledge/actions/runs/45206901778) success。两次CI均不运行66项资源测试。

### CH12-T003 机电功率互易与规定路径约束功符号契约（2026-11-23）

- **机电端口：** 核对电气端口方程 v=R*i+L*di/dt+Ke*ell_dot 与机械广义力 Ja.T*Kf*i，联合储能预算中的互易不匹配项为有符号 (Kf-Ke)*i*ell_dot；匹配SI互易常数时为零，不能作为始终非负耗散量。
- **约束功：** 约束力按正向 +s 广义力定义，规定路径能量账本应加 +lambda*sdot_ref；反向速度自然变号；自由路径无理想约束，约束功必须为零。
- **回归用例：** 新增3项PATH-01测试覆盖端口互易项正/负/零、规定路径正/反向约束功及自由模型排除约束功。求解器32项、运行器37项，共69项资源测试均未执行。
- **内容提交与仓库CI：** 代码测试提交 f28696c3df90b7a29b2a1a959a5ff8a0f66b5d6d；GitHub Actions [Run 45208562193](https://github.com/rexyll/cnc-knowledge/actions/runs/45208562193) success，仓库既有单元测试步骤和 strict knowledge lint 均成功。该CI不执行资源测试。
- **验证边界：** 仅补强代数/符号契约测试及文档；未运行ENE-01～03、PATH-01仿真或能量收敛分析。验证矩阵8项继续 NOT_RUN，CH12-T003保持 IN_PROGRESS。


### CH12-T003 阻尼耗散与外部广义力功率符号复核（2026-11-24）

- **解析核对：** 结构阻尼功率为 q_dot.T @ D0 @ q_dot；轴向摩擦功率为 (b*s_dot + Fc*tanh(s_dot/v_eps))*s_dot。按当前参数约束（D0半正定、b/Fc非负、v_eps正），两项理论上非负，速度反向不改变耗散符号。
- **外力功率：** P_ext=Q_ext.T @ [q_dot,s_dot]，属于有符号输入/输出项。固定外力下速度反向应反号，力与速度正交时为零；账本与动力学方程采用相同广义坐标顺序。
- **测试：** 新增2项PATH-01资源测试；运行器39项、求解器32项，共71项资源测试，均未执行。
- **提交/CI：** 测试提交 `451ca951ff54b8eb9377f09e44f08abb8fa9ecb4`；GitHub Actions [Run 45307608288](https://github.com/rexyll/cnc-knowledge/actions/runs/45307608288) success。该工作流不执行 `resouces/` 资源测试。
- **验证边界：** 本轮只完成代数审查和单样本符号契约测试定义；未执行ENE-02/03积分、PATH-01数值仿真或HIL。验证矩阵8项继续 `NOT_RUN`，CH12-T003保持 `IN_PROGRESS`。
