@echo off
chcp 65001 >nul
:: ==============================================================================
:: Script: setup_pz1d.bat (Windows)
:: Tự động cấu hình Nissan Head Unit (PZ1D) từ máy tính Windows qua ADB
:: Hoàn toàn KHÔNG LƯU LẠI BẤT KỲ FILE NÀO TRÊN HU (Zero Footprint)
:: ==============================================================================

set "SERIAL=%~1"
set "WIFI_SSID=%~2"
if "%WIFI_SSID%"=="" set "WIFI_SSID=GG"
set "WIFI_PASS=%~3"
if "%WIFI_PASS%"=="" set "WIFI_PASS=11111112"
set "LOCALE=%~4"
if "%LOCALE%"=="" set "LOCALE=en-US"

set "SCRIPT_DIR=%~dp0"
set "JAR_PATH=%SCRIPT_DIR%setlocale.jar"

echo 🚀 [Setup PZ1D - Windows] Đang khởi động cấu hình thiết bị...

:: Nếu không truyền serial, tự tìm serial đầu tiên
if "%SERIAL%"=="" (
    for /f "skip=1 tokens=1" %%i in ('adb devices') do (
        if not "%%i"=="" if not "%%i"=="List" (
            set "SERIAL=%%i"
            goto :found_serial
        )
    )
)

:found_serial
if "%SERIAL%"=="" (
    echo ❌ Không tìm thấy thiết bị nào kết nối qua ADB!
    echo Vui lòng cắm cáp USB hoặc kết nối adb connect.
    pause
    exit /b 1
)

echo 📱 Thiết bị mục tiêu: %SERIAL%
echo 📶 Wi-Fi: %WIFI_SSID% ^| 🌐 Ngôn ngữ: %LOCALE% ^| ⏰ Giờ: 12h ^| 🔵 Bluetooth: ON

:: 0. ADB Root nếu có thể
adb -s %SERIAL% root >nul 2>&1
timeout /t 1 /nobreak >nul

:: 1. Bật Wi-Fi và kết nối mạng Native (Không cần cài bất kỳ App/File nào)
echo   [1/5] Bật Wi-Fi ^& kết nối '%WIFI_SSID%'...
adb -s %SERIAL% shell svc wifi enable
adb -s %SERIAL% shell cmd -w wifi connect-network "%WIFI_SSID%" wpa2 "%WIFI_PASS%" >nul 2>&1

:: 2. Đổi ngôn ngữ hệ thống thời gian thực qua setlocale.jar và XÓA NGAY LẬP TỨC
echo   [2/5] Cấu hình ngôn ngữ hệ thống sang %LOCALE% (Zero Footprint)...
if exist "%JAR_PATH%" (
    adb -s %SERIAL% push "%JAR_PATH%" /data/local/tmp/setlocale.jar >nul 2>&1
    adb -s %SERIAL% shell "CLASSPATH=/data/local/tmp/setlocale.jar app_process /data/local/tmp com.setlocale.SetLocale %LOCALE%"
    adb -s %SERIAL% shell rm -f /data/local/tmp/setlocale.jar >nul 2>&1
)
adb -s %SERIAL% shell setprop persist.sys.locale %LOCALE%
adb -s %SERIAL% shell settings put system system_locales %LOCALE%

:: 3. Đặt định dạng giờ 12h & tự động cập nhật
echo   [3/5] Đặt định dạng thời gian 12h...
adb -s %SERIAL% shell settings put system time_12_24 12
adb -s %SERIAL% shell settings put global auto_time 1
adb -s %SERIAL% shell settings put global auto_time_zone 1

:: 4. Bật Bluetooth
echo   [4/5] Kích hoạt Bluetooth...
adb -s %SERIAL% shell svc bluetooth enable
adb -s %SERIAL% shell settings put global bluetooth_on 1

:: 5. Giữ màn hình luôn sáng & tắt màn hình khóa (Stay Awake)
echo   [5/5] Cấu hình màn hình luôn sáng ^& mở khóa...
adb -s %SERIAL% shell settings put global stay_on_while_plugged_in 7
adb -s %SERIAL% shell svc power stayon true
adb -s %SERIAL% shell settings put secure lock_screen_lock_none true
adb -s %SERIAL% shell wm dismiss-keyguard
adb -s %SERIAL% shell input keyevent 224
adb -s %SERIAL% shell input keyevent 3

echo ========================================================
echo ✅ CẤU HÌNH THÀNH CÔNG! TRÊN THIẾT BỊ HOÀN TOÀN KHÔNG LƯU FILE RÁC.
echo • Định dạng giờ: 12h
echo • Bluetooth:     Bật
echo • Trạng thái:    Sẵn sàng kiểm thử CTS
