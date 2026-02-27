from os import path
import pandas as pd
import numpy as np
from moment import moment
from tcalendars.tools.get_se_calendar import get_filename, get_calendar
CWD = path.abspath(path.dirname(__file__))
SE_DTYPE = {'zrxh': np.int8, 'jybz': np.int8, 'jyrq': str}


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class TradingCalendars(metaclass=Singleton):
    def __init__(self):
        self._se_calendars_filename = get_filename(CWD)
        if path.exists(self._se_calendars_filename):
            self._se_calendar = pd.read_csv(self._se_calendars_filename, dtype=SE_DTYPE)
            now = moment().format('YYYY-MM-DD')
            latest_date = self._se_calendar['jyrq'].max()
            if latest_date < now:
                self.update_calendar(latest_date, now)
        else:
            self.init_calendar()  # pragma: no cover

    def init_calendar(self):
        '''
        初始化交易日历
        '''
        get_calendar(dir=CWD)
        self._se_calendar = pd.read_csv(self._se_calendars_filename, dtype=SE_DTYPE)

    def update_calendar(self, start: str, end: str):
        '''
        更新start到end之间的交易日历
        '''
        get_calendar(start, end, CWD)
        self._se_calendar = pd.read_csv(self._se_calendars_filename, dtype=SE_DTYPE)

    def is_trading_day(self, dt):
        '''
        判断dt是否为交易日
        '''
        try:
            res = bool(self._se_calendar.loc[self._se_calendar['jyrq'] == dt].iloc[0]['jybz'] == 1)
        except IndexError:
            res = False
        return res

    def get_trading_days(self, start: str, end: str):
        '''
        获取start到end之间的所有交易日
        '''
        return self._se_calendar.loc[(self._se_calendar['jyrq'] >= start) & (self._se_calendar['jyrq'] <= end) & (self._se_calendar['jybz'] == 1)]['jyrq'].tolist()

    def get_trading_day(self, dt: str):
        '''
        获取dt所在的交易日
        '''
        latest_date = self._se_calendar['jyrq'].max()
        while not self.is_trading_day(dt):
            if dt < latest_date:
                next_day = moment(dt).add(1, 'days')
                dt = next_day.format('YYYY-MM-DD')
            else:
                return None
        return dt
