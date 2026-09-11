"""CRC-framed simulated serial transport to the actual compiled controller."""

import binascii
import ctypes
import os
import sys
from pathlib import Path

STATES = [
    "IDLE",
    "PUMP_DOWN",
    "HEAT",
    "STABILIZE",
    "DEPOSITION",
    "PURGE",
    "COOLDOWN",
    "COMPLETE",
    "FAULT",
]
FAULTS = [
    "NONE",
    "PROTOCOL",
    "STALE",
    "SENSOR",
    "DOOR",
    "ESTOP",
    "OVERTEMP",
    "OVERPRESSURE",
    "TIMEOUT",
    "ABORT",
    "RECIPE",
    "PROCESS_WINDOW",
]


def frame(payload: str) -> bytes:
    data = payload.encode("ascii")
    return data + f"*{binascii.crc_hqx(data, 0xFFFF):04X}\n".encode("ascii")


def unframe(data: bytes) -> str:
    if len(data) > 319 or not data.endswith(b"\n"):
        raise ValueError("Invalid frame length or terminator")
    payload, checksum = data[:-1].rsplit(b"*", 1)
    if (
        len(checksum) != 4
        or any(c not in b"0123456789ABCDEF" for c in checksum)
        or binascii.crc_hqx(payload, 0xFFFF) != int(checksum, 16)
    ):
        raise ValueError("CRC mismatch")
    return payload.decode("ascii")


class Controller:
    def __init__(self, library=None):
        root = Path(__file__).resolve().parents[2]
        suffix = (
            ".dll" if sys.platform == "win32" else ".dylib" if sys.platform == "darwin" else ".so"
        )
        paths = [
            root / "build" / ("fabtwin_controller" + suffix),
            root / "build" / ("libfabtwin_controller" + suffix),
            root / "build/Release/fabtwin_controller.dll",
        ]
        supplied = library or os.environ.get("FABTWIN_CONTROLLER")
        path = Path(supplied) if supplied else next((p for p in paths if p.exists()), None)
        if path is None:
            raise FileNotFoundError(
                "Build the C++ controller first: python scripts/build_controller.py"
            )
        self.lib = ctypes.CDLL(str(path.resolve()))
        self.lib.ft_create.restype = ctypes.c_void_p
        self.lib.ft_destroy.argtypes = [ctypes.c_void_p]
        self.lib.ft_watchdog.argtypes = [ctypes.c_void_p, ctypes.c_double]
        self.lib.ft_exchange.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
        ]
        self.lib.ft_exchange.restype = ctypes.c_int
        self.handle = self.lib.ft_create()
        if not self.handle:
            raise MemoryError("Controller allocation failed")
        self.seq = 0

    def exchange(self, packet):
        if not self.handle:
            raise RuntimeError("Controller is closed")
        output = ctypes.create_string_buffer(320)
        n = self.lib.ft_exchange(self.handle, packet, len(packet), output, len(output))
        if n < 0:
            raise RuntimeError("C++ bridge failure")
        return output.raw[:n]

    def step(self, now, sensor, recipe, command=0, stamp=None):
        payload = f"FT1,{self.seq},{now:.6f},{now if stamp is None else stamp:.6f},{command},{sensor[0]:.6f},{sensor[1]:.6f},{sensor[2]:.6f},{int(sensor[3])},{int(sensor[4])},{recipe.temperature_c:.6f},{recipe.pressure_torr:.6f},{recipe.flow_sccm:.6f},{recipe.deposition_s:.6f}"
        fields = unframe(self.exchange(frame(payload))).split(",")
        if fields[0] != "FT1" or int(fields[1]) != self.seq:
            raise ValueError("Unexpected response sequence")
        self.seq = (self.seq + 1) % 2**32
        return dict(
            state=STATES[int(fields[2])],
            fault=FAULTS[int(fields[3])],
            heater=float(fields[4]),
            throttle=float(fields[5]),
            flow_command=float(fields[6]),
            precursor=bool(int(fields[7])),
        )

    def close(self):
        if self.handle:
            self.lib.ft_destroy(self.handle)
            self.handle = None

    def watchdog(self, now):
        if not self.handle:
            raise RuntimeError("Controller is closed")
        self.lib.ft_watchdog(self.handle, now)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
