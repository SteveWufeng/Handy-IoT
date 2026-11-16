import os
import sys
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

if sys.platform.startswith("linux"):
    if (not os.environ.get("SDL_VIDEODRIVER") and not os.environ.get("DISPLAY")
            and not os.environ.get("WAYLAND_DISPLAY") and os.path.exists("/dev/dri/card0")):
        os.environ["SDL_VIDEODRIVER"] = "kmsdrm"
    os.environ.setdefault("SDL_AUDIODRIVER", "alsa")

import pygame

from . import theme as T
from . import ui
from .audio import Chime
from .config import Config
from .screens.home import HomeScreen
from .services.calendar import CalendarService
from .services.music import MusicService
from .services.pomodoro import PomodoroTimer
from .tasks import Tasks


class App:
    def __init__(self):
        self.config = Config()
        pygame.mixer.pre_init(44100, -16, 1, 512)
        pygame.display.init()
        pygame.font.init()
        try:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        except pygame.error:
            self.screen = pygame.display.set_mode((800, 480))
        pygame.display.set_caption("Handy")
        pygame.mouse.set_visible(False)
        self.size = self.screen.get_size()
        self.theme = T.Theme(self.size)
        self.background = T.Background(self.size)
        self.tasks = Tasks()
        self.chime = Chime(self.config.get("audio.enabled", True))
        self.calendar = CalendarService(self.config)
        self.music = MusicService(self.config)
        self.pomodoro = PomodoroTimer(self.config, on_phase_end=self.on_phase_end)
        self.keyboard = ui.Keyboard(self)
        self.music_screen = None
        self.stack = []
        self.running = True
        self.fps = max(10, min(60, int(self.config.get("display.fps", 30))))
        self.clock = pygame.time.Clock()
        self._toast_text = None
        self._toast_until = 0.0
        self._calendar_future = None
        self._calendar_notify = False
        self._calendar_last_attempt = -1e9
        self._touch_seen = -10.0
        self._touch_active = False
        self.push(HomeScreen(self))
        self.tasks.submit(self.music.start_player)
        self.refresh_calendar()

    @property
    def calendar_loading(self):
        return self._calendar_future is not None and not self._calendar_future.done()

    def _calendar_interval(self):
        return 60 if self.calendar.error else self.calendar.refresh_minutes * 60

    def refresh_calendar(self, notify=False):
        if self._calendar_future is not None and not self._calendar_future.done():
            self._calendar_notify = self._calendar_notify or notify
            return self._calendar_future
        if not self.calendar.url:
            self.calendar.error = "No calendar URL configured"
            return None
        self._calendar_last_attempt = time.monotonic()
        self._calendar_notify = notify
        self._calendar_future = self.tasks.submit(self.calendar.refresh)
        return self._calendar_future

    def _poll_calendar(self):
        if self._calendar_future is None or not self._calendar_future.done():
            return
        future = self._calendar_future
        self._calendar_future = None
        notify = self._calendar_notify
        self._calendar_notify = False
        try:
            future.result()
        except Exception:  # noqa: BLE001
            if notify:
                self.toast(self.calendar.error or "Calendar sync failed")
        if (self.calendar.url
                and time.monotonic() - self._calendar_last_attempt > self._calendar_interval()):
            self.refresh_calendar()

    def toast(self, message, seconds=2.5):
        self._toast_text = message
        self._toast_until = time.monotonic() + seconds

    def push(self, screen):
        self.keyboard.close()
        self.stack.append(screen)
        screen.on_enter()

    def open_music(self):
        if self.music_screen is None:
            from .screens.music import MusicScreen
            self.music_screen = MusicScreen(self)
        self.push(self.music_screen)

    def pop(self):
        if len(self.stack) <= 1:
            return
        self.keyboard.close()
        screen = self.stack.pop()
        screen.on_exit()
        self.stack[-1].on_enter()

    def quit(self):
        self.running = False

    def on_phase_end(self, finished, next_phase, skipped):
        if skipped:
            return
        if finished == "work":
            self.chime.play("focus_done")
            self.toast("Break time - step away")
        else:
            self.chime.play("break_done")
            self.toast("Back to focus")

    def _translate(self, event):
        now = time.monotonic()
        if event.type == pygame.FINGERDOWN:
            self._touch_seen = now
            self._touch_active = True
            pos = (int(event.x * self.size[0]), int(event.y * self.size[1]))
            return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1})
        if event.type == pygame.FINGERUP:
            self._touch_seen = now
            self._touch_active = False
            pos = (int(event.x * self.size[0]), int(event.y * self.size[1]))
            return pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": 1})
        if event.type == pygame.FINGERMOTION:
            self._touch_seen = now
            pos = (int(event.x * self.size[0]), int(event.y * self.size[1]))
            return pygame.event.Event(pygame.MOUSEMOTION, {
                "pos": pos,
                "rel": (0, 0),
                "buttons": (1, 0, 0) if self._touch_active else (0, 0, 0),
            })
        if (event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION)
                and now - self._touch_seen < 0.15):
            return None
        return event

    def _draw_toast(self):
        remaining = self._toast_until - time.monotonic()
        if remaining <= 0 or not self._toast_text:
            return
        theme = self.theme
        font = theme.font(13, bold=True)
        text_width = font.size(self._toast_text)[0]
        height = theme.px(40)
        width = text_width + theme.px(40)
        bottom = self.size[1] - theme.px(20)
        if self.keyboard.visible:
            bottom = self.keyboard.panel_rect.top - theme.px(16)
        rect = pygame.Rect((self.size[0] - width) // 2, bottom - height, width, height)
        ui.panel(self.screen, rect, T.CARD_HI, height // 2, T.BORDER)
        ui.text(self.screen, font, self._toast_text, T.TEXT, rect.center, "center")

    def run(self):
        try:
            while self.running:
                dt = min(0.1, self.clock.tick(self.fps) / 1000.0)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                        continue
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.pop()
                        elif event.key == pygame.K_q and event.mod & pygame.KMOD_CTRL:
                            self.running = False
                        continue
                    normalized = self._translate(event)
                    if normalized is None:
                        continue
                    if self.keyboard.visible and self.keyboard.handle(normalized):
                        continue
                    self.stack[-1].handle(normalized)
                self.pomodoro.update(dt)
                self._poll_calendar()
                if (self.calendar.url and self._calendar_future is None
                        and time.monotonic() - self._calendar_last_attempt > self._calendar_interval()):
                    self.refresh_calendar()
                self.stack[-1].update(dt)
                if self.music_screen is not None and self.stack[-1] is not self.music_screen:
                    self.music_screen.update(dt)
                self.chime.tick()
                self.background.draw(self.screen)
                self.stack[-1].draw(self.screen)
                self.keyboard.draw(self.screen)
                self._draw_toast()
                pygame.display.flip()
        finally:
            self.shutdown()

    def shutdown(self):
        self.music.shutdown()
        self.tasks.shutdown()
        pygame.quit()


def main():
    try:
        app = App()
    except pygame.error as exc:
        print(f"Unable to start display: {exc}", file=sys.stderr)
        return 1
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
