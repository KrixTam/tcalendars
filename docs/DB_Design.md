# Database Design

本项目使用 SQLite 存储本地缓存数据，数据库文件固定为 `tcalendars/cache/data.dat`。

## 设计目标

- 用单一 SQLite 文件统一承载交易日历、股票名称代码、基金名称代码及元数据
- 用 `metadata` 记录各业务表最后更新日期，支持按天刷新
- 为股票简称检索提供 `pinyin` 字段，支撑拼音首字母查询与中文输入的拼音降级匹配
- 保持缓存文件位于包内 `tcalendars/cache/`，避免散落多个 CSV 文件

## 存储位置

- 数据库目录：`tcalendars/cache/`
- 数据库文件：`tcalendars/cache/data.dat`

## 初始化与兼容性

- `DatabaseManager` 初始化时会确保数据库目录存在
- 当前会显式初始化以下表：
  - `metadata`
  - `se_calendar`
  - `stock_name_code`
- `fund_name_code` 由 `save_dataframe(..., if_exists='replace')` 写入时自动创建
- 对历史数据库兼容：
  - 若旧版 `stock_name_code` 表缺少 `pinyin` 字段，初始化时会自动补列

## 表结构设计

### 1. `se_calendar` (深交所交易日历)

存储 A 股市场交易日历数据。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| zrxh | INTEGER | 星期序号，1（星期天）- 7（星期六） |
| jybz | INTEGER | 交易标志，1 表示交易日，0 表示非交易日 |
| jyrq | TEXT | 交易日期，格式 `YYYY-MM-DD`，主键 |

补充说明：
- `TradingCalendars._load_calendar()` 会在加载后将 `zrxh` / `jybz` 转为整数类型
- `TradingCalendars.update_calendar()` 会在交易日历未覆盖到当年年末时增量更新

### 2. `stock_name_code` (股票名称代码)

存储沪市、深市、北交所股票名称代码映射关系。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| code | TEXT | 6 位股票代码，主键 |
| name | TEXT | 股票简称 |
| market | TEXT | 所属市场，取值示例：`沪市` / `深市` / `北交所` |
| pinyin | TEXT | 股票简称拼音首字母，全部大写 |

补充说明：
- 数据来源：
  - `ak.stock_info_sh_name_code("主板A股")`
  - `ak.stock_info_sh_name_code("科创板")`
  - `ak.stock_info_sz_name_code()`
  - `ak.stock_info_bj_name_code()`
- 写入前会先统一：
  - 字段重命名为 `code` / `name` / `market`
  - `code` 补齐为 6 位字符串
  - 按 `code` 去重，保留首条
- `name` 写入前会执行简称清洗：
  - `XD` / `XR` / `DR`：优先回退旧简称，否则剔除前缀
  - `N` / `C`：优先回退旧简称；若旧简称不存在，则等待 30 秒交互输入；超时后剔除前缀
  - `None` / `nan` / 空字符串等异常值会被清洗为空
- `pinyin` 由清洗后的 `name` 生成，供 `StockNameCodeHelper.query()` 使用

### 3. `fund_name_code` (基金名称代码)

存储天天基金基金名称与代码映射关系。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| code | TEXT | 6 位基金代码，主键 |
| name | TEXT | 基金简称 |

补充说明：
- 数据来源：`ak.fund_name_em()`
- 写入前会执行：
  - 字段重命名为 `code` / `name`
  - `code` 补齐为 6 位字符串
  - 按 `code` 去重，保留首条

### 4. `metadata` (元数据)

存储各业务表最后更新时间。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| table_name | TEXT | 业务表名，主键 |
| last_update | TEXT | 最后更新日期，格式 `YYYY-MM-DD` |

补充说明：
- `stock_name_code`
- `fund_name_code`

上述两张业务表均依赖 `metadata.last_update` 实现“按天刷新”。

## 与查询逻辑的关系

### 股票查询依赖

`StockNameCodeHelper.query()` 依赖 `stock_name_code` 表中的以下字段：
- `code`：代码精确匹配、`?` 通配匹配
- `name`：中文名称精确/前缀/包含/单字容错匹配
- `market`：作为返回结果的一部分
- `pinyin`：拼音首字母精确/前缀/包含匹配，以及中文输入的拼音 fallback

补充说明：
- 当中文输入进入“拼音首字母精确匹配”阶段时，当前实现会同时结合 `name` 与 `pinyin` 做二次排序
- 该阶段会优先排序同时满足中文单字容错的候选，再综合比较相同位置汉字命中数、公共前后缀长度、差异汉字的完整拼音距离等证据

### 基金查询依赖

`FundNameCodeHelper` 依赖 `fund_name_code` 表中的：
- `code`
- `name`

其中 `query_shares()` 不依赖额外字段，而是在内存中对 `name` 做标准化清洗后识别关联份额。

## 导出能力

当前数据库中的两类名称代码缓存都支持导出为 CSV：

- `StockNameCodeHelper.export_to_csv(file_path)`
- `FundNameCodeHelper.export_to_csv(file_path)`

导出的是内存中已加载的数据快照，不会额外修改数据库结构。
