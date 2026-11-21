# TaskHistory — 2026-11-22

> 时区：Asia/Shanghai（UTC+08:00）  
> 当日目标：完成MAP-001行业全景图首轮建图，形成行业分类、产业链、代表性厂商/产品生态及可追溯实体数据。

## 已完成任务

| 任务ID | 任务名称 | 完成时间（UTC+08:00） | 分支 | 最终提交SHA | 交付物 | 验收结果 |
|---|---|---|---|---|---|---|
| MAP-001 | 建立数控机床行业、机型、厂商、系统及供应链首轮全景图 | 2026-11-22T00:11:41+08:00 | main | [19de9c6](https://github.com/rexyll/cnc-knowledge/commit/19de9c62a884c297086c524390fe740703e8cfc2) | `docs/01-industry-and-fundamentals/industry-map.md`、`docs/02-machine-types-and-products/machine-tool-classification.md`、`docs/19-manufacturers-products-and-supply-chain/representative-ecosystem.md`、`docs/data/`、`docs/data-model/chapter-dictionaries/CH02.csv`、`CH19.csv`、`docs/coverage/CHAPTER-COVERAGE.csv` | 建立26条SRC来源、50个实体、30条关系；包括14种机床类型、8个术语、15家代表性组织、7个整机型号/系列、6项CNC/运动/直线运动产品；GitHub Actions Run #4通过，5项单元测试通过，质量脚本PASS（0 errors），检查22章、203条内部链接、42处来源引用和22条覆盖记录。 |

> 最终验收以提交 `19de9c62a884c297086c524390fe740703e8cfc2` 触发的GitHub Actions Run #4为准：  
> https://github.com/rexyll/cnc-knowledge/actions/runs/44923203355

## 本次研究与数据范围

- 行业边界：区分宏观统计分类、协会产品目录与本项目的工程知识分类；纳入数控车削、铣削、加工中心、钻镗、磨削、齿轮加工、特种加工、金属成形及直接相关的控制/功能部件、自动化和生命周期服务。
- 分类模型：采用“加工过程 × 结构布局 × 运动/轴配置 × 自动化程度 × 工艺集成能力”的多维分类；明确轴数不等于同时联动轴数，FMC/FMS属于制造单元/系统层级。
- 产业链：覆盖基础材料与基础制造、机械功能部件、CNC/PLC/伺服/反馈、电气与通信、刀具夹具/测量、整机OEM、系统集成、终端应用和生命周期服务。
- 代表性组织：DMG MORI、Mazak、Okuma、Makino、DN Solutions、TRUMPF、沈阳机床、秦川机床、Nidec、FANUC、Siemens、HEIDENHAIN、广州数控、Yaskawa、THK。
- 代表性产品：INH 63、INTEGREX i NEO、VARIAXIS i NEO、GENOS M560-V、DVF series、沈阳机床H系列、秦川YKS7225A，以及FANUC 0i-F Plus、SINUMERIK ONE、TNC7、GSK 988MA、Sigma-7、THK LM Guide。
- 数据边界：产品归属基于厂商官方目录；没有将目录信息扩展成未经核实的精度、行程、配置、价格、库存、市场份额或采购评级。当前样本不代表全球完整厂商/型号名录。

## 章节进度与覆盖度

| 章节 | 本次完成节点 | 当前覆盖度 | 后续重点 |
|---|---|---|---|
| CH01 | CH01-T001 行业知识地图 | 1级 inventory | CH01-T002：基础原理、坐标系、轴系与通用术语 |
| CH02 | CH02-T001 机床分类体系 | 1级 inventory | CH02-T002：主要机型结构/技术档案；补充具体型号规格 |
| CH19 | CH19-T001 厂商与产品主数据 | 1级 inventory | CH19-T002继续整理整机与系统厂商；CH19-T003补齐功能部件/刀具/测量供应商 |

覆盖矩阵采用“章节主归属实体、与该章主数据相连的关系、正文/实体实际引用的去重SRC ID”口径；未归档媒体资产计数保持为0。首轮地图只是inventory，不代表相应章节整体完成。

## CI问题与修复记录

- 数据录入后首次质量检查发现4条来源记录的 `source_type` / `evidence_kind` 与Source Schema枚举不一致。
- 已将统计/协会页面的来源类型和证据性质调整为Schema允许且语义匹配的值；没有删除来源，也没有改变引用论据。
- 后续重新运行通过；覆盖矩阵去重计数校准后再次运行Run #4通过，最终结果为0 errors。

## 验收结论

MAP-001首轮行业地图已完成并在根目录TaskPlan标记为DONE。CH01-T001、CH02-T001、CH19-T001已标记DONE；CH19-T002保持IN_PROGRESS。行业地图和实体数据是具有官方资料支撑的代表性样本，不是全球完整供应商/型号库。其余知识内容继续按章节TaskPlan逐项研究，不因地图完成而自动标记完成。

## 未完成 / 后续任务

- CH01-T002：补齐数控机床基本工作原理、坐标系、轴系、运动链及基础术语。
- CH02-T002：按机型建立结构、工作原理、关键配置和应用技术档案。
- CH19-T002：补充整机与数控/驱动系统厂商的具体系列和地区资料。
- CH19-T003：研究主轴、轴承、丝杠、导轨、转台、刀库、编码器、刀具、夹具、测量和辅助系统供应商。
- 后续更新必须继续遵守main分支、来源证据、资源归档、质量门禁和每日历史规则。
