"""Drone simulation transitions enforce the demo's connection and preflight flow."""
from copy import deepcopy

import pytest

from src.drone_demo import can_start, new_state, preflight_checks, transition


def connected(scenario="Normal conditions"):
    return transition(transition(new_state(), "discover"), "connect", scenario)


def test_disconnected_actions_and_preflight_are_blocked():
    state = new_state()
    for action in ("connect", "preflight", "start", "advance", "capture", "disconnect"):
        with pytest.raises(ValueError):
            transition(state, action)
    assert state == new_state()
    assert not can_start(state)
    assert not any(passed for _, passed in preflight_checks(state))


@pytest.mark.parametrize("scenario", ["Low battery", "Weak signal"])
def test_failed_preflight_blocks_inspection(scenario):
    state = transition(connected(scenario), "preflight")
    assert state["preflight_checked"]
    assert not all(passed for _, passed in preflight_checks(state))
    assert not can_start(state)
    with pytest.raises(ValueError):
        transition(state, "start")


def test_complete_inspection_capture_and_disconnect_preserve_history():
    state = connected()
    with pytest.raises(ValueError):
        transition(state, "start")
    state = transition(state, "preflight")
    assert can_start(state)
    state = transition(state, "start")
    assert state["altitude_m"] == 25
    with pytest.raises(ValueError):
        transition(state, "preflight")
    state = transition(state, "capture")
    for _ in range(state["total_waypoints"]):
        state = transition(state, "advance")
    assert state["status"] == "completed"
    assert state["altitude_m"] == 0
    assert state["waypoint_index"] == state["total_waypoints"]
    with pytest.raises(ValueError):
        transition(state, "advance")
    state = transition(state, "capture")
    state = transition(state, "disconnect")
    assert state["status"] == "disconnected"
    assert state["captured_frames"] == 2
    assert state["events"]
    assert not state["preflight_checked"]
    state = transition(state, "connect")
    assert state["waypoint_index"] == 0
    assert not can_start(state)
    assert state["captured_frames"] == 2


def test_transition_is_pure_and_reset_clears_only_drone_state():
    original = connected()
    before = deepcopy(original)
    updated = transition(original, "preflight")
    assert original == before
    assert updated["preflight_checked"] and not original["preflight_checked"]
    assert len(updated["events"]) == len(original["events"]) + 1
    assert transition(updated, "reset") == new_state()


def test_unknown_scenario_and_actions_are_rejected():
    with pytest.raises(ValueError):
        transition(transition(new_state(), "discover"), "connect", "Real drone")
    with pytest.raises(ValueError):
        transition(new_state(), "takeoff")
