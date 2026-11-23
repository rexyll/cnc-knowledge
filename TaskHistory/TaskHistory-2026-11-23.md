# 龙门联合求解器参数数组所有权加固（2026-11-23）

## 实际完成记录

- **任务ID：** CH12-T003（联合移动轴/电流环模型实现的静态接口加固切片）
- **任务名称：** 参数数组私有快照与只读约束
- **实际完成时间：** 2026-11-23T14:00:31+08:00（Asia/Shanghai）
- **分支：** `main`
- **交付文件：**
  - `resouces/12-control-and-machining-algorithms/gantry_joint_drive_solver.py`
  - `resouces/12-control-and-machining-algorithms/test_gantry_joint_drive_solver.py`
  - `docs/12-control-and-machining-algorithms/gantry-continuous-moving-load-and-multiloop-disk-margin.md`
  - `resouces/12-control-and-machining-algorithms/README.md`
  - `resouces/12-control-and-machining-algorithms/ASSET-INDEX.md`
  - `docs/TaskPlan/12-control-and-machining-algorithms/TaskPlan.md`

## 问题与处理

Python 的 `frozen=True` 不会递归冻结 NumPy 数组。若求解器持有外部传入数组的同一引用，调用方可在构造阶段参数校验后继续修改质量、阻尼、刚度、重力或执行器系数，令已检查的不变量失效。

求解器改为在构造时复制这些数组，并将内部副本设为只读；测试夹具改为在模型构造时显式提供零重力参数，新增资源测试验证原始数组后续修改不会影响模型，以及模型内部参数数组拒绝写入。

## 验收与限制

- **静态审查：** 已检查构造路径、参数引用关系、原测试对参数数组的修改行为及文档/资源索引的一致性。
- **资源测试：** 新增后共13项，尚未执行；当前未取得可用的授权Python/NumPy运行结果。
- **GitHub CI：** 待提交后触发；CI不执行 `resouces/` 下的求解器测试，CI成功也只证明既有仓库测试和知识结构检查通过。
- **提交SHA：** 待提交后补录。
- **遗留事项：** 运行13项资源测试；补做RK4步长收敛、机械/电气能量平衡独立核验、规定轨迹与自由轴模型交叉比较；真实驱动器参数辨识和HIL/实机验证仍未完成。
- **任务状态：** CH12-T003保持 `IN_PROGRESS`。
