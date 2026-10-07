# maschine-mk3-driver

Driver propio para la Maschine MK3, para dejar de depender del programa de
Native Instruments y usar las pantallas a gusto. Funciona con el mapeo de
[maschine-mk3-ableton-virtualdj](https://github.com/santiagojorda/maschine-mk3-ableton-virtualdj)
(Ableton Live + VirtualDJ).

- [PLAN.md](PLAN.md): el driver completo (Go, Windows primero, después Push 3 standalone).
- [PROTOTIPO-HOY.md](PROTOTIPO-HOY.md): el prototipo de pantallas de VirtualDJ.

## Estado

Prototipo en Python (`prototipo/`): en modo DJ (SAMPLING), las pantallas de
la Maschine muestran dos zonas de la ventana de VirtualDJ. El programa de NI
sigue manejando pads, botones y LEDs.

## Usar el prototipo

1. Instalar dependencias (Python 3.12):

   ```
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   ```

2. Con **Zadig** (Options → List All Devices), poner **WinUSB** solo en
   **"Maschine MK3 (Interface 5)"**. Verificar que pads, botones y LEDs siguen
   andando en Ableton y VirtualDJ.

3. Desde `prototipo/`, con el Python del venv:

   | Comando | Qué hace |
   |---|---|
   | `python screen_test.py` | Imagen de prueba en las dos pantallas y fps |
   | `python mode_watch.py --list` | Lista los puertos MIDI |
   | `python mode_watch.py` | Imprime DJ / ABLETON al apretar SAMPLING / MIXER / PLUGIN |
   | `python pick_region.py` | Elegir con el mouse las zonas de VirtualDJ |
   | `python dj_screens.py` | El prototipo completo |

4. Copiar `config.example.json` a `config.json` y pegar las zonas que
   imprime `pick_region.py`. `fit` puede ser `contain` (entera, con bordes),
   `cover` (llena recortando) o `stretch` (llena deformando).

## Volver atrás (driver de NI en las pantallas)

Administrador de dispositivos → la interfaz 5 de la Maschine → Desinstalar
dispositivo (marcando borrar el driver) → desenchufar y volver a enchufar.

## Limitación conocida

Mientras la interfaz 5 tiene WinUSB, el programa de NI no puede escribir en
las pantallas: en modo Ableton se ve un cartel "ABLETON" en lugar del texto del
script.

## Créditos

El protocolo de pantallas y la configuración de la MK3 vienen de
[ni-controllers-lib](https://github.com/asutherland/ni-controllers-lib) (ISC).
