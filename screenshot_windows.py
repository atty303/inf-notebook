import ctypes
from ctypes import windll, wintypes, create_string_buffer
import numpy as np
from logging import getLogger

logger = getLogger().getChild('screenshot_windows')

SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0
PW_CLIENTONLY = 1

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', wintypes.DWORD),
        ('biWidth', wintypes.LONG),
        ('biHeight', wintypes.LONG),
        ('biPlanes', wintypes.WORD),
        ('biBitCount', wintypes.WORD),
        ('biCompression', wintypes.DWORD),
        ('biSizeImage', wintypes.DWORD),
        ('biXPelsPerMeter', wintypes.LONG),
        ('biYPelsPerMeter', wintypes.LONG),
        ('biClrUsed', wintypes.DWORD),
        ('biClrImportant', wintypes.DWORD),
    ]

class RGBQUAD(ctypes.Structure):
    _fields_ = [
        ('rgbRed', ctypes.c_byte),
        ('rgbGreen', ctypes.c_byte),
        ('rgbBlue', ctypes.c_byte),
        ('rgbReserved', ctypes.c_byte),
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ('bmiHeader', BITMAPINFOHEADER),
        ('bmiColors', ctypes.POINTER(RGBQUAD))
    ]

class WindowsCapture:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.bmi = BITMAPINFO()
        self.bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        self.bmi.bmiHeader.biWidth = self.width
        self.bmi.bmiHeader.biHeight = self.height
        self.bmi.bmiHeader.biPlanes = 1
        self.bmi.bmiHeader.biBitCount = 24
        self.bmi.bmiHeader.biCompression = 0
        self.bmi.bmiHeader.biSizeImage = 0

        self.screen = windll.gdi32.CreateDCW("DISPLAY", None, None, None)
        self.screen_copy = windll.gdi32.CreateCompatibleDC(self.screen)
        self.bitmap = windll.gdi32.CreateCompatibleBitmap(self.screen, self.width, self.height)

        windll.gdi32.SelectObject(self.screen_copy, self.bitmap)

        self.buffer = create_string_buffer(self.height * self.width * 3)
    
    def shot(self, left, top):
        windll.gdi32.BitBlt(self.screen_copy, 0, 0, self.width, self.height, self.screen, left, top, SRCCOPY)
        windll.gdi32.GetDIBits(self.screen_copy, self.bitmap, 0, self.height, ctypes.pointer(self.buffer), ctypes.pointer(self.bmi), DIB_RGB_COLORS)

        return np.array(bytearray(self.buffer)).reshape(self.height, self.width, 3)

    def __del__(self):
        windll.gdi32.DeleteObject(self.bitmap)
        windll.gdi32.DeleteDC(self.screen_copy)
        windll.gdi32.DeleteDC(self.screen)

        logger.debug('Called Windows Screenshot destructor.')