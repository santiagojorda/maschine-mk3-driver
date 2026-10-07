# Prototipo de hoy: pantallas de VirtualDJ en la Maschine MK3

Fecha: 2026-10-07

## Objetivo

Al apretar **SAMPLING** (modo DJ), las pantallas de la Maschine muestran
VirtualDJ en vivo: una zona de la ventana capturada y escalada a cada
pantalla. Al apretar **MIXER** o **PLUGIN**, vuelve a modo Ableton.

## El atajo que lo hace posible en un día

**El programa de NI sigue manejando todo lo demás.** Pads, botones, LEDs,
Ableton y VirtualDJ funcionan como hoy. El prototipo solo toma las pantallas:

- Con Zadig se le pone WinUSB **solo a la interfaz 5** (pantallas). El resto
  de la Maschine sigue con los drivers de NI.
- El prototipo abre el puerto MIDI de la Maschine (`Maschine MK3 Ctrl MIDI`)
  como un cliente más (Windows MIDI Services ya permite varios) y escucha
  SAMPLING / MIXER / PLUGIN para saber el modo.
- Captura la zona de VirtualDJ y la manda a las pantallas por USB.

No hace falta descifrar pads, velocity ni LEDs. Eso es el driver completo
([PLAN.md](PLAN.md)).

## Lenguaje: Python (solo para el prototipo)

En esta PC hay Python 3.12 y no hay Go ni gcc. Python con estas librerías
corre sin compilar nada:

| Para qué | Librería |
|---|---|
| USB (pantallas) | `pyusb` + `libusb-package` (trae la DLL de libusb) |
| Leer el puerto MIDI | `mido` + `python-rtmidi` |
| Captura de pantalla | `mss` (alternativa: `dxcam`, que usa Desktop Duplication) |
| Escalar y convertir a RGB565 | `pillow` + `numpy` |

El driver definitivo sigue siendo en Go; esto es para aprender y validar.

## Datos que usa

- USB: vendor `0x17CC`, producto `0x1600`. Pantallas: interfaz 5, endpoint
  bulk `0x04`, 2 × 480×272.
- Cuadro: cabecera de 16 bytes:
  - Byte 0 = `0x84`, byte 2 = pantalla (0/1), byte 3 = `0x60`.
  - Bytes 8–15 = x, y, ancho, alto (16 bits, big endian).
  - Después, el comando de 4 bytes `00` + (píxeles / 2) en 24 bits big endian.
  - Después, los píxeles RGB565 big endian.
  - Al final, `03 00 00 00` (dibujar) y `40 00 00 00` (fin).
  (Fuente: `ni_lcd_displays.ts` de ni-controllers-lib.)
- Modo (de `MaschineMK3-VDJ.xml` y `CONTEXTO-TECNICO.md`): Control Change en
  canal MIDI 2 (status `0xB1`), valor 127 al apretar:
  - SAMPLING = CC 39 (`0x27`) → modo DJ.
  - MIXER = CC 37 (`0x25`) y PLUGIN = CC 35 (`0x23`) → modo Ableton.

## Pasos

### 1. Preparación (~30 min)

- `pip install pyusb libusb-package mido python-rtmidi mss pillow numpy`
- Bajar Zadig (zadig.akeo.ie).
- **Cómo volver atrás** (anotarlo antes de tocar nada): Administrador de
  dispositivos → la interfaz 5 de la Maschine → Desinstalar dispositivo
  (marcando borrar el driver) → desenchufar y volver a enchufar. Windows
  vuelve a poner el driver de NI.

### 2. Zadig en la interfaz 5 (~30 min) — punto de decisión

- Zadig → Options → List All Devices → elegir **"Maschine MK3 (Interface
  5)"** → WinUSB → Replace Driver.
- Verificar que **pads, botones y LEDs siguen andando** en Ableton y
  VirtualDJ.

**Si el programa de NI deja de funcionar del todo:** volver atrás y pasar al
plan B (abajo).

### 3. Prueba de pantallas (~1 h)

- `screen_test.py`: pinta barras de colores en la pantalla 0 y un degradé en
  la 1.
- Medir cuántos cuadros por segundo salen con la pantalla completa.

**Listo cuando:** las dos pantallas muestran la imagen.

### 4. Detectar el modo (~45 min)

- `mode_watch.py`: abre `Maschine MK3 Ctrl MIDI` con mido e imprime "DJ" o
  "ABLETON" al apretar SAMPLING / MIXER / PLUGIN.
- Si el puerto no se puede abrir (ocupado): plan B del modo (abajo).

**Listo cuando:** el cambio de modo se imprime al apretar los botones.

### 5. Captura de VirtualDJ (~1,5 h)

- `config.json` con dos rectángulos de la pantalla de la PC: uno para cada
  pantalla de la Maschine. Por ejemplo, izquierda = zona de ondas, derecha =
  zona de info de los decks. `pick_region.py` ayuda a anotar las coordenadas
  (imprime la posición del mouse).
- Cada cuadro: capturar el rectángulo, escalarlo a 480×272 (manteniendo la
  proporción, con bordes negros), convertir a RGB565 y mandarlo.
- Objetivo: 20–30 fps.

**Listo cuando:** las ondas de VirtualDJ se mueven en la Maschine.

### 6. Juntar todo (~1 h)

- `dj_screens.py`:
  - Un hilo escucha el MIDI y cambia el modo.
  - Otro hilo dibuja:
    - **Modo DJ:** captura a 20–30 fps.
    - **Modo Ableton:** una pantalla fija con el texto "ABLETON" (ver
      limitaciones).
  - Al cerrar (Ctrl+C), deja las pantallas en negro.
- Probar con tu set real: cambiar de modo varias veces, pasar dos temas y
  sincronizar mirando la Maschine.
- Mirar en el Administrador de tareas el CPU de `python` y notar si los pads
  se sienten igual.

**Listo cuando:** entrar y salir del modo DJ cambia las pantallas sin
cortes, y los pads se sienten como siempre.

### 7. Cierre (~15 min)

- Anotar fps, CPU y problemas.
- Decidir si dejar WinUSB en la interfaz 5 o volver atrás.

Total: ~5–6 horas.

## Limitaciones del prototipo (conocidas)

- **Mientras la interfaz 5 tiene WinUSB, el programa de NI no puede dibujar
  en las pantallas.** En modo Ableton se ve "ABLETON" en lugar del texto del
  script, y en modo DJ no se ven los textos que manda VirtualDJ (solo la
  captura). Se recupera volviendo atrás con el paso 1.
- Si movés o cambiás el tamaño de la ventana de VirtualDJ, hay que ajustar
  los rectángulos.
- Python y captura con `mss`: suficiente para probar; el driver definitivo
  usa Go y Desktop Duplication.

## Plan B

- **Si Zadig rompe el programa de NI:** el prototipo lee el HID de la
  Maschine directamente para detectar SAMPLING/MIXER/PLUGIN (Windows deja
  leer un HID desde varios programas). Los pads no andarían mientras dure la
  prueba, pero se validan las pantallas, que es lo importante.
- **Si no se puede abrir el puerto MIDI:** mismo camino, leer el HID.
- **Si `mss` captura en negro** (VirtualDJ en pantalla completa
  acelerada): usar `dxcam`, o poner VirtualDJ en modo ventana.

## Extras si sobra tiempo

- **Texto de Ableton en las pantallas:** un parche chico en el script que,
  además de mandar el texto MCU a la Maschine, lo mande por UDP a
  `127.0.0.1`. El prototipo lo dibuja en modo Ableton.
- **Franja de info en modo DJ:** BPM y SYNC dibujados encima de la captura.
