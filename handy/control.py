import json
import os
import socket
import threading
from concurrent.futures import Future

DEFAULT_SOCKET = f"/tmp/handy-iot-control-{os.getuid()}.sock"


class ControlCommandError(Exception):
    pass


class ControlBridge:
    def __init__(self, app, socket_path=None):
        self.app = app
        self.path = os.path.abspath(
            socket_path or os.environ.get("HANDY_CONTROL_SOCKET") or DEFAULT_SOCKET
        )
        self._socket = None
        self._thread = None
        self._running = False

    def start(self):
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.bind(self.path)
        os.chmod(self.path, 0o600)
        self._socket.listen(8)
        self._socket.settimeout(0.5)
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._socket:
            self._socket.close()
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def _serve(self):
        while self._running:
            try:
                conn, _ = self._socket.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn):
        try:
            with conn:
                conn.settimeout(60)
                stream = conn.makefile("rb")
                line = stream.readline()
                stream.close()
                if not line:
                    return
                try:
                    request = json.loads(line)
                except ValueError:
                    return
                if not isinstance(request, dict):
                    return
                response = self._dispatch(request)
                conn.sendall(json.dumps(response).encode() + b"\n")
        except (OSError, ValueError, TimeoutError):
            pass

    def _dispatch(self, request):
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params")
        if params is None:
            params = {}
        if not isinstance(params, dict):
            return {"id": request_id, "error": "params must be an object"}
        future = Future()
        self.app.control_queue.put({"method": method, "params": params, "future": future})
        try:
            result = future.result(timeout=self._timeout(params))
            if isinstance(result, Future):
                result.result(timeout=self._timeout(params))
                result = self.app.mcp_calendar_payload(params)
            return {"id": request_id, "result": result}
        except TimeoutError:
            return {"id": request_id, "error": "Timed out waiting for the Handy app"}
        except (ControlCommandError, RuntimeError, OSError, ValueError, AttributeError,
                TypeError, KeyError) as exc:
            return {"id": request_id, "error": str(exc) or exc.__class__.__name__}

    def _timeout(self, params):
        try:
            timeout = float(params.get("timeout", 45))
        except (TypeError, ValueError):
            return 45.0
        return max(1.0, min(timeout, 120.0))
