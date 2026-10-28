#!/usr/bin/env python3
import sys, time
import usb.core, usb.util

def flash(partition, file_path):
    dev = usb.core.find(idVendor=0x18d1, idProduct=0xd00d)
    if not dev:
        print("Fastboot device not found.")
        sys.exit(1)

    cfg = dev.get_active_configuration()
    intf = cfg[(0, 0)]
    ep_out = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
    ep_in = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)

    dev.clear_halt(ep_in)
    dev.clear_halt(ep_out)

    with open(file_path, 'rb') as f:
        data = f.read()

    sz = len(data)
    cmd = f'download:{sz:08x}'
    print(f'Sending download command: {cmd}')
    ep_out.write(cmd.encode())

    resp = ep_in.read(64, timeout=3000)
    resp_str = bytes(resp).decode(errors='replace')
    print(f'Download response: {resp_str}')
    if not resp_str.startswith('DATA'):
        print(f'Error starting download: {resp_str}')
        sys.exit(1)

    print(f'Streaming {sz} bytes ({sz / (1024*1024):.2f} MB)...')
    CHUNK = 1024 * 1024
    off = 0
    t0 = time.time()
    while off < sz:
        chunk = data[off:off+CHUNK]
        ep_out.write(chunk)
        off += len(chunk)
    elapsed = time.time() - t0
    print(f'Streamed in {elapsed:.2f}s ({sz / elapsed / (1024*1024):.2f} MB/s)')

    resp = ep_in.read(64, timeout=5000)
    print(f'Download status: {bytes(resp).decode(errors="replace")}')

    flash_cmd = f'flash:{partition}'
    print(f'Sending flash command: {flash_cmd}')
    ep_out.write(flash_cmd.encode())

    t0 = time.time()
    while True:
        try:
            resp = ep_in.read(64, timeout=5000)
            resp_str = bytes(resp).decode(errors='replace')
            print(f'Flash response [{time.time() - t0:.1f}s]: {resp_str}')
            if resp_str.startswith('OKAY'):
                print(f'Successfully flashed {partition}!')
                break
            elif resp_str.startswith('FAIL'):
                print(f'Flashing failed: {resp_str}')
                sys.exit(1)
        except usb.core.USBTimeoutError:
            print(f'Waiting for flash... [{time.time() - t0:.1f}s]')

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: pong_flash.py <partition> <file_path>")
        sys.exit(1)
    flash(sys.argv[1], sys.argv[2])
