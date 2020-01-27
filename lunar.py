#!/usr/local/bin/python3
# coding=utf-8
# Created:     20/07/2012
# Copyright:   http://www.cnblogs.com/txw1958/
'''
A Chinese Calendar Library in Python
'''


import os, io, sys, re, time, datetime, base64

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


class LunarDate(object):
    _startDate = datetime.date(1900, 1, 31)

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

    @staticmethod
    def fromSolarDate(year, month, day):
        solarDate = datetime.date(year, month, day)
        offset = (solarDate - LunarDate._startDate).days
        return LunarDate._fromOffset(offset)

    def toSolarDate(self):
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
            offset += yearDays[i]

        offset += _calcDays(yearInfos[yearIdx], self.month, self.day, self.isLeapMonth)
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

    @classmethod
    def today(cls):
        res = datetime.date.today()
        return cls.fromSolarDate(res.year, res.month, res.day)

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
        month, day, isLeapMonth = _calcMonthDay(yearInfo, offset)
        return LunarDate(year, month, day, isLeapMonth)

class ChineseWord():
    def weekday_str(tm):
        a = '星期日 星期一 星期二 星期三 星期四 星期五 星期六'.split()
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
        return tg[(y - 4) % 10] + dz[(y - 4) % 12] + '[' + sx[(y - 4) % 12] + ']' + '年'

class Festival():
    #国历节日 *表示放假日
    def solar_Fstv(solar_month, solar_day):
        sFtv = [
        "0101#元旦节#",
        "0202#世界湿地日#",
        "0210#国际气象节#",
        "0214#情人节#",
        "0301#国际海豹日#",
        "0303#全国爱耳日#",
        "0305#学雷锋纪念日#",
        "0308#妇女节#",
        "0312#植树节# #孙中山逝世纪念日#",
        "0314#国际警察日#",
        "0315#消费者权益日#",
        "0317#中国国医节# #国际航海日#",
        "0321#世界森林日# #消除种族歧视国际日# #世界儿歌日#",
        "0322#世界水日#",
        "0323#世界气象日#",
        "0324#世界防治结核病日#",
        "0325#全国中小学生安全教育日#",
        "0330#巴勒斯坦国土日#",
        "0401#愚人节# #全国爱国卫生运动月(四月)# #税收宣传月(四月)#",
        "0407#世界卫生日#",
        "0422#世界地球日#",
        "0423#世界图书和版权日#",
        "0424#亚非新闻工作者日#",
        "0501#劳动节#",
        "0504#青年节#",
        "0505#碘缺乏病防治日#",
        "0508#世界红十字日#",
        "0512#国际护士节#",
        "0515#国际家庭日#",
        "0517#国际电信日#",
        "0518#国际博物馆日#",
        "0520#全国学生营养日#",
        "0523#国际牛奶日#",
        "0531#世界无烟日#",
        "0601#国际儿童节#",
        "0605#世界环境保护日#",
        "0606#全国爱眼日#",
        "0617#防治荒漠化和干旱日#",
        "0623#国际奥林匹克日#",
        "0625#全国土地日#",
        "0626#国际禁毒日#",
        "0701#中国共·产党诞辰# #香港回归纪念日# #世界建筑日#",
        "0702#国际体育记者日#",
        "0707#抗日战争纪念日#",
        "0711#世界人口日#",
        "0730#非洲妇女日#",
        "0801#建军节#",
        "0808#中国男子节(爸爸节)#",
        "0815#抗日战争胜利纪念#",
        "0908#国际扫盲日# #国际新闻工作者日#",
        "0909#毛·泽东逝世纪念#",
        "0910#中国教师节#",
        "0914#世界清洁地球日#",
        "0916#国际臭氧层保护日#",
        "0918#九·一八事变纪念日#",
        "0920#国际爱牙日#",
        "0927#世界旅游日#",
        "0928#孔子诞辰#",
        "1001#国庆节# #世界音乐日# #国际老人节#",
        "1002#国庆节假日# #国际和平与民主自由斗争日#",
        "1003#国庆节假日#",
        "1004#世界动物日#",
        "1006#老人节#",
        "1008#全国高血压日# #世界视觉日#",
        "1009#世界邮政日# #万国邮联日#",
        "1010#辛亥革命纪念日# #世界精神卫生日#",
        "1013#世界保健日# #国际教师节#",
        "1014#世界标准日#",
        "1015#国际盲人节(白手杖节)#",
        "1016#世界粮食日#",
        "1017#世界消除贫困日#",
        "1022#世界传统医药日#",
        "1024#联合国日#",
        "1031#世界勤俭日#",
        "1107#十月社会主义革命纪念日#",
        "1108#中国记者日#",
        "1109#全国消防安全宣传教育日#",
        "1110#世界青年节#",
        "1111#国际科学与和平周(本日所属的一周)#",
        "1112#孙中山诞辰纪念日#",
        "1114#世界糖尿病日#",
        "1116#国际宽容日#",
        "1117#国际大学生节# #世界学生节#",
        "1120#彝族年#",
        "1121#彝族年# #世界问候日# #世界电视日#",
        "1122#彝族年#",
        "1129#国际声援巴勒斯坦人民国际日#",
        "1201#世界艾滋病日#",
        "1203#世界残疾人日#",
        "1205#国际经济和社会发展志愿人员日#",
        "1208#国际儿童电视日#",
        "1209#世界足球日#",
        "1210#世界人权日#",
        "1212#西安事变纪念日#",
        "1213#南京大屠杀(1937年)纪念日#",
        "1220#澳门回归纪念#",
        "1221#国际篮球日#",
        "1224#平安夜#",
        "1225#圣诞节#",
        "1226#毛·泽东诞辰纪念日#"
        ]
        solar_month_str = str(solar_month) if solar_month > 9 else "0" + str(solar_month)
        solar_day_str = str(solar_day) if solar_day > 9 else "0" + str(solar_day)
        pattern = "(" + solar_month_str + solar_day_str + ")([\w+?\#?\(?\)?\d+\s?·?]*)"
        for solar_fstv_item in sFtv:
            result = re.search(pattern, solar_fstv_item)
            if result is not None:
                return result.group(2)


    def lunar_Fstv(lunar_month, lunar_day):
        #农历节日 *表示放假日
        #每年单独来算
        lFtv = [
        "0101#春节#",
        "0115#元宵节#",
        "0202#春龙节",
        #"0314#清明节#", #每年不一样，此为2012年，事实上为公历节日
        "0505#端午节#",
        "0707#七夕情人节#",
        "0715#中元节#",
        "0815#中秋节#",
        "0909#重阳节#",
        "1208#腊八节#",
        "1223#小年#",
        "1229#除夕#"   #每年不一样，此为2011年
        ]
        lunar_month_str = str(lunar_month) if lunar_month > 9 else "0" + str(lunar_month)
        lunar_day_str = str(lunar_day) if lunar_day > 9 else "0" + str(lunar_day)
        pattern = "(" + lunar_month_str + lunar_day_str + ")([\w+?\#?\s?]*)"
        for lunar_fstv_item in lFtv:
            result = re.search(pattern, lunar_fstv_item)
            if result is not None:
                return result.group(2)

    #国历节日 *表示放假日
    def weekday_Fstv(solar_month, solar_day, solar_weekday):
        #某月的第几个星期几
        wFtv = [
        "0150#世界防治麻风病日#", #一月的最后一个星期日（月倒数第一个星期日）
        "0520#国际母亲节#",
        "0530#全国助残日#",
        "0630#父亲节#",
        "0730#被奴役国家周#",
        "0932#国际和平日#",
        "0940#国际聋人节# #世界儿童日#",
        "0950#世界海事日#",
        "1011#国际住房日#",
        "1013#国际减轻自然灾害日(减灾日)#",
        "1144#感恩节#"]

        #7，14等应该属于1, 2周，能整除的那天实际属于上一周，做个偏移
        offset = -1 if solar_day % 7 == 0 else 0
        #计算当前日属于第几周，得出来从0开始计周，再向后偏移1
        weekday_ordinal = solar_day // 7 + offset + 1

        solar_month_str = str(solar_month) if solar_month > 9 else "0" + str(solar_month)
        solar_weekday_str = str(weekday_ordinal) + str(solar_weekday)

        pattern = "(" + solar_month_str + solar_weekday_str + ")([\w+?\#?\s?]*)"
        for weekday_fstv_item in wFtv:
            result = re.search(pattern, weekday_fstv_item)
            if result is not None:
                return result.group(2)

        #如何计算某些最后一个星期几的情况，..........

    #24节气
    def solar_Term(solar_month, solar_day):
        #每年数据不一样，此为2012年内的数据
        stFtv = [
        "0106#小寒#",
        "0120#大寒#",
        "0204#立春#",
        "0219#雨水#",
        "0305#惊蛰#",
        "0320#春分#",
        "0404#清明#",
        "0420#谷雨#",
        "0505#立夏#",
        "0521#小满#",
        "0605#芒种#",
        "0621#夏至#",
        "0707#小暑#",
        "0722#大暑#",
        "0807#立秋#",
        "0823#处暑#",
        "0907#白露#",
        "0922#秋分#",
        "1008#寒露#",
        "1023#霜降#",
        "1107#立冬#",
        "1122#小雪#",
        "1206#大雪#",
        "1221#冬至#",
        ]
        solar_month_str = str(solar_month) if solar_month > 9 else "0" + str(solar_month)
        solar_day_str = str(solar_day) if solar_day > 9 else "0" + str(solar_day)
        pattern = "(" + solar_month_str + solar_day_str + ")([\w+?\#?]*)"
        for solarTerm_fstv_item in stFtv:
            result = re.search(pattern, solarTerm_fstv_item)
            if result is not None:
                return result.group(2)

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

        solar_year      = int(time.strftime("%Y", time.localtime()))
        solar_month     = int(time.strftime("%m", time.localtime()))
        solar_day       = int(time.strftime("%d", time.localtime()))
        solar_weekday   = int(time.strftime("%w", time.localtime()))

        self.year = solar_year
        self.month = solar_month
        self.day = solar_day
        self.weekday = solar_weekday

    def __str__(self):
        return 'LunarDate(%d, %d, %d, %d)' % (self.year, self.month, self.day, self.isLeapMonth)


def getCalendar_today():
    solar = SolarDate()
    LunarDate.fromSolarDate(solar_year, solar_month, solar_day)

    festival = ""
    result_dict = {}

    if Festival.solar_Term(solar_month, solar_day):
        festival = festival + " 今日节气：" + Festival.solar_Term(solar_month, solar_day)
    if Festival.solar_Fstv(solar_month, solar_day):
        festival = festival + " 公历节日：" + Festival.solar_Fstv(solar_month, solar_day)
    if Festival.weekday_Fstv(solar_month, solar_day, solar_weekday):
        if festival.find("公历节日") == -1:
            festival = festival + " 公历节日：" + Festival.weekday_Fstv(solar_month, solar_day, solar_weekday)
        else:
            festival = festival + " " + Festival.weekday_Fstv(solar_month, solar_day, solar_weekday)
    if Festival.lunar_Fstv(lunar_month, lunar_day):
        festival = festival + " 农历节日：" + Festival.lunar_Fstv(lunar_month, lunar_day)

    twitter = \
    "今天是" + str(solar_year) + "年" + str(solar_month) + "月" + str(solar_day) + "日" + " " \
    + ChineseWord.weekday_str(solar_weekday) + " 农历" + ChineseWord.year_lunar(lunar_year) \
    + ChineseWord.month_lunar(lunar_isLeapMonth,lunar_month) \
    + ChineseWord.day_lunar(lunar_day) + festival
    result_dict['lunar'] =  ChineseWord.month_lunar(lunar_isLeapMonth,lunar_month) + ChineseWord.day_lunar(lunar_day)
    result_dict['lunar_month'] = lunar_month
    result_dict['lunar_day'] = lunar_day
    if festival != "":
        result_dict['festival'] = festival
    return result_dict



def main():
    #"main function"
    #print(base64.b64decode(b'Q29weXJpZ2h0IChjKSAyMDEyIERvdWN1YmUgSW5jLiBBbGwgcmlnaHRzIHJlc2VydmVkLg==').decode())
    #getCalendar_all_day()
    getCalendar_today()


if __name__ == '__main__':
    main()
