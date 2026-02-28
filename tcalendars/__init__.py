from os import path
import pandas as pd
import numpy as np
from moment import moment
from datetime import datetime
import akshare as ak
from tcalendars.tools.get_se_calendar import get_calendar_filename, get_calendar
from tcalendars.tools.yfinance_query import search_yahoo_finance
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
        self._se_calendars_filename = get_calendar_filename(CWD)
        self.update_calendar()

    def update_calendar(self):
        '''
        更新交易日历
        '''
        # 更新新增的交易日历
        if path.exists(self._se_calendars_filename):
            self._se_calendar = pd.read_csv(self._se_calendars_filename, dtype=SE_DTYPE)
            now = moment().format('YYYY-MM-DD')
            latest_date = self._se_calendar['jyrq'].max()
            if latest_date < now:
                get_calendar(latest_date, now, CWD)
                self._se_calendar = pd.read_csv(self._se_calendars_filename, dtype=SE_DTYPE)
        # 初始化下载交易日历
        else:  # pragma: no cover
            get_calendar(dir=CWD)
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

class StockNameCodeHelper(metaclass=Singleton):
    def __init__(self):
        self._stock_name_code_filename = path.join(CWD, 'stock_name_code.csv')
        self._stock_name_code = pd.DataFrame(columns=['code', 'name', 'market'])
        self.update_stock_name_code()

    def update_stock_name_code(self):
        '''
        更新股票名称代码表
        '''
        update_flag = False
        if path.exists(self._stock_name_code_filename):
            today = moment().format('YYYY-MM-DD')
            file_timestamp = moment(datetime.fromtimestamp(path.getmtime(self._stock_name_code_filename))).format('YYYY-MM-DD')
            if file_timestamp < today:
                update_flag = True
        else:
            update_flag = True
        if update_flag:
            try:
                # 1. 获取沪市+深市+北交所股票列表（akshare最新接口）
                # 沪市A股
                df_sh = ak.stock_info_sh_name_code("主板A股")
                df_sh = df_sh.rename(columns={"证券代码": "code", "证券简称": "name"})
                df_sh["market"] = "沪市"

                # 沪市科创板
                df_kc = ak.stock_info_sh_name_code("科创板")
                df_kc = df_kc.rename(columns={"证券代码": "code", "证券简称": "name"})
                df_kc["market"] = "沪市"
                
                # 深市A股（包含创业板）
                df_sz = ak.stock_info_sz_name_code()
                df_sz = df_sz.rename(columns={"A股代码": "code", "A股简称": "name"})
                df_sz["market"] = "深市"
                
                # 北交所A股
                df_bj = ak.stock_info_bj_name_code()
                df_bj = df_bj.rename(columns={"证券代码": "code", "证券简称": "name"})
                df_bj["market"] = "北交所"
                
                # 合并所有市场，去重，补全6位代码（避免短码）
                df_all = pd.concat([df_sh[["code", "name", "market"]], 
                                    df_kc[["code", "name", "market"]],
                                    df_sz[["code", "name", "market"]], 
                                    df_bj[["code", "name", "market"]]], ignore_index=True)
                df_all["code"] = df_all["code"].astype(str).str.zfill(6)  # 补全6位（如547→000547）
                df_all = df_all.drop_duplicates(subset=["code"], keep="first")  # 去重
                
                # 2. 保存到CSV
                df_all.to_csv(self._stock_name_code_filename, index=False, encoding="utf-8-sig")
                self._stock_name_code = df_all
                print(f"更新股票名称代码表成功，共{len(df_all)}条记录")
            except Exception as e:
                print(f"更新股票名称代码表失败：{e}")
        else:
            print(f"股票名称代码表已最新，无需更新")
            self._stock_name_code = pd.read_csv(self._stock_name_code_filename, dtype={'code': str, 'name': str, 'market': str})

    def get_stock_name(self, code: str):
        '''
        获取股票代码对应的股票名称
        '''
        try:
            res = self._stock_name_code.loc[self._stock_name_code['code'] == code].iloc[0]['name']
        except IndexError:
            res = None
        return res

    def get_stock_code(self, name: str):
        '''
        获取股票名称对应的股票代码
        '''
        try:
            res = self._stock_name_code.loc[self._stock_name_code['name'] == name].iloc[0]['code']
        except IndexError:
            res = None
        return res
    
    @staticmethod
    def get_stock_code_by_english_name(name: str):
        '''
        获取股票英文名称对应的股票代码
        '''
        response = search_yahoo_finance(name)
        # print(response)
        if response:
            quotes = response.get('quotes', [])
            res = quotes[0].get('symbol', None) if quotes else None
            if res is None:
                if "(" in name and ")" in name:
                    res = StockNameCodeHelper.get_stock_code_by_english_name(name.split("(")[0].strip())
        else:
            res = None
        return res