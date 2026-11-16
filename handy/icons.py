import math

import pygame


def arc_lines(surface, color, center, radius, start_deg, end_deg, width, steps=36):
    points = []
    for i in range(steps + 1):
        angle = math.radians(start_deg + (end_deg - start_deg) * i / steps)
        points.append((center[0] + math.cos(angle) * radius, center[1] - math.sin(angle) * radius))
    if len(points) > 1:
        pygame.draw.lines(surface, color, False, points, width)
    if width > 2:
        for point in (points[0], points[-1]):
            pygame.draw.circle(surface, color, (int(point[0]), int(point[1])), width // 2)


def _point(rect, x, y):
    return (rect.x + rect.w * x, rect.y + rect.h * y)


def draw(surface, name, rect, color, width=None):
    rect = pygame.Rect(rect)
    unit = max(2, int(min(rect.w, rect.h) * 0.085))
    line = width or unit

    if name == "back":
        pts = [_point(rect, 0.62, 0.22), _point(rect, 0.38, 0.5), _point(rect, 0.62, 0.78)]
        pygame.draw.lines(surface, color, False, pts, line)
    elif name == "chevron":
        pts = [_point(rect, 0.42, 0.26), _point(rect, 0.6, 0.5), _point(rect, 0.42, 0.74)]
        pygame.draw.lines(surface, color, False, pts, line)
    elif name == "gear":
        center = rect.center
        radius = min(rect.w, rect.h) * 0.34
        for i in range(8):
            angle = math.radians(i * 45)
            inner = (center[0] + math.cos(angle) * radius * 0.82, center[1] + math.sin(angle) * radius * 0.82)
            outer = (center[0] + math.cos(angle) * radius * 1.3, center[1] + math.sin(angle) * radius * 1.3)
            pygame.draw.line(surface, color, inner, outer, max(2, int(line * 1.1)))
        pygame.draw.circle(surface, color, center, int(radius), line)
        pygame.draw.circle(surface, color, center, max(1, int(radius * 0.32)), line)
    elif name == "calendar":
        body = pygame.Rect(rect.x + rect.w * 0.12, rect.y + rect.h * 0.2, rect.w * 0.76, rect.h * 0.68)
        pygame.draw.rect(surface, color, body, line, border_radius=unit)
        pygame.draw.line(surface, color, (body.left, body.top + body.h * 0.28), (body.right, body.top + body.h * 0.28), line)
        pygame.draw.line(surface, color, (body.left + body.w * 0.28, body.top - rect.h * 0.09), (body.left + body.w * 0.28, body.top + rect.h * 0.09), line)
        pygame.draw.line(surface, color, (body.right - body.w * 0.28, body.top - rect.h * 0.09), (body.right - body.w * 0.28, body.top + rect.h * 0.09), line)
        for x, y in ((0.3, 0.58), (0.5, 0.58), (0.7, 0.58), (0.3, 0.78), (0.5, 0.78)):
            pygame.draw.circle(surface, color, (int(body.left + body.w * x), int(body.top + body.h * y)), max(1, unit // 2))
    elif name == "timer":
        center = (rect.centerx, rect.y + rect.h * 0.56)
        radius = min(rect.w, rect.h) * 0.32
        pygame.draw.circle(surface, color, center, int(radius), line)
        pygame.draw.line(surface, color, (rect.centerx, rect.y + rect.h * 0.12), (rect.centerx, rect.y + rect.h * 0.25), line)
        pygame.draw.line(surface, color, (rect.centerx - rect.w * 0.08, rect.y + rect.h * 0.1), (rect.centerx + rect.w * 0.08, rect.y + rect.h * 0.1), line)
        pygame.draw.line(surface, color, center, (center[0], center[1] - radius * 0.62), line)
        pygame.draw.line(surface, color, center, (center[0] + radius * 0.48, center[1] + radius * 0.22), line)
    elif name == "music":
        r = min(rect.w, rect.h) * 0.105
        left = (rect.x + rect.w * 0.3, rect.y + rect.h * 0.72)
        right = (rect.x + rect.w * 0.68, rect.y + rect.h * 0.63)
        pygame.draw.circle(surface, color, left, int(r))
        pygame.draw.circle(surface, color, right, int(r))
        pygame.draw.line(surface, color, (left[0] + r, left[1]), (left[0] + r, rect.y + rect.h * 0.24), line)
        pygame.draw.line(surface, color, (right[0] + r, right[1]), (right[0] + r, rect.y + rect.h * 0.15), line)
        pygame.draw.line(surface, color, (left[0] + r, rect.y + rect.h * 0.24), (right[0] + r, rect.y + rect.h * 0.15), line)
        pygame.draw.line(surface, color, (left[0] + r, rect.y + rect.h * 0.33), (right[0] + r, rect.y + rect.h * 0.24), line)
    elif name in ("play", "pause", "next", "prev", "stop"):
        center = rect.center
        size = min(rect.w, rect.h) * 0.34
        if name == "play":
            pts = [(center[0] - size * 0.62, center[1] - size), (center[0] - size * 0.62, center[1] + size), (center[0] + size * 0.95, center[1])]
            pygame.draw.polygon(surface, color, pts)
        elif name == "pause":
            bar = size * 0.44
            pygame.draw.rect(surface, color, (center[0] - size * 0.78, center[1] - size, bar, size * 2), border_radius=int(bar * 0.35))
            pygame.draw.rect(surface, color, (center[0] + size * 0.34, center[1] - size, bar, size * 2), border_radius=int(bar * 0.35))
        elif name == "stop":
            side = size * 1.5
            pygame.draw.rect(surface, color, (center[0] - side / 2, center[1] - side / 2, side, side), border_radius=unit // 2)
        else:
            if name == "prev":
                pts = [(center[0] + size * 0.6, center[1] - size), (center[0] + size * 0.6, center[1] + size), (center[0] - size * 0.65, center[1])]
                pygame.draw.polygon(surface, color, pts)
                pygame.draw.line(surface, color, (center[0] - size * 0.78, center[1] - size), (center[0] - size * 0.78, center[1] + size), line)
            else:
                pts = [(center[0] - size * 0.6, center[1] - size), (center[0] - size * 0.6, center[1] + size), (center[0] + size * 0.65, center[1])]
                pygame.draw.polygon(surface, color, pts)
                pygame.draw.line(surface, color, (center[0] + size * 0.78, center[1] - size), (center[0] + size * 0.78, center[1] + size), line)
    elif name == "search":
        center = (rect.x + rect.w * 0.42, rect.y + rect.h * 0.42)
        radius = min(rect.w, rect.h) * 0.22
        pygame.draw.circle(surface, color, center, int(radius), line)
        pygame.draw.line(surface, color, (center[0] + radius * 0.72, center[1] + radius * 0.72), (rect.x + rect.w * 0.8, rect.y + rect.h * 0.8), line)
    elif name == "refresh":
        center = rect.center
        radius = min(rect.w, rect.h) * 0.29
        arc_lines(surface, color, center, radius, 40, 330, line, 34)
        end_angle = math.radians(40)
        tip = (center[0] + math.cos(end_angle) * radius, center[1] - math.sin(end_angle) * radius)
        pygame.draw.polygon(surface, color, [
            (tip[0] - radius * 0.46, tip[1] - radius * 0.2),
            (tip[0] + radius * 0.3, tip[1] - radius * 0.42),
            (tip[0] + radius * 0.02, tip[1] + radius * 0.34),
        ])
    elif name in ("plus", "minus"):
        pygame.draw.line(surface, color, (rect.x + rect.w * 0.26, rect.centery), (rect.right - rect.w * 0.26, rect.centery), line)
        if name == "plus":
            pygame.draw.line(surface, color, (rect.centerx, rect.y + rect.h * 0.26), (rect.centerx, rect.bottom - rect.h * 0.26), line)
    elif name == "speaker":
        pts = [
            _point(rect, 0.14, 0.4), _point(rect, 0.3, 0.4), _point(rect, 0.46, 0.24),
            _point(rect, 0.46, 0.76), _point(rect, 0.3, 0.6), _point(rect, 0.14, 0.6),
        ]
        pygame.draw.polygon(surface, color, pts)
        for factor in (0.24, 0.38):
            box = pygame.Rect(0, 0, rect.w * factor * 2, rect.h * factor * 2)
            box.center = (int(rect.x + rect.w * 0.46), rect.centery)
            pygame.draw.arc(surface, color, box, math.radians(-55), math.radians(55), max(2, line // 2))
    elif name == "power":
        center = (rect.centerx, rect.y + rect.h * 0.55)
        radius = min(rect.w, rect.h) * 0.29
        arc_lines(surface, color, center, radius, 55, 305, line, 30)
        pygame.draw.line(surface, color, (rect.centerx, rect.y + rect.h * 0.18), (rect.centerx, rect.y + rect.h * 0.52), line)
    elif name == "close":
        pygame.draw.line(surface, color, _point(rect, 0.3, 0.3), _point(rect, 0.7, 0.7), line)
        pygame.draw.line(surface, color, _point(rect, 0.7, 0.3), _point(rect, 0.3, 0.7), line)
    elif name == "check":
        pygame.draw.lines(surface, color, False, [_point(rect, 0.24, 0.52), _point(rect, 0.44, 0.72), _point(rect, 0.76, 0.3)], line)
    elif name == "wifi":
        center = (rect.centerx, rect.y + rect.h * 0.72)
        pygame.draw.circle(surface, color, center, max(2, line // 2 + 1))
        for i, factor in enumerate((0.2, 0.34, 0.48)):
            box = pygame.Rect(0, 0, rect.w * factor * 2, rect.h * factor * 2)
            box.center = (center[0], center[1])
            pygame.draw.arc(surface, color, box, math.radians(45), math.radians(135), max(2, line // 2))
    elif name == "clock":
        center = rect.center
        radius = min(rect.w, rect.h) * 0.34
        pygame.draw.circle(surface, color, center, int(radius), line)
        pygame.draw.line(surface, color, center, (center[0], center[1] - radius * 0.55), line)
        pygame.draw.line(surface, color, center, (center[0] + radius * 0.42, center[1]), line)
    elif name == "exit":
        pygame.draw.rect(surface, color, (rect.x + rect.w * 0.18, rect.y + rect.h * 0.2, rect.w * 0.4, rect.h * 0.6), line, border_radius=unit)
        pygame.draw.line(surface, color, (rect.x + rect.w * 0.48, rect.centery), (rect.x + rect.w * 0.82, rect.centery), line)
        pygame.draw.lines(surface, color, False, [_point(rect, 0.68, 0.38), _point(rect, 0.82, 0.5), _point(rect, 0.68, 0.62)], line)
    elif name == "sun":
        center = rect.center
        radius = min(rect.w, rect.h) * 0.22
        pygame.draw.circle(surface, color, center, int(radius), line)
        for i in range(8):
            angle = math.radians(i * 45)
            inner = (center[0] + math.cos(angle) * radius * 1.45, center[1] + math.sin(angle) * radius * 1.45)
            outer = (center[0] + math.cos(angle) * radius * 1.95, center[1] + math.sin(angle) * radius * 1.95)
            pygame.draw.line(surface, color, inner, outer, max(2, int(line * 0.9)))
    elif name == "moon":
        size = int(min(rect.w, rect.h) * 0.88)
        layer = pygame.Surface((size, size), pygame.SRCALPHA)
        radius = size // 2
        offset = max(1, size // 5)
        margin = max(1, line // 2)
        pygame.draw.circle(layer, (*color, 255), (radius, radius), max(1, radius - margin))
        cutter = pygame.Surface((size, size), pygame.SRCALPHA)
        cutter.fill((255, 255, 255, 255))
        pygame.draw.circle(cutter, (0, 0, 0, 0), (radius + offset, radius - offset // 2), max(1, radius - margin))
        layer.blit(cutter, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(layer, (rect.centerx - size // 2, rect.centery - size // 2))
