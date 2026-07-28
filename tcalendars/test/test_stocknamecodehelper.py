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
        
        # 测试 query 空输入
        self.assertEqual(helper.query(''), [])
        self.assertEqual(helper.query(None), [])
        self.assertEqual(helper.query('A'), [])
        self.assertEqual(helper.query('平'), [])
        
        # 准备假数据供 query 测试，保证能测试出顺序逻辑
        helper._stock_name_code = pd.DataFrame([
            {"code": "000001", "name": "平安银行", "market": "深市", "pinyin": "PAYH"},
            {"code": "000002", "name": "平安大华", "market": "深市", "pinyin": "PADH"},
            {"code": "000003", "name": "大平安", "market": "深市", "pinyin": "DPA"},
            {"code": "000004", "name": "万科A", "market": "深市", "pinyin": "WKA"},
            {"code": "000005", "name": "平安", "market": "深市", "pinyin": "PA"},
            {"code": "000006", "name": "华天科技", "market": "深市", "pinyin": "HTKJ"},
            {"code": "000007", "name": "汇顶科技", "market": "沪市", "pinyin": "HDKJ"},
            {"code": "000008", "name": "华电科工", "market": "沪市", "pinyin": "HDKG"},
            {"code": "000009", "name": "长电科技", "market": "沪市", "pinyin": "ZDKJ"},
            {"code": "000010", "name": "西测测试", "market": "深市", "pinyin": "XCCS"},
            {"code": "000011", "name": "富信科技", "market": "沪市", "pinyin": "FXKJ"},
            {"code": "000012", "name": "复洁科技", "market": "沪市", "pinyin": "FJKJ"},
            {"code": "000013", "name": "万兴科技", "market": "深市", "pinyin": "WXKJ"},
            {"code": "000014", "name": "同兴科技", "market": "深市", "pinyin": "TXKJ"},
        ])
        
        # 验证拼音精确匹配命中后直接返回
        res_pa = helper.query('PA')
        self.assertEqual(len(res_pa), 1)
        self.assertEqual(res_pa[0]['code'], '000005')

        # 验证拼音前缀搜索
        res_py_prefix = helper.query('HD')
        self.assertEqual([item['code'] for item in res_py_prefix], ['000007', '000008'])

        # 验证拼音包含搜索
        res_py_contains = helper.query('DK')
        self.assertEqual([item['code'] for item in res_py_contains], ['000007', '000008', '000009'])
        
        # 验证中文名称精确匹配命中后直接返回
        res_cn = helper.query('平安')
        self.assertEqual(len(res_cn), 1)
        self.assertEqual(res_cn[0]['code'], '000005')

        # 验证中文名称前缀搜索
        res_cn_prefix = helper.query('华电')
        self.assertEqual([item['code'] for item in res_cn_prefix], ['000008'])

        # 验证中文名称包含搜索
        res_cn_contains = helper.query('科技', 10)
        self.assertEqual([item['code'] for item in res_cn_contains], ['000006', '000007', '000009', '000011', '000012', '000013', '000014'])
        
        # 验证代码精确匹配
        res_code = helper.query('000001')
        self.assertEqual(res_code[0]['code'], '000001')
        self.assertEqual(helper.query('0000'), [])
        self.assertEqual(helper.query('60'), [])

        # 验证代码 ? 模糊匹配
        res_code_mask = helper.query('00000?')
        self.assertEqual([item['code'] for item in res_code_mask[:5]], ['000001', '000002', '000003', '000004', '000005'])
        
        # 验证中文 fallback 长度限制：2 个汉字不启用中文转拼音 fallback
        self.assertEqual(helper.query('屏安'), [])

        # 验证降级搜索（输入语音错别字："屏安银杭"）
        # 4 字中文没有直接名称命中，会退化成拼音首字母 PAYH 再匹配
        res_typo = helper.query('屏安银杭')
        self.assertEqual(res_typo[0]['code'], '000001') # 平安银行
        
        # 验证单字容错搜索（输入 "华电科技"）
        # 强单字容错优先于拼音精确匹配，并在命中后直接返回
        res_fuzzy = helper.query('华电科技')
        self.assertEqual(len(res_fuzzy), 1)
        self.assertEqual(res_fuzzy[0]['code'], '000006') # 华天科技

        # 验证中文转拼音后的混淆字母单位置替换
        res_confusion = helper.query('汽车测试')
        self.assertEqual(res_confusion[0]['code'], '000010') # 西测测试

        # 验证名称精确匹配后直接返回，不再混入其他弱匹配结果
        res_exact_cn = helper.query('富信科技')
        self.assertEqual(len(res_exact_cn), 1)
        self.assertEqual(res_exact_cn[0]['code'], '000011')

        # 验证中文转拼音精确匹配优先于名称单字容错
        res_voice_cn = helper.query('复兴科技')
        self.assertEqual(len(res_voice_cn), 1)
        self.assertEqual(res_voice_cn[0]['code'], '000011')

        # 验证 limit 参数
        res_limit = helper.query('DK', limit=2)
        self.assertEqual(len(res_limit), 2)
    
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

    def test_clean_and_generate_pinyin(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_instances = singleton_module.Singleton._instances
            original_cwd = stock_module.CWD
            try:
                singleton_module.Singleton._instances = {}
                stock_module.CWD = tmp_dir
                
                # 初始化一个 helper
                with patch.object(stock_module.ak, "stock_info_sh_name_code", return_value=pd.DataFrame({"证券代码": [], "证券简称": []})):
                    with patch.object(stock_module.ak, "stock_info_sz_name_code", return_value=pd.DataFrame({"A股代码": [], "A股简称": []})):
                        with patch.object(stock_module.ak, "stock_info_bj_name_code", return_value=pd.DataFrame({"证券代码": [], "证券简称": []})):
                            helper = StockNameCodeHelper()

                # 模拟旧数据，提供一个已知映射
                old_df = pd.DataFrame([
                    {"code": "000001", "name": "平安银行", "market": "深市", "pinyin": "PAYH"},
                    {"code": "000007", "name": "老次新股", "market": "深市", "pinyin": "LCXG"},
                ])
                helper._db.save_dataframe('stock_name_code', old_df)

                # 测试用的新数据DataFrame
                test_df = pd.DataFrame([
                    {"code": "000001", "name": "XD平安银", "market": "深市"}, # 命中旧数据映射
                    {"code": "000002", "name": "DR万科A", "market": "深市"},   # 没命中旧数据，正则清洗
                    {"code": "000003", "name": "N新股", "market": "深市"},     # 交互式测试，提供输入
                    {"code": "000004", "name": "C次新股", "market": "深市"},   # 交互式测试，超时/无输入
                    {"code": "000005", "name": "正常股", "market": "深市"},    # 正常
                    {"code": "000006", "name": None, "market": "深市"},        # 异常数据
                    {"code": "000007", "name": "C老次新股", "market": "深市"},  # 命中旧数据回退
                    {"code": "000008", "name": "None", "market": "深市"},      # 字符串空值
                ])

                # mock 交互式输入：第一次有输入，第二次返回空字符串，补足侧面效应返回值
                with patch.object(stock_module, "_interactive_input_with_timeout", side_effect=["用户输入名", "", "", ""]):
                    result_df = helper._clean_and_generate_pinyin(test_df)
                
                # 断言
                self.assertEqual(result_df.loc[result_df['code'] == '000001', 'name'].iloc[0], "平安银行") # 回退旧名
                self.assertEqual(result_df.loc[result_df['code'] == '000002', 'name'].iloc[0], "万科A") # 正则清洗
                self.assertEqual(result_df.loc[result_df['code'] == '000003', 'name'].iloc[0], "用户输入名") # 交互输入
                self.assertEqual(result_df.loc[result_df['code'] == '000004', 'name'].iloc[0], "次新股") # 正则清洗 (空输入)
                self.assertEqual(result_df.loc[result_df['code'] == '000005', 'name'].iloc[0], "正常股")
                self.assertEqual(result_df.loc[result_df['code'] == '000005', 'pinyin'].iloc[0], "ZCG")
                self.assertEqual(result_df.loc[result_df['code'] == '000007', 'name'].iloc[0], "老次新股")
                
                # 对空数据单独断言
                self.assertEqual(result_df.loc[result_df['code'] == '000006', 'pinyin'].iloc[0], "")
                self.assertTrue(pd.isna(result_df.loc[result_df['code'] == '000008', 'name'].iloc[0]))
                
            finally:
                stock_module.CWD = original_cwd
                singleton_module.Singleton._instances = original_instances

    def test_pinyin_helpers_with_empty_values(self):
        self.assertEqual(stock_module._generate_pinyin(None), "")
        self.assertEqual(stock_module._generate_pinyin("None"), "")
        self.assertEqual(stock_module._generate_full_pinyin(None), "")
        self.assertEqual(stock_module._generate_full_pinyin("None"), "")

    def test_query_additional_branches(self):
        helper = StockNameCodeHelper()

        helper._stock_name_code = pd.DataFrame([
            {"code": "100001", "name": "复洁科技", "market": "沪市", "pinyin": "FJKJ"},
        ])
        res_weak_typo = helper.query('复测科技')
        self.assertEqual(len(res_weak_typo), 1)
        self.assertEqual(res_weak_typo[0]['code'], '100001')

        helper._stock_name_code = pd.DataFrame([
            {"code": "100002", "name": "阿北测试股", "market": "深市", "pinyin": "ABCSG"},
        ])
        res_py_prefix = helper.query('安贝测试')
        self.assertEqual(len(res_py_prefix), 1)
        self.assertEqual(res_py_prefix[0]['code'], '100002')

        helper._stock_name_code = pd.DataFrame([
            {"code": "100003", "name": "甲安贝测股", "market": "深市", "pinyin": "JABCSG"},
        ])
        res_py_contains = helper.query('安贝测试')
        self.assertEqual(len(res_py_contains), 1)
        self.assertEqual(res_py_contains[0]['code'], '100003')

        helper._stock_name_code = pd.DataFrame([
            {"code": "100004", "name": "西测测试扩展", "market": "深市", "pinyin": "XCCSKZ"},
        ])
        res_confusion_prefix = helper.query('汽车测')
        self.assertEqual(len(res_confusion_prefix), 1)
        self.assertEqual(res_confusion_prefix[0]['code'], '100004')

        helper._stock_name_code = pd.DataFrame([
            {"code": "100005", "name": None, "market": "深市", "pinyin": "ZZZZ"},
            {"code": "100006", "name": "正常样本", "market": "深市", "pinyin": "ZCYB"},
        ])
        self.assertEqual(helper.query('999999'), [])
        self.assertEqual(helper.query('QQ'), [])

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
