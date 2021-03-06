"""Config flow to configure XMRIG component."""

import json
import logging
from typing import Any, Callable, Dict, Optional
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback

from .const import (
    CONF_ADDRESS,
    CONF_TOKEN,
    DATA_CONTROLLER,
    DOMAIN,
)
from .restapicall import RestApiCall

_LOGGER = logging.getLogger(__name__)

# ---------------------------
#   configured_instances
# ---------------------------
@callback
def configured_instances(hass, item: str):
    """Return a set of configured instances."""
    return set(entry.data[item] for entry in hass.config_entries.async_entries(DOMAIN))


class ConfigFlowException(Exception):
    """Excepion in config flow occurred."""

    def __init__(self, error: str) -> None:
        self.error = error


AUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_ADDRESS): cv.string,
        vol.Optional(CONF_TOKEN): cv.string,
    }
)


class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    data: Optional[Dict[str, Any]]

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Invoked when a user initiates a flow via the user interface."""
        _LOGGER.debug(f"async_step_user({user_input})")
        errors: Dict[str, str] = {}
        if user_input is not None:
            try:
                _LOGGER.debug("user_input not None")
                if user_input[CONF_NAME] in configured_instances(self.hass, CONF_NAME):
                    raise ConfigFlowException("name_exists")
                if user_input[CONF_ADDRESS] in configured_instances(
                    self.hass, CONF_ADDRESS
                ):
                    raise ConfigFlowException("address_exists")

                resource = user_input[CONF_ADDRESS] + "/2/summary"
                token = user_input[CONF_TOKEN] if CONF_TOKEN in user_input else None
                headers = (
                    None if token is None else {"Authorization": "Bearer " + token}
                )
                rest = RestApiCall(
                    self.hass,
                    "GET",
                    resource,
                    auth=None,
                    headers=headers,
                    params=None,
                    data=None,
                    verify_ssl=True,
                )
                await rest.async_update()
                if rest.status == 403:
                    raise ConfigFlowException("not_authorized")
                if rest.data is None:
                    raise ConfigFlowException("no_answer")
                response = json.loads(rest.data)
                if "error" in response:
                    responseError = response["error"]
                    if responseError == "Unauthorized":
                        raise ConfigFlowException("not_authorized")
                    else:
                        _LOGGER.warning(
                            "Error received from server: %s", response.error
                        )
            except ConfigFlowException as ex:
                _LOGGER.warning("Configuration error: %s", ex.error)
                errors["base"] = ex.error
            except Exception as ex:
                _LOGGER.warning("Unexpected exception %s", ex)
                errors["base"] = "unknown_exception"
            if not errors:
                # Input is valid, set data.
                self.data = user_input
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=self.data
                )

        _LOGGER.debug("Show input form")
        return self.async_show_form(
            step_id="user", data_schema=AUTH_SCHEMA, errors=errors
        )
