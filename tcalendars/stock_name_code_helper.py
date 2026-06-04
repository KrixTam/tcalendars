from os import path
import pandas as pd
from moment import moment
import akshare as ak
from tcalendars.tools.yfinance_query import search_yahoo_finance
from tcalendars.singleton import Singleton
from tcalendars.db import DatabaseManager

CWD = path.abspath(path.dirname(__file__))


class StockNameCodeHelper(metaclass=Singleton):
    def __init__(self):
        self._db = DatabaseManager(CWD)
        self._stock_name_code = pd.DataFrame(columns=['code', 'name', 'market'])
        self.update_stock_name_code()

    def update_stock_name_code(self):
        '''
        更新股票名称代码表
        '''
        update_flag = False
        last_update = self._db.get_last_update('stock_name_code')
        today = moment().format('YYYY-MM-DD')
        
        if last_update:
            if last_update < today:
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
                
                # 2. 保存到DB
                self._db.save_dataframe('stock_name_code', df_all)
                self._db.set_last_update('stock_name_code', today)
                
                self._stock_name_code = df_all
                print(f"更新股票名称代码表成功，共{len(df_all)}条记录")
            except Exception as e:
                print(f"更新股票名称代码表失败：{e}")
                # 尝试加载旧数据
                self._stock_name_code = self._db.read_dataframe('stock_name_code')
        else:  # pragma: no cover
            print(f"股票名称代码表已最新，无需更新")
            self._stock_name_code = self._db.read_dataframe('stock_name_code')

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
        response = StockNameCodeHelper.get_stock_info_by_english_name(name)
        if response:
            res = response.get('symbol', None)
        else:
            res = None
        return res

    @staticmethod
    def get_stock_info_by_english_name(name: str):
        '''
        获取股票英文名称对应的股票名称和股票代码等信息
        '''
        response = search_yahoo_finance(name)
        # print(response)
        if response:
            quotes = response.get('quotes', [])
            res = quotes[0] if quotes else None
            if res is None and "(" in name and ")" in name:
                res = StockNameCodeHelper.get_stock_info_by_english_name(name.split("(")[0].strip()) # pragma: no cover
        else:
            res = None
        return res
