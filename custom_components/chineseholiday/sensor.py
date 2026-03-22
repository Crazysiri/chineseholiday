# coding=utf-8
"""中国节假日传感器 - 版本 0.3.0"""
from __future__ import annotations

import asyncio
import datetime
from datetime import timedelta
import logging
import threading
from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import event as evt
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import Throttle

from .const import DEFAULT_NAME, DOMAIN
from . import holiday
from . import lunar

_LOGGER = logging.getLogger(__name__)

CONF_UPDATE_INTERVAL = "update_interval"
CONF_SOLAR_ANNIVERSARY = "solar_anniversary"
CONF_LUNAR_ANNIVERSARY = "lunar_anniversary"
CONF_CALCULATE_AGE = "calculate_age"
CONF_CALCULATE_AGE_DATE = "date"
CONF_CALCULATE_AGE_NAME = "name"
CONF_NOTIFY_SCRIPT_NAME = "notify_script_name"
CONF_NOTIFY_TIMES = "notify_times"
CONF_NOTIFY_PRINCIPLES = "notify_principles"
CONF_NOTIFY_PRINCIPLES_DATE = "date"
CONF_NOTIFY_PRINCIPLES_NAME = "name"
CONF_NOTIFY_PRINCIPLES_SOLAR = "solar"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NOTIFY_TIMES, default=["09:00:00"]): [cv.time],
        vol.Optional(CONF_NOTIFY_SCRIPT_NAME, default=""): cv.string,
        vol.Optional("show_detail", default=True): cv.boolean,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_SOLAR_ANNIVERSARY, default={}): {str: [str]},
        vol.Optional(CONF_LUNAR_ANNIVERSARY, default={}): {str: [str]},
        vol.Optional(CONF_CALCULATE_AGE, default=[]): [
            {
                vol.Optional(CONF_CALCULATE_AGE_DATE): cv.string,
                vol.Optional(CONF_CALCULATE_AGE_NAME): cv.string,
            }
        ],
        vol.Optional(CONF_NOTIFY_PRINCIPLES, default={}): {
            str: [
                {
                    vol.Optional(CONF_NOTIFY_PRINCIPLES_NAME, default=""): cv.string,
                    vol.Optional(CONF_NOTIFY_PRINCIPLES_DATE, default=""): cv.string,
                    vol.Optional(CONF_NOTIFY_PRINCIPLES_SOLAR, default=True): cv.boolean,
                }
            ]
        },
        vol.Optional(
            CONF_UPDATE_INTERVAL, default=timedelta(hours=8)
        ): (vol.All(cv.time_period, cv.positive_timedelta)),
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
) -> None:
    """YAML 方式配置（向后兼容）。"""
    name = config[CONF_NAME]
    interval = config.get(CONF_UPDATE_INTERVAL, timedelta(hours=8))
    sensor = ChineseHolidaySensor(
        hass,
        name,
        config.get(CONF_NOTIFY_TIMES, [datetime.time(9, 0, 0)]),
        config.get(CONF_NOTIFY_SCRIPT_NAME, ""),
        interval,
        config.get("show_detail", True),
        config.get(CONF_SOLAR_ANNIVERSARY, {}),
        config.get(CONF_LUNAR_ANNIVERSARY, {}),
        config.get(CONF_CALCULATE_AGE, []),
        config.get(CONF_NOTIFY_PRINCIPLES, {}),
    )
    async_add_entities([sensor], True)


def _parse_notify_times(times_str: str) -> list[datetime.time]:
    """将逗号分隔的时间字符串解析为 datetime.time 列表。"""
    result = []
    for t in times_str.split(","):
        t = t.strip()
        if not t:
            continue
        try:
            result.append(datetime.time.fromisoformat(t))
        except ValueError:
            _LOGGER.warning("notify_times 格式错误，跳过：%s", t)
    return result or [datetime.time(9, 0, 0)]


def _entry_get(entry: ConfigEntry, key: str, default):
    """从 options 优先，再从 data 取值。"""
    return entry.options.get(key, entry.data.get(key, default))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Config entry 方式配置（UI 添加）。"""
    notify_times = _parse_notify_times(
        _entry_get(entry, "notify_times", "09:00:00")
    )
    sensor = ChineseHolidaySensor(
        hass,
        _entry_get(entry, "name", DEFAULT_NAME),
        notify_times,
        _entry_get(entry, "notify_script_name", ""),
        timedelta(hours=8),
        _entry_get(entry, "show_detail", True),
        _entry_get(entry, "solar_anniversary", {}),
        _entry_get(entry, "lunar_anniversary", {}),
        _entry_get(entry, "calculate_age", []),
        _entry_get(entry, "notify_principles", {}),
        unique_id=f"{DOMAIN}_sensor",
        entity_id=f"sensor.{DEFAULT_NAME}",
    )
    async_add_entities([sensor], True)


class ChineseHolidaySensor(SensorEntity):
    """中国节假日传感器实体。

    state 输出：工作日 / 休息日 / 节假日
    通过 native_value 提供状态（HA 2024+ SensorEntity 要求）
    """

    _attr_icon = "mdi:calendar-today"
    # 非数值型 sensor 不设 device_class / unit_of_measurement

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        notify_times: list,
        script_name: str,
        interval: timedelta,
        show_detail: bool,
        solar_anniversary: dict,
        lunar_anniversary: dict,
        calculate_age: list,
        notify_principles: dict,
        unique_id: str | None = None,
        entity_id: str | None = None,
    ) -> None:
        self.client_name = name
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._show_detail = show_detail
        self._hass = hass
        self._script_name = script_name
        self._notify_times = notify_times
        # 不在 __init__（事件循环）里做任何 I/O
        # Holiday() 和 CalendarToday() 在 _update()（executor 线程）里懒加载
        self._holiday: holiday.Holiday | None = None
        self._lunar: lunar.CalendarToday | None = None
        self.attributes: dict[str, Any] = {}
        self.localizedAttributes: dict[str, Any] = {}
        self._solar_anniversary = solar_anniversary
        self._lunar_anniversary = lunar_anniversary
        self._calculate_age = calculate_age
        self._notify_principles = notify_principles
        self.entity_id = entity_id or generate_entity_id(
            "sensor.{}", self.client_name, hass=self._hass
        )
        # Throttle 仍然可用（HA dev 分支确认）
        self.update = Throttle(interval)(self._update)
        self._setup_update_listener()
        self._setup_notify_listener()

    @property
    def name(self) -> str:
        return self._attr_name

    @property
    def native_value(self) -> str | None:
        """HA 2024+ SensorEntity 通过 native_value 暴露状态。

        SensorEntity.state 是 @final，子类不能覆盖，必须用 native_value。
        """
        return self._attr_native_value  # type: ignore[return-value]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.localizedAttributes

    # ------------------------------------------------------------------
    # 定时器：每天凌晨 00:00:15 强制更新
    # ------------------------------------------------------------------

    def _setup_update_listener(self) -> None:
        @callback
        def _listener(_):
            self._setup_update_listener()
            self._hass.async_add_executor_job(self._update)

        now = datetime.datetime.utcnow() + timedelta(hours=8)
        next_midnight = (
            datetime.datetime.strptime(now.strftime("%Y-%m-%d"), "%Y-%m-%d")
            + timedelta(days=1, seconds=15)
        )
        evt.async_track_point_in_time(self._hass, _listener, next_midnight)

    # ------------------------------------------------------------------
    # 定时器：按配置时间触发通知脚本
    # ------------------------------------------------------------------

    def _setup_notify_listener(self) -> None:
        @callback
        def _listener(_):
            self._setup_notify_listener()
            # notify() 包含阻塞操作，放入线程执行
            threading.Thread(target=self.notify, daemon=True).start()

        now = datetime.datetime.utcnow() + timedelta(hours=8)
        notify_dates = []
        for t in self._notify_times:
            dt_str = now.strftime("%Y-%m-%d") + " " + str(t)
            notify_dates.append(
                datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            )

        notify_d = next((d for d in notify_dates if d > now), None)
        if not notify_d:
            notify_d = notify_dates[0] + timedelta(days=1)

        evt.async_track_point_in_time(self._hass, _listener, notify_d)

    # ------------------------------------------------------------------
    # 通知脚本
    # ------------------------------------------------------------------

    def notify(self) -> None:
        """调用 HA 脚本发送节日提醒（在线程中运行）。"""

        def _call_script(message: str) -> None:
            # 从非 async 线程调用 HA 服务需要用 run_coroutine_threadsafe
            asyncio.run_coroutine_threadsafe(
                self._hass.services.async_call(
                    "script", self._script_name, {"message": message}
                ),
                self._hass.loop,
            ).result(timeout=10)

        if not self._script_name or not self._notify_principles:
            return
        if self._lunar is None:
            _LOGGER.warning("notify: _lunar 尚未初始化，跳过本次通知")
            return

        dates = self._dates_need_to_notify()
        messages = []
        for item in dates:
            days = item["day"]
            fes_list = item["list"]
            if days == 0:
                messages.append("今天是 " + ",".join(fes_list))
            else:
                messages.append(
                    "距离 " + ",".join(fes_list) + "还有" + str(days) + "天"
                )
        if messages:
            try:
                _call_script(",".join(messages))
            except Exception as e:
                _LOGGER.error("notify: 调用脚本失败: %s", e)

    def _dates_need_to_notify(self) -> list[dict]:
        dates = []
        for key, value in self._notify_principles.items():
            days_keys = key.split("|")
            for item in value:
                date = item.get("date", "")
                solar = item.get("solar", True)
                name = item.get("name", "")
                fes_date = None
                fes_list: list[str] = []

                if name:
                    try:
                        fes_list = [name]
                        date_str = (
                            str(self._lunar.solar()[0])
                            + lunar.Festival._weekday_festival_reserse[name]
                        )
                        fes_date = datetime.datetime.strptime(
                            date_str, "%Y%m%d"
                        ).date()
                    except Exception:
                        pass
                elif date:
                    if solar:
                        date_str = str(self._lunar.solar()[0]) + date
                        fes_date = datetime.datetime.strptime(
                            date_str, "%Y%m%d"
                        ).date()
                        fes_list = list(
                            lunar.Festival._solar_festival.get(date, [])
                        )
                        fes_list += self._solar_anniversary.get(date, [])
                    else:
                        month, day = int(date[:2]), int(date[2:])
                        fes_date = lunar.CalendarToday.lunar_to_solar(
                            self._lunar.solar()[0], month, day
                        )
                        fes_list = list(
                            lunar.Festival._lunar_festival.get(date, [])
                        )
                        fes_list += self._lunar_anniversary.get(date, [])

                if fes_date and fes_list:
                    today = datetime.date.today()
                    diff = (fes_date - today).days
                    if str(diff) in days_keys:
                        dates.append({**item, "day": diff, "list": fes_list})
        return dates

    # ------------------------------------------------------------------
    # 纪念日计算
    # ------------------------------------------------------------------

    def _anniversary_label(self, names: list[str], age: int) -> str:
        if age == -1:
            return ",".join(names)
        return ",".join(
            f"{n}({age}岁)" if "生日" in n else f"{n}({age}周年)" for n in names
        )

    def calculate_anniversary(self, count: int = 1) -> list[tuple]:
        anniversaries: dict[str, list] = {}

        for key, value in self._lunar_anniversary.items():
            if len(key) == 8:
                year, month, day = int(key[:4]), int(key[4:6]), int(key[6:])
                age = lunar.CalendarToday.get_age_by_birth_lunar_to_solar(
                    year, month, day
                ) + 1
            else:
                month, day = int(key[:2]), int(key[2:])
                age = -1
            y = self._lunar.lunar()[0]
            if month < self._lunar.lunar()[1]:
                y += 1
            elif month == self._lunar.lunar()[1] and day < self._lunar.lunar()[2]:
                y += 1
            solar_date = lunar.CalendarToday.lunar_to_solar(y, month, day)
            date_str = solar_date.strftime("%Y%m%d")
            self._lunar = lunar.CalendarToday()
            anniversaries.setdefault(date_str, []).append(
                {"anniversary": self._anniversary_label(value, age), "solar": False}
            )

        for key, value in self._solar_anniversary.items():
            if len(key) == 8:
                year, month, day = int(key[:4]), int(key[4:6]), int(key[6:])
                key = key[4:]
                age = lunar.CalendarToday.get_age_by_birth_solar(year, month, day) + 1
            else:
                age = -1
            date_str = str(self._lunar.solar()[0]) + key
            anniversaries.setdefault(date_str, []).append(
                {"anniversary": self._anniversary_label(value, age), "solar": True}
            )

        today = datetime.date.today()
        results = []
        for key, annis in sorted(anniversaries.items()):
            last_update = datetime.datetime.strptime(key, "%Y%m%d").date()
            diff = (last_update - today).days
            if diff > 0 and len(results) < count:
                results.append((key, diff, annis))
        return results

    def custom_anniversary(self) -> str:
        l_month = self._lunar.lunar()[1]
        l_day = self._lunar.lunar()[2]
        s_month = self._lunar.solar()[1]
        s_day = self._lunar.solar()[2]
        l = lunar.festival_handle(self._lunar_anniversary, l_month, l_day) or ""
        s = lunar.festival_handle(self._solar_anniversary, s_month, s_day) or ""
        return l + s

    def calculate_age(self) -> None:
        if not self._calculate_age:
            return
        now_day = datetime.datetime.now()
        past_dates = []
        future_dates = []
        past_count = 0
        future_count = 0

        for item in self._calculate_age:
            date = item[CONF_CALCULATE_AGE_DATE]
            name = item[CONF_CALCULATE_AGE_NAME]
            key = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")

            if (now_day - key).total_seconds() > 0:
                ts = int((now_day - key).total_seconds())
                y, r = divmod(ts, 86400 * 365)
                d, r = divmod(r, 86400)
                h, r = divmod(r, 3600)
                m, s = divmod(r, 60)
                desc = f"{y}年{d}天{h}小时{m}分钟{s}秒"
                self.localizedAttributes[f"{past_count+1}.过去纪念日"] = name
                self.localizedAttributes[f"{past_count+1}.过去纪念日日期"] = date
                self.localizedAttributes[f"{past_count+1}.已经过去"] = desc
                past_dates.append({"name": name, "date": date, "interval": ts, "description": desc})
                past_count += 1

                counter = 0
                while (now_day - key).total_seconds() > 0:
                    date = str(key.year + 1) + date[4:]
                    key = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
                    counter += 1
                name = name + " " + str(counter) + ("周岁" if "生日" in name else "周年")

            if (now_day - key).total_seconds() < 0:
                ts = int((key - now_day).total_seconds())
                y, r = divmod(ts, 86400 * 365)
                d, r = divmod(r, 86400)
                h, r = divmod(r, 3600)
                m, s = divmod(r, 60)
                desc = f"{y}年{d}天{h}小时{m}分钟{s}秒"
                self.localizedAttributes[f"{future_count+1}.未来纪念日"] = name
                self.localizedAttributes[f"{future_count+1}.未来纪念日日期"] = date
                self.localizedAttributes[f"{future_count+1}.还有"] = desc
                future_dates.append({"name": name, "date": date, "interval": ts, "description": desc})
                future_count += 1

        self.attributes["past_dates"] = past_dates
        self.attributes["future_dates"] = future_dates

    def nearest_holiday(self) -> dict:
        now_day = datetime.date.today()
        results = self._holiday.getHoliday()
        count_dict = {k: (k - now_day).days for k in results if (k - now_day).days > 0}
        if not count_dict:
            return {}
        nearest = min(count_dict)
        return {
            "name": results[nearest],
            "date": nearest.isoformat(),
            "day": str((nearest - now_day).days),
        }

    # ------------------------------------------------------------------
    # 主更新方法（在 executor 线程中运行）
    # ------------------------------------------------------------------

    def _update(self) -> None:
        """在 executor 线程中运行，允许阻塞 I/O。"""
        _LOGGER.info("chineseholiday: updating...")
        self.attributes = {}
        self.localizedAttributes = {}
        # 懒加载：第一次 update 时初始化（此时已在 executor 线程，可以做阻塞 I/O）
        if self._holiday is None:
            self._holiday = holiday.Holiday()
        if self._lunar is None:
            self._lunar = lunar.CalendarToday()
        else:
            self._lunar = lunar.CalendarToday()  # 每次更新重新计算当日

        # HA 2024+ SensorEntity：必须写 _attr_native_value，不能覆盖 state 属性
        self._attr_native_value = self._holiday.is_holiday_today()

        self.attributes["tomorrow_state"] = self._holiday.is_holiday_tomorrow()
        self.localizedAttributes["明天"] = self._holiday.is_holiday_tomorrow()

        self.attributes["solar"] = self._lunar.solar_date_description()
        self.localizedAttributes["今天"] = self._lunar.solar_date_description()
        self.attributes["week"] = self._lunar.week_description()
        self.localizedAttributes["星期"] = self._lunar.week_description()
        self.attributes["lunar"] = self._lunar.lunar_date_description()
        self.localizedAttributes["农历"] = self._lunar.lunar_date_description()
        self.attributes["week_number"] = self._lunar.solar_week_number()
        self.localizedAttributes["周数"] = self._lunar.solar_week_number_description()

        term = self._lunar.solar_Term()
        if term:
            self.attributes["term"] = term
            self.localizedAttributes["节气"] = term

        festival = self._lunar.festival_description()
        if festival:
            self.attributes["festival"] = festival
            self.localizedAttributes["节日"] = festival

        custom = self.custom_anniversary()
        if custom:
            self.attributes["anniversary"] = custom
            self.localizedAttributes["纪念日"] = custom

        results = self.calculate_anniversary(5)
        self.attributes["next_anniversaries"] = []
        self.localizedAttributes["接下来的纪念日"] = []

        for i, (key, days, annis) in enumerate(results):
            s = "".join(a["anniversary"] for a in annis)
            if i == 0:
                self.attributes["nearest_anniversary"] = s
                self.localizedAttributes["最近的纪念日"] = s
                self.attributes["nearest_anniversary_date"] = key
                self.localizedAttributes["最近的纪念日日期"] = key
                self.attributes["nearest_anniversary_days"] = days
                self.localizedAttributes["最近的纪念日还有"] = f"{days}天"
            else:
                self.attributes["next_anniversaries"].append(
                    {"date": key, "name": s, "days": days}
                )
                self.localizedAttributes["接下来的纪念日"].append(
                    f"距离纪念日 {s}-{key} 还有 {days} 天 "
                )

        nearest = self.nearest_holiday()
        if nearest:
            self.attributes["nearest_holiday"] = nearest["name"]
            self.localizedAttributes["最近的节日"] = nearest["name"]
            self.attributes["nearest_holiday_date"] = nearest["date"]
            self.localizedAttributes["最近的节日日期"] = nearest["date"]
            self.attributes["nearest_holiday_days"] = int(nearest["day"])
            self.localizedAttributes["最近的节日还有"] = f"{nearest['day']}天"

        self.calculate_age()

        detail = self._holiday.nearest_holiday_detail(12, 45)
        if detail:
            self.attributes["holiday_info_detail"] = detail
            self.localizedAttributes["节假日放假详情结构化"] = detail

        info = self._holiday.nearest_holiday_info(12, 45)
        if info:
            self.attributes["holiday_info"] = info
            self.localizedAttributes["节假日放假详情"] = info

        if self._show_detail:
            self.localizedAttributes["data"] = self.attributes
