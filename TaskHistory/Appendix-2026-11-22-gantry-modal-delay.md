# 历史附录：双驱龙门横梁模态、负载位置与离散延迟（2026-11-22）

> 时区：Asia/Shanghai (UTC+08:00)  
> 主历史文件：`TaskHistory/TaskHistory-2026-11-22.md`  
> 分支：`main`（提交前后均核验仅有main分支）

## 工作范围与边界

在前一轮双驱龙门2自由度MIMO对象上扩展4个广义坐标：

`q=[x_common, yaw, beam_bending, beam_torsion]`

使用位置相关质量矩阵 `M(xi,mp)=M0+mp*g(xi)*g(xi)^T`，负载质量5/15/30kg、归一化位置0.1～0.9，共27个冻结LTI工况。横梁跨度、质量矩阵、模态频率和阻尼全部是合成假设，不是有限元或实验模态辨识结果。

每个工况按1ms采样周期精确ZOH离散化，并将0～6ms整数命令FIFO延迟显式并入离散闭环状态矩阵。没有模拟负载连续移动过程中的 `Mdot`、科氏/离心项、非整数延迟、抖动、丢帧或左右轴时钟偏斜。

## 结果摘要

### 模态扫描

27个冻结负载工况下3个柔性/转动耦合模态的频率范围：

- 模态1：20.12～26.85Hz
- 模态2：27.14～49.02Hz
- 模态3：74.16～76.43Hz

模态编号按各工况频率排序，未使用MAC/子空间方法跨工况跟踪振型；接近/交叉时不应把排序编号当作固定物理模态身份。

### 离散延迟稳定工况数

每个单元格为27个负载位置/质量冻结工况中，离散闭环全部极点位于单位圆内的工况数：

| 控制器 | 0ms | 1ms | 2ms | 3ms |
|---|---:|---:|---:|---:|
| 独立双轴PD | 27/27 | 27/27 | 27/27 | 0/27 |
| 同步低P-D | 27/27 | 27/27 | 10/27 | 0/27 |
| 同步中P-D | 27/27 | 27/27 | 5/27 | 0/27 |
| 同步P-only | 27/27 | 27/27 | 9/27 | 0/27 |

在本合成对象中，独立PD可保持至2ms全工况稳定，而交叉同步候选在2ms出现不同数量的冻结工况失稳；这不是同步控制普遍降低延迟鲁棒性的定理，也不能作为真实设备的允许延迟上限。

### 一毫秒延迟下的时域样例

| 负载质量 / 位置 | 控制器 | 峰值同步误差 | 峰值横梁弯曲 |
|---|---|---:|---:|
| 5kg / 0.1 | 独立PD | 54.89μm | 32.19μm |
| 5kg / 0.1 | 同步中P-D | 53.02μm | 32.96μm |
| 15kg / 0.5 | 独立PD | 42.08μm | 205.37μm |
| 15kg / 0.5 | 同步中P-D | 36.73μm | 205.93μm |
| 30kg / 0.9 | 独立PD | 239.34μm | 99.58μm |
| 30kg / 0.9 | 同步中P-D | 228.43μm | 110.78μm |

同步P-D降低两侧位置差，但部分工况横梁弯曲峰值上升；同步误差、结构变形与负载点轨迹误差不可互相替代。

### 采样小增益诊断

对15kg中心负载使用1024点离散频率网格。独立PD的采样 `1/max sigma_max(T)` 指示量在0/1/2ms分别为0.6773/0.3539/0.0315；同步低P-D为0.6402/0.3026（2ms名义闭环已不稳定）；同步中P-D为0.6071/0.2566（2ms名义闭环已不稳定）。

该数字是有限频率网格估计，不是严格H∞上界、disk margin、结构化μ或鲁棒稳定证明。名义闭环不稳定的工况不发布小增益半径。

## 交付文件

正文：

- `docs/12-control-and-machining-algorithms/gantry-mimo-modal-load-position-delay-robustness.md`

资源：

- `resouces/12-control-and-machining-algorithms/gantry-modal-delay-study.py`
- `resouces/12-control-and-machining-algorithms/gantry-modal-delay-study-config.json`
- `resouces/12-control-and-machining-algorithms/gantry-mimo-modal-position-envelope.csv`
- `resouces/12-control-and-machining-algorithms/gantry-mimo-delay-robustness-envelope.csv`
- `resouces/12-control-and-machining-algorithms/gantry-mimo-discrete-step-comparison.csv`
- `resouces/12-control-and-machining-algorithms/gantry-mimo-discrete-small-gain-margin.csv`

新增来源SRC-000352～SRC-000360，新增文章实体KNOW-000019；CH08/CH12数据字典各增加3项字段。无来源关系边，因为来源记录不是实体关系目标；来源链通过文章实体source_ids和正文SRC引用维护。

## 验证与提交

- 本地参考实现脚本完成 `py_compile` 并运行，输出27个模态工况、756组离散极点延迟工况、9个阶跃样例和16个中心负载小增益诊断点。仓库中的资源脚本采用同一模型/状态方程和延迟队列关系的精简重写版本；本轮CI不执行资源脚本，不能把CI视为仿真运行验证。
- 内容提交：`c51f68ed9003e168e2cda47d66986f81e2d5a784`
- GitHub Actions：[Run 45033980670](https://github.com/rexyll/cnc-knowledge/actions/runs/45033980670) success；5/5单元测试通过；strict lint PASS（0 errors）。
- 内容提交CI统计：22章、123个Markdown文件、399条内部链接、142条实体、240条关系、360条来源、642处正文来源引用。
- 模型仅为合成低阶假设模态与冻结负载位置，不包含FE、实验模态、连续移动质量全动力学、HIL或实机测试。没有计算严格multiloop disk margin。

## 任务状态

- CH08-T002：IN_PROGRESS
- CH08-T003：IN_PROGRESS
- CH12-T003：IN_PROGRESS

上述任务仅完成本专题切片，其他主轴功能、速度规划、误差补偿等工作仍待继续。
