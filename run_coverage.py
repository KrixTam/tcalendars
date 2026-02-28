import os
import shutil
import coverage
import unittest


def run_all_tests(test_modules):
    suite = unittest.TestSuite()
    for t in test_modules:
        try:
            # If the module defines a suite() function, call it to get the suite.
            mod = __import__(t, globals(), locals(), ['suite'])
            suite_fn = getattr(mod, 'suite')
            suite.addTest(suite_fn())
        except (ImportError, AttributeError):
            # else, just load all the test cases from the module.
            suite.addTest(unittest.defaultTestLoader.loadTestsFromName(t))
    unittest.TextTestRunner().run(suite)


# 删除测试输出目录
dirs = ['log', 'output', 'htmlcov']
for d in dirs:
    if os.path.exists(d):
        shutil.rmtree(d)

test_modules = [
    'tcalendars.test.test_tools',
    'tcalendars.test.test_tradingcalendars',
    'tcalendars.test.test_stocknamecodehelper',
]

# 执行测试用例
cov = coverage.Coverage(source=["./tcalendars"])
cov.start()

run_all_tests(test_modules)

cov.stop()
cov.save()

cov.html_report(directory='htmlcov')