import datetime as dt
import time

import pygame

from .. import icons, ui
from .. import theme as T
from .base import Screen


def day_label(day):
    today = dt.date.today()
    if day == today:
        return "TODAY"
    if day == today + dt.timedelta(days=1):
        return "TOMORROW"
    return day.strftime("%a, %b %d").upper()


class CalendarScreen(Screen):
    def __init__(self, app):
        self.scroll = ui.ScrollModel()
        self.state_key = None
        self.action = None
        super().__init__(app)

    def layout(self):
        super().layout()
        theme = self.theme
        pad = theme.px(18)
        self.viewport = pygame.Rect(
            pad,
            self.header_height() + theme.px(34),
            self.app.size[0] - pad * 2,
            self.app.size[1] - self.header_height() - theme.px(34) - pad,
        )
        size = theme.px(44)
        self.header_buttons = [ui.Button(
            (self.app.size[0] - pad - size, (self.header_height() - size) // 2, size, size),
            icon="refresh",
            style="ghost",
            on_click=self.refresh,
        )]
        button_width = theme.px(170)
        self.state_button = ui.Button(
            (self.viewport.centerx - button_width // 2, self.viewport.centery + theme.px(48),
             button_width, theme.px(46)),
            label="Retry",
            style="accent",
            on_click=self.retry,
            size=14,
        )
        self.action = None

    def on_enter(self):
        if self.app.calendar.stale():
            self.app.refresh_calendar()

    def refresh(self):
        self.app.refresh_calendar(notify=True)

    def retry(self):
        if self.action:
            self.action()

    def handle(self, event):
        if self.handle_header(event):
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.state_button is not None and self.state_button.mousedown(event.pos):
                return True
            if self.viewport.collidepoint(event.pos):
                self.scroll.begin(event.pos[1])
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.state_button is not None and self.state_button.mouseup(event.pos):
                return True
            if self.scroll.dragging:
                self.scroll.end()
                return True
        elif event.type == pygame.MOUSEMOTION:
            if self.scroll.dragging:
                self.scroll.move(event.pos[1])
                return True
        elif (event.type == pygame.MOUSEWHEEL
                and self.viewport.colliderect(pygame.Rect(pygame.mouse.get_pos(), (1, 1)))):
            self.scroll.scroll(-event.y * self.theme.px(48))
            return True
        return False

    def update(self, dt):
        self.scroll.update(dt)
        self.refresh_state()

    def refresh_state(self):
        calendar = self.app.calendar
        events = calendar.upcoming()
        if not calendar.url:
            key = "no-url"
            self.action = self.open_settings
            self.state_key = key
            return
        if not events and self.app.calendar_loading:
            key = "loading"
        elif not events and calendar.error:
            key = "error"
        elif not events:
            key = "empty"
        else:
            key = "list"
        self.state_key = key
        if key == "error":
            self.action = self.refresh
        elif key in ("no-url", "empty"):
            self.action = self.refresh if key == "empty" else self.open_settings
        else:
            self.action = None

    def open_settings(self):
        from .settings import SettingsScreen
        self.app.push(SettingsScreen(self.app))

    def _build(self, events):
        theme = self.theme
        title_font = theme.font(15, bold=True)
        meta_font = theme.font(11)
        pad = theme.px(10)
        time_width = theme.px(82)
        items = []
        y = 0
        groups = {}
        order = []
        today = dt.date.today()
        for event in events:
            group_day = max(event.start_date, today)
            if group_day not in groups:
                groups[group_day] = []
                order.append(group_day)
            groups[group_day].append(event)
        for index, day in enumerate(order):
            date_height = theme.px(30) if index else theme.px(24)
            items.append(("date", day, y, date_height))
            y += date_height
            for event in groups[day]:
                title_lines = ui.wrap(title_font, event.summary,
                                      self.viewport.w - pad * 2 - time_width - theme.px(14), 2)
                location_height = meta_font.get_height() + theme.px(2) if event.location else 0
                height = max(theme.px(60),
                             pad * 2 + title_font.get_height() * len(title_lines) + location_height)
                items.append(("event", event, y, height, title_lines))
                y += height + theme.px(8)
            y += theme.px(6)
        return items, y

    def draw(self, surface):
        theme = self.theme
        self.draw_header(surface, "Calendar")
        info_font = theme.font(10, bold=True)
        ui.text(surface, info_font, "UPCOMING", T.FAINT,
                (self.viewport.x + theme.px(2), self.header_height() + theme.px(12)))
        updated = self.app.calendar.updated_label()
        font = theme.font(11)
        label_rect = ui.text(surface, font, updated, T.FAINT,
                             (self.viewport.right - theme.px(2), self.header_height() + theme.px(12)), "topright")
        if self.app.calendar_loading:
            ui.draw_spinner(surface, (label_rect.left - theme.px(12), label_rect.centery),
                            theme.px(7), T.ACCENT, (time.monotonic() % 1.0), max(2, theme.px(2)))
        events = self.app.calendar.upcoming()
        if self.state_key != "list":
            self.draw_state(surface, theme)
            return
        items, content_height = self._build(events)
        self.scroll.configure(content_height, self.viewport.h)
        surface.set_clip(self.viewport)
        for item in items:
            if item[0] == "date":
                _, day, y, height = item
                draw_y = self.viewport.y + y - self.scroll.offset
                if draw_y < self.viewport.bottom and draw_y + height > self.viewport.top:
                    self.draw_date(surface, theme, day, draw_y)
            else:
                _, event, y, height, lines = item
                draw_y = self.viewport.y + y - self.scroll.offset
                if draw_y < self.viewport.bottom and draw_y + height > self.viewport.top:
                    self.draw_event(surface, theme, event, draw_y, height, lines)
        surface.set_clip(None)
        self.draw_scrollbar(surface, theme, content_height)

    def draw_date(self, surface, theme, day, y):
        font = theme.font(10, bold=True)
        zone = pygame.Rect(self.viewport.x, y, self.viewport.w, theme.px(26))
        ui.text(surface, font, day_label(day), T.MUTED, (zone.x + theme.px(2), zone.centery), "midleft")
        label_width = font.size(day_label(day))[0]
        line_x = zone.x + label_width + theme.px(12)
        if line_x < zone.right:
            pygame.draw.line(surface, T.BORDER, (line_x, zone.centery),
                             (zone.right - theme.px(4), zone.centery), max(1, theme.px(1)))

    def draw_event(self, surface, theme, event, y, height, lines):
        pad = theme.px(10)
        card = pygame.Rect(self.viewport.x, y, self.viewport.w, height)
        border = T.TEAL if event.ongoing else T.BORDER
        ui.panel(surface, card, T.CARD, theme.px(14), border)
        accent = T.TEAL if event.ongoing else T.ACCENT
        pill = pygame.Rect(card.x + theme.px(14), card.y + pad, theme.px(3), height - pad * 2)
        pygame.draw.rect(surface, accent, pill, border_radius=theme.px(2))
        time_width = theme.px(82)
        time_x = card.x + pad + theme.px(18)
        title_font = theme.font(15, bold=True)
        meta_font = theme.font(11)
        if event.all_day:
            ui.text(surface, theme.font(10, bold=True), "ALL DAY", accent,
                    (time_x, card.y + pad), "topleft")
        else:
            ui.text(surface, theme.font(13, bold=True), event.start.strftime("%H:%M"), T.TEXT,
                    (time_x, card.y + pad), "topleft")
            end_label = event.end.strftime("%H:%M") if event.end.date() == event.start.date() else event.end.strftime("%b %d")
            ui.text(surface, theme.font(10), end_label, T.FAINT,
                    (time_x, card.y + pad + theme.px(17)), "topleft")
        text_x = card.x + pad + time_width
        text_width = card.right - text_x - pad
        top = card.y + pad
        for line in lines[:2]:
            ui.text(surface, title_font, line, T.TEXT, (text_x, top))
            top += title_font.get_height()
        if event.location:
            ui.text(surface, meta_font, ui.ellipsize(meta_font, event.location, text_width),
                    T.MUTED, (text_x, top + theme.px(1)))

    def draw_scrollbar(self, surface, theme, content_height):
        if self.scroll.max_offset <= 0:
            return
        track_x = self.rect.right - theme.px(5)
        track = pygame.Rect(track_x, self.viewport.y, theme.px(3), self.viewport.h)
        pygame.draw.rect(surface, T.CARD, track, border_radius=theme.px(2))
        ratio = self.viewport.h / max(1, content_height)
        thumb_h = max(theme.px(26), int(self.viewport.h * ratio))
        progress = self.scroll.offset / self.scroll.max_offset if self.scroll.max_offset else 0
        thumb_y = self.viewport.y + int((self.viewport.h - thumb_h) * progress)
        pygame.draw.rect(surface, T.FAINT, (track_x, thumb_y, theme.px(3), thumb_h),
                         border_radius=theme.px(2))

    def draw_state(self, surface, theme):
        calendar = self.app.calendar
        center_x = self.viewport.centerx
        icon_box = theme.px(64)
        icon_rect = pygame.Rect(center_x - icon_box // 2, self.viewport.centery - theme.px(112),
                                icon_box, icon_box)
        ui.panel(surface, icon_rect, T.CARD, theme.px(18), T.BORDER)
        if self.state_key == "loading":
            ui.draw_spinner(surface, icon_rect.center, theme.px(16), T.ACCENT,
                            (time.monotonic() % 1.0), max(2, theme.px(3)))
            title = "Loading calendar"
            body = "Fetching your upcoming events"
        elif self.state_key == "error":
            icons.draw(surface, "calendar", icon_rect.inflate(-theme.px(30), -theme.px(30)), T.DANGER,
                       max(2, theme.px(2)))
            title = "Calendar unavailable"
            body = calendar.error or "Could not load events"
        elif self.state_key == "no-url":
            icons.draw(surface, "calendar", icon_rect.inflate(-theme.px(30), -theme.px(30)), T.ACCENT,
                       max(2, theme.px(2)))
            title = "Connect your calendar"
            body = "Paste the public iCal link from Google Calendar in Settings"
        else:
            icons.draw(surface, "check", icon_rect.inflate(-theme.px(30), -theme.px(30)), T.TEAL,
                       max(2, theme.px(2)))
            title = "Nothing coming up"
            body = f"You are all clear for the next {calendar.days_ahead} days"
        ui.text(surface, theme.font(20, bold=True), title, T.TEXT,
                (center_x, icon_rect.bottom + theme.px(22)), "center")
        font = theme.font(12)
        body_lines = ui.wrap(font, body, self.viewport.w - theme.px(100), 2)
        for index, line in enumerate(body_lines):
            ui.text(surface, font, line, T.MUTED,
                    (center_x, icon_rect.bottom + theme.px(50) + index * font.get_height()), "center")
        self.state_button.rect.centery = icon_rect.bottom + theme.px(96) + theme.px(23)
        self.state_button.rect.centerx = center_x
        if self.state_key in ("no-url", "error"):
            self.state_button.label = "Open settings" if self.state_key == "no-url" else "Try again"
            self.state_button.draw(surface, theme)
        elif self.state_key == "empty":
            self.state_button.label = "Refresh"
            self.state_button.draw(surface, theme)
