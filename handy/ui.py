import math
from typing import ClassVar

import pygame

from . import icons
from . import theme as T


def text(surface, font, value, color, pos, anchor="topleft"):
    image = font.render(value, True, color)
    rect = image.get_rect(**{anchor: pos})
    surface.blit(image, rect)
    return rect


def ellipsize(font, value, max_width):
    if max_width <= 0:
        return ""
    if font.size(value)[0] <= max_width:
        return value
    lo, hi = 0, len(value)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if font.size(value[:mid] + "...")[0] <= max_width:
            lo = mid
        else:
            hi = mid - 1
    return value[:lo].rstrip() + "..."


def wrap(font, value, max_width, max_lines=2):
    words = value.split()
    lines = []
    current = ""
    index = 0
    while index < len(words):
        word = words[index]
        candidate = (current + " " + word).strip()
        if font.size(candidate)[0] <= max_width:
            current = candidate
            index += 1
            continue
        if current:
            lines.append(current)
            current = ""
            if len(lines) == max_lines:
                remaining = " ".join(words[index:])
                lines[-1] = ellipsize(font, lines[-1] + " " + remaining, max_width)
                return lines
        else:
            lines.append(ellipsize(font, word, max_width))
            index += 1
            if len(lines) == max_lines:
                return lines
    if current and len(lines) < max_lines:
        lines.append(current)
    return lines


def panel(surface, rect, color, radius=0, border=None, border_width=1):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border is not None:
        pygame.draw.rect(surface, border, rect, width=border_width, border_radius=radius)


def blend(a, b, amount):
    return (
        int(a[0] + (b[0] - a[0]) * amount),
        int(a[1] + (b[1] - a[1]) * amount),
        int(a[2] + (b[2] - a[2]) * amount),
    )


def rounded_image(surface, image, rect, radius):
    rect = pygame.Rect(rect)
    scaled = pygame.transform.smoothscale(image, rect.size)
    layer = pygame.Surface(rect.size, pygame.SRCALPHA)
    layer.blit(scaled, (0, 0))
    mask = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(layer, rect.topleft)


def format_duration(seconds):
    seconds = max(0, int(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def clock_time(seconds):
    seconds = max(0, math.ceil(seconds))
    minutes, secs = divmod(seconds, 60)
    return f"{minutes:02d}:{secs:02d}"


class Button:
    def __init__(self, rect, label=None, icon=None, on_click=None, style="card", size=16,
                 radius=14, enabled=True, selected=False):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.icon = icon
        self.on_click = on_click
        self.style = style
        self.size = size
        self.radius = radius
        self.enabled = enabled
        self.selected = selected
        self.down = False

    def hit(self, pos):
        return self.rect.collidepoint(pos)

    def mousedown(self, pos):
        if not self.enabled:
            return False
        if self.hit(pos):
            self.down = True
            return True
        return False

    def mouseup(self, pos):
        if not self.down:
            return False
        self.down = False
        if self.hit(pos) and self.on_click:
            self.on_click()
        return True

    def cancel(self):
        self.down = False

    def draw(self, surface, theme):
        styles = {
            "card": (T.CARD, T.CARD_PRESS, T.TEXT, T.BORDER),
            "accent": (T.ACCENT, T.ACCENT_HI, T.WHITE, None),
            "ghost": (None, T.CARD, T.MUTED, None),
            "soft": (T.ACCENT_SOFT, T.SOFT_PRESS, T.TEXT, None),
            "danger": (None, T.DANGER_PRESS, T.DANGER, None),
            "teal": (T.TEAL, T.TEAL_PRESS, T.TEAL_TEXT, None),
        }
        background, pressed, foreground, border = styles.get(self.style, styles["card"])
        if self.selected:
            background = T.ACCENT_SOFT
            foreground = T.TEXT
        if not self.enabled:
            foreground = T.FAINT
        if self.down:
            background = pressed
        radius = theme.px(self.radius)
        if background is not None:
            panel(surface, self.rect, background, radius, border)
        elif self.down:
            panel(surface, self.rect, T.CARD, radius)
        content_rect = self.rect.inflate(-theme.px(14), -theme.px(10))
        font = theme.font(self.size, bold=True)
        if self.icon and self.label:
            icon_size = min(content_rect.h, theme.px(22))
            gap = theme.px(8)
            label_w = font.size(self.label)[0]
            total = icon_size + gap + label_w
            x = self.rect.centerx - total // 2
            icons.draw(surface, self.icon, pygame.Rect(x, self.rect.centery - icon_size // 2, icon_size, icon_size), foreground)
            text(surface, font, self.label, foreground, (x + icon_size + gap, self.rect.centery), "midleft")
        elif self.icon:
            icon_size = int(min(self.rect.w, self.rect.h) * 0.52)
            icons.draw(surface, self.icon, pygame.Rect(0, 0, icon_size, icon_size).move(
                self.rect.centerx - icon_size // 2, self.rect.centery - icon_size // 2), foreground)
        elif self.label:
            text(surface, font, ellipsize(font, self.label, content_rect.w), foreground, self.rect.center, "center")


class Chip:
    def __init__(self, rect, label, on_click):
        self.rect = pygame.Rect(rect)
        self.label = label
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
        if self.rect.collidepoint(pos) and self.on_click:
            self.on_click()
        return True

    def draw(self, surface, theme):
        background = T.CARD_PRESS if self.down else T.CARD
        panel(surface, self.rect, background, self.rect.h // 2, T.BORDER)
        font = theme.font(12, bold=False)
        value = ellipsize(font, self.label, self.rect.w - theme.px(22))
        text(surface, font, value, T.MUTED, self.rect.center, "center")


class TextField:
    def __init__(self, rect, placeholder="", icon="search"):
        self.rect = pygame.Rect(rect)
        self.placeholder = placeholder
        self.icon = icon

    def draw(self, surface, theme, value, active=False):
        panel(surface, self.rect, T.CARD_HI if active else T.CARD, theme.px(14), T.ACCENT if active else T.BORDER)
        icon_size = min(self.rect.h - theme.px(14), theme.px(22))
        icon_rect = pygame.Rect(self.rect.x + theme.px(14), self.rect.centery - icon_size // 2, icon_size, icon_size)
        if self.icon:
            icons.draw(surface, self.icon, icon_rect, T.ACCENT if active else T.MUTED)
        font = theme.font(15)
        left = icon_rect.right + theme.px(10)
        available = self.rect.right - left - theme.px(14)
        shown = value if value else self.placeholder
        color = T.TEXT if value else T.FAINT
        value_rect = text(surface, font, ellipsize(font, shown, available), color, (left, self.rect.centery), "midleft")
        if active:
            caret_x = min(value_rect.right + theme.px(1), self.rect.right - theme.px(10))
            pygame.draw.line(surface, T.ACCENT, (caret_x, self.rect.centery - theme.px(10)),
                             (caret_x, self.rect.centery + theme.px(10)), max(2, theme.px(2)))


class ScrollModel:
    def __init__(self):
        self.offset = 0.0
        self.max_offset = 0.0
        self.velocity = 0.0
        self.dragging = False
        self._last = 0.0

    def configure(self, content_height, view_height):
        self.max_offset = max(0.0, content_height - view_height)
        self.offset = min(max(0.0, self.offset), self.max_offset)

    def begin(self, y):
        self.dragging = True
        self._last = y
        self.velocity = 0.0

    def move(self, y):
        if not self.dragging:
            return
        delta = y - self._last
        self._last = y
        self.offset = min(max(0.0, self.offset - delta), self.max_offset)
        self.velocity = -delta

    def end(self):
        self.dragging = False

    def scroll(self, amount):
        self.offset = min(max(0.0, self.offset + amount), self.max_offset)
        self.velocity = 0.0

    def update(self, dt):
        if self.dragging or abs(self.velocity) < 0.8:
            return
        factor = max(0.5, min(3.0, dt * 60))
        self.offset = min(max(0.0, self.offset + self.velocity * factor), self.max_offset)
        self.velocity *= 0.86 ** factor

    def reset(self):
        self.offset = 0.0
        self.velocity = 0.0
        self.dragging = False


def dispatch(buttons, event):
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        for button in buttons:
            if button.mousedown(event.pos):
                return True
    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
        handled = False
        for button in buttons:
            if button.mouseup(event.pos):
                handled = True
        return handled
    return False


def draw_spinner(surface, center, radius, color, phase, width=4):
    icons.arc_lines(surface, color, center, radius, phase * 360, phase * 360 + 270, max(2, width), 28)


class Keyboard:
    LETTER_ROWS: ClassVar[list] = [
        [("q", 1), ("w", 1), ("e", 1), ("r", 1), ("t", 1), ("y", 1), ("u", 1), ("i", 1), ("o", 1), ("p", 1)],
        [("a", 1), ("s", 1), ("d", 1), ("f", 1), ("g", 1), ("h", 1), ("j", 1), ("k", 1), ("l", 1)],
        [("shift", 1.5), ("z", 1), ("x", 1), ("c", 1), ("v", 1), ("b", 1), ("n", 1), ("m", 1), ("back", 1.5)],
        [("layer", 1.5), ("space", 5.5), ("dot", 1), ("search", 2.2)],
    ]

    NUMBER_ROWS: ClassVar[list] = [
        [("1", 1), ("2", 1), ("3", 1), ("4", 1), ("5", 1), ("6", 1), ("7", 1), ("8", 1), ("9", 1), ("0", 1)],
        [("-", 1), ("/", 1), (":", 1), (";", 1), ("(", 1), (")", 1), ("$", 1), ("&", 1), ("@", 1), ("_", 1)],
        [("letters", 1.5), (".", 1), (",", 1), ("?", 1), ("!", 1), ("'", 1), ('"', 1), ("+", 1), ("back", 1.5)],
        [("space", 5.5), ("dot", 1), ("search", 2.2)],
    ]

    def __init__(self, app):
        self.app = app
        self.visible = False
        self.title = ""
        self.text = ""
        self.on_change = None
        self.on_submit = None
        self.submit_label = "Search"
        self.clear_button = None
        self.shift = False
        self.layer = 0
        self.keys = []
        self.pressed = None
        self.close_button = None
        self.panel_rect = pygame.Rect(0, 0, 0, 0)
        self.dim = None
        self.layout()

    def layout(self):
        w, h = self.app.size
        theme = self.app.theme
        radius = theme.px(20)
        panel_height = max(theme.px(196), int(h * 0.46))
        panel_height = min(panel_height, theme.px(340))
        self.panel_rect = pygame.Rect(0, h - panel_height, w, panel_height + radius)
        self.dim = pygame.Surface((w, h), pygame.SRCALPHA)
        self.dim.fill((0, 0, 0, 120))
        self.build_keys()

    def build_keys(self):
        if self.panel_rect.w == 0:
            return
        theme = self.app.theme
        pad = theme.px(10)
        gap = theme.px(6)
        title_height = theme.px(30)
        top = self.panel_rect.top + title_height + pad
        bottom = self.app.size[1] - pad
        rows = self.NUMBER_ROWS if self.layer else self.LETTER_ROWS
        row_count = len(rows)
        key_height = max(theme.px(30), (bottom - top - gap * (row_count - 1)) / row_count)
        self.keys = []
        self.close_button = pygame.Rect(self.panel_rect.right - pad - theme.px(30), self.panel_rect.top + pad,
                                        theme.px(30), theme.px(30))
        self.clear_button = pygame.Rect(self.close_button.left - theme.px(8) - theme.px(58),
                                        self.panel_rect.top + pad, theme.px(58), theme.px(30))
        for r, row in enumerate(rows):
            total_weight = sum(weight for _, weight in row)
            available = self.panel_rect.w - pad * 2 - gap * (len(row) - 1)
            unit = available / total_weight
            x = pad
            y = top + r * (key_height + gap)
            for key, weight in row:
                width = unit * weight
                self.keys.append((key, pygame.Rect(int(x), int(y), int(width), int(key_height))))
                x += width + gap

    def open(self, text, on_change=None, on_submit=None, title="", submit_label="Search"):
        self.text = text or ""
        self.on_change = on_change
        self.on_submit = on_submit
        self.title = title
        self.submit_label = submit_label
        self.shift = False
        self.layer = 0
        self.visible = True
        self.pressed = None
        self.build_keys()

    def close(self):
        self.visible = False
        self.on_change = None
        self.on_submit = None
        self.pressed = None

    def _label(self, key):
        labels = {
            "shift": "SHIFT",
            "back": "DEL",
            "layer": "123",
            "letters": "ABC",
            "space": "space",
            "dot": ".",
            "search": self.submit_label,
        }
        if key in labels:
            return labels[key]
        if self.layer == 0 and self.shift and len(key) == 1:
            return key.upper()
        return key

    def _activate(self, key):
        if key == "shift":
            self.shift = not self.shift
            self.build_keys()
            return
        if key == "layer":
            self.layer = 1
            self.shift = False
            self.build_keys()
            return
        if key == "letters":
            self.layer = 0
            self.build_keys()
            return
        if key == "back":
            self.text = self.text[:-1]
        elif key == "space":
            self.text += " "
        elif key == "dot":
            self.text += "."
        elif key == "search":
            submit = self.on_submit
            value = self.text
            self.close()
            if submit:
                submit(value)
            return
        else:
            self.text += key.upper() if self.shift else key
        if self.on_change:
            self.on_change(self.text)

    def handle(self, event):
        if not self.visible:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_button.collidepoint(event.pos):
                self.close()
                return True
            if self.clear_button.collidepoint(event.pos):
                self.text = ""
                if self.on_change:
                    self.on_change("")
                return True
            if not self.panel_rect.collidepoint(event.pos):
                self.close()
                return True
            for key, rect in self.keys:
                if rect.collidepoint(event.pos):
                    self.pressed = key
                    self._activate(key)
                    return True
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.pressed = None
            return True
        if event.type == pygame.MOUSEMOTION:
            return self.panel_rect.collidepoint(event.pos) or self.pressed is not None
        if event.type == pygame.MOUSEWHEEL:
            return False
        return False

    def draw(self, surface):
        if not self.visible:
            return
        theme = self.app.theme
        surface.blit(self.dim, (0, 0))
        panel(surface, self.panel_rect, T.CARD, theme.px(18), T.BORDER)
        font = theme.font(12, bold=True)
        text(surface, font, self.title.upper() if self.title else "", T.FAINT,
             (theme.px(16), self.panel_rect.top + theme.px(20)), "midleft")
        icons.draw(surface, "close", self.close_button.inflate(-theme.px(6), -theme.px(6)), T.MUTED)
        small_font = theme.font(11, bold=True)
        text(surface, small_font, "CLEAR", T.FAINT, self.clear_button.center, "center")
        key_font = theme.font(17, bold=False)
        small_font = theme.font(11, bold=True)
        for key, rect in self.keys:
            special = key in ("shift", "back", "layer", "letters", "space", "search")
            background = T.CARD_HI
            foreground = T.TEXT
            if key == "search":
                background = T.ACCENT
                foreground = T.WHITE
            elif key in ("shift", "layer", "letters") and (
                    (key == "shift" and self.shift) or (key == "layer" and self.layer == 1) or
                    (key == "letters" and self.layer == 0)):
                background = T.ACCENT_SOFT
            if self.pressed == key:
                background = T.ACCENT_SOFT if key != "search" else T.ACCENT_HI
            panel(surface, rect, background, theme.px(9))
            label = self._label(key)
            active_font = small_font if special else key_font
            text(surface, active_font, label, foreground, rect.center, "center")
