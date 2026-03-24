#!/usr/local/bin/python3
# coding=utf-8
"""
节假日模块：从 API 获取并缓存节假日状态
数据源：http://tool.bitefu.net/jiari/ (主) / 本地 JSON 缓存 (备)
"""
from __future__ import annotations

import datetime
from datetime import datetime as datetime_class
from datetime import timedelta
import json
import logging
import os
import re
import time

import requests

from . import lunar

_LOGGER = logging.getLogger(__name__)

holiday_database_path = os.path.dirname(os.path.realpath(__file__)) + "/data.db"
holiday_status_json_path = (
    os.path.dirname(os.path.realpath(__file__)) + "/holiday.json"
)

# ---------------------------------------------------------------------------
# 轻量 SQLite 数据库（供 getHoliday 旧接口兼容使用）
# ---------------------------------------------------------------------------

class Holiday:
    """节假日查询与缓存。

    主数据源：http://tool.bitefu.net/jiari/
      - 返回格式 {"YYYYMM": {"MMDD": {"type": "0/1/2", "week2": "1-7", ...}}}
      - type 0=工作日 1=休息日 2=法定节假日
    本地缓存：holiday.json（同目录）
    """

    _BITEFU_API = "http://tool.bitefu.net/jiari/"
    _REQUEST_TIMEOUT = 10
    _CACHE_TTL_DAYS = 15  # 超过 N 天重新从服务器拉取

    def __init__(self):
        # __init__ 完全不做 I/O，所有磁盘/网络操作延迟到 _update() 线程中执行
        # 原因：async_setup_entry 在事件循环主线程运行，阻塞 I/O 会被 HA 2024+ 检测并报错
        self._holiday_json: dict = {}
        self._session: requests.Session | None = None

    def _ensure_session(self) -> requests.Session:
        if self._session is None:
            s = requests.Session()
            s.keep_alive = False
            requests.adapters.DEFAULT_RETRIES = 3
            self._session = s
        return self._session

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @classmethod
    def day(cls, n: int) -> datetime_class:
        """返回 UTC+8 当天 + n 天的 datetime。"""
        return datetime_class.utcnow() + timedelta(hours=8) + timedelta(hours=n * 24)

    @classmethod
    def today(cls) -> datetime_class:
        return cls.day(0)

    @classmethod
    def tomorrow(cls) -> datetime_class:
        return cls.day(1)

    # ------------------------------------------------------------------
    # 磁盘缓存读写
    # ------------------------------------------------------------------

    def get_holidays_from_disk(self):
        try:
            with open(holiday_status_json_path, "r") as f:
                self._holiday_json = json.load(f)
        except Exception as e:
            _LOGGER.debug("get_holidays_from_disk: %s", e)

    def _write_cache(self, data: dict):
        try:
            with open(holiday_status_json_path, "w") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            _LOGGER.error("写入节假日缓存失败: %s", e)

    # ------------------------------------------------------------------
    # 服务器拉取（bitefu.net）
    # ------------------------------------------------------------------

    def get_holidays_from_server(self, days: int = 15):
        """从 bitefu.net 更新节假日状态缓存（未来 6 个月）。"""
        data: dict = {}
        update_date = "2000-01-01"

        try:
            with open(holiday_status_json_path, "r") as f:
                data = json.load(f)
        except Exception:
            pass

        if data and "update_time" in data:
            update_date = data["update_time"]

        today = self.today()
        today_str = today.strftime("%Y-%m-%d")
        last_update = datetime_class.strptime(update_date, "%Y-%m-%d")
        interval = today - last_update

        if interval.days <= days and days != 0:
            _LOGGER.debug("get_holidays_from_server: 缓存未过期，跳过更新")
            return

        _LOGGER.info("get_holidays_from_server: 开始从服务器拉取节假日数据...")
        data = {"update_time": today_str}

        for i in range(6):
            month = today.month + i
            year = today.year
            if month > 12:
                year += 1
                month -= 12
            data.setdefault(str(year), {})
            try:
                self._fetch_one_month(year, month, data[str(year)])
                time.sleep(0.5)
            except Exception as e:
                _LOGGER.warning(
                    "get_holidays_from_server: %d-%02d 拉取失败: %s", year, month, e
                )

        self._write_cache(data)
        self._holiday_json = data

    def _fetch_one_month(self, year: int, month: int, year_dict: dict):
        """拉取单月节假日数据并写入 year_dict。"""
        d = f"{year}{month:02d}"
        params = {"d": d, "info": 1}
        try:
            resp = self._ensure_session().get(
                self._BITEFU_API, params=params, timeout=self._REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            _LOGGER.warning("_fetch_one_month %s: %s", d, e)
            return

        if d not in result:
            _LOGGER.warning("_fetch_one_month: 响应中无 %s 数据", d)
            return

        for key, info in result[d].items():
            t = int(info.get("type", 0))
            w = int(info.get("week2", 0))
            # 节假日(1/2)或本应为周末却被调为工作日的(0)都记录
            if t in (1, 2) or (w in (6, 7) and t == 0):
                year_dict[key] = str(t)

    # ------------------------------------------------------------------
    # 节假日状态查询
    # ------------------------------------------------------------------

    def is_holiday_status(self, date: datetime_class) -> int:
        """返回 0=工作日 1=休息日 2=法定节假日。
        
        此方法必须在 executor 线程中调用（包含阻塞 I/O）。
        """
        # 首次调用时从磁盘加载缓存，避免 __init__ 时做 I/O
        if not self._holiday_json:
            self.get_holidays_from_disk()
        self.get_holidays_from_server()

        y_str = str(date.year)
        h_dict = self._holiday_json.get(y_str, {})
        key = f"{date.month:02d}{date.day:02d}"

        if key in h_dict:
            return int(h_dict[key])
        # 没有特殊标注：周末=休息日，工作日=工作日
        return 1 if date.weekday() >= 5 else 0

    def is_holiday(self, date: datetime_class) -> str:
        return {0: "工作日", 1: "休息日", 2: "节假日"}[self.is_holiday_status(date)]

    def is_holiday_today(self) -> str:
        return self.is_holiday(self.today())

    def is_holiday_tomorrow(self) -> str:
        return self.is_holiday(self.tomorrow())

    # ------------------------------------------------------------------
    # 最近节日信息（放假安排详情）
    # ------------------------------------------------------------------

    def nearest_holiday_detail(self, min_days: int = 30, max_days: int = 45) -> dict:
        """返回最近一次法定节假日的结构化放假安排。"""
        today = self.today()
        for y in self._holiday_json:
            if y == "update_time":
                continue
            dates = self._holiday_json[y]
            for m, t in dates.items():
                if int(t) != 2:
                    continue
                d = "{}-{}-{}".format(y, m[0:2], m[2:])
                date = datetime_class.strptime(d, "%Y-%m-%d")
                diff = (date - today).days
                if diff > max_days:
                    continue

                start = date
                end = date

                while self.is_holiday_status(start) != 0:
                    start -= timedelta(days=1)
                while self.is_holiday_status(end) != 0:
                    end += timedelta(days=1)

                start += timedelta(days=1)
                end -= timedelta(days=1)

                if diff < min_days and not self._is_in_bridge_window(start, end, today):
                    continue

                holiday_name = self._resolve_holiday_period_name(y, start, end, m)
                holiday_days = (end - start).days + 1
                before_plan = self._build_bridge_plan(start, end, "before", today)
                after_plan = self._build_bridge_plan(start, end, "after", today)

                rows = []
                if before_plan:
                    rows.append({
                        "label": "向前拼",
                        "range": before_plan["leave_range"],
                        "start": before_plan["leave_start"],
                        "end": before_plan["leave_end"],
                        "days": before_plan["leave_days"],
                        "total_days": before_plan["total_days"],
                        "calendar_days": before_plan["calendar_days"],
                    })
                if after_plan:
                    rows.append({
                        "label": "向后拼",
                        "range": after_plan["leave_range"],
                        "start": after_plan["leave_start"],
                        "end": after_plan["leave_end"],
                        "days": after_plan["leave_days"],
                        "total_days": after_plan["total_days"],
                        "calendar_days": after_plan["calendar_days"],
                    })
                detail = {
                    "name": holiday_name,
                    "range": f"{start.month}/{start.day} - {end.month}/{end.day}",
                    "start": start.strftime("%Y-%m-%d"),
                    "end": end.strftime("%Y-%m-%d"),
                    "days": holiday_days,
                    "title": f"{holiday_name}（{start.month}/{start.day} - {end.month}/{end.day}）",
                    "rows": rows,
                }
                _LOGGER.debug("nearest_holiday_detail: %s", detail)
                return detail
        return {}

    def _is_in_bridge_window(
        self,
        holiday_start: datetime_class,
        holiday_end: datetime_class,
        today: datetime_class,
    ) -> bool:
        """判断今天是否已进入节前/节后拼假可展示窗口。"""
        before_start = self._bridge_edge_date(holiday_start, "before")
        after_end = self._bridge_edge_date(holiday_end, "after")
        if before_start and before_start <= today <= holiday_end:
            return True
        if after_end and holiday_start <= today <= after_end:
            return True
        return False

    def _bridge_edge_date(self, anchor: datetime_class, direction: str) -> datetime_class | None:
        """获取节前/节后拼假展示窗口的最外层边界日期。"""
        step = -1 if direction == "before" else 1
        cursor = anchor - timedelta(days=1) if direction == "before" else anchor + timedelta(days=1)

        saw_workday = False
        while self.is_holiday_status(cursor) == 0:
            saw_workday = True
            cursor += timedelta(days=step)

        if not saw_workday:
            return None

        edge = cursor - timedelta(days=step)
        while self.is_holiday_status(cursor) != 0:
            edge = cursor
            cursor += timedelta(days=step)

        return edge

    def _resolve_holiday_period_name(
        self,
        year: str,
        holiday_start: datetime_class,
        holiday_end: datetime_class,
        fallback_mmdd: str,
    ) -> str:
        """从整段假期中找最合适的节日名，避免返回“5月2日”这类泛名称。"""
        current = holiday_start
        while current <= holiday_end:
            mmdd = current.strftime("%m%d")
            name = self._resolve_holiday_name(year, mmdd)
            if not re.fullmatch(r"\d+月\d+日", name):
                return name
            current += timedelta(days=1)
        return self._resolve_holiday_name(year, fallback_mmdd)

    def _build_bridge_plan(
        self,
        holiday_start: datetime_class,
        holiday_end: datetime_class,
        direction: str,
        today: datetime_class,
    ) -> dict:
        """构建节前/节后拼假方案，补上紧邻的休息日和调休工作日。"""
        step = -1 if direction == "before" else 1
        cursor = holiday_start - timedelta(days=1) if direction == "before" else holiday_end + timedelta(days=1)

        leave_dates = []
        while self.is_holiday_status(cursor) == 0:
            leave_dates.append(cursor)
            cursor += timedelta(days=step)

        if not leave_dates:
            return {}

        extra_rest_dates = []
        while self.is_holiday_status(cursor) != 0:
            extra_rest_dates.append(cursor)
            cursor += timedelta(days=step)

        if direction == "before":
            leave_dates.reverse()
            extra_rest_dates.reverse()
            calendar_dates = extra_rest_dates + leave_dates
        else:
            calendar_dates = leave_dates + extra_rest_dates

        clip_anchor = today.replace(hour=0, minute=0, second=0, microsecond=0)
        if direction == "before" and calendar_dates and holiday_start <= clip_anchor <= holiday_end:
            calendar_dates = []
            leave_dates = []
            extra_rest_dates = []
        elif direction == "before" and calendar_dates and calendar_dates[0] <= clip_anchor <= holiday_end:
            calendar_dates = [d for d in calendar_dates if d >= clip_anchor]
            leave_dates = [d for d in leave_dates if d >= clip_anchor]
            extra_rest_dates = [d for d in extra_rest_dates if d >= clip_anchor]
        elif direction == "after" and calendar_dates and holiday_start <= clip_anchor <= calendar_dates[-1]:
            calendar_dates = [d for d in calendar_dates if d >= clip_anchor]
            leave_dates = [d for d in leave_dates if d >= clip_anchor]
            extra_rest_dates = [d for d in extra_rest_dates if d >= clip_anchor]

        if not calendar_dates:
            return {}

        calendar_days = []
        leave_set = {d.strftime("%Y-%m-%d") for d in leave_dates}
        rest_set = {d.strftime("%Y-%m-%d") for d in extra_rest_dates}
        for date in calendar_dates:
            key = date.strftime("%Y-%m-%d")
            if key in leave_set:
                tag = "请假"
                day_type = "leave"
            elif key in rest_set:
                tag = "休息"
                day_type = "rest"
            else:
                tag = "上班"
                day_type = "work"
            calendar_days.append({
                "key": key,
                "label": f"{date.month}/{date.day}",
                "tag": tag,
                "type": day_type,
            })

        leave_range = self._format_date_range(leave_dates)
        total_days = len(calendar_days) + (holiday_end - holiday_start).days + 1

        return {
            "leave_range": leave_range,
            "leave_start": leave_dates[0].strftime("%Y-%m-%d") if leave_dates else "",
            "leave_end": leave_dates[-1].strftime("%Y-%m-%d") if leave_dates else "",
            "leave_days": len(leave_dates),
            "total_days": total_days,
            "calendar_days": calendar_days,
        }

    def nearest_holiday_info(self, min_days: int = 30, max_days: int = 45) -> str:
        """返回最近一次法定节假日的放假安排说明。"""
        detail = self.nearest_holiday_detail(min_days, max_days)
        if not detail:
            return ""

        lines = [detail["title"]]
        for row in detail.get("rows", []):
            lines.append(
                f"{row['label']}：{row['range']}（{row['days']}天）👉 连休 {row['total_days']} 天"
            )
        info = "\n".join(lines)
        _LOGGER.debug("nearest_holiday_info: %s", info)
        return info

    def _format_range(self, days: list[dict]) -> str:
        """将日期列表格式化为 M/D - M/D。"""
        if not days:
            return ""
        start = days[0]["date"]
        end = days[-1]["date"]
        return f"{start.month}/{start.day} - {end.month}/{end.day}"

    def _format_date_range(self, dates: list[datetime_class]) -> str:
        """将 datetime 列表格式化为 M/D - M/D。"""
        if not dates:
            return ""
        start = dates[0]
        end = dates[-1]
        return f"{start.month}/{start.day} - {end.month}/{end.day}"

    # ------------------------------------------------------------------
    # getHoliday：兼容旧接口，返回 {date: 节日名} 字典
    # ------------------------------------------------------------------

    def getHoliday(self, days: int = 1) -> dict:
        """返回 {datetime.date: 节日名称} 字典（用于寻找最近节日）。"""
        self.get_holidays_from_server()
        results = {}
        for y, dates in self._holiday_json.items():
            if y == "update_time":
                continue
            for m, t in dates.items():
                if int(t) == 2:
                    d_str = "{}-{}-{}".format(y, m[0:2], m[2:])
                    try:
                        d = datetime_class.strptime(d_str, "%Y-%m-%d").date()
                        # 节日名称从 lunar 模块推断，这里简单用日期字符串
                        results[d] = self._resolve_holiday_name(y, m)
                    except Exception:
                        pass
        return results

    def _resolve_holiday_name(self, year: str, mmdd: str) -> str:
        """根据年份和 MMDD 推断节日名称（使用内置节日映射）。"""
        _HOLIDAY_NAMES = {
            "0101": "元旦",
            "0214": "情人节",
            "0308": "妇女节",
            "0401": "愚人节",
            "0501": "劳动节",
            "0601": "儿童节",
            "0701": "建党节",
            "0801": "建军节",
            "0910": "教师节",
            "1001": "国庆节",
            "1002": "国庆节",
            "1003": "国庆节",
            "1004": "国庆节",
            "1005": "国庆节",
            "1006": "国庆节",
            "1007": "国庆节",
            "1231": "元旦前夕",
        }
        if mmdd in _HOLIDAY_NAMES:
            return _HOLIDAY_NAMES[mmdd]

        month = int(mmdd[:2])
        day = int(mmdd[2:])
        year_int = int(year)

        # 兼容旧逻辑：未命中固定映射时，再按公历节日/农历节日/节气动态解析。
        names = []

        solar_name = lunar.Festival.solar_Fstv(month, day)
        if solar_name:
            names.extend([name.strip() for name in solar_name.split(",") if name.strip()])

        try:
            lunar_date = lunar.LunarDate.fromSolarDate(year_int, month, day)
            lunar_name = lunar.Festival.lunar_Fstv(lunar_date.month, lunar_date.day)
            if lunar_name:
                names.extend([name.strip() for name in lunar_name.split(",") if name.strip()])
        except Exception as err:
            _LOGGER.debug("resolve lunar holiday name failed for %s-%s: %s", year, mmdd, err)

        try:
            for item in lunar.jieqi().creat_year_jieqi(year_int):
                comps = item["time"].split("-")
                if item["name"] == "清明" and int(comps[1]) == month and int(comps[2]) == day:
                    names.append("清明节")
                    break
        except Exception as err:
            _LOGGER.debug("resolve term holiday name failed for %s-%s: %s", year, mmdd, err)

        seen = set()
        ordered = []
        for name in names:
            if name not in seen:
                seen.add(name)
                ordered.append(name)

        if ordered:
            preferred = next((name for name in ordered if "节" in name), ordered[0])
            if preferred == "元旦节":
                return "元旦"
            if preferred == "国际儿童节":
                return "儿童节"
            return preferred

        return f"{month}月{day}日"


def main():
    pass


if __name__ == "__main__":
    main()
