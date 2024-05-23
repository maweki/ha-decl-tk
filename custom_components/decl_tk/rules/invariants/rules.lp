-has_value(E) :- is_state(E, "unknown").
-has_value(E) :- is_state(E, "unavailable").
has_value(E) :- is_state(E, S), S != "unknown", S != "unavailable".
:- is_state(E, S), was_state(E, S), action(E, _).
:- action(E, A1), action(E, A2), A1!=A2.
is_state(E, S) :- not action(E, _), was_state(E, S).
call_service(D, A, E) :- action(E, A), domain(D, E).
#minimize { C@1 : action(E, _), last_changed(E,C) }.

% Domains:
% sensor
:- action(E, _), domain(sensor, E).
% binary_sensor
:- action(E, _), domain(binary_sensor, E).
% zone
:- action(E, _), domain(zone, E).
% sun
:- action(E, _), domain(sun, E).
% light
{action(E, turn_off); action(E, turn_on)} :- domain(light, E).
is_state(L, "on") :- domain(light, L), was_state(L, "off"), action(L, turn_on).
is_state(L, "off") :- domain(light, L), was_state(L, "on"), action(L, turn_off).
% switch
{action(E, turn_off); action(E, turn_on)} :- domain(switch, E).
is_state(L, "on") :- domain(switch, L), was_state(L, "off"), action(L, turn_on).
is_state(L, "off") :- domain(switch, L), was_state(L, "on"), action(L, turn_off).
% input_boolean
{action(E, turn_off); action(E, turn_on)} :- domain(input_boolean, E).
is_state(L, "on") :- domain(input_boolean, L), was_state(L, "off"), action(L, turn_on).
is_state(L, "off") :- domain(input_boolean, L), was_state(L, "on"), action(L, turn_off).

% domains (not yet) implemented:
% automation
% button
% calendar
% camera
% climate
% conversation
% device_tracker
% event
% fan
% group
% input_button
% input_datetime
% input_number
% input_select
% input_text
% lock
% media_player
% number
% openhasp
% person
% proximity
% remote
% scene
% script
% select
% sensor
% stt
% text
% timer
% todo
% tts
% update
% vacuum
% weather

% Facts:
% domain(domain, entity). -- entity domains
% was_state(entity, state). -- The current state (is_state is the goal state)
% last_changed(entity, -10th-seconds)
