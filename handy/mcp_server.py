import asyncio
import json
import os
import socket

from mcp.server.mcpserver import MCPServer


def _socket_path():
    return os.environ.get("HANDY_MCP_SOCKET") or f"/tmp/handy-iot-control-{os.getuid()}.sock"


def _call_handy(method, params, timeout=45.0):
    path = _socket_path()
    if not os.path.exists(path):
        return {"ok": False, "error": "Handy app is not running"}
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect(path)
            request = {"id": "mcp", "method": method, "params": params}
            sock.sendall(json.dumps(request).encode() + b"\n")
            line = sock.makefile("rb").readline()
        if not line:
            return {"ok": False, "error": "Handy app closed the connection"}
        reply = json.loads(line)
    except (OSError, ValueError, TimeoutError) as exc:
        return {"ok": False, "error": f"Could not reach the Handy app: {exc}"}
    if "error" in reply:
        return {"ok": False, "error": reply["error"]}
    result = reply.get("result")
    if not isinstance(result, dict):
        return {"ok": True, "result": result}
    result = dict(result)
    result["ok"] = True
    return result


server = MCPServer("Handy", instructions="Control the local Handy dashboard.")


@server.tool(description="Fetch upcoming calendar events loaded in the Handy dashboard.")
async def handy_calendar_events(limit: int = 20) -> dict:
    return await asyncio.to_thread(_call_handy, "calendar.upcoming", {"limit": limit}, 30.0)


@server.tool(description="Refresh the calendar in the Handy dashboard and return updated events.")
async def handy_calendar_refresh() -> dict:
    return await asyncio.to_thread(_call_handy, "calendar.refresh", {}, 60.0)


def _http_port():
    try:
        port = int(os.environ.get("HANDY_MCP_PORT", "8765"))
    except ValueError:
        port = 8765
    return max(1, min(port, 65535))


def main():
    transport = os.environ.get("HANDY_MCP_TRANSPORT", "stdio")
    if transport == "streamable-http":
        server.run(
            transport=transport,
            host=os.environ.get("HANDY_MCP_HOST", "127.0.0.1"),
            port=_http_port(),
            stateless_http=True,
        )
    else:
        server.run()


if __name__ == "__main__":
    main()
