# 08. 伺服、主轴与运动控制 — 资源目录

本目录只存放归属于本章节的图片、动图、视频/音频（如适用）及有权保存的完整文档（Word、PDF、Excel、CSV等），以及本章相关的工程图、测量数据和附件。

## 归档规则

- 资源在正文中必须有引用，并在本章 `ASSET-INDEX.md`（建立后）中登记来源、作者/机构、取得或生成日期、版本、许可/授权状态、关联知识条目和说明。
- 优先保留原始文件；整理版、裁剪版、翻译版必须单独命名并注明与原件的关系。
- 对版权或保密状态不明、无权再分发的资料，不保存副本，仅记录可合法保留的元数据和官方链接。
- 不重复复制同一原始文件；跨章节使用时引用主归属章节的资源路径。

## 本轮新增CSV

- `servo-control-loop-identification-template.csv`：电流/速度/位置环架构、参数版本、反馈点、采样和滤波、阶跃/频响、跟随误差、机械负载与安全批准记录；不含通用增益或带宽值。
- 来源记录SRC-000320～SRC-000322：Siemens SINAMICS S200（2025版）级联环路/机械刚度说明、S120（2018版）速度环频响优化手册和SIMOTICS T-1FW3（2022版）slot ripple/转矩准确度条件。厂商参数与过程仅支持指定产品/固件。


## 本轮新增伺服辨识专题
- 正文：docs/08-servo-spindle-and-motion-control/servo-parameter-identification-and-frequency-response.md。
- 合成仿真脚本、配置和CSV结果集中存储于CH12资源目录，避免跨章节重复副本。
- 新增SRC-000327～SRC-000330：Beckhoff TwinCAT 3 Autotuning、Siemens SINAMICS S120、MathWorks系统辨识和频域模型估计资料。厂商方法只支持对应产品/固件；软件文档仅说明一般辨识方法。


## 本轮多工况辨识专题
- 正文：docs/08-servo-spindle-and-motion-control/multicondition-servo-identification-and-model-order-selection.md。
- 仿真脚本和CSV结果集中归属CH12资源目录；本章不重复存储。
- 新增SRC-000333～SRC-000337：PLOS ONE两惯量伺服系统研究作为非CNC建模范例；MathWorks R2026b用于模型交叉验证、过拟合诊断、候选模型比较和disk margin方法。所有软件资料只作方法参考，不是机床验收标准。
