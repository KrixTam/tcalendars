import unittest
import os
import tempfile
import pandas as pd
import tcalendars
from os import path
from unittest.mock import patch
from tcalendars import StockNameCodeHelper

CWD = path.abspath(path.dirname(__file__))

class TestStockNameCodeHelper(unittest.TestCase):
    def test_update_stock_name_code(self):
        helper = StockNameCodeHelper()
        helper.update_stock_name_code()
        self.assertGreater(len(helper._stock_name_code), 0)
        self.assertTrue(helper.get_stock_name('000001'), '平安银行')
        self.assertTrue(helper.get_stock_code('平安银行'), '000001')
        self.assertTrue(helper.get_stock_name('600000'), '浦发银行')
        self.assertTrue(helper.get_stock_code('浦发银行'), '600000')
        self.assertTrue(helper.get_stock_name('920002'), '万达轴承')
        self.assertTrue(helper.get_stock_code('万达轴承'), '920002')
        self.assertTrue(helper.get_stock_name('688001'), '华兴源创')
        self.assertTrue(helper.get_stock_code('华兴源创'), '688001')
    
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
            original_instances = tcalendars.Singleton._instances
            original_cwd = tcalendars.CWD
            try:
                tcalendars.Singleton._instances = {}
                tcalendars.CWD = tmp_dir

                with patch.object(tcalendars.path, "exists", return_value=False):
                    with patch.object(tcalendars.ak, "stock_info_sh_name_code", side_effect=[df_sh, df_kc]):
                        with patch.object(tcalendars.ak, "stock_info_sz_name_code", return_value=df_sz):
                            with patch.object(tcalendars.ak, "stock_info_bj_name_code", return_value=df_bj):
                                helper = tcalendars.StockNameCodeHelper()

                self.assertEqual(helper.get_stock_name("000547"), "X")
                self.assertEqual(helper.get_stock_name("000001"), "Y")
                self.assertTrue(os.path.exists(os.path.join(tmp_dir, "stock_name_code.csv")))
            finally:
                tcalendars.CWD = original_cwd
                tcalendars.Singleton._instances = original_instances

    def test_update_flag_true_when_file_outdated(self):
        df_sh = pd.DataFrame({"证券代码": ["547"], "证券简称": ["X"]})
        df_kc = pd.DataFrame({"证券代码": ["688001"], "证券简称": ["KC"]})
        df_sz = pd.DataFrame({"A股代码": ["000001"], "A股简称": ["Y2"]})
        df_bj = pd.DataFrame({"证券代码": ["920002"], "证券简称": ["BJ"]})

        class _Moment:
            def __init__(self, value):
                self._value = value

            def format(self, _fmt):
                return self._value

        def _moment_side_effect(*args, **kwargs):
            _ = kwargs
            if args:
                return _Moment("2000-01-01")
            return _Moment("2000-01-02")

        with tempfile.TemporaryDirectory() as tmp_dir:
            original_instances = tcalendars.Singleton._instances
            original_cwd = tcalendars.CWD
            try:
                tcalendars.Singleton._instances = {}
                tcalendars.CWD = tmp_dir
                stock_file = os.path.join(tmp_dir, "stock_name_code.csv")
                with open(stock_file, "w", encoding="utf-8") as f:
                    f.write("code,name,market\n")

                with patch.object(tcalendars.path, "exists", return_value=True):
                    with patch.object(tcalendars.path, "getmtime", return_value=0):
                        with patch.object(tcalendars, "moment", side_effect=_moment_side_effect):
                            with patch.object(tcalendars.ak, "stock_info_sh_name_code", side_effect=[df_sh, df_kc]):
                                with patch.object(tcalendars.ak, "stock_info_sz_name_code", return_value=df_sz):
                                    with patch.object(tcalendars.ak, "stock_info_bj_name_code", return_value=df_bj):
                                        helper = tcalendars.StockNameCodeHelper()

                self.assertEqual(helper.get_stock_name("000547"), "X")
            finally:
                tcalendars.CWD = original_cwd
                tcalendars.Singleton._instances = original_instances

    def test_update_stock_name_code_exception_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_instances = tcalendars.Singleton._instances
            original_cwd = tcalendars.CWD
            try:
                tcalendars.Singleton._instances = {}
                tcalendars.CWD = tmp_dir
                with patch.object(tcalendars.path, "exists", return_value=False):
                    with patch.object(tcalendars.ak, "stock_info_sh_name_code", side_effect=RuntimeError("x")):
                        helper = tcalendars.StockNameCodeHelper()
                        self.assertIsNotNone(helper._stock_name_code)
            finally:
                tcalendars.CWD = original_cwd
                tcalendars.Singleton._instances = original_instances

    def test_get_stock_code_by_english_name(self):
        with patch.object(tcalendars.StockNameCodeHelper, "get_stock_info_by_english_name", return_value={"symbol": "HSAI"}):
            self.assertEqual(tcalendars.StockNameCodeHelper.get_stock_code_by_english_name("HESAI GROUP"), "HSAI")
        with patch.object(tcalendars.StockNameCodeHelper, "get_stock_info_by_english_name", return_value=None):
            self.assertIsNone(tcalendars.StockNameCodeHelper.get_stock_code_by_english_name("HESAI GROUP"))

    def test_get_stock_info_by_english_name_branches(self):
        with patch.object(tcalendars, "search_yahoo_finance", return_value=None):
            self.assertIsNone(tcalendars.StockNameCodeHelper.get_stock_info_by_english_name("ANY"))

        with patch.object(tcalendars, "search_yahoo_finance", return_value={"quotes": [{"symbol": "HSAI"}]}):
            self.assertEqual(tcalendars.StockNameCodeHelper.get_stock_info_by_english_name("HESAI GROUP"), {"symbol": "HSAI"})

        with patch.object(tcalendars, "search_yahoo_finance", return_value={"quotes": []}):
            with patch.object(tcalendars.StockNameCodeHelper, "get_stock_code_by_english_name", return_value="PONY"):
                self.assertEqual(tcalendars.StockNameCodeHelper.get_stock_info_by_english_name("PONY AI (Class A)"), "PONY")

if __name__ == '__main__':
    unittest.main()  # pragma: no cover
