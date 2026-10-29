# 🖥️ Maschine MK3 Driver

Librería de Python para dibujar en las **dos pantallas a color (480 × 272) de la Native Instruments Maschine MK3** por USB, sin el software de Native Instruments.

No depende de Ableton ni de VirtualDJ: es la base para cualquier proyecto que quiera usar las pantallas de la Maschine. Hoy la usa **[maschine-mk3-as-ableton-push](https://github.com/santiagojorda/maschine-mk3-as-ableton-push)** (sus pantallas viven en `Pantallas/` de ese repo).

![Maschine MK3](docs/images/maschine-mk3-as-push-hero.jpg)

---

## Uso

```python
from PIL import Image
from maschine_mk3_driver import MaschineDisplays, WIDTH, HEIGHT

pantallas = MaschineDisplays.wait_for_device()
pantallas.send_image(0, Image.new("RGB", (WIDTH, HEIGHT), "orange"))  # pantalla izquierda
pantallas.close()
```

| Módulo | Qué hace |
|---|---|
| `display` | El protocolo USB (interfaz 5, endpoint bulk `0x04`, RGB565 big endian) y `MaschineDisplays`: `send_image`, `send_rgb`, `send_changes` (solo las franjas que cambiaron), `clear` |
| `screen_capture` | Captura una zona de la pantalla de la PC y la adapta a 480 × 272 |
| `window_capture` | Captura una ventana de Windows aunque esté tapada por otras |
| `screen_test` | Prueba de hardware: barras de colores y fps — `python -m maschine_mk3_driver.screen_test` |

## Instalación

```bash
pip install -e .                 # desde este repo, para desarrollar
```

Antes, la interfaz 5 de la Maschine tiene que tener el driver **WinUSB** (Zadig): ver **[docs/GUIA-INSTALACION.md](docs/GUIA-INSTALACION.md)**, que también explica cómo volver al driver original de Native Instruments.

El driver solo toma la interfaz 5 y no llama a `set_configuration`, así que el programa de Native Instruments puede seguir manejando pads, botones y luces al mismo tiempo.

## Documentación

- 📖 **[Guía de instalación y restauración](docs/GUIA-INSTALACION.md):** Zadig paso a paso y cómo volver al driver de fábrica.
- 🔬 **[Protocolo de pantallas](docs/PROTOTIPO-PANTALLAS.md):** estructura del paquete USB, RGB565 y tasa de refresco (20-30 fps reenviando solo lo que cambia).
- 📋 **[Plan](docs/PLAN.md):** el driver completo (pads, botones y luces por HID, sin el software de NI) y Push 3 standalone.

## Créditos

- **Desarrollo:** Santiago Jorda (Maicol)
- **Protocolo de pantallas y USB:** basado en [ni-controllers-lib](https://github.com/asutherland/ni-controllers-lib) de Andrew Sutherland (licencia ISC).
