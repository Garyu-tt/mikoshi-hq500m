"""Optional native C99 batch generator for the original HQ500M C5 synapses.

Optional C99 kernels cover C5 edge generation, exact ordered event
reduction and batched numerical LIF integration. Python remains the
owner of page residency, queues, plasticity, checkpoints and telemetry.
The user must explicitly select native event/LIF; default is Python.
No auto-compilation, network install, GPU code, or dynamic system loader paths.
"""
import ctypes
from array import array
from pathlib import Path
from .core import VIRTUAL_NEURONS

EDGE_GAIN = 0.000035
BATCH_CAP = 8192
EVENT_CAP = 1_200_000
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
            library.hq500m_event_lif_abi_version.argtypes = []
            library.hq500m_event_lif_abi_version.restype = ctypes.c_uint32
            if library.hq500m_event_lif_abi_version() != 1:
                raise NativeUnavailable("native event/LIF ABI mismatch")
            library.hq500m_reduce_sorted.argtypes = [
                ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_double),
                ctypes.c_size_t, ctypes.POINTER(ctypes.c_uint32),
                ctypes.POINTER(ctypes.c_double), ctypes.c_size_t,
                ctypes.POINTER(ctypes.c_size_t)]
            library.hq500m_reduce_sorted.restype = ctypes.c_int
            library.hq500m_lif_batch.argtypes = [
                ctypes.POINTER(ctypes.c_double),
                ctypes.POINTER(ctypes.c_int64),
                ctypes.POINTER(ctypes.c_int64),
                ctypes.POINTER(ctypes.c_double),
                ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t,
                ctypes.c_int64, ctypes.c_double]
            library.hq500m_lif_batch.restype = ctypes.c_int
        except (AttributeError, OSError) as exc:
            raise NativeUnavailable("invalid native C5/event shared library") from exc
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


    def reduce_sorted(self, events):
        """Exact binary64 ordered grouping; events sorted by (dst,src,slot)."""
        n = len(events)
        if not 0 <= n <= EVENT_CAP:
            raise ValueError("native event batch exceeds 1,200,000")
        if n == 0:
            return {}
        ids = array("I", (ev[0] for ev in events))
        currents = array("d", (ev[1] for ev in events))
        out_ids = (ctypes.c_uint32*n)()
        out_currents = (ctypes.c_double*n)()
        count = ctypes.c_size_t(0)
        status = self._lib.hq500m_reduce_sorted(
            (ctypes.c_uint32*n).from_buffer(ids),
            (ctypes.c_double*n).from_buffer(currents), n,
            out_ids, out_currents, n, ctypes.byref(count))
        if status:
            raise ValueError("native event reducer rejected unsorted/invalid events")
        return {out_ids[i]: out_currents[i] for i in range(count.value)}

    def lif_rows(self, rows, now, threshold):
        """Bulk exact lazy-LIF integration; each row=(v,last_tick,last_fire,I).

        Returns per-cell (v,last_tick,last_fire,flag) in input order.
        Caller controls all page state/learning/clock semantics.
        """
        n = len(rows)
        if not 0 <= n <= EVENT_CAP:
            raise ValueError("native LIF batch too large")
        if n == 0:
            return []
        voltages = array("d", (v for v, lt, lf, current in rows))
        updates = array("q", (lt for v, lt, lf, current in rows))
        fires = array("q", (lf for v, lt, lf, current in rows))
        currents = array("d", (current for v, lt, lf, current in rows))
        flags = (ctypes.c_ubyte*n)()
        status = self._lib.hq500m_lif_batch(
            (ctypes.c_double*n).from_buffer(voltages),
            (ctypes.c_int64*n).from_buffer(updates),
            (ctypes.c_int64*n).from_buffer(fires),
            (ctypes.c_double*n).from_buffer(currents),
            flags, n, now, threshold)
        if status:
            raise ValueError("native lazy LIF rejected input state")
        return [(voltages[i], updates[i], fires[i], bool(flags[i]))
                for i in range(n)]
