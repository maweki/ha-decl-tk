"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from homeassistant.const import (
    STATE_ON, STATE_OFF
)

from logging import Logger, getLogger
logger = getLogger(__package__)

from . import DOMAIN


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the sensor platform."""
    # We only want this platform to be set up via discovery.
    # if discovery_info is None:
    #     return

    logger.debug("binary_sensor discovery")
    hass.data[DOMAIN]['invariants_sensors'] = {}
    for name, code in hass.data[DOMAIN]['invariants'].items():
      new_binary_sensor = InvariantSensor(hass, name, code)
      hass.data[DOMAIN]['invariants_sensors'][name] = new_binary_sensor
      add_entities([new_binary_sensor])


class InvariantSensor(BinarySensorEntity):
    """Representation of a sensor."""

    def __init__(self, hass, name, code) -> None:
        from .parse import code_to_cnf, get_used_entities
        from homeassistant.helpers.event import async_track_state_change_event
        from ast import unparse

        """Initialize the sensor."""
        self._hass = hass
        self._state = None
        self._name = name
        self._code = code
        self._ast = code_to_cnf(code)
        self._entities = get_used_entities(self._ast)
        logger.debug("New Invariant: " + unparse(self._ast))
        logger.debug("Tracking" + repr(self._entities))
        async_track_state_change_event(hass, list(self._entities), self.source_entity_changed)

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return 'Decl TK Invariant \'' + self._name + '\''

    @property
    def is_on(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        from ast import unparse
        return { 'code': self._code, 'code_cnf': unparse(self._ast), 'tracked_entities': list(self._entities)}

    def source_entity_changed(self, *args, **kwargs):
      self.update()

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        from .parse import eval_cnf
        new_state = eval_cnf(self._hass, self._ast)
        if not new_state == self._state:
          self._state = new_state
          self.schedule_update_ha_state()

class InvariantSwitch(SwitchEntity):

  def __init__(self, hass, name, code) -> None:
      self._name = name

  @property
  def name(self) -> str:
      """Return the name of the sensor."""
      return 'Decl TK Invariant \'' + self._name + '\' Switch'
