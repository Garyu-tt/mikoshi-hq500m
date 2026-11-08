"""Optional native C99 batch generator for the original HQ500M C5 synapses.

This only accelerates exact C5 edge generation. Event delivery, LIF,
plasticity, page scheduling and telemetry still run in Python.
No auto-compilation, network install, GPU code, or dynamic system loader paths.
"""
import ctypes
from pathlib import Path
from .core import VIRTUAL_NEURONS

EDGE_GAIN = 0.000035
BATCH_CAP = 8192
LIB_PATH = Path(__file__).resolve().parent / "native" / "libhq500m_c5.so"


class NativeUnavailable(RuntimeError):
    pass


class NativeC5:
    def __init__(self, library_path=None):
        path = LIB_PATH if library_path is None else Path(library_path).resolve()
        if not path.is_file():
            raise NativeUnavailable(
                "native C5 library not built; run: "
                "sh hq500m/native/build.sh (or select --kernel python)"
            )
        try:
            library = ctypes.CDLL(str(path))
            library.hq500m_c5_abi_version.argtypes = []
            library.hq500m_c5_abi_version.restype = ctypes.c_uint32
            if library.hq500m_c5_abi_version() != 1:
                raise NativeUnavailable("native C5 ABI version mismatch")
            library.hq500m_c5_batch.argtypes = [
                ctypes.POINTER(ctypes.c_uint32), ctypes.c_size_t,
                ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_int32),
                ctypes.c_size_t,
            ]
            library.hq500m_c5_batch.restype = ctypes.c_int
        except (AttributeError, OSError) as exc:
            raise NativeUnavailable("invalid native C5 shared library") from exc
        self._lib = library
        self.library_path = str(path)

    def batch(self, source_ids):
        n = len(source_ids)
        if not 0 <= n <= BATCH_CAP:
            raise ValueError("native C5 batch must contain 0..8192 source IDs")
        if any(type(gid) is not int or not 0 <= gid < VIRTUAL_NEURONS
               for gid in source_ids):
            raise ValueError("invalid source ID in native C5 batch")
        if n == 0:
            return (), ()
        inputs = (ctypes.c_uint32 * n)(*source_ids)
        targets = (ctypes.c_uint32 * (32 * n))()
        weights = (ctypes.c_int32 * (32 * n))()
        status = self._lib.hq500m_c5_batch(inputs, n, targets, weights, 32 * n)
        if status != 0:
            raise RuntimeError("native C5 batch failed with status " + str(status))
        return targets, weights
