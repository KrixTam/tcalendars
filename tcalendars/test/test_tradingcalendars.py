import unittest
from os import path
import os
import pandas as pd
from unittest.mock import patch
from tcalendars import TradingCalendars
from tcalendars.tools.get_se_calendar import get_calendar_filename
from tcalendars.db import DatabaseManager
from tcalendars import singleton as singleton_module

CWD = path.abspath(path.dirname(__file__))


class TestTradingCalendars(unittest.TestCase):
    def test_normal(self):
        # 清除 Singleton 实例以确保重新初始化
        singleton_module.Singleton._instances = {}
        
        src_filename = path.join(CWD, 'calendar.csv')
        db_path = get_calendar_filename(path.dirname(CWD))
        
        # 将 CSV 数据导入 SQLite
        df = pd.read_csv(src_filename)
        db = DatabaseManager(path.dirname(CWD))
        db.save_dataframe('se_calendar', df)
        
        with patch('tcalendars.trading_calendars.get_calendar') as mock_get_calendar:
            tc = TradingCalendars()
            self.assertFalse(tc.is_trading_day('2005-02-05'))
            self.assertTrue(tc.is_trading_day('2005-02-04'))
            self.assertFalse(tc.is_trading_day('2224-11-24'))
            self.assertEqual(tc.get_trading_days('2005-02-01', '2005-02-04'), ['2005-02-01', '2005-02-02', '2005-02-03', '2005-02-04'])
            self.assertEqual(tc.get_trading_day('2005-02-05'), '2005-02-16')
            self.assertEqual(tc.get_trading_day('2005-02-04'), '2005-02-04')
            self.assertIsNone(tc.get_trading_day('2224-11-24'))


if __name__ == '__main__':
    unittest.main()  # pragma: no cover
