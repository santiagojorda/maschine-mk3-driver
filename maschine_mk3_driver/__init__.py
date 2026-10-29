"""Driver de las pantallas de la Maschine MK3: manda imágenes a sus dos pantallas por USB.

No depende de Ableton ni de VirtualDJ: cualquier programa que quiera dibujar en la Maschine lo puede usar.

    from maschine_mk3_driver import MaschineDisplays, WIDTH, HEIGHT
    pantallas = MaschineDisplays.wait_for_device()
    pantallas.send_image(0, imagen)   # imagen de Pillow de WIDTH x HEIGHT; send_rgb para un array de numpy

Módulos:
  display         el protocolo USB (interfaz 5, endpoint 0x04, RGB565) y MaschineDisplays
  screen_capture  captura una zona de la pantalla de la PC y la adapta a 480 x 272
  window_capture  captura una ventana aunque esté tapada (Windows)
  screen_test     prueba: barras de colores y fps (python -m maschine_mk3_driver.screen_test)
"""

from .display import HEIGHT, NUM_DISPLAYS, WIDTH, MaschineDisplays

__all__ = ["HEIGHT", "NUM_DISPLAYS", "WIDTH", "MaschineDisplays"]
