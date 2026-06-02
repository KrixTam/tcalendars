import random
import requests
import csv
import time
import os
from moment import moment
from os import path

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
    获取交易日历文件名
    '''
    output_filename = 'se_calendar.csv'
    if dir is None:
        dir_name = path.dirname(path.dirname(__file__))
    else:
        dir_name = dir
    return path.join(dir_name, 'cache', output_filename)


def get_calendar(append: bool = False, start_date: str = '2005-01-01', end_date: str = None, dir: str = None):
    '''
    获取A股交易日历
    :param append: 是否追加到已存在文件
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
    filename = get_calendar_filename(dir)
    os.makedirs(path.dirname(filename), exist_ok=True)
    existing_dates = set()
    mode = 'w'
    fieldnames = None
    write_header = True
    if append and path.exists(filename):
        mode = 'a'
        write_header = False
        with open(filename, 'r') as rf:
            reader = csv.DictReader(rf)
            fieldnames = reader.fieldnames
            for row in reader:
                jyrq = row.get('jyrq')
                if jyrq:
                    existing_dates.add(jyrq)
        if not fieldnames:
            mode = 'w'
            write_header = True
    with open(filename, mode) as fd:
        w = None
        for d in get_dates_by_month(dt):
            if w is None:
                w = csv.DictWriter(fd, fieldnames=fieldnames or list(d.keys()))
                if write_header:
                    w.writeheader()
            if append:
                jyrq = d.get('jyrq')
                if jyrq in existing_dates:
                    continue
                if jyrq:
                    existing_dates.add(jyrq)
            w.writerow(d)
        dt.add(1, 'months', inplace=True)
        count = 0
        while dt <= now:
            for d in get_dates_by_month(dt):
                if append:
                    jyrq = d.get('jyrq')
                    if jyrq in existing_dates:
                        continue
                    if jyrq:
                        existing_dates.add(jyrq)
                w.writerow(d)
            count = count + 1
            if count > 10:  # pragma: no cover
                time.sleep(4 + int(random.random()*10))
                count = 0
            dt.add(1, 'months', inplace=True)
