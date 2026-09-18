# ==============================================================================
# Script: setup_pz1d.ps1 (PowerShell)
# Tự động cấu hình Nissan Head Unit (PZ1D) từ máy tính Windows qua ADB
# Hoàn toàn KHÔNG LƯU LẠI BẤT KỲ FILE NÀO TRÊN HU (Zero Footprint)
# ==============================================================================

param (
    [string]$Serial = "",
    [string]$WifiSsid = "GG",
    [string]$WifiPass = "11111112",
    [string]$Locale = "en-US"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$JarPath = Join-Path $ScriptDir "setlocale.jar"

Write-Host "🚀 [Setup PZ1D - PowerShell] Đang khởi động cấu hình thiết bị..." -ForegroundColor Cyan

# Nếu không truyền Serial, tự động lấy thiết bị đầu tiên
if ([string]::IsNullOrWhiteSpace($Serial)) {
    $devices = (adb devices) | Where-Object { $_ -match "\bdevice\b" -and $_ -notmatch "List of" }
    if ($devices) {
        $Serial = ($devices[0] -split "\s+")[0]
    }
}

if ([string]::IsNullOrWhiteSpace($Serial)) {
    Write-Host "❌ Không tìm thấy thiết bị nào kết nối qua ADB!" -ForegroundColor Red
    Write-Host "Vui lòng cắm cáp USB hoặc chạy lệnh adb connect." -ForegroundColor Yellow
    exit 1
}

Write-Host "📱 Thiết bị mục tiêu: $Serial" -ForegroundColor Green
Write-Host "📶 Wi-Fi: $WifiSsid | 🌐 Ngôn ngữ: $Locale | ⏰ Giờ: 12h | 🔵 Bluetooth: ON`n" -ForegroundColor DarkGray

# 0. ADB Root nếu có thể
adb -s $Serial root | Out-Null
Start-Sleep -Seconds 1

# 1. Bật Wi-Fi và kết nối mạng Native (Không cần cài bất kỳ APK nào trên HU)
Write-Host "  [1/5] Bật Wi-Fi & kết nối '$WifiSsid'..." -ForegroundColor Yellow
adb -s $Serial shell "svc wifi enable"
adb -s $Serial shell "cmd -w wifi connect-network `"$WifiSsid`" wpa2 `"$WifiPass`"" | Out-Null

# 2. Đổi ngôn ngữ hệ thống thời gian thực qua setlocale.jar và XÓA NGAY LẬP TỨC (Zero Footprint)
Write-Host "  [2/5] Đổi ngôn ngữ hệ thống sang $Locale (Zero Footprint)..." -ForegroundColor Yellow
if (Test-Path $JarPath) {
    adb -s $Serial push $JarPath /data/local/tmp/setlocale.jar | Out-Null
    adb -s $Serial shell "CLASSPATH=/data/local/tmp/setlocale.jar app_process /data/local/tmp com.setlocale.SetLocale $Locale"
    # Xóa file ngay sau khi chạy: đảm bảo không để lại file rác
    adb -s $Serial shell "rm -f /data/local/tmp/setlocale.jar" | Out-Null
}
adb -s $Serial shell "setprop persist.sys.locale $Locale"
adb -s $Serial shell "settings put system system_locales $Locale"

# 3. Đặt định dạng giờ 12h & tự động cập nhật
Write-Host "  [3/5] Cấu hình định dạng giờ 12h..." -ForegroundColor Yellow
adb -s $Serial shell "settings put system time_12_24 12"
adb -s $Serial shell "settings put global auto_time 1"
adb -s $Serial shell "settings put global auto_time_zone 1"

# 4. Bật Bluetooth
Write-Host "  [4/5] Kích hoạt Bluetooth..." -ForegroundColor Yellow
adb -s $Serial shell "svc bluetooth enable"
adb -s $Serial shell "settings put global bluetooth_on 1"

# 5. Giữ màn hình luôn sáng & tắt màn hình khóa (Stay Awake)
Write-Host "  [5/5] Cấu hình màn hình luôn sáng & gỡ khóa..." -ForegroundColor Yellow
adb -s $Serial shell "settings put global stay_on_while_plugged_in 7"
adb -s $Serial shell "svc power stayon true"
adb -s $Serial shell "settings put secure lock_screen_lock_none true"
adb -s $Serial shell "wm dismiss-keyguard"
adb -s $Serial shell "input keyevent 224"
adb -s $Serial shell "input keyevent 3"

$curLang = adb -s $Serial shell "dumpsys activity | grep 'mGlobalConfiguration' | grep -o '\[.*\]'"
Write-Host "`n========================================================" -ForegroundColor Green
Write-Host "✅ CẤU HÌNH THÀNH CÔNG! TRÊN HU HOÀN TOÀN KHÔNG CÓ FILE RÁC." -ForegroundColor Green
Write-Host "• Ngôn ngữ RAM: $curLang" -ForegroundColor Cyan
Write-Host "• Định dạng giờ: 12h" -ForegroundColor Cyan
Write-Host "• Bluetooth:     Bật" -ForegroundColor Cyan
