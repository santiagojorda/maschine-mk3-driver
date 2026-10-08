"""Mantiene el puerto MIDI virtual "MK3 Screens" por donde VirtualDJ manda el estado de los decks.

Corre aparte del prototipo (dj_screens.py lo lanza si no está) para que reiniciar el
prototipo no cierre el puerto: VirtualDJ no se reconecta a un puerto que desaparece
hasta que se reinicia. Pasa cada sysex por UDP a vdj_data.py y guarda el último de
cada campo: cuando el prototipo pide "todo", se los reenvía.

El puerto se abre sin que el driver arme los mensajes: el título en UTF-8 trae bytes
de 8 bits que cortarían un sysex, así que se juntan acá de F0 a F7.

Uso: python vdj_puerto.py   (si ya hay uno corriendo, este sale solo)
"""

import ctypes
import ctypes.wintypes as W
import socket
import sys
import threading
import time

from vdj_data import BRIDGE_ADDRESS, DATA_PORT, REQUEST_ALL, SYSEX_ID

PORT_NAME = "MK3 Screens"

_MIDI_DATA_CALLBACK = ctypes.WINFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(ctypes.c_ubyte), W.DWORD, ctypes.c_void_p)


class PortBridge:
    def __init__(self, sock):
        self._socket = sock
        self._lock = threading.Lock()
        self._last = {}  # campo -> último sysex
        self._buffer = None  # bytes del sysex en curso
        self.messages = 0
        dll = ctypes.WinDLL("teVirtualMIDI64.dll")
        dll.virtualMIDICreatePortEx2.restype = ctypes.c_void_p
        dll.virtualMIDICreatePortEx2.argtypes = [W.LPCWSTR, _MIDI_DATA_CALLBACK, ctypes.c_void_p, W.DWORD, W.DWORD]
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
                    self._forward(bytes(self._buffer))
                self._buffer = None
            elif self._buffer is not None:
                self._buffer.append(byte)

    def _forward(self, message):
        if len(message) < 2 or message[0] != SYSEX_ID:
            return
        with self._lock:
            self._last[message[1]] = message
            self.messages += 1
        self._send(message)

    def _send(self, message):
        try:
            self._socket.sendto(message, ("127.0.0.1", DATA_PORT))
        except OSError:
            pass

    def send_all(self):
        with self._lock:
            messages = list(self._last.values())
        for message in messages:
            self._send(message)


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(BRIDGE_ADDRESS)
    except OSError:
        print("Ya hay un vdj_puerto.py corriendo")
        return 0
    try:
        bridge = PortBridge(sock)
    except Exception as error:
        print(error)
        return 1
    print(f"Puerto '{PORT_NAME}' creado; datos por UDP a {DATA_PORT}", flush=True)
    sock.settimeout(5.0)
    last_report = time.perf_counter()
    while True:
        try:
            request, _ = sock.recvfrom(64)
            if request == REQUEST_ALL:
                bridge.send_all()
        except (socket.timeout, ConnectionResetError):
            pass
        if time.perf_counter() - last_report > 60:
            print(f"{bridge.messages} mensajes de VirtualDJ", flush=True)
            last_report = time.perf_counter()


if __name__ == "__main__":
    sys.exit(main())
