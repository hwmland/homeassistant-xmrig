"""XMRIG summary controller"""

import asyncio
import json
import logging
from datetime import datetime, timedelta

from typing import Any, Dict, Optional, List

from homeassistant import config_entries
from homeassistant.components.rest.data import RestData
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN, CONF_ADDRESS, CONF_TOKEN
from .hwm_controller import HwmController

_LOGGER = logging.getLogger(__name__)


class SummaryController(HwmController):
    """XMRIG summary controller class"""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: config_entries.ConfigEntry,
    ) -> None:
        """Initialize controller"""
        self._address: str = config_entry.data[CONF_ADDRESS]
        self._token: str = config_entry.data[CONF_TOKEN]
        super().__init__(DOMAIN, "summary", hass, config_entry)

    def _vGetResource(self, config_entry: config_entries.ConfigEntry) -> str:
        """Get RestData resource"""
        return self._address + "/2/summary"

    def _vGetHeaders(self, config_entry: config_entries.ConfigEntry) -> any:  # @type
        """Get RestData headers"""
        if self._token is None:
            return None
        return {"Authorization": "Bearer " + self._token}
