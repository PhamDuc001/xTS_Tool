<#
Tạo giọng đọc chuẩn (Edge NamMinh +15%) trên máy Windows cho agent không truy cập được Edge TTS (vd. Muse).

  .\make_vo.ps1 <slug>                          # dùng videos\<slug>\script.json có sẵn
  .\make_vo.ps1 <slug> -Script C:\path\script.json  # chép script.json agent gửi vào videos\<slug>\ trước

Chạy tts.py -> voice_check.py (phải PASS) -> nén vo\ thành renders\<slug>_vo.zip để gửi lại cho agent.
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Slug,
    [string]$Script
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$py = 'D:\Learning\video\manim-studio\.venv\Scripts\python.exe'
$vdir = Join-Path $root "videos\$Slug"
$env:PYTHONIOENCODING = 'utf-8'

if ($Script) {
    New-Item -ItemType Directory -Force $vdir | Out-Null
    Copy-Item -LiteralPath $Script -Destination (Join-Path $vdir 'script.json') -Force
    Write-Host "Đã chép script.json -> $vdir"
}
if (-not (Test-Path (Join-Path $vdir 'script.json'))) { throw "Không có $vdir\script.json" }

Push-Location (Join-Path $root 'tools')
try {
    for ($i = 1; $i -le 3; $i++) {
        & $py tts.py $Slug
        if ($LASTEXITCODE -eq 0) { break }
        if ($i -eq 3) { throw "tts.py lỗi 3 lần liền (mạng/Edge). Thử lại sau vài phút." }
        Write-Host "tts.py lỗi, chờ 45 s rồi thử lại ($i/3)..."
        Start-Sleep -Seconds 45
    }
    & $py voice_check.py $Slug
    if ($LASTEXITCODE -ne 0) { throw "voice_check FAIL - không đóng gói." }
}
finally { Pop-Location }

$renders = Join-Path $root 'renders'
New-Item -ItemType Directory -Force $renders | Out-Null
$zip = Join-Path $renders "${Slug}_vo.zip"
Compress-Archive -Path (Join-Path $vdir 'vo\*') -DestinationPath $zip -Force
$n = (Get-ChildItem (Join-Path $vdir 'vo') -File).Count
Write-Host ("`nXONG: {0} ({1} file, {2:N0} KB) -> giải nén vào videos\{3}\vo\ trên máy agent" -f $zip, $n, ((Get-Item $zip).Length / 1KB), $Slug)
