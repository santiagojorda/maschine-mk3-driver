"""Recibe de VirtualDJ el estado de cada deck por un puerto MIDI virtual.

El prototipo crea el puerto "MK3 Screens" con teVirtualMIDI (viene con
loopMIDI). VirtualDJ lo ve como un controlador más (vdj/generar.py) y le
manda textos por sysex: F0 7D <campo> <texto> F7, con campo = deck * 16 + código
(ver FIELDS en vdj/generar.py). VirtualDJ manda cada texto cuando cambia.

El puerto se abre sin que el driver arme los mensajes: el título en UTF-8 trae
bytes de 8 bits que cortarían un sysex, así que se juntan acá de F0 a F7.
"""

import ctypes
import ctypes.wintypes as W
import threading
import time
import unicodedata

PORT_NAME = "MK3 Screens"
SYSEX_ID = 0x7D  # "uso no comercial / experimental"

FIELDS = {
    1: "title", 2: "artist", 3: "bpm", 4: "bpm_original", 5: "playing", 6: "volume", 7: "filter",
    8: "sync", 9: "keylock", 10: "loop", 11: "loop_length", 12: "title_utf8", 13: "artist_utf8", 14: "loaded",
}
THOUSANDTHS = ("bpm", "bpm_original", "volume", "filter", "loop_length")
FLAGS = ("playing", "keylock", "loop", "loaded")

_MIDI_DATA_CALLBACK = ctypes.WINFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(ctypes.c_ubyte), W.DWORD, ctypes.c_void_p)


def _ascii_skeleton(text):
    return "".join(char if ord(char) < 127 else "?" for char in unicodedata.normalize("NFC", text))


class DeckState:
    def __init__(self):
        self.values = {}
        self.changed_at = {}  # campo -> perf_counter del último cambio (para los pop-ups)

    def get(self, name, default=None):
        return self.values.get(name, default)

    def _best_text(self, name):
        # El UTF-8 vale si llegó entero: en ASCII tiene que dar lo mismo que el campo ASCII
        ascii_text, utf8_text = self.values.get(name), self.values.get(name + "_utf8")
        if utf8_text and (ascii_text is None or _ascii_skeleton(utf8_text) == ascii_text):
            return utf8_text
        return ascii_text

    @property
    def title(self):
        return self._best_text("title")

    @property
    def artist(self):
        return self._best_text("artist")


class VdjData:
    def __init__(self):
        self.decks = [DeckState(), DeckState()]
        self.lock = threading.Lock()
        self.messages = 0
        self._buffer = None  # bytes del sysex en curso
        dll = ctypes.WinDLL("teVirtualMIDI64.dll")
        dll.virtualMIDICreatePortEx2.restype = ctypes.c_void_p
        dll.virtualMIDICreatePortEx2.argtypes = [W.LPCWSTR, _MIDI_DATA_CALLBACK, ctypes.c_void_p, W.DWORD, W.DWORD]
        dll.virtualMIDIClosePort.argtypes = [ctypes.c_void_p]
        self._dll = dll
        self._callback = _MIDI_DATA_CALLBACK(self._on_data)  # hay que guardar la referencia
        self._port = dll.virtualMIDICreatePortEx2(PORT_NAME, self._callback, None, 0x1FFFE, 0)
        if not self._port:
            raise RuntimeError(f"No se pudo crear el puerto virtual '{PORT_NAME}' (¿está instalado loopMIDI / teVirtualMIDI?)")

    def _on_data(self, port, data, length, instance):
        if not data or not length:
            return
        for byte in bytes(data[:length]):
            if byte == 0xF0:
                self._buffer = bytearray()
            elif byte == 0xF7:
                if self._buffer is not None:
                    self._handle(bytes(self._buffer))
                self._buffer = None
            elif self._buffer is not None:
                self._buffer.append(byte)

    def _handle(self, message):
        if len(message) < 2 or message[0] != SYSEX_ID:
            return
        field = message[1]
        deck_index, name = (field >> 4) - 1, FIELDS.get(field & 0x0F)
        if deck_index not in (0, 1) or name is None:
            return
        encoding = "utf-8" if name.endswith("_utf8") else "ascii"
        text = message[2:].decode(encoding, "replace").strip()
        if name in THOUSANDTHS:
            try:
                value = int(text) / 1000
            except ValueError:
                return
        elif name in FLAGS:
            value = text == "1"
        else:
            value = text
        deck = self.decks[deck_index]
        with self.lock:
            self.messages += 1
            if deck.values.get(name) != value:
                if name in deck.values:
                    deck.changed_at[name] = time.perf_counter()
                deck.values[name] = value

    def close(self):
        if self._port:
            self._dll.virtualMIDIClosePort(self._port)
            self._port = None
