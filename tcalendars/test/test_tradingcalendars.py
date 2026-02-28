import unittest
from os import path
import shutil
from tcalendars import TradingCalendars
from tcalendars.tools.get_se_calendar import get_calendar_filename

CWD = path.abspath(path.dirname(__file__))


class TestTradingCalendars(unittest.TestCase):
    def test_normal(self):
        src_filename = path.join(CWD, 'calendar.csv')
        dis_filename = get_calendar_filename(path.dirname(CWD))
        shutil.copy(src_filename, dis_filename)
        tc = TradingCalendars()
        self.assertFalse(tc.is_trading_day('2024-11-24'))
        self.assertTrue(tc.is_trading_day('2024-11-28'))
        self.assertFalse(tc.is_trading_day('2224-11-24'))
        self.assertEqual(tc.get_trading_days('2024-11-24', '2024-11-28'), ['2024-11-25', '2024-11-26', '2024-11-27', '2024-11-28'])
        self.assertEqual(tc.get_trading_day('2024-11-24'), '2024-11-25')
        self.assertEqual(tc.get_trading_day('2024-11-28'), '2024-11-28')
        self.assertIsNone(tc.get_trading_day('2224-11-24'))


if __name__ == '__main__':
    unittest.main()  # pragma: no cover
