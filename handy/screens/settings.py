import pygame

from .. import theme as T
from .. import ui
from .base import Screen


class SettingsScreen(Screen):
    def __init__(self, app):
        super().__init__(app)

    def layout(self):
        super().layout()
        theme = self.theme
        pad = theme.px(18)
        width = self.app.size[0]
        self.content = pygame.Rect(pad, self.header_height() + theme.px(6),
                                   width - pad * 2, self.app.size[1] - self.header_height() - theme.px(6) - pad)
        y = self.content.y
        self.cal_header = y
        y += theme.px(18)
        self.url_row = pygame.Rect(pad, y, self.content.w, theme.px(56))
        y += self.url_row.h + theme.px(8)
        self.refresh_row = pygame.Rect(pad, y, self.content.w, theme.px(36))
        y += self.refresh_row.h + theme.px(12)
        self.audio_header = y
        y += theme.px(18)
        self.volume_row = pygame.Rect(pad, y, self.content.w, theme.px(46))
        y += self.volume_row.h + theme.px(12)
        self.display_header = y
        y += theme.px(18)
        self.theme_row = pygame.Rect(pad, y, self.content.w, theme.px(40))
        y += self.theme_row.h + theme.px(12)
        self.status_header = y
        y += theme.px(18)
        self.status_row = pygame.Rect(pad, y, self.content.w, theme.px(44))
        self.quit_row = pygame.Rect(pad, self.app.size[1] - pad - theme.px(48),
                                    width - pad * 2, theme.px(48))
        button_w = theme.px(64)
        button_h = theme.px(34)
        self.edit_button = ui.Button(
            (self.url_row.right - theme.px(12) - button_w, self.url_row.centery - button_h // 2,
             button_w, button_h),
            label="Edit", style="soft", on_click=self.edit_url, size=12)
        self.refresh_button = ui.Button(
            (self.refresh_row.right - theme.px(10) - theme.px(30), self.refresh_row.centery - theme.px(15),
             theme.px(30), theme.px(30)),
            icon="refresh", style="ghost", on_click=self.refresh)
        side = theme.px(38)
        self.minus_button = ui.Button(
            (self.volume_row.right - theme.px(190), self.volume_row.centery - side // 2, side, side),
            icon="minus", style="soft", on_click=lambda: self.adjust_volume(-5))
        self.plus_button = ui.Button(
            (self.volume_row.right - theme.px(12) - side, self.volume_row.centery - side // 2, side, side),
            icon="plus", style="soft", on_click=lambda: self.adjust_volume(5))
        theme_button_w = theme.px(76)
        theme_button_h = theme.px(30)
        current_mode = self.app.config.get("display.theme", "night")
        self.theme_button = ui.Button(
            (self.theme_row.right - theme.px(12) - theme_button_w,
             self.theme_row.centery - theme_button_h // 2,
             theme_button_w, theme_button_h),
            label="Day" if current_mode == "night" else "Night",
            icon="sun" if current_mode == "night" else "moon",
            style="soft", on_click=self.app.toggle_theme, size=12)
        self.quit_button = ui.Button(self.quit_row, label="Quit app", icon="power",
                                     style="danger", on_click=self.app.quit, size=14)

    def edit_url(self):
        self.app.keyboard.open(self.app.config.get("calendar.ics_url", ""),
                               title="Calendar iCal URL", on_submit=self.save_url,
                               submit_label="Save")

    def save_url(self, value):
        self.app.config.set("calendar.ics_url", value.strip())
        if not self.save_config():
            return
        self.app.toast("Calendar URL saved")
        self.app.refresh_calendar(notify=True)

    def save_config(self):
        try:
            self.app.config.save()
            return True
        except OSError:
            self.notify("Could not save settings")
            return False

    def refresh(self):
        self.app.refresh_calendar(notify=True)

    def adjust_volume(self, delta):
        value = max(0, min(100, int(self.app.config.get("music.volume", 70)) + delta))
        self.app.config.set("music.volume", value)
        if not self.save_config():
            return
        self.app.music.player.set_volume(value)
        self.app.chime.play("tap")

    def handle(self, event):
        if self.handle_header(event):
            return True
        if ui.dispatch([self.edit_button, self.refresh_button, self.minus_button,
                        self.plus_button, self.theme_button, self.quit_button], event):
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.url_row.collidepoint(event.pos):
                self.edit_url()
                return True
            if self.refresh_row.collidepoint(event.pos):
                self.refresh()
                return True
            if self.theme_row.collidepoint(event.pos):
                self.app.toggle_theme()
                return True
        return False

    def draw(self, surface):
        theme = self.theme
        self.draw_header(surface, "Settings")
        self.draw_section(surface, theme, self.cal_header, "CALENDAR")
        ui.panel(surface, self.url_row, T.CARD, theme.px(14), T.BORDER)
        pad = theme.px(14)
        ui.text(surface, theme.font(10, bold=True), "GOOGLE CALENDAR FEED", T.FAINT,
                (self.url_row.x + pad, self.url_row.y + theme.px(12)))
        url = self.app.calendar.url or "Not connected - tap to add your public iCal link"
        color = T.TEXT if self.app.calendar.url else T.MUTED
        font = theme.font(12)
        ui.text(surface, font, ui.ellipsize(font, url, self.edit_button.rect.left - self.url_row.x - pad * 2),
                color, (self.url_row.x + pad, self.url_row.y + theme.px(34)))
        self.edit_button.draw(surface, theme)

        ui.panel(surface, self.refresh_row, T.CARD, theme.px(14), T.BORDER)
        ui.text(surface, theme.font(13), "Refresh calendar", T.TEXT,
                (self.refresh_row.x + pad, self.refresh_row.centery), "midleft")
        status = "Syncing..." if self.app.calendar_loading else self.app.calendar.updated_label()
        status_font = theme.font(10)
        ui.text(surface, status_font, status, T.FAINT,
                (self.refresh_button.rect.left - theme.px(10), self.refresh_row.centery), "midright")
        self.refresh_button.draw(surface, theme)

        self.draw_section(surface, theme, self.audio_header, "AUDIO")
        ui.panel(surface, self.volume_row, T.CARD, theme.px(14), T.BORDER)
        ui.text(surface, theme.font(13), "Volume", T.TEXT,
                (self.volume_row.x + pad, self.volume_row.centery), "midleft")
        value = int(self.app.config.get("music.volume", 70))
        ui.text(surface, theme.font(15, bold=True), f"{value}%", T.TEXT,
                ((self.minus_button.rect.right + self.plus_button.rect.left) // 2,
                 self.volume_row.centery), "center")
        self.minus_button.draw(surface, theme)
        self.plus_button.draw(surface, theme)

        self.draw_section(surface, theme, self.display_header, "DISPLAY")
        ui.panel(surface, self.theme_row, T.CARD, theme.px(14), T.BORDER)
        ui.text(surface, theme.font(13), "Theme", T.TEXT,
                (self.theme_row.x + pad, self.theme_row.centery), "midleft")
        mode = self.app.config.get("display.theme", "night")
        self.theme_button.icon = "sun" if mode == "night" else "moon"
        self.theme_button.label = "Day" if mode == "night" else "Night"
        self.theme_button.draw(surface, theme)

        self.draw_section(surface, theme, self.status_header, "PLAYER")
        ui.panel(surface, self.status_row, T.CARD, theme.px(14), T.BORDER)
        statuses = self.app.music.status()
        items = [("mpv", statuses["mpv"]), ("yt-dlp", statuses["ytdlp"])]
        column_w = self.status_row.w // 3
        for index, (name, ok) in enumerate(items):
            x = self.status_row.x + pad + index * column_w
            color = T.TEAL if ok else T.DANGER
            pygame.draw.circle(surface, color, (x + theme.px(4), self.status_row.centery), theme.px(3))
            ui.text(surface, theme.font(12), name, T.TEXT,
                    (x + theme.px(14), self.status_row.centery), "midleft")
            ui.text(surface, theme.font(10), "Ready" if ok else "Missing", color,
                    (x + theme.px(14), self.status_row.centery + theme.px(13)), "midleft")
        display_x = self.status_row.x + pad + column_w * 2
        pygame.draw.circle(surface, T.ACCENT, (display_x + theme.px(4), self.status_row.centery), theme.px(3))
        ui.text(surface, theme.font(12), "Display", T.TEXT,
                (display_x + theme.px(14), self.status_row.centery), "midleft")
        ui.text(surface, theme.font(10), f"{self.app.size[0]} x {self.app.size[1]}", T.FAINT,
                (display_x + theme.px(14), self.status_row.centery + theme.px(13)), "midleft")

        self.quit_button.draw(surface, theme)

    def draw_section(self, surface, theme, y, label):
        ui.text(surface, theme.font(9, bold=True), label, T.FAINT,
                (self.content.x + theme.px(2), y + theme.px(7)))
