#!/usr/bin/env python

import asyncio
import subprocess
from astral.geocoder import database, lookup
from astral.sun import sun
from bleak import BleakClient
from datetime import datetime, timezone

address = "C6:70:45:7F:CB:F0"
CONSMART_BLE_NOTIFICATION_SERVICE_WRGB_UUID = "0000ffd5-0000-1000-8000-00805f9b34fb"
CONSMART_BLE_NOTIFICATION_CHARACTERISTICS_WRGB_UUID = "0000ffd9-0000-1000-8000-00805f9b34fb"

SRCAES = [-5, 2, 5, 5, 16, 8, 35, 1, 2, 0, 5, 85, 34, 1, 18, 19, 20, -6]
TRIONES_SRCAES = SRCAES
TRIONES_SRCAES[0] = -5
TRIONES_SRCAES[17] = -6
TRIONES_SRCAES_UNSIGNED = bytearray([x % 256 for x in TRIONES_SRCAES])

city = lookup("Tallinn", database())


def create_wrgb_command(red: int, green: int, blue: int) -> bytearray:
    warmwhite = 0
    color_cmd = [86, red & 0xff, green & 0xff,
                 blue & 0xff, warmwhite & 0xff, -16, -86]

    return bytearray([x % 256 for x in color_cmd])


BRIGHTNESS_DAY = 0
BRIGHTNESS_DUSK = 127
BRIGHTNESS_NIGHT = 255


def get_brightness() -> int:
    time = datetime.now(timezone.utc)
    sun_times = sun(city.observer, date=datetime.now())

    if (time < sun_times['dawn']):
        print("Night before dawn")
        return BRIGHTNESS_NIGHT
    elif (sun_times['dawn'] < time < sun_times['sunrise']):
        print("Morning between dawn and sunrise")
        return BRIGHTNESS_DUSK
    elif (sun_times['sunrise'] < time < sun_times['sunset']):
        print("Day between sunrise and sunset")
        return BRIGHTNESS_DAY
    elif (sun_times['sunset'] < time < sun_times['dusk']):
        print("Evening between sunset and dusk")
        return BRIGHTNESS_DUSK
    elif (sun_times['dusk'] < time):
        print("Night after dusk")
        return BRIGHTNESS_NIGHT

    print(f"Should never reach here, time {time}")
    return BRIGHTNESS_DAY


async def prepare_aes(client: BleakClient):
    for _ in range(5):
        print("Writing srcaes")
        await client.write_gatt_char(CONSMART_BLE_NOTIFICATION_CHARACTERISTICS_WRGB_UUID, TRIONES_SRCAES_UNSIGNED)
        await asyncio.sleep(1)


async def write_brightness(client: BleakClient, brightness: int):
    cmd = create_wrgb_command(brightness, 0, 0)
    await client.write_gatt_char(CONSMART_BLE_NOTIFICATION_CHARACTERISTICS_WRGB_UUID, cmd)


async def connect(client: BleakClient):
    print(f"Connecting to device {client.address}")
    await client.connect()
    if (client.is_connected):
        await prepare_aes(client)


def disconnected_callback(_: BleakClient):
    print("Device was disconnected.")


client = BleakClient(address, disconnected_callback=disconnected_callback)


async def main():
    try:
        current_brightness = -1
        while True:
            if (not client.is_connected):
                try:
                    await connect(client)
                except Exception as e:
                    print(f"Failed to connect: {e}")
                    await asyncio.sleep(5)
                    continue

            print("Main loop")
            brightness = get_brightness()

            if (brightness != current_brightness):
                print("Writing new brightness")
                await write_brightness(client, brightness)
                current_brightness = brightness

            await asyncio.sleep(60)
    except Exception as e:
        print(e)
    finally:
        await client.disconnect()

try:
    subprocess.call(['bluetoothctl', 'disconnect', address], timeout=10)
except:
    print("Failed to disconnect")

asyncio.run(main())
