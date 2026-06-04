import random
import requests
import time
from moment import moment
from tcalendars.db import DatabaseManager

SZSE_URL = 'http://www.szse.cn/api/report/exchange/onepersistenthour/monthList'


def get_dates_by_month(date: str):
    '''
    获取date所在月的交易日数据
    '''
    params = {
        'month': moment(date).format('YYYY-MM'),
        'random': random.random(),
    }
    response = requests.get(SZSE_URL, params=params)
    # print(params)
    return response.json()['data']


def get_calendar_filename(dir: str = None):
    '''
    获取交易日历数据库路径
    '''
    return DatabaseManager(dir).db_path


def get_calendar(append: bool = False, start_date: str = '2005-01-01', end_date: str = None, dir: str = None):
    '''
    获取A股交易日历
    :param append: 是否追加到已存在记录
    :param start_date: 开始日期
    :param end_date: 结束日期
    :param dir: 输出目录
    zrxh：weekday，1（星期天） - 7（星期六）
    jybz：1 - 交易日；0 - 非交易日
    jyrq：交易日期
    '''
    if not isinstance(append, bool):
        if start_date == '2005-01-01' and end_date is None and dir is None:
            start_date, end_date, dir, append = append, None, None, False
        else:
            start_date, end_date, dir, append = append, start_date, end_date, False
    print('获取A股交易日历中，请稍等……')
    dt = moment(moment(start_date).format('YYYY-MM-01'))
    if end_date is None:
        now = moment(moment().format('YYYY-12-31'))
    else:
        now = moment(end_date)
    
    db = DatabaseManager(dir)
    
    if not append:
        db.execute('DELETE FROM se_calendar')
    
    def save_data(data):
        for d in data:
            db.execute('''
                INSERT OR REPLACE INTO se_calendar (zrxh, jybz, jyrq)
                VALUES (?, ?, ?)
            ''', (d['zrxh'], d['jybz'], d['jyrq']))

    save_data(get_dates_by_month(dt))
    dt.add(1, 'months', inplace=True)
    count = 0
    while dt <= now:
        save_data(get_dates_by_month(dt))
        count = count + 1
        if count > 10:  # pragma: no cover
            time.sleep(4 + int(random.random()*10))
            count = 0
        dt.add(1, 'months', inplace=True)
