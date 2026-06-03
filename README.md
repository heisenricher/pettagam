# FTP-SYNC (Pettagam)

[Download APK](https://github.com/heisenricher/pettagam/releases/download/v3.1.0/app-release.apk)

FTP-SYNC is a clean and lightweight Android application that lets you connect your phone to Windows Explorer over your local Wi-Fi. It uses a custom FTP server running directly on your device. It does not send your data to any cloud service. It is fully local and open source.

## Features

* Lightweight. The app runs with a very small footprint and has no heavy libraries.
* Bright UI. Built with Jetpack Compose, using a clean, light-only design.
* Windows integration. You can scan the QR code or use the provided PowerShell script to mount your phone storage in Windows Explorer.
* Background service. Runs as a foreground service so your file transfers do not stop when you lock your screen.
* Local network advertisement. Automatically advertises the connection on your local network.

## How it works

The Android app starts an FTP server on port 2121. Windows Explorer connects to this port over your local Wi-Fi network. This allows you to drag, drop, and manage files on your phone directly from your computer.

## Quick start guide

### Windows pairing

1. Connect your phone and PC to the same Wi-Fi network.
2. Open the FTP-SYNC app and tap Start Sharing.
3. Open a PowerShell console, navigate to the folder where you saved the files, and run:
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process
   .\Mount-FtpDevice.ps1
   ```
4. Enter the IP address shown on your screen. The script will add a network folder shortcut under This PC.

### Manual connection

1. Open File Explorer in Windows.
2. Type the address shown in the app (like `ftp://192.168.1.10:2121`) in the address bar and press Enter.

## Developer details

The app code is structured simply:
* `app/src/main/java/com/ftpsync/app/MainActivity.kt` handles permissions and manages the service life cycle.
* `app/src/main/java/com/ftpsync/app/service/FtpServerService.kt` is the FTP server itself, written using Apache FtpServer.
* `app/src/main/java/com/ftpsync/app/net/NsdHelper.kt` advertises the server over local network service discovery.
* `app/src/main/java/com/ftpsync/app/ui/screens/DashboardScreen.kt` contains the Compose UI layout.
