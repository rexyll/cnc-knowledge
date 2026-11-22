# 2026-11-22 龙门双驱模型数值更正与连续移动负载研究附录

> 本附录记录本轮在main分支的模型更正、移动质量时变推导、数值核验、交付物与验证边界。所有模型参数和结果是项目原创合成示例，不代表实际数控机床，也不构成安全/性能证明。

## 1. 任务范围与提交

- 起始main：839ec44c9b02f85efd92d0d585f21411447e03b8；仓库仅有main分支。
- 内容提交：c2f624767c85202e2520932245611eea163f0da3。
- 内容CI：[Run 45036988333](https://github.com/rexyll/cnc-knowledge/actions/runs/45036988333) completed/success；5/5单元测试通过；strict lint PASS（0 errors）。
- 本轮聚焦两件事：先纠正上一轮冻结位置模型中的交叉阻尼量纲错误；再从移动负载点速度和动能推导连续规定轨迹的时变模型，并定义真正的MIMO multiloop disk margin接口。

## 2. 冻结位置模型数值更正

### 2.1 根因

旧脚本的偏航/扭转交叉阻尼系数误使用刚度矩阵对角项，形式为 D_psi_theta=0.03*sqrt(K_psi_psi*K_theta_theta)。该式把刚度量纲带入阻尼矩阵，导致阻尼交叉项量纲不一致。现已替换为：

D_psi_theta=0.03*sqrt(D_psi_psi*D_theta_theta)

脚本与配置均已修正。该错误不改变无阻尼广义特征值 K v=omega^2 Mv 的结果，但会改变阻尼矩阵、闭环极点、时域阶跃和频域小增益诊断。因此旧版本的延迟稳定性表、阶跃数值和小增益数值已被新结果覆盖，不再作为有效结果引用。

### 2.2 修正后的离散稳定工况数

每格为27个冻结负载质量/位置工况中离散闭环极点位于单位圆内的数量：

| 控制器 | 0ms | 1ms | 2ms | 3ms |
|---|---:|---:|---:|---:|
| 独立双轴PD | 27/27 | 27/27 | 27/27 | 3/27 |
| 同步低P-D | 27/27 | 27/27 | 27/27 | 0/27 |
| 同步中P-D | 27/27 | 27/27 | 10/27 | 0/27 |
| 仅同步P | 27/27 | 27/27 | 27/27 | 0/27 |

4～6ms时所有控制器均为0/27稳定。本表是该合成模型的结果，不是任何实际龙门系统的延迟保证。

### 2.3 修正后的1ms延迟阶跃示例

| 负载/位置 | 控制器 | 同步误差峰值 | 横梁弯曲峰值 |
|---|---|---:|---:|
| 5kg / ξ=0.1 | 独立PD | 76.15 μm | 30.59 μm |
| 5kg / ξ=0.1 | 中同步P-D | 71.78 μm | 31.67 μm |
| 15kg / ξ=0.5 | 独立PD | 9.49 μm | 204.79 μm |
| 15kg / ξ=0.5 | 中同步P-D | 8.24 μm | 204.81 μm |
| 30kg / ξ=0.9 | 独立PD | 292.15 μm | 82.74 μm |
| 30kg / ξ=0.9 | 中同步P-D | 272.23 μm | 93.71 μm |

同步误差略有改善不意味着结构弯曲同步改善；重载边缘示例中，横梁弯曲峰值反而增加。

### 2.4 修正后采样小增益指示量

15kg中心冻结工况，1024点有限频率网格，输出乘性无结构小增益诊断量 1/max singular value(T)：

| 控制器 | 0ms | 1ms | 2ms |
|---|---:|---:|---:|
| 独立PD | 0.69570 | 0.39015 | 0.08480 |
| 同步低P-D | 0.65482 | 0.33150 | 0.02232 |
| 同步中P-D | 0.61804 | 0.27894 | 名义闭环不稳定 |
| 仅同步P | 0.64319 | 0.32873 | 0.02418 |

此量不是disk margin，也不是连续频率严格H-infinity上界。原脚本对应3份CSV已重算并覆盖。

## 3. 连续移动负载时变模型

### 3.1 动能与方程

广义坐标 q=[x_c,psi,eta_b,theta_t]^T，规定负载位置为s(t)，空间位置：

r(q,s)=r0(s)+Phi(s)q

移动点速度和加速度：

r_dot = Phi*q_dot + r_s*s_dot

r_ddot = Phi*q_ddot + 2*Phi_s*q_dot*s_dot + r_ss*s_dot^2 + r_s*s_ddot

T = 0.5*q_dot.T*M0*q_dot + 0.5*mp*r_dot.T*r_dot

因此：

M(s)=M0+mp*Phi.T*Phi

Mdot=mp*(Phi_s.T*Phi+Phi.T*Phi_s)*s_dot

结构广义坐标q的拉格朗日方程中保留速度交叉项 2*mp*Phi.T*Phi_s*q_dot*s_dot 和路径运输项 mp*Phi.T*(r_ss*s_dot^2+r_s*s_ddot)。不得将整个速度项简单替换为0.5*Mdot*q_dot。该推导依据移动梁/移动质量研究中的移动点链式法则和拉格朗日方程 [SRC-000361][SRC-000362]。

本轮s(t)是外部规定轨迹；尚未把负载轴驱动器自由度、摩擦、约束及其对横梁结构的反向作用联立，故明确为单向规定轨迹时变模型，不是完整双向耦合模型。

### 3.2 假设与核验

- 跨距1.6m；四广义坐标；偏航/弯曲/扭转名义目标频率约25/50/72Hz；质量5/15/30kg。
- 负载从0.1L移动到0.9L，五次平滑轨迹2.0s；最大设定速度1.2m/s；结束时域2.5s；积分步长1ms，RK4。
- 两种控制器（独立PD、中等同步P-D），三种对象模式（完整移动、只保留M(s)、冻结起始位置），共18组×2500个积分步。
- 123组方程检查：最大Mdot有限差分相对误差2.49e-10；负载点加速度链式法则误差4.35e-7；q行Euler–Lagrange残差8.89e-10；增广(q,s)质量矩阵在所声明坐标缩放下最小特征值2.02059。
- 30kg边缘移动示例中，冻结起点模型将独立PD负载点位置误差RMS从完整移动模型的8.486μm低估到1.582μm；同步P-D从8.331μm低估到1.257μm。完整模型和只变质量模型的差异很小，说明本次2s平滑轨迹下的运输项数值贡献较小，不能外推到高速或真实模态。

### 3.3 交付与代码验证边界

- 正文：[连续移动负载时变模型与多回路disk margin](../docs/12-control-and-machining-algorithms/gantry-continuous-moving-load-and-multiloop-disk-margin.md)。
- CSV：resouces/12-control-and-machining-algorithms/gantry-moving-load-model-comparison.csv、gantry-moving-load-equation-checks.csv。
- 脚本：resouces/12-control-and-machining-algorithms/gantry-moving-load-study.py；配置同目录。
- **重要复现声明：** CSV来自本轮已完成的参考计算结果导出；新提交的资源脚本是可运行复现实现，但本批次CI没有执行该脚本，本轮也未完成该精确提交版本的本地回归。因此，不能仅凭CSV/CI通过声明该脚本已执行验证；后续需单独用Python 3.10+、NumPy、SciPy运行并对照CSV。

## 4. MIMO multiloop disk margin方法边界

- 设P(z)为两驱动力到两编码器等效位置的2×2离散对象，C(z)为双通道控制器。对象输出反馈扰动端口使用PC；对象输入执行器端口使用CP。两者扰动位置不同，应分别报告。
- MathWorks diskmargin提供loop-at-a-time及多回路分析，逐回路裕度不等同同时多回路裕度 [SRC-000359]。
- python-control MIMO disk_margins路径使用Slycot AB13MD结构奇异值上界；其上界倒数形成保守逐频率样本disk-margin下界估计 [SRC-000363][SRC-000364]。资源脚本定义1024点网格0.2～499Hz，并命名为采样最小disk-margin估计，不声称全频率认证。
- 当前工作环境缺少python-control/Slycot，本轮没有生成disk-margin数值。不能用 1/max singular value(T) 冒充disk margin。需装依赖后与MATLAB Robust Control Toolbox交叉核验。

## 5. 遗留事项和状态

1. 对提交的gantry-moving-load-study.py进行语法和数值回归，验证与已归档CSV一致；CI当前不执行资源脚本。
2. 安装兼容python-control/Slycot，运行PC、CP两端口MIMO multiloop disk margin；记录工具版本、频率网格、算法返回含义及稳定前置检查。
3. 后续若扩展到双向耦合，必须增加负载轴动力学并从完整(q,s)拉格朗日方程推导，不要把规定轨迹模型说成双向耦合。
4. CH08-T002、CH08-T003、CH12-T003均保持IN_PROGRESS；本轮仅完成专题切片。

## 6. 版本与验收

- 仅在main分支操作；内容提交c2f624767c85202e2520932245611eea163f0da3。
- GitHub Actions [Run 45036988333](https://github.com/rexyll/cnc-knowledge/actions/runs/45036988333) success；5/5单元测试通过；strict lint PASS（0 errors）。
- 当前内容批次CI结构统计：22章、125 Markdown、401内部链接、143实体、240关系、364来源、649正文引用；计划/历史补录后会再次执行CI更新统计。


## 7. 计划/历史补录CI验收

- 计划/历史补录提交：1abcbc4ae1d4400586b49fd7767f61f020ec5362。
- GitHub Actions [Run 45037385127](https://github.com/rexyll/cnc-knowledge/actions/runs/45037385127) completed/success；5/5单元测试通过；strict lint PASS（0 errors）。
- 该次CI统计：22章、126个Markdown文件、406条内部链接、143条实体记录、240条关系记录、364条来源记录、649处正文来源引用。
- 根TaskPlan本次将补入本研究入口和本历史附录两条导航链接，统计值按下一次CI的实际扫描复核。
