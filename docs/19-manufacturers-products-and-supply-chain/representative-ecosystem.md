# 代表性机床厂商、CNC与功能部件生态图

> 知识ID：KNOW-000004  
> 主章节：CH19  
> 核验日期：2026-11-22  
> 范围：代表性样本；非全球供应商全集、市场份额榜单或采购评级

## 1. 厂商生态分层

| 层级 | 主要供给 | 典型字段/后续研究重点 |
|---|---|---|
| 整机OEM | 数控车床、加工中心、磨床、齿轮机床、特种加工和钣金设备 | 企业/品牌、机型、型号、配置、生产地、技术资料、服务网络 |
| CNC与自动化平台 | CNC、PLC、运动控制、HMI、工业通信、数字化和仿真 | CNC系列、轴数/通道、插补能力、总线、软硬件版本、选件 |
| 伺服和执行部件 | 伺服/主轴驱动、电机、直接驱动和线性电机 | 功率/转矩、编码器反馈、控制周期、总线、制动和冷却 |
| 机械功能部件 | 主轴、轴承、导轨、丝杠、转台、刀库、刀塔和夹紧机构 | 精度、刚度、速度、负载、预压、寿命、润滑和安装条件 |
| 刀具与工件系统 | 刀具、刀柄、夹具、卡盘、托盘和工件交换 | 接口规格、材料/涂层、跳动、夹持力、平衡和适用工况 |
| 测量与工艺支持 | 编码器、光栅尺、探头、测量仪、在线检测和工艺软件 | 测量范围、不确定度、接口、校准、软件兼容 |
| 自动化及生产系统 | 上下料、托盘库、机器人接口、FMC/FMS和物流系统 | 节拍、互锁、安全接口、系统控制和可重构能力 |
| 生命周期服务 | 安装调试、培训、维护、维修、备件、升级和再制造 | 服务授权、地区覆盖、备件生命周期、固件与软件版本 |

行业组织目录也会把机床主机、CNC单元、CAD/CAM、制造管理系统、测量仪器、机床装备和刀柄等分组列出，说明供应链不仅包括整机OEM。〔SRC-000004；SRC-000005〕

## 2. 代表性整机及加工设备厂商

| VENDOR实体 | 主要产品/技术范围（官方目录） | 官方资料 |
|---|---|---|
| [DMG MORI](../data/entities/VENDOR/VENDOR-000001.json) | 车削、铣削、磨削、钻削、五轴、多任务、超声/激光加工及自动化 | 〔SRC-000009；SRC-000010〕 |
| [Yamazaki Mazak](../data/entities/VENDOR/VENDOR-000002.json) | 多任务、五轴、车削、瑞士型、立卧加工中心及激光加工 | 〔SRC-000011；SRC-000012〕 |
| [Okuma](../data/entities/VENDOR/VENDOR-000003.json) | 车床、多任务、加工中心、五轴、双立柱、磨床及自动化 | 〔SRC-000013〕 |
| [Makino](../data/entities/VENDOR/VENDOR-000004.json) | 水平/垂直加工中心、五轴、线切割和成形EDM、磨削 | 〔SRC-000014〕 |
| [DN Solutions](../data/entities/VENDOR/VENDOR-000005.json) | 车削中心、加工中心、镗铣、双立柱、五轴和多功能复合 | 〔SRC-000015〕 |
| [TRUMPF](../data/entities/VENDOR/VENDOR-000006.json) | 板材/管材激光切割、冲压、冲激复合、折弯和激光焊接 | 〔SRC-000016〕 |
| [沈阳机床](../data/entities/VENDOR/VENDOR-000007.json) | 卧式/立式加工中心和数控车床 | 〔SRC-000017〕 |
| [秦川机床](../data/entities/VENDOR/VENDOR-000008.json) | 齿轮机床、车床、加工中心、磨床、数控系统、工具和功能部件 | 〔SRC-000018；SRC-000019〕 |
| [Nidec](../data/entities/VENDOR/VENDOR-000009.json) | 加工中心、大型机床、铣床、齿轮加工、车床和激光加工等 | 〔SRC-000020〕 |

本表按产品门类选取样本，不是同一精度等级、加工范围或市场区域的横向排名。整机厂的实际产品供应和服务能力应按地区子公司、产品系列和销售服务网络分别核验。

## 3. CNC、伺服与运动控制生态

| VENDOR实体 | 公开产品/业务范围 | 官方资料 |
|---|---|---|
| [FANUC](../data/entities/VENDOR/VENDOR-000010.json) | 0i-F Plus、30i/31i/32i系列CNC及相关运动控制、驱动和电机 | 〔SRC-000021〕 |
| [Siemens](../data/entities/VENDOR/VENDOR-000011.json) | SINUMERIK ONE、828D、808等CNC平台 | 〔SRC-000022〕 |
| [HEIDENHAIN](../data/entities/VENDOR/VENDOR-000012.json) | TNC CNC、编码器、测头和长度测量设备 | 〔SRC-000023〕 |
| [广州数控GSK](../data/entities/VENDOR/VENDOR-000013.json) | 车削、加工中心、五轴、多通道CNC系列和驱动/电机资料 | 〔SRC-000024〕 |
| [Yaskawa](../data/entities/VENDOR/VENDOR-000014.json) | Sigma-7伺服、直接驱动和线性伺服产品 | 〔SRC-000025〕 |
| [THK](../data/entities/VENDOR/VENDOR-000015.json) | LM Guide直线导轨等线性运动产品 | 〔SRC-000026〕 |

控制系统供应商不等于机床OEM。具体机床可能采用原厂自研控制，也可能集成第三方CNC/PLC、伺服驱动和反馈元件；不能仅依据某个品牌的产品目录推断某一机床型号采用了该控制平台。

## 4. 已登记的代表性型号与产品记录

CH02已建立独立的[典型数控机床产品与型号规格目录](../02-machine-types-and-products/representative-model-catalog.md)，包含型号级规格、配置边界和原厂来源定位；本节保留厂商生态导航用途。

### 4.1 整机型号（MACHINE）

| 型号/系列 | 制造商 | 类型归属 | 实体记录 |
|---|---|---|---|
| INH 63 | DMG MORI | 五轴加工中心 | [MACHINE-000001](../data/entities/MACHINE/MACHINE-000001.json) |
| INTEGREX i NEO | Yamazaki Mazak | 多任务/车铣复合 | [MACHINE-000002](../data/entities/MACHINE/MACHINE-000002.json) |
| VARIAXIS i NEO | Yamazaki Mazak | 五轴加工中心 | [MACHINE-000003](../data/entities/MACHINE/MACHINE-000003.json) |
| GENOS M560-V | Okuma | 立式加工中心 | [MACHINE-000004](../data/entities/MACHINE/MACHINE-000004.json) |
| DVF series | DN Solutions | 五轴立式加工中心 | [MACHINE-000005](../data/entities/MACHINE/MACHINE-000005.json) |
| H series | 沈阳机床 | 卧式加工中心 | [MACHINE-000006](../data/entities/MACHINE/MACHINE-000006.json) |
| YKS7225A | 秦川机床 | 齿轮磨削机床 | [MACHINE-000007](../data/entities/MACHINE/MACHINE-000007.json) |

### 4.2 CNC/运动及功能部件产品（PRODUCT）

| 产品 | 供应商 | 产品类别 | 实体记录 |
|---|---|---|---|
| FANUC Series 0i-F Plus | FANUC | CNC系统 | [PRODUCT-000001](../data/entities/PRODUCT/PRODUCT-000001.json) |
| SINUMERIK ONE | Siemens | CNC系统 | [PRODUCT-000002](../data/entities/PRODUCT/PRODUCT-000002.json) |
| TNC7 | HEIDENHAIN | CNC系统 | [PRODUCT-000003](../data/entities/PRODUCT/PRODUCT-000003.json) |
| GSK 988MA | 广州数控 | 加工中心CNC系统 | [PRODUCT-000004](../data/entities/PRODUCT/PRODUCT-000004.json) |
| Sigma-7 | Yaskawa | 伺服/运动控制 | [PRODUCT-000005](../data/entities/PRODUCT/PRODUCT-000005.json) |
| LM Guide | THK | 直线导轨 | [PRODUCT-000006](../data/entities/PRODUCT/PRODUCT-000006.json) |

## 5. 采购、选型和供应商评估需要分开核验的事项

1. **厂商存在与具体型号供货不是一回事**：厂商官方网站有某产品系列，不代表该系列在所有地区均销售或可立即供货。
2. **公开参数与选件配置不是一回事**：同一系列可能有多种行程、主轴、刀库、控制系统、软件和安全选件。
3. **原厂、品牌、代理和集成商必须分开登记**：代理商可以供货或服务，但不能自动写成制造商。
4. **兼容性需要组合证据**：机械安装接口、电气额定值、反馈协议、总线版本、控制器选件、固件和安全功能均可能影响兼容性。
5. **停产、替代、售后和交期需实时证据**：历史目录不能证明当前库存、当前交期或授权服务状态。
6. **价格和商业条件不属于本轮地图**：没有可靠来源时不录价格，不发布未经核实的供应链风险评分。

## 6. 后续供应链补全方向

后续CH19-T003优先研究主轴/主轴轴承、丝杠、导轨、回转工作台、刀库/刀塔、编码器/光栅尺、刀具/刀柄、卡盘/夹具、润滑冷却、过滤排屑、测量和探测设备。每一类先确定代表性供应商，再按产品系列和具体型号录入；不以本轮15家组织样本代替完整供应商目录。
