import pygame

from .. import theme as T
from .. import ui


class Screen:
    def __init__(self, app):
        self.app = app
        self.theme = app.theme
        self.header_buttons = []
        self.layout()

    def layout(self):
        self.rect = pygame.Rect(0, 0, *self.app.size)
        theme = self.theme
        pad = theme.px(14)
        size = theme.px(44)
        self.back_button = ui.Button(
            (pad, (self.header_height() - size) // 2, size, size),
            icon="back",
            style="ghost",
            on_click=self.app.pop,
        )

    def header_height(self):
        return self.theme.px(62)

    def on_enter(self):
        pass

    def on_exit(self):
        pass

    def notify(self, message, seconds=2.5):
        self.app.toast(message, seconds)

    def handle(self, event):
        return False

    def update(self, dt):
        pass

    def draw(self, surface):
        pass

    def handle_header(self, event):
        return ui.dispatch([self.back_button] + self.header_buttons, event)

    def draw_header(self, surface, title, subtitle=None):
        self.back_button.draw(surface, self.theme)
        x = self.back_button.rect.right + self.theme.px(6)
        if subtitle:
            ui.text(surface, self.theme.font(20, bold=True), title, T.TEXT,
                    (x, self.header_height() // 2 - self.theme.px(8)), "midleft")
            ui.text(surface, self.theme.font(11), subtitle, T.FAINT,
                    (x, self.header_height() // 2 + self.theme.px(10)), "midleft")
        else:
            ui.text(surface, self.theme.font(20, bold=True), title, T.TEXT,
                    (x, self.header_height() // 2), "midleft")
        for button in self.header_buttons:
            button.draw(surface, self.theme)
