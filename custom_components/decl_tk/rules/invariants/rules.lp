-has_value(E) :- is_state(E, "unknown").
-has_value(E) :- is_state(E, "unavailable").
has_value(E) :- is_state(E, S), S != "unknown", S != "unavailable".
:- is_state(E, S), was_state(E, S), action(E, _, _).
:- action(E, A1, _), action(E, A2, _), A1!=A2.
:- action(E, Ac, A1), action(E, Ac, A2), A1!=A2.
is_state(E, S) :- not action(E, _, _), was_state(E, S).
call_service(D, Act, E, Args) :- action(E, Act, Args), domain(D, E).
#maximize { C@1 : action(E, _, _), last_changed(E,C) }.

% Domains:
% sensor
:- action(E, _, _), domain(sensor, E).
% binary_sensor
:- action(E, _, _), domain(binary_sensor, E).
% zone
:- action(E, _, _), domain(zone, E).
% sun
:- action(E, _, _), domain(sun, E).
% weather
:- action(E, _, _), domain(weather, E).
% person
:- action(E, _, _), domain(person, E).
% device_tracker
:- action(E, _, _), domain(device_tracker, E).
% light
{action(E, turn_off, args()); action(E, turn_on, args())} :- domain(light, E).
is_state(L, "on") :- domain(light, L), was_state(L, _), action(L, turn_on, _).
is_state(L, "off") :- domain(light, L), was_state(L, _), action(L, turn_off, _).
% switch
{action(E, turn_off, args()); action(E, turn_on, args())} :- domain(switch, E).
is_state(L, "on") :- domain(switch, L), was_state(L, _), action(L, turn_on, _).
is_state(L, "off") :- domain(switch, L), was_state(L, _), action(L, turn_off, _).
% input_boolean
{action(E, turn_off, args()); action(E, turn_on)} :- domain(input_boolean, E).
is_state(L, "on") :- domain(input_boolean, L), was_state(L, _), action(L, turn_on, _).
is_state(L, "off") :- domain(input_boolean, L), was_state(L, _), action(L, turn_off, _).
% button
{action(E, press, args())} :- domain(button, E).
is_state(E, 0) :- domain(button, E), was_state(E, _), action(E, press, _).
% input_button
{action(E, press, args())} :- domain(input_button, E).
is_state(E, 0) :- domain(input_button, E), was_state(E, _), action(E, press, _).
% select - base facts: select_option/2
{action(E, select_option, args(option(O)))} :- domain(select, E), select_option(E, O).
is_state(E, O) :- domain(select, E), was_state(E, _), action(E, select_option, args(option(O))).
% input_select - base facts: select_option/2
{action(E, select_option, args(option(O)))} :- domain(input_select, E), select_option(E, O).
is_state(E, O) :- domain(input_select, E), was_state(E, _), action(E, select_option, args(option(O))).
% input_number - base facts: set_value/3
{action(E, set_value, args(value(Min..Max)))} :- domain(input_number, E), set_value(E, max, Max), set_value(E, min, Min).
is_state(E, V) :- domain(input_number, E), was_state(E, _), action(E, set_value, args(value(V))).
% number - base facts: set_value/3
{action(E, set_value, args(value(Min..Max)))} :- domain(input_number, E), set_value(E, max, Max), set_value(E, min, Min).
is_state(E, V) :- domain(input_number, E), was_state(E, _), action(E, set_value, args(value(V))).


% domains (not yet) implemented:
% automation
% calendar
% camera
% climate
% conversation
% event
% fan
% group
% input_datetime
% input_text
% lock
% media_player
% openhasp
% proximity
% remote
% scene
% script
% stt
% text
% timer
% todo
% tts
% update
% vacuum

% Facts:
% domain(domain, entity). -- entity domains
% was_state(entity, state). -- The current state (is_state is the goal state)
% last_changed(entity, seconds)
