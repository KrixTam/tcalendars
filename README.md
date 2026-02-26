# Transaction Calendars(tcalendars)

交易日历，用于交易时间的判断。当前支持的市场有：
- 中国股票市场（2005年1月1日起）

## 安装

```bash
pip install tcalendars
```

## 使用方法
```python
from tcalendars import TransactionCalendars

calendar = TransactionCalendars()
calendar.is_trading_day('2023-01-01')
```