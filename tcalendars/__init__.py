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


class TransactionCalendars(metaclass=Singleton):
    def __init__(self):
        self._se_calendars_filename = get_filename(CWD)
        if path.exists(self._se_calendars_filename):
            self._se_calendar = pd.read_csv(self._se_calendars_filename, dtype=SE_DTYPE)
            now = moment().format('YYYY-MM-DD')
            if self._se_calendar.loc[self._se_calendar['jyrq'] >= now].empty:
                self.update_calendar()
        else:
            self.update_calendar()  # pragma: no cover

    def update_calendar(self):
        get_calendar(dir=CWD)
        self._se_calendar = pd.read_csv(self._se_calendars_filename, dtype=SE_DTYPE)

    def is_trading_day(self, dt):
        try:
            res = bool(self._se_calendar.loc[self._se_calendar['jyrq'] == dt].iloc[0]['jybz'] == 1)
        except IndexError:
            res = False
        return res
