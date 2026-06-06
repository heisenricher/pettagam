# FTP-SYNC (Pettagam)

<div style="background-color: #FAF8F5; border: 1px solid #DFDCD6; border-radius: 24px; padding: 24px; text-align: center; margin: 20px 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <h3 style="margin-top: 0; color: #2D2E2C; font-weight: 600; font-size: 20px; margin-bottom: 8px;">Get FTP-SYNC</h3>
  <p style="color: #8E877F; font-size: 14px; margin-bottom: 20px; margin-top: 0;">Local and lightweight file sharing for Android.</p>
  <div style="display: inline-block;">
    <a href="https://github.com/heisenricher/pettagam/releases/download/v3.3.0/app-release.apk" style="background-color: #4F6456; color: #FAF8F5; padding: 12px 24px; border-radius: 24px; text-decoration: none; font-weight: bold; font-size: 14px; margin-right: 12px; display: inline-block;">Download Now</a>
    <a href="https://github.com/heisenricher/pettagam/releases" style="background-color: #FAF8F5; color: #8E877F; border: 1px solid #DFDCD6; padding: 12px 24px; border-radius: 24px; text-decoration: none; font-weight: bold; font-size: 14px; display: inline-block;">All Versions</a>
  </div>
</div>

FTP-SYNC is a lightweight Android application built with a Japandi-inspired minimalist design. It hosts a local, RFC-compliant FTP server on your phone so you can manage your files natively from Windows File Explorer over Wi-Fi or Mobile Hotspot without any cloud middleman.

### Highlights
* **Zero Cloud / Fully Offline:** Operates entirely within your local network. No analytics, tracking, or external server calls.
* **Japandi Aesthetic:** Grounded minimalist user experience with calming transitions, smooth river-stone shapes, and warm organic tones.
* **Mobile Hotspot Support:** Prioritizes network interface detection so you can share files directly using your phone's hotspot.
* **Granular Security:** Restricts network listening to active local interfaces, limits concurrent sessions, and supports customizable credentials.
* **Live Activity Logs:** Displays active uploads, downloads, and deletions in real time.

---

## Quick Start Guide

### Pairing with Windows
1. Connect your phone and PC to the same network (Wi-Fi or Mobile Hotspot).
2. Open the FTP-SYNC app and configure your login credentials if desired.
3. Tap **Start Sharing**.
4. Open a PowerShell console on Windows, navigate to the folder where you saved `Mount-FtpDevice.ps1`, and run:
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process
   .\Mount-FtpDevice.ps1
   ```
5. Enter the IP address shown on your screen. The script will add a permanent network folder shortcut under This PC.

### Manual Connection
1. Open Windows File Explorer.
2. Type the address shown in the app (e.g. `ftp://192.168.43.1:2121`) in the address bar and press Enter.
3. Enter the configured username and password (or connect anonymously if enabled).

---

## Developer Details

The app is built using modern Android standards:
* **Jetpack Compose** handles the declarative user interface and animations.
* **Apache FtpServer** manages the protocol connection socket, session timeouts, and user jailing (chroot).
* **NsdHelper.kt** advertises the server over local network service discovery (mDNS).
