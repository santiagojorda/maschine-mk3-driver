"""Paso 6: el prototipo completo.

Modo DJ (SAMPLING): cada pantalla muestra en vivo las zonas de VirtualDJ de
config.json, apiladas de arriba a abajo y con su propia velocidad. BROWSER prende
y apaga, en la pantalla derecha, la lista de carpetas o temas que tiene el foco (vdj_browser.py);
si no, la derecha muestra el estado de los decks con los datos de VirtualDJ (dj_info.py, vdj_data.py). Con
"capture_from": "window" (por defecto) se captura la ventana de VirtualDJ en
sí, aunque esté tapada (no minimizada), y las zonas van en coordenadas de la
ventana; con "screen", lo que se ve en el monitor. Modo Ableton
(MIXER / PLUGIN): en las vistas mixer y dispositivo, faders y knobs dibujados
con el estado que manda el script (ableton_ui.py); en las demás, el texto
(ableton_text.py); hasta que llega algo, un cartel "ABLETON".

La Maschine acepta ~20 pantallas completas por segundo en total (~50 ms cada
una), así que conviene repartir: ondas rápido, info de los decks lento. Una
pantalla que no cambió no se reenvía.

Uso: python dj_screens.py [--config config.json] [--start dj]
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ableton_text import DEFAULT_PORT as ABLETON_TEXT_PORT
from ableton_text import AbletonText, render_screen
from ableton_ui import render_screen as render_ui_screen
from ableton_ui import screen_kind, wants_graphics
from maschine_display import HEIGHT, WIDTH, MaschineDisplays
from mode import ABLETON, DJ, ModeWatcher
from screen_capture import RegionCapture, set_dpi_aware
from dj_info import render_decks
from vdj_browser import BrowserView
from vdj_data import VdjData
from window_capture import BackgroundWindowCapture

STATS_EVERY_S = 5.0
SCREEN_NAMES = ("left", "right")
ABLETON_FPS = 30
BROWSER_FPS = 12
BROWSER_DISPLAY = 1  # derecha: la izquierda sigue con las ondas
DECKS_DISPLAY = 1  # derecha, cuando no está el browser: estado de los decks
DECKS_FPS = 15
# Cada tanto se manda todo de nuevo, aunque no haya cambiado: si otro programa (el de NI al cambiar
# de modo, por ejemplo) dibujó en las pantallas, como solo se manda lo que cambia, quedaría pisado
FULL_REFRESH_SECONDS = 2.0


class MeterSmoother:
    """Medidores suaves: Ableton manda el estado 10 veces por segundo; entre dato y dato
    el medidor sube al instante y baja de a poco, así se ve fluido a 30 cuadros por segundo."""

    FALL_PER_SECOND = 1.5

    def __init__(self):
        self._levels = {}
        self._last = time.perf_counter()

    def apply(self, state):
        now = time.perf_counter()
        elapsed, self._last = now - self._last, now
        knobs = []
        for index, knob in enumerate(state.get("knobs") or []):
            if knob and "meter" in knob:
                level = max(knob["meter"], self._levels.get(index, 0.0) - self.FALL_PER_SECOND * elapsed)
                self._levels[index] = level
                knob = dict(knob, meter=level)
            knobs.append(knob)
        return dict(state, knobs=knobs)


def load_config(path):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    config.setdefault("midi_port", "Maschine MK3 Ctrl MIDI")
    config.setdefault("ableton_text_port", ABLETON_TEXT_PORT)
    config.setdefault("capture_from", "window")
    for name in SCREEN_NAMES:
        screen = config["screens"][name]
        screen.setdefault("fit", "contain")
        screen.setdefault("fps", 10)
        screen.setdefault("regions", [])
        # Alto de la zona que se manda, centrada (el resto queda en negro). La Maschine tarda ~0,18 ms
        # por fila: 272 filas = 49 ms (20 fps máx.), 216 filas = 39 ms (25 fps).
        screen["height"] = min(HEIGHT, screen.get("height", HEIGHT)) // 2 * 2
    return config


def start_vdj_port():
    """Lanza vdj_puerto.py aparte, para que sobreviva a los reinicios del prototipo (si ya corre, sale solo)."""
    log = Path(__file__).resolve().parent.parent / ".venv" / "vdj_puerto.log"
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    for extra in (0x01000000, 0):  # CREATE_BREAKAWAY_FROM_JOB, si el job lo permite
        try:
            with open(log, "a", encoding="utf-8") as output:
                subprocess.Popen([sys.executable, "-u", str(Path(__file__).with_name("vdj_puerto.py"))],
                                 cwd=str(Path(__file__).parent), stdout=output, stderr=output,
                                 stdin=subprocess.DEVNULL, creationflags=flags | extra, close_fds=True)
            return
        except OSError:
            continue


def banner(text):
    image = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arialbd.ttf", 56)
    except OSError:
        font = ImageFont.load_default()
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    position = ((WIDTH - (right - left)) // 2 - left, (HEIGHT - (bottom - top)) // 2 - top)
    draw.text(position, text, fill=(255, 255, 255), font=font)
    return image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.json")))
    parser.add_argument("--start", choices=[DJ, ABLETON], default=ABLETON, help="modo al arrancar")
    parser.add_argument("--midi-log", action="store_true", help="imprimir todos los mensajes MIDI que llegan")
    args = parser.parse_args()

    config = load_config(args.config)
    screens = [config["screens"][name] for name in SCREEN_NAMES]

    set_dpi_aware()
    displays = MaschineDisplays.wait_for_device()
    if config["capture_from"] == "window":
        capture = BackgroundWindowCapture(fps=max(screen["fps"] for screen in screens))
    else:
        capture = RegionCapture()
    watcher = ModeWatcher(
        port_hint=config["midi_port"],
        start_mode=args.start,
        on_message=(lambda message: print(f"MIDI {message}")) if args.midi_log else None,
    )
    ableton_text = AbletonText(config["ableton_text_port"])
    start_vdj_port()
    try:
        vdj_data = VdjData()
        print("Escuchando los datos de VirtualDJ (puerto 'MK3 Screens', vdj_puerto.py)")
    except Exception as error:
        vdj_data = None
        print(f"Sin datos de VirtualDJ: {error}")
    print(f"Escuchando '{watcher.port_name}' y el texto de Ableton en UDP {config['ableton_text_port']}. "
          f"Modo inicial: {args.start.upper()}. Ctrl+C para salir.")

    ableton_banner = banner("ABLETON")
    browser_view = BrowserView(config.get("browser"))
    mode = None
    showing_browser = False
    next_due = [0.0, 0.0]
    last_sent = [None, None]
    last_frame = [None, None]  # última imagen mandada en modo gráfico, para mandar solo lo que cambia
    meters = MeterSmoother()
    last_version = 0  # para contar cuántos estados de Ableton llegan entre estadísticas
    sent = [0, 0]
    stats_start = time.perf_counter()
    last_full_refresh = time.perf_counter()

    try:
        while True:
          try:
              if watcher.sync(ableton_text.reported_mode()):
                  print("(modo tomado del script de Ableton)")
              new_mode = watcher.mode
              if time.perf_counter() - last_full_refresh >= FULL_REFRESH_SECONDS:
                  last_full_refresh = time.perf_counter()
                  last_sent = [None, None]
                  last_frame = [None, None]
              if new_mode != mode:
                  mode = new_mode
                  print(f"--> modo {mode.upper()}")
                  last_sent = [None, None]
                  last_frame = [None, None]
                  next_due = [0.0, 0.0]
                  if hasattr(capture, "set_active"):
                      capture.set_active(mode == DJ)
                  if mode == DJ:
                      # Las bandas fuera de la zona de cada pantalla quedan en negro desde acá
                      displays.clear()

              browser = mode == DJ and watcher.browser
              if browser != showing_browser:
                  showing_browser = browser
                  print("--> browser" if browser else "--> ondas")
                  last_sent = [None, None]
                  last_frame = [None, None]
                  next_due = [0.0, 0.0]
                  if mode == DJ and not browser:
                      displays.clear()

              if mode != DJ:
                  frame_start = time.perf_counter()
                  state = ableton_text.state()
                  if wants_graphics(state):
                      # Session, mixer o dispositivo: solo se manda lo que cambió
                      try:
                          smoothed = meters.apply(state)
                          for display in range(2):
                              rgb = np.asarray(render_ui_screen(smoothed, display))
                              if displays.send_changes(display, rgb, last_frame[display]):
                                  sent[display] += 1
                              last_frame[display] = rgb
                      except Exception as error:  # un cuadro perdido no frena la pantalla
                          print(f"Error dibujando Ableton: {error!r}")
                          last_frame = [None, None]
                      last_sent = [None, None]
                  else:
                      last_frame = [None, None]
                      for display in range(2):
                          content = ableton_text.screen_lines(display) if ableton_text.received else "banner"
                          if content == last_sent[display]:
                              continue
                          displays.send_image(display, ableton_banner if content == "banner" else render_screen(*content))
                          last_sent[display] = content
                  elapsed = time.perf_counter() - stats_start
                  if elapsed >= STATS_EVERY_S:
                      if state is None:
                          print("Ableton: sin estado JSON (¿script recargado?); se muestra el texto")
                      else:
                          print(f"Ableton: dibuja {screen_kind(state) or 'texto'}, vista {state.get('view')}, "
                                f"session {state.get('session_view')}, encoder {state.get('encoder_mode')}, "
                                f"estados {ableton_text.state_version - last_version} en {elapsed:.0f} s, "
                                f"cuadros {sent[0] / elapsed:.1f} / {sent[1] / elapsed:.1f} por segundo")
                          Path(__file__).resolve().parent.parent.joinpath(".venv", "last_state.json").write_text(
                              json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8")
                      last_version = ableton_text.state_version
                      sent = [0, 0]
                      stats_start = time.perf_counter()
                  time.sleep(max(0.0, 1.0 / ABLETON_FPS - (time.perf_counter() - frame_start)))
                  continue

              now = time.perf_counter()
              for display, screen in enumerate(screens):
                  if now < next_due[display]:
                      continue
                  if browser and display == BROWSER_DISPLAY:
                      next_due[display] = now + 1.0 / BROWSER_FPS
                      try:
                          window = capture.latest() if hasattr(capture, "latest") else None
                          focus = browser_view.focus
                          rgb = browser_view.render_focused(window)
                          if browser_view.focus != focus:
                              print(f"--> browser: {browser_view.focus}")
                          if displays.send_changes(display, rgb, last_frame[display]):
                              sent[display] += 1
                          last_frame[display] = rgb
                      except Exception as error:
                          print(f"Error en el browser: {error!r}")
                          last_frame[display] = None
                      continue
                  if display == DECKS_DISPLAY:
                      next_due[display] = now + 1.0 / DECKS_FPS
                      try:
                          rgb = np.asarray(render_decks(vdj_data))
                          if displays.send_changes(display, rgb, last_frame[display]):
                              sent[display] += 1
                          last_frame[display] = rgb
                      except Exception as error:
                          print(f"Error en los decks: {error!r}")
                          last_frame[display] = None
                      continue
                  next_due[display] = now + 1.0 / screen["fps"]
                  try:
                      rgb = capture.grab_stack(screen["regions"], screen["fit"], screen["height"])
                      frame = rgb.tobytes()
                      if frame != last_sent[display]:
                          displays.send_rgb(display, rgb, 0, (HEIGHT - screen["height"]) // 2)
                          last_sent[display] = frame
                          sent[display] += 1
                  except Exception as error:  # un cuadro perdido no corta el prototipo
                      print(f"Error en la pantalla {display}: {error}")

              elapsed = time.perf_counter() - stats_start
              if elapsed >= STATS_EVERY_S:
                  print(f"fps enviados: izquierda {sent[0] / elapsed:.1f}, derecha {sent[1] / elapsed:.1f}; "
                        f"datos de VirtualDJ: {vdj_data.messages if vdj_data else 'sin puerto'}")
                  sent = [0, 0]
                  stats_start = time.perf_counter()

              wait = min(next_due) - time.perf_counter()
              if wait > 0:
                  time.sleep(wait)
          except Exception as error:
              # Nada corta el prototipo: un error (por ejemplo, USB) se anota y se reintenta
              print(f"Error en el ciclo: {error!r}; sigo en medio segundo")
              last_sent = [None, None]
              last_frame = [None, None]
              time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        watcher.close()
        ableton_text.close()
        if vdj_data is not None:
            vdj_data.close()
        capture.close()
        try:
            displays.clear()
        except Exception:
            pass
        finally:
            displays.close()


if __name__ == "__main__":
    main()
