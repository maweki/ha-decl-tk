"""Example Load Platform integration."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from logging import Logger, getLogger


DOMAIN = 'decl_tk'

logger = getLogger(__package__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Your controller/hub specific code."""
    # Data that you want to share with your platforms
    invariants_config = config.get("decl_tk").get("invariants", {})
    logger.debug(invariants_config)
    hass.data[DOMAIN] = {
        'invariants': invariants_config
    }

    await hass.helpers.discovery.async_load_platform('binary_sensor', DOMAIN, {}, config)
    await hass.helpers.discovery.async_load_platform('switch', DOMAIN, {}, config)

    return True
