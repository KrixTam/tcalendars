import unittest
from os import path
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

if __name__ == '__main__':
    unittest.main()  # pragma: no cover