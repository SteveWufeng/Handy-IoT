import datetime as dt
import math

import pygame

from .. import icons, ui
from .. import theme as T
from .base import Screen


class Tile:
    def __init__(self, rect, title, icon, accent, subtitle, on_click):
        self.rect = pygame.Rect(rect)
        self.title = title
        self.icon = icon
        self.accent = accent
        self.subtitle = subtitle
        self.on_click = on_click
        self.down = False

    def mousedown(self, pos):
        if self.rect.collidepoint(pos):
            self.down = True
            return True
        return False

    def mouseup(self, pos):
        if not self.down:
            return False
        self.down = False
        if self.rect.collidepoint(pos):
            self.on_click()
        return True

    def draw(self, surface, theme):
        background = T.CARD_PRESS if self.down else T.CARD
        ui.panel(surface, self.rect, background, theme.px(22), T.BORDER)
        pad = theme.px(20)
        watermark_size = int(min(self.rect.w, self.rect.h) * 0.62)
        watermark = pygame.Surface((watermark_size, watermark_size), pygame.SRCALPHA)
        icons.draw(watermark, self.icon, watermark.get_rect(), (*self.accent, 18))
        surface.blit(watermark, (self.rect.right - watermark_size + theme.px(8),
                                 self.rect.bottom - watermark_size + theme.px(6)))
        box_size = theme.px(58)
        box = pygame.Rect(self.rect.x + pad, self.rect.y + pad, box_size, box_size)
        ui.panel(surface, box, ui.blend(T.CARD, self.accent, 0.16), theme.px(17))
        icons.draw(surface, self.icon, box.inflate(-theme.px(28), -theme.px(28)), self.accent,
                   max(2, theme.px(2)))
        icons.draw(surface, "chevron", (self.rect.right - pad - theme.px(14), self.rect.y + pad + theme.px(6),
                                        theme.px(14), theme.px(14)), T.FAINT)
        title_font = theme.font(21, bold=True)
        subtitle_font = theme.font(12)
        lines = ui.wrap(subtitle_font, self.subtitle, self.rect.w - pad * 2 - theme.px(4), 2)
        line_height = subtitle_font.get_height()
        title_height = title_font.get_height()
        subtitle_bottom = self.rect.bottom - pad
        subtitle_top = subtitle_bottom - line_height * len(lines)
        title_y = subtitle_top - title_height - theme.px(4)
        ui.text(surface, title_font, self.title, T.TEXT, (self.rect.x + pad, title_y))
        for index, line in enumerate(lines):
            ui.text(surface, subtitle_font, line, T.MUTED,
                    (self.rect.x + pad, subtitle_top + index * line_height))


class HomeScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.tiles = []
        self.build()

    def header_height(self):
        return self.theme.px(120)

    def layout(self):
        super().layout()
        theme = self.theme
        pad = theme.px(20)
        self.settings_button = ui.Button(
            (self.app.size[0] - pad - theme.px(44), theme.px(12), theme.px(44), theme.px(44)),
            icon="gear",
            style="ghost",
            on_click=self.open_settings,
        )
        area = pygame.Rect(pad, self.header_height() + theme.px(4),
                           self.app.size[0] - pad * 2,
                           self.app.size[1] - self.header_height() - theme.px(4) - pad)
        gap = theme.px(14)
        if area.w >= theme.px(580):
            columns = 3
        elif area.w >= theme.px(380):
            columns = 2
        else:
            columns = 1
        rows = math.ceil(3 / columns)
        tile_w = (area.w - gap * (columns - 1)) / columns
        tile_h = (area.h - gap * (rows - 1)) / rows
        self.tile_rects = []
        for index in range(3):
            row, column = divmod(index, columns)
            rect = pygame.Rect(int(area.x + column * (tile_w + gap)),
                               int(area.y + row * (tile_h + gap)),
                               int(tile_w), int(tile_h))
            self.tile_rects.append(rect)

    def build(self):
        rects = self.tile_rects
        self.tiles = [
            Tile(rects[0], "Calendar", "calendar", T.ACCENT, self.calendar_subtitle, self.open_calendar),
            Tile(rects[1], "Pomodoro", "timer", T.TEAL, self.pomodoro_subtitle, self.open_pomodoro),
            Tile(rects[2], "Music", "music", T.AMBER, self.music_subtitle, self.open_music),
        ]

    def on_enter(self):
        if self.app.calendar.stale():
            self.app.refresh_calendar()

    def open_calendar(self):
        from .calendar import CalendarScreen
        self.app.push(CalendarScreen(self.app))

    def open_pomodoro(self):
        from .pomodoro import PomodoroScreen
        self.app.push(PomodoroScreen(self.app))

    def open_music(self):
        self.app.open_music()

    def open_settings(self):
        from .settings import SettingsScreen
        self.app.push(SettingsScreen(self.app))

    def calendar_subtitle(self):
        calendar = self.app.calendar
        if not calendar.url:
            return "Connect your calendar in Settings"
        event = calendar.next_event()
        if event is None and self.app.calendar_loading:
            return "Syncing calendar..."
        if event is not None:
            if event.ongoing:
                return f"Now - {event.summary}"
            today = dt.date.today()
            if event.start_date == today:
                return f"{event.start:%H:%M} - {event.summary}"
            if event.start_date == today + dt.timedelta(days=1):
                return f"Tomorrow {event.start:%H:%M} - {event.summary}"
            return f"{event.start:%a %H:%M} - {event.summary}"
        if calendar.error:
            return "Calendar unavailable - tap to retry"
        return "No upcoming events"

    def pomodoro_subtitle(self):
        return self.app.pomodoro.summary()

    def music_subtitle(self):
        state = self.app.music.player.snapshot()
        if state["title"] and (state["playing"] or state["paused"]):
            prefix = "Paused" if state["paused"] else "Playing"
            return f"{prefix} - {state['title']}"
        if state["loading"]:
            return "Loading music..."
        return "Search and play music"

    def handle(self, event):
        if self.handle_header(event):
            return True
        if ui.dispatch([self.settings_button], event):
            return True
        return bool(ui.dispatch(self.tiles, event))

    def draw(self, surface):
        theme = self.theme
        pad = theme.px(20)
        now = dt.datetime.now()
        clock_font = theme.font(46, bold=True)
        ui.text(surface, clock_font, now.strftime("%H:%M"), T.TEXT, (pad, theme.px(8)))
        ui.text(surface, theme.font(13), now.strftime("%A, %B %d"), T.MUTED,
                (pad, theme.px(72)))
        self.settings_button.draw(surface, theme)
        self.draw_next_event(surface, theme, pad)
        getters = (self.calendar_subtitle, self.pomodoro_subtitle, self.music_subtitle)
        for tile, getter in zip(self.tiles, getters):
            tile.subtitle = getter()
            tile.draw(surface, theme)

    def draw_next_event(self, surface, theme, pad):
        event = self.app.calendar.next_event()
        icon_size = theme.px(15)
        top = theme.px(95)
        icon_rect = pygame.Rect(pad, top, icon_size, icon_size)
        icons.draw(surface, "calendar", icon_rect, T.ACCENT)
        max_width = self.settings_button.rect.left - pad - icon_size - theme.px(20)
        if event is not None:
            if event.ongoing:
                label = f"Now - {event.summary}"
            elif event.start_date == dt.date.today():
                label = f"{event.start:%H:%M} - {event.summary}"
            else:
                label = f"{event.start:%a %H:%M} - {event.summary}"
        elif not self.app.calendar.url:
            label = "Connect a public Google Calendar in Settings"
        elif self.app.calendar.error:
            label = "Calendar unavailable"
        else:
            label = "No upcoming events"
        font = theme.font(13)
        ui.text(surface, font, ui.ellipsize(font, label, max_width), T.MUTED,
                (icon_rect.right + theme.px(8), top + icon_size // 2), "midleft")
