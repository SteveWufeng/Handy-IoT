import queue
import threading
from concurrent.futures import Future


class Tasks:
    def __init__(self, workers=4):
        self.queue = queue.Queue()
        self.lock = threading.Lock()
        self.stopped = False
        self.threads = [
            threading.Thread(target=self._work, name=f"handy-{index}", daemon=True)
            for index in range(max(1, workers))
        ]
        for thread in self.threads:
            thread.start()

    def submit(self, fn, *args, **kwargs):
        future = Future()
        self.queue.put((future, fn, args, kwargs))
        return future

    def _work(self):
        while True:
            item = self.queue.get()
            if item is None:
                return
            future, fn, args, kwargs = item
            if not future.set_running_or_notify_cancel():
                continue
            try:
                future.set_result(fn(*args, **kwargs))
            except Exception as exc:  # noqa: BLE001
                future.set_exception(exc)

    def shutdown(self):
        with self.lock:
            if self.stopped:
                return
            self.stopped = True
        while True:
            try:
                item = self.queue.get_nowait()
            except queue.Empty:
                break
            if item is not None:
                item[0].cancel()
        for _ in self.threads:
            self.queue.put(None)
