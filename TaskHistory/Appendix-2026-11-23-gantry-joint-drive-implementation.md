# 龙门自由移动轴与电流环联合求解器实现切片（2026-11-23）

## 工作范围

将前序自由路径坐标解析模型和电流受控驱动接口转成可调用的联合状态求解器资源。内容仅覆盖模型代码与资源测试文件的编写、文档和索引登记，以及仓库知识结构CI验收。

## 交付文件

- resouces/12-control-and-machining-algorithms/gantry_joint_drive_solver.py
- resouces/12-control-and-machining-algorithms/test_gantry_joint_drive_solver.py
- docs/12-control-and-machining-algorithms/gantry-continuous-moving-load-and-multiloop-disk-margin.md
- resouces/12-control-and-machining-algorithms/README.md
- resouces/12-control-and-machining-algorithms/ASSET-INDEX.md

## 实现结构

- 状态向量：x = [q, q_dot, s, s_dot, i, x_i]。
- 联合质量矩阵：diag(M0, m_s0) + m_p J.T J，J = [Phi, r_s]。
- 移动负载运输加速度偏置：m_p J.T (2 Phi_s q_dot s_dot + r_ss s_dot^2)。
- 结构、路径阻尼/摩擦、重力势能梯度与外部广义力统一进入联合方程。
- 执行器相对位移使用仿射接口 ell_a = c_q.T q + c_s s + c0；广义力按 Q_a = J_a.T F_a 投影。
- 电气模型使用单轴等效RL关系，PI环采用电压限幅和反算anti-windup；命令电流也受限幅。
- RK4积分以自由路径坐标状态推进，不再要求预先提供 s(t)。

## 测试覆盖（仅编写，未执行）

共8项资源测试：联合质量矩阵对称正定、零负载极限、执行器虚功功率一致性、零速RL衰减、电压/电流命令限幅、无输入静止极限、匹配SI常数下机电储能变化与电阻铜耗平衡、自由路径坐标积分。运行命令：

python -m unittest discover -s resouces/12-control-and-machining-algorithms -p 'test_gantry_joint_drive_solver.py' -v

**当前没有该命令的运行结果。** CI工作流不会调用此资源测试目录。

## 仓库CI验收

- 内容提交：c6e7852048d04487d045e5ff05894fdda8051af7。
- GitHub Actions：Run 45112047320，success。
- 仓库既有测试：5/5通过；strict knowledge lint：PASS（0 errors）。
- 扫描统计：22章、128 Markdown、407内部链接、143实体、240关系、371来源、660处正文来源引用。
- 本CI只证明仓库既有测试与知识结构/数据校验通过，不证明新增求解器或资源测试已执行。

## 限制与遗留

未提供任何特定机床/电机/驱动器参数或厂商适配声明；未完成时间步长收敛、独立方程核验、硬限位、接触/碰撞、滚珠丝杠扭转/间隙、离散采样与PWM、完整PMSM dq、多轴电流耦合、有限元/试验模态、HIL或实机验证。后续必须先在可运行NumPy的Python 3.10+环境执行8项资源测试，再根据错误修正；之后再开展步长收敛与模型交叉验证。CH12-T003保持IN_PROGRESS。
