"""Utilidades ligeras de diagnóstico de RAM sin dependencias externas."""
from __future__ import annotations

import gc
import os
import sys


def current_rss_mb() -> float | None:
    """RSS actual del proceso en MB cuando el sistema lo permite."""
    try:
        if sys.platform.startswith("win"):
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                    ("PrivateUsage", ctypes.c_size_t),
                ]

            counters = PROCESS_MEMORY_COUNTERS_EX()
            counters.cb = ctypes.sizeof(counters)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ok = ctypes.windll.psapi.GetProcessMemoryInfo(
                handle, ctypes.byref(counters), counters.cb
            )
            return counters.WorkingSetSize / (1024.0 * 1024.0) if ok else None
        if sys.platform.startswith("linux"):
            with open("/proc/self/statm", "r", encoding="ascii") as fh:
                resident_pages = int(fh.read().split()[1])
            return resident_pages * os.sysconf("SC_PAGE_SIZE") / (1024.0 * 1024.0)
    except Exception:
        return None
    return None


def collect_and_log(label: str = "") -> float | None:
    """Fuerza GC y, solo con SOMBRA_MEMORY_DEBUG=1, imprime RSS."""
    gc.collect()
    rss = current_rss_mb()
    if os.environ.get("SOMBRA_MEMORY_DEBUG") == "1" and rss is not None:
        print(f"[RAM] {label or 'estado'}: {rss:.1f} MB")
    return rss
