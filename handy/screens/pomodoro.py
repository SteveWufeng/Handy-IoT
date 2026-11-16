import pygame

from .. import icons, ui
from .. import theme as T
from .base import Screen


class PomodoroScreen(Screen):
    def __init__(self, app):
        self.timer = app.pomodoro
        super().__init__(app)

    def layout(self):
        super().layout()
        theme = self.theme
        pad = theme.px(18)
        button_h = theme.px(54)
        button_y = self.app.size[1] - pad - button_h
        primary_w = min(theme.px(210), self.app.size[0] - theme.px(190))
        primary = pygame.Rect(self.app.size[0] // 2 - primary_w // 2, button_y, primary_w, button_h)
        gap = theme.px(16)
        side = button_h
        self.start_button = ui.Button(primary, label="Start", style="accent",
                                      on_click=self.timer.toggle, size=16, radius=16)
        self.reset_button = ui.Button(
            (primary.left - gap - side, button_y, side, side), icon="refresh",
            style="ghost", on_click=self.timer.reset)
        self.skip_button = ui.Button(
            (primary.right + gap, button_y, side, side), icon="next",
            style="ghost", on_click=self.timer.skip)
        top = self.header_height() + theme.px(18)
        bottom = button_y - theme.px(26)
        self.center = (self.app.size[0] // 2, int((top + bottom) / 2))
        self.radius = int(min(self.app.size[0] * 0.27, (bottom - top) * 0.4))

    def handle(self, event):
        if self.handle_header(event):
            return True
        return ui.dispatch([self.start_button, self.reset_button, self.skip_button], event)

    def draw(self, surface):
        theme = self.theme
        self.draw_header(surface, "Pomodoro")
        timer = self.timer
        accent = T.TEAL if timer.phase != "work" else T.ACCENT
        width = max(3, theme.px(10))
        pygame.draw.circle(surface, T.CARD_HI, self.center, self.radius, width)
        if timer.progress > 0:
            end_angle = 90 - 360 * timer.progress
            icons.arc_lines(surface, accent, self.center, self.radius, 90, end_angle, width, 90)
        phase_font = theme.font(11, bold=True)
        ui.text(surface, phase_font, timer.phase_label().upper(), accent,
                (self.center[0], self.center[1] - self.radius - theme.px(14)), "center")
        time_font = theme.font(54, bold=True)
        ui.text(surface, time_font, timer.clock(), T.TEXT, (self.center[0], self.center[1] + theme.px(2)), "center")
        ui.text(surface, theme.font(11), timer.session_label(), T.MUTED,
                (self.center[0], self.center[1] + self.radius * 0.46), "center")
        self.draw_cycles(surface, theme, accent)
        self.start_button.label = "Pause" if timer.running else "Start"
        self.start_button.style = "teal" if timer.phase != "work" else "accent"
        for button in (self.reset_button, self.skip_button, self.start_button):
            button.draw(surface, theme)

    def draw_cycles(self, surface, theme, accent):
        timer = self.timer
        y = self.center[1] + self.radius + theme.px(22)
        gap = theme.px(14)
        radius = max(3, theme.px(4))
        total = timer.cycles()
        completed = timer.completed % total
        if timer.completed and timer.phase == "work" and timer.completed % total == 0:
            completed = 0
        start_x = self.center[0] - (total - 1) * gap // 2
        for index in range(total):
            x = start_x + index * gap
            if index < completed:
                pygame.draw.circle(surface, accent, (x, y), radius)
            else:
                pygame.draw.circle(surface, T.BORDER, (x, y), radius, max(1, theme.px(1)))
        hint = "Stay with it" if timer.phase == "work" else "Step away and breathe"
        ui.text(surface, theme.font(11), hint, T.FAINT,
                (self.center[0], y + theme.px(20)), "center")
