#! usr/bin/python
#coding=utf-8
"""
中国节假日
版本：0.1.3
"""
from homeassistant.helpers.entity import Entity
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import event as evt
import voluptuous as vol
import logging
from homeassistant.util import Throttle
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
     CONF_NAME)
from homeassistant.helpers.entity import generate_entity_id
import datetime
from datetime import timedelta
import time
from . import holiday
from . import lunar

_LOGGER = logging.getLogger(__name__)

"""
    cal = lunar.CalendarToday()
    print(cal.solar_Term())
    print(cal.festival_description())
    print(cal.solar_date_description())
    print(cal.week_description())
    print(cal.lunar_date_description())
    print(cal.solar())
    print(cal.lunar())
"""

_Log=logging.getLogger(__name__)

DEFAULT_NAME = 'chinese_holiday'
CONF_UPDATE_INTERVAL = 'update_interval'
CONF_SOLAR_ANNIVERSARY = 'solar_anniversary'
CONF_LUNAR_ANNIVERSARY = 'lunar_anniversary'
CONF_CALCULATE_AGE = 'calculate_age'
CONF_CALCULATE_AGE_DATE = 'date'
CONF_CALCULATE_AGE_NAME = 'name'

CONF_NOTIFY_SCRIPT_NAME = 'notify_script_name'
CONF_NOTIFY_TIME = 'notify_time'
CONF_NOTIFY_PRINCIPLES = 'notify_principles'
CONF_NOTIFY_PRINCIPLES_DATE = 'date'
CONF_NOTIFY_PRINCIPLES_NAME = 'name'
CONF_NOTIFY_PRINCIPLES_SOLAR = 'solar'

# CALCULATE_AGE_DEFAULTS_SCHEMA = vol.Any(None, vol.Schema({
#     vol.Optional(CONF_TRACK_NEW, default=DEFAULT_TRACK_NEW): cv.boolean,
#     vol.Optional(CONF_AWAY_HIDE, default=DEFAULT_AWAY_HIDE): cv.boolean,
# }))

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NOTIFY_TIME,default='09:00:00'): cv.time,
    vol.Optional(CONF_NOTIFY_SCRIPT_NAME, default=''): cv.string,
    vol.Optional('show_detail',default=True): cv.boolean,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_SOLAR_ANNIVERSARY, default={}): {
        str : [str]
    },
    vol.Optional(CONF_LUNAR_ANNIVERSARY, default={}): {
        str : [str]
    },
    vol.Optional(CONF_CALCULATE_AGE,default=[]): [
        {
            vol.Optional(CONF_CALCULATE_AGE_DATE): cv.string,
            vol.Optional(CONF_CALCULATE_AGE_NAME): cv.string,
        }
    ],
    vol.Optional(CONF_NOTIFY_PRINCIPLES,default={}): {
        str : [
            {
                vol.Optional(CONF_NOTIFY_PRINCIPLES_NAME,default=''): cv.string,
                vol.Optional(CONF_NOTIFY_PRINCIPLES_DATE,default=''): cv.string,
                vol.Optional(CONF_NOTIFY_PRINCIPLES_SOLAR,default=True): cv.boolean,
            }
        ]
    },
    vol.Optional(CONF_UPDATE_INTERVAL, default=timedelta(hours=8)): (vol.All(cv.time_period, cv.positive_timedelta)),
})


#公历 纪念日 每年都有的
# {'0101':['aa生日','bb生日']}
SOLAR_ANNIVERSARY = {}

#农历 纪念日 每年都有的
# {'0101':['aa生日','bb生日']}
LUNAR_ANNIVERSARY = {}

#纪念日 指定时间的（出生日到今天的计时或今天到某一天还需要的时间例如金婚）
CALCULATE_AGE = {}

NOTIFY_PRINCIPLES = {}
    # '2010-10-10 08:23:12': 'xx',

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the movie sensor."""

    name = config[CONF_NAME]
    interval = config.get(CONF_UPDATE_INTERVAL)
    global SOLAR_ANNIVERSARY
    global LUNAR_ANNIVERSARY
    global CALCULATE_AGE
    global NOTIFY_PRINCIPLES
    SOLAR_ANNIVERSARY = config[CONF_SOLAR_ANNIVERSARY]
    LUNAR_ANNIVERSARY = config[CONF_LUNAR_ANNIVERSARY]
    CALCULATE_AGE = config[CONF_CALCULATE_AGE]
    NOTIFY_PRINCIPLES = config[CONF_NOTIFY_PRINCIPLES]
    script_name = config[CONF_NOTIFY_SCRIPT_NAME]
    notify_time = config[CONF_NOTIFY_TIME]
    show_detail = config['show_detail']
    sensors = [ChineseHolidaySensor(hass, name,notify_time,script_name, interval,show_detail)]
    add_devices(sensors, True)


class ChineseHolidaySensor(Entity):

    _holiday = None
    _lunar = None

    def __init__(self, hass, name,notify_time,script_name, interval,show_detail):
        """Initialize the sensor."""
        self.client_name = name
        self._show_detail = show_detail
        self._state = None
        self._hass = hass
        self._script_name = script_name
        self._notify_time = notify_time
        self._holiday = holiday.Holiday()
        self._lunar = lunar.CalendarToday()
        self.attributes = {}
        self.localizedAttributes = {} #汉化的attributes 用来显示
        self.entity_id = generate_entity_id(
            'sensor.{}', self.client_name, hass=self._hass)
        self.update = Throttle(interval)(self._update)
        self.setListener() #设置脚本通知的定时器
        self.setUpdateListener() #设置更新时间，凌晨00:00:15秒，15秒就是过了一天随便定定
    @property
    def name(self):
        """Return the name of the sensor."""
        return '节假日'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return 'mdi:calendar-today'

    # @property
    # def state_attributes(self):
    #     return self.attributes

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self.localizedAttributes

    #更新为两处，一处为Throttle 默认8小时，此处为第二处 是每天凌晨12:01更新
    def setUpdateListener(self):

        @callback
        def _listener_callback(_):
            self.setUpdateListener()
            self._update()

        self._updateListener = None

        now = datetime.datetime.utcnow() + timedelta(hours=8)
        notify_date_str = now.strftime('%Y-%m-%d') + ' ' + str('00:00:15') #目前预设是每天9点通知
        notify_date = datetime.datetime.strptime(notify_date_str, "%Y-%m-%d %H:%M:%S")
        notify_date = notify_date + timedelta(days=1) #明天的时间
        # notify_date = now + timedelta(seconds=10)

        self._updateListener = evt.async_track_point_in_time(
            self._hass, _listener_callback, notify_date
        )

    def setListener(self):

        @callback
        def _date_listener_callback(_):
            self.setListener() #重设定时器
            self.notify() #执行通知

        self._listener = None
        # now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        now = datetime.datetime.utcnow() + timedelta(hours=8)
        notify_date_str = now.strftime('%Y-%m-%d') + ' ' + str(self._notify_time) #目前预设是每天9点通知
        notify_date = datetime.datetime.strptime(notify_date_str, "%Y-%m-%d %H:%M:%S")
        # notify_date = now + timedelta(seconds=10)
        if notify_date < now:
            _LOGGER.info('小于')
            notify_date = notify_date + timedelta(days=1) #已经过了就设置为明天的时间
        _LOGGER.info('notify_date')
        _LOGGER.info(notify_date)
        self._listener = evt.async_track_point_in_time(
            self._hass, _date_listener_callback, notify_date
        )



    def notify(self):
        import threading
        def call_service_script(message):
            _LOGGER.info('begin call')
            _LOGGER.info(message)
            self._hass.services.call('script',self._script_name,{'message':message})
            _LOGGER.info('end call')

        #[{'days':1,'list':['国庆节']}]
        def dates_need_to_notify():
            """
                {
                 '14|7|1':[{'date':'0101','solar':True}]
                }
            """
            dates = []
            for key,value in NOTIFY_PRINCIPLES.items():
                _LOGGER.info(key)
                _LOGGER.info(value)
                days = key.split('|') #解析需要匹配的天 14|7|1 分别还有14，7，1天时推送
                for item in value:
                    date = item['date'] #0101 格式的日期字符串
                    solar = item['solar'] #是否是公历
                    name = item['name'] #名称这个是个特殊逻辑，只有Festival._weekday_festival中记录的才会用，因为这里记录的每年时间不固定
                    fes_date = None
                    fes_list = []

                    #name和date是互斥的，因为name就是为了母亲节父亲节设计的
                    if name:
                        try:
                            fes_list = [name]
                            date_str = str(self._lunar.solar()[0])+lunar.Festival._weekday_festival_reserse[name] #20200101
                            fes_date = datetime.datetime.strptime(date_str,'%Y%m%d').date()
                        except Exception as e:
                            pass
                    elif date:
                        if solar:
                            date_str = str(self._lunar.solar()[0])+date #20200101
                            fes_date = datetime.datetime.strptime(date_str,'%Y%m%d').date()
                            try:
                                fes_list = lunar.Festival._solar_festival[date]
                            except Exception as e:
                                pass
                            try:
                                fes_list += SOLAR_ANNIVERSARY[date]
                            except Exception as e:
                                pass
                        else:
                            month = int(date[:2])
                            day = int(date[2:])
                            fes_date = lunar.CalendarToday.lunar_to_solar(self._lunar.solar()[0],month,day)#下标和位置
                            try:
                                fes_list = lunar.Festival._lunar_festival[date]
                            except Exception as e:
                                pass
                            try:
                                fes_list += LUNAR_ANNIVERSARY[date]
                            except Exception as e:
                                pass

                    now_str = datetime.datetime.now().strftime('%Y-%m-%d')
                    today = datetime.datetime.strptime(now_str, "%Y-%m-%d").date()
                    diff = (fes_date - today).days

                    if (str(diff) in days) and fes_list:
                        item['day'] = diff
                        item['list'] = fes_list
                        dates.append(item)

            return dates

        if self._script_name and NOTIFY_PRINCIPLES:
            dates = dates_need_to_notify()
            messages = []
            for item in dates:
                days = item['day']
                fes_list = item['list']
                if days == 0:
                    messages.append('今天是 ' + ','.join(fes_list))
                else:
                    messages.append('距离 ' + ','.join(fes_list) + '还有' + str(days) + '天')
            if messages:
                t1 = threading.Thread(target=call_service_script,args=(','.join(messages),))
                t1.start()

    #计算纪念日（每年都有的） count 返回n条 默认只返回1条
    def calculate_anniversary(self,count=1):
        def anniversary_handle(l,age):

            l_new = []
            if age != -1: #年龄-1的时候就是没有年份，而且name里得有生日才加这个
                for name in l:
                    if '生日' in name:
                        l_new.append('%s(%s岁)' % (name,age))
                    else:
                        l_new.append('%s(%s周年)' % (name,age))
                l = l_new;
            return ','.join(l)
        """
            {
                '20200101':[{'anniversary':'0101#xx生日#','solar':True}]
            }
        """
        anniversaries = {}

        for key,value in LUNAR_ANNIVERSARY.items():
            if len(key) == 8: #带年
                year = int(key[:4])
                month = int(key[4:6])
                day = int(key[6:])
                age = lunar.CalendarToday.get_age_by_birth(year,month,day,2) #周岁          
            else:              
                month = int(key[:2])
                day = int(key[2:])
                age = -1

            solar_date = lunar.CalendarToday.lunar_to_solar(self._lunar.solar()[0],month,day)#下标和位置
            date_str = solar_date.strftime('%Y%m%d')
            try:
                l = anniversaries[date_str]
            except Exception as e:
                anniversaries[date_str] = []
                l = anniversaries[date_str]
            l.append({'anniversary':anniversary_handle(value,age),'solar':False})

        for key,value in SOLAR_ANNIVERSARY.items():

            if len(key) == 8: #带年
                year = int(key[:4])
                month = int(key[4:6])
                day = int(key[6:])
                key = key[4:] #剩下的
                age = lunar.CalendarToday.get_age_by_birth(year,month,day,2) #周岁                 
            else:
                age = -1
            date_str = str(self._lunar.solar()[0])+key #20200101
            try:
                l = anniversaries[date_str]
            except Exception as e:
                anniversaries[date_str] = []
                l = anniversaries[date_str]
            l.append({'anniversary':anniversary_handle(value,age),'solar':True})


    #根据key 排序 因为key就是日期字符串
        l=sorted(anniversaries.items(),key=lambda x:x[0])
        #找到第一个大于今天的纪念日
        cur = 0
        results = []
        for item in l:
            key = item[0]
            annis = item[1] #纪念日数组
            now_str = datetime.datetime.now().strftime('%Y-%m-%d')
            today = datetime.datetime.strptime(now_str, "%Y-%m-%d")
            last_update = datetime.datetime.strptime(key,'%Y%m%d')
            days = (last_update - today).days
            if days > 0 and cur < count: #只有大于今天的才会显示，今天的会在纪念日中显示
                cur += 1
                results.append((key,days,annis))
        return results

    #今天是否是自定义的纪念日（阴历和阳历）
    def custom_anniversary(self):
        l_month = self._lunar.lunar()[1]
        l_day = self._lunar.lunar()[2]
        s_month = self._lunar.solar()[1]
        s_day = self._lunar.solar()[2]
        l_anni = lunar.festival_handle(LUNAR_ANNIVERSARY,l_month,l_day)
        s_anni = lunar.festival_handle(SOLAR_ANNIVERSARY,s_month,s_day)
        anni = ''
        if l_anni:
            anni += l_anni
        if s_anni:
            anni += s_anni
        return anni


    def calculate_age(self):
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
                self.attributes['calculate_age_past'] = name
                self.localizedAttributes['过去纪念日'] = name
                self.attributes['calculate_age_past_date'] = date
                self.localizedAttributes['过去纪念日日期'] = date
                self.attributes['calculate_age_past_interval'] = total_seconds
                self.attributes['calculate_age_past_description'] = '{}年{}天{}小时{}分钟{}秒'.format(year,day,hour,minute,second)
                self.localizedAttributes['已经过去'] = '{}年{}天{}小时{}分钟{}秒'.format(year,day,hour,minute,second)

            if (now_day - key).total_seconds() < 0:
                total_seconds = int((key - now_day ).total_seconds())
                year, remainder = divmod(total_seconds,60*60*24*365)
                day, remainder = divmod(remainder,60*60*24)
                hour, remainder = divmod(remainder,60*60)
                minute, second = divmod(remainder,60)
                self.attributes['calculate_age_future'] = name
                self.localizedAttributes['未来纪念日'] = name
                self.attributes['calculate_age_future_date'] = date
                self.localizedAttributes['未来纪念日日期'] = date
                self.attributes['calculate_age_future_interval'] = total_seconds
                self.attributes['calculate_age_future_description'] = '{}年{}天{}小时{}分钟{}秒'.format(year,day,hour,minute,second)
                self.localizedAttributes['还有'] = '{}年{}天{}小时{}分钟{}秒'.format(year,day,hour,minute,second)
    def nearest_holiday(self):
        '''查找离今天最近的法定节假日，并显示天数'''
        now_day = datetime.date.today()
        count_dict = {}
        results = self._holiday.getHoliday()
        for key in results.keys():
            if (key - now_day).days > 0:
                count_dict[key] = (key - now_day).days
        nearest_holiday_dict = {}
        if count_dict:
            nearest_holiday_dict['name'] = results[min(count_dict)]
            nearest_holiday_dict['date'] = min(count_dict).isoformat()
            nearest_holiday_dict['day'] = str((min(count_dict)-now_day).days)

        return nearest_holiday_dict

    def _update(self):
        self.attributes = {} #重置attributes
        self._lunar = lunar.CalendarToday()#重新赋值

        self._state = self._holiday.is_holiday_today()
        self.attributes['solar'] = self._lunar.solar_date_description()
        self.localizedAttributes['今天'] = self._lunar.solar_date_description()
        # self.attributes['今天'] = datetime.date.today().strftime('%Y{y}%m{m}%d{d}').format(y='年', m='月', d='日')
        self.attributes['week'] = self._lunar.week_description()
        self.localizedAttributes['星期'] = self._lunar.week_description()
        self.attributes['lunar'] = self._lunar.lunar_date_description()
        self.localizedAttributes['农历'] = self._lunar.lunar_date_description()
        term = self._lunar.solar_Term()
        if term:
            self.attributes['term'] = term
            self.localizedAttributes['节气'] = term
        festival = self._lunar.festival_description()
        if festival:
            self.attributes['festival'] = festival
            self.localizedAttributes['节日'] = festival

        custom = self.custom_anniversary()
        if custom:
            self.attributes['anniversary'] = custom
            self.localizedAttributes['纪念日'] = custom

        #这里传的数字 控制 显示几个 自定义的纪念日
        results = self.calculate_anniversary(2)

        self.attributes['next_anniversaries'] = []
        self.localizedAttributes['接下来的纪念日'] = []        
        #拼接接下来的纪念日
        for i in range(0,len(results)):
            key,days,annis = results[i]
            s = ''
            for anni in annis:
                s += anni['anniversary']
            if i == 0:
                self.attributes['nearest_anniversary'] = s
                self.localizedAttributes['最近的纪念日'] = s
                self.attributes['nearest_anniversary_date'] = key
                self.localizedAttributes['最近的纪念日日期'] = key
                self.attributes['nearest_anniversary_days'] = days
                self.localizedAttributes['最近的纪念日还有'] = str(days) + '天'
            else:
                next_anniversaries = self.attributes['next_anniversaries']
                next_anniversaries.append({'date':key,'name':s,'days':days})
                next_anniversaries_local = self.localizedAttributes['接下来的纪念日']
                next_anniversaries_local.append('距离纪念日 %s-%s 还有 %s 天 ' % (s,key,days))                

        nearest = self.nearest_holiday()
        if nearest:
            self.attributes['nearest_holiday'] = nearest['name']
            self.localizedAttributes['最近的节日'] = nearest['name']          
            self.attributes['nearest_holiday_date'] = nearest['date']
            self.localizedAttributes['最近的节日日期'] = nearest['date']
            self.attributes['nearest_holiday_days'] = int(nearest['day'])
            self.localizedAttributes['最近的节日还有'] = str(nearest['day']) + '天'
        self.calculate_age()

        info = self._holiday.nearest_holiday_info(12,45)
        if info:
            self.attributes['holiday_info'] = info
            self.localizedAttributes['节假日放假详情'] = info

        if self._show_detail:
            self.localizedAttributes['data'] = self.attributes

   