#!/usr/local/bin/python3
# coding=utf-8
# Created:     20/07/2012
# Copyright:   http://www.cnblogs.com/txw1958/
'''
A Chinese Calendar Library in Python
'''


import os, io, sys, re, time, datetime, base64
from datetime import timedelta
path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(path)
import  term
from term import jieqi

__version__ = "$Rev: 123 $"
__all__ = ['LunarDate']


solar_year          = 1900
solar_month         = 1
solar_day           = 31
solar_weekday          = 0

lunar_year          = 0
lunar_month         = 0
lunar_day           = 0
lunar_isLeapMonth   = False
#   0620#aa 生日# #bb 纪念日#
# '([\w+?\#?\(?\)?\d+\s?·?]*)' | solar_Fstv | #aa 生日# #bb 纪念日#
# '([\w+?\#?\s?]*)' | festival_handle,weekday_Fstv |  #aa 生日# #bb 纪念日#
# '([\w+?\#?]*)' | solar_Term | #aa
def festival_handle(params,month,day):
    month_str = "{:0>2d}".format(month)
    day_str = "{:0>2d}".format(day)
    # pattern = "(" + month_str + day_str + ")([\w+?\#?\s?]*)"
    # pattern = "(%s%s)#([\s\S]+?)#"%(month_str,day_str)
    # pattern = '#([\s\S]+?)#'
    md = month_str+day_str
    for key,value in params.items():
        if md in key[-4:]:
            return ','.join(params[key])
    return None

class LunarDate(object):
    _startDate = datetime.date(1900, 1, 31)


    @staticmethod
    def fromSolarDate(year, month, day):
        #通过公历年月日生成农历
        #@return  LunarDate
        solarDate = datetime.date(year, month, day)
        offset = (solarDate - LunarDate._startDate).days
        return LunarDate._fromOffset(offset)

    @staticmethod
    def _enumMonth(yearInfo):
        months = [(i, 0) for i in range(1, 13)]
        leapMonth = yearInfo % 16
        if leapMonth == 0:
            pass
        elif leapMonth <= 12:
            months.insert(leapMonth, (leapMonth, 1))
        else:
            raise ValueError("yearInfo %r mod 16 should in [0, 12]" % yearInfo)

        for month, isLeapMonth in months:
            if isLeapMonth:
                days = (yearInfo >> 16) % 2 + 29
            else:
                days = (yearInfo >> (16 - month)) % 2 + 29
            yield month, days, isLeapMonth

    @classmethod
    def _fromOffset(cls, offset):
        def _calcMonthDay(yearInfo, offset):
            for month, days, isLeapMonth in cls._enumMonth(yearInfo):
                if offset < days:
                    break
                offset -= days
            return (month, offset + 1, isLeapMonth)

        offset = int(offset)

        for idx, yearDay in enumerate(Info.yearDays()):
            if offset < yearDay:
                break
            offset -= yearDay
        year = 1900 + idx

        yearInfo = Info.yearInfos[idx]
        print('yearInfo')
        print(year)
        print(idx)
        month, day, isLeapMonth = _calcMonthDay(yearInfo, offset)
        return LunarDate(year, month, day, isLeapMonth)

    @classmethod
    def today(cls):
        res = datetime.date.today()
        return cls.fromSolarDate(res.year, res.month, res.day)


    def __init__(self, year, month, day, isLeapMonth=False):
        global lunar_year
        global lunar_month
        global lunar_day
        global lunar_isLeapMonth

        lunar_year          = int(year)
        lunar_month         = int(month)
        lunar_day           = int(day)
        lunar_isLeapMonth   = bool(isLeapMonth)

        self.year = year
        self.month = month
        self.day = day
        self.isLeapMonth = bool(isLeapMonth)

    def __str__(self):
        return 'LunarDate(%d, %d, %d, %d)' % (self.year, self.month, self.day, self.isLeapMonth)

    __repr__ = __str__

    def toSolarDate(self):
        #输出公历
        #return datetime
        def _calcDays(yearInfo, month, day, isLeapMonth):
            isLeapMonth = int(isLeapMonth)
            res = 0
            ok = False
            for _month, _days, _isLeapMonth in self._enumMonth(yearInfo):
                if (_month, _isLeapMonth) == (month, isLeapMonth):
                    if 1 <= day <= _days:
                        res += day - 1
                        return res
                    else:
                        raise ValueError("day out of range")
                res += _days

            raise ValueError("month out of range")

        offset = 0
        if self.year < 1900 or self.year >= 2050:
            raise ValueError('year out of range [1900, 2050)')
        yearIdx = self.year - 1900
        for i in range(yearIdx):
            offset += Info.yearDays()[i]

        offset += _calcDays(Info.yearInfos[yearIdx], self.month, self.day, self.isLeapMonth)
        return self._startDate + datetime.timedelta(days=offset)

    def __sub__(self, other):
        if isinstance(other, LunarDate):
            return self.toSolarDate() - other.toSolarDate()
        elif isinstance(other, datetime.date):
            return self.toSolarDate() - other
        elif isinstance(other, datetime.timedelta):
            res = self.toSolarDate() - other
            return LunarDate.fromSolarDate(res.year, res.month, res.day)
        raise TypeError

    def __rsub__(self, other):
        if isinstance(other, datetime.date):
            return other - self.toSolarDate()

    def __add__(self, other):
        if isinstance(other, datetime.timedelta):
            res = self.toSolarDate() + other
            return LunarDate.fromSolarDate(res.year, res.month, res.day)
        raise TypeError

    def __radd__(self, other):
        return self + other

    def __lt__(self, other):
        return self - other < datetime.timedelta(0)

    def __le__(self, other):
        return self - other <= datetime.timedelta(0)


class ChineseWord():
    def weekday_str(tm):
        a = '星期一 星期二 星期三 星期四 星期五 星期六 星期日'.split()
        return a[tm]

    def solarTerm(year, month, day):
        a = '小寒 大寒 立春 雨水 惊蛰 春分\
             清明 谷雨 立夏 小满 芒种 夏至\
             小暑 大暑 立秋 处暑 白露 秋分\
             寒露 霜降 立冬 小雪 大雪 冬至'.split()
        return

    def day_lunar(ld):
        a = '初一 初二 初三 初四 初五 初六 初七 初八 初九 初十\
             十一 十二 十三 十四 十五 十六 十七 十八 十九 廿十\
             廿一 廿二 廿三 廿四 廿五 廿六 廿七 廿八 廿九 三十'.split()
        return a[ld - 1]

    def month_lunar(le, lm):
        a = '正月 二月 三月 四月 五月 六月 七月 八月 九月 十月 十一月 十二月'.split()
        if le:
            return "闰" + a[lm - 1]
        else:
            return a[lm - 1]

    def year_lunar(ly):
        y = ly
        tg = '甲 乙 丙 丁 戊 己 庚 辛 壬 癸'.split()
        dz = '子 丑 寅 卯 辰 巳 午 未 申 酉 戌 亥'.split()
        sx = '鼠 牛 虎 兔 龙 蛇 马 羊 猴 鸡 狗 猪'.split()
        return tg[(y - 4) % 10] + dz[(y - 4) % 12] +  sx[(y - 4) % 12] + '年'

class Festival():

    _solar_festival = {'0101': ['元旦节'], '0202': ['世界湿地日'], '0210': ['国际气象节'], '0214': ['情人节'], '0301': ['国际海豹日'], '0303': ['全国爱耳日'], '0305': ['学雷锋纪念日'], '0308': ['妇女节'], '0312': ['植树节', '孙中山逝世纪念日'], '0314': ['国际警察日'], '0315': ['消费者权益日'], '0317': ['中国国医节', '国际航海日'], '0321': ['世界森林日', '消除种族歧视国际日', '世界儿歌日'], '0322': ['世界水日'], '0323': ['世界气象日'], '0324': ['世界防治结核病日'], '0325': ['全国中小学生安全教育日'], '0330': ['巴勒斯坦国土日'], '0401': ['愚人节', '全国爱国卫生运动月(四月)', '税收宣传月(四月)'], '0407': ['世界卫生日'], '0422': ['世界地球日'], '0423': ['世界图书和版权日'], '0424': ['亚非新闻工作者日'], '0501': ['劳动节'], '0504': ['青年节'], '0505': ['碘缺乏病防治日'], '0508': ['世界红十字日'], '0512': ['国际护士节'], '0515': ['国际家庭日'], '0517': ['国际电信日'], '0518': ['国际博物馆日'], '0520': ['全国学生营养日'], '0523': ['国际牛奶日'], '0531': ['世界无烟日'], '0601': ['国际儿童节'], '0605': ['世界环境保护日'], '0606': ['全国爱眼日'], '0617': ['防治荒漠化和干旱日'], '0623': ['国际奥林匹克日'], '0625': ['全国土地日'], '0626': ['国际禁毒日'], '0701': ['中国共·产党诞辰', '香港回归纪念日', '世界建筑日'], '0702': ['国际体育记者日'], '0707': ['抗日战争纪念日'], '0711': ['世界人口日'], '0730': ['非洲妇女日'], '0801': ['建军节'], '0808': ['中国男子节(爸爸节)'], '0815': ['抗日战争胜利纪念'], '0908': ['国际扫盲日', '国际新闻工作者日'], '0909': ['毛·泽东逝世纪念'], '0910': ['中国教师节'], '0914': ['世界清洁地球日'], '0916': ['国际臭氧层保护日'], '0918': ['九·一八事变纪念日'], '0920': ['国际爱牙日'], '0927': ['世界旅游日'], '0928': ['孔子诞辰'], '1001': ['国庆节', '世界音乐日', '国际老人节'], '1002': ['国庆节假日', '国际和平与民主自由斗争日'], '1003': ['国庆节假日'], '1004': ['世界动物日'], '1006': ['老人节'], '1008': ['全国高血压日', '世界视觉日'], '1009': ['世界邮政日', '万国邮联日'], '1010': ['辛亥革命纪念日', '世界精神卫生日'], '1013': ['世界保健日', '国际教师节'], '1014': ['世界标准日'], '1015': ['国际盲人节(白手杖节)'], '1016': ['世界粮食日'], '1017': ['世界消除贫困日'], '1022': ['世界传统医药日'], '1024': ['联合国日'], '1031': ['世界勤俭日'], '1107': ['十月社会主义革命纪念日'], '1108': ['中国记者日'], '1109': ['全国消防安全宣传教育日'], '1110': ['世界青年节'], '1111': ['光棍节', '国际科学与和平周(本日所属的一周)'], '1112': ['孙中山诞辰纪念日'], '1114': ['世界糖尿病日'], '1116': ['国际宽容日'], '1117': ['国际大学生节', '世界学生节'], '1120': ['彝族年'], '1121': ['彝族年', '世界问候日', '世界电视日'], '1122': ['彝族年'], '1129': ['国际声援巴勒斯坦人民国际日'], '1201': ['世界艾滋病日'], '1203': ['世界残疾人日'], '1205': ['国际经济和社会发展志愿人员日'], '1208': ['国际儿童电视日'], '1209': ['世界足球日'], '1210': ['世界人权日'], '1212': ['西安事变纪念日'], '1213': ['南京大屠杀(1937年)纪念日'], '1220': ['澳门回归纪念'], '1221': ['国际篮球日'], '1224': ['平安夜'], '1225': ['圣诞节'], '1226': ['毛·泽东诞辰纪念日']}

    _lunar_festival = {'0101': ['春节'], '0115': ['元宵节'], '0202': ['春龙节'], '0505': ['端午节'], '0707': ['七夕情人节'], '0715': ['中元节'], '0815': ['中秋节'], '0909': ['重阳节'], '1208': ['腊八节'], '1223': ['小年'], '1229': ['除夕']}

    _is_create_weekday = False #是否创建了某月第几个周末的节日
    _weekday_festival = {'0150': ['世界防治麻风病日'], '0520': ['母亲节'], '0530': ['全国助残日'], '0630': ['父亲节'], '0730': ['被奴役国家周'], '0932': ['国际和平日'], '0940': ['国际聋人节', '世界儿童日'], '0950': ['世界海事日'], '1011': ['国际住房日'], '1013': ['国际减轻自然灾害日(减灾日)'], '1144': ['感恩节']}

    _weekday_festival_reserse = {} #这个字典用来记录 用节日名字做为key 实际日期做为value的 数据

    _solar_term = {}

    # _winter_solstice = {}
    #
    # _summer_solstice = {}

    @classmethod
    def lunar_Fstv(cls,lunar_month, lunar_day):
        #农历节日
        return festival_handle(Festival._lunar_festival,lunar_month,lunar_day)

    #国历节日
    @classmethod
    def solar_Fstv(cls,solar_month, solar_day):
        return festival_handle(Festival._solar_festival,solar_month,solar_day)

    @classmethod
    def _create_weekday_festival(cls):

        if cls._is_create_weekday:
            return
        cls._is_create_weekday = True

        year = datetime.date.today().year

        for key,value in cls._weekday_festival.items():
            month = int(key[:2])
            w = int(key[3:])
            n = int(key[2])
            first = datetime.date(year, month, 1).weekday() + 1#该月的第一天星期几
            day = 1 + 7 - first + w + (n - 1) * 7
            if day > 30: #  如果有计算错误 此处30需要改成当月天数
                day = day - 7 #此处只减一个7，因为上面数据最大为5，而实际上每月最少有4个星期n，所以减1即可
            month_str = "{:0>2d}".format(month)
            day_str = "{:0>2d}".format(day)
            date_str = month_str + day_str
            for k in value:
                cls._weekday_festival_reserse[k] = date_str
            cls._solar_festival[date_str] = value

    @classmethod
    def _create_terms(cls):
        #计算节气 并且 把清明节放入节日中，获取夏至和冬至
        if not Festival._solar_term:
            terms = jieqi().creat_year_jieqi(datetime.date.today().year)
            for item in terms:
                comps = item['time'].split('-')
                if item['name'] == '清明':
                    Festival._solar_festival[comps[1]+comps[2]] = ['清明节']
                Festival._solar_term[comps[1]+comps[2]] = [item['name']]
    #24节气
    @classmethod
    def solar_Term(cls,solar_month, solar_day):
        return festival_handle(Festival._solar_term,solar_month,solar_day)


class Info():
    yearInfos = [
        #    /* encoding:
        #               b bbbbbbbbbbbb bbbb
        #       bit#    1 111111000000 0000
        #               6 543210987654 3210
        #               . ............ ....
        #       month#    000000000111
        #               M 123456789012   L
        #
        #    b_j = 1 for long month, b_j = 0 for short month
        #    L is the leap month of the year if 1<=L<=12; NO leap month if L = 0.
        #    The leap month (if exists) is long one iff M = 1.
        #    */
        0x04bd8,                                    #   /* 1900 */
        0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950,#   /* 1905 */
        0x16554, 0x056a0, 0x09ad0, 0x055d2, 0x04ae0,#   /* 1910 */
        0x0a5b6, 0x0a4d0, 0x0d250, 0x1d255, 0x0b540,#   /* 1915 */
        0x0d6a0, 0x0ada2, 0x095b0, 0x14977, 0x04970,#   /* 1920 */
        0x0a4b0, 0x0b4b5, 0x06a50, 0x06d40, 0x1ab54,#   /* 1925 */
        0x02b60, 0x09570, 0x052f2, 0x04970, 0x06566,#   /* 1930 */
        0x0d4a0, 0x0ea50, 0x06e95, 0x05ad0, 0x02b60,#   /* 1935 */
        0x186e3, 0x092e0, 0x1c8d7, 0x0c950, 0x0d4a0,#   /* 1940 */
        0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0,#   /* 1945 */
        0x092d0, 0x0d2b2, 0x0a950, 0x0b557, 0x06ca0,#   /* 1950 */
        0x0b550, 0x15355, 0x04da0, 0x0a5d0, 0x14573,#   /* 1955 */
        0x052d0, 0x0a9a8, 0x0e950, 0x06aa0, 0x0aea6,#   /* 1960 */
        0x0ab50, 0x04b60, 0x0aae4, 0x0a570, 0x05260,#   /* 1965 */
        0x0f263, 0x0d950, 0x05b57, 0x056a0, 0x096d0,#   /* 1970 */
        0x04dd5, 0x04ad0, 0x0a4d0, 0x0d4d4, 0x0d250,#   /* 1975 */
        0x0d558, 0x0b540, 0x0b5a0, 0x195a6, 0x095b0,#   /* 1980 */
        0x049b0, 0x0a974, 0x0a4b0, 0x0b27a, 0x06a50,#   /* 1985 */
        0x06d40, 0x0af46, 0x0ab60, 0x09570, 0x04af5,#   /* 1990 */
        0x04970, 0x064b0, 0x074a3, 0x0ea50, 0x06b58,#   /* 1995 */
        0x05ac0, 0x0ab60, 0x096d5, 0x092e0, 0x0c960,#   /* 2000 */
        0x0d954, 0x0d4a0, 0x0da50, 0x07552, 0x056a0,#   /* 2005 */
        0x0abb7, 0x025d0, 0x092d0, 0x0cab5, 0x0a950,#   /* 2010 */
        0x0b4a0, 0x0baa4, 0x0ad50, 0x055d9, 0x04ba0,#   /* 2015 */
        0x0a5b0, 0x15176, 0x052b0, 0x0a930, 0x07954,#   /* 2020 */
        0x06aa0, 0x0ad50, 0x05b52, 0x04b60, 0x0a6e6,#   /* 2025 */
        0x0a4e0, 0x0d260, 0x0ea65, 0x0d530, 0x05aa0,#   /* 2030 */
        0x076a3, 0x096d0, 0x04afb, 0x04ad0, 0x0a4d0,#   /* 2035 */
        0x1d0b6, 0x0d250, 0x0d520, 0x0dd45, 0x0b5a0,#   /* 2040 */
        0x056d0, 0x055b2, 0x049b0, 0x0a577, 0x0a4b0,#   /* 2045 */
        0x0aa50, 0x1b255, 0x06d20, 0x0ada0          #   /* 2049 */
        ]

    def yearInfo2yearDay(yearInfo):
        yearInfo = int(yearInfo)

        res = 29 * 12

        leap = False
        if yearInfo % 16 != 0:
            leap = True
            res += 29

        yearInfo //= 16

        for i in range(12 + leap):
            if yearInfo % 2 == 1:
                res += 1
            yearInfo //= 2
        return res

    def yearDays():
        yearDays = [Info.yearInfo2yearDay(x) for x in Info.yearInfos]
        return yearDays

    def day2LunarDate(offset):
        offset = int(offset)
        res = LunarDate()

        for idx, yearDay in enumerate(yearDays()):
            if offset < yearDay:
                break
            offset -= yearDay
        res.year = 1900 + idx

class SolarDate():

    def __init__(self):
        global solar_year
        global solar_month
        global solar_day
        global solar_weekday

        t = datetime.datetime.utcnow() + timedelta(hours=8)
        #time.localtime()
        solar_year      = t.year
        solar_month     = t.month
        solar_day       = t.day
        solar_weekday   = t.weekday()
        self.year = solar_year
        self.month = solar_month
        self.day = solar_day
        self.weekday = solar_weekday

    def __str__(self):
        return 'LunarDate(%d, %d, %d, %d)' % (self.year, self.month, self.day, self.isLeapMonth)


class CalendarToday:

    _solar = None
    _lunar = None
    def __init__(self):
        _solar = SolarDate()
        _lunar = LunarDate.fromSolarDate(solar_year,solar_month,solar_day)

    def _solar_festival(self):
        #公历节日
        s = Festival.solar_Fstv(solar_month, solar_day)
        if s:
            return s
        return ''

    def _lunar_festival(self):
        #农历节日
        s =  Festival.lunar_Fstv(lunar_month, lunar_day)
        if s:
            return s
        return ''


    def festival_description(self):
        return self._lunar_festival() + self._solar_festival()

    def solar_Term(self):
        #今日节气
        return Festival.solar_Term(solar_month,solar_day)

    def solar_date_description(self):
        #2000年01月01日
        return str(solar_year) + "年" + str(solar_month) + "月" + str(solar_day) + "日"

    def week_description(self):
        #星期几
        return ChineseWord.weekday_str(solar_weekday)

    def lunar_date_description(self):
        #正月初一
        return ChineseWord.year_lunar(lunar_year) + ' ' + ChineseWord.month_lunar(lunar_isLeapMonth,lunar_month) + ChineseWord.day_lunar(lunar_day)

    def solar(self):
        return solar_year,solar_month,solar_day

    def lunar(self):
        return lunar_year,lunar_month,lunar_day

    @classmethod
    def lunar_to_solar(cls,year,month,day):
        l = LunarDate(year,month,day,False)
        return l.toSolarDate()


    @classmethod
    #date '20000101' type: 1 虚岁 2 周岁
    def get_age_by_birth(cls,year,month,day,t):
        if t == 1:
            return solar_year - (year - 1)
        elif t == 2:
            if solar_month < month:
                return solar_year - year - 1
            elif solar_month == month:
                if solar_day < day:
                    return solar_year - year - 1
                else:
                    return solar_year - year
            else:
                return solar_year - year
        else:
            return -1


Festival._create_terms()
Festival._create_weekday_festival()

def main():
    cal = CalendarToday()
    print(cal.solar_Term())
    print(cal.festival_description())
    print(cal.solar_date_description())
    print(cal.week_description())
    print(cal.lunar_date_description())
    print(cal.solar())
    print(cal.lunar())
    print(CalendarToday.lunar_to_solar(2020,1,5))
    print(Festival.solar_Term(2,4))
    print(ChineseWord.year_lunar(2020))

if __name__ == '__main__':
    main()


"""
    idx = 2020 - 1900
    yearInfo = Info.yearInfos[idx]
    isLeapMonth = False
    for _month, _days, _isLeapMonth in LunarDate._enumMonth(yearInfo):
        if _isLeapMonth:
            isLeapMonth = _isLeapMonth
            break
"""
