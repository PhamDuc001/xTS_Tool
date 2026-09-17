#!/usr/bin/env python3
# ==============================================================================
# Script: control_relay_pcb.py
# Mục đích: Điều khiển nguồn rơ-le Arduino cho 3 DUTs (22324141, 70b1036, 5a9ba6a2)
# Sử dụng: python3 control_relay_pcb.py <R1|R1off|R2|R2off|R3|R3off|cycle1|cycle2|cycle3|cycle_all>
# ==============================================================================

import sys
import time

try:
    import serial
except ImportError:
    print("❌ Lỗi: Vui lòng cài đặt pyserial (pip install pyserial)")
    sys.exit(1)

ARDUINO_PORT = "/dev/arduino"
BAUD_RATE = 9600

def send_signal(sig):
    print(f"🔌 [Relay PCB] Gửi tín hiệu: {sig} tới {ARDUINO_PORT}...")
    try:
        ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=2)
        ser.write(bytes(sig, 'ascii'))
        ser.close()
        print(f"✅ [Relay PCB] Đã gửi thành công tín hiệu: {sig}")
    except Exception as e:
        print(f"❌ [Relay PCB] Lỗi kết nối cổng {ARDUINO_PORT}: {e}")

def cycle_relay(port_num, sleep_sec=10):
    off_sig = f"R{port_num}off"
    on_sig = f"R{port_num}"
    print(f"🔄 [Relay PCB] Thực hiện chu kỳ khởi động lại Relay {port_num} (Nghỉ {sleep_sec}s)...")
    send_signal(off_sig)
    time.sleep(sleep_sec)
    send_signal(on_sig)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Sử dụng:")
        print("  python3 control_relay_pcb.py <R1|R1off|R2|R2off|R3|R3off>")
        print("  python3 control_relay_pcb.py <cycle1|cycle2|cycle3|cycle_all>")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "cycle1":
        cycle_relay(1)
    elif cmd == "cycle2":
        cycle_relay(2)
    elif cmd == "cycle3":
        cycle_relay(3)
    elif cmd == "cycle_all":
        cycle_relay(1, 10)
        cycle_relay(2, 10)
        cycle_relay(3, 10)
    else:
        send_signal(sys.argv[1])
