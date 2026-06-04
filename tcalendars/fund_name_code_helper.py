from os import path
import pandas as pd
import re
from moment import moment
import akshare as ak
from tcalendars.singleton import Singleton
from tcalendars.db import DatabaseManager

CWD = path.abspath(path.dirname(__file__))


class FundNameCodeHelper(metaclass=Singleton):
    def __init__(self):
        self._db = DatabaseManager(CWD)
        self._fund_name_code = pd.DataFrame(columns=['code', 'name'])
        self.update_fund_name_code()

    def update_fund_name_code(self):
        '''
        更新基金名称代码表
        '''
        update_flag = False
        last_update = self._db.get_last_update('fund_name_code')
        today = moment().format('YYYY-MM-DD')
        
        if last_update:
            if last_update < today:
                update_flag = True
        else:
            update_flag = True
            
        if update_flag:
            try:
                df = ak.fund_name_em()
                df = df.rename(columns={"基金代码": "code", "基金简称": "name"})
                df = df[['code', 'name']]
                df["code"] = df["code"].astype(str).str.zfill(6)
                df = df.drop_duplicates(subset=["code"], keep="first")
                
                # 保存到DB
                self._db.save_dataframe('fund_name_code', df)
                self._db.set_last_update('fund_name_code', today)
                
                self._fund_name_code = df
                print(f"更新基金名称代码表成功，共{len(df)}条记录")
            except Exception as e:
                print(f"更新基金名称代码表失败：{e}")
                # 尝试加载旧数据
                self._fund_name_code = self._db.read_dataframe('fund_name_code')
        else:  # pragma: no cover
            print(f"基金名称代码表已最新，无需更新")
            self._fund_name_code = self._db.read_dataframe('fund_name_code')

    def get_fund_name(self, code: str):
        '''
        获取基金代码对应的基金名称
        '''
        try:
            res = self._fund_name_code.loc[self._fund_name_code['code'] == code].iloc[0]['name']
        except IndexError:
            res = None
        return res

    def get_fund_code(self, name: str):
        '''
        获取基金名称对应的基金代码
        '''
        try:
            res = self._fund_name_code.loc[self._fund_name_code['name'] == name].iloc[0]['code']
        except IndexError:
            res = None
        return res

    @staticmethod
    def clean_name(name: str) -> str:
        '''
        提取基金核心名称（去括号、去类型词、去份额后缀）
        '''
        if not name or pd.isna(name):
            return ""
        name = str(name).strip()
        name = re.sub(r'[（(].*?[）)]', '', name)
        name = re.sub(r'\s+', '', name)
        name = re.sub(r'(?:联接|份额|分级)?[A-Z](?:类)?$', '', name)
        name = re.sub(r'(FOF|LOF|ETF|QDII|REITs)$', '', name, flags=re.I)
        return name.strip()

    def query_shares(self, code: str) -> pd.DataFrame:
        '''
        精确模式：查询指定基金代码的所有关联份额
        '''
        target = self._fund_name_code[self._fund_name_code['code'] == code]
        if target.empty:
            return pd.DataFrame()
        base_name = FundNameCodeHelper.clean_name(target.iloc[0]['name'])
        if not base_name:
            return pd.DataFrame()
        cleaned_series = self._fund_name_code['name'].apply(FundNameCodeHelper.clean_name)
        matches = self._fund_name_code[cleaned_series == base_name]
        return matches.drop_duplicates(subset=['code'])[['code', 'name']]

    def search_by_keyword(self, keyword: str) -> pd.DataFrame:
        '''
        模糊模式：按关键词搜索基金名称
        '''
        mask = self._fund_name_code['name'].str.contains(keyword, case=False, na=False, regex=False)
        return self._fund_name_code[mask][['code', 'name']].drop_duplicates()
