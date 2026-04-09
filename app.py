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
app = Dash(__name__)
server = app.server

# ------------------------
# Constants / Defaults
# ------------------------
# Toggle: True = use video player for 3D motion, False = use HTML iframe viewer
USE_VIDEO_FOR_3D_VIEWER = True

UPLOAD_DIR = Path("assets/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SCAN_EXTS = {
    ".obj", ".stl", ".ply", ".glb", ".gltf", ".fbx",
    ".las", ".laz", ".e57", ".xyz", ".ptx", ".pts"
}


_EXP_OBJECT_MAP = {
    "exp1": "box", "exp1_v2": "box",
    "exp2": "handle", "exp2_v2": "handle",
    "exp3": "timber", "exp3_v2": "timber",
    "exp4": "bag", "exp4_v2": "bag",
}


def get_experiment_paths(exp: str) -> dict:
    """Return all asset paths for a given experiment (e.g. 'exp1')."""
    return {
        "gen_video": f"/assets/static_dash/generated/{exp}/short.mp4",
        "orig_video": f"/assets/static_dash/mocap/{exp}/input.mov",
        "mocap_html": f"/assets/static_dash/mocap/{exp}/ref_motion_render_small_hand_patched.html?v=1",
        "mocap_video": f"/assets/static_dash/mocap/{exp}/short.mov",
        "sspp_cap_left": f"/assets/static_dash/mocap/{exp}/2-2-humanoid.png",
        "sspp_cap_right": f"/assets/static_dash/mocap/{exp}/2-2-stick-side.png",
        "sspp_cap_wide": f"/assets/static_dash/mocap/{exp}/2-2-back.png",
        "sspp_gen_left": f"/assets/static_dash/generated/{exp}/1-humanoid.png",
        "sspp_gen_right": f"/assets/static_dash/generated/{exp}/1-stick-side.png",
        "sspp_gen_wide": f"/assets/static_dash/generated/{exp}/1-back.png",
        "score_gen_path": Path(f"assets/static_dash/generated/{exp}/NIOSH_score.py"),
        "score_cap_path": Path(f"assets/static_dash/mocap/{exp}/NIOSH_score.py"),
        "object_thumbnail": f"/assets/objects/{_EXP_OBJECT_MAP.get(exp, 'box')}.png",
    }


DEFAULT_PATHS = get_experiment_paths("exp1_v2")


# ------------------------
# Helpers
# ------------------------
def load_niosh_scores(path: Path, id: int = 0) -> dict:
    try:
        if not path.exists():
            return {}
        spec = importlib.util.spec_from_file_location("niosh_scores", str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        def get_item(var, idx):
            try:
                v = getattr(mod, var, None)
                if v is None:
                    return None
                return v[idx] if isinstance(v, (list, tuple)) and len(v) > idx else v
            except Exception:
                return getattr(mod, var, None)

        return {
            "SSPP_L4L5": get_item("SSPP_L4L5", id),
            "LI": get_item("LI", id),
            "RWL": get_item("RWL", id),
        }
    except Exception as e:
        print("[error] Failed to load NIOSH scores:", e)
        return {}


def format_niosh_text(scores: dict) -> str:
    """Format NIOSH scores with safe/unsafe emoji indicators.
    LI <= 1: safe (green check), 1 < LI <= 3: caution (yellow warning), LI > 3: unsafe (red X)
    """
    if not scores:
        return "NIOSH scores unavailable."

    li = scores.get('LI')
    rwl = scores.get('RWL')

    if li is not None:
        try:
            li_val = float(li)
            if li_val <= 1.0:
                li_str = f"Lifting Index (LI): {li_val:.2f}  \u2264 1 \u2705"
            elif li_val <= 3.0:
                li_str = f"Lifting Index (LI): {li_val:.2f}  > 1 \u26a0\ufe0f"
            else:
                li_str = f"Lifting Index (LI): {li_val:.2f}  > 3 \u274c"
        except (ValueError, TypeError):
            li_str = f"Lifting Index (LI): {li}"
    else:
        li_str = "Lifting Index (LI): \u2014"

    if rwl is not None:
        try:
            rwl_val = float(rwl)
            rwl_str = f"Recommended Weight Limit (RWL): {rwl_val:.2f} kg"
        except (ValueError, TypeError):
            rwl_text = str(rwl).strip()
            if not rwl_text.lower().endswith("kg"):
                rwl_text = f"{rwl_text} kg"
            rwl_str = f"Recommended Weight Limit (RWL): {rwl_text}"
    else:
        rwl_str = "Recommended Weight Limit (RWL): \u2014"

    return f"{li_str}\n{rwl_str}"


def is_scan_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in SCAN_EXTS


def save_upload_to_disk(contents: str, filename: str) -> str:
    if not contents or "," not in contents:
        raise ValueError("Invalid upload contents")
    header, b64data = contents.split(",", 1)
    raw = base64.b64decode(b64data)
    safe = "scan." + filename.split(".")[-1]
    out = UPLOAD_DIR / safe
    with open(out, "wb") as f:
        f.write(raw)
    return "/" + str(out).replace("\\", "/")


def save_task_json(raw_text: str) -> str:
    out = UPLOAD_DIR / "task.json"
    stub = {"raw": raw_text, "extracted": "xxxx"}
    out.write_text(json.dumps(stub, indent=2), encoding="utf-8")
    return "/" + str(out).replace("\\", "/")


def is_motion_safe(scores: dict) -> bool | None:
    li = scores.get("LI")
    backN = scores.get("SSPP_L4L5")
    if li is None or backN is None:
        return None
    try:
        return (float(li) <= 1.0) and (float(backN) <= 3400.0)
    except Exception:
        return None


PLACEHOLDER_SCAN = "/assets/uploads/scan_thumbnail.png"


def bubble(role, kind, content, filename=None, image_src=None, image_label=None):
    if kind == "file":
        inner = html.Div([
            html.Div("\U0001f4ce", className="file-ico"),
            html.Div([
                html.Div("File uploaded", className="file-title"),
            ], className="file-meta"),
        ], className="file-bubble")
    elif kind == "image":
        children = []
        if image_label:
            children.append(html.Div(image_label, className="img-bubble-label"))
        children.append(html.Img(src=image_src or "", className="chat-thumbnail"))
        if content:
            children.append(html.Div(content, className="msg-text", style={"padding": "4px 0 0", "box-shadow": "none"}))
        inner = html.Div(children, className="img-bubble")
    else:
        inner = html.Div(content, className="msg-text")
    return html.Div(inner, className=f"msg msg-{role}")


_PRELOADED_TASK_TEXT = {
    "exp2_v2": "Task description: Lift a 10 lbs. container w/ handle from the floor near position (8.5, 4)",
    "exp3_v2": "Task description: Lift a 3 ft long lumber from the floor near position (8.5, 4)",
    "exp4_v2": "Task description: Lift a 25 lbs.  bag from the floor near position (8.5, 4)",
}

_PRELOADED_PARAMS = {
    "exp2_v2": (
        'Extracted task parameters:\n'
        '{\n'
        '"task":                "lift",\n'
        '"weight_kg":      4.54,\n'
        '"start_h_m":      0.0,\n'
        '"start_loc_m":  [8.5, 4.0]\n'
        '"object_type":   "container w/ handle",\n'
        '}'
    ),
    "exp3_v2": (
        'Extracted task parameters:\n'
        '{\n'
        '"task":                "lift",\n'
        '"size_m":           [0.9, 0.1, 0.05],\n'
        '"start_h_m":      0.0,\n'
        '"start_loc_m":  [8.5, 4.0]\n'
        '"object_type":   "lumber",\n'
        '}'
    ),
    "exp4_v2": (
        'Extracted task parameters:\n'
        '{\n'
        '"task":                "lift",\n'
        '"weight_kg":      8.0,\n'
        '"start_h_m":      0.0,\n'
        '"start_loc_m":  [8.5, 4.0]\n'
        '"object_type":   "bag",\n'
        '}'
    ),
}

# _PRELOADED_VERDICT = {
#     # TODO: Replace placeholder verdicts with actual verdicts per scenario
#     "exp2_v2": ("Posture improvement alone is not sufficient (LI > 1), conduct what-if experiments: \n"
#                 "   1) reduce the weight,\n"
#                 "   2) increasing the lift height."),
#     "exp3_v2": ("Posture improvement alone is not sufficient (LI > 1), conduct what-if experiments: \n"
#                 "   1) reduce the weight,\n"
#                 "   2) increasing the lift height."),
#     "exp4_v2": ("Posture improvement alone is not sufficient (LI > 1), conduct what-if experiments: \n"
#                 "   1) reduce the weight,\n"
#                 "   2) increasing the lift height."),
# }


def _get_preloaded_chat(exp: str) -> list:
    """Return a preloaded chat history for scenarios 2-4."""
    paths = get_experiment_paths(exp)
    return [
        {"role": "user", "kind": "file", "content": "file", "filename": "site_scan.glb"},
        {"role": "assistant", "kind": "image", "content": "Received 3D scan of site.",
         "image_src": PLACEHOLDER_SCAN, "image_label": "3D Site Scan"},
        {"role": "user", "kind": "text",
         "content": _PRELOADED_TASK_TEXT.get(exp, "Task description: ...")},
        {"role": "assistant", "kind": "text",
         "content": _PRELOADED_PARAMS.get(exp, "Extracted task parameters: ...")},
        {"role": "assistant", "kind": "image", "content": "",
         "image_src": paths["object_thumbnail"], "image_label": "Object Model"},
        # {"role": "assistant", "kind": "text",
        #  "content": _PRELOADED_VERDICT.get(exp, "...")},
    ]


# ------------------------
# Layout
# ------------------------
app.layout = html.Div(
    className="page",
    children=[
        # Stores
        dcc.Store(id="show-video", data={"show": False, "src": ""}),
        dcc.Store(id="chat-store", data=[]),
        dcc.Store(id="scan-state", data={"has_scan": False, "path": ""}),
        dcc.Store(id="task-state", data={"has_task": False, "json_path": ""}),
        dcc.Store(id="verdict-state", data={"ready": False, "safe": None}),
        dcc.Store(id="active-experiment", data="exp1_v2"),
        # Per-tab chat memory: {exp1: [...], exp2: [...], ...}
        dcc.Store(id="chat-cache", data={
            "exp1_v2": [],
            "exp2_v2": _get_preloaded_chat("exp2_v2"),
            "exp3_v2": _get_preloaded_chat("exp3_v2"),
            "exp4_v2": _get_preloaded_chat("exp4_v2"),
        }),

        # ---- Tabs (compact, left-aligned, with + button) ----
        dcc.Tabs(
            id="experiment-tabs",
            value="exp1_v2",
            className="tab-bar",
            children=[
                dcc.Tab(label="Scenario 1", value="exp1_v2", className="tab-item", selected_className="tab-item--selected"),
                dcc.Tab(label="Scenario 2", value="exp2_v2", className="tab-item", selected_className="tab-item--selected"),
                dcc.Tab(label="Scenario 3", value="exp3_v2", className="tab-item", selected_className="tab-item--selected"),
                dcc.Tab(label="Scenario 4", value="exp4_v2", className="tab-item", selected_className="tab-item--selected"),
                dcc.Tab(label="+", value="exp-add", className="tab-item tab-item-plus", disabled=True),
            ],
        ),

        # ---- Section headers (large, black) ----
        html.Div(className="section-headers", children=[
            html.Div("Input", className="header-input"),
            html.Div(),  # spacer for divider column
            html.Div("Output", className="header-output"),
        ]),

        # ---- Main grid ----
        html.Div(className="grid-body", children=[

            # Top-left: Original motion video (no badge)
            html.Div(className="card pink no-badge orig-video-area", children=[
                html.Video(
                    id="orig-video",
                    src=DEFAULT_PATHS["orig_video"],
                    controls=False,
                    autoPlay=True,
                    loop=False,
                    muted=True,
                    className="player",
                ),
            ]),

            # Top-right: Merged — 3D motion + Captured scores
            html.Div(className="card pink top-output-area", children=[
                html.Div("Current Task Motion", className="card-badge"),
                html.Div(className="output-inner-split", children=[
                    html.Div(className="media-pane", children=[
                        html.Video(
                            id="viewport-video",
                            src=DEFAULT_PATHS["mocap_video"],
                            controls=False,
                            autoPlay=True,
                            loop=False,
                            muted=True,
                            className="player motion-video",
                        ) if USE_VIDEO_FOR_3D_VIEWER else
                        html.Div(className="iframe-frame", children=[
                            html.Iframe(
                                id="viewport-iframe",
                                src=DEFAULT_PATHS["mocap_html"],
                                className="viewport-iframe",
                            )
                        ]),
                    ]),
                    html.Div(className="scores-content scores-pane", children=[
                        html.H4("NIOSH Lifting Equation", className="score-heading"),
                        html.Pre(id="niosh-text-captured", className="score-pre"),
                        html.H4("3D SSPP", className="score-heading"),
                        html.Img(id="cap-sspp-wide", src=DEFAULT_PATHS["sspp_cap_wide"], className="ssp-back-img"),
                        html.Div(className="ssp-grid", children=[
                            html.Img(id="cap-sspp-left", src=DEFAULT_PATHS["sspp_cap_left"], className="ssp-img"),
                            html.Img(id="cap-sspp-right", src=DEFAULT_PATHS["sspp_cap_right"], className="ssp-img"),
                        ]),
                    ]),
                ]),
            ]),

            # Vertical divider between input and output (rendered via CSS)

            # Bottom-left: Chat
            html.Div(className="card chatbox-area", children=[
                html.Div(id="chat-history", className="chat-history"),
                html.Div(className="chat-input-row", children=[
                    dcc.Upload(
                        id="chat-upload",
                        multiple=False,
                        children=html.Div([
                            html.Span("\uff0b", className="upload-plus"),
                        ], className="upload-area"),
                    ),
                    dcc.Textarea(
                        id="chat-text",
                        placeholder="Try: Task description: ... ",
                        className="chat-textarea",
                        maxLength=4000,
                    ),
                    html.Button("Send", id="chat-send", n_clicks=0, className="chat-send-btn"),
                ]),
            ]),

            # Bottom-right: Merged — Generated video + Generated scores
            html.Div(className="card green bot-output-area", children=[
                html.Div("Generated Intervention", className="card-badge"),
                html.Div(className="output-inner-split", children=[
                    html.Div(className="media-pane", children=[
                        dcc.Loading(
                            id="video-loading",
                            type="circle",
                            children=html.Div(
                                id="video-stage",
                                children=[
                                    html.Video(
                                        id="player",
                                        src="",
                                        controls=False,
                                        autoPlay=False,
                                        loop=False,
                                        muted=True,
                                        preload="auto",
                                        className="player motion-video",
                                    ),
                                ],
                            ),
                        ),
                    ]),
                    html.Div(className="scores-content scores-pane", children=[
                        html.H4("NIOSH Lifting Equation", className="score-heading"),
                        html.Pre(id="niosh-text-generated", className="score-pre"),
                        html.H4("3D SSPP", className="score-heading"),
                        html.Img(id="gen-sspp-wide", src="", className="ssp-back-img"),
                        html.Div(className="ssp-grid", children=[
                            html.Img(id="gen-sspp-left", src="", className="ssp-img"),
                            html.Img(id="gen-sspp-right", src="", className="ssp-img"),
                        ]),
                    ]),
                ]),
            ]),
        ]),
    ],
)


# ------------------------
# Callbacks
# ------------------------

# Unified content callback: updates everything on tab switch or verdict
_viewer_output_id = "viewport-video" if USE_VIDEO_FOR_3D_VIEWER else "viewport-iframe"

@app.callback(
    Output("orig-video", "src"),
    Output(_viewer_output_id, "src"),
    Output("cap-sspp-left", "src"),
    Output("cap-sspp-right", "src"),
    Output("cap-sspp-wide", "src"),
    Output("niosh-text-captured", "children"),
    Output("player", "src"),
    Output("gen-sspp-left", "src"),
    Output("gen-sspp-right", "src"),
    Output("gen-sspp-wide", "src"),
    Output("niosh-text-generated", "children"),
    Output("active-experiment", "data"),
    Input("experiment-tabs", "value"),
    Input("verdict-state", "data"),
)
def update_all_content(tab_value, verdict_state):
    paths = get_experiment_paths(tab_value)

    # Captured side: always visible
    cap_scores = load_niosh_scores(paths["score_cap_path"])

    # Viewer source depends on toggle
    viewer_src = paths["mocap_video"] if USE_VIDEO_FOR_3D_VIEWER else paths["mocap_html"]

    # For scenarios 2-4, always show generated results
    is_preloaded = tab_value in ("exp2_v2", "exp3_v2", "exp4_v2")

    if is_preloaded or (verdict_state and verdict_state.get("ready")):
        gen_scores = load_niosh_scores(paths["score_gen_path"])
        gen_video = paths["gen_video"]
        gen_sspp = (paths["sspp_gen_left"], paths["sspp_gen_right"], paths["sspp_gen_wide"])
        niosh_gen = format_niosh_text(gen_scores)
    else:
        gen_video = ""
        gen_sspp = ("", "", "")
        niosh_gen = ""

    return (
        paths["orig_video"],
        viewer_src,
        paths["sspp_cap_left"], paths["sspp_cap_right"], paths["sspp_cap_wide"],
        format_niosh_text(cap_scores),
        gen_video,
        *gen_sspp,
        niosh_gen,
        tab_value,
    )


# Save current chat to cache when leaving a tab, load cached chat for new tab
@app.callback(
    Output("chat-store", "data", allow_duplicate=True),
    Output("chat-cache", "data"),
    Input("experiment-tabs", "value"),
    State("chat-store", "data"),
    State("chat-cache", "data"),
    State("active-experiment", "data"),
    prevent_initial_call=True,
)
def switch_tab_chat(new_tab, current_chat, cache, prev_tab):
    # Save current chat to cache under the previous tab
    cache = cache or {}
    if prev_tab:
        cache[prev_tab] = current_chat or []

    # Load cached chat for the new tab
    new_chat = cache.get(new_tab, [])

    return new_chat, cache


# Chat handler
@app.callback(
    Output("chat-store", "data"),
    Output("chat-text", "value"),
    Output("chat-upload", "contents"),
    Output("chat-upload", "filename"),
    Output("show-video", "data"),
    Output("scan-state", "data"),
    Output("task-state", "data"),
    Output("verdict-state", "data"),
    Output("chat-cache", "data", allow_duplicate=True),
    Input("chat-send", "n_clicks"),
    Input("chat-upload", "contents"),
    State("chat-upload", "filename"),
    State("chat-text", "value"),
    State("chat-store", "data"),
    State("show-video", "data"),
    State("scan-state", "data"),
    State("task-state", "data"),
    State("active-experiment", "data"),
    State("chat-cache", "data"),
    prevent_initial_call=True,
)
def handle_chat(n_clicks, upload_contents, upload_filename, text_value,
                history, video_state, scan_state, task_state, active_exp, cache):
    ctx = getattr(dash, "callback_context", None) or getattr(dash, "ctx", None)
    if not ctx or not ctx.triggered:
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

    history = history or []
    video_state = video_state or {"show": False, "src": ""}
    scan_state = scan_state or {"has_scan": False, "path": ""}
    task_state = task_state or {"has_task": False, "json_path": ""}
    cache = cache or {}
    verdict_state = {"ready": False, "safe": None}
    active_exp = active_exp or "exp1_v2"
    paths = get_experiment_paths(active_exp)

    def _save_and_return(hist, text_val, upl_c, upl_f, vid, scan, task, verd):
        """Save chat to cache for the active tab, then return all 9 outputs."""
        cache[active_exp] = hist if hist is not no_update else (history or [])
        return hist, text_val, upl_c, upl_f, vid, scan, task, verd, cache

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # Verdict is now handled by a separate chained callback (generate_verdict)
    # to allow the loading spinner to show between steps

    if trigger_id == "chat-upload" and upload_contents is not None:
        if upload_filename and is_scan_file(upload_filename):
            try:
                saved_path = save_upload_to_disk(upload_contents, upload_filename)
                scan_state = {"has_scan": True, "path": saved_path}
                history.append({"role": "user", "kind": "file", "content": "file", "filename": upload_filename})
                time.sleep(0.75)
                history.append({"role": "assistant", "kind": "image", "content": "Received 3D scan of site.",
                                "image_src": PLACEHOLDER_SCAN, "image_label": "3D Site Scan"})
                return _save_and_return(history, no_update, None, None, video_state, scan_state, task_state, verdict_state)
            except Exception as e:
                history.append({"role": "assistant", "kind": "text", "content": f"Failed to save upload: {e}"})
                return _save_and_return(history, no_update, None, None, no_update, scan_state, task_state, no_update)
        else:
            accepted = ", ".join(sorted(SCAN_EXTS))
            history.append({"role": "user", "kind": "file", "content": "file", "filename": upload_filename})
            history.append({"role": "assistant", "kind": "text",
                            "content": f"Sorry, I can't process this file type. "
                                       f"Please upload a 3D scan in one of the following formats: {accepted}"})
            return _save_and_return(history, no_update, None, None, no_update, scan_state, task_state, no_update)

    if trigger_id == "chat-send":
        user_text = (text_value or "").strip()
        if user_text == "":
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

        history.append({"role": "user", "kind": "text", "content": user_text})
        lowered = user_text.lower()

        if lowered.startswith("task description:"):
            try:
                json_path = save_task_json(user_text)
                task_state = {"has_task": True, "json_path": json_path}
                sample = '''
{
"task":                "lift",
"weight_kg":      9.07,
"start_h_m":      0.0,
"start_loc_m":  [8.5, 4.0],
"object_type":   "container",
}
'''
                time.sleep(0.75)
                history.append({
                    "role": "assistant", "kind": "text",
                    "content": f"Extracted task parameters: {sample}Saved to {json_path}"
                })
                # Show object model thumbnail
                exp_paths = get_experiment_paths(active_exp or "exp1_v2")
                history.append({
                    "role": "assistant", "kind": "image", "content": "",
                    "image_src": exp_paths["object_thumbnail"], "image_label": "Object Model"
                })
                return _save_and_return(history, "", no_update, no_update, video_state, scan_state, task_state, verdict_state)
            except Exception as e:
                history.append({"role": "assistant", "kind": "text",
                                "content": f"Could not save task description: {e}"})
                return _save_and_return(history, "", no_update, no_update, no_update, scan_state, task_state, no_update)

        if "lower weight" in lowered:
            history.append({
                "role": "assistant", "kind": "text",
                "content": "What-if experiment: **lower weight**.\n"
                           "Simulating reduced load in NIOSH and 3D SSPP\u2026 (placeholder output)."
            })
            return _save_and_return(history, "", no_update, no_update, no_update, scan_state, task_state, no_update)

        m = re.search(r"(?:^|\s)/(?:play|video)(?:\s+(.+))?$", user_text, flags=re.IGNORECASE)
        if m:
            candidate = (m.group(1) or "").strip()
            if candidate == "":
                src = paths["gen_video"]
            elif candidate.startswith("/assets/"):
                src = candidate
            elif candidate.startswith("assets/"):
                src = "/" + candidate
            else:
                src = f"/assets/static_dash/mocap/{active_exp}/{candidate}"
            video_state = {"show": True, "src": src}
            bot_reply = f"Playing: {src}"
        elif any(k in lowered for k in ("/hide", "/stop", "hide video", "stop video")):
            video_state = {"show": False, "src": video_state.get("src", "")}
            bot_reply = "Video hidden."
        elif "increase height" in lowered:
            bot_reply = "What-if experiment: **increase height** \u2014 not implemented."
        else:
            bot_reply = "\u2026"
        history.append({"role": "assistant", "kind": "text", "content": bot_reply})
        return _save_and_return(history, "", no_update, no_update, video_state, scan_state, task_state, no_update)

    return _save_and_return(history, no_update, no_update, no_update, no_update, scan_state, task_state, no_update)


@app.callback(
    Output("chat-history", "children"),
    Input("chat-store", "data")
)
def render_history(history):
    history = history or []
    return [
        bubble(
            role=msg.get("role", "user"),
            kind=msg.get("kind", "text"),
            content=msg.get("content", ""),
            filename=msg.get("filename"),
            image_src=msg.get("image_src"),
            image_label=msg.get("image_label"),
        )
        for msg in history
    ]


# Chained callback: when both scan and task are ready, show spinner then set verdict
@app.callback(
    Output("verdict-state", "data", allow_duplicate=True),
    Output("video-stage", "children"),
    Input("scan-state", "data"),
    Input("task-state", "data"),
    State("active-experiment", "data"),
    prevent_initial_call=True,
)
def generate_verdict(scan_state, task_state, active_exp):
    if not scan_state or not scan_state.get("has_scan"):
        return no_update, no_update
    if not task_state or not task_state.get("has_task"):
        return no_update, no_update

    active_exp = active_exp or "exp1_v2"
    paths = get_experiment_paths(active_exp)

    # This sleep triggers the dcc.Loading spinner on video-stage
    time.sleep(1.7)

    # Return the verdict and re-create the video element with the src set
    verdict = {"ready": True, "safe": True}
    video_el = html.Video(
        id="player",
        src=paths["gen_video"],
        controls=False,
        autoPlay=False,
        loop=False,
        muted=True,
        preload="auto",
        className="player motion-video",
    )
    return verdict, video_el


# Auto-scroll chat to bottom whenever messages update
app.clientside_callback(
    """
    function(children) {
        var el = document.getElementById('chat-history');
        if (el) {
            setTimeout(function() { el.scrollTop = el.scrollHeight; }, 50);
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("chat-history", "id"),
    Input("chat-history", "children"),
)


# For scenarios 2-4: pause generated video, play it after mocap video ends
app.clientside_callback(
    """
    function(activeExp, genSrc) {
        var mocap = document.getElementById('viewport-video');
        var gen = document.getElementById('player');
        if (!mocap || !gen) return window.dash_clientside.no_update;

        var isScenario1 = (activeExp === 'exp1_v2');
        var hasGenSrc = gen.src && !gen.src.endsWith('/');

        // Clean up previous listener
        if (mocap._onEndedHandler) {
            mocap.removeEventListener('ended', mocap._onEndedHandler);
            mocap._onEndedHandler = null;
        }

        if (isScenario1 && hasGenSrc) {
            // Scenario 1: autoplay generated video immediately when src is set
            gen.currentTime = 0;
            gen.play().catch(function(){});
        } else if (!isScenario1 && hasGenSrc) {
            // Scenarios 2-4: pause generated video, play after mocap ends
            gen.pause();
            gen.currentTime = 0;
            mocap._onEndedHandler = function() {
                gen.currentTime = 0;
                gen.play().catch(function(){});
            };
            mocap.addEventListener('ended', mocap._onEndedHandler);
        }

        return window.dash_clientside.no_update;
    }
    """,
    Output("orig-video", "id"),
    Input("active-experiment", "data"),
    Input("player", "src"),
)


if __name__ == "__main__":
    app.run(debug=False)
"""
Task description: Lift a 20lbs. container from the floor near position (8.5, 4)
"""
