"""An interactive local aircraft simulation, never a real drone connection."""
import plotly.graph_objects as go
import streamlit as st

from config import AnalysisConfig
from src.drone_demo import MISSION_POINTS, SCENARIOS, can_start, new_state, preflight_checks, transition
from src.mapping.visualization import annotated_image
from src.services.analysis import demo_result, run_cached
from src.ui.session import navigate_to, store_results


def _act(action):
    try:
        state = st.session_state.get("drone_demo", new_state())
        next_state = transition(state, action, st.session_state.get("drone_scenario", SCENARIOS[0]))
        if action == "capture":
            result = run_cached(b"", AnalysisConfig().to_dict(), "Drone demo · generated vineyard frame", True)
            store_results([result])
        elif action == "reset":
            st.session_state["drone_scenario"] = SCENARIOS[0]
        st.session_state["drone_demo"] = next_state
    except (ValueError, OSError) as exc:
        st.session_state["drone_demo_error"] = str(exc)


def _route_chart(state):
    xs, ys = zip(*MISSION_POINTS)
    fig = go.Figure(go.Scatter(x=xs, y=ys, mode="lines+markers", name="Planned route",
                              line={"color": "#b8cbbd", "width": 2, "dash": "dot"},
                              marker={"size": 8}, hovertemplate="Simulated local x: %{x} m<br>y: %{y} m<extra></extra>"))
    if state["status"] in {"inspecting", "completed"}:
        end = state["waypoint_index"] + 1
        fig.add_trace(go.Scatter(x=xs[:end], y=ys[:end], mode="lines+markers", name="Simulated progress",
                                 line={"color": "#25805b", "width": 4}, marker={"size": 9}))
        fig.add_trace(go.Scatter(x=[xs[end - 1]], y=[ys[end - 1]], mode="markers", name="Demo drone",
                                 marker={"color": "#174b34", "size": 17, "symbol": "diamond"}))
    fig.update_layout(height=300, margin={"l": 12, "r": 12, "t": 12, "b": 10},
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#f1f5ef", font={"color": "#18392e"},
                      legend={"orientation": "h", "y": -0.24}, showlegend=True)
    fig.update_xaxes(title="Simulated local x (m)", range=[-8, 78], zeroline=False)
    fig.update_yaxes(title="Simulated local y (m)", range=[-8, 68], zeroline=False, scaleanchor="x")
    return fig


def render():
    state = st.session_state.setdefault("drone_demo", new_state())
    st.session_state.setdefault("drone_scenario", state["scenario"])
    st.title("Drone Connect")
    st.caption("DEMO MODE · Connection, route and telemetry are simulated. Captures use one generated vineyard fixture; no hardware or live camera is connected.")
    error = st.session_state.pop("drone_demo_error", None)
    if error:
        st.error(error)

    connected = state["status"] != "disconnected"
    left, right = st.columns([1, 2], gap="large")
    with left:
        with st.container(border=True):
            st.subheader("Connection")
            st.button("Discover demo drone", on_click=_act, args=("discover",), disabled=connected, width="stretch")
            if state["discovered"]:
                st.write(f"**{state['device_name']}**")
                st.caption("Virtual RGB aircraft · Local simulator")
            st.selectbox("Connection scenario", SCENARIOS, key="drone_scenario", disabled=connected)
            if not connected:
                st.button("Connect demo drone", type="primary", on_click=_act, args=("connect",),
                          disabled=not state["discovered"], width="stretch")
            else:
                st.success(f"Demo link connected · {state['status'].replace('_', ' ').title()}")
                st.button("Disconnect", on_click=_act, args=("disconnect",), width="stretch")
        with st.container(border=True):
            st.subheader("Preflight")
            st.button("Run preflight check", on_click=_act, args=("preflight",), disabled=state["status"] != "ready", width="stretch")
            if state["preflight_checked"]:
                for label, passed in preflight_checks(state):
                    st.markdown(f"{'✓' if passed else '✕'} {label}")
                if not all(passed for _, passed in preflight_checks(state)):
                    st.warning("Inspection blocked. Disconnect and select normal conditions to retry.")
            else:
                st.caption("Check the simulated link, battery, signal and camera before starting.")
            st.button("Start demo inspection", type="primary", on_click=_act, args=("start",),
                      disabled=not can_start(state), width="stretch")
    with right:
        st.subheader("Inspection control")
        st.caption("SIMULATED TELEMETRY · Values change when you advance the route.")
        a, b, c, d = st.columns(4)
        a.metric("Battery", f"{state['battery_pct']}%" if connected else "—")
        b.metric("Signal", f"{state['signal_pct']}%" if connected else "—")
        c.metric("Altitude", f"{state['altitude_m']} m" if connected else "—")
        d.metric("Captured frames", str(state["captured_frames"]))
        route, camera = st.tabs(["Mission route", "Synthetic camera preview"])
        with route:
            st.plotly_chart(_route_chart(state), width="stretch", config={"displayModeBar": False})
        with camera:
            if connected:
                st.image(demo_result()["image"], caption="GENERATED RGB FIXTURE · Fixed demonstration image; this is not a live camera feed.", width="stretch")
            else:
                st.info("Connect a demo drone to preview the generated camera fixture.")
        st.progress(state["waypoint_index"] / state["total_waypoints"],
                    text=f"Route progress · {state['waypoint_index']} / {state['total_waypoints']} waypoints")
        advance, capture = st.columns(2)
        advance.button("Advance inspection", on_click=_act, args=("advance",),
                       disabled=state["status"] != "inspecting", width="stretch")
        capture.button("Capture demo frame", on_click=_act, args=("capture",),
                       disabled=state["status"] not in {"inspecting", "completed"}, width="stretch")
        if state["status"] == "completed":
            st.success("Simulated route complete. Review a captured frame or disconnect.")

    results = st.session_state.get("results", [])
    if state["captured_frames"] and results and results[0]["metadata"].get("source_name") == "Drone demo · generated vineyard frame":
        with st.container(border=True):
            preview, summary = st.columns([2, 1], gap="large")
            result = results[0]
            preview.image(annotated_image(result), caption="SYNTHETIC CAPTURE · Generated fixture with computed canopy and gap overlays.", width="stretch")
            with summary:
                st.subheader("Capture inspection")
                st.write("The generated frame has been processed by the vineyard analysis pipeline.")
                st.metric("Visible canopy", f"{result['summary']['canopy_coverage']:.1f}%")
                st.metric("Possible canopy gaps", str(result["summary"]["gap_count"]))
                st.button("Open captured health map", on_click=navigate_to, args=("Vineyard Health Map",), type="primary", width="stretch")
                st.caption("Each capture reuses the same synthetic fixture. Findings are demonstration results and require field validation on real imagery.")
    with st.expander("Demo activity log", expanded=False):
        if state["events"]:
            st.dataframe(state["events"], hide_index=True, width="stretch")
        else:
            st.caption("Discover a demo drone to begin.")
        st.button("Reset drone demo", on_click=_act, args=("reset",))
