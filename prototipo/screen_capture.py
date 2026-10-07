"""Captura una zona de la pantalla de la PC y la adapta a 480x272."""

import ctypes

import mss
import numpy as np
from PIL import Image

from maschine_display import HEIGHT, WIDTH


def set_dpi_aware():
    """Hace que las coordenadas sean píxeles reales aunque Windows tenga escala (125 %, 150 %...)."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        ctypes.windll.user32.SetProcessDPIAware()


def fit_image(image, fit):
    """Adapta una imagen PIL a 480x272.

    contain = entra entera con bordes negros; cover = llena la pantalla recortando;
    stretch = llena la pantalla deformando.
    """
    if fit == "stretch":
        return image.resize((WIDTH, HEIGHT), Image.BILINEAR)

    scale_w = WIDTH / image.width
    scale_h = HEIGHT / image.height
    scale = max(scale_w, scale_h) if fit == "cover" else min(scale_w, scale_h)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    resized = image.resize(size, Image.BILINEAR)

    canvas = Image.new("RGB", (WIDTH, HEIGHT))
    canvas.paste(resized, ((WIDTH - size[0]) // 2, (HEIGHT - size[1]) // 2))
    return canvas


class RegionCapture:
    """Usar desde un solo hilo: mss en Windows no se puede compartir entre hilos."""

    def __init__(self):
        self._sct = mss.mss()

    def grab(self, region, fit):
        shot = self._sct.grab(region)
        bgra = np.frombuffer(shot.bgra, dtype=np.uint8).reshape(shot.height, shot.width, 4)
        image = Image.fromarray(bgra[..., 2::-1])  # BGRA -> RGB
        return np.asarray(fit_image(image, fit))

    def close(self):
        self._sct.close()
