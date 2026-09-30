"""Sample clock, multi-characteristic assembly and ordered CSV output."""
import io

import muse_record as mr

MS = 1_000_000


def test_clock_spacing_wrap_and_loss():
    c = mr.SampleClock(256.0, 12)
    period = 1e9 / 256
    t = 1_000_000 * MS
    ts = c.packet(65534, t)
    assert ts[1] - ts[0] == int(period) or abs(ts[1] - ts[0] - period) < 2
    assert abs(ts[-1] - t) < 2  # least-delayed packet anchors the last sample
    ts2 = c.packet(65535, t + int(12 * period))
    ts3 = c.packet(1, t + int(36 * period))  # wraps, one packet (seq 0) lost
    assert c.lost_packets == 1
    assert abs(ts3[0] - ts2[-1] - 13 * period) < 2


def test_clock_monotonic_under_jitter_and_rate_error():
    # true rate 50.8 Hz, nominal 52 Hz, arrival jitter up to 40 ms
    import random
    rnd = random.Random(1)
    c = mr.SampleClock(52.0, 3)
    true_period = 1e9 / 50.8
    last = None
    for p in range(3000):  # ~3 minutes
        arrival = int(1e18 + (p * 3 + 2) * true_period + 5 * MS + rnd.random() * 40 * MS)
        for t in c.packet(p & 0xFFFF, arrival):
            if last is not None:
                assert t > last
            last = t
    assert abs(c.rate_hz - 50.8) < 0.05


def test_assembler_joins_channels():
    blocks = []
    a = mr.MultiCharAssembler(lambda s, t, c: blocks.append((s, sorted(c))))
    for seq in range(10):
        for i, col in enumerate(["TP9", "AF7", "AF8"]):
            a.add(col, seq, seq * 100 + i, [0.0])
    a.flush()
    assert [s for s, _ in blocks] == list(range(10))
    assert all(cols == ["AF7", "AF8", "TP9"] for _, cols in blocks)


def test_writer_orders_and_formats():
    out = io.StringIO()
    w = mr.OrderedCSVWriter(out, latency_ns=0, include_raw=False, include_seq=False)
    w.add(2_000, "acc", 1, {"ax": 0.5})
    w.add(1_000, "eeg", 1, {"TP9": -1.5})
    w.flush(everything=True)
    lines = out.getvalue().splitlines()
    assert lines[0].split(",")[:4] == ["timestamp_ns", "timestamp_iso", "stream", "TP9"]
    assert len(lines[0].split(",")) == len(lines[1].split(","))
    assert lines[1].startswith("1000,1970-01-01T00:00:00.000001000Z,eeg,-1.5,")
    assert lines[2].split(",")[2] == "acc"
