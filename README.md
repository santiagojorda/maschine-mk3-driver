# maschine-mk3-driver

Driver propio para la Maschine MK3, para dejar de depender del programa de
Native Instruments y usar las pantallas a gusto. Funciona con el mapeo de
[maschine-mk3-ableton-virtualdj](https://github.com/santiagojorda/maschine-mk3-ableton-virtualdj)
(Ableton Live + VirtualDJ).

- [PLAN.md](PLAN.md): el driver completo (Go, Windows primero, después Push 3 standalone).
- [PROTOTIPO-HOY.md](PROTOTIPO-HOY.md): el prototipo de pantallas de VirtualDJ.

## Ejecutable

`construir_exe.bat` arma `dist\MaschineMK3AsPush\MaschineMK3AsPush.exe` (una carpeta con el programa y todo lo que
necesita; no hace falta tener Python para usarlo, solo para armarlo).

| Comando | Qué hace |
|---|---|
| `MaschineMK3AsPush.exe` | Arranca las pantallas y el puerto de datos de VirtualDJ, sin ventana, y las reinicia si se caen o se cuelgan. Si ya está corriendo, avisa |
| `MaschineMK3AsPush.exe --salir` | Lo detiene todo |
| `MaschineMK3AsPush.exe --instalar-vdj` | Instala en VirtualDJ el dispositivo de datos (reiniciar VirtualDJ después) |

El registro (`pantallas.log`), la configuración (`config.json`) y el estado quedan en
`%LOCALAPPDATA%\MaschineMK3AsPush\`. Para que arranque con Windows, poner un acceso directo al .exe en
`shell:startup`.

## Estado

Prototipo en Python (`prototipo/`), **funcionando** (2026-10-07): en modo DJ
(SAMPLING), la pantalla izquierda de la Maschine muestra en vivo las ondas de
los dos decks de VirtualDJ a ~18 cuadros por segundo. MIXER / PLUGIN vuelven a
modo Ableton. El programa de NI sigue manejando pads, botones y LEDs.

Medido: la Maschine tarda ~50 ms en recibir una pantalla completa por USB
(~5 MB/s), así que entran ~20 pantallas completas por segundo en total.
Convertir la imagen tarda ~1 ms y no influye.

## Usar el prototipo

1. Instalar dependencias (Python 3.12):

   ```
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   ```

2. Con **Zadig** (Options → List All Devices), poner **WinUSB** solo en
   **"Maschine MK3 BD (Interface 5)"**. No tocar "Maschine MK3 (Interface 0)"
   (la usa el programa de NI), "Maschine MK3 HID (Interface 4)" ni
   "Maschine MK3 DFU (Interface 6)" (firmware). Después, desenchufar y volver
   a enchufar la Maschine: hasta entonces la interfaz no queda habilitada.
   Si Ableton o VirtualDJ estaban abiertos, reiniciarlos para que tomen los
   puertos MIDI de nuevo, y volver a poner la Maschine en modo MIDI.

3. Desde `prototipo/`, con el Python del venv:

   | Comando | Qué hace |
   |---|---|
   | `python screen_test.py` | Imagen de prueba en las dos pantallas y fps |
   | `python mode_watch.py --list` | Lista los puertos MIDI |
   | `python mode_watch.py` | Imprime DJ / ABLETON al apretar SAMPLING / MIXER / PLUGIN |
   | `python pick_region.py` | Elegir con el mouse las zonas de VirtualDJ |
   | `python dj_screens.py` | El prototipo completo (`--start dj` arranca en modo DJ; `--midi-log` muestra el MIDI que llega) |

4. Copiar `config.example.json` a `config.json`. Cada pantalla (`left`,
   `right`) tiene:
   - `regions`: zonas de la pantalla de la PC (las imprime `pick_region.py`),
     apiladas de arriba a abajo. Vacío = pantalla en negro.
   - `fit`: `contain` (entera, con bordes), `cover` (llena recortando) o
     `stretch` (llena deformando).
   - `fps`: cuadros por segundo. Entre las dos pantallas no pasar de ~20.

   El ejemplo está hecho para VirtualDJ a pantalla completa en 1920×1200 con
   el diseño PRO: las ondas de los dos decks, alrededor del punto de
   reproducción.

## Volver atrás (driver de NI en las pantallas)

Administrador de dispositivos → la interfaz 5 de la Maschine → Desinstalar
dispositivo (marcando borrar el driver) → desenchufar y volver a enchufar.

**Si por error Zadig le pone WinUSB a la interfaz 0** (pasa si se elige mal
en la lista; la Maschine deja de mandar MIDI y de prender luces): buscar el
paquete que creó Zadig con `pnputil /enum-drivers` (nombre original
`maschine_mk3_(interface_0).inf`) y, en una terminal de administrador:

```
pnputil /delete-driver oemNN.inf /uninstall /force
pnputil /scan-devices
```

Después, desenchufar y volver a enchufar. Windows vuelve a usar el driver de
NI (`nimc3usb.inf`).

## Limitación conocida

Mientras la interfaz 5 tiene WinUSB, el programa de NI no puede escribir en
las pantallas: en modo Ableton se ve un cartel "ABLETON" en lugar del texto del
script.

## Créditos

El protocolo de pantallas y la configuración de la MK3 vienen de
[ni-controllers-lib](https://github.com/asutherland/ni-controllers-lib) (ISC).
