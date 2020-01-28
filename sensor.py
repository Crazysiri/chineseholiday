#! usr/bin/python
#coding=utf-8
"""
中国节假日
版本：0.1.0
"""
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
import datetime
from datetime import timedelta
import time
import logging
from homeassistant.util import Throttle
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
     CONF_NAME)
from homeassistant.helpers.entity import generate_entity_id
import json
import re

_Log=logging.getLogger(__name__)



DEFAULT_NAME = 'chinese_holiday'
CONF_UPDATE_INTERVAL = 'update_interval'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_UPDATE_INTERVAL, default=timedelta(minutes=360)): (vol.All(cv.time_period, cv.positive_timedelta)),
})

HOLIDAY = {}

#公历 纪念日 每年都有的
SOLAR_ANNIVERSARY = [
    "0731#仇友博生日#"
]
#农历 纪念日 每年都有的
LUNAR_ANNIVERSARY = [
    "0618#仇友博农历生日#",
]

CALCULATEAGE= {
    #datetime.datetime(year=1990, month=9, day=18, hour=3, minute=32, second=54): '小思出生',
    #datetime.datetime(year=2068, month=5, day=1, hour=12, minute=32, second=54): '小思金婚',
}

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the movie sensor."""
    name = config[CONF_NAME]
    interval = config.get(CONF_UPDATE_INTERVAL)

    sensors = [ChineseHolidaySensor(hass, name, interval)]
    add_devices(sensors, True)

class ChineseHolidaySensor(Entity):
    def __init__(self, hass, name, interval):
        """Initialize the sensor."""
        self.client_name = name
        self._state = None
        self._hass = hass
        self.attributes = {}
        self.entity_id = generate_entity_id(
            'sensor.{}', self.client_name, hass=self._hass)
        self.update = Throttle(interval)(self._update)


    def nearest_holiday(self):
        '''查找离今天最近的法定节假日，并显示天数'''
        now_day = datetime.date.today()
        count_dict = {}
        for key in HOLIDAY.keys():
            if (key - now_day).days > 0:
                count_dict[key] = (key - now_day).days
        nearest_holiday_dict = {}
        if count_dict == {}:
            nearest_holiday_dict['name'] ='本年度已无法定节假日'
            nearest_holiday_dict['date'] = '本年度已无法定节假日'
            nearest_holiday_dict['day'] = '-1'

        else:
            nearest_holiday_dict['name'] = HOLIDAY[min(count_dict)]
            nearest_holiday_dict['date'] = min(count_dict).isoformat()
            nearest_holiday_dict['day'] = str((min(count_dict)-now_day).days)+'天'

        return nearest_holiday_dict

    def nearest_anniversary(self):
        '''查找离今天最近的纪念日，并显示天数'''
        now_day = datetime.date.today()
        count_dict = {}
        for key in ANNIVERSARY.keys():
            if (key - now_day).days > 0:
                count_dict[key] = (key - now_day).days
        nearest_anniversary_dict = {}
        if count_dict == {}:
            nearest_anniversary_dict['name'] = '未定义或无纪念日'
            nearest_anniversary_dict['date'] = '未定义或无纪念日'
            nearest_anniversary_dict['day'] = '-1'
        else:
            nearest_anniversary_dict['name'] = ANNIVERSARY[min(count_dict)]
            nearest_anniversary_dict['date'] = min(count_dict).isoformat()
            nearest_anniversary_dict['day'] = str((min(count_dict)-now_day).days)+'天'

        return nearest_anniversary_dict


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



    @property
    def device_state_attributes(self):
        """Return the state attributes."""

        return self.attributes


    def _update(self):
        self.getonline40dholiday('101240101',datetime.date.today().strftime('%Y%m%d'))
        self._state = self.is_holiday_today()
        self.attributes['今天日期'] = datetime.date.today().strftime('%Y{y}%m{m}%d{d}').format(y='年', m='月', d='日')
        self.attributes['农历'] = lunar.getCalendar_today()['lunar']
        if 'festival' in lunar.getCalendar_today().keys():
            self.attributes['节日'] = lunar.getCalendar_today()['festival']

        month = lunar.getCalendar_today()['lunar_month']
        day = lunar.getCalendar_today()['lunar_day']
        anni = ''
        anni = self.lunar_Fstv(month,day)
        if anni:
            self.attributes['农历纪念日'] = anni

        self.attributes['离今天最近的法定节日'] = self.nearest_holiday()['name']
        self.attributes['法定节日日期'] = self.nearest_holiday()['date']
        self.attributes['还有'] = self.nearest_holiday()['day']
        self.attributes['最近的纪念日'] = self.nearest_anniversary()['name']
        self.attributes['纪念日日期'] = self.nearest_anniversary()['date']
        self.attributes['相隔'] = self.nearest_anniversary()['day']
        if CALCULATEAGE:
            now_day = datetime.datetime.now()
            count_dict = {}
            for key, value in CALCULATEAGE.items():
                if (now_day - key).total_seconds() > 0:
                    total_seconds = int((now_day - key).total_seconds())
                    year, remainder = divmod(total_seconds,60*60*24*365)
                    day, remainder = divmod(remainder,60*60*24)
                    hour, remainder = divmod(remainder,60*60)
                    minute, second = divmod(remainder,60)
                    self.attributes['离'+value+'过去'] = '{}年 {} 天 {} 小时 {} 分钟 {} 秒'.format(year,day,hour,minute,second)
                if (now_day - key).total_seconds() < 0:
                    total_seconds = int((key - now_day ).total_seconds())
                    year, remainder = divmod(total_seconds,60*60*24*365)
                    day, remainder = divmod(remainder,60*60*24)
                    hour, remainder = divmod(remainder,60*60)
                    minute, second = divmod(remainder,60)
                    self.attributes['离'+value+'还差']  = '{}年 {} 天 {} 小时 {} 分钟 {} 秒'.format(year,day,hour,minute,second)
