import math
import time

import pygame

from .. import icons, ui
from .. import theme as T
from ..services.music import MusicError
from .base import Screen


class MusicScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.query = ""
        self.results = []
        self.future = None
        self.loading = False
        self.error = None
        self.scroll = ui.ScrollModel()
        self.queue = []
        self.index = -1
        self.current = None
        self.playing_id = None
        self.press_pos = None
        self.press_index = None
        self.drag_distance = 0.0

    def layout(self):
        super().layout()
        theme = self.theme
        pad = theme.px(16)
        width, height = self.app.size
        self.search_rect = pygame.Rect(pad, self.header_height() + theme.px(4),
                                       width - pad * 2, theme.px(46))
        self.field = ui.TextField(self.search_rect, "Search YouTube", icon="search")
        chip_y = self.search_rect.bottom + theme.px(10)
        chip_h = theme.px(30)
        queries = list(self.app.config.get("music.quick_searches", []) or [])[:4]
        self.chips = []
        if queries:
            gap = theme.px(8)
            chip_w = (width - pad * 2 - gap * (len(queries) - 1)) / len(queries)
            for index, query in enumerate(queries):
                rect = pygame.Rect(int(pad + index * (chip_w + gap)), chip_y, int(chip_w), chip_h)
                self.chips.append(ui.Chip(rect, query, lambda value=query: self.run_search(value)))
        self.player_rect = pygame.Rect(pad, height - pad - theme.px(96), width - pad * 2, theme.px(96))
        self.thumb_rect = pygame.Rect(self.player_rect.x + theme.px(10),
                                      self.player_rect.y + theme.px(10),
                                      int(theme.px(50) * 16 / 9), theme.px(50))
        size = theme.px(42)
        play_size = theme.px(48)
        next_rect = pygame.Rect(self.player_rect.right - theme.px(10) - size,
                                self.player_rect.y + theme.px(12), size, size)
        play_rect = pygame.Rect(next_rect.left - theme.px(6) - play_size,
                                self.player_rect.y + theme.px(9), play_size, play_size)
        prev_rect = pygame.Rect(play_rect.left - theme.px(6) - size,
                                self.player_rect.y + theme.px(12), size, size)
        self.next_button = ui.Button(next_rect, icon="next", style="ghost", on_click=self.next_track)
        self.play_button = ui.Button(play_rect, icon="play", style="accent", on_click=self.toggle_play,
                                     radius=24)
        self.prev_button = ui.Button(prev_rect, icon="prev", style="ghost", on_click=self.previous_track)
        self.time_font = theme.font(10)
        self.progress_rect = pygame.Rect(
            self.player_rect.x + theme.px(10) + self.time_font.size("00:00")[0] + theme.px(10),
            self.player_rect.bottom - theme.px(16),
            self.player_rect.w - theme.px(20) - (self.time_font.size("00:00")[0] + theme.px(10)) * 2,
            theme.px(4),
        )
        self.controls_left = prev_rect.left
        results_top = chip_y + chip_h + theme.px(10)
        self.viewport = pygame.Rect(pad, results_top, width - pad * 2,
                                    self.player_rect.y - theme.px(10) - results_top)
        self.row_height = theme.px(66)
        self.row_gap = theme.px(8)
        self.thumb_size = (theme.px(84), theme.px(47))

    def on_enter(self):
        pass

    def open_keyboard(self):
        self.app.keyboard.open(self.query, on_change=self.on_query_change,
                               on_submit=self.run_search, title="Search YouTube")

    def on_query_change(self, value):
        self.query = value

    def run_search(self, query):
        query = (query or "").strip()
        if not query:
            return
        self.query = query
        self.loading = True
        self.error = None
        self.results = []
        self.scroll.reset()
        self.future = self.app.tasks.submit(self.app.music.search, query)

    def play_result(self, result, queue, index):
        self.queue = queue
        self.index = index
        self.current = result
        self.playing_id = result.get("id")
        self.app.music.thumbnails.request(result.get("thumbnail"))
        try:
            self.app.music.player.load(result["url"], result["title"])
        except MusicError as exc:
            self.error = str(exc)
            self.notify(str(exc))

    def play_index(self, index):
        if 0 <= index < len(self.results):
            self.play_result(self.results[index], self.results, index)

    def next_track(self):
        if self.queue and self.index + 1 < len(self.queue):
            self.play_result(self.queue[self.index + 1], self.queue, self.index + 1)

    def previous_track(self):
        if self.queue and self.index > 0:
            self.play_result(self.queue[self.index - 1], self.queue, self.index - 1)

    def toggle_play(self):
        player = self.app.music.player
        if self.current is None:
            if self.results:
                self.play_index(0)
            return
        if player.snapshot().get("error"):
            try:
                player.load(self.current["url"], self.current["title"])
            except MusicError as exc:
                self.error = str(exc)
                self.notify(str(exc))
            return
        player.toggle_pause()

    def seek_at(self, pos):
        state = self.app.music.player.snapshot()
        duration = state.get("duration") or 0
        if duration <= 0:
            return
        ratio = (pos[0] - self.progress_rect.x) / max(1, self.progress_rect.w)
        self.app.music.player.seek(max(0.0, min(1.0, ratio)) * duration)

    def _row_index(self, pos):
        if not self.viewport.collidepoint(pos):
            return None
        step = self.row_height + self.row_gap
        index = int((pos[1] - self.viewport.y + self.scroll.offset) // step)
        if not 0 <= index < len(self.results):
            return None
        top = self.viewport.y + index * step - self.scroll.offset
        if top <= pos[1] <= top + self.row_height:
            return index
        return None

    def handle(self, event):
        if self.handle_header(event):
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.search_rect.collidepoint(event.pos):
                self.open_keyboard()
                return True
            if ui.dispatch(self.chips, event):
                return True
            if self.progress_rect.inflate(0, self.theme.px(16)).collidepoint(event.pos):
                self.seek_at(event.pos)
                return True
            if ui.dispatch([self.prev_button, self.play_button, self.next_button], event):
                return True
            if self.viewport.collidepoint(event.pos):
                self.scroll.begin(event.pos[1])
                self.press_pos = event.pos
                self.press_index = self._row_index(event.pos)
                self.drag_distance = 0.0
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if ui.dispatch(self.chips, event):
                return True
            if ui.dispatch([self.prev_button, self.play_button, self.next_button], event):
                return True
            if self.scroll.dragging:
                self.scroll.end()
                if self.drag_distance < self.theme.px(8) and self.press_index is not None:
                    self.play_index(self.press_index)
                self.press_pos = None
                self.press_index = None
                return True
        elif event.type == pygame.MOUSEMOTION:
            if self.scroll.dragging:
                before = self.scroll.offset
                self.scroll.move(event.pos[1])
                self.drag_distance += abs(self.scroll.offset - before)
                return True
        elif (event.type == pygame.MOUSEWHEEL
                and self.viewport.collidepoint(pygame.mouse.get_pos())):
            self.scroll.scroll(-event.y * self.theme.px(44))
            return True
        return False

    def update(self, dt):
        self.scroll.update(dt)
        if self.future is not None and self.future.done():
            future = self.future
            self.future = None
            self.loading = False
            try:
                self.results = future.result()
                self.error = None
                self.scroll.reset()
                for result in self.results[:12]:
                    self.app.music.thumbnails.request(result.get("thumbnail"))
            except Exception as exc:  # noqa: BLE001
                self.error = str(exc)
                self.results = []
                self.notify("Search failed")
        player = self.app.music.player
        if player.consume_failed():
            self.error = player.snapshot().get("error") or "Could not play this track"
            self.notify(self.error)
        if player.consume_finished():
            if self.queue and self.index + 1 < len(self.queue):
                self.play_result(self.queue[self.index + 1], self.queue, self.index + 1)
            else:
                self.index = -1
                self.current = None
                self.playing_id = None

    def draw(self, surface):
        theme = self.theme
        self.draw_header(surface, "Music")
        active = self.app.keyboard.visible and self.app.keyboard.title == "Search YouTube"
        self.field.draw(surface, theme, self.query, active)
        for chip in self.chips:
            chip.draw(surface, theme)
        self.draw_results(surface, theme)
        self.draw_player(surface, theme)

    def draw_results(self, surface, theme):
        if self.loading:
            ui.draw_spinner(surface, self.viewport.center, theme.px(18), T.ACCENT,
                            (time.monotonic() % 1.0), max(2, theme.px(3)))
            ui.text(surface, theme.font(12), "Searching YouTube", T.MUTED,
                    (self.viewport.centerx, self.viewport.centery + theme.px(34)), "center")
            return
        if self.error and not self.results:
            ui.text(surface, theme.font(16, bold=True), "Search failed", T.TEXT,
                    (self.viewport.centerx, self.viewport.centery - theme.px(10)), "center")
            font = theme.font(11)
            lines = ui.wrap(font, self.error, self.viewport.w - theme.px(60), 2)
            for index, line in enumerate(lines):
                ui.text(surface, font, line, T.MUTED,
                        (self.viewport.centerx, self.viewport.centery + theme.px(16) + index * font.get_height()), "center")
            return
        if not self.results:
            title = "No results" if self.query else "Pick a mood or search"
            body = f"Nothing found for \"{self.query}\"" if self.query else "Type above to browse YouTube"
            ui.text(surface, theme.font(14, bold=True), title, T.MUTED,
                    (self.viewport.centerx, self.viewport.centery - theme.px(8)), "center")
            ui.text(surface, theme.font(11), ui.ellipsize(theme.font(11), body, self.viewport.w - theme.px(40)),
                    T.FAINT, (self.viewport.centerx, self.viewport.centery + theme.px(14)), "center")
            return
        step = self.row_height + self.row_gap
        content_height = len(self.results) * step - self.row_gap
        self.scroll.configure(content_height, self.viewport.h)
        surface.set_clip(self.viewport)
        first = max(0, int(self.scroll.offset // step) - 1)
        last = min(len(self.results), first + int(self.viewport.h // step) + 3)
        for index in range(first, last):
            result = self.results[index]
            y = self.viewport.y + index * step - self.scroll.offset
            self.draw_row(surface, theme, result, index, y)
        surface.set_clip(None)
        self.draw_scrollbar(surface, theme, content_height)

    def draw_row(self, surface, theme, result, index, y):
        playing = result.get("id") == self.playing_id
        pressed = self.press_index == index and self.scroll.dragging and self.drag_distance < theme.px(8)
        card = pygame.Rect(self.viewport.x, int(y), self.viewport.w, self.row_height)
        background = T.CARD_PRESS if pressed else T.CARD
        ui.panel(surface, card, background, theme.px(14), T.ACCENT if playing else T.BORDER)
        pad = theme.px(8)
        thumb = pygame.Rect(card.x + pad, card.centery - self.thumb_size[1] // 2, *self.thumb_size)
        self.app.music.thumbnails.request(result.get("thumbnail"))
        image = self.app.music.thumbnails.get(result.get("thumbnail"), self.thumb_size)
        if image is not None:
            ui.rounded_image(surface, image, thumb, theme.px(9))
        else:
            ui.panel(surface, thumb, T.CARD_HI, theme.px(9))
            icons.draw(surface, "music", thumb.inflate(-theme.px(30), -theme.px(18)), T.FAINT)
        text_x = thumb.right + theme.px(10)
        text_width = self.viewport.right - text_x - theme.px(30)
        title_font = theme.font(14, bold=True)
        meta_font = theme.font(10)
        title = ui.ellipsize(title_font, result.get("title") or "Untitled", text_width)
        ui.text(surface, title_font, title, T.TEXT, (text_x, card.y + theme.px(14)))
        uploader = result.get("uploader") or "YouTube"
        duration = result.get("duration")
        meta = uploader
        if isinstance(duration, (int, float)):
            meta = f"{uploader}  -  {ui.format_duration(duration)}"
        ui.text(surface, meta_font, ui.ellipsize(meta_font, meta, text_width), T.MUTED,
                (text_x, card.y + theme.px(36)))
        if playing:
            self.draw_equalizer(surface, theme, self.viewport.right - theme.px(20), card.centery)

    def draw_equalizer(self, surface, theme, x, center_y):
        width = max(2, theme.px(3))
        for index in range(3):
            phase = time.monotonic() * 5 + index * 1.4
            height = theme.px(6) + (0.5 + 0.5 * math.sin(phase)) * theme.px(14)
            bar = pygame.Rect(x + index * (width + theme.px(3)), center_y - height // 2, width, int(height))
            pygame.draw.rect(surface, T.ACCENT if index != 1 else T.TEAL, bar, border_radius=width // 2)

    def draw_player(self, surface, theme):
        rect = self.player_rect
        ui.panel(surface, rect, T.CARD, theme.px(16), T.BORDER)
        state = self.app.music.player.snapshot()
        current = self.current
        image = None
        if current is not None:
            image = self.app.music.thumbnails.get(current.get("thumbnail"), (self.thumb_rect.w, self.thumb_rect.h))
        if image is not None:
            ui.rounded_image(surface, image, self.thumb_rect, theme.px(9))
        else:
            ui.panel(surface, self.thumb_rect, T.CARD_HI, theme.px(9))
            icons.draw(surface, "music", self.thumb_rect.inflate(-theme.px(34), -theme.px(20)), T.FAINT)
        text_x = self.thumb_rect.right + theme.px(12)
        text_width = self.controls_left - text_x - theme.px(8)
        title_font = theme.font(14, bold=True)
        if current is not None:
            title = current.get("title") or state.get("title") or "Playing"
        elif state.get("playing") or state.get("paused") or state.get("loading"):
            title = state.get("title") or "Playing"
        else:
            title = "Nothing playing"
        ui.text(surface, title_font, ui.ellipsize(title_font, title, text_width), T.TEXT,
                (text_x, rect.y + theme.px(14)))
        if state.get("error"):
            status = state["error"]
        elif state.get("loading"):
            status = "Loading..."
        elif state.get("playing"):
            status = "Playing"
        elif state.get("paused"):
            status = "Paused"
        elif current is None:
            status = "Choose a track to begin"
        else:
            status = "Ready"
        meta_font = theme.font(10)
        ui.text(surface, meta_font, ui.ellipsize(meta_font, status, text_width), T.MUTED,
                (text_x, rect.y + theme.px(33)))
        self.play_button.icon = "pause" if state.get("playing") else "play"
        self.play_button.style = "accent"
        self.play_button.enabled = current is not None or bool(self.results)
        self.prev_button.enabled = bool(self.queue) and self.index > 0
        self.next_button.enabled = bool(self.queue) and self.index + 1 < len(self.queue)
        for button in (self.prev_button, self.play_button, self.next_button):
            button.draw(surface, theme)
        position = state.get("position") or 0.0
        duration = state.get("duration") or 0.0
        ratio = min(1.0, max(0.0, position / duration)) if duration else 0.0
        pygame.draw.rect(surface, T.CARD_HI, self.progress_rect, border_radius=self.progress_rect.h // 2)
        filled = pygame.Rect(self.progress_rect.x, self.progress_rect.y,
                             int(self.progress_rect.w * ratio), self.progress_rect.h)
        if filled.w > 0:
            pygame.draw.rect(surface, T.ACCENT, filled, border_radius=self.progress_rect.h // 2)
        time_y = self.progress_rect.centery
        ui.text(surface, self.time_font, ui.format_duration(position), T.FAINT,
                (self.progress_rect.x - theme.px(10), time_y), "midright")
        ui.text(surface, self.time_font, ui.format_duration(duration), T.FAINT,
                (self.progress_rect.right + theme.px(10), time_y), "midleft")

    def draw_scrollbar(self, surface, theme, content_height):
        if self.scroll.max_offset <= 0:
            return
        track_x = self.viewport.right - theme.px(4)
        track = pygame.Rect(track_x, self.viewport.y, theme.px(3), self.viewport.h)
        pygame.draw.rect(surface, T.CARD, track, border_radius=theme.px(2))
        ratio = self.viewport.h / max(1, content_height)
        thumb_h = max(theme.px(24), int(self.viewport.h * ratio))
        progress = self.scroll.offset / self.scroll.max_offset if self.scroll.max_offset else 0
        thumb_y = self.viewport.y + int((self.viewport.h - thumb_h) * progress)
        pygame.draw.rect(surface, T.FAINT, (track_x, thumb_y, theme.px(3), thumb_h),
                         border_radius=theme.px(2))
