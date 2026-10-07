"""Sigue el modo de la Maschine (DJ o Ableton) escuchando su puerto MIDI.

Usa los mismos botones que el mapeo de maschine-mk3-ableton-virtualdj
(Control Change en canal MIDI 2, valor 127 al apretar):
SAMPLING = CC 39 entra a modo DJ; MIXER = CC 37 y PLUGIN = CC 35 vuelven a Ableton.

El puerto se abre como un cliente más: Windows MIDI Services deja que varios
programas lo usen a la vez.
"""

import threading

import mido

DJ = "dj"
ABLETON = "ableton"

MODE_CHANNEL = 1  # mido numera desde 0: 1 = canal MIDI 2
SAMPLING_CC = 39
MIXER_CC = 37
PLUGIN_CC = 35

DEFAULT_PORT_HINT = "Maschine MK3 Ctrl MIDI"


def find_input_port(hint):
    names = mido.get_input_names()
    for name in names:
        if hint.lower() in name.lower():
            return name
    raise RuntimeError(f"No hay un puerto MIDI que contenga '{hint}'. Puertos: {names}")


def mode_for_message(message):
    """Devuelve DJ, ABLETON o None si el mensaje no cambia el modo."""
    if message.type != "control_change" or message.channel != MODE_CHANNEL or message.value == 0:
        return None
    if message.control == SAMPLING_CC:
        return DJ
    if message.control in (MIXER_CC, PLUGIN_CC):
        return ABLETON
    return None


class ModeWatcher:
    def __init__(self, port_hint=DEFAULT_PORT_HINT, start_mode=ABLETON, on_change=None, on_message=None):
        self._lock = threading.Lock()
        self._mode = start_mode
        self._on_change = on_change
        self._on_message = on_message
        self.port_name = find_input_port(port_hint)
        self._port = mido.open_input(self.port_name, callback=self._handle)

    @property
    def mode(self):
        with self._lock:
            return self._mode

    def _handle(self, message):
        if self._on_message:
            self._on_message(message)
        new_mode = mode_for_message(message)
        if new_mode is None:
            return
        with self._lock:
            changed = new_mode != self._mode
            self._mode = new_mode
        if changed and self._on_change:
            self._on_change(new_mode)

    def close(self):
        self._port.close()
