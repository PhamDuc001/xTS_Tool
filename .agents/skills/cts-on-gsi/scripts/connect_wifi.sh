#!/usr/bin/env bash
# ==============================================================================
# Script: connect_wifi.sh
# Mục đích: Tự động kết nối Wi-Fi cho bản GSI qua adbjoinwifi và kiểm tra mạng.
# Sử dụng: ./connect_wifi.sh <device_serial> [SSID] [PASSWORD]
# ==============================================================================

set -e

SERIAL="$1"
SSID="${2:-LGE_Auto_Test}"
PASS="${3:-lge12345}"

if [ -z "$SERIAL" ]; then
    echo "❌ Lỗi: Vui lòng cung cấp Serial Number của thiết bị."
    echo "Ví dụ: ./connect_wifi.sh cf8886c9 [SSID] [PASSWORD]"
    exit 1
fi

echo "📶 [Wi-Fi] Đang kết nối mạng Wi-Fi '$SSID' cho thiết bị: $SERIAL ..."

# 1. Bật giao diện Wi-Fi
adb -s "$SERIAL" shell svc wifi enable
sleep 2

# 2. Gửi lệnh kết nối qua adbjoinwifi nếu có
adb -s "$SERIAL" shell am start -n com.steinwurf.adbjoinwifi/.MainActivity \
    -e ssid "$SSID" \
    -e password_type WPA \
    -e password "$PASS" 2>/dev/null || true

sleep 5

# 3. Kiểm tra địa chỉ IP và kết nối Internet
IP=$(adb -s "$SERIAL" shell ip route | awk '/src/ {print $NF}' | head -n 1)
echo "  -> IP thiết bị nhận được: ${IP:-Chưa có IP}"

echo "  -> Kiểm tra ping tới 8.8.8.8..."
if adb -s "$SERIAL" shell ping -c 3 8.8.8.8 >/dev/null 2>&1; then
    echo "✅ [Wi-Fi] Kết nối Internet thành công!"
else
    echo "⚠️ [Wi-Fi] Cảnh báo: Thiết bị chưa ping được ra Internet. Vui lòng kiểm tra Access Point."
fi
