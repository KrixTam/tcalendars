# Database Design

本项目使用 SQLite 存储缓存数据，数据库文件位于 `tcalendars/cache/data.dat`。

## 表结构设计

### 1. `se_calendar` (深交所交易日历)
存储 A 股市场的交易日历数据。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| zrxh | INTEGER | 星期序号，1（星期天） - 7（星期六） |
| jybz | INTEGER | 交易标志，1 - 交易日；0 - 非交易日 |
| jyrq | TEXT | 交易日期，格式为 YYYY-MM-DD (主键) |

### 2. `stock_name_code` (股票名称代码)
存储沪深北交所股票的名称与代码对应关系。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| code | TEXT | 股票代码 (6位数字) (主键) |
| name | TEXT | 股票简称 |
| market | TEXT | 所属市场（沪市/深市/北交所） |

### 3. `fund_name_code` (基金名称代码)
存储天天基金网获取的基金名称与代码对应关系。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| code | TEXT | 基金代码 (6位数字) (主键) |
| name | TEXT | 基金简称 |

### 4. `metadata` (元数据)
存储各业务表的最后更新时间。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| table_name | TEXT | 表名 (主键) |
| last_update | TEXT | 最后更新日期 (YYYY-MM-DD) |
