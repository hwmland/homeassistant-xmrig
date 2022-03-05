"""XMRIG sensor platform."""

from collections.abc import Awaitable, Iterable, Mapping
import logging
from typing import Any, Dict, List, Optional

from voluptuous.validators import Switch

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_NAME, STATE_UNKNOWN

# from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import StateType

from .const import DATA_CONTROLLER, DOMAIN
from .helpers import DefaultTo

from .summary_controller import SummaryController


_LOGGER = logging.getLogger(__name__)

SETUP_FACTORY = "factory"
SETUP_ICON = "icon"
SETUP_NAME = "name"
SETUP_UNIT = "unit"
SETUP_KEY = "key"
SETUP_DATA = "data"

_SENSORS: Dict[str, Dict[str, Any]] = {
    "hashrate10s": {
        SETUP_NAME: "Hashrate 10s",
        SETUP_FACTORY: lambda: XmrigSensorHashrate,
        SETUP_DATA: 0,
        SETUP_UNIT: "H/s",
        SETUP_ICON: "mdi:gauge",
    },
    "hashrate1m": {
        SETUP_NAME: "Hashrate 1m",
        SETUP_FACTORY: lambda: XmrigSensorHashrate,
        SETUP_DATA: 1,
        SETUP_UNIT: "H/s",
        SETUP_ICON: "mdi:gauge",
    },
    "hashrate15m": {
        SETUP_NAME: "Hashrate 15m",
        SETUP_FACTORY: lambda: XmrigSensorHashrate,
        SETUP_DATA: 2,
        SETUP_UNIT: "H/s",
        SETUP_ICON: "mdi:gauge",
    },
    "difficulty": {
        SETUP_NAME: "Difficulty",
        SETUP_FACTORY: lambda: XmrigSensorSimple,
        SETUP_DATA: ["results", "diff_current"],
        SETUP_UNIT: "dif",
        SETUP_ICON: "mdi:gauge",
    },
    "shares_good": {
        SETUP_NAME: "Shares good",
        SETUP_FACTORY: lambda: XmrigSensorSimple,
        SETUP_DATA: ["results", "shares_good"],
        SETUP_UNIT: "cnt",
        SETUP_ICON: "mdi:counter",
    },
    "shares_total": {
        SETUP_NAME: "Shares total",
        SETUP_FACTORY: lambda: XmrigSensorSimple,
        SETUP_DATA: ["results", "shares_total"],
        SETUP_UNIT: "cnt",
        SETUP_ICON: "mdi:counter",
    },
    "connection": {
        SETUP_NAME: "Pool",
        SETUP_FACTORY: lambda: XmrigSensorSimple,
        SETUP_DATA: ["connection", "pool"],
        SETUP_ICON: "mdi:cable",
    },
    "algo": {
        SETUP_NAME: "Algo",
        SETUP_FACTORY: lambda: XmrigSensorSimple,
        SETUP_DATA: ["algo"],
        SETUP_ICON: "mdi:application-braces-outline",
    },
}


async def async_setup_entry(
    hass: HomeAssistant, configEntry: config_entries.ConfigEntry, async_add_entities
):
    """Set up XMRIG sensor."""
    _LOGGER.debug(
        "async_setup_entry({0}), state: {1}".format(
            configEntry.data[CONF_NAME], configEntry.state
        )
    )

    instanceName: str = configEntry.data[CONF_NAME]
    controller: SummaryController = hass.data[DOMAIN][DATA_CONTROLLER][
        configEntry.entry_id
    ]
    sensors = {}

    @callback
    def controllerUpdatedCallback():
        """Update the values of the controller."""
        UpdateItems(instanceName, controller, async_add_entities, sensors)

    controller.listeners.append(
        async_dispatcher_connect(
            hass, controller.UpdateSignal, controllerUpdatedCallback
        )
    )


@callback
def UpdateItems(
    instanceName: str,
    controller: SummaryController,
    async_add_entities,
    sensors: Dict[str, Any],
) -> None:
    """Update sensor state"""
    _LOGGER.debug("UpdateItems({})".format(instanceName))
    sensorsToAdd: Dict[str, Any] = []

    for sensor in _SENSORS:
        sensorId = "{}-{}".format(instanceName, sensor)
        if sensorId in sensors:
            if sensors[sensorId].enabled:
                sensors[sensorId].async_schedule_update_ha_state()
        else:
            sensorDefinition = _SENSORS[sensor]
            sensorFactory = sensorDefinition[SETUP_FACTORY]()
            sensorInstance = sensorFactory(
                instanceName, sensor, controller, sensorDefinition
            )
            sensors[sensorId] = sensorInstance
            sensorsToAdd.append(sensorInstance)
    if sensorsToAdd:
        async_add_entities(sensorsToAdd, True)


################################################
class XmrigSensor(SensorEntity):
    """Define XMRIG sensor"""

    def __init__(
        self,
        instanceName: str,
        sensorName: str,
        controller: SummaryController,
        sensorDefinition: Dict[str, Any],
    ) -> None:
        """Initialize"""
        self._instanceName = instanceName
        self._sensorName = sensorName
        self._controller = controller
        self._name = "{} {}".format(
            self._instanceName,
            DefaultTo(sensorDefinition.get(SETUP_NAME), self._sensorName),
        )
        self._icon = sensorDefinition.get(SETUP_ICON)
        self._unit = sensorDefinition.get(SETUP_UNIT)
        self._sensorDefinition = sensorDefinition
        self._privateInit()

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._controller.entity_id + self._sensorName

    @property
    def name(self) -> str:
        """Return name"""
        return self._name

    @property
    def state(self) -> StateType:
        """Return the state."""
        if self._controller.InError:
            return STATE_UNKNOWN
        else:
            return self._stateInternal

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement of this entity, if any."""
        return self._unit

    @property
    def icon(self) -> str:
        """Return the icon."""
        return self._icon

    async def async_update(self):
        """Synchronize state with controller."""
        _LOGGER.debug("async_update")

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        _LOGGER.debug("async_added_to_hass({})".format(self.name))

    ### Overrides
    @property
    def _stateInternal(self) -> StateType:
        """Return the internal state."""
        return "OK"

    def _privateInit(self) -> None:
        """Private instance intialization"""
        pass

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return a description for device registry."""
        info = {
            "name": self._instanceName + " xmrig",
            "identifiers": {
                (
                    DOMAIN,
                    self._instanceName,
                )
            },
            "sw_version": self._controller.GetData(["version"]),
            "manufacturer": self._controller.GetData(["cpu", "brand"]),
            "model": "{}-{}".format(
                self._controller.GetData(["cpu", "arch"]),
                self._controller.GetData(["cpu", "assembly"]),
            ),
            # "entry_type": "service",
        }

        return info


################################################
class XmrigSensorHashrate(XmrigSensor):
    @property
    def _stateInternal(self) -> StateType:
        """Return the internal state."""
        hashrates: List[float] = self._controller.GetData(["hashrate", "total"])
        return hashrates[self._index]

    def _privateInit(self) -> None:
        """Private instance intialization"""
        self._index: int = self._sensorDefinition[SETUP_DATA]


################################################
class XmrigSensorSimple(XmrigSensor):
    @property
    def _stateInternal(self) -> StateType:
        """Return the internal state."""
        return self._controller.GetData(self._path)

    def _privateInit(self) -> None:
        """Private instance intialization"""
        self._path: List[str] = self._sensorDefinition[SETUP_DATA]
