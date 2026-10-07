"""Paso 6: el prototipo completo.

Modo DJ (SAMPLING): cada pantalla muestra en vivo las zonas de VirtualDJ de
config.json, apiladas de arriba a abajo y con su propia velocidad. Con
"capture_from": "window" (por defecto) se captura la ventana de VirtualDJ en
sí, aunque esté tapada (no minimizada), y las zonas van en coordenadas de la
ventana; con "screen", lo que se ve en el monitor. Modo Ableton
(MIXER / PLUGIN): el texto que manda el script de Ableton por UDP
(ableton_text.py); hasta que llega, un cartel "ABLETON".

La Maschine acepta ~20 pantallas completas por segundo en total (~50 ms cada
una), así que conviene repartir: ondas rápido, info de los decks lento. Una
pantalla que no cambió no se reenvía.

Uso: python dj_screens.py [--config config.json] [--start dj]
"""

import argparse
import json
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ableton_text import DEFAULT_PORT as ABLETON_TEXT_PORT
from ableton_text import AbletonText, render_screen
from maschine_display import HEIGHT, WIDTH, MaschineDisplays
from mode import ABLETON, DJ, ModeWatcher
from screen_capture import RegionCapture, set_dpi_aware
from window_capture import BackgroundWindowCapture

STATS_EVERY_S = 5.0
SCREEN_NAMES = ("left", "right")


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
    return config


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
    displays = MaschineDisplays()
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
    print(f"Escuchando '{watcher.port_name}' y el texto de Ableton en UDP {config['ableton_text_port']}. "
          f"Modo inicial: {args.start.upper()}. Ctrl+C para salir.")

    ableton_banner = banner("ABLETON")
    mode = None
    next_due = [0.0, 0.0]
    last_sent = [None, None]
    sent = [0, 0]
    stats_start = time.perf_counter()

    try:
        while True:
            new_mode = watcher.mode
            if new_mode != mode:
                mode = new_mode
                print(f"--> modo {mode.upper()}")
                last_sent = [None, None]
                next_due = [0.0, 0.0]
                if hasattr(capture, "set_active"):
                    capture.set_active(mode == DJ)

            if mode != DJ:
                for display in range(2):
                    content = ableton_text.screen_lines(display) if ableton_text.received else "banner"
                    if content == last_sent[display]:
                        continue
                    image = ableton_banner if content == "banner" else render_screen(*content)
                    displays.send_image(display, image)
                    last_sent[display] = content
                time.sleep(0.03)
                continue

            now = time.perf_counter()
            for display, screen in enumerate(screens):
                if now < next_due[display]:
                    continue
                next_due[display] = now + 1.0 / screen["fps"]
                try:
                    rgb = capture.grab_stack(screen["regions"], screen["fit"])
                    frame = rgb.tobytes()
                    if frame != last_sent[display]:
                        displays.send_rgb(display, rgb)
                        last_sent[display] = frame
                        sent[display] += 1
                except Exception as error:  # un cuadro perdido no corta el prototipo
                    print(f"Error en la pantalla {display}: {error}")

            elapsed = time.perf_counter() - stats_start
            if elapsed >= STATS_EVERY_S:
                print(f"fps enviados: izquierda {sent[0] / elapsed:.1f}, derecha {sent[1] / elapsed:.1f}")
                sent = [0, 0]
                stats_start = time.perf_counter()

            wait = min(next_due) - time.perf_counter()
            if wait > 0:
                time.sleep(wait)
    except KeyboardInterrupt:
        pass
    finally:
        watcher.close()
        ableton_text.close()
        capture.close()
        try:
            displays.clear()
        finally:
            displays.close()


if __name__ == "__main__":
    main()
