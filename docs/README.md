# Trading Calendars(tcalendars)

交易日历，用于交易时间的判断。当前支持的市场有：
- 中国股票市场（2005年1月1日起）

## 安装

```bash
pip install playwright
playwright install chromium

pip install tcalendars
```

## 缓存

- `StockNameCodeHelper.get_stock_code_by_english_name` / `StockNameCodeHelper.get_stock_info_by_english_name` 会通过 Playwright 调用 Yahoo Finance 搜索接口
- 所有数据缓存统一存放在 `tcalendars/cache/` 目录下：
  - 数据库：`tcalendars/cache/data.dat` (SQLite 格式，包含交易日历、股票名称代码、基金名称代码等)
  - Yahoo Finance 查询：`tcalendars/cache/.yfinance_cache`（JSON 格式，启动时自动加载到内存缓存）
- `.yfinance_cache` 超过 60 天的缓存不会加载到内存（删除该文件可重建缓存）

## 示例

**代码示例**

```python
from tcalendars import TradingCalendars

calendar = TradingCalendars()
# 判断2023年1月1日是否为交易日
calendar.is_trading_day('2023-01-01')
# 输出：False

# 获取2023年1月1日至2023年1月5日的所有交易日
calendar.get_trading_days('2023-01-01', '2023-01-05')
# 输出：['2023-01-03', '2023-01-04', '2023-01-05']

# 获取2023年1月1日所在的交易日，如果1月1日不是交易日，则返回后一个交易日
calendar.get_trading_day('2023-01-01')
# 输出：'2023-01-03'

from tcalendars import StockNameCodeHelper

helper = StockNameCodeHelper()

# 根据股票代码获取股票名称
helper.get_stock_name('000001')
# 输出：'平安银行'

# 根据股票名称获取股票代码
helper.get_stock_code('平安银行')
# 输出：'000001'

# 根据股票英文名称获取股票代码
StockNameCodeHelper.get_stock_code_by_english_name('PONY AI')
# 输出：'PONY'

StockNameCodeHelper.get_stock_code_by_english_name("HESAI GROUP")
# 输出：'HESAI'

# 根据股票英文名称获取股票信息
StockNameCodeHelper.get_stock_info_by_english_name("HESAI GROUP")
# 输出：{'exchange': 'NMS', 'shortname': 'Hesai Group', 'quoteType': 'EQUITY', 'symbol': 'HSAI', 'index': 'quotes', 'score': 20006.0, 'typeDisp': '股票', 'longname': 'Hesai Group', 'exchDisp': 'NASDAQ', 'sector': 'Consumer Cyclical', 'sectorDisp': '消費週期性股票', 'industry': 'Auto Parts', 'industryDisp': '汽車零件', 'isYahooFinance': True}

# 导出股票名称代码表到CSV文件
helper.export_to_csv('stock_name_code.csv')

from tcalendars import FundNameCodeHelper

fund_helper = FundNameCodeHelper()

# 根据基金代码获取基金名称
fund_helper.get_fund_name('000001')

# 根据基金名称获取基金代码
fund_helper.get_fund_code('华夏成长混合')

# 查询基金关联份额
fund_helper.query_shares('000001')

# 按关键词搜索基金名称
fund_helper.search_by_keyword('华夏')
# 输出：DataFrame
#   code name
# 0  000001 华夏成长混合
# ...

# 导出基金名称代码表到CSV文件
fund_helper.export_to_csv('fund_name_code.csv')
```

*StockNameCodeHelper.get_stock_info_by_english_name* 返回结果示例：

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
  "isYahooFinance": True
}
```
