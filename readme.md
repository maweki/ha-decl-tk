# Home Assistant Declarative Toolkit

The Declarative Toolkit is a Home Assistant integration that extends Home Assistant with some declarative features that enables symbolic AI and automated reasoning.

## Installation and Usage

Copy the integration directory into your `custom_components` directory.
After installation, add `decl_tk:` to your configuration.

## Features/Tools

### Invariant Maintenance through Answer Set Programming

A home usually has some invariants, some conditions that should be true, no matter what. Once such a condition is no longer true, the smart home should try to make it true again, returning to a valid state. Event-Condition-Action rules are not very "smart" for this use case, as we need to know which Events may affect the condition and once we are in an invalid state, which actions need to be taken, in order to return to a valid state.

#### Usage

Add the key `invariants:` under `decl_tk:` and add an invariant as a python expression using the `states` and `is_state` functions. For equivalence, use the `is` operator. The following example uses a binary sensor for when it is dark, and the state of a light should track the state of darkness.

```
decl_tk:
  invariants:
    inv1: "is_state('binary_sensor.it_is_dark', 'on') is is_state('light.light1', 'on')"
```

![invariant 1](https://dbs.informatik.uni-halle.de/wenzel/invariant1.gif)

Each invariant will add a sensor, tracking the value of said invariant, and a switch that allows us to disable enforcement/maintenance of said invariant.


#### Todo

* support more domains
* support arithmetic in invariants
* support attributes
* extend configuration to allow for nice entity names, heuristics, other settings

### Event Recognition through Metric Temporal Operators

This is not yet implemented.

## Research

There are currently academic papers in the works describing possible approaches for (constraint) logic programming within the home automation domain. This repository is a "playground" to allow us to evaluate approaches within a real home automation setting. I am happy to participate in any research in that direction.

## Contributing

Contributions are welcome, both academic in nature, and general support for home assistant programming (code style, best practices, etc.).
