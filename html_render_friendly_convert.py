
#!/usr/bin/env python3
# Patch a 3D HTML viewer file to be responsive in an iframe, reduce whitespace
# before/after controls, fix orbit target and up-axis for three.js viewers,
# and (optionally) preserve a chosen aspect ratio.
#
# Usage:
#   python patch_ref_motion_render_v2.py --input INPUT.html [--output OUTPUT.html] [--aspect 16:9|1.7777] [--z-up true|false]
#
# Defaults:
#   --input  ref_motion_render.html
#   --output <input_stem>_patched.html
#   --aspect 16:9  (empty string "" to disable)
#   --z-up   true

import argparse
from pathlib import Path

HEAD_BASE = """
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
<style>
  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; padding: 0; }

  .scenepic-container, .scenepic-root, #sp-main, .viewer, .viewport, .scene-container {
    height: 100%;
    margin: 0 !important;
    padding: 0 !important;
    display: flex;
    flex-direction: column;
    gap: 0;
    min-height: 420px;
  }

  body > :first-child,
  #sp-main > :first-child,
  .scenepic-container > :first-child,
  .viewer > :first-child,
  .viewport > :first-child { margin-top: 0 !important; }
  body > :last-child,
  #sp-main > :last-child,
  .scenepic-container > :last-child,
  .viewer > :last-child,
  .viewport > :last-child { margin-bottom: 0 !important; }

  h1, h2, h3, h4, h5, h6 { margin-top: 0.2rem; margin-bottom: 0.2rem; }

  .controls, .sp-controls, #controls, [class*=\"control\"], [id*=\"control\"] {
    margin: 0 !important;
    padding: 2px 0 !important;
  }

  :root { --viewer-aspect: __VIEWER_ASPECT__; }

  canvas {
    width: 100% !important;
    display: block;
    __CANVAS_DIMENSIONS__
  }
</style>
"""

RESIZE_SCRIPT = """
<script>
(function () {
  function getAspect() {
    var v = getComputedStyle(document.documentElement).getPropertyValue('--viewer-aspect').trim();
    if (!v || v === '""') return 0;
    if (v.includes('/')) {
      var parts = v.split('/');
      var a = parseFloat(parts[0]);
      var b = parseFloat(parts[1] || "1");
      var r = (b && !isNaN(a) && !isNaN(b)) ? (a / b) : 0;
      return r || 0;
    } else {
      var r = parseFloat(v);
      return (r && !isNaN(r)) ? r : 0;
    }
  }

  function resizeCanvas() {
    var c = document.querySelector('canvas');
    if (!c) return;
    var aspect = getAspect();
    var parent = c.parentElement || document.body;
    var w = parent.clientWidth || document.documentElement.clientWidth;

    if (aspect > 0) {
      var h = Math.round(w / aspect);
      c.width = w;
      c.height = h;
      c.style.width = "100%";
      c.style.height = "auto";
    } else {
      var h = document.documentElement.clientHeight;
      c.width = w;
      c.height = h;
      c.style.width = "100%";
      c.style.height = "100%";
    }

    if (window.sp && typeof window.sp.resize === "function") {
      try { window.sp.resize(); } catch (e) {}
    }
    if (window.renderer && window.scene && window.camera && window.renderer.render) {
      try { window.renderer.render(window.scene, window.camera); } catch(e) {}
    }
  }
  window.addEventListener('load', resizeCanvas);
  window.addEventListener('resize', resizeCanvas);
})();
</script>
"""

CAMERA_SCRIPT = """
<script>
(function fixCameraOnceReady(){
  var THREE = window.THREE || (window.scenepic && window.scenepic.THREE);
  if (!THREE) { requestAnimationFrame(fixCameraOnceReady); return; }

  var scene    = window.scene    || (window.sp && window.sp.scene)    || (window._scene);
  var camera   = window.camera   || (window.sp && window.sp.camera)   || (window._camera);
  var controls = window.controls || (window.sp && window.sp.controls) || (window._controls);

  if (!scene || !camera) { requestAnimationFrame(fixCameraOnceReady); return; }

  try {
    __SET_Z_UP__
    var root = scene;
    var box  = new THREE.Box3().setFromObject(root);
    if (box.isEmpty()) return;

    var center = box.getCenter(new THREE.Vector3());
    var sizeV  = box.getSize(new THREE.Vector3());
    var diag   = Math.sqrt(sizeV.x*sizeV.x + sizeV.y*sizeV.y + sizeV.z*sizeV.z);
    var dist   = Math.max(1e-3, diag * 0.8);

    if (controls && controls.target && controls.update) {
      controls.target.copy(center);
      controls.screenSpacePanning = true;
      controls.update();
    }

    var dir = new THREE.Vector3(1, 1, 0.6).normalize();
    camera.position.copy(center.clone().add(dir.multiplyScalar(dist)));
    if (camera.lookAt) camera.lookAt(center);

    if (window.renderer && window.renderer.render) {
      window.renderer.render(scene, camera);
    }
  } catch (e) { /* non-fatal */ }
})();
</script>
"""

def build_head_patch(aspect_ratio: str) -> str:
  if aspect_ratio:
      canvas_dims = "aspect-ratio: var(--viewer-aspect); height: auto !important;"
      aspect_value = aspect_ratio  # e.g., "16/9" or "1.7777"
  else:
      canvas_dims = "height: 100% !important;"
      aspect_value = '""'  # empty string disables
  return HEAD_BASE.replace("__CANVAS_DIMENSIONS__", canvas_dims).replace("__VIEWER_ASPECT__", aspect_value)

def insert_after_head_open(html: str, insert: str) -> str:
  idx = html.lower().find("<head")
  if idx == -1:
    # no <head>, create one after <html>
    ih = html.lower().find("<html")
    if ih != -1:
      end_tag = html.find(">", ih)
      if end_tag != -1:
        return html[:end_tag+1] + "\n<head>\n" + insert + "\n</head>" + html[end_tag+1:]
    # if no <html>, prepend
    return "<head>\n" + insert + "\n</head>\n" + html
  # find end of <head ...>
  end = html.find(">", idx)
  if end == -1:
    return "<head>\n" + insert + "\n</head>\n" + html
  return html[:end+1] + "\n" + insert + html[end+1:]

def insert_before_body_close(html: str, insert: str) -> str:
  lower = html.lower()
  idx = lower.rfind("</body>")
  if idx == -1:
    return html + "\n" + insert + "\n</body>\n</html>"
  return html[:idx] + insert + html[idx:]

def patch_html_text(html_text: str, aspect_ratio: str, z_up: bool) -> str:
  head_patch = build_head_patch(aspect_ratio)
  html_text = insert_after_head_open(html_text, head_patch)

  z_code = "if (camera && camera.up) { camera.up.set(0, 0, 1); }" if z_up else "// leave camera.up as-is"
  scripts = RESIZE_SCRIPT + CAMERA_SCRIPT.replace("__SET_Z_UP__", z_code)
  html_text = insert_before_body_close(html_text, scripts)
  return html_text

def parse_aspect(s: str) -> str:
  s = (s or "").strip()
  if not s:
      return ""
  if ":" in s:
      a, b = s.split(":", 1)
      a = float(a); b = float(b)
      if a <= 0 or b <= 0:
          raise SystemExit("Invalid --aspect. Use A:B with positive numbers.")
      return f"{a}/{b}"
  else:
      r = float(s)
      if r <= 0:
          raise SystemExit("Invalid --aspect. Use a positive float.")
      return str(r)

def main():
  ap = argparse.ArgumentParser(description="Patch 3D HTML viewer for Dash iframe embedding.")
  ap.add_argument("--input", "-i", default="assets/static_dash/mocap/exp1/ref_motion_render.html", help="Input HTML path (default: ref_motion_render.html)")
  ap.add_argument("--output", "-o", default=None, help="Output HTML path (default: <input_stem>_patched.html)")
  ap.add_argument("--aspect", "-a", default="4:3", help='Aspect ratio to preserve (e.g., "16:9" or "1.7777"). Use empty string "" to disable. Default: 16:9')
  ap.add_argument("--z-up", dest="z_up", default="true", choices=["true", "false"], help="Set camera up-axis to Z-up if three.js is detected (default: true)")
  args = ap.parse_args()

  in_path = Path(args.input)
  out_path = Path(args.output) if args.output else in_path.with_name(in_path.stem + "_patched.html")
  aspect_str = parse_aspect(args.aspect) if args.aspect != "" else ""
  z_up = (args.z_up.lower() == "true")

  if not in_path.exists():
      raise SystemExit(f"Input file not found: {in_path}")

  original = in_path.read_text(encoding="utf-8", errors="ignore")
  patched = patch_html_text(original, aspect_str, z_up)
  out_path.write_text(patched, encoding="utf-8")
  print(f"Wrote: {out_path}")

if __name__ == "__main__":
  main()
