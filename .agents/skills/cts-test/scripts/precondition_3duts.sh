#!/usr/bin/env bash
# ==============================================================================
# Script: precondition_3duts.sh
# Mục đích: Thiết lập pre-conditions cho cả 3 thiết bị CTS (22324141, 70b1036, 5a9ba6a2)
# ==============================================================================

set -e

DUT_LIST=("22324141" "70b1036" "5a9ba6a2")

# Nếu người dùng truyền serial qua tham số, chỉ cấu hình serial đó
if [ -n "$1" ]; then
    DUT_LIST=("$1")
fi

echo "🚀 [Pre-conditions] Bắt đầu thiết lập trạng thái cho danh sách thiết bị: ${DUT_LIST[*]}"

for SERIAL in "${DUT_LIST[@]}"; do
    echo "--------------------------------------------------------"
    echo "📱 Cấu hình thiết bị: $SERIAL"
    
    # Kiểm tra thiết bị có online trong ADB không
    if ! adb devices | grep -q "$SERIAL"; then
        echo "⚠️ Cảnh báo: Thiết bị $SERIAL không có trong adb devices. Bỏ qua."
        continue
    fi

    # 1. Root & Remount
    adb -s "$SERIAL" root 2>/dev/null || true
    sleep 1

    # 2. Stay Awake khi cắm sạc
    echo "  -> Thiết lập màn hình luôn sáng (Stay Awake)..."
    adb -s "$SERIAL" shell settings put global stay_on_while_plugged_in 7
    adb -s "$SERIAL" shell svc power stayon true
    adb -s "$SERIAL" shell input keyevent 224

    # 3. Gỡ bỏ màn hình khóa (Dismiss Keyguard)
    echo "  -> Tắt khóa màn hình..."
    adb -s "$SERIAL" shell settings put secure lock_screen_lock_none true 2>/dev/null || true
    adb -s "$SERIAL" shell wm dismiss-keyguard

    # 4. Reset kích thước màn hình & DPI
    echo "  -> Reset độ phân giải hiển thị về mặc định..."
    adb -s "$SERIAL" shell wm size reset
    adb -s "$SERIAL" shell wm density reset

    # 5. Cấu hình ngôn ngữ chuẩn
    echo "  -> Đặt ngôn ngữ en-US..."
    adb -s "$SERIAL" shell 'setprop persist.sys.locale en-US' 2>/dev/null || true

    # 6. Dọn dẹp bộ đệm statsd
    echo "  -> Xóa bộ nhớ đệm Statsd..."
    adb -s "$SERIAL" shell cmd statsd data-wipe 2>/dev/null || true

    # 7. Trở về Home Screen
    echo "  -> Về màn hình chính..."
    adb -s "$SERIAL" shell input keyevent 3

    echo "✅ Thiết bị $SERIAL đã sẵn sàng kiểm thử CTS!"
done

echo "========================================================"
echo "🎉 Tất cả thiết bị đã được cấu hình xong pre-conditions."
