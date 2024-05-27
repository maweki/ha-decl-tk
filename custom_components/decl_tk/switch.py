"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from homeassistant.const import (
    STATE_ON, STATE_OFF
)

from logging import Logger, getLogger
logger = getLogger(__package__)

from . import DOMAIN
from time import sleep
from pathlib import Path
from datetime import datetime

import clingo
from random import choice

invariant_rules_dir = Path(__file__).parent / "rules" / "invariants"
invariant_rules_files = invariant_rules_dir.glob("*.lp")
invariant_rules = ''
for rules_file_path in invariant_rules_files:
    with open(file=rules_file_path, encoding="UTF-8") as rules_file:
        invariant_rules += rules_file.read()

def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the sensor platform."""
    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    logger.debug("switch discovery")
    hass.data[DOMAIN]['invariants_switches'] = {}
    for name, code in hass.data[DOMAIN]['invariants'].items():
      while name not in hass.data[DOMAIN]['invariants_sensors']:
        sleep(0.5) # there must be a better way to wait for platform setup
      sensor = hass.data[DOMAIN]['invariants_sensors'][name]
      new_switch = InvariantSwitch(hass, name, code, sensor)
      add_entities([new_switch])
      hass.data[DOMAIN]['invariants_switches'][name] = new_switch

class InvariantSwitch(SwitchEntity, RestoreEntity):

    def __init__(self, hass, name, code, tracked_sensor) -> None:
        from .parse import code_to_cnf, get_used_entities

        self._name = name
        self._tracked_sensor = tracked_sensor
        self.unsub_tracker = None
        self._hass = hass
        self._code = code
        self._ast = code_to_cnf(code)
        self._entities = get_used_entities(self._ast)
        self._unsatisfiable = False

    @property
    def extra_state_attributes(self):
        from ast import unparse
        return { 'code': self._code, 'code_cnf': unparse(self._ast),
                 'tracked_invariant_sensor': self._tracked_sensor.entity_id, 'used_entities': list(self._entities), 'unsatisfiable': self._unsatisfiable}

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return 'Decl TK Invariant \'' + self._name + '\' Switch'

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self.unsub_tracker is not None

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        last_state = await self.async_get_last_state()
        if last_state and last_state.state == STATE_ON:
            await self.async_turn_on()

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        if self.unsub_tracker:
            self.unsub_tracker()
        return await super().async_will_remove_from_hass()

    async def async_turn_on(self, **kwargs: Any) -> None:
        if self.is_on:
            return
        from homeassistant.helpers.event import async_track_state_change_event

        self.unsub_tracker = async_track_state_change_event(
            self.hass,
            [self._tracked_sensor.entity_id],
            self.async_tracked_sensor_change,
        )

        self.async_write_ha_state()

    async def async_tracked_sensor_change(self, *args, **kwargs):
        await self.async_update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off flux."""
        if self.is_on:
            self.unsub_tracker()
            self.unsub_tracker = None

        self.async_write_ha_state()

    async def async_update(self):
        if self.is_on is True and self._tracked_sensor.is_on is False:
            from .parse import split_disjunctions, to_implication_form, implication_body_to_rule
            goal_rules = []
            for d in split_disjunctions(self._ast):
              body = implication_body_to_rule(to_implication_form(d))
              body = body.replace('\'', '"') # this is bad. This should be done via visitor
              goal_rules.append(body)
            # logger.debug(repr(goal_rules))
            state_facts = []
            for e in self._entities:
              entity = self.hass.states.get(e)
              state_facts.append('was_state(' + quote(e) + ', '+ format_return_value(entity.state) +').')
              state_facts.append('domain(' + entity.domain + ', '+ quote(e) +').')
              state_facts.append('last_changed(' + quote(e) + ', '+ format_return_value(entity.last_changed) + ').')
              if entity.domain in ('select', 'input_select'):
                for option in entity.attributes['options']:
                  state_facts.append('select_option(' + quote(e) + ', '+ quote(option) +').')

            ctl = clingo.Control()
            ctl.configuration.solve.models = 0
            program = invariant_rules + '\n'.join(state_facts + goal_rules)
            logger.debug(program)
            ctl.add("base", [], program)
            ctl.ground([("base", [])])
            with ctl.solve(yield_=True) as handle:
              models = []
              for model in handle:
                models.append(model.symbols(atoms=True))
              logger.debug(str(len(models)) + " models found")
              if models:
                self._unsatisfiable = False
                self.schedule_update_ha_state()
                # mdl = choice(models)
                mdl = models[-1]
                logger.debug("Model found: " + " - " + repr(mdl))
                for term in mdl:
                  if term.name == 'call_service':
                    domain, service, entity, args = term.arguments
                    kwargs = decode_args(args)
                    logger.debug(repr(domain.name) + " - " + repr(service.name) + repr({"entity_id" : entity.string} | kwargs))
                    await self.hass.services.async_call(domain.name, service.name, {"entity_id" : entity.string} | kwargs)
              else:
                logger.debug('Invariant ' + self._name + ' is currently not satisfiable')
                self._unsatisfiable = True
                self.schedule_update_ha_state()

from .parse import coerce_return_value

def decode_args(args):
  def get_val_from_symbol(symbol):
    try:
      return symbol.number
    except:
      return symbol.string

  return { arg.name : get_val_from_symbol(arg.arguments[0]) for arg in args.arguments}

def format_return_value(v):
  try:
    return str(coerce_return_value(v))
  except:
    return quote(v)

def quote(v):
  return "\"" + str(v).replace("\"", "\\\"") + "\""
