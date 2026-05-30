import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FW = os.path.dirname(HERE)

spec = importlib.util.spec_from_file_location("serial_handler", os.path.join(FW, "serial_handler.py"))
serial_handler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(serial_handler)

crc32 = serial_handler.crc32
STX = serial_handler.STX
ETX = serial_handler.ETX


def test_crc32_empty():
    assert crc32(b"") == 0


def test_crc32_nonzero():
    assert crc32(b"123456789") != 0
    assert crc32(b"hello") != 0


def test_crc32_different():
    assert crc32(b"abc") != crc32(b"abd")


def test_crc32_same():
    assert crc32(b"test data") == crc32(b"test data")


def test_crc32_consistent():
    for data in [b"", b"\x00", b"\xff" * 100, b"hello world" * 50]:
        assert crc32(data) == crc32(data)


def test_constants():
    assert STX == 0xFE
    assert ETX == 0xFD


def test_crc32_frame():
    data = bytes([STX, 0, 5, 0, 0x01]) + b"hello"
    crc = crc32(data)
    frame = data + crc.to_bytes(4, "little") + bytes([ETX])
    pd = frame[:-5]
    pc = int.from_bytes(frame[-5:-1], "little")
    pe = frame[-1]
    assert crc32(pd) == pc
    assert pe == ETX
