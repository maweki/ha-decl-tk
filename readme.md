# Home Assistant Declarative Toolkit

The Declarative Toolkit is a Home Assistant integration that extends Home Assistant with some declarative features that enables symbolic AI and automated reasoning.

## Installation and Usage

Copy the integration directory into your `custom_components` directory. After installation, add `decl_tk:` to your configuration.

## Features/Tools

### Integrity Maintenance through Answer Set Programming

A home usually has some integrity constraints, some conditions that should be true, no matter what. Once such a condition is no longer true, the smart home should try to make it true again, returning to a valid state. Event-Condition-Action rules are not very "smart" for this use case, as we need to know *which events* may affect the condition and once we are in an invalid state, *which actions* need to be taken, in order to return to a valid state.

#### How it works

You give the ingerity maintenance module a Python expression using the `states`/`is_state`/`has_state` functions as you're used to in your templates. The Python expression is parsed, transformed according to some rules, and then evaluated against Home Assistant's current state. Each invariant will add a sensor, tracking the value of said invariant. Each invariant will also add a switch that allows us to disable enforcement/maintenance of said invariant. If enforcement is enabled and the sensor shows the invariant in need of maintaining, the transformed Python expression is converted to goal clauses of a logic program, specifically an Answer Set Program. Facts for the states and domains for the used entities are added to the program, as are some general rules about how entity states change depending on called services. We feed the Answer Set Program into [clingo](https://potassco.org/clingo/) and get possible services to call in order to achieve the desired goal of restoring the invariant. We optimize for affecting the switches/lights/devices/etc. that have least recently been changed and try to leave the recently changed ones alone. For the best answer set, we call all deduced services and expect the invariant to be restored.

#### Usage

Add the key `invariants:` under `decl_tk:` and add an invariant as a python expression using the `states` and `is_state` functions. For equivalence, use the `is` operator. The following example uses a binary sensor for when it is dark, and the state of a light should track the state of darkness.

```
decl_tk:
  invariants:
    inv1: "is_state('binary_sensor.it_is_dark', 'on') is is_state('light.light1', 'on')"
    inv2: "(is_state('binary_sensor.it_is_dark', 'on') or is_state('cover.shutter', 'closed')) and states('zone.home') > 0) is is_state('light.light1', 'on')"
```

![invariant 1](https://dbs.informatik.uni-halle.de/wenzel/invariant1.gif)

For the second example (domains not yet implemented completely), the light should be on if someone's home and either the shutters are closed or it is dark outside. If the shutters are being closed, then the lights turn on. And if the lights are turned on, the shutters close.

Currently supported domains:

* sensor/binary_sensor
* light (only on/off)
* switch/input_boolean
* sun/weather
* zone/device_tracker
* button/input_button
* select/input_select
* person

#### Notes

The used ASP solver does not support floating point numbers. **Only strings and integers**. Therefore, in the solving case, floating point numbers are rounded to the next integer using `round`. During invariant tracking, no rounding occurs. This means, that it is possible for the solver to see no action necessary while the invariant is tracked as `off`. This is probably not ideal behaviour and due to change (i.e., rounding should also occur when evaluating invariants).

Entities with a timestamp as state (e.g. buttons) do not really make sense in terms of an invariant. Each timestamp is always converted to the number of seconds passed since that timestamp. So you can do `states('input_button.btn') < 30` for an invariant that a button should not be unpressed for 30 seconds or more. If an entity of such a domain is added, the invariant state is evaluated every 60 seconds in addition to the other state changes. The 60 seconds value should be configurable in the future.

Additional rules can be added into `*.lp` files in the `rules/invariants/` subdirectory. Predefined predicates are:

* `is_state` / `was_state` for goal state and current state
* `action`, `domain`, `call_service`

As only the states for the entities actually used are fed into the solver, entity names may not be generated dynamically.

Multiple invariants should, if possible, use disjoint sets of devices that receive actions, as there is no global coordination between the invariants. Of course, it is always possible to write them in a single invariant as a conjunction. Though the seperate switches for enforcing both invariants may be desired.

#### Todo

* support more domains
* support True/False constants to make some rules easier
* more graceful error handling
* support arithmetic in invariants
* support attributes
* configuration verification
* extend configuration to allow for nice entity names, heuristics, other settings. Ideally we would like to be able to exclude entities for changing.
* allow scenes to be checked against the invariants (somehow?)
* make time tracking configurable

### Event Recognition through Metric Temporal Operators

This is not yet implemented.

## Scope & Research

There are currently academic papers in the works describing possible approaches for (constraint) logic programming within the home automation domain. This repository is a "playground" to allow us to evaluate approaches within a real home automation setting. I am happy to participate in any research in that direction.

Though I have an academic background and the ideas are very much shaped by my research, this is not just a proof of concept. I plan to use and maintain this extension and hope other people find the declerative semantics useful. Declarative descriptions should be much clearer and much easier to reason about than the alternative.

## Contributing

Contributions are welcome, both academic in nature, and general support for home assistant programming (code style, best practices, etc.).
