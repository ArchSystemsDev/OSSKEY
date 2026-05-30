import struct
import time
import usb_cdc

CMD_PING = 0x01
CMD_PUT_VAULT = 0x03
CMD_INJECT = 0x05
CMD_LOCK = 0x06
CMD_WIPE = 0x07
CMD_SET_KEY = 0x08
CMD_INJECT_ENC = 0x09

RSP_ACK = 0x81
RSP_NAK = 0x82

STX = 0xFE
ETX = 0xFD

ERR_INVALID_PAYLOAD = 0x01
ERR_INJECTION_FAILED = 0x02
ERR_UNKNOWN_CMD = 0x03

_CRC_TABLE = None


def _build_crc32_table():
    global _CRC_TABLE
    _CRC_TABLE = [0] * 256
    for i in range(256):
        crc = i
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1
        _CRC_TABLE[i] = crc


def crc32(data):
    global _CRC_TABLE
    if _CRC_TABLE is None:
        _build_crc32_table()
    crc = 0xFFFFFFFF
    for byte in data:
        crc = _CRC_TABLE[(crc ^ byte) & 0xFF] ^ (crc >> 8)
    return crc ^ 0xFFFFFFFF


class SerialHandler:
    def __init__(self, serial=None):
        self._rx = bytearray()
        self._ser = serial
        if self._ser is not None:
            self._ser.timeout = 0

    @property
    def _serial(self):
        return self._ser

    def read_frame(self):
        ser = self._serial
        if ser is None:
            return None, None
        if ser.in_waiting > 0:
            chunk = ser.read(ser.in_waiting)
            self._rx.extend(chunk)
        return self._parse()

    def _parse(self):
        while len(self._rx) >= 9:
            idx = self._rx.find(bytes([STX]))
            if idx < 0:
                self._rx = bytearray()
                return None, None
            if idx > 0:
                self._rx = self._rx[idx:]
                continue
            if len(self._rx) < 5:
                return None, None
            flags = self._rx[1]
            payload_len = self._rx[2] | (self._rx[3] << 8)
            cmd = self._rx[4]
            total = 10 + payload_len
            if len(self._rx) < total:
                return None, None
            frame = self._rx[:total]
            self._rx = self._rx[total:]
            crc_off = 5 + payload_len
            if frame[crc_off + 4] != ETX:
                continue
            recv_crc = struct.unpack_from("<I", frame, crc_off)[0]
            data = frame[:crc_off]
            if crc32(data) != recv_crc:
                continue
            payload = frame[5:crc_off]
            return cmd, payload
        return None, None

    def send_ack(self, echoed_cmd):
        self._send_frame(RSP_ACK, bytes([echoed_cmd]))

    def send_nak(self, error_code):
        self._send_frame(RSP_NAK, bytes([error_code]))

    def _send_frame(self, cmd, payload=b""):
        header = bytes([STX, 0, len(payload) & 0xFF, (len(payload) >> 8) & 0xFF, cmd])
        data = header + payload
        crc = crc32(data)
        frame = data + struct.pack("<I", crc) + bytes([ETX])
        for attempt in range(3):
            ser = self._serial
            if ser is None:
                return
            try:
                ser.write(frame)
                return
            except Exception:
                if attempt < 2:
                    time.sleep(0.25)
                else:
                    return
