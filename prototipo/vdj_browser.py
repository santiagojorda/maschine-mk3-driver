"""Vista browser del modo DJ: carpetas en la pantalla izquierda y temas en la derecha.

Recorta las listas de la captura de la ventana de VirtualDJ (zonas en config.json,
"browser") y muestra solo las filas alrededor de la seleccionada, a un tamaño que se
lee. La fila seleccionada se reconoce por su fondo más claro: VirtualDJ pinta las filas
alternando dos grises oscuros y la seleccionada, bastante más clara.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from maschine_display import HEIGHT, WIDTH

HEADER_HEIGHT = 24
SELECTED_MIN_BRIGHTNESS = 48  # mediana del gris de una línea de la fila seleccionada (las otras: 19 y 34)
SELECTED_MIN_LINES = 12  # alto mínimo para que no cuente una línea suelta
MAX_SCALE = 1.0  # no agranda: se vería borroso

DEFAULT_LAYOUT = {
    # Coordenadas de la ventana de VirtualDJ (pantalla completa 1920 x 1200, skin PRO)
    "folders": {"title": "CARPETAS", "top": 596, "height": 592, "columns": [[50, 430]]},
    # Título + artista y BPM
    "songs": {"title": "TEMAS", "top": 618, "height": 540, "columns": [[610, 1030], [1105, 1195]]},
}

_font_cache = {}


def _font(size):
    if size not in _font_cache:
        try:
            _font_cache[size] = ImageFont.truetype("arialbd.ttf", size)
        except OSError:
            _font_cache[size] = ImageFont.load_default()
    return _font_cache[size]


def _selected_row(lines):
    """(arriba, abajo) de la fila seleccionada, en líneas de la lista, o None si no se ve."""
    gray = lines.mean(axis=2)
    bright = np.median(gray, axis=1) >= SELECTED_MIN_BRIGHTNESS
    best, start = None, None
    for y, on in enumerate(np.append(bright, False)):
        if on and start is None:
            start = y
        elif not on and start is not None:
            if y - start >= SELECTED_MIN_LINES and (best is None or y - start > best[1] - best[0]):
                best = (start, y)
            start = None
    return best


class BrowserView:
    def __init__(self, layout=None):
        self.layout = layout or DEFAULT_LAYOUT
        self._last_center = {}  # si no se ve la selección (por ejemplo, al scrollear) se queda donde estaba

    def render(self, window, name):
        """Imagen RGB (numpy) de 480 x 272 con la lista name ("folders" o "songs")."""
        zone = self.layout[name]
        image = Image.new("RGB", (WIDTH, HEIGHT))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, WIDTH, HEADER_HEIGHT - 1), fill=(28, 28, 28))
        draw.text((8, 3), zone["title"], font=_font(16), fill=(235, 235, 235))
        if window is None:
            draw.text((8, HEADER_HEIGHT + 10), "VirtualDJ no está a la vista", font=_font(16), fill=(140, 140, 140))
            return np.asarray(image)

        top, height = zone["top"], zone["height"]
        lines = np.concatenate([window[top:top + height, left:right] for left, right in zone["columns"]], axis=1)
        if not lines.size:
            return np.asarray(image)
        row = _selected_row(lines)
        center = self._last_center.get(name, 0) if row is None else (row[0] + row[1]) // 2
        self._last_center[name] = center

        # Ancho de la pantalla, sin agrandar; se ven las filas de alrededor de la seleccionada
        area = HEIGHT - HEADER_HEIGHT
        scale = min(MAX_SCALE, WIDTH / lines.shape[1])
        source_height = min(lines.shape[0], int(area / scale))
        first = min(max(center - source_height // 2, 0), lines.shape[0] - source_height)
        crop = Image.fromarray(np.ascontiguousarray(lines[first:first + source_height]))
        size = (round(crop.width * scale), round(crop.height * scale))
        image.paste(crop.resize(size, Image.BILINEAR), (0, HEADER_HEIGHT))
        if row is not None:
            # Borde blanco en la fila seleccionada: el gris de VirtualDJ se nota poco en la Maschine
            y0 = HEADER_HEIGHT + (row[0] - first) * scale
            y1 = HEADER_HEIGHT + (row[1] - first) * scale - 1
            draw.rectangle((0, max(y0, HEADER_HEIGHT), size[0] - 1, min(y1, HEIGHT - 1)), outline=(255, 255, 255), width=2)
        return np.asarray(image)
