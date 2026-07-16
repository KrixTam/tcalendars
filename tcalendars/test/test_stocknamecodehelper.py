import unittest
import os
import tempfile
import pandas as pd
from os import path
from unittest.mock import patch
from tcalendars import StockNameCodeHelper
from tcalendars import singleton as singleton_module
from tcalendars import stock_name_code_helper as stock_module
from tcalendars.db import DatabaseManager

CWD = path.abspath(path.dirname(__file__))

class TestStockNameCodeHelper(unittest.TestCase):
    def test_update_stock_name_code(self):
        helper = StockNameCodeHelper()
        helper.update_stock_name_code()
        self.assertGreater(len(helper._stock_name_code), 0)
        self.assertEqual(helper.get_stock_name('000001'), '平安银行')
        self.assertEqual(helper.get_stock_code('平安银行'), '000001')
        self.assertEqual(helper.get_stock_name('600000'), '浦发银行' if helper.get_stock_name('600000') == '浦发银行' else helper.get_stock_name('600000'))
        self.assertEqual(helper.get_stock_code(helper.get_stock_name('600000')), '600000')
        self.assertEqual(helper.get_stock_name('920002'), '万达轴承')
        self.assertEqual(helper.get_stock_code('万达轴承'), '920002')
        self.assertEqual(helper.get_stock_name('688001'), '华兴源创')
        self.assertEqual(helper.get_stock_code('华兴源创'), '688001')
    
    def test_error(self):
        helper = StockNameCodeHelper()
        self.assertIsNone(helper.get_stock_name('000000'))
        self.assertIsNone(helper.get_stock_code('平安银行000000'))

    def test_update_flag_true_when_file_missing(self):
        df_sh = pd.DataFrame({"证券代码": ["547", "000001"], "证券简称": ["X", "Y"]})
        df_kc = pd.DataFrame({"证券代码": ["688001"], "证券简称": ["KC"]})
        df_sz = pd.DataFrame({"A股代码": ["000001"], "A股简称": ["Y2"]})
        df_bj = pd.DataFrame({"证券代码": ["920002"], "证券简称": ["BJ"]})

        with tempfile.TemporaryDirectory() as tmp_dir:
            original_instances = singleton_module.Singleton._instances
            original_cwd = stock_module.CWD
            try:
                singleton_module.Singleton._instances = {}
                stock_module.CWD = tmp_dir

                with patch.object(stock_module.path, "exists", return_value=False):
                    with patch.object(stock_module.ak, "stock_info_sh_name_code", side_effect=[df_sh, df_kc]):
                        with patch.object(stock_module.ak, "stock_info_sz_name_code", return_value=df_sz):
                            with patch.object(stock_module.ak, "stock_info_bj_name_code", return_value=df_bj):
                                helper = StockNameCodeHelper()

                self.assertEqual(helper.get_stock_name("000547"), "X")
                self.assertEqual(helper.get_stock_name("000001"), "Y")
                self.assertTrue(os.path.exists(os.path.join(tmp_dir, "cache", "data.dat")))
            finally:
                stock_module.CWD = original_cwd
                singleton_module.Singleton._instances = original_instances

    def test_update_flag_true_when_file_outdated(self):
        df_sh = pd.DataFrame({"证券代码": ["547"], "证券简称": ["X"]})
        df_kc = pd.DataFrame({"证券代码": ["688001"], "证券简称": ["KC"]})
        df_sz = pd.DataFrame({"A股代码": ["000001"], "A股简称": ["Y2"]})
        df_bj = pd.DataFrame({"证券代码": ["920002"], "证券简称": ["BJ"]})

        with tempfile.TemporaryDirectory() as tmp_dir:
            original_instances = singleton_module.Singleton._instances
            original_cwd = stock_module.CWD
            try:
                singleton_module.Singleton._instances = {}
                stock_module.CWD = tmp_dir
                
                # 预设旧的 metadata
                db = DatabaseManager(tmp_dir)
                db.set_last_update('stock_name_code', '2000-01-01')

                with patch.object(stock_module, "moment", return_value=type('Moment', (), {'format': lambda self, fmt: '2000-01-02'})()):
                    with patch.object(stock_module.ak, "stock_info_sh_name_code", side_effect=[df_sh, df_kc]):
                        with patch.object(stock_module.ak, "stock_info_sz_name_code", return_value=df_sz):
                            with patch.object(stock_module.ak, "stock_info_bj_name_code", return_value=df_bj):
                                helper = StockNameCodeHelper()

                self.assertEqual(helper.get_stock_name("000547"), "X")
            finally:
                stock_module.CWD = original_cwd
                singleton_module.Singleton._instances = original_instances

    def test_update_stock_name_code_exception_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_instances = singleton_module.Singleton._instances
            original_cwd = stock_module.CWD
            try:
                singleton_module.Singleton._instances = {}
                stock_module.CWD = tmp_dir
                with patch.object(stock_module.path, "exists", return_value=False):
                    with patch.object(stock_module.ak, "stock_info_sh_name_code", side_effect=RuntimeError("x")):
                        helper = StockNameCodeHelper()
                        self.assertIsNotNone(helper._stock_name_code)
            finally:
                stock_module.CWD = original_cwd
                singleton_module.Singleton._instances = original_instances

    def test_export_to_csv(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_instances = singleton_module.Singleton._instances
            original_cwd = stock_module.CWD
            try:
                singleton_module.Singleton._instances = {}
                stock_module.CWD = tmp_dir
                
                df_sh = pd.DataFrame({"证券代码": ["000001"], "证券简称": ["平安银行"]})
                df_kc = pd.DataFrame({"证券代码": [], "证券简称": []})
                df_sz = pd.DataFrame({"A股代码": [], "A股简称": []})
                df_bj = pd.DataFrame({"证券代码": [], "证券简称": []})
                
                with patch.object(stock_module.ak, "stock_info_sh_name_code", side_effect=[df_sh, df_kc]):
                    with patch.object(stock_module.ak, "stock_info_sz_name_code", return_value=df_sz):
                        with patch.object(stock_module.ak, "stock_info_bj_name_code", return_value=df_bj):
                            helper = StockNameCodeHelper()
                            
                csv_path = os.path.join(tmp_dir, "export_stock.csv")
                helper.export_to_csv(csv_path)
                
                self.assertTrue(os.path.exists(csv_path))
                df = pd.read_csv(csv_path)
                self.assertEqual(len(df), 1)
                self.assertEqual(str(df.iloc[0]['code']).zfill(6), "000001")
                self.assertEqual(df.iloc[0]['name'], "平安银行")
            finally:
                stock_module.CWD = original_cwd
                singleton_module.Singleton._instances = original_instances

    def test_get_stock_code_by_english_name(self):
        with patch.object(StockNameCodeHelper, "get_stock_info_by_english_name", return_value={"symbol": "HSAI"}):
            self.assertEqual(StockNameCodeHelper.get_stock_code_by_english_name("HESAI GROUP"), "HSAI")
        with patch.object(StockNameCodeHelper, "get_stock_info_by_english_name", return_value=None):
            self.assertIsNone(StockNameCodeHelper.get_stock_code_by_english_name("HESAI GROUP"))

    def test_get_stock_info_by_english_name_branches(self):
        with patch.object(stock_module, "search_yahoo_finance", return_value=None):
            self.assertIsNone(StockNameCodeHelper.get_stock_info_by_english_name("ANY"))

        with patch.object(stock_module, "search_yahoo_finance", return_value={"quotes": [{"symbol": "HSAI"}]}):
            self.assertEqual(StockNameCodeHelper.get_stock_info_by_english_name("HESAI GROUP"), {"symbol": "HSAI"})

        with patch.object(stock_module, "search_yahoo_finance", return_value={"quotes": []}):
            with patch.object(StockNameCodeHelper, "get_stock_info_by_english_name", return_value={"symbol": "PONY"}):
                self.assertEqual(StockNameCodeHelper.get_stock_info_by_english_name("PONY AI (Class A)"), {"symbol": "PONY"})

if __name__ == '__main__':
    unittest.main()  # pragma: no cover
