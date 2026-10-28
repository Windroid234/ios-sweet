#!/usr/bin/env python3
import sys, time
import usb.core, usb.util

def get_device():
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
    return dev, ep_in, ep_out

def send_cmd(cmd_str):
    dev, ep_in, ep_out = get_device()
    print(f"Sending: {cmd_str}")
    ep_out.write(cmd_str.encode())
    try:
        resp = ep_in.read(64, timeout=3000)
        resp_str = bytes(resp).decode(errors='replace')
        print(f"Response: {resp_str}")
        return resp_str
    except Exception as e:
        print(f"Error/Timeout reading response: {e}")
        return None

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: fb_cmd.py <command>")
        sys.exit(1)
    send_cmd(sys.argv[1])
