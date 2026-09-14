"""
Flow routing on a DEM grid, used by cascade.py. Not a source itself.

route() floods the grid inward from its edges with a priority queue (Barnes et al. 2014,
"Priority-Flood"). Every cell drains to the neighbour it was flooded from, which fills every
depression and gives each cell exactly one downstream cell without a separate flat-resolving step.

Lakes are single units: all cells of a lake drain to one outlet, the cell the flood first entered
the lake from. That is the lowest point on the lake's rim, where it overflows.
"""

import heapq

import numpy as np
from numba import njit

# D8 neighbour offsets.
DR = np.array([-1, -1, -1, 0, 0, 1, 1, 1], dtype=np.int64)
DC = np.array([-1, 0, 1, -1, 1, -1, 0, 1], dtype=np.int64)


@njit(cache=True)
def _flood(z, seed):
    """
    z: 2-D float32 elevations. seed: 2-D bool, cells where water leaves the grid (edges, missing data).
    Returns (receiver, order): receiver[i] is the flat index each cell drains to (-1 for seeds),
    order is the flat indices in the sequence they were flooded; every receiver comes before its cells.
    """
    rows, cols = z.shape
    n = rows * cols
    flat = z.ravel()
    receiver = np.full(n, -1, dtype=np.int64)
    order = np.empty(n, dtype=np.int64)
    done = np.zeros(n, dtype=np.bool_)
    level = np.empty(n, dtype=np.float32)
    heap = [(np.float32(0.0), np.int64(0), np.int64(0))]
    heap.pop()
    pit = np.empty(n, dtype=np.int64)  # FIFO of cells inside a depression, filled to the spill level
    pit_head = 0
    pit_tail = 0
    counter = 0
    seeds = seed.ravel()
    for i in range(n):
        if seeds[i]:
            done[i] = True
            level[i] = flat[i]
            heapq.heappush(heap, (flat[i], np.int64(counter), np.int64(i)))
            counter += 1
    k = 0
    while pit_head < pit_tail or len(heap) > 0:
        if pit_head < pit_tail:
            c = pit[pit_head]
            pit_head += 1
        else:
            _, _, c = heapq.heappop(heap)
        order[k] = c
        k += 1
        r, cc = c // cols, c % cols
        for d in range(8):
            nr, nc = r + DR[d], cc + DC[d]
            if nr < 0 or nr >= rows or nc < 0 or nc >= cols:
                continue
            j = nr * cols + nc
            if done[j]:
                continue
            done[j] = True
            receiver[j] = c
            if flat[j] <= level[c]:
                level[j] = level[c]
                pit[pit_tail] = j
                pit_tail += 1
            else:
                level[j] = flat[j]
                heapq.heappush(heap, (flat[j], np.int64(counter), np.int64(j)))
                counter += 1
    return receiver, order[:k]


@njit(cache=True)
def _lake_outlets(lake, receiver, order, n_lakes):
    """For each lake id (1..n_lakes), the first lake cell flooded and the cell it was flooded from."""
    first = np.full(n_lakes + 1, -1, dtype=np.int64)
    outlet = np.full(n_lakes + 1, -1, dtype=np.int64)
    for c in order:
        lk = lake[c]
        if lk > 0 and first[lk] < 0:
            first[lk] = c
            outlet[lk] = receiver[c]
    return first, outlet


@njit(cache=True)
def _teleport(lake, receiver, outlet):
    """Point every lake cell straight at its lake's outlet cell."""
    out = receiver.copy()
    for c in range(lake.size):
        lk = lake[c]
        if lk > 0:
            out[c] = outlet[lk]
    return out


@njit(cache=True)
def _accumulate(receiver, order, cell_area):
    acc = cell_area.copy()
    for i in range(order.size - 1, -1, -1):
        c = order[i]
        r = receiver[c]
        if r >= 0:
            acc[r] += acc[c]
    return acc


@njit(cache=True)
def _first_downstream(receiver, order, label):
    """
    For every cell, the first non-zero label met strictly downstream of it (0 if none before the edge).
    Walks the flood order forwards, so each receiver is resolved before the cells draining to it.
    """
    down = np.zeros(receiver.size, dtype=label.dtype)
    for c in order:
        r = receiver[c]
        if r >= 0:
            down[c] = label[r] if label[r] != 0 else down[r]
    return down


class Routing:
    """Flow directions and accumulation for one grid. lake: 2-D int32 lake ids (0 = no lake), or None."""

    def __init__(self, z, seed, cell_area_rows, lake=None):
        self.shape = z.shape
        self.receiver, self.order = _flood(z, seed)
        self.lake = None if lake is None else lake.ravel()
        if lake is not None:
            n_lakes = int(lake.max())
            self.lake_first, self.lake_outlet = _lake_outlets(self.lake, self.receiver, self.order, n_lakes)
            self.receiver = _teleport(self.lake, self.receiver, self.lake_outlet)
        area = np.repeat(cell_area_rows.astype(np.float64), self.shape[1])
        self.acc = _accumulate(self.receiver, self.order, area)

    def first_downstream(self, label):
        return _first_downstream(self.receiver, self.order, label.ravel())

    def path(self, start, limit=10_000_000):
        """Flat indices from start down to the grid edge."""
        out, c = [], start
        while c >= 0 and len(out) < limit:
            out.append(c)
            c = self.receiver[c]
        return out
