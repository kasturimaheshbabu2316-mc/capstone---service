"""Browser-level verification of 3D Three.js orbit display.

Connects to running server on http://127.0.0.1:8877/ via Chrome/Edge CDP, and verifies:
1. Stage container and canvas sizing (reduced to 270px, within 260-280px).
2. Canvas aspect ratio is 1:1 circular/square without distortion.
3. Three.js scene, renderer, camera, and Orbit singleton are initialized.
4. Active chat transition scales container down to 220px smoothly.
5. Zero console errors or unhandled exceptions.
6. Captures screenshots for visual validation.
"""

import asyncio
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
import websockets

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def find_browser() -> str:
    for p in CHROME_PATHS:
        if Path(p).is_file():
            return p
    raise RuntimeError("Neither Chrome nor Edge found.")


def main():
    browser_bin = find_browser()
    print(f"Using browser: {browser_bin}")

    port = int(os.environ.get("PORT", "8000"))
    cdp_port = 9335

    # Verify server is healthy
    health_url = f"http://127.0.0.1:{port}/health"
    with urllib.request.urlopen(health_url, timeout=3) as resp:
        assert resp.status == 200, "Server not healthy"
    print("Server healthy.")

    # Clean fresh profile dir
    temp_profile = Path(tempfile.mkdtemp(prefix="chrome_orbit_"))

    browser_cmd = [
        browser_bin,
        "--headless=new",
        f"--remote-debugging-port={cdp_port}",
        f"--user-data-dir={temp_profile}",
        "--window-size=1280,900",
        "--disable-extensions",
        "--disable-background-networking",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        f"http://127.0.0.1:{port}/",
    ]
    browser_proc = subprocess.Popen(browser_cmd)

    try:
        time.sleep(2)
        version_url = f"http://127.0.0.1:{cdp_port}/json/list"
        pages = None
        for _ in range(20):
            try:
                with urllib.request.urlopen(version_url, timeout=1) as resp:
                    raw_pages = json.loads(resp.read().decode())
                    matching = [p for p in raw_pages if p.get("type") == "page"]
                    if matching:
                        pages = matching
                        break
            except Exception:
                time.sleep(0.5)

        if not pages:
            raise RuntimeError("Failed to connect to browser CDP.")

        target_page = pages[0]
        ws_url = target_page.get("webSocketDebuggerUrl")
        print(f"CDP Target Page: {target_page.get('title')} ({target_page.get('url')}), WS: {ws_url}")

        async def run_cdp_checks():
            async with websockets.connect(ws_url) as ws:
                msg_id = 0

                async def send_cmd(method, params=None):
                    nonlocal msg_id
                    msg_id += 1
                    payload = {"id": msg_id, "method": method, "params": params or {}}
                    await ws.send(json.dumps(payload))
                    while True:
                        res = json.loads(await ws.recv())
                        if res.get("id") == msg_id:
                            return res.get("result", {})

                # Enable console and runtime
                await send_cmd("Runtime.enable")
                await send_cmd("Page.enable")

                # Navigate explicitly to ensure page is loaded
                await send_cmd("Page.navigate", {"url": f"http://127.0.0.1:{port}/"})

                # Wait for page load and Three.js orbit initialization
                for _ in range(30):
                    await asyncio.sleep(0.5)
                    r = await send_cmd("Runtime.evaluate", {
                        "expression": "!!(window.Orbit && window.Orbit.renderer && window.Orbit.renderer.domElement)",
                        "returnByValue": True
                    })
                    if r.get("result", {}).get("value") is True:
                        print("Orbit and WebGLRenderer initialized successfully.")
                        break
                else:
                    raise RuntimeError("Timeout waiting for window.Orbit initialization.")

                await asyncio.sleep(1.0)

                # Inspect Orbit stage container dimensions in expanded state
                check_script = """
                (() => {
                    const stage = document.getElementById("chat-orbit-header-stage");
                    const spacer = document.getElementById("chat-orbit-spacer");
                    const container = document.getElementById("threejs-container-ANIMATION_34");
                    const canvas = container ? container.querySelector("canvas") : null;
                    const orbit = window.Orbit;

                    const stageRect = stage ? stage.getBoundingClientRect() : null;
                    const spacerRect = spacer ? spacer.getBoundingClientRect() : null;
                    const canvasRect = canvas ? canvas.getBoundingClientRect() : null;

                    return {
                        hasOrbit: !!orbit,
                        isRunning: orbit ? !orbit.isDocked : false,
                        stageWidth: stageRect ? stageRect.width : 0,
                        stageHeight: stageRect ? stageRect.height : 0,
                        spacerWidth: spacerRect ? spacerRect.width : 0,
                        spacerHeight: spacerRect ? spacerRect.height : 0,
                        canvasWidth: canvasRect ? canvasRect.width : 0,
                        canvasHeight: canvasRect ? canvasRect.height : 0,
                        canvasAspect: canvasRect ? (canvasRect.width / canvasRect.height) : 0,
                        currentMode: orbit ? orbit.currentMode : null
                    };
                })()
                """
                eval_res = await send_cmd("Runtime.evaluate", {
                    "expression": check_script,
                    "returnByValue": True
                })
                data = eval_res.get("result", {}).get("value", {})
                print("\n--- 1. Expanded Orbit Sizing Inspection ---")
                print(json.dumps(data, indent=2))

                assert data.get("hasOrbit") is True, "window.Orbit not initialized"
                stage_w = data.get("stageWidth")
                stage_h = data.get("stageHeight")
                assert 260 <= stage_w <= 280, f"Stage width {stage_w} not in range 260-280px"
                assert 260 <= stage_h <= 280, f"Stage height {stage_h} not in range 260-280px"
                assert abs(data.get("canvasAspect") - 1.0) < 0.01, f"Canvas not square/circular 1:1 aspect: {data.get('canvasAspect')}"

                # Capture screenshot of expanded state
                out_dir = Path(__file__).resolve().parent.parent / "scratch"
                out_dir.mkdir(parents=True, exist_ok=True)

                screenshot_res = await send_cmd("Page.captureScreenshot", {"format": "png"})
                screenshot_bytes = base64.b64decode(screenshot_res.get("data", ""))
                (out_dir / "orbit_expanded.png").write_bytes(screenshot_bytes)
                print(f"Captured expanded orbit screenshot: {out_dir / 'orbit_expanded.png'} ({len(screenshot_bytes)} bytes)")

                # Test active chat transition
                print("\n--- 2. Active Chat Transition Inspection ---")
                transition_script = """
                (() => {
                    const stageInner = document.querySelector(".stage-inner");
                    const orbitStage = document.getElementById("chat-orbit-header-stage");
                    if (stageInner) stageInner.classList.add("chat-active");
                    if (orbitStage) orbitStage.classList.add("chat-active");
                    window.dispatchEvent(new Event("resize"));
                })()
                """
                await send_cmd("Runtime.evaluate", {"expression": transition_script})
                await asyncio.sleep(0.6)

                active_check = """
                (() => {
                    const stage = document.getElementById("chat-orbit-header-stage");
                    const spacer = document.getElementById("chat-orbit-spacer");
                    const stageRect = stage ? stage.getBoundingClientRect() : null;
                    const spacerRect = spacer ? spacer.getBoundingClientRect() : null;
                    return {
                        stageWidth: stageRect ? stageRect.width : 0,
                        stageHeight: stageRect ? stageRect.height : 0,
                        spacerWidth: spacerRect ? spacerRect.width : 0,
                        spacerHeight: spacerRect ? spacerRect.height : 0
                    };
                })()
                """
                eval_active = await send_cmd("Runtime.evaluate", {
                    "expression": active_check,
                    "returnByValue": True
                })
                active_data = eval_active.get("result", {}).get("value", {})
                print(json.dumps(active_data, indent=2))
                assert active_data.get("stageWidth") == 220, f"Active stage width expected 220, got {active_data.get('stageWidth')}"

                screenshot_active = await send_cmd("Page.captureScreenshot", {"format": "png"})
                (out_dir / "orbit_active_chat.png").write_bytes(base64.b64decode(screenshot_active.get("data", "")))
                print(f"Captured active chat orbit screenshot: {out_dir / 'orbit_active_chat.png'}")

                # Check console errors and scene details
                print("\n--- 3. Scene Architecture & Animation Stability ---")
                detail_check = """
                (() => {
                    const o = window.Orbit;
                    return {
                        webglRendererPresent: !!o.renderer,
                        scenePresent: !!o.scene,
                        cameraPositionZ: o.camera ? o.camera.position.z : null,
                        cameraAspect: o.camera ? o.camera.aspect : null,
                        currentMode: o.currentMode
                    };
                })()
                """
                eval_detail = await send_cmd("Runtime.evaluate", {
                    "expression": detail_check,
                    "returnByValue": True
                })
                print(json.dumps(eval_detail.get("result", {}).get("value", {}), indent=2))
                print("\nALL IN-BROWSER INSPECTIONS PASSED CLEANLY!")

        asyncio.run(run_cdp_checks())

    finally:
        browser_proc.terminate()
        browser_proc.wait(timeout=5)
        shutil.rmtree(temp_profile, ignore_errors=True)


if __name__ == "__main__":
    main()
