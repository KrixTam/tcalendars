import unittest
import os
import tempfile
import pandas as pd
from unittest.mock import patch
from tcalendars.fund_name_code_helper import FundNameCodeHelper
from tcalendars import fund_name_code_helper as fund_module
from tcalendars import singleton as singleton_module
from tcalendars.db import DatabaseManager


class TestFundNameCodeHelper(unittest.TestCase):
    def test_update_fund_name_code_success_when_file_missing(self):
        df = pd.DataFrame(
            {
                "基金代码": ["1", "000001", "000001"],
                "基金简称": ["新能源ETF联接A", "新能源ETF联接C", "新能源ETF联接C"],
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            original_instances = singleton_module.Singleton._instances
            original_cwd = fund_module.CWD
            try:
                singleton_module.Singleton._instances = {}
                fund_module.CWD = tmp_dir

                with patch.object(fund_module.path, "exists", return_value=False):
                    with patch.object(fund_module.ak, "fund_name_em", return_value=df):
                        helper = FundNameCodeHelper()

                self.assertEqual(helper.get_fund_name("000001"), "新能源ETF联接A")
                self.assertTrue(os.path.exists(os.path.join(tmp_dir, "cache", "data.dat")))
                self.assertIsNone(helper.get_fund_name("999999"))
            finally:
                fund_module.CWD = original_cwd
                singleton_module.Singleton._instances = original_instances

    def test_update_fund_name_code_success_when_file_outdated(self):
        df = pd.DataFrame({"基金代码": ["000001"], "基金简称": ["中证红利"]})

        with tempfile.TemporaryDirectory() as tmp_dir:
            original_instances = singleton_module.Singleton._instances
            original_cwd = fund_module.CWD
            try:
                singleton_module.Singleton._instances = {}
                fund_module.CWD = tmp_dir
                
                # 预设旧的 metadata
                db = DatabaseManager(tmp_dir)
                db.set_last_update('fund_name_code', '2000-01-01')

                with patch.object(fund_module, "moment", return_value=type('Moment', (), {'format': lambda self, fmt: '2000-01-02'})()):
                    with patch.object(fund_module.ak, "fund_name_em", return_value=df):
                        helper = FundNameCodeHelper()

                self.assertEqual(helper.get_fund_name("000001"), "中证红利")
            finally:
                fund_module.CWD = original_cwd
                singleton_module.Singleton._instances = original_instances

    def test_update_fund_name_code_exception(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_instances = singleton_module.Singleton._instances
            original_cwd = fund_module.CWD
            try:
                singleton_module.Singleton._instances = {}
                fund_module.CWD = tmp_dir

                with patch.object(fund_module.path, "exists", return_value=False):
                    with patch.object(fund_module.ak, "fund_name_em", side_effect=RuntimeError("x")):
                        helper = FundNameCodeHelper()

                self.assertIsNotNone(helper._fund_name_code)
                # DatabaseManager(tmp_dir) 会自动创建文件，所以这里不检查文件不存在，而是检查表是否没数据
                db = DatabaseManager(tmp_dir)
                df = db.read_dataframe('fund_name_code')
                self.assertTrue(df.empty)
            finally:
                fund_module.CWD = original_cwd
                singleton_module.Singleton._instances = original_instances

    def test_export_to_csv(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_instances = singleton_module.Singleton._instances
            original_cwd = fund_module.CWD
            try:
                singleton_module.Singleton._instances = {}
                fund_module.CWD = tmp_dir

                df_mock = pd.DataFrame({"基金代码": ["000001"], "基金简称": ["中证红利"]})
                with patch.object(fund_module.ak, "fund_name_em", return_value=df_mock):
                    helper = FundNameCodeHelper()

                csv_path = os.path.join(tmp_dir, "export_fund.csv")
                helper.export_to_csv(csv_path)

                self.assertTrue(os.path.exists(csv_path))
                df_out = pd.read_csv(csv_path)
                self.assertEqual(len(df_out), 1)
                self.assertEqual(str(df_out.iloc[0]['code']).zfill(6), "000001")
                self.assertEqual(df_out.iloc[0]['name'], "中证红利")
            finally:
                fund_module.CWD = original_cwd
                singleton_module.Singleton._instances = original_instances

    def test_get_fund_code_and_name(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_instances = singleton_module.Singleton._instances
            original_cwd = fund_module.CWD
            try:
                singleton_module.Singleton._instances = {}
                fund_module.CWD = tmp_dir

                with patch.object(fund_module.path, "exists", return_value=False):
                    with patch.object(fund_module.ak, "fund_name_em", return_value=pd.DataFrame({"基金代码": [], "基金简称": []})):
                        helper = FundNameCodeHelper()

                helper._fund_name_code = pd.DataFrame(
                    [
                        {"code": "000001", "name": "中证红利"},
                        {"code": "000002", "name": "新能源ETF联接A"},
                    ]
                )

                self.assertEqual(helper.get_fund_name("000001"), "中证红利")
                self.assertEqual(helper.get_fund_code("中证红利"), "000001")
                self.assertIsNone(helper.get_fund_name("000003"))
                self.assertIsNone(helper.get_fund_code("不存在"))
            finally:
                fund_module.CWD = original_cwd
                singleton_module.Singleton._instances = original_instances

    def test_clean_name(self):
        self.assertEqual(FundNameCodeHelper.clean_name(None), "")
        self.assertEqual(FundNameCodeHelper.clean_name(float("nan")), "")
        self.assertEqual(FundNameCodeHelper.clean_name(" 新能源ETF联接A "), "新能源")
        self.assertEqual(FundNameCodeHelper.clean_name("中证红利（指数）C类"), "中证红利")
        self.assertEqual(FundNameCodeHelper.clean_name("REITs"), "")

    def test_query_shares_and_search_by_keyword(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_instances = singleton_module.Singleton._instances
            original_cwd = fund_module.CWD
            try:
                singleton_module.Singleton._instances = {}
                fund_module.CWD = tmp_dir

                with patch.object(fund_module.path, "exists", return_value=False):
                    with patch.object(fund_module.ak, "fund_name_em", return_value=pd.DataFrame({"基金代码": [], "基金简称": []})):
                        helper = FundNameCodeHelper()

                helper._fund_name_code = pd.DataFrame(
                    [
                        {"code": "000001", "name": "新能源ETF联接A"},
                        {"code": "000002", "name": "新能源ETF联接C"},
                        {"code": "000003", "name": "新能源"},
                        {"code": "000010", "name": None},
                        {"code": "000100", "name": "中证红利"},
                    ]
                )

                shares = helper.query_shares("000001")
                self.assertEqual(set(shares["code"].tolist()), {"000001", "000002", "000003"})

                self.assertTrue(helper.query_shares("999999").empty)
                self.assertTrue(helper.query_shares("000010").empty)

                res = helper.search_by_keyword("红利")
                self.assertEqual(res["code"].tolist(), ["000100"])
            finally:
                fund_module.CWD = original_cwd
                singleton_module.Singleton._instances = original_instances


if __name__ == "__main__":
    unittest.main()  # pragma: no cover
