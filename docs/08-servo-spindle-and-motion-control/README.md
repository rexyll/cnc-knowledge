# 08. 伺服、主轴与运动控制

**English:** Servo, Spindle and Motion Control  
**范围：** 伺服驱动器、电机、主轴电机/驱动、编码器、反馈链、轴控制、同步控制和运动性能。

## 本章覆盖内容

- 伺服电机、直线电机、力矩电机、主轴电机和驱动器
- 编码器、光栅尺、旋转变压器及位置/速度/电流反馈
- 电流环、速度环、位置环、前馈、滤波和增益调试概念
- 多轴同步、主从轴、龙门同步、主轴定向和刚性攻丝

## 本章任务计划

[打开本章 TaskPlan](../TaskPlan/08-servo-spindle-and-motion-control/TaskPlan.md)

本章知识内容按任务计划逐步研究，不在初始化阶段预填未经核实的技术参数或结论。

## 专题内容

- [伺服级联控制：电流环、速度环与位置环](servo-cascade-control.md)：三环级联、PMSM FOC模型、前馈/反馈、带宽与稳定性、调试顺序和数据留存。
- [伺服控制环辨识与调试记录模板](../../resouces/08-servo-spindle-and-motion-control/servo-control-loop-identification-template.csv)：参数基线、反馈点、采样/滤波、阶跃/频响和跟随误差记录。

## 新增专题

- [伺服参数辨识、负载惯量估计与频率响应建模](servo-parameter-identification-and-frequency-response.md)：负载惯量折算、转矩平衡回归、可辨识性、频响测量、柔性模态与独立验证。

## 多工况专题

- [多工况伺服辨识与模型阶次选择](multicondition-servo-identification-and-model-order-selection.md)：负载/方向/冷热状态、1/2/多惯量模型选型、H1相干度、交叉验证与稳定裕度边界。

## 建议正文结构

- `overview.md`：章节总览、概念和分类。
- `architecture.md` / `principles.md`：结构、原理和系统关系（适用时）。
- `specifications.md`：参数、型号、接口和指标（适用时）。
- `procedures/`：设计、制造、安装、操作或维护专题（适用时）。
- `cases/`：工程案例、测试和故障分析（适用时）。
- `ASSET-INDEX.md`：本章在 `resouces/08-servo-spindle-and-motion-control/` 中的资源索引。

## 相关资源

本章图片、动图和有权保存的完整文档统一放在 [`resouces/08-servo-spindle-and-motion-control/`](../../resouces/08-servo-spindle-and-motion-control/README.md)。正文使用相对链接引用资源。外部版权受限资料只记录合法元数据和官方链接。

## 来源与审查

事实性内容需记录来源、版本、适用机型/系统、核验日期和证据等级；未知项显式标记待核实。安全、版权和保密要求遵循根目录 `TaskPlan.md`。


## 多工况控制器设计

- [多工况伺服级联控制器设计与验证](multicondition-cascade-controller-design.md)：将多工况对象模型接入电流/转矩、速度和位置三级控制，并记录控制器候选、反馈点与验证边界。


## 前馈与滤波联合设计

- [伺服速度/加速度前馈与陷波、低通滤波器联合设计](servo-feedforward-and-filter-co-design.md)：说明轨迹导数前馈、刚体总惯量/扭转约化惯量区别、陷波/低通设计及多工况验证边界。
