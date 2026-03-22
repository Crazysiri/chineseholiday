"""Config flow for Chinese Holiday integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN, DEFAULT_NAME

SINGLETON_UNIQUE_ID = DOMAIN

# ── 工具 ────────────────────────────────────────────────────────────────────

def _opt(key: str, default, entry=None):
    """从 config_entry.options 或 data 中安全取值。"""
    if entry is None:
        return default
    return entry.options.get(key, entry.data.get(key, default))


# ── 步骤一：基本设置 ──────────────────────────────────────────────────────────

def _step_user_schema(defaults: dict | None = None) -> vol.Schema:
    d = defaults or {}
    return vol.Schema(
        {
            vol.Optional("name", default=d.get("name", DEFAULT_NAME)): selector.selector(
                {"text": {}}
            ),
            vol.Optional(
                "notify_script_name", default=d.get("notify_script_name", "")
            ): selector.selector({"text": {}}),
            vol.Optional(
                "notify_times", default=d.get("notify_times", "09:00:00")
            ): selector.selector(
                {
                    "text": {
                        "multiline": False,
                    }
                }
            ),
            vol.Optional(
                "show_detail", default=d.get("show_detail", True)
            ): selector.selector({"boolean": {}}),
        }
    )


# ── 步骤二：纪念日 ────────────────────────────────────────────────────────────

def _step_anniversary_schema(defaults: dict | None = None) -> vol.Schema:
    d = defaults or {}
    return vol.Schema(
        {
            vol.Optional(
                "solar_anniversary", default=d.get("solar_anniversary", {})
            ): selector.selector({"object": {}}),
            vol.Optional(
                "lunar_anniversary", default=d.get("lunar_anniversary", {})
            ): selector.selector({"object": {}}),
            vol.Optional(
                "calculate_age", default=d.get("calculate_age", [])
            ): selector.selector({"object": {}}),
        }
    )


# ── 步骤三：通知规则 ──────────────────────────────────────────────────────────

def _step_notify_schema(defaults: dict | None = None) -> vol.Schema:
    d = defaults or {}
    return vol.Schema(
        {
            vol.Optional(
                "notify_principles", default=d.get("notify_principles", {})
            ): selector.selector({"object": {}}),
        }
    )


# ── Config Flow ───────────────────────────────────────────────────────────────

class ChineseHolidayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """三步式安装向导。"""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict = {}

    async def async_step_user(self, user_input=None):
        """步骤一：基本配置（名称、脚本、通知时间）。"""
        await self.async_set_unique_id(SINGLETON_UNIQUE_ID)
        self._abort_if_unique_id_configured()
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_anniversary()

        return self.async_show_form(
            step_id="user",
            data_schema=_step_user_schema(),
        )

    async def async_step_anniversary(self, user_input=None):
        """步骤二：阳历 / 阴历纪念日 & calculate_age。"""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_notify()

        return self.async_show_form(
            step_id="anniversary",
            data_schema=_step_anniversary_schema(),
        )

    async def async_step_notify(self, user_input=None):
        """步骤三：通知规则（notify_principles）。"""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(
                title=self._data.get("name", DEFAULT_NAME),
                data=self._data,
            )

        return self.async_show_form(
            step_id="notify",
            data_schema=_step_notify_schema(),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ChineseHolidayOptionsFlow()


# ── Options Flow ──────────────────────────────────────────────────────────────

class ChineseHolidayOptionsFlow(config_entries.OptionsFlow):
    """修改已安装集成的配置（三步）。

    HA 2024.8+ 中 config_entry 由框架自动注入为只读属性，
    不能在 __init__ 里赋值。
    """

    def __init__(self) -> None:
        self._updated: dict = {}

    def _merged_entry_data(self) -> dict:
        """Merge edited values back into the original config entry data."""
        return {
            **self.config_entry.data,
            **self.config_entry.options,
            **self._updated,
        }

    async def async_step_init(self, user_input=None):
        """步骤一：基本设置。"""
        entry = self.config_entry
        defaults = {
            "name": _opt("name", DEFAULT_NAME, entry),
            "notify_script_name": _opt("notify_script_name", "", entry),
            "notify_times": _opt("notify_times", "09:00:00", entry),
            "show_detail": _opt("show_detail", True, entry),
        }
        if user_input is not None:
            self._updated.update(user_input)
            return await self.async_step_anniversary()

        return self.async_show_form(
            step_id="init",
            data_schema=_step_user_schema(defaults),
        )

    async def async_step_anniversary(self, user_input=None):
        """步骤二：纪念日设置。"""
        entry = self.config_entry
        defaults = {
            "solar_anniversary": _opt("solar_anniversary", {}, entry),
            "lunar_anniversary": _opt("lunar_anniversary", {}, entry),
            "calculate_age": _opt("calculate_age", [], entry),
        }
        if user_input is not None:
            self._updated.update(user_input)
            return await self.async_step_notify()

        return self.async_show_form(
            step_id="anniversary",
            data_schema=_step_anniversary_schema(defaults),
        )

    async def async_step_notify(self, user_input=None):
        """步骤三：通知规则。"""
        entry = self.config_entry
        defaults = {
            "notify_principles": _opt("notify_principles", {}, entry),
        }
        if user_input is not None:
            self._updated.update(user_input)
            updated_data = self._merged_entry_data()
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=updated_data,
                options={},
                title=updated_data.get("name", DEFAULT_NAME),
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="notify",
            data_schema=_step_notify_schema(defaults),
        )
