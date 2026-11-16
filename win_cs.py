"""
Модуль для работы с критическими секциями Windows.

Во 2 задании по условию нужно использовать системные функции:
EnterCriticalSection() и LeaveCriticalSection().
"""

import ctypes
from ctypes import wintypes

# Загружаем библиотеку kernel32, где находятся нужные функции Windows
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class CRITICAL_SECTION(ctypes.Structure):
    """Структура CRITICAL_SECTION из WinAPI."""

    _fields_ = [
        ("DebugInfo", ctypes.c_void_p),
        ("LockCount", wintypes.LONG),
        ("RecursionCount", wintypes.LONG),
        ("OwningThread", wintypes.HANDLE),
        ("LockSemaphore", wintypes.HANDLE),
        ("SpinCount", ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else wintypes.ULONG),
    ]


# Описываем функции WinAPI
InitializeCriticalSection = kernel32.InitializeCriticalSection
InitializeCriticalSection.argtypes = [ctypes.POINTER(CRITICAL_SECTION)]
InitializeCriticalSection.restype = None

EnterCriticalSection = kernel32.EnterCriticalSection
EnterCriticalSection.argtypes = [ctypes.POINTER(CRITICAL_SECTION)]
EnterCriticalSection.restype = None

LeaveCriticalSection = kernel32.LeaveCriticalSection
LeaveCriticalSection.argtypes = [ctypes.POINTER(CRITICAL_SECTION)]
LeaveCriticalSection.restype = None

DeleteCriticalSection = kernel32.DeleteCriticalSection
DeleteCriticalSection.argtypes = [ctypes.POINTER(CRITICAL_SECTION)]
DeleteCriticalSection.restype = None


class WinCriticalSection:
    """
    Класс-обёртка для критической секции.

    enter()  -> вход в критическую секцию (EnterCriticalSection)
    leave()  -> выход из критической секции (LeaveCriticalSection)
    """

    def __init__(self):
        self.cs = CRITICAL_SECTION()
        InitializeCriticalSection(ctypes.byref(self.cs))

    def enter(self):
        # Входим в критическую секцию (если она занята, поток будет ждать)
        EnterCriticalSection(ctypes.byref(self.cs))

    def leave(self):
        # Выходим из критической секции
        LeaveCriticalSection(ctypes.byref(self.cs))

    def __del__(self):
        # При удалении объекта освобождаем ресурсы критической секции
        try:
            DeleteCriticalSection(ctypes.byref(self.cs))
        except Exception:
            pass
