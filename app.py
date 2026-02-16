from dash import Dash, html, dcc, Input, Output, State, no_update
import dash
import time
import re
import importlib.util
from pathlib import Path
import base64
import json
from datetime import datetime

# ------------------------
# App bootstrap
# ------------------------
app = Dash(__name__)  # auto-loads ./assets/*.css if present
server = app.server

# ------------------------
# Constants / Defaults
# ------------------------
DEFAULT_VIDEO = "/assets/static_dash/generated/exp1/slowed_generated_terrain_lift_fast.mp4"

# 3DSSPP images (update to your actual exported files)
SSPP_SMALL_LEFT  = "/assets/static_dash/mocap/exp1/2-2-humanoid.png"
SSPP_SMALL_RIGHT = "/assets/static_dash/mocap/exp1/2-2-stick-side.png"
SSPP_SMALL_WIDE  = "/assets/static_dash/mocap/exp1/2-2-back.png"

SSPP_BIG_LEFT  = "/assets/static_dash/generated/exp1/1-humanoid.png"
SSPP_BIG_RIGHT = "/assets/static_dash/generated/exp1/1-stick-side.png"
SSPP_BIG_WIDE  = "/assets/static_dash/generated/exp1/1-back.png"

# Top-left two tiles
SMALL_VIDEO_A = "/assets/static_dash/mocap/exp1/bad_raw.mov"
MOCAP_HTML    = "/assets/static_dash/mocap/exp1/ref_motion_render_small_hand_patched.html?v=1"

# Path to your generated NIOSH score python file
SCORE_GENERATED_PATH = Path("assets/static_dash/generated/exp1/NIOSH_score.py")
SCORE_PATH = Path("assets/static_dash/mocap/exp1/NIOSH_score.py")

# Upload directory
UPLOAD_DIR = Path("assets/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 3D scan extensions (filename-based only)
SCAN_EXTS = {
    ".obj", ".stl", ".ply", ".glb", ".gltf", ".fbx",
    ".las", ".laz", ".e57", ".xyz", ".ptx", ".pts"
}


# ------------------------
# Helpers: NIOSH & DSSPP & Uploads
# ------------------------
def load_niosh_scores(path: Path = SCORE_GENERATED_PATH, id: int = 0) -> dict:
    """
    Load score variables from the given NIOSH file.
    Each variable may be a list/array — we select entry [id].
    """
    try:
        if not path.exists():
            print(f"[warn] NIOSH score file not found: {path}")
            return {}

        spec = importlib.util.spec_from_file_location("niosh_scores", str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore

        def get_item(var, idx):
            """Return single index if possible, else var itself."""
            try:
                v = getattr(mod, var, None)
                if v is None:
                    return None
                return v[idx] if isinstance(v, (list, tuple)) and len(v) > idx else v
            except Exception:
                return getattr(mod, var, None)

        data = {
            "SSPP_L4L5": get_item("SSPP_L4L5", id),
            "LI": get_item("LI", id),
            "RWL": get_item("RWL", id),
        }
        print(f"[Debug] data {data}")
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


def format_dsspp_text(scores: dict | None = None) -> str:
    # If scores provided, try to print back force; else fall back to placeholder
    if scores:
        backN = scores.get("SSPP_L4L5")
        if backN is not None:
            try:
                kN = float(backN) / 1000.0
                return f"L4/L5 Back Compression Force = {kN:.2f} kN"
            except Exception:
                pass
    return "L4/L5 Back Compression Force = —"


def is_scan_file(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in SCAN_EXTS


def save_upload_to_disk(contents: str, filename: str) -> str:
    """
    contents: dcc.Upload data URL 'data:<mime>;base64,<b64>'
    returns web path like '/assets/uploads/scan.ext'
    """
    if not contents or "," not in contents:
        raise ValueError("Invalid upload contents")
    header, b64data = contents.split(",", 1)
    raw = base64.b64decode(b64data)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe = "scan." + filename.split(".")[-1]
    out = UPLOAD_DIR / f"{safe}"
    with open(out, "wb") as f:
        f.write(raw)
    return "/" + str(out).replace("\\", "/")


def save_task_json(raw_text: str) -> str:
    """
    Saves a stub JSON extracted from a 'Task description:' chat message.
    You will replace the 'xxxx' later with real parsed parameters.
    """
    out = UPLOAD_DIR / "task.json"
    stub = {"raw": raw_text, "extracted": "xxxx"}  # placeholder
    out.write_text(json.dumps(stub, indent=2), encoding="utf-8")
    return "/" + str(out).replace("\\", "/")


def is_motion_safe(scores: dict) -> bool | None:
    """
    Safety rule (per spec):
      - NIOSH: LI <= 1
      - 3DSSPP: back force <= 3400 N
    Returns None if either metric is missing.
    """
    li = scores.get("LI")
    backN = scores.get("SSPP_L4L5")
    print(f"[Debug] LI {li}")
    print(f"[Debug] backN {backN}")
    if li is None or backN is None:
        return None
    try:
        return (float(li) <= 1.0) and (float(backN) <= 3400.0)
    except Exception:
        return None


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
        dcc.Store(id="scan-state",  data={"has_scan": False, "path": ""}),
        dcc.Store(id="task-state",  data={"has_task": False, "json_path": ""}),
        dcc.Store(id="verdict-state", data={"ready": False, "safe": None}),

        # ---- Top-left two squares: left = video, right = mocap HTML (square iframe) ----
        html.Div(className="card pink video1", children=[
            html.Div("Captured Motion", className="card-badge"),
            html.Div(className="video-grid", children=[
                html.Video(src=SMALL_VIDEO_A,
                            controls=True,
                            autoPlay=True,
                            loop=False,
                            muted=True,
                            className="player",),
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
                            loop=True,
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
                html.Img(id="ssp-big-left",  src="", className="square"),
                html.Img(id="ssp-big-right", src="", className="square"),
                html.Img(id="ssp-big-wide",  src="", className="wide"),
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
                    placeholder="Ask anything… Try: Task description: ...  or type lower weight",
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
    Output("scan-state", "data"),
    Output("task-state", "data"),
    Output("verdict-state", "data"),
    Input("chat-send", "n_clicks"),
    Input("chat-upload", "contents"),
    State("chat-upload", "filename"),
    State("chat-text", "value"),
    State("chat-store", "data"),
    State("show-video", "data"),
    State("scan-state", "data"),
    State("task-state", "data"),
    prevent_initial_call=True,
)
def handle_chat(n_clicks, upload_contents, upload_filename, text_value,
                history, video_state, scan_state, task_state):
    ctx = getattr(dash, "callback_context", None) or getattr(dash, "ctx", None)
    if not ctx or not ctx.triggered:
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

    history = history or []
    video_state = video_state or {"show": False, "src": ""}
    scan_state = scan_state or {"has_scan": False, "path": ""}
    task_state = task_state or {"has_task": False, "json_path": ""}
    verdict_state = {"ready": False, "safe": None}

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    print("[debug] handle_chat triggered by:", trigger_id)

    def maybe_finish_and_verdict():
        """If both flags set, compute verdict, show video, and add message."""
        nonlocal history, video_state, verdict_state
        if scan_state.get("has_scan") and task_state.get("has_task"):
            # Compute verdict from current scores
            scores = load_niosh_scores()
            verdict = is_motion_safe(scores)

            # Show the recommended motion video in bottom player
            video_state = {"show": True, "src": DEFAULT_VIDEO}

            # Academic-style messaging
            time.sleep(0.75)
            if verdict is None:
                msg = (
                    "I have both the 3D scan and task description. "
                    "However, the available metrics are incomplete for a safety decision. "
                    "Please ensure LI and the L5/S1 back force are present."
                )
                verdict_state = {"ready": True, "safe": None}
            else:
                msg = (
                    "Techniques for lifting boxes from hard-to-reach positions (e.g., back of pallets) \n"
                    "Lift with your legs, not back.\n"
                    "Bring box closer to body by:\n"
                    "   1) step on the ledge,\n"
                    "   2) straddle the box corner.\n")
                history.append({"role": "assistant", "kind": "text", "content": msg})
            if verdict:
                msg = (
                    "You can safely perform the task by following the example motion shown."
                )
                verdict_state = {"ready": True, "safe": True}
            else:
                msg = (
                    "Posture improvement alone is not sufficient (LI > 1), conduct what-if experiments: \n"
                    "   1) reduce the weight,\n"
                    "   2) increasing the lift height.\n")
                verdict_state = {"ready": True, "safe": False}
            history.append({"role": "assistant", "kind": "text", "content": msg})

    if trigger_id == "chat-upload" and upload_contents is not None:
        # Handle file upload
        if upload_filename and is_scan_file(upload_filename):
            try:
                saved_path = save_upload_to_disk(upload_contents, upload_filename)
                scan_state = {"has_scan": True, "path": saved_path}

                history.append({
                    "role": "user", "kind": "file", "content": "file", "filename": upload_filename
                })
                time.sleep(0.75)
                history.append({
                    "role": "assistant", "kind": "text",
                    "content": f"Received 3D scan of site." #\nSaved to: {saved_path}."
                })
                # Clear upload inputs
                maybe_finish_and_verdict()
                return history, no_update, None, None, video_state, scan_state, task_state, verdict_state
            except Exception as e:
                history.append({"role": "assistant", "kind": "text",
                                "content": f"Failed to save upload: {e}"})
                return history, no_update, None, None, no_update, scan_state, task_state, no_update
        else:
            # Not a recognized 3D scan
            accepted = ", ".join(sorted(SCAN_EXTS))
            history.append({
                "role": "user", "kind": "file", "content": "file", "filename": upload_filename
            })
            history.append({
                "role": "assistant", "kind": "text",
                "content": f"Sorry, I can’t process this file type. "
                           f"Please upload a 3D scan in one of the following formats: {accepted}"
            })
            return history, no_update, None, None, no_update, scan_state, task_state, no_update

    if trigger_id == "chat-send":
        user_text = (text_value or "").strip()
        if user_text == "":
            return history, no_update, no_update, no_update, no_update, no_update, no_update, no_update

        history.append({"role": "user", "kind": "text", "content": user_text})
        lowered = user_text.lower()

        # Task description typed in chat
        if lowered.startswith("task description:"):
            try:
                json_path = save_task_json(user_text)
                task_state = {"has_task": True, "json_path": json_path}
                """Lift a 10-kilogram box without handles from the floor near position (8.5, 4) in the scan. It’s a cube about 40 centimeters in each dimension."""
                sample = '''
{
"task":                "lift",
"object_type":   "box",
"handle_type":  "none",
"weight_kg":      10.0,
"size_m":           [0.4, 0.4, 0.4],
"start_h_m":      0.0,
"start_loc_m":  [8.5, 4.0]
}
'''
                time.sleep(0.75)
                history.append({
                    "role": "assistant", "kind": "text",
                    "content": f"Extracted task parameters: "
                               f""
                               f"{sample}"
                               f""
                               f"Saved to {json_path}"
                })
                # After saving task, check if we can proceed
                maybe_finish_and_verdict()
                return history, "", no_update, no_update, video_state, scan_state, task_state, verdict_state
            except Exception as e:
                history.append({"role": "assistant", "kind": "text",
                                "content": f"Could not save task description: {e}"})
                return history, "", no_update, no_update, no_update, scan_state, task_state, no_update

        # What-if: lower weight (typed)
        if "lower weight" in lowered:
            history.append({
                "role": "assistant", "kind": "text",
                "content": (
                    "What‑if experiment: **lower weight**.\n"
                    "Simulating reduced load in NIOSH and 3DSSPP… (placeholder output)."
                )
            })
            return history, "", no_update, no_update, no_update, scan_state, task_state, no_update

        # Slash-controls for video
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
        elif "increase height" in lowered:
            bot_reply = "What‑if experiment: **increase height** — not implemented."
        else:
            bot_reply = "…"
        history.append({"role": "assistant", "kind": "text", "content": bot_reply})

        return history, "", no_update, no_update, video_state, scan_state, task_state, no_update

    # Fallback
    return history, no_update, no_update, no_update, no_update, scan_state, task_state, no_update


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


# Populate score texts. Keep existing behavior (updates on any chat activity).
@app.callback(
    Output("niosh-text-small", "children"),
    Output("dsspp-text-small", "children"),
    Input("chat-store", "data")
)
def fill_score_text(_):
    n_small = format_niosh_text(load_niosh_scores(SCORE_PATH))
    d_small = format_dsspp_text(load_niosh_scores(SCORE_PATH))
    return n_small, d_small


# --- Show NIOSH & 3DSSPP texts ONLY after both flags are set and with 2.5s delay ---
@app.callback(
    Output("niosh-text-big",   "children"),
    Output("dsspp-text-big",   "children"),
    Input("verdict-state", "data"),
)
def fill_score_text_after_ready(verdict_state):
    if not verdict_state or not verdict_state.get("ready"):
        # Keep them blank until ready
        return "L4/L5 Back Compression Force = -", "L4/L5 Back Compression Force = -",
    # Delay before showing results
    time.sleep(2.5)
    n_big   = format_niosh_text(load_niosh_scores(SCORE_GENERATED_PATH))
    d_big   = format_dsspp_text(load_niosh_scores(SCORE_GENERATED_PATH))
    return n_big, d_big


# 2.5s delayed swap of bottom-row DSSPP images after verdict is ready
@app.callback(
    Output("ssp-big-left",  "src"),
    Output("ssp-big-right", "src"),
    Output("ssp-big-wide",  "src"),
    Input("verdict-state", "data"),
)
def populate_big_dsspp_images(verdict_state):
    if not verdict_state or not verdict_state.get("ready"):
        return "", "", ""  # keep blank until ready
    time.sleep(2.5)  # deliberate UX delay
    return SSPP_BIG_LEFT, SSPP_BIG_RIGHT, SSPP_BIG_WIDE


if __name__ == "__main__":
    app.run(debug=False)
"""
Task description: Lift a 10 kg, 40 cm box without handles from the floor near position (8.5, 4) in the scan
"""

"""
/Users/leyangwen/Documents/Isaac/terrain_model/scan/vicon_lab/Lab_scan.glb
"""

