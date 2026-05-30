import binascii
import contextlib
import os
import struct
import time
from typing import Any

import serial
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from serial.tools import list_ports

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

BAUDRATE = 115200
DEFAULT_TIMEOUT = 5.0
OSSKEY_VID = 0x2E8A
OSSKEY_PID = 0x10B5


def _crc32(data: bytes) -> int:
    # Use the built-in binascii.crc32 for significantly better performance
    # binascii.crc32 returns an unsigned 32-bit integer.
    return binascii.crc32(data) & 0xFFFFFFFF


class SerialCommsError(Exception):
    pass


class SerialComms:
    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._port: serial.Serial | None = None
        self._timeout = timeout
        self._rx = bytearray()

    def find_device(self) -> str | None:
        for port in list_ports.comports():
            if port.vid == OSSKEY_VID and port.pid == OSSKEY_PID:
                return port.device
        return None

    def connect(self, port: str) -> None:
        self._port = serial.Serial(
            port,
            baudrate=BAUDRATE,
            timeout=self._timeout,
            exclusive=True,
            dsrdtr=False,
        )
        self._rx = bytearray()

    def disconnect(self) -> None:
        if self._port is not None:
            with contextlib.suppress(Exception):
                self._port.close()
            self._port = None
        self._rx = bytearray()

    @property
    def connected(self) -> bool:
        return self._port is not None and self._port.is_open

    def ping(self) -> bool:
        try:
            resp, _ = self._send_command(CMD_PING)
            return resp == RSP_ACK
        except SerialCommsError:
            return False

    def put_vault(self, blob: bytes) -> None:
        resp, payload = self._send_command(CMD_PUT_VAULT, blob)
        if resp == RSP_NAK:
            reason = payload[0] if payload else 0
            raise SerialCommsError(f"PUT_VAULT rejected (error {reason})")

    def inject(self, label: str, username: str, password: str) -> None:
        label_b = label.encode("utf-8", errors="replace")
        user_b = username.encode("utf-8", errors="replace")
        pass_b = password.encode("utf-8", errors="replace")
        payload = bytearray(label_b + b"\x00" + user_b + b"\x00" + pass_b + b"\x00")
        try:
            resp, rpayload = self._send_command(CMD_INJECT, bytes(payload))
            if resp == RSP_NAK:
                reason = rpayload[0] if rpayload else 0
                raise SerialCommsError(f"INJECT rejected (error {reason})")
        finally:
            for i in range(len(payload)):
                payload[i] = 0

    def lock(self) -> None:
        resp, _ = self._send_command(CMD_LOCK)
        if resp == RSP_NAK:
            raise SerialCommsError("LOCK rejected")

    def set_key(self, key: bytes) -> None:
        resp, _ = self._send_command(CMD_SET_KEY, key)
        if resp == RSP_NAK:
            raise SerialCommsError("SET_KEY rejected")

    def inject_encrypted(self, username: str, password: str, key: bytes) -> None:
        payload = username.encode("utf-8", errors="replace") + b"\x00" + password.encode("utf-8", errors="replace")
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ct_tag = aesgcm.encrypt(nonce, payload, None)
        body = nonce + ct_tag

        ecb = Cipher(algorithms.AES256(key), modes.ECB(), backend=default_backend())  # noqa: S305
        enc = ecb.encryptor()
        x = bytes(16)
        for i in range(0, len(body), 16):
            block = body[i:i + 16]
            if len(block) < 16:
                block = block + b"\x80" + b"\x00" * (15 - len(block))
            xored = bytes(a ^ b for a, b in zip(x, block, strict=True))
            x = enc.update(xored)
        enc.finalize()
        mac_tag = x[:4]

        self.set_key(key)
        resp, rpayload = self._send_command(CMD_INJECT_ENC, body + mac_tag)
        if resp == RSP_NAK:
            reason = rpayload[0] if rpayload else 0
            raise SerialCommsError(f"INJECT_ENC rejected (error {reason})")

    def wipe(self) -> None:
        resp, _ = self._send_command(CMD_WIPE)
        if resp == RSP_NAK:
            raise SerialCommsError("WIPE rejected")

    def _send_command(self, cmd: int, payload: bytes = b"") -> tuple[int, bytes]:
        if self._port is None:
            raise SerialCommsError("Not connected")

        header = bytes([STX, 0, len(payload) & 0xFF, (len(payload) >> 8) & 0xFF, cmd])
        data = header + payload
        crc = _crc32(data)
        frame = data + struct.pack("<I", crc) + bytes([ETX])
        self._port.write(frame)
        return self._read_response(cmd)

    def _read_response(self, cmd: int) -> tuple[int, bytes]:
        start_time = time.time()
        while (time.time() - start_time) < self._timeout:
            response = self._try_parse()
            if response is not None:
                resp_cmd, resp_payload = response
                return resp_cmd, resp_payload
            chunk = self._port.read(1)
            if not chunk:
                raise SerialCommsError(f"Timeout waiting for response to cmd 0x{cmd:02x}")
            self._rx.extend(chunk)

    def _try_parse(self) -> tuple[int, bytes] | None:
        while len(self._rx) >= 9:
            idx = self._rx.find(bytes([STX]))
            if idx < 0:
                self._rx = bytearray()
                return None
            if idx > 0:
                self._rx = self._rx[idx:]
                continue
            if len(self._rx) < 5:
                return None
            payload_len = self._rx[2] | (self._rx[3] << 8)
            cmd = self._rx[4]
            total = 10 + payload_len
            if len(self._rx) < total:
                return None
            frame = self._rx[:total]
            self._rx = self._rx[total:]
            crc_off = 5 + payload_len
            if len(frame) < crc_off + 5:
                continue
            if frame[crc_off + 4] != ETX:
                continue
            recv_crc = struct.unpack_from("<I", frame, crc_off)[0]
            data = frame[:crc_off]
            if _crc32(data) != recv_crc:
                continue
            payload = frame[5:crc_off]
            return cmd, bytes(payload)
        return None

    def __enter__(self) -> "SerialComms":
        return self

    def __exit__(self, *args: Any) -> None:
        self.disconnect()
