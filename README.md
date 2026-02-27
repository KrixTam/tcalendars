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
```