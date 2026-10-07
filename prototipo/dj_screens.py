"""Paso 6: el prototipo completo.

Modo DJ (SAMPLING): las pantallas muestran en vivo las dos zonas de VirtualDJ
de config.json. Modo Ableton (MIXER / PLUGIN): un cartel fijo, porque mientras
la interfaz 5 tiene WinUSB el programa de NI no puede escribir su texto.

Uso: python dj_screens.py [--config config.json] [--start dj]
"""

import argparse
import json
import queue
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from maschine_display import HEIGHT, WIDTH, MaschineDisplays
from mode import ABLETON, DJ, ModeWatcher
from screen_capture import RegionCapture, set_dpi_aware

STATS_EVERY_S = 5.0


def load_config(path):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    config.setdefault("fps", 25)
    config.setdefault("fit", "contain")
    config.setdefault("midi_port", "Maschine MK3 Ctrl MIDI")
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
    args = parser.parse_args()

    config = load_config(args.config)
    regions = [config["regions"]["left"], config["regions"]["right"]]
    frame_time = 1.0 / config["fps"]

    set_dpi_aware()
    displays = MaschineDisplays()
    capture = RegionCapture()
    changes = queue.Queue()
    watcher = ModeWatcher(port_hint=config["midi_port"], start_mode=args.start, on_change=changes.put)
    print(f"Escuchando '{watcher.port_name}'. Modo inicial: {args.start.upper()}. Ctrl+C para salir.")

    ableton_banner = banner("ABLETON")
    mode = None
    frames, busy, stats_start = 0, 0.0, time.perf_counter()

    try:
        while True:
            new_mode = watcher.mode
            if new_mode != mode:
                mode = new_mode
                print(f"--> modo {mode.upper()}")
                if mode == ABLETON:
                    for display in range(2):
                        displays.send_image(display, ableton_banner)
                frames, busy, stats_start = 0, 0.0, time.perf_counter()

            if mode != DJ:
                try:
                    changes.get(timeout=0.2)
                except queue.Empty:
                    pass
                continue

            start = time.perf_counter()
            try:
                for display, region in enumerate(regions):
                    displays.send_rgb(display, capture.grab(region, config["fit"]))
            except Exception as error:  # un cuadro perdido no corta el prototipo
                print(f"Error en un cuadro: {error}")
            work = time.perf_counter() - start
            frames += 1
            busy += work

            elapsed = time.perf_counter() - stats_start
            if elapsed >= STATS_EVERY_S:
                print(f"{frames / elapsed:.1f} fps, {1000 * busy / frames:.1f} ms por cuadro")
                frames, busy, stats_start = 0, 0.0, time.perf_counter()

            time.sleep(max(0.0, frame_time - work))
    except KeyboardInterrupt:
        pass
    finally:
        watcher.close()
        capture.close()
        try:
            displays.clear()
        finally:
            displays.close()


if __name__ == "__main__":
    main()
