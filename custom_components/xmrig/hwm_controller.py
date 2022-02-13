"""HWM(land) controller"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta

from typing import Any, Dict, Optional, List

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

from .restapicall import RestApiCall

_LOGGER = logging.getLogger(__name__)


class HwmController:
    """HWM(land) Controller class"""

    def __init__(
        self,
        domain: str,
        controlerId: str,
        hass: HomeAssistant,
        config_entry: config_entries.ConfigEntry,
    ) -> None:
        """Initialize controller"""
        self._lock = asyncio.Lock()
        self._scheduledUpdateCallback = None
        self.listeners = []
        self._domain = domain
        self._controlerId = controlerId
        self._hass = hass
        self._name: str = config_entry.data[CONF_NAME]
        self._id = f"{self._name}-{self._controlerId}"
        self.entity_id = config_entry.entry_id
        # pylint: disable=assignment-from-none
        resource = self._vGetResource(config_entry)
        headers = self._vGetHeaders(config_entry)
        self._rest = RestApiCall(
            self._hass,
            "GET",
            resource,
            auth=None,
            headers=headers,
            params=None,
            data=None,
            verify_ssl=True,
        )
        self._data: Dict[str, Any] = None

    def _vGetResource(self, config_entry: config_entries.ConfigEntry) -> str:
        """Get RestApiCall resource"""
        return None

    def _vGetHeaders(self, config_entry: config_entries.ConfigEntry) -> any:  # @type
        """Get RestApiCall headers"""
        return None

    async def async_initialize(self) -> None:
        """Async initialization"""
        await self.async_ScheduledUpdate()
        self._scheduledUpdateCallback = async_track_time_interval(
            self._hass, self.async_ScheduledUpdate, timedelta(seconds=30)
        )

    async def async_reset(self) -> bool:
        """Reset dispatchers"""
        for unsub_dispatcher in self.listeners:
            unsub_dispatcher()

        self.listeners = []
        self._scheduledUpdateCallback()  # remove it now
        return True

    @callback
    async def async_ScheduledUpdate(self, _now=None):
        """Trigger update by timer"""
        await self.async_Update()

    async def async_Update(self):
        """Update data"""
        _LOGGER.debug("async_Update({})".format(self._id))
        try:
            await asyncio.wait_for(self._lock.acquire(), timeout=10)
        except:
            _LOGGER.warning("async_Update({} lock failed)".format(self._id))
            return
        try:  # Lock region start
            await self._rest.async_update()

            if self._rest.data is None:
                _LOGGER.info("async_Update({}) - no data received".format(self._id))
                self._data = None
            else:
                data = json.loads(self._rest.data)
                self._data = data
            async_dispatcher_send(self._hass, self.UpdateSignal)
        finally:  # Lock region end
            self._lock.release()

    @property
    def UpdateSignal(self) -> str:
        """New data event"""
        return "{}-update-{}".format(self._domain, self._id)

    @property
    def InError(self) -> bool:
        """Is controller in error (no data)?"""
        return self._data == None

    def GetData(self, path: List[str]) -> any:
        """Get data block corresponding to path"""
        current = self._data
        for key in path:
            if current is None:
                return None
            current = current.get(key)
        return current
