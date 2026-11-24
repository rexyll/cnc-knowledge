# TaskHistory — 2026-11-24

## CH12-T003 阻尼耗散与外部广义力功率符号审查

- **结构阻尼：** 动力学方程使用 D0*q_dot 作为阻尼广义力，账本扣除 q_dot.T @ D0 @ q_dot。模型校验 D0 对称半正定，因此该耗散功率理论上非负。
- **轴向摩擦：** 动力学方程使用 b*s_dot + Fc*tanh(s_dot/v_eps)，账本扣除摩擦力与速度的乘积。b、Fc 非负且 v_eps 正，路径反向时摩擦力与速度同时反号，功率仍非负；零速度时为零。
- **外部广义力：** 自由和规定路径动力学均将 Q_ext 加到广义力右端。账本以 Q_ext.T @ [q_dot,s_dot] 计算外部功率；其符号由力与速度方向决定，不应当作耗散项。
- **新增测试：** PATH-01运行器新增2项资源测试，覆盖正反向结构/轴摩擦耗散非负，以及外部广义力功率正/负/零。运行器39项、求解器32项，共71项资源测试。
- **测试提交：** `451ca951ff54b8eb9377f09e44f08abb8fa9ecb4`。
- **CI：** GitHub Actions [Run 45307608288](https://github.com/rexyll/cnc-knowledge/actions/runs/45307608288) success；仓库Knowledge Quality工作流通过。该CI不执行 `resouces/` 下资源测试。
- **本轮边界：** 资源测试仍未执行；未执行ENE-02/03积分或PATH-01仿真，没有新增数值能量残差或HIL/实机结论。验证矩阵8项继续 `NOT_RUN`，CH12-T003保持 `IN_PROGRESS`。
