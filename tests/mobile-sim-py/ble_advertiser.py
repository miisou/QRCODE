import argparse
import asyncio
import sys
import uuid

from winsdk.windows.devices.bluetooth import BluetoothError, BluetoothAdapter
from winsdk.windows.devices.bluetooth.advertisement import (
    BluetoothLEAdvertisement,
    BluetoothLEAdvertisementPublisher,
    BluetoothLEAdvertisementPublisherStatus,
    BluetoothLEAdvertisementDataSection,
    BluetoothLEAdvertisementFlags,
)
from winsdk.windows.storage.streams import DataWriter


def parse_args():
    parser = argparse.ArgumentParser(
        description="Simulate Android BLE advertiser on Windows: advertise a service UUID"
    )
    parser.add_argument("uuid", help="BLE service UUID to advertise (e.g. 12345678-1234-1234-1234-1234567890ab)")
    parser.add_argument(
        "--seconds",
        type=int,
        default=0,
        help="Stop after N seconds (default: 0 = run until Ctrl+C)",
    )
    return parser.parse_args()


async def main():
    args = parse_args()

    try:
        service_uuid = uuid.UUID(args.uuid)
    except Exception:
        print("ERROR: invalid UUID format", file=sys.stderr)
        return 2

    # Pre-check adapter capabilities
    try:
        adapter = await BluetoothAdapter.get_default_async()
    except Exception:
        adapter = None
    if adapter is None:
        print("ERROR: Bluetooth adapter not found or unavailable")
        return 4
    try:
        if hasattr(adapter, "is_peripheral_role_supported") and not adapter.is_peripheral_role_supported:
            print("ERROR: This Bluetooth adapter does not support BLE Peripheral (advertising) on Windows")
            return 4
    except Exception:
        # Continue if property not available
        pass

    adv = BluetoothLEAdvertisement()
    adv.flags = BluetoothLEAdvertisementFlags.GENERAL_DISCOVERABLE_MODE
    # Try primary method: declare service UUID in advertisement.ServiceUuids
    adv.service_uuids.append(service_uuid)
    publisher = BluetoothLEAdvertisementPublisher(adv)

    def on_status_changed(sender, event_args):
        status = event_args.status
        error = getattr(event_args, "error", None)
        if error is None or error == BluetoothError.SUCCESS:
            print(f"Status: {BluetoothLEAdvertisementPublisherStatus(status).name}")
        else:
            print(
                f"Status: {BluetoothLEAdvertisementPublisherStatus(status).name}, "
                f"Error: {BluetoothError(error).name}"
            )

    token = publisher.add_status_changed(on_status_changed)

    print(f"Advertising BLE service UUID: {args.uuid}")
    try:
        publisher.start()
    except OSError as e:
        # Fallback: build a 0x07 (Complete List of 128-bit Service UUIDs) data section manually
        if getattr(e, "winerror", None) == -2147024809:  # E_INVALIDARG
            try:
                # Reset and use data section
                try:
                    publisher.stop()
                except Exception:
                    pass
                adv.service_uuids.clear()
                writer = DataWriter()
                # BLE advert expects little-endian UUID bytes
                writer.write_bytes(service_uuid.bytes_le)
                buf = writer.detach_buffer()
                section = BluetoothLEAdvertisementDataSection(0x07, buf)
                adv.data_sections.append(section)
                publisher = BluetoothLEAdvertisementPublisher(adv)
                print("Primary advertise path failed, retrying with raw data section (0x07)...")
                publisher.start()
            except Exception as e2:
                print(f"Failed to start advertising: {e2}")
                return 3
        else:
            print(f"Failed to start advertising: {e}")
            return 3

    try:
        if args.seconds and args.seconds > 0:
            await asyncio.sleep(args.seconds)
        else:
            # Wait until Ctrl+C
            while True:
                await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            publisher.stop()
        except Exception:
            pass
        try:
            publisher.remove_status_changed(token)
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            exit_code = loop.run_until_complete(main())
        finally:
            loop.close()
    sys.exit(exit_code)


