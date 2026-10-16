"""Live WebSocket client test for deployed Hugging Face Space or local server.

Usage:
    python scripts/ws_live_test.py https://<username>-ola-support-agent.hf.space
    python scripts/ws_live_test.py http://localhost:7860
"""

from __future__ import annotations

import asyncio
import json
import sys
from urllib.parse import urlparse

import websockets


def convert_http_to_ws(base_url: str) -> str:
    """Converts http(s):// base URL to ws(s):// with /ws/chat path."""
    parsed = urlparse(base_url.rstrip("/"))
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc or parsed.path

    if scheme == "https":
        ws_scheme = "wss"
    elif scheme == "http":
        ws_scheme = "ws"
    elif scheme in ("ws", "wss"):
        ws_scheme = scheme
    else:
        ws_scheme = "wss" if "hf.space" in netloc else "ws"

    # Handle URL that may have been passed without scheme
    if "://" in base_url:
        host_port = parsed.netloc
    else:
        host_port = base_url.rstrip("/").replace("https://", "").replace("http://", "")

    return f"{ws_scheme}://{host_port}/ws/chat"


async def run_websocket_test(base_url: str) -> bool:
    """Connects to /ws/chat, sends two test messages, prints replies, and disconnects."""
    ws_url = convert_http_to_ws(base_url)
    print(f"[*] Connecting to WebSocket: {ws_url}")

    test_messages = [
        "What is the resolution SLA for a Sev-1 safety incident?",
        "What is the status of ticket TKT-0007?",
    ]

    try:
        async with websockets.connect(ws_url, open_timeout=15, close_timeout=10) as ws:
            print("[+] WebSocket connection established successfully!\n")

            for idx, msg in enumerate(test_messages, 1):
                print(f"[Turn {idx}] Sending query: '{msg}'")
                await ws.send(msg)

                reply_raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
                reply = json.loads(reply_raw)

                print(f"[Turn {idx}] Reply received:")
                print(f"  • Type:       {reply.get('type')}")
                print(f"  • Session ID: {reply.get('session_id')}")
                print(f"  • Latency:    {reply.get('latency_ms', 0):.2f} ms")

                data = reply.get("data", {})
                if isinstance(data, dict):
                    print(f"  • Route:      {data.get('route')}")
                    print(f"  • Answer:     {data.get('answer')}")
                print("-" * 65)

            print("[+] Closing WebSocket session cleanly...")
            await ws.close()
            print("[+] WebSocket closed gracefully. All turns PASSED!")
            return True

    except Exception as exc:
        print(f"[-] WebSocket test error: {exc}", file=sys.stderr)
        return False


def main() -> None:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:7860"
    success = asyncio.run(run_websocket_test(base_url))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
