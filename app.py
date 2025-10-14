from dash import Dash, html, dcc, Input, Output, State, no_update
import dash
import time
import re
import importlib.util
from pathlib import Path

# ------------------------
# App bootstrap
# ------------------------
app = Dash(__name__)  # auto-loads ./assets/*.css if present
server = app.server

# ------------------------
# Constants / Defaults
# ------------------------
DEFAULT_VIDEO = "/assets/static_dash/generated/exp1/slowed_generated_terrain_lift.mp4"

# 3DSSPP images (update to your actual exported files)
SSPP_SMALL_LEFT  = "/assets/static_dash/generated/exp1/1-humanoid.png"
SSPP_SMALL_RIGHT = "/assets/static_dash/generated/exp1/1-stick-side.png"
SSPP_SMALL_WIDE  = "/assets/static_dash/generated/exp1/1-back.png"

SSPP_BIG_LEFT  = "/assets/static_dash/mocap/exp1/2-2-humanoid.png"
SSPP_BIG_RIGHT = "/assets/static_dash/mocap/exp1/2-2-stick-side.png"
SSPP_BIG_WIDE  = "/assets/static_dash/mocap/exp1/2-2-back.png"

# Top-left two tiles
SMALL_VIDEO_A = "/assets/static_dash/mocap/exp1/bad_raw.mov"
MOCAP_HTML    = "/assets/static_dash/mocap/exp1/ref_motion_render_patched.html?v=1"

# Path to your generated NIOSH score python file
SCORE_PATH = Path("assets/static_dash/generated/exp1/NIOSH_score.py")


# ------------------------
# Helpers: NIOSH & DSSPP
# ------------------------
def load_niosh_scores(path: Path = SCORE_PATH) -> dict:
    """
    Dynamically load score variables from a python file without requiring PYTHONPATH changes.
    Expected (customize to your file's contents): LI, RWL, HM, VM, DM, AM, FM, CM
    """
    try:
        if not path.exists():
            print(f"[warn] NIOSH score file not found: {path}")
            return {}
        spec = importlib.util.spec_from_file_location("niosh_scores", str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        data = {
            "LI":  getattr(mod, "LI",  None),
            "RWL": getattr(mod, "RWL", None),
            "HM":  getattr(mod, "HM",  None),
            "VM":  getattr(mod, "VM",  None),
            "DM":  getattr(mod, "DM",  None),
            "AM":  getattr(mod, "AM",  None),
            "FM":  getattr(mod, "FM",  None),
            "CM":  getattr(mod, "CM",  None),
        }
        return data
    except Exception as e:
        print("[error] Failed to load NIOSH scores:", e)
        return {}


def format_niosh_text(scores: dict) -> str:
    if not scores:
        return "NIOSH scores unavailable."
    def fmt(x):
        return "—" if x is None else f"{x}"
    return (
        f"Lifting Index (LI): {fmt(scores.get('LI'))}\n"
        f"Recommended Weight Limit (RWL): {fmt(scores.get('RWL'))}\n"
        # f"HM: {fmt(scores.get('HM'))}   VM: {fmt(scores.get('VM'))}   DM: {fmt(scores.get('DM'))}\n"
        # f"AM: {fmt(scores.get('AM'))}   FM: {fmt(scores.get('FM'))}   CM: {fmt(scores.get('CM'))}"
    )


def format_dsspp_text() -> str:
    # Placeholder; wire to your real numbers/file if needed.
    return "L4/L5 Back Compression Force = 3.1 kN"


# ------------------------
# Chat bubble helper
# ------------------------
def bubble(role, kind, content, filename=None):
    classes = f"msg msg-{role}"
    if kind == "file":
        inner = html.Div([
            html.Div("📎", className="file-ico"),
            html.Div([
                html.Div("File uploaded", className="file-title"),
                # html.Div(filename or "file", className="file-name"),
            ], className="file-meta"),
        ], className="file-bubble")
    else:
        inner = html.Div(content, className="msg-text")
    return html.Div(inner, className=classes)


# ------------------------
# Layout
# ------------------------
app.layout = html.Div(
    className="page",

    children=[
        # Invisible stores
        dcc.Store(id="show-video", data={"show": False, "src": ""}),  # controls big video rendering
        dcc.Store(id="chat-store", data=[]),

        # ---- Top-left two squares: left = video, right = mocap HTML (square iframe) ----
        html.Div(className="card pink video1", children=[
            html.Div("Captured Motion", className="card-badge"),
            html.Div(className="video-grid", children=[
                html.Video(src=SMALL_VIDEO_A, controls=True, className="player"),
                html.Div(className="square-frame", children=[
                    html.Iframe(
                        src=MOCAP_HTML,
                        className="square-iframe",
                    )
                ]),
            ]),
        ]),
        # top spacer
        html.Div(className="divider"),
        # ---- Middle column row 1: NIOSH text ----
        html.Div(className="card pink niosh", children=[
            html.Div("NIOSH Lifting Equation", className="card-badge"),
            # html.Div("NIOSH Lifting Equation", className="card-title"),
            html.Pre(id="niosh-text-small", className="score-pre"),
        ]),

        # ---- Middle column row 2: 3DSSPP images + text ----
        html.Div(className="card pink dsspp", children=[
            html.Div("3DSSPP", className="card-badge"),
            html.Div(className="ssp-grid", children=[
                html.Img(src=SSPP_SMALL_LEFT,  className="square"),
                html.Img(src=SSPP_SMALL_RIGHT, className="square"),
                html.Img(src=SSPP_SMALL_WIDE,  className="wide"),
            ]),
            html.Pre(id="dsspp-text-small", className="score-pre"),
        ]),

        # ---- Left bottom two rows: Big video (persistent element) with dcc.Loading spinner ----
        html.Div(className="card green video_big", children=[
            html.Div("Recommended Motion", className="card-badge"),
            dcc.Loading(
                id="video-loading",
                type="circle",
                children=html.Div(
                    id="video-stage",
                    children=[
                        html.Video(
                            id="player",
                            src="",
                            controls=True,
                            autoPlay=True,
                            muted=True,   # iOS Safari requires muted for autoplay
                            preload="auto",
                            className="big-player"
                        ),
                    ],
                ),
            ),
        ]),

        # ---- Middle bottom row 3: NIOSH big text ----
        html.Div(className="card green niosh_big", children=[
            html.Div("NIOSH Lifting Equation", className="card-badge"),
            html.Pre(id="niosh-text-big", className="score-pre"),
        ]),

        # ---- Middle bottom row 4: 3DSSPP big images + text ----
        html.Div(className="card green dsspp_big", children=[
            html.Div("3DSSPP", className="card-badge"),
            html.Div(className="ssp-grid", children=[
                html.Img(src=SSPP_BIG_LEFT,  className="square"),
                html.Img(src=SSPP_BIG_RIGHT, className="square"),
                html.Img(src=SSPP_BIG_WIDE,  className="wide"),
            ]),
            html.Pre(id="dsspp-text-big", className="score-pre"),
        ]),

        # ---- Right: Chat spanning all rows ----
        html.Div(className="card chat", children=[
            html.Div(id="chat-history", className="chat-history"),
            html.Div(className="chat-input-row", children=[
                dcc.Upload(
                    id="chat-upload",
                    multiple=False,
                    children=html.Div([
                        html.Span("＋", className="upload-plus"),
                    ], className="upload-area"),
                ),
                dcc.Textarea(
                    id="chat-text",
                    placeholder="Ask anything…",
                    className="chat-textarea",
                    maxLength=4000,
                ),
                html.Button("Send", id="chat-send", n_clicks=0, className="chat-send-btn"),
            ]),
        ]),
    ],
)


# ------------------------
# Callbacks
# ------------------------
@app.callback(
    Output("chat-store", "data"),
    Output("chat-text", "value"),
    Output("chat-upload", "contents"),
    Output("chat-upload", "filename"),
    Output("show-video", "data"),  # updates big video state {show, src}
    Input("chat-send", "n_clicks"),
    Input("chat-upload", "contents"),
    State("chat-upload", "filename"),
    State("chat-text", "value"),
    State("chat-store", "data"),
    State("show-video", "data"),
    prevent_initial_call=True,
)
def handle_chat(n_clicks, upload_contents, upload_filename, text_value, history, video_state):
    ctx = getattr(dash, "callback_context", None) or getattr(dash, "ctx", None)
    if not ctx or not ctx.triggered:
        return no_update, no_update, no_update, no_update, no_update

    history = history or []
    video_state = video_state or {"show": False, "src": ""}

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    print("[debug] handle_chat triggered by:", trigger_id)

    if trigger_id == "chat-send":
        user_text = (text_value or "").strip()
        if user_text == "":
            return history, no_update, no_update, no_update, no_update

        history.append({"role": "user", "kind": "text", "content": user_text})
        lowered = user_text.lower()

        # /play [optional path], /video, /hide, /stop
        m = re.search(r"(?:^|\s)/(?:play|video)(?:\s+(.+))?$", user_text, flags=re.IGNORECASE)
        if m:
            candidate = (m.group(1) or "").strip()
            if candidate == "":
                src = DEFAULT_VIDEO
            else:
                if candidate.startswith("/assets/"):
                    src = candidate
                elif candidate.startswith("assets/"):
                    src = "/" + candidate
                else:
                    src = f"/assets/static_dash/mocap/exp1/{candidate}"
            video_state = {"show": True, "src": src}
            bot_reply = f"Playing: {src}"
        elif any(k in lowered for k in ("/hide", "/stop", "hide video", "stop video")):
            video_state = {"show": False, "src": video_state.get("src", "")}
            bot_reply = "Video hidden."
        else:
            bot_reply = "fixed response B" if "key" in lowered else "…"

        history.append({"role": "assistant", "kind": "text", "content": bot_reply})
        return history, "", no_update, no_update, video_state

    if trigger_id == "chat-upload" and upload_contents is not None:
        history.append({"role": "user", "kind": "file", "content": "file", "filename": upload_filename})
        history.append({"role": "assistant", "kind": "text", "content": "fixed response A"})
        return history, no_update, None, None, no_update

    return history, no_update, no_update, no_update, no_update


@app.callback(
    Output("chat-history", "children"),
    Input("chat-store", "data")
)
def render_history(history):
    history = history or []
    children = [
        bubble(
            role=msg.get("role", "user"),
            kind=msg.get("kind", "text"),
            content=msg.get("content", ""),
            filename=msg.get("filename"),
        )
        for msg in history
    ]
    return children


# Persistent big video: update only the src and rely on dcc.Loading to show spinner while sleeping
@app.callback(
    Output("player", "src"),
    Input("show-video", "data")
)
def update_big_video_src(video_state):
    print("[debug] update_big_video_src:", video_state)
    if not video_state or not video_state.get("show"):
        return ""
    src = video_state.get("src") or DEFAULT_VIDEO
    # Artificial wait (2s) so dcc.Loading shows the spinner
    time.sleep(2)
    return src


@app.callback(
    Output("niosh-text-small", "children"),
    Output("niosh-text-big",   "children"),
    Output("dsspp-text-small", "children"),
    Output("dsspp-text-big",   "children"),
    Input("chat-store", "data")   # re-evaluate when chat changes; change to your preferred trigger
)
def fill_score_text(_):
    scores = load_niosh_scores()
    n_small = format_niosh_text(scores)
    n_big   = format_niosh_text(scores)
    d_small = format_dsspp_text()
    d_big   = format_dsspp_text()
    return n_small, n_big, d_small, d_big


if __name__ == "__main__":
    app.run(debug=True)
