# 12. 控制与加工算法

**English:** Control and Machining Algorithms  
**范围：** 插补、轨迹规划、加减速、前瞻、坐标变换、误差补偿、主轴/进给控制、加工优化和算法验证。

## 本章覆盖内容

- 直线/圆弧/样条插补、多轴插补和高阶曲线
- 速度规划、加速度/跃度约束、前瞻和拐角平滑
- 坐标变换、刀具半径/长度补偿、RTCP和运动学变换
- 螺距/反向间隙/直线度/垂直度/热误差补偿
- 振动抑制、切削参数优化、负载监测和加工误差分析

## 本章任务计划

[打开本章 TaskPlan](../TaskPlan/12-control-and-machining-algorithms/TaskPlan.md)

本章知识内容按任务计划逐步研究，不在初始化阶段预填未经核实的技术参数或结论。

## 专题内容

- [扰动观测器与直驱回转轴周期转矩补偿](disturbance-observer-and-periodic-torque-compensation.md)：DOB/Q滤波、摩擦模型、机械角/电角度周期映射、谐波前馈、重复控制/迭代学习和回归验证。
- [周期扰动观测与转矩补偿验证模板](../../resouces/12-control-and-machining-algorithms/periodic-disturbance-observer-validation-template.csv)：名义模型、观测器、补偿参数、基线对照、限幅/副作用和验证层级记录。

## 新增专题

- [伺服对象不确定性、DOB鲁棒稳定性与数值仿真验证](servo-model-and-dob-robustness-simulation.md)：相对阶次、Q滤波可实现性、鲁棒稳定性审查及可复现合成仿真。

## 多工况模型验证专题

- [多工况对象模型、交叉验证与鲁棒稳定裕度评估](servo-model-cross-validation-and-robust-margins.md)：模型阶次、H1/相干度、独立验证、不确定性包络和GM/PM/disk margin计算边界。

## 建议正文结构

- `overview.md`：章节总览、概念和分类。
- `architecture.md` / `principles.md`：结构、原理和系统关系（适用时）。
- `specifications.md`：参数、型号、接口和指标（适用时）。
- `procedures/`：设计、制造、安装、操作或维护专题（适用时）。
- `cases/`：工程案例、测试和故障分析（适用时）。
- `ASSET-INDEX.md`：本章在 `resouces/12-control-and-machining-algorithms/` 中的资源索引。

## 相关资源

本章图片、动图和有权保存的完整文档统一放在 [`resouces/12-control-and-machining-algorithms/`](../../resouces/12-control-and-machining-algorithms/README.md)。正文使用相对链接引用资源。外部版权受限资料只记录合法元数据和官方链接。

## 来源与审查

事实性内容需记录来源、版本、适用机型/系统、核验日期和证据等级；未知项显式标记待核实。安全、版权和保密要求遵循根目录 `TaskPlan.md`。


## 级联控制器鲁棒性专题

- [多工况伺服级联控制的稳定裕度与限幅仿真](multicondition-cascade-robust-stability-and-saturation-simulation.md)：SISO嵌套环路GM/PM、延迟扫描、柔性模态、限幅和反算抗积分饱和的合成联合仿真。


## 前馈与滤波联合验证

- [伺服速度/加速度前馈、陷波与低通滤波器联合验证](servo-feedforward-notch-lowpass-co-design.md)：对比前馈跟随收益、模态失谐、外部负载扰动、滤波相位与多交越环路裕度。

## 双驱龙门 MIMO 同步控制专题

- [双驱龙门轴的 MIMO 耦合同步控制与鲁棒性评估](gantry-dual-drive-mimo-synchronization-and-robustness.md)：比较独立双轴PD与交叉耦合同步P-D，展示MIMO返回差/灵敏度诊断的用途和disk margin计算边界；全部数据为合成示例。

## 横梁模态与离散延迟鲁棒性专题

- [双驱龙门轴的横梁模态、变位置负载与离散延迟鲁棒性](gantry-mimo-modal-load-position-delay-robustness.md)：用假设模态和冻结负载位置模型研究横梁弯曲/扭转、ZOH离散化、整数命令延迟及同步控制权衡，所有参数和结果均为合成示例。
