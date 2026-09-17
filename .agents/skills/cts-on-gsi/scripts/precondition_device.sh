#!/usr/bin/env bash
# ==============================================================================
# Script: precondition_device.sh
# Mục đích: Thiết lập trạng thái thiết bị (Pre-conditions) trước khi chạy/retry CTS on GSI.
# Sử dụng: ./precondition_device.sh <device_serial>
# ==============================================================================

set -e

SERIAL="$1"

if [ -z "$SERIAL" ]; then
    echo "❌ Lỗi: Vui lòng cung cấp Serial Number của thiết bị."
    echo "Ví dụ: ./precondition_device.sh cf8886c9"
    exit 1
fi

echo "🚀 [Pre-condition] Đang cấu hình thiết bị: $SERIAL ..."

# 1. Đảm bảo ADB kết nối root
adb -s "$SERIAL" root 2>/dev/null || true
sleep 1

# 2. Bật màn hình và giữ sáng liên tục (Stay Awake khi cắm USB/AC)
echo "  -> Thiết lập màn hình luôn sáng (Stay Awake)..."
adb -s "$SERIAL" shell settings put global stay_on_while_plugged_in 7
adb -s "$SERIAL" shell svc power stayon true
adb -s "$SERIAL" shell input keyevent 224

# 3. Tắt màn hình khóa (Lockscreen & Keyguard)
echo "  -> Gỡ bỏ màn hình khóa (Dismiss Keyguard)..."
adb -s "$SERIAL" shell settings put secure lock_screen_lock_none true 2>/dev/null || true
adb -s "$SERIAL" shell wm dismiss-keyguard

# 4. Reset kích thước và mật độ màn hình về mặc định
echo "  -> Đặt lại kích thước hiển thị và DPI về mặc định..."
adb -s "$SERIAL" shell wm size reset
adb -s "$SERIAL" shell wm density reset

# 5. Cấu hình ngôn ngữ chuẩn tiếng Anh Mỹ (en-US)
echo "  -> Đặt ngôn ngữ hệ thống: en-US..."
adb -s "$SERIAL" shell 'setprop persist.sys.locale en-US' 2>/dev/null || true

# 6. Dọn dẹp bộ đệm statsd (Tránh lỗi CtsStatsdAtomHostTestCases)
echo "  -> Dọn bộ đệm Statsd..."
adb -s "$SERIAL" shell cmd statsd data-wipe 2>/dev/null || true

# 7. Nhấn phím HOME để dọn dẹp các app treo
echo "  -> Trở về màn hình Home..."
adb -s "$SERIAL" shell input keyevent 3

echo "✅ [Pre-condition] Thiết bị $SERIAL đã sẵn sàng chạy CTS on GSI!"
