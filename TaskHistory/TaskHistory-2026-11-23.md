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
- **内容提交SHA：** d48f8f3bdc69b2b780c330f6582c279212643175。
- **GitHub CI：** [Run 45121368649](https://github.com/rexyll/cnc-knowledge/actions/runs/45121368649) success；仓库现有测试5/5通过；strict knowledge lint PASS（0 errors）。
- **CI扫描统计：** 22章、130个Markdown文件、407条内部链接、143个实体、240条关系、371条来源、660处章节来源引用。
- **边界：** 该CI没有执行 `resouces/` 下的13项求解器测试。
- **遗留事项：** 运行13项资源测试；补做RK4步长收敛、机械/电气能量平衡独立核验、规定轨迹与自由轴模型交叉比较；真实驱动器参数辨识和HIL/实机验证仍未完成。
- **任务状态：** CH12-T003保持 `IN_PROGRESS`。


## 参数数组只读契约再次加固（2026-11-23）

- **实际完成时间：** 2026-11-23T14:30:00+08:00（Asia/Shanghai）
- **分支：** `main`
- **问题：** NumPy 对自有内存的只读数组可允许调用方通过 `setflags(write=True)` 重新开启写权限，前一提交的 `write=False` 只能防止直接赋值，不能充分保证只读。
- **处理：** `_readonly_float_array` 改为将浮点快照序列化为不可变 `bytes` 缓冲区，再以 `np.frombuffer` 生成数组视图；资源测试逐一检查 `M0/D0/K0`、重力向量和执行器系数数组无法恢复写权限。
- **交付文件：** `resouces/12-control-and-machining-algorithms/gantry_joint_drive_solver.py`、`resouces/12-control-and-machining-algorithms/test_gantry_joint_drive_solver.py`、`docs/12-control-and-machining-algorithms/gantry-continuous-moving-load-and-multiloop-disk-margin.md`、本章 TaskPlan 与本历史记录。
- **验收边界：** 本轮静态修订尚待提交及CI；13项资源测试仍未运行。仓库CI不运行资源级测试，不能用CI成功替代该测试结果。
- **遗留事项：** 运行13项资源测试、RK4步长收敛和独立能量平衡核验；真实机床参数辨识与HIL/实机验证未完成。CH12-T003保持 `IN_PROGRESS`。
