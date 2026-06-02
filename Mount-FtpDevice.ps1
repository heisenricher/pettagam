# Mount-FtpDevice.ps1
# A clean, minimalistic helper script to mount your FtpSync Android device to Windows Explorer.

$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " FtpSync - Windows Connection Helper" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Ask for Android device IP (Displayed on the FtpSync App)
$ip = Read-Host -Prompt "Enter the FTP URL or IP address shown on your phone (e.g. 192.168.1.10)"

# Clean up input in case user pasted the whole URL
$ip = $ip -replace "ftp://", ""
$ip = $ip -replace "/$", ""
if ($ip -notlike "*:*") {
    $ip = "$ip:2121" # Default FtpSync port
}

$ftpPath = "ftp://$ip/"

Write-Host "`nAttempting to pair with FtpSync at $ftpPath..." -ForegroundColor Yellow

# 2. Add Network Location shortcut in Windows Explorer under "This PC"
try {
    $appData = [System.Environment]::GetFolderPath('ApplicationData')
    $netHood = Join-Path $appData "Microsoft\Windows\Network ShortCuts"
    
    if (-not (Test-Path $netHood)) {
        New-Item -ItemType Directory -Path $netHood -Force | Out-Null
    }

    $shortcutPath = Join-Path $netHood "FtpSync Phone.lnk"
    
    # Create Shortcut COM Object
    $wshShell = New-Object -ComObject WScript.Shell
    $shortcut = $wshShell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $ftpPath
    $shortcut.Description = "FtpSync Android Connection"
    $shortcut.Save()

    Write-Host "`n[Success] FtpSync has been mounted!" -ForegroundColor Green
    Write-Host "Open 'This PC' in Windows File Explorer. You will see a folder shortcut named 'FtpSync Phone'." -ForegroundColor White
    
    # Open File Explorer directly to "This PC"
    Start-Process "explorer.exe" "shell:::{20D04FE0-3AEA-1069-A2D8-08002B30309D}"
}
catch {
    Write-Host "`n[Error] Failed to create shortcut: $_" -ForegroundColor Red
}

Write-Host "`nPress any key to exit..."
[void]$Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
