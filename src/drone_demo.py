"""Deterministic drone simulator. No hardware, network or GPS connection is made."""
from copy import deepcopy


SCENARIOS = ("Normal conditions", "Low battery", "Weak signal")
MISSION_POINTS = ((0, 0), (0, 60), (35, 60), (35, 0), (70, 0), (70, 60), (0, 0))


def new_state():
    return {
        "status": "disconnected", "discovered": False,
        "device_name": "Vineyard Demo Drone", "scenario": SCENARIOS[0],
        "battery_pct": 92, "signal_pct": 98, "altitude_m": 0,
        "waypoint_index": 0, "total_waypoints": len(MISSION_POINTS) - 1,
        "captured_frames": 0, "preflight_checked": False, "events": [],
    }


def preflight_checks(state):
    connected = state["status"] != "disconnected"
    return (
        ("Demo connection", connected),
        ("Battery at least 30%", connected and state["battery_pct"] >= 30),
        ("Signal at least 50%", connected and state["signal_pct"] >= 50),
        ("Simulated RGB camera", connected),
    )


def can_start(state):
    return (state["status"] == "ready" and state["preflight_checked"]
            and all(passed for _, passed in preflight_checks(state)))


def transition(state, action, scenario=SCENARIOS[0]):
    """Return a new state or reject an invalid transition without mutating input."""
    result = deepcopy(state)
    status = result["status"]
    if action == "reset":
        return new_state()
    if action == "discover":
        if status != "disconnected":
            raise ValueError("Disconnect before discovering a demo drone.")
        result["discovered"] = True
        message = "One simulated RGB drone discovered."
    elif action == "connect":
        if status != "disconnected" or not result["discovered"]:
            raise ValueError("Discover a demo drone before connecting.")
        if scenario not in SCENARIOS:
            raise ValueError("Unknown demo scenario.")
        result.update(status="ready", scenario=scenario, battery_pct=18 if scenario == "Low battery" else 92,
                      signal_pct=28 if scenario == "Weak signal" else 98, altitude_m=0,
                      preflight_checked=False, waypoint_index=0)
        message = f"Demo link connected · {scenario.lower()}."
    elif action == "preflight":
        if status != "ready":
            raise ValueError("Connect and stop the inspection before running preflight.")
        result["preflight_checked"] = True
        passed = all(check for _, check in preflight_checks(result))
        message = "Simulated preflight passed." if passed else "Simulated preflight failed; inspection blocked."
    elif action == "start":
        if not can_start(result):
            raise ValueError("A connected drone and a passed preflight check are required.")
        result.update(status="inspecting", altitude_m=25, waypoint_index=0)
        message = "Simulated inspection started at waypoint 0."
    elif action == "advance":
        if status != "inspecting":
            raise ValueError("Start an inspection before advancing the route.")
        result["waypoint_index"] += 1
        result["battery_pct"] -= 3
        result["signal_pct"] = (96, 94, 91, 95, 93, 98)[result["waypoint_index"] - 1]
        if result["waypoint_index"] == result["total_waypoints"]:
            result.update(status="completed", altitude_m=0)
            message = "Simulated route complete; drone returned to its start point."
        else:
            message = f"Reached simulated waypoint {result['waypoint_index']}."
    elif action == "capture":
        if status not in {"inspecting", "completed"}:
            raise ValueError("Start an inspection before capturing a demo frame.")
        result["captured_frames"] += 1
        message = f"Generated fixture frame {result['captured_frames']} analysed; no camera feed."
    elif action == "disconnect":
        if status == "disconnected":
            raise ValueError("The demo drone is already disconnected.")
        result.update(status="disconnected", altitude_m=0, preflight_checked=False)
        message = "Demo link disconnected; captured analysis retained."
    else:
        raise ValueError(f"Unknown drone action: {action}")
    result["events"].append({"step": len(result["events"]) + 1, "event": message})
    return result
