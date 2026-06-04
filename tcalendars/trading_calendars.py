from os import path
import pandas as pd
import numpy as np
from moment import moment
from tcalendars.tools.get_se_calendar import get_calendar
from tcalendars.singleton import Singleton
from tcalendars.db import DatabaseManager

CWD = path.abspath(path.dirname(__file__))


class TradingCalendars(metaclass=Singleton):
    def __init__(self):
        self._db = DatabaseManager(CWD)
        self.update_calendar()

    def init_calendar(self): # pragma: no cover
        '''
        初始化交易日历
        '''
        get_calendar(dir=CWD)
        self._load_calendar()

    def _load_calendar(self):
        df = self._db.read_dataframe('se_calendar')
        if not df.empty:
            # 确保类型正确
            df['zrxh'] = df['zrxh'].astype(np.int8)
            df['jybz'] = df['jybz'].astype(np.int8)
            df['jyrq'] = df['jyrq'].astype(str)
            self._se_calendar = df
        else:
            self._se_calendar = pd.DataFrame(columns=['zrxh', 'jybz', 'jyrq']) # pragma: no cover

    def update_calendar(self):
        '''
        更新交易日历
        '''
        self._load_calendar()
        if not self._se_calendar.empty:
            now_year_last_day = moment().format('YYYY-12-31')
            latest_date = self._se_calendar['jyrq'].max()
            if latest_date < now_year_last_day:
                get_calendar(True, latest_date, None, CWD)
                self._load_calendar()
        else:
            self.init_calendar() # pragma: no cover

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
