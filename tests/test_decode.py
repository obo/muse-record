"""Decoders, checked against packets captured live from a Muse 2."""
import pytest

import muse_record as mr


def test_eeg_packet():
    seq, uv = mr.decode_eeg(bytes.fromhex("14dc8007fe7ee8546b67adb7691b5cf504778b50"))
    assert seq == 0x14DC
    assert len(uv) == 12
    # first two 12-bit values: 0x800 -> 0 uV, 0x7fe -> -2 LSB
    assert uv[0] == 0.0
    assert uv[1] == pytest.approx(-2 * 0.48828125)
    assert uv[2] == pytest.approx((0x7EE - 0x800) * 0.48828125)


def test_drlref_packet():
    seq, pairs = mr.decode_drlref(bytes.fromhex("04a080b7ca80b7c980b7c980b7ca80b7ca80b7ca"))
    assert seq == 0x04A0
    assert len(pairs) == 6
    assert pairs[0] == (pytest.approx(5.37109375), pytest.approx(-26.3671875))


def test_ppg_packet():
    seq, vals = mr.decode_ppg(bytes.fromhex("0a6e016ac00182a001828301827f018242018228"))
    assert seq == 0x0A6E
    assert vals == [0x016AC0, 0x0182A0, 0x018283, 0x01827F, 0x018242, 0x018228]


def test_imu_packet():
    data = bytes.fromhex("0001" "0001ffff7fff" "800000000000" "000200030004")
    seq, samples = mr.decode_imu(data, 1.0)
    assert seq == 1
    assert samples == [(1, -1, 32767), (-32768, 0, 0), (2, 3, 4)]


def test_telemetry_packet():
    seq, (bat, fuel, adc, temp) = mr.decode_telemetry(
        bytes.fromhex("0014c80005e00000000000000000000000000000"))
    assert seq == 20
    assert bat == 100.0
    assert fuel == pytest.approx(3308.8)
    assert (adc, temp) == (0.0, 0.0)


def test_encode_command():
    assert mr.encode_command("p50") == b"\x04p50\n"
    assert mr.encode_command("d") == b"\x02d\n"
