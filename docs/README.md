# Trading Calendars(tcalendars)

交易日历与名称代码辅助工具库。当前对外暴露以下核心能力：
- `TradingCalendars`：A 股交易日历查询
- `StockNameCodeHelper`：股票名称/代码/拼音首字母查询
- `FundNameCodeHelper`：基金名称/代码查询

当前支持的市场范围：
- 中国股票市场交易日历（2005 年 1 月 1 日起）
- 沪市、深市、北交所股票名称代码
- 公募基金名称代码

## 安装

### 通过 pip 安装

```bash
pip install tcalendars
playwright install chromium
```

### 从源码环境安装依赖

```bash
pip install pandas pymoment akshare playwright pypinyin
playwright install chromium
```

说明：
- `playwright` 用于 `StockNameCodeHelper.get_stock_code_by_english_name` / `get_stock_info_by_english_name`
- `pypinyin` 用于生成股票简称拼音首字母，以及中文输入的拼音降级检索

## 缓存

- 所有缓存统一位于包目录下的 `tcalendars/cache/`
- 数据缓存使用 SQLite，数据库文件为 `tcalendars/cache/data.dat`
- Yahoo Finance 查询缓存文件为 `tcalendars/cache/.yfinance_cache`
- `.yfinance_cache` 在启动时自动加载到内存；超过 60 天的缓存不会被加载
- 删除 `.yfinance_cache` 后会在下一次查询时自动重建

### SQLite 中的主要数据

- `se_calendar`：交易日历
- `stock_name_code`：股票名称代码与拼音首字母
- `fund_name_code`：基金名称代码
- `metadata`：各业务表最后更新时间

### 自动更新行为

- `TradingCalendars()` 初始化时会自动加载本地交易日历；若数据尚未覆盖到当年年末，会继续增量更新
- `StockNameCodeHelper()` / `FundNameCodeHelper()` 初始化时会检查 `metadata` 中的最后更新日期，按“按天更新”策略自动刷新
- 股票与基金代码表更新失败时，会自动回退读取本地已有缓存

## 示例

### 交易日历

```python
from tcalendars import TradingCalendars

calendar = TradingCalendars()

calendar.is_trading_day('2023-01-01')
# False

calendar.get_trading_days('2023-01-01', '2023-01-05')
# ['2023-01-03', '2023-01-04', '2023-01-05']

calendar.get_trading_day('2023-01-01')
# '2023-01-03'

# 如有需要，也可以手工初始化交易日历
calendar.init_calendar()
```

### 股票名称代码

```python
from tcalendars import StockNameCodeHelper

helper = StockNameCodeHelper()

helper.get_stock_name('000001')
# '平安银行'

helper.get_stock_code('平安银行')
# '000001'

# 6 位代码精确查询
helper.query('000001')
# [{'code': '000001', 'name': '平安银行', 'market': '深市', 'pinyin': 'PAYH'}]

# 6 位代码模糊查询：? 代表恰好 1 位未知数字
helper.query('00000?')
# 返回所有匹配 00000x 的股票，默认最多 5 条

# 拼音首字母精确查询
helper.query('PA')
# [{'code': '000001' 或其他精确匹配 PA 的结果, ...}]

# 中文名称精确查询命中后直接返回，不再混入更弱规则结果
helper.query('平安')
# [{'code': '000005', 'name': '平安', 'market': '深市', 'pinyin': 'PA'}]

# 2 个汉字不会触发中文转拼音 fallback
helper.query('屏安')
# []

# 4 个汉字在名称通道无命中时，会尝试转拼音首字母 fallback
helper.query('屏安银杭')
# 可能返回 [{'code': '000001', 'name': '平安银行', ...}]

# 强单字容错优先于拼音精确匹配
helper.query('华电科技')
# 可能返回 [{'code': '000006', 'name': '华天科技', ...}]

# 弱单字容错不会挡住更强的拼音精确匹配
helper.query('复兴科技')
# 可能返回 [{'code': '000011', 'name': '富信科技', ...}]

# 中文输入会在必要时启用拼音混淆替换 fallback
helper.query('汽车测试')
# 可能返回 [{'code': '301306', 'name': '西测测试', ...}]

# 导出股票名称代码表
helper.export_to_csv('stock_name_code.csv')
```

### 股票 `query` 规则

`StockNameCodeHelper.query(keyword, limit=5)` 返回值为 `list[dict]`，每项包含：
- `code`
- `name`
- `market`
- `pinyin`

当前实现遵循“分阶段命中后短路返回”的策略，命中某一阶段后，不再继续执行更弱阶段。

#### 1. 输入拦截

- `keyword` 为空、`None`、空白字符串时，返回空列表
- `keyword` 仅 1 个字符（1 个汉字 / 1 个字母 / 1 位数字）时，返回空列表
- 如果输入仅由数字和 `?` 组成，但长度不是 6 位，也直接返回空列表

#### 2. 代码查询规则

- 仅接受 6 位字符串，且字符只能是 `0-9` 或 `?`
- 不含 `?` 时，仅做 6 位代码精确匹配
- 含 `?` 时，`?` 表示恰好 1 位未知数字，按固定位置做通配匹配

#### 3. 中文查询规则

按以下顺序执行，命中即停止：

1. 中文名称精确匹配
2. 中文名称前缀匹配
3. 中文名称包含匹配（要求输入至少 2 个汉字）
4. 强单字容错匹配
5. 中文转拼音首字母后的精确匹配
6. 弱单字容错匹配
7. 中文转拼音首字母后的前缀匹配
8. 中文转拼音首字母后的包含匹配
9. 拼音混淆替换后的精确匹配
10. 拼音混淆替换后的前缀匹配

其中：
- 单字容错仅对“名称等长且仅 1 个汉字不同”的候选生效
- 中文转拼音相关 fallback 仅在输入长度 `>= 3` 时启用
- 强单字容错指：首字相同，且差异汉字的完整拼音编辑距离 `<= 1`
- 弱单字容错指：其余满足“等长且只差 1 个汉字”的候选

#### 4. 非中文查询规则

按以下顺序执行，命中即停止：

1. 拼音首字母精确匹配
2. 拼音首字母前缀匹配
3. 拼音首字母包含匹配

#### 5. 拼音混淆替换规则

拼音混淆替换仅对“用户输入本身为中文，且长度 `>= 3`”的场景启用；仅替换 1 个字母位置。

当前实现中的混淆组包括：
- `B ↔ P`
- `D ↔ T`
- `G ↔ K`
- `J ↔ Q ↔ X`
- `N ↔ L`
- `F ↔ H`
- `R ↔ L`
- `S ↔ Z`

### 股票名称清洗规则

更新 `stock_name_code` 时，股票简称会先清洗，再生成 `pinyin`：

- `XD` / `XR` / `DR` 前缀：
  - 若旧缓存中已有同代码股票简称，则优先回退旧简称
  - 否则直接剔除前缀
- `N` / `C` 前缀：
  - 若旧缓存中已有同代码股票简称，则优先回退旧简称
  - 否则会弹出交互式输入，等待 30 秒
  - 用户未输入时，自动剔除前缀
- 空值、`None`、`"None"`、`"nan"` 等异常名称会被清洗为空，并生成空拼音

### 股票英文名称查询

```python
StockNameCodeHelper.get_stock_code_by_english_name('PONY AI')
# 'PONY'

StockNameCodeHelper.get_stock_code_by_english_name('HESAI GROUP')
# 'HSAI'

StockNameCodeHelper.get_stock_info_by_english_name('HESAI GROUP')
# 返回 Yahoo Finance 的 quotes[0] 信息
```

`get_stock_info_by_english_name` 返回结果示例：

```json
{
  "exchange": "NMS",
  "shortname": "Hesai Group",
  "quoteType": "EQUITY",
  "symbol": "HSAI",
  "index": "quotes",
  "score": 20012,
  "typeDisp": "equity",
  "longname": "Hesai Group",
  "exchDisp": "NASDAQ",
  "sector": "Consumer Cyclical",
  "sectorDisp": "消費週期性股票",
  "industry": "Auto Parts",
  "industryDisp": "汽車零件",
  "isYahooFinance": true
}
```

### 基金名称代码

```python
from tcalendars import FundNameCodeHelper

fund_helper = FundNameCodeHelper()

fund_helper.get_fund_name('000001')
fund_helper.get_fund_code('华夏成长混合')

fund_helper.query_shares('000001')
# 返回同一核心基金名称下的所有关联份额

fund_helper.search_by_keyword('华夏')
# 返回包含关键词的 DataFrame

fund_helper.export_to_csv('fund_name_code.csv')
```

### 基金名称清洗规则

`FundNameCodeHelper.query_shares()` 内部会对基金简称做标准化清洗，用于识别不同份额：
- 删除中英文括号内容
- 删除空白字符
- 删除末尾份额标识，如 `A` / `C` / `A类`
- 删除基金类型后缀，如 `FOF` / `LOF` / `ETF` / `QDII` / `REITs`
