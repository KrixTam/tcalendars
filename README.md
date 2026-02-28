# Trading Calendars(tcalendars)

交易日历，用于交易时间的判断。当前支持的市场有：
- 中国股票市场（2005年1月1日起）

## 安装

```bash
pip install tcalendars
```

## 示例
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
```