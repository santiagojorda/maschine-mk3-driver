"""Envía imágenes a las dos pantallas de la Maschine MK3 por USB.

Protocolo tomado de ni-controllers-lib (lib/components/output/ni_lcd_displays.ts):
interfaz 5, endpoint bulk 0x04, 2 pantallas de 480x272, píxeles RGB565 big endian.

Solo toma la interfaz 5. No llama a set_configuration para no resetear las
interfaces que sigue usando el programa de NI.
"""

import struct

import libusb_package
import numpy as np
import usb.core
import usb.util

VENDOR_ID = 0x17CC
PRODUCT_ID = 0x1600
DISPLAY_INTERFACE = 5
DISPLAY_ENDPOINT = 0x04
WIDTH = 480
HEIGHT = 272
NUM_DISPLAYS = 2

_BLIT = b"\x03\x00\x00\x00"
_END = b"\x40\x00\x00\x00"


def rgb_to_rgb565(rgb):
    """Convierte un array (alto, ancho, 3) uint8 en bytes RGB565 big endian."""
    r = rgb[..., 0].astype(np.uint16)
    g = rgb[..., 1].astype(np.uint16)
    b = rgb[..., 2].astype(np.uint16)
    value = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return value.astype(">u2").tobytes()


def build_frame(display, x, y, width, height, pixels):
    """Arma el paquete de un rectángulo: cabecera, comando, píxeles, dibujar y fin."""
    num_pixels = width * height
    if num_pixels % 2:
        raise ValueError("ancho x alto tiene que ser par")
    if len(pixels) != num_pixels * 2:
        raise ValueError(f"se esperaban {num_pixels * 2} bytes de píxeles, llegaron {len(pixels)}")

    header = bytearray(16)
    header[0] = 0x84
    header[2] = display
    header[3] = 0x60
    struct.pack_into(">HHHH", header, 8, x, y, width, height)

    # 24 bits big endian con la mitad de los píxeles; el primer byte es el comando (0)
    command = b"\x00" + struct.pack(">I", num_pixels // 2)[1:]

    return bytes(header) + command + pixels + _BLIT + _END


class MaschineDisplays:
    def __init__(self, timeout_ms=1000):
        self.timeout_ms = timeout_ms
        backend = libusb_package.get_libusb1_backend()
        self.device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID, backend=backend)
        if self.device is None:
            raise RuntimeError(
                "No se encontró la Maschine MK3 por libusb. ¿Está conectada y la "
                "interfaz 5 tiene WinUSB (Zadig)?"
            )
        usb.util.claim_interface(self.device, DISPLAY_INTERFACE)

    def send_rgb(self, display, rgb, x=0, y=0):
        """Dibuja un array (alto, ancho, 3) uint8 en la posición x, y de una pantalla."""
        height, width = rgb.shape[:2]
        frame = build_frame(display, x, y, width, height, rgb_to_rgb565(rgb))
        self.device.write(DISPLAY_ENDPOINT, frame, self.timeout_ms)

    def send_image(self, display, image):
        """Dibuja una imagen PIL de 480x272 en una pantalla."""
        self.send_rgb(display, np.asarray(image.convert("RGB")))

    def clear(self):
        black = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        for display in range(NUM_DISPLAYS):
            self.send_rgb(display, black)

    def close(self):
        try:
            usb.util.release_interface(self.device, DISPLAY_INTERFACE)
        finally:
            usb.util.dispose_resources(self.device)
