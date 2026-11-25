# TaskHistory — 2026-11-26

## CH17-T001 机床操作、维护与维修第一轮框架

- **实际完成时间：** 2026-11-26T01:00:00+08:00（Asia/Shanghai）
- **分支：** main（未创建其他分支）
- **实施提交：** 031a257996a9a45766ee30f4a5bb3fe4ce131621
- **新增正文：** docs/17-operation-maintenance-and-repair/overview.md
- **新增资源：** resouces/17-operation-maintenance-and-repair/operation-readiness-checklist.csv（25项空白检查模板）、ASSET-INDEX.md；更新资源README和章节README。
- **新增来源：** SRC-000382～SRC-000388，覆盖美国OSHA危险能量控制法规、ISO 16090-1/ISO 23125官方标准目录、Haas官方手册索引/安全说明/车床维护计划。
- **内容结论：** 建立操作、操作者日常维护、计划/状态维护、故障维修/服务四类责任边界；梳理开机准备、运行监视、正常停机、维修前风险识别和维修后复验的数据结构。
- **验收边界：** 检查模板结果初始均为NOT_ASSESSED；未填入型号级维护周期、润滑剂/冷却液牌号、压力/扭矩/温度限值。OSHA来源只作为美国法规适用场景，ISO工作草案不作为已发布标准，Haas资料不泛化到其他品牌。未复制受版权保护的标准或手册全文。
- **当前状态：** CH17-T001为IN_PROGRESS；缺少用户指定的目标机床型号/控制系统/选件及对应现行手册，故尚不能形成型号级SOP或维护周期表。CH17-T002～T004保持TODO。
- **后续工作：** 选定一个目标机床系列，获取现行官方操作/维护手册，将25项模板逐项映射到制造商条款、适用周期和判定依据。


## CH12-T003 SCURVE-01 标量三阶七段限跃度S曲线参考运行

- **完成时间：** 2026-11-26（Asia/Shanghai）
- **CI：** [GitHub Actions Run 45517202862](https://github.com/rexyll/cnc-knowledge/actions/runs/45517202862)，两个Job均success；CH12资源测试143/143，仓库测试和strict lint通过。
- **运行范围：** 标量静止—静止三阶七段S曲线，合成距离0.25m，最大速度0.2m/s、最大加速度1m/s²、最大跃度10m/s³，采样周期0.001s。
- **结果：** 总时间1.55s，巡航0.95s，峰值速度/加速度/跃度0.2m/s、1m/s²、10m/s³，终点位置0.25m、速度/加速度为0；七段、1551个采样点。manifest状态COMPLETED_REPORT_ONLY，acceptance_decision=DESCRIPTIVE_ONLY。
- **归档：** `resouces/12-control-and-machining-algorithms/generated/scurve-01-synthetic/`，包括时序CSV 1551×8、分段CSV 7×12、汇总CSV 1×19和manifest；CI确认archive=VERIFIED。
- **来源ID恢复：** 登记SCURVE原有引用SRC-000375～SRC-000378，分别对应S曲线阶次/段数论文、五轴CNC轴空间/笛卡尔空间约束论文、LinuxCNC路径控制与look-ahead官方文档。CH17七条来源统一顺延为SRC-000382～SRC-000388。
- **边界：** 仅为合成标量参考，不是多轴CNC规划器；不包含逆运动学、块段look-ahead算法实现、拐角混合、Snap限制、伺服动力学或机床验收。CH12-T003仍IN_PROGRESS。
