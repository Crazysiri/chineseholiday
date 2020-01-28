#!/usr/local/bin/python3
# coding=utf-8
#holiday 模块：1.从服务端获取数据并、2.存入数据库 3.从数据库读数库

import requests
import datetime
import time
import lunar
import json

FESTIVAL_TYPE= {
    'new_years_day' : '元旦',
    'spring_festival' : '春节',
    'tomb_sweeping_day' : '清明节',
    'labour_day' : '国际劳动节',
    'dragon_boat_festival' : '端午节',
    'national_day' : '国庆节',
    'mid_autumn_festival' : '中秋节',
    'day_off' : '调休日需上班'
}


import sqlite3

class HolidayDatabase:
    conn = None
    cursor = None

    def __init__(self):
    	self.connect()
    	self.create_table('holiday',[{'key':'date','type':'varchar not null UNIQUE'},{'key':'json','type':'text'},{'key':'updateDate','type':'varchar not null'}])

    def connect(self):

    	self.conn = sqlite3.connect('data.db')

    	self.cursor = self.conn.cursor()

    	pass

    """
    name:表名
    keys：json [{'key','type'},{'key':'type'}]

    默认创建ID字段 主键
    """
    def create_table(self,name,keys):
    	try:
    		insert_keys = ''
    		for key in keys:
    			insert_keys += ',' + key['key'] + ' ' + key['type']
    		self.cursor.execute('CREATE TABLE %s (id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE %s);' % (name,insert_keys))

    		self.conn.commit()
    		# self.conn.close()

    		return True
    	except Exception as e:
    		return False

    """
    name: 表名
    keys：需要插入的key 数组
    values：需要插入的value 数组
    """
    def insert_values(self,name,keys,values):
    	try:
            flags = []
            for i in range(0,len(keys)):
                flags.append('?')
            keys = ','.join(keys)
            flags = ','.join(flags)
            sql = "INSERT INTO %s (%s) VALUES (%s)" % (name,keys,flags)
            self.cursor.execute(sql,tuple(values))
            self.conn.commit()
            return True
    	except Exception as e:
            return False

    """
    keys 和 values的 大小需要一样
    name:表名
    keys：需要更新的key 数组
    values：需要更新的value 数组
    condtion：条件（id = 1）
    """
    def update_values(self,name,keys,values,condition):
    	try:
    		set_value_array = []
    		for i in range(len(keys)):
    			key = keys[i]
    			value = values[i]
    			if not value:
    				value = "''"
    			set_value_array.append("%s = ?" % key)

    		sql = "update %s set %s where %s;" % (name,','.join(set_value_array),condition)
    		self.cursor.execute(sql,tuple(values))
    		self.conn.commit()
    		return True
    	except Exception as e:
    		return False

#以下两个方法为数据库的应用方法 一个是更新数据 一个是获取数据

    #json 是字符串的json数据
    def setData(self,dateString,json,updateDate):
        status = self.insert_values('holiday',['date','json','updateDate'],[dateString,json,updateDate])
        if not status:
            self.update_values('holiday',['date','json','updateDate'],[dateString,json,updateDate],'date = %s' % dateString)

    def getData(self,condition='where 1'):
        keys = ['date','json','updateDate']
        sql = "SELECT %s from holiday %s;" % (','.join(keys), condition)
        print(sql)
        cursor = self.cursor.execute(sql)
        results = []
        for row in cursor:
        	result = {}
        	for i in range(len(keys)):
        		result[keys[i]] = row[i]
        	results.append(result)

        return results

class Holiday:
    """
     public methods

     is_holiday 是否是节日
     is_holiday_today 今天是否是节假日
     getHoliday 获取节假日

     """

    database = None
    session = None
    """docstring for Holiday."""
    def __init__(self):
        self.database = HolidayDatabase()
        session = requests.session()
        requests.adapters.DEFAULT_RETRIES = 5 # 增加重连次数
        session.keep_alive = False
        # session.proxies = {"https": "47.100.104.247:8080", "http": "36.248.10.47:8080", }
        self.session = session

    def is_holiday(self,day):
        """
        判断是否节假日, api 来自百度 apistore: [url]http://apistore.baidu.com/apiworks/servicedetail/1116.html[/url]
        :param day: 日期， 格式为 '20160404'
        :return: bool
        api = 'http://tool.bitefu.net/jiari/'
        params = {'d': day, 'apiserviceid': 1116}
        rep = requests.get(api, params)
        if rep.status_code != 200:
            return '无法获取节日数据'
        res = rep.text
        return "法定节日" if res != "0" else "非法定节日"
        """
        holiday_api = 'http://timor.tech/api/holiday/info/{0}'.format(day)
        rep =requests.get(holiday_api)
        if rep.status_code != 200:
            return '无法获取节日数据'
        holiday_date = rep.json()
        get_day = holiday_date['type']['type']
        result = ''
        if get_day == 0:
            result = '工作日'
        elif get_day == 1:
            result = '休息日'
        elif get_day == 2:
            result = '节假日'
        else:
            result = '出错了呀！'
        return result

    def is_holiday_today(self):
        """
        判断今天是否时节假日
        :return: bool
        """
        today = datetime.date.today().strftime('%Y-%m-%d')
        return self.is_holiday(today)

    #获取节日数据
    def holiday_handle(self,list):
        subkey = {'date': '阳历日期','nlyf': '农历月份','nl': '农历','w1': '天气','jq': '节气', 'hmax': '最高温度', 'hmin': '最低温度', 'hgl': '降水概率', 'fe': '阴历节日', 'yl': '阳历节日', 'wk': '星期', 'time': '发布时间'}
        results = {}
        for dict in list:
            subdict = {value: dict[key] for key, value in subkey.items()}
            if subdict['阴历节日'] != '' or subdict['阳历节日']!= '':
                year = int(subdict['阳历日期'][0:4],base=10);
                month = (int(subdict['阳历日期'][4:6],base=10) if int(subdict['阳历日期'][4:6],base=10) >=10 else int(subdict['阳历日期'][5:6],base=10))
                day = (int(subdict['阳历日期'][6:8],base=10) if int(subdict['阳历日期'][6:8],base=10) >=10 else int(subdict['阳历日期'][7:8],base=10))
                hlday = subdict['阴历节日']+subdict['阳历节日'];
                ##print(datetime.date(year=year, month=month, day=day).str()+"-"+hlday)
                results[datetime.date(year=year, month=month, day=day)] = hlday
        return results

    #days 每几天更新数据 days = 0 则每次更新
    def getHoliday(self,days = 1):
        last_date = '2020-01-01' #这个是默认时间，数据库读不到 取当天肯定会执行更新逻辑
        try:
            last_date = self.database.getData('LIMIT 1')[0]['updateDate']
        except Exception as e:
            print('getHoliday:database get last object')
            print(e)

        # 计算今天和未来一个日期的天数差值
        now_str = datetime.datetime.now().strftime('%Y-%m-%d')
        today = datetime.datetime.strptime(now_str, "%Y-%m-%d")
        last_update = datetime.datetime.strptime(last_date,'%Y-%m-%d')
        interval = today - last_update
        #从服务器拿数据
        if interval.days > days or days == 0:
            list = self.getholidayForNMonths()
            try:
                for subList in list:
                    #一次获取 是一个subList
                    for dict in subList:
                        # print(dict)
                        self.database.setData(dict['date'],json.dumps(dict),today.strftime('%Y-%m-%d'))

            except Exception as e:
                print('getHoliday:getholidayForNMonths:')
                print(e)

        #从本地数据库拿数据
        results = self.database.getData()
        list = []
        for result in results:
            r = json.loads(result['json'])
            list.append(r)
        return self.holiday_handle(list)

    #n 获取从该月开始的往后n个月的数据 ,这里n要小于12 因为year += 1
    def getholidayForNMonths(self,n=6):
        # return self.getonline40dholiday('101010100',datetime.date.today().strftime('%Y%m%d'))
        year_str = time.strftime("%Y", time.localtime())
        month_str = time.strftime("%m", time.localtime())
        year      = int(year_str)
        month     = int(month_str)
        list = []
        for i in range(1,n+1):
            m = month
            y = year
            if m + i > 12:
                y += 1
                m = m + i - 12
            else:
                m = month + i
            results = self.getonline40dholiday('101010100',str(year),"{:0>2d}".format(m))
            sub_list = []
            for r in results:
                #有阴历或阳历节日的
                if r['fe'] != '' or r['yl'] != '':
                    sub_list.append(r)
            list.append(sub_list)
        return list

    #year month 需要字符串 '2010' '01'
    def getonline40dholiday(self,citycode,year,month):
        url = "http://d1.weather.com.cn/calendar_new/"+year+"/"+citycode+"_"+year+month+".html";
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36",
         "Referer": "http://www.weather.com.cn/weather40d/"+citycode+".shtml"}
        res = self.session.get(url, headers=headers)
        json_str = res.content.decode(encoding='utf-8')[11:]
        list = json.loads(json_str)
        return list

def main():
    print(Holiday().getHoliday())


if __name__ == '__main__':
    main()
