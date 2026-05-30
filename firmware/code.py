import time
import usb_cdc

from aes import aes_gcm_decrypt, aes_mac
from led import LEDController
from serial_handler import (
    SerialHandler,
    CMD_PING,
    CMD_PUT_VAULT,
    CMD_INJECT,
    CMD_LOCK,
    CMD_WIPE,
    CMD_SET_KEY,
    CMD_INJECT_ENC,
    RSP_NAK,
    ERR_INVALID_PAYLOAD,
    ERR_INJECTION_FAILED,
    ERR_UNKNOWN_CMD,
)
from hid_inject import HIDInjector
import vault


IDLE = 0
RECEIVING_VAULT = 1
READY = 2
INJECTING = 3


def _get_serial():
    if usb_cdc.data is not None:
        return usb_cdc.data
    return usb_cdc.console


def serial_connected():
    return _get_serial() is not None


def main():
    while True:
        try:
            _main()
        except BaseException:
            time.sleep(1)


def _main():
    led = LEDController()
    serial = SerialHandler(serial=_get_serial())
    hid = HIDInjector()

    state = IDLE
    device_key = None
    vault_flash_t = 0.0
    error_cooldown = 0.0

    led.set_mode(LEDController.IDLE)

    while True:
        led.update()

        now = time.monotonic()

        conn = serial_connected()

        if not conn:
            if state != IDLE:
                state = IDLE
                led.set_mode(LEDController.IDLE)
            continue

        if state == IDLE:
            if vault.vault_exists():
                state = READY
                led.set_mode(LEDController.READY)
            else:
                state = RECEIVING_VAULT
                led.set_mode(LEDController.CONNECTED)

        if state == READY and led.mode == LEDController.VAULT_LOAD:
            if now - vault_flash_t > 0.18:
                led.set_mode(LEDController.READY)

        if now < error_cooldown:
            continue

        cmd, payload = serial.read_frame()
        if cmd is None:
            continue

        if cmd == CMD_PING:
            serial.send_ack(CMD_PING)

        elif cmd == CMD_PUT_VAULT:
            try:
                vault.write_vault(payload)
                time.sleep(0.5)
                state = READY
                led.set_mode(LEDController.VAULT_LOAD)
                vault_flash_t = time.monotonic()
                serial.send_ack(CMD_PUT_VAULT)
            except Exception:
                time.sleep(0.5)
                serial.send_nak(ERR_INVALID_PAYLOAD)

        elif cmd == CMD_INJECT:
            try:
                nulls = []
                for i in range(1, len(payload)):
                    if payload[i] == 0:
                        nulls.append(i)
                if len(nulls) < 3:
                    serial.send_nak(ERR_INVALID_PAYLOAD)
                    continue
                username = payload[nulls[0] + 1 : nulls[1]].decode(
                    "utf-8", errors="replace"
                )
                password = payload[nulls[1] + 1 : nulls[2]].decode(
                    "utf-8", errors="replace"
                )
                state = INJECTING
                led.set_mode(LEDController.INJECTING)
                hid.type_credentials(username, password)
                state = READY
                led.set_mode(LEDController.READY)
                serial.send_ack(CMD_INJECT)
            except Exception:
                state = READY if vault.vault_exists() else RECEIVING_VAULT
                led.set_mode(
                    LEDController.READY
                    if state == READY
                    else LEDController.CONNECTED
                )
                serial.send_nak(ERR_INJECTION_FAILED)

        elif cmd == CMD_SET_KEY:
            if len(payload) == 32:
                device_key = bytearray(payload)
                serial.send_ack(CMD_SET_KEY)
            else:
                serial.send_nak(ERR_INVALID_PAYLOAD)

        elif cmd == CMD_INJECT_ENC:
            if device_key is None:
                serial.send_nak(ERR_INVALID_PAYLOAD)
                continue
            if len(payload) < 33:
                serial.send_nak(ERR_INVALID_PAYLOAD)
                continue
            mac_tag = payload[-4:]
            payload_body = payload[:-4]
            expected_mac = aes_mac(bytes(device_key), payload_body)
            if expected_mac is None or mac_tag != expected_mac:
                serial.send_nak(ERR_INVALID_PAYLOAD)
                continue
            nonce = payload_body[:12]
            tag = payload_body[-16:]
            ciphertext = payload_body[12:-16]
            plaintext = aes_gcm_decrypt(bytes(device_key), nonce, ciphertext, tag)
            if plaintext is None:
                serial.send_nak(ERR_INVALID_PAYLOAD)
                continue
            nulls = []
            for i in range(len(plaintext)):
                if plaintext[i] == 0:
                    nulls.append(i)
            if len(nulls) < 2:
                serial.send_nak(ERR_INVALID_PAYLOAD)
                continue
            username = plaintext[: nulls[0]].decode("utf-8", errors="replace")
            password = plaintext[nulls[0] + 1 : nulls[1]].decode(
                "utf-8", errors="replace"
            )
            state = INJECTING
            led.set_mode(LEDController.INJECTING)
            hid.type_credentials(username, password)
            state = READY
            led.set_mode(LEDController.READY)
            serial.send_ack(CMD_INJECT_ENC)

        elif cmd == CMD_LOCK:
            device_key = None
            state = RECEIVING_VAULT
            led.set_mode(LEDController.CONNECTED)
            serial.send_ack(CMD_LOCK)

        elif cmd == CMD_WIPE:
            device_key = None
            vault.erase_vault()
            state = RECEIVING_VAULT
            led.set_mode(LEDController.CONNECTED)
            serial.send_ack(CMD_WIPE)

        else:
            serial.send_nak(ERR_UNKNOWN_CMD)
            led.set_mode(LEDController.ERROR)
            error_cooldown = time.monotonic() + 1.8

        time.sleep(0.001)


main()
