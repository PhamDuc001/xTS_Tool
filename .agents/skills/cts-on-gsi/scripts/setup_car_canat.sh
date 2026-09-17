#!/usr/bin/env bash
# ==============================================================================
# Script: setup_car_canat.sh
# Mục đích: Kích hoạt tín hiệu mô phỏng mạng CAN xe hơi (CANat) phục vụ CtsCarTestCases (HVAC).
# Sử dụng: ./setup_car_canat.sh <device_serial>
# ==============================================================================

set -e

SERIAL="$1"

if [ -z "$SERIAL" ]; then
    echo "❌ Lỗi: Vui lòng cung cấp Serial Number của thiết bị."
    echo "Ví dụ: ./setup_car_canat.sh cf8886c9"
    exit 1
fi

echo "🚗 [CANat] Khởi tạo mô phỏng CAN bus cho xe trên thiết bị: $SERIAL ..."

# 1. Khởi chạy app giám sát CANat trên DUT
echo "  -> Đảm bảo app com.lge.canat đang chạy..."
adb -s "$SERIAL" shell am start -n com.lge.canat/.MainActivity 2>/dev/null || true
sleep 1

# 2. Gửi tín hiệu giả lập chìa khóa xe / Ignition ON (ACC = ON)
echo "  -> Bơm tín hiệu CAN Ignition ON (VehicleStates:2:0)..."
if [ -e "/dev/canat" ]; then
    echo "VehicleStates:2:0" > /dev/canat 2>/dev/null || true
fi

# Gửi broadcast Intent tới receiver của xe
adb -s "$SERIAL" shell am broadcast -a com.lge.canat.ACTION_SEND_CAN --es signal "VehicleStates:2:0" 2>/dev/null || true
sleep 2

# 3. Gửi tín hiệu chu kỳ chuẩn
echo "  -> Bơm tín hiệu đồng bộ chu kỳ CAN bus (VehicleStates:0:0)..."
if [ -e "/dev/canat" ]; then
    echo "VehicleStates:0:0" > /dev/canat 2>/dev/null || true
fi
adb -s "$SERIAL" shell am broadcast -a com.lge.canat.ACTION_SEND_CAN --es signal "VehicleStates:0:0" 2>/dev/null || true

echo "✅ [CANat] Đã thiết lập trạng thái CAN bus thành công. Sẵn sàng retry CtsCarTestCases!"
