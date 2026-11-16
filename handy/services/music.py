import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from io import BytesIO
from pathlib import Path

import pygame
import requests

from ..tasks import Tasks


class MusicError(Exception):
    pass


def find_tool(name):
    candidate = Path(sys.executable).with_name(name)
    if candidate.exists():
        return str(candidate)
    return shutil.which(name)


def search(query, limit=20):
    tool = find_tool("yt-dlp")
    if not tool:
        raise MusicError("yt-dlp is not installed")
    command = [
        tool,
        f"ytsearch{max(1, limit)}:{query}",
        "--flat-playlist",
        "--dump-single-json",
        "--no-warnings",
        "--ignore-errors",
        "--skip-download",
        "--no-progress",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    except subprocess.TimeoutExpired:
        raise MusicError("Search timed out")
    except OSError as exc:
        raise MusicError(str(exc))
    if not result.stdout.strip():
        message = result.stderr.strip().splitlines()
        raise MusicError(message[-1] if message else "Search failed")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise MusicError("Unexpected response from YouTube")
    entries = payload.get("entries") or []
    results = []
    for entry in entries:
        video_id = entry.get("id")
        if not video_id:
            continue
        title = entry.get("title") or "(Untitled)"
        uploader = entry.get("uploader") or entry.get("channel") or ""
        duration = entry.get("duration")
        if not isinstance(duration, (int, float)):
            duration = None
        results.append({
            "id": video_id,
            "title": title,
            "uploader": uploader,
            "duration": duration,
            "thumbnail": f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg",
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "live": bool(entry.get("is_live")),
        })
    return results


class Player:
    def __init__(self, volume=70):
        self.volume = int(max(0, min(100, volume)))
        self.socket_path = f"/tmp/handy-iot-mpv-{os.getpid()}.sock"
        self.process = None
        self.title = ""
        self.state = {
            "playing": False,
            "paused": False,
            "position": 0.0,
            "duration": 0.0,
            "title": "",
            "loading": False,
            "error": None,
        }
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._media_loaded = False
        self._started = False
        self._deadline = 0.0
        self._finished = False
        self._failed = False

    def available(self):
        return find_tool("mpv") is not None

    def start(self):
        if self.process is not None and self.process.poll() is None:
            return
        mpv = find_tool("mpv")
        if not mpv:
            raise MusicError("mpv is not installed")
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except OSError:
                pass
        ytdl = find_tool("yt-dlp")
        env = os.environ.copy()
        if ytdl:
            env["PATH"] = str(Path(ytdl).parent) + os.pathsep + env.get("PATH", "")
        command = [
            mpv,
            "--no-video",
            "--idle=yes",
            "--force-window=no",
            "--really-quiet",
            "--no-terminal",
            "--audio-display=no",
            f"--input-ipc-server={self.socket_path}",
            f"--volume={self.volume}",
            "--ytdl-format=bestaudio/best",
            "--cache=yes",
            "--demuxer-max-bytes=64MiB",
        ]
        if ytdl:
            command.append(f"--script-opts=ytdl_hook-ytdl_path={ytdl}")
        try:
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
            )
        except OSError as exc:
            raise MusicError(str(exc))
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            if os.path.exists(self.socket_path):
                break
            if self.process.poll() is not None:
                raise MusicError("mpv failed to start")
            time.sleep(0.05)
        self._stop.clear()
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._poll, name="mpv-poll", daemon=True)
            self._thread.start()

    def _command(self, *args, timeout=1.2):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(timeout)
                connection.connect(self.socket_path)
                payload = json.dumps({"command": list(args)}) + "\n"
                connection.sendall(payload.encode("utf-8"))
                if args[0] in ("get_property", "observe_property"):
                    buffer = b""
                    while not buffer.endswith(b"\n"):
                        chunk = connection.recv(4096)
                        if not chunk:
                            break
                        buffer += chunk
                    if not buffer:
                        return None
                    reply = json.loads(buffer.decode("utf-8", "ignore").splitlines()[0])
                    return reply.get("data")
        except (OSError, ValueError, json.JSONDecodeError):
            return None
        return None

    def load(self, url, title=""):
        self.start()
        with self._lock:
            self.title = title
            self._media_loaded = True
            self._started = False
            self._finished = False
            self._failed = False
            self._deadline = time.monotonic() + 15
            self.state.update({
                "playing": False,
                "paused": False,
                "position": 0.0,
                "duration": 0.0,
                "title": title,
                "loading": True,
                "error": None,
            })
        self._command("loadfile", url, "replace")
        self._command("set_property", "pause", False)

    def toggle_pause(self):
        paused = self._command("get_property", "pause")
        self._command("set_property", "pause", not bool(paused))

    def pause(self, value=True):
        self._command("set_property", "pause", bool(value))

    def stop(self):
        with self._lock:
            self._media_loaded = False
            self._started = False
            self.state.update({"playing": False, "paused": False, "position": 0.0, "loading": False})
        self._command("stop")

    def seek(self, position):
        self._command("seek", float(position), "absolute")

    def set_volume(self, volume):
        self.volume = int(max(0, min(100, volume)))
        self._command("set_property", "volume", self.volume)

    def snapshot(self):
        with self._lock:
            return dict(self.state)

    def consume_finished(self):
        with self._lock:
            value = self._finished
            self._finished = False
            return value

    def consume_failed(self):
        with self._lock:
            value = self._failed
            self._failed = False
            return value

    def _poll(self):
        while not self._stop.is_set():
            if self.process is None or self.process.poll() is not None:
                return
            if not self._media_loaded:
                time.sleep(0.3)
                continue
            idle = self._command("get_property", "idle-active")
            paused = self._command("get_property", "pause")
            position = self._command("get_property", "time-pos")
            duration = self._command("get_property", "duration")
            with self._lock:
                if idle is False:
                    self._started = True
                elif idle is True and self._started:
                    self._finished = True
                    self._media_loaded = False
                    self._started = False
                    self.state.update({"playing": False, "paused": False, "loading": False})
                elif idle is True and not self._started and time.monotonic() > self._deadline:
                    self._failed = True
                    self._media_loaded = False
                    self._started = False
                    self.state.update({
                        "playing": False,
                        "paused": False,
                        "loading": False,
                        "error": "Could not play this track",
                    })
                if isinstance(position, (int, float)):
                    self.state["position"] = float(position)
                if isinstance(duration, (int, float)):
                    self.state["duration"] = float(duration)
                if paused is not None:
                    self.state["paused"] = bool(paused)
                self.state["playing"] = bool(self._media_loaded and self._started and not self.state["paused"])
                self.state["loading"] = bool(self._media_loaded and not self._started)
            time.sleep(0.4)

    def shutdown(self):
        self._stop.set()
        if self.process is not None and self.process.poll() is None:
            self._command("quit")
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
        try:
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
        except OSError:
            pass


class Thumbnails:
    def __init__(self):
        self.pool = Tasks(workers=3)
        self.futures = {}
        self.data = {}
        self.cache = {}

    def request(self, url):
        if not url or url in self.data or url in self.futures:
            return
        self.futures[url] = self.pool.submit(self._fetch, url)

    def _fetch(self, url):
        try:
            response = requests.get(url, timeout=10)
            if response.ok:
                return response.content
        except requests.RequestException:
            return None
        return None

    def get(self, url, size):
        key = (url, size)
        if key in self.cache:
            return self.cache[key]
        future = self.futures.get(url)
        if future is not None and future.done():
            self.futures.pop(url, None)
            try:
                payload = future.result()
            except Exception:  # noqa: BLE001
                payload = None
            if payload:
                self.data[url] = payload
        payload = self.data.get(url)
        if not payload:
            return None
        try:
            image = pygame.image.load(BytesIO(payload)).convert()
        except pygame.error:
            self.data.pop(url, None)
            return None
        image = pygame.transform.smoothscale(image, size)
        self.cache[key] = image
        if len(self.cache) > 220:
            self.cache.clear()
            self.cache[key] = image
        return image

    def shutdown(self):
        self.pool.shutdown()


class MusicService:
    def __init__(self, config):
        self.config = config
        self.player = Player(volume=config.get("music.volume", 70))
        self.thumbnails = Thumbnails()

    def search(self, query):
        return search(query, int(self.config.get("music.search_results", 20) or 20))

    def start_player(self):
        try:
            self.player.start()
        except MusicError:
            pass

    def status(self):
        return {
            "mpv": find_tool("mpv") is not None,
            "ytdlp": find_tool("yt-dlp") is not None,
        }

    def shutdown(self):
        self.player.shutdown()
        self.thumbnails.shutdown()
