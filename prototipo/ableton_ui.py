"""Dibuja el modo Ableton con gráficos: faders en el mixer y knobs en los dispositivos.

Usa el estado JSON que manda el script CustomMaschineMK3 (ver ableton_text.py).
Cada pantalla tiene 4 columnas de 120 px, una por perilla (izquierda: perillas
1-4, derecha: 5-8), así cada control queda arriba de su perilla.

Las vistas que no son mixer ni dispositivo (clip, browser, settings...) y los
modos del encoder (volumen master, tempo...) se siguen mostrando con texto.
"""

import math
import time

from PIL import Image, ImageDraw, ImageFont

from maschine_display import HEIGHT, WIDTH

MIXER_VIEW = "default"
DEVICE_VIEW = "device"
GRAPHIC_VIEWS = (MIXER_VIEW, DEVICE_VIEW)
# Modos del encoder grande que tapan la pantalla con su valor (VOLUME, SWING, TEMPO, escala): ahí va texto.
# Los demás (mixer "default", dispositivo "device", posición...) dejan ver los gráficos.
TEXT_ENCODER_MODES = ("volume", "swing", "tempo", "scale")

COLUMNS = 4
COLUMN_WIDTH = WIDTH // COLUMNS
HEADER_HEIGHT = 28

BACKGROUND = (0, 0, 0)
HEADER_BACKGROUND = (28, 28, 28)
TEXT = (235, 235, 235)
DIM_TEXT = (140, 140, 140)
GROOVE = (55, 55, 55)
ACCENT = (255, 150, 30)  # naranja de Ableton para valores
TOUCHED = (255, 255, 255)
METER_GREEN = (60, 200, 90)
METER_YELLOW = (230, 200, 40)
METER_RED = (230, 50, 40)
DEFAULT_TRACK_COLOR = (120, 120, 120)

_fonts = {}


def _font(size, bold=False):
    key = (size, bold)
    if key not in _fonts:
        try:
            _fonts[key] = ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", size)
        except OSError:
            _fonts[key] = ImageFont.load_default()
    return _fonts[key]


def screen_kind(state):
    """Qué dibujar: "session" (grilla de clips), "controls" (faders / knobs) o None (texto)."""
    if state is None:
        return None
    # ARRANGER prende la vista session: se ve la grilla hasta apretar otro botón de vista
    if state.get("session_view") and state.get("session"):
        return "session"
    if state.get("encoder_mode") in TEXT_ENCODER_MODES:
        return None
    if state.get("view") in GRAPHIC_VIEWS:
        return "controls"
    return None


def wants_graphics(state):
    return screen_kind(state) is not None


def _track_rgb(color):
    if color is None:
        return DEFAULT_TRACK_COLOR
    return ((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)


def _text_color_on(rgb):
    return (0, 0, 0) if sum(rgb) > 380 else (255, 255, 255)


def _fit_text(draw, text, font, width):
    text = text or ""
    if draw.textlength(text, font=font) <= width:
        return text
    while text and draw.textlength(text + "..", font=font) > width:
        text = text[:-1]
    return text + ".."


def _centered(draw, text, center_x, y, font, fill, width=COLUMN_WIDTH - 8):
    text = _fit_text(draw, text, font, width)
    draw.text((center_x - draw.textlength(text, font=font) / 2, y), text, font=font, fill=fill)


def _header(draw, left_text, right_text=None, color=None):
    draw.rectangle((0, 0, WIDTH, HEADER_HEIGHT - 1), fill=HEADER_BACKGROUND)
    x = 8
    if color is not None:
        draw.rectangle((8, 7, 21, 20), fill=color)
        x = 28
    draw.text((x, 5), _fit_text(draw, left_text, _font(17, True), WIDTH - x - 120), font=_font(17, True), fill=TEXT)
    if right_text:
        width = draw.textlength(right_text, font=_font(15))
        draw.text((WIDTH - 8 - width, 7), right_text, font=_font(15), fill=DIM_TEXT)


def _meter_color(level):
    if level > 0.92:
        return METER_RED
    if level > 0.75:
        return METER_YELLOW
    return METER_GREEN


def _draw_fader(draw, column, knob, touched):
    x0 = column * COLUMN_WIDTH
    center = x0 + COLUMN_WIDTH // 2
    color = _track_rgb(knob.get("color"))

    # Valor arriba; abajo, cerca de la perilla, el nombre del track sobre una franja de su color
    _centered(draw, knob.get("text"), center, HEADER_HEIGHT + 6, _font(17, True), TOUCHED if touched else TEXT)
    name_top = HEIGHT - 30
    draw.rectangle((x0 + 4, name_top, x0 + COLUMN_WIDTH - 5, name_top + 24), fill=color)
    _centered(draw, knob.get("track") or knob.get("name"), center, name_top + 4, _font(15, True), _text_color_on(color))

    area_top, area_bottom = HEADER_HEIGHT + 34, name_top - 8
    value = max(0.0, min(1.0, knob.get("value", 0.0)))

    if knob.get("bipolar"):
        # Paneo: barra horizontal desde el centro
        y = (area_top + area_bottom) // 2
        left, right = x0 + 14, x0 + COLUMN_WIDTH - 14
        draw.rectangle((left, y - 3, right, y + 3), fill=GROOVE)
        position = left + value * (right - left)
        middle = (left + right) / 2
        draw.rectangle((min(middle, position), y - 6, max(middle, position), y + 6), fill=ACCENT)
        draw.rectangle((position - 3, y - 12, position + 3, y + 12), fill=TOUCHED if touched else TEXT)
    else:
        # Fader: canal con el relleno del valor y la perilla del fader
        groove_x = center - 14
        draw.rectangle((groove_x - 3, area_top, groove_x + 3, area_bottom), fill=GROOVE)
        y = area_bottom - value * (area_bottom - area_top)
        draw.rectangle((groove_x - 3, y, groove_x + 3, area_bottom), fill=color)
        draw.rectangle((groove_x - 14, y - 5, groove_x + 14, y + 5), fill=TOUCHED if touched else (200, 200, 200))

    # Medidor de nivel del track
    if "meter" in knob:
        meter_x = center + 18
        level = max(0.0, min(1.0, knob["meter"]))
        draw.rectangle((meter_x, area_top, meter_x + 10, area_bottom), fill=(25, 25, 25))
        if level > 0:
            y = area_bottom - level * (area_bottom - area_top)
            draw.rectangle((meter_x, y, meter_x + 10, area_bottom), fill=_meter_color(level))

    if touched:
        draw.rectangle((x0 + 2, HEADER_HEIGHT + 1, x0 + COLUMN_WIDTH - 3, HEIGHT - 2), outline=TOUCHED, width=2)


def _draw_knob(draw, column, knob, touched, color, label, meter=None):
    """Knob con arco del color del track: valor arriba, nombre abajo sobre una franja de ese color.

    En el mixer (paneo, envíos) label es el track y va su medidor al costado; en un
    dispositivo, label es el nombre del parámetro.
    """
    x0 = column * COLUMN_WIDTH
    center_x = x0 + COLUMN_WIDTH // 2
    _centered(draw, knob.get("text"), center_x, HEADER_HEIGHT + 6, _font(17, True), TOUCHED if touched else TEXT)
    name_top = HEIGHT - 30
    draw.rectangle((x0 + 4, name_top, x0 + COLUMN_WIDTH - 5, name_top + 24), fill=color)
    _centered(draw, label, center_x, name_top + 4, _font(15, True), _text_color_on(color))

    if meter is not None:
        meter_x, top, bottom = x0 + COLUMN_WIDTH - 16, HEADER_HEIGHT + 34, name_top - 8
        level = max(0.0, min(1.0, meter))
        draw.rectangle((meter_x, top, meter_x + 8, bottom), fill=(25, 25, 25))
        if level > 0:
            draw.rectangle((meter_x, bottom - level * (bottom - top), meter_x + 8, bottom), fill=_meter_color(level))
        center_x -= 8

    center_y, radius = 144, 40
    box = (center_x - radius, center_y - radius, center_x + radius, center_y + radius)
    start, end = 135, 405  # 270 grados, con el hueco abajo (PIL mide en sentido horario desde las 3)
    value = max(0.0, min(1.0, knob.get("value", 0.0)))
    angle = start + value * (end - start)
    width = 9
    arc_color = _visible(color)
    draw.arc(box, start, end, fill=GROOVE, width=width)
    if knob.get("bipolar"):
        middle = (start + end) / 2
        if angle != middle:
            draw.arc(box, min(middle, angle), max(middle, angle), fill=arc_color, width=width)
    elif angle > start:
        draw.arc(box, start, angle, fill=arc_color, width=width)

    # Indicador desde el centro
    rad = math.radians(angle)
    inner, outer = radius * 0.25, radius * 0.75
    draw.line((center_x + inner * math.cos(rad), center_y + inner * math.sin(rad),
               center_x + outer * math.cos(rad), center_y + outer * math.sin(rad)),
              fill=TOUCHED if touched else TEXT, width=4)

    if touched:
        draw.rectangle((x0 + 2, HEADER_HEIGHT + 1, x0 + COLUMN_WIDTH - 3, HEIGHT - 2), outline=TOUCHED, width=2)


def _visible(rgb):
    """Un color de track muy oscuro no se ve sobre negro: se aclara lo justo."""
    brightness = max(rgb)
    if brightness >= 90:
        return rgb
    if brightness == 0:
        return (90, 90, 90)
    scale = 90 / brightness
    return tuple(min(255, int(channel * scale)) for channel in rgb)


def _is_volume(knob):
    return "volume" in (knob.get("name") or "").lower()


SESSION_ROWS = 4
TRACK_STRIP_HEIGHT = 26
EMPTY_SLOT = (30, 30, 30)
PLAYING = (60, 220, 90)
PADS_FRAME = (0, 230, 80)  # marco de las columnas que están en los pads
PADS_FRAME_WIDTH = 4
RECORDING = (230, 50, 40)
BLINK_SECONDS = 0.25


def _dim(rgb, factor):
    return tuple(int(channel * factor) for channel in rgb)


def _draw_clip(draw, box, slot, dim):
    x0, y0, x1, y1 = box
    if slot is None:
        return
    if slot.get("empty"):
        draw.rectangle(box, fill=_dim(EMPTY_SLOT, dim))
        if slot.get("triggered") and int(time.perf_counter() / BLINK_SECONDS) % 2:
            draw.rectangle(box, outline=TEXT, width=2)
        return
    color = _dim(_track_rgb(slot.get("color")), dim)
    blink_off = slot.get("triggered") and int(time.perf_counter() / BLINK_SECONDS) % 2
    draw.rectangle(box, fill=_dim(color, 0.45) if blink_off else color)
    text_color = _text_color_on(color)
    left = x0 + 6
    if slot.get("recording"):
        draw.ellipse((x0 + 6, y0 + 7, x0 + 18, y0 + 19), fill=RECORDING, outline=(255, 255, 255))
        left = x0 + 24
    elif slot.get("playing"):
        draw.polygon(((x0 + 7, y0 + 6), (x0 + 7, y0 + 20), (x0 + 19, y0 + 13)), fill=text_color)
        left = x0 + 24
    font = _font(15, True)
    name = _fit_text(draw, slot.get("name") or "", font, x1 - left - 4)
    draw.text((left, y0 + 5), name, font=font, fill=text_color)
    if slot.get("playing") or slot.get("recording"):
        # Blanco y no verde: el verde marca la zona de los pads
        draw.rectangle(box, outline=TEXT if slot.get("playing") else RECORDING, width=3)


def render_session(state, display):
    """Grilla de clips: un bloque fijo de 8 tracks (4 por pantalla) x 4 escenas. Las columnas que están
    en los pads se ven normales y las demás, más tenues; mover los pads dentro del bloque solo mueve el resaltado."""
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    session = state.get("session") or {}
    tracks = session.get("tracks") or []
    ring_start = session.get("ring_column", 0)
    ring_end = ring_start + session.get("ring_tracks", COLUMNS)
    row_height = (HEIGHT - TRACK_STRIP_HEIGHT) // SESSION_ROWS
    for column in range(COLUMNS):
        index = display * COLUMNS + column
        track = tracks[index] if index < len(tracks) else None
        dim = 1.0 if ring_start <= index < ring_end else 0.65
        x0 = column * COLUMN_WIDTH
        if track is None:
            continue
        color = _dim(_track_rgb(track.get("color")), dim)
        draw.rectangle((x0 + 2, 0, x0 + COLUMN_WIDTH - 3, TRACK_STRIP_HEIGHT - 3), fill=color)
        _centered(draw, track.get("name"), x0 + COLUMN_WIDTH // 2, 4, _font(14, True), _text_color_on(color))
        slots = track.get("slots") or []
        for row in range(SESSION_ROWS):
            top = TRACK_STRIP_HEIGHT + row * row_height
            box = (x0 + 2, top + 2, x0 + COLUMN_WIDTH - 3, top + row_height - 3)
            _draw_clip(draw, box, slots[row] if row < len(slots) else None, dim)

    _draw_pads_frame(draw, display, ring_start, ring_end)

    # Pop-up del volumen de la perilla que se toca, en la otra pantalla (no tapa la columna que se mira)
    touched = state.get("touched", -1)
    knobs = state.get("knobs") or []
    if 0 <= touched < len(knobs) and knobs[touched] and touched // COLUMNS != display:
        _draw_volume_popup(draw, knobs[touched])
    return image


def _draw_pads_frame(draw, display, ring_start, ring_end):
    """Marco verde alrededor de las columnas que están en los pads. Si siguen en la otra pantalla,
    ese lado queda abierto, así el marco se lee como uno solo entre las dos."""
    first_on_screen = display * COLUMNS
    first = max(ring_start, first_on_screen)
    last = min(ring_end, first_on_screen + COLUMNS) - 1
    if first > last:
        return
    left = (first - first_on_screen) * COLUMN_WIDTH
    right = (last - first_on_screen + 1) * COLUMN_WIDTH - 1
    top, bottom, width = 0, HEIGHT - 1, PADS_FRAME_WIDTH
    draw.rectangle((left, top, right, top + width - 1), fill=PADS_FRAME)
    draw.rectangle((left, bottom - width + 1, right, bottom), fill=PADS_FRAME)
    if first == ring_start:
        draw.rectangle((left, top, left + width - 1, bottom), fill=PADS_FRAME)
    if last == ring_end - 1:
        draw.rectangle((right - width + 1, top, right, bottom), fill=PADS_FRAME)


def _draw_volume_popup(draw, knob):
    color = _track_rgb(knob.get("color"))
    left, top, right, bottom = 40, 46, WIDTH - 40, HEIGHT - 46
    draw.rectangle((left, top, right, bottom), fill=(18, 18, 18), outline=TEXT, width=2)
    draw.rectangle((left + 2, top + 2, right - 2, top + 34), fill=color)
    _centered(draw, knob.get("track") or knob.get("name"), WIDTH // 2, top + 8, _font(19, True),
              _text_color_on(color), width=right - left - 16)
    _centered(draw, knob.get("text"), WIDTH // 2, top + 44, _font(34, True), TEXT, width=right - left - 16)

    # Barra de volumen con el medidor del track debajo
    bar_left, bar_right, bar_top = left + 20, right - 20, bottom - 52
    value = max(0.0, min(1.0, knob.get("value", 0.0)))
    draw.rectangle((bar_left, bar_top, bar_right, bar_top + 16), fill=GROOVE)
    draw.rectangle((bar_left, bar_top, bar_left + value * (bar_right - bar_left), bar_top + 16), fill=_visible(color))
    meter = max(0.0, min(1.0, knob.get("meter") or 0.0))
    draw.rectangle((bar_left, bar_top + 24, bar_right, bar_top + 32), fill=(25, 25, 25))
    if meter > 0:
        draw.rectangle((bar_left, bar_top + 24, bar_left + meter * (bar_right - bar_left), bar_top + 32),
                       fill=_meter_color(meter))


def render_screen(state, display):
    """Imagen PIL de una pantalla (0 = izquierda, 1 = derecha): grilla de session, mixer o dispositivo."""
    if screen_kind(state) == "session":
        return render_session(state, display)
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    view = state.get("view")
    track_color = _track_rgb(state.get("track_color"))

    if display == 0:
        if view == MIXER_VIEW:
            parameter = state.get("mixer_parameter")
            _header(draw, "MIXER", parameter)
        else:
            _header(draw, state.get("device") or "Sin dispositivo", "FX")
    else:
        _header(draw, state.get("track") or "", "LOCK" if state.get("locked") else None, color=track_color)

    knobs = state.get("knobs") or []
    touched = state.get("touched", -1)
    for column in range(COLUMNS):
        index = display * COLUMNS + column
        knob = knobs[index] if index < len(knobs) else None
        if not knob:
            continue
        if view == MIXER_VIEW:
            # Volumen = fader; paneo y envíos = knob
            if _is_volume(knob):
                _draw_fader(draw, column, knob, touched == index)
            else:
                _draw_knob(draw, column, knob, touched == index, _track_rgb(knob.get("color")),
                           knob.get("track") or knob.get("name"), knob.get("meter"))
        else:
            _draw_knob(draw, column, knob, touched == index, track_color, knob.get("name"))
        if column:
            x = column * COLUMN_WIDTH
            draw.line((x, HEADER_HEIGHT + 4, x, HEIGHT - 4), fill=(35, 35, 35))
    return image
