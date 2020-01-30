#! usr/bin/python
#coding=utf-8

import datetime
from datetime import timedelta
import holiday
import lunar



SOLAR_ANNIVERSARY = [
    "0620#aa 生日# #bb 纪念日#",
    "0721#cc 生日#"
]
#农历 纪念日 每年都有的
LUNAR_ANNIVERSARY = [
    "0602#cc 农历生日#",
]

CALCULATE_AGE = [
    {
        'date':'2010-10-10 08:23:12',
        'name':'xxx'
    }
]

_lunar = lunar.CalendarToday()

def calculate_age():
    if not CALCULATE_AGE:
        return
    now_day = datetime.datetime.now()
    count_dict = {}
    for item in CALCULATE_AGE:
        date = item[CONF_CALCULATE_AGE_DATE]
        name = item[CONF_CALCULATE_AGE_NAME]
        key = datetime.datetime.strptime(date,'%Y-%m-%d %H:%M:%S')
        if (now_day - key).total_seconds() > 0:
            total_seconds = int((now_day - key).total_seconds())
            year, remainder = divmod(total_seconds,60*60*24*365)
            day, remainder = divmod(remainder,60*60*24)
            hour, remainder = divmod(remainder,60*60)
            minute, second = divmod(remainder,60)
            self.attributes['离'+name+'过去'] = '{}年 {} 天 {} 小时 {} 分钟 {} 秒'.format(year,day,hour,minute,second)
        if (now_day - key).total_seconds() < 0:
            total_seconds = int((key - now_day ).total_seconds())
            year, remainder = divmod(total_seconds,60*60*24*365)
            day, remainder = divmod(remainder,60*60*24)
            hour, remainder = divmod(remainder,60*60)
            minute, second = divmod(remainder,60)
            self.attributes['离'+name+'还差']  = '{}年 {} 天 {} 小时 {} 分钟 {} 秒'.format(year,day,hour,minute,second)


def custom_anniversary():
    lunar_month = _lunar.lunar()[1]
    lunar_day = _lunar.lunar()[2]
    solar_month = _lunar.solar()[1]
    solar_day = _lunar.solar()[2]
    lunar_anni = lunar.festival_handle(LUNAR_ANNIVERSARY,lunar_month,lunar_day)
    solar_anni = lunar.festival_handle(SOLAR_ANNIVERSARY,solar_month,solar_day)
    anni = ''
    if lunar_anni:
        anni += lunar_anni
    if solar_anni:
        anni += solar_anni
    return anni

#计算纪念日（每年都有的）
def calculate_anniversary():
    def anniversary_handle(input_str):
        list = input_str.split('#')
        annis = []
        for i in range(1,len(list)):
            s = list[i]
            s = s.strip()
            if s:
                annis.append(s)
        return ','.join(annis)
    """
        {
            '20200101':[{'anniversary':'0101#xx生日#','solar':True}]
        }
    """
    anniversaries = {}

    for l in LUNAR_ANNIVERSARY:
        date_str = l.split('#')[0]
        month = int(date_str[:2])
        day = int(date_str[2:])
        solar_date = lunar.CalendarToday.lunar_to_solar(_lunar.solar()[0],month,day)#下标和位置
        date_str = solar_date.strftime('%Y%m%d')
        try:
            list = anniversaries[date_str]
        except Exception as e:
            anniversaries[date_str] = []
            list = anniversaries[date_str]
        list.append({'anniversary':anniversary_handle(l),'solar':False})

    for s in SOLAR_ANNIVERSARY:
        date_str = s.split('#')[0]
        date_str = str(_lunar.solar()[0])+date_str #20200101
        try:
            list = anniversaries[date_str]
        except Exception as e:
            anniversaries[date_str] = []
            list = anniversaries[date_str]
        list.append({'anniversary':anniversary_handle(s),'solar':True})


#根据key 排序 因为key就是日期字符串
    list=sorted(anniversaries.items(),key=lambda x:x[0])
    #找到第一个大于今天的纪念日
    for item in list:
        key = item[0]
        annis = item[1] #纪念日数组
        now_str = datetime.datetime.now().strftime('%Y-%m-%d')
        today = datetime.datetime.strptime(now_str, "%Y-%m-%d")
        last_update = datetime.datetime.strptime(key,'%Y%m%d')
        days = (last_update - today).days
        if days > 0:
            return key,days,annis
    return None,None,None

def main():
    import os
    print(os.path.dirname(os.path.realpath(__file__)))
    print(calculate_anniversary())


if __name__ == '__main__':
    main()
