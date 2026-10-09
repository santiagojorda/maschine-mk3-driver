# 🖥️ Maschine MK3 Screen Driver

[![Ableton Live 12](https://img.shields.io/badge/Ableton%20Live-12%20Suite-00D2B4.svg)](https://www.ableton.com)
[![Native Instruments](https://img.shields.io/badge/Hardware-Maschine%20MK3-black.svg)](https://www.native-instruments.com)
[![Windows 11](https://img.shields.io/badge/OS-Windows%2011%20MIDI%20Services-0078D4.svg)](https://microsoft.com)
[![Repo Principal](https://img.shields.io/badge/Repo-maschine--mk3--as--ableton--push-orange.svg)](https://github.com/santiagojorda/maschine-mk3-as-ableton-push)
[![Manual Web](https://img.shields.io/badge/Manual-All%20Operations%20(Web)-brightgreen.svg)](https://santiagojorda.github.io/maschine-mk3-as-ableton-push/)

Servidor y driver de pantallas USB para **Native Instruments Maschine MK3**, diseñado para renderizar la interfaz gráfica de **Ableton Live 12** en las dos pantallas LCD a color (480 × 272 c/u). 

Forma parte del proyecto **[maschine-mk3-as-ableton-push](https://github.com/santiagojorda/maschine-mk3-as-ableton-push)**.

---

## ⚡ Cómo Funciona

1. **Comunicación con Ableton Live:**
   - El script MIDI de Ableton Live (`CustomMaschineMK3`) transmite su estado en tiempo real vía socket **UDP local (puerto 9017)**.
   - Envía nombres de pistas, colores, clips activos, faders, vúmetros dinámicos, parámetros de plugins, árbol del browser y modos de encoder.

2. **Renderizado en Pantallas:**
   - El servidor procesa la telemetría y dibuja las vistas completas a **~20 fps** en formato **RGB565**.
   - Envía los datos directamente por el endpoint USB Bulk (`0x04`) de la **interfaz 5** de la controladora (usando el driver WinUSB configurado en Zadig).
   - Para maximizar rendimiento y fluidez, calcula diferencias (dirty rects) y refresca la pantalla completa periódicamente.

3. **Modo Reposo inteligente (Standby):**
   - Al presionar <kbd>SHIFT</kbd> + <kbd>CHANNEL</kbd>, apaga botones y pads, y muestra un salvapantallas con el logotipo oficial para proteger las pantallas y evitar toques involuntarios.

---

## 🚀 Ejecutable (`MaschineMK3AsPush.exe`)

El script `construir_exe.bat` compila la aplicación autocontenida en `dist\MaschineMK3AsPush\MaschineMK3AsPush.exe` (no requiere tener Python instalado para usarla en vivo):

| Comando | Acción |
|---|---|
| `MaschineMK3AsPush.exe` | Inicia el servicio de pantallas en segundo plano con supervisor automático (se reconecta solo si la Maschine se apaga o desconecta). |
| `MaschineMK3AsPush.exe --salir` | Detiene y cierra todos los procesos del driver. |

- **Ruta de datos:** El registro (`pantallas.log`), la configuración (`config.json`) y el estado se almacenan en:  
  `%LOCALAPPDATA%\MaschineMK3AsPush\`
- **Inicio automático:** Para que arranque automáticamente al iniciar Windows, colocá un acceso directo a `MaschineMK3AsPush.exe` dentro de `shell:startup`.

---

## 🛠️ Desarrollo y Prototipo en Python

Para ejecutar o modificar el código fuente directamente con Python 3.12:

### 1. Entorno virtual y dependencias
```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### 2. Configuración del Driver USB (Zadig)
1. Abrí **[Zadig](https://zadig.akeo.ie/)** y marcá *Options → List All Devices*.
2. Seleccioná únicamente **`Maschine MK3 BD (Interface 5)`**.
3. Elegí **WinUSB** y hacé clic en **Install Driver**.
4. Desconectá y volvé a conectar el cable USB de la controladora.
   > ⚠️ **Importante:** No toques la interfaz 0 (MIDI nativo de NI) ni la interfaz 4 o 6.

### 3. Scripts disponibles en `prototipo/`
Desde la carpeta `prototipo/`:

| Script | Propósito |
|---|---|
| `python supervisor.py` | Supervisor principal que gestiona el ciclo de vida de las pantallas de Ableton. |
| `python screen_test.py` | Imagen de prueba en ambas pantallas y medición de FPS por USB. |
| `python mode_watch.py` | Monitor de eventos MIDI y cambios de modo de la Maschine. |
| `python encoder_view.py` | Vista gráfica de los modos de encoder (Volumen Master, Cue y Tempo). |

---

## 🔄 Volver al Driver de Fábrica de Native Instruments

Si querés restaurar el driver original oficial de NI para la pantalla:

1. Abrí el **Administrador de Dispositivos** (`devmgmt.msc`).
2. En *Dispositivos de bus serie universal* (o *Universal Serial Bus devices*), buscá **`Maschine MK3 BD (Interface 5)`**.
3. Clic derecho → **Desinstalar el dispositivo** (marcando la casilla de eliminar el controlador).
4. Desconectá y reconectá el cable USB: Windows reinstalará automáticamente el driver original oficial de Native Instruments (`nimc3usb.inf`).

> **Recuperación rápida por comando (si se asignó WinUSB a otra interfaz por error):**  
> Identificá el paquete con `pnputil /enum-drivers` y ejecutá como Administrador:  
> ```bash
> pnputil /delete-driver oemNN.inf /uninstall /force
> pnputil /scan-devices
> ```

---

## 👤 Creador y Créditos

- **Desarrollo y concepto:** Santiago Jorda (Maicol)  
  - 📺 [Maicol Session en YouTube](https://www.youtube.com/watch?v=ImqHw-zkiZQ&list=PLxk2dEOPjuEYO00P264yMStEUhukVkO1y)  
  - 📸 Instagram: [@santiagojorda](http://instagram.com/santiagojorda)
- **Protocolo de pantallas y comunicación USB:** Basado en especificaciones de [ni-controllers-lib](https://github.com/asutherland/ni-controllers-lib).
