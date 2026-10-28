#!/usr/bin/env python3
"""Device monitor and automation tool for Nothing Phone (2) (pong) HackiOS bring-up.

Monitors USB for:
  - 18d1:d00d: Fastboot mode
  - 18d1:4ee7: Recovery mode (OrangeFox)
  - 1209:0001: HackiOS USB gadget

Can automatically flash new kernels on Fastboot, pull persistent logs and
continuous splash framebuffer from Recovery.
"""
import os, sys, time, subprocess
import usb.core, usb.util

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(REPO_ROOT, "logs")
ARTIFACTS_DIR = os.path.join(REPO_ROOT, "artifacts")
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

def check_devices():
    devs = {}
    for dev in usb.core.find(find_all=True):
        vid_pid = (dev.idVendor, dev.idProduct)
        if vid_pid == (0x18d1, 0xd00d):
            devs['fastboot'] = dev
        elif vid_pid == (0x18d1, 0x4ee7):
            devs['recovery'] = dev
        elif vid_pid == (0x1209, 0x0001):
            devs['hackios'] = dev
    return devs

def pull_recovery_artifacts():
    print("[*] Pulling recovery artifacts...")
    ts = time.strftime("%Y%m%d-%H%M%S")
    log_out = os.path.join(LOGS_DIR, f"boot-log-{ts}.txt")
    raw_fb = os.path.join(ARTIFACTS_DIR, f"rawfb-{ts}.bin")
    png_fb = os.path.join(ARTIFACTS_DIR, f"framebuffer-{ts}.png")
    latest_png = os.path.join(ARTIFACTS_DIR, "lockscreen.png")

    # 1. Pull persistent log from userdata
    pull_script = os.path.join(REPO_ROOT, "tools/sweet-log-pull.sh")
    cmd = [pull_script, log_out]
    print(f"[*] Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode == 0:
        print(f"[✓] Persistent log successfully pulled to {log_out}")
    else:
        print(f"[-] Log pull error: {res.stderr}")

    # 2. Dump continuous splash framebuffer memory at 0xb8000000 (1080x2412 BGRA, 10,419,840 bytes)
    fb_base = 0xb8000000
    fb_size = 1080 * 2412 * 4  # 10419840 bytes
    blocks = (fb_size + 4095) // 4096
    skip = fb_base // 4096
    print(f"[*] Dumping framebuffer at 0x{fb_base:x} ({blocks} 4K blocks)...")
    dd_cmd = f"dd if=/dev/mem bs=4096 skip={skip} count={blocks} 2>/dev/null"
    dump_res = subprocess.run(["adb", "exec-out", dd_cmd], stdout=open(raw_fb, "wb"))
    if os.path.exists(raw_fb) and os.path.getsize(raw_fb) >= fb_size:
        print(f"[✓] Dumped raw framebuffer ({os.path.getsize(raw_fb)} bytes) to {raw_fb}")
        # Convert to PNG
        conv_script = os.path.join(REPO_ROOT, "tools/rawfb_to_png.py")
        subprocess.run(["python3", conv_script, raw_fb, png_fb, "1080", "2412", "BGRA"])
        subprocess.run(["python3", conv_script, raw_fb, latest_png, "1080", "2412", "BGRA"])
        print(f"[✓] Framebuffer converted to {png_fb} and {latest_png}")
    else:
        print(f"[-] Framebuffer dump failed or incomplete: {raw_fb}")

def monitor_loop(auto_flash_img=None, reboot_to_recovery=False):
    print("[*] Starting pong device monitor loop...")
    if auto_flash_img:
        print(f"[*] Auto-flash image configured: {auto_flash_img}")
    last_state = None

    while True:
        devs = check_devices()
        state = list(devs.keys())
        if state != last_state:
            print(f"[{time.strftime('%H:%M:%S')}] Detected device states: {state or 'none'}")
            last_state = state

        if 'recovery' in devs:
            print(f"[!] Device in Recovery mode! Pulling artifacts...")
            pull_recovery_artifacts()
            time.sleep(5)

        elif 'fastboot' in devs:
            print(f"[!] Device in Fastboot mode!")
            if auto_flash_img and os.path.exists(auto_flash_img):
                print(f"[*] Auto-flashing {auto_flash_img} to boot_a...")
                flash_script = os.path.join(REPO_ROOT, "tools/pong_flash.py")
                res = subprocess.run(["python3", flash_script, "boot_a", auto_flash_img])
                if res.returncode == 0:
                    print("[✓] Flashed successfully!")
                    if reboot_to_recovery:
                        print("[*] Rebooting to recovery to capture logs...")
                        fb_cmd = os.path.join(REPO_ROOT, "tools/fb_cmd.py")
                        subprocess.run(["python3", fb_cmd, "reboot-recovery"])
                    else:
                        print("[*] Rebooting phone...")
                        fb_cmd = os.path.join(REPO_ROOT, "tools/fb_cmd.py")
                        subprocess.run(["python3", fb_cmd, "reboot"])
                    time.sleep(5)
            else:
                time.sleep(2)

        time.sleep(1)

if __name__ == '__main__':
    img = sys.argv[1] if len(sys.argv) > 1 else None
    monitor_loop(img)
