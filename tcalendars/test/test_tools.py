import unittest
import pandas as pd
from os import path
from moment import moment
from tcalendars.tools.get_se_calendar import get_calendar_filename, get_calendar

CWD = path.abspath(path.dirname(__file__))


class TestTools(unittest.TestCase):
    def test_get_se_calendars_01(self):
        get_calendar('2005-02-01', '2005-03-01')
        a = pd.read_csv(get_calendar_filename())
        b = pd.read_csv(path.join(CWD, 'calendar.csv'))
        self.assertTrue(a.equals(b))

    def test_get_se_calendars_02(self):
        now = moment().format('YYYY-10-01')
        get_calendar(now)
        a = pd.read_csv(get_calendar_filename())
        get_calendar(now, moment().format('YYYY-12-02'))
        b = pd.read_csv(get_calendar_filename())
        self.assertTrue(a.equals(b))

    def test_get_calendar_filename_01(self):
        filename = get_calendar_filename('.')
        self.assertEqual(filename, './se_calendar.csv')


if __name__ == '__main__':
    unittest.main()  # pragma: no cover
