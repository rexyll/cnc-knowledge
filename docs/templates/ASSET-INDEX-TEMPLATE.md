# 资源索引（ASSET-INDEX）

> 所属章节：CHxx
> 本索引对应资源目录：resouces/<章节目录>/
> 说明：每个本地资源文件都必须有ASSET实体记录；本表是便于人工浏览的索引，不替代实体主记录。

## 资源列表

| ASSET ID | 文件相对路径 | 资源类型 | 说明/图注 | 关联实体/知识ID | 来源ID | 版本/日期 | 权利状态 | SHA-256 |
|---|---|---|---|---|---|---|---|---|
| <ASSET-ID> | ../../resouces/<章节目录>/<文件名> | <image/animation/pdf/docx/xlsx/csv/cad等> | <内容、用途、图注> | <ENTITY-ID/KNOW-ID> | <SRC-ID> | <版本/取得或生成日期> | <open_license/permission_granted/user_supplied等> | <校验值> |

## 资源记录要求

- 每个资源文件建立ASSET实体JSON，存放路径按实体数据存储规则。
- 记录原始文件名、规范文件名、MIME类型、文件大小、SHA-256、作者/发布机构、取得/生成日期、版本和关联实体。
- 标明资源权利状态：public_domain、open_license、permission_granted、user_supplied、link_only、restricted或unknown。
- 权利状态为restricted或unknown时，不得公开分发文件副本；不具备保存依据时只留可合法保存的来源元数据与链接。
- 图片和动图应记录图注、视图方向/裁剪说明（适用时）和作者/来源；整理版不得覆盖原件。
- 跨章节复用时只保存一份原始文件，其他章节链接到主归属章节的资源路径。
- 文件移动或重命名时更新本索引、ASSET实体和所有正文引用。
