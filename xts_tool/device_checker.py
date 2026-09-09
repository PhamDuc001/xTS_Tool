"""
Device Checker Utility
Parses adb and fastboot outputs to determine connected devices and state.
"""
import re
from typing import List, Dict, Tuple


class DeviceInfo:
    def __init__(self, serial: str, mode: str, state: str = "ok"):
        self.serial = serial
        self.mode = mode  # 'adb', 'fastboot', 'fastbootd', 'recovery', 'unauthorized'
        self.state = state

    def __repr__(self):
        return f"<Device {self.serial} ({self.mode})>"


def parse_adb_devices(output: str) -> List[DeviceInfo]:
    """
    Parses output of 'adb devices -l' or 'adb devices'.
    Example lines:
    List of devices attached
    ABC1234567\tdevice product:...
    DEF9876543\tunauthorized
    """
    devices = []
    lines = output.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("*") or line.startswith("List of devices"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            serial = parts[0]
            status = parts[1]
            mode = "adb"
            if status == "recovery":
                mode = "recovery"
            elif status == "unauthorized":
                mode = "unauthorized"
            elif status == "offline":
                mode = "offline"
            devices.append(DeviceInfo(serial=serial, mode=mode, state=status))
    return devices


def parse_fastboot_devices(output: str) -> List[DeviceInfo]:
    """
    Parses output of 'fastboot devices'.
    Example lines:
    ABC1234567\tfastboot
    """
    devices = []
    lines = output.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "fastboot":
            devices.append(DeviceInfo(serial=parts[0], mode="fastboot", state="fastboot"))
    return devices


def evaluate_device_connection(adb_out: str, fastboot_out: str) -> Tuple[bool, str, List[DeviceInfo]]:
    """
    Evaluates whether exactly ONE device is connected (either adb or fastboot).
    Returns (is_valid_single_device, message, device_list).
    """
    adb_devs = parse_adb_devices(adb_out)
    fb_devs = parse_fastboot_devices(fastboot_out)
    
    all_devs = []
    seen_serials = set()
    for d in adb_devs + fb_devs:
        if d.serial not in seen_serials:
            all_devs.append(d)
            seen_serials.add(d.serial)

    count = len(all_devs)
    if count == 0:
        return False, "Không phát hiện thiết bị nào (0 device). Vui lòng kết nối 1 thiết bị!", []
    elif count == 1:
        dev = all_devs[0]
        if dev.state == "unauthorized":
            return False, f"Thiết bị {dev.serial} chưa được cấp quyền (unauthorized). Vui lòng kiểm tra màn hình thiết bị!", all_devs
        return True, f"Phát hiện 1 thiết bị hợp lệ: {dev.serial} ({dev.mode})", all_devs
    else:
        serials_str = ", ".join([f"{d.serial} [{d.mode}]" for d in all_devs])
        return False, f"CẢNH BÁO: Phát hiện {count} thiết bị ({serials_str}). Vui lòng chỉ kết nối DUY NHẤT 1 thiết bị!", all_devs
