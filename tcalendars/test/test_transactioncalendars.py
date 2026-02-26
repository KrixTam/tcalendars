import unittest
from os import path
import shutil
from tcalendars import TransactionCalendars
from tcalendars.tools.get_se_calendar import get_filename

CWD = path.abspath(path.dirname(__file__))


class TestTransactionCalendars(unittest.TestCase):
    def test_normal(self):
        src_filename = path.join(CWD, 'calendar.csv')
        dis_filename = get_filename(path.dirname(CWD))
        shutil.copy(src_filename, dis_filename)
        tc = TransactionCalendars()
        self.assertFalse(tc.is_trading_day('2024-11-24'))
        self.assertTrue(tc.is_trading_day('2024-11-28'))
        self.assertFalse(tc.is_trading_day('2224-11-24'))


if __name__ == '__main__':
    unittest.main()  # pragma: no cover
