# FtpSync (Pettagam) 🚀

A clean, lightweight, and minimalistic Android application designed to seamlessly connect your Android device with Windows Explorer over the local network using a built-in custom FTP Server. No cloud, no trackings, completely open source and local.

---

## Features ✨

- ⚡ **Lightweight & High Performance**: Minimal resource footprint with zero heavy dependencies.
- 📱 **Clean Light-Mode UI**: Built with Jetpack Compose featuring a bright, crisp, and minimalist design.
- 🛜 **Instant Windows Integration**: Generate a dynamic **QR Code** or run the included PowerShell script to instantly mount the Android device storage under "This PC" in Windows.
- ⚙️ **Background Service**: Runs as an Android Foreground Service to keep file transfers active even when the screen is off.
- 🛡️ **mDNS Auto-Discovery**: Automatically advertises the FTP service over local network protocols.

---

## App Design & Screenshots 🎨

The app is built entirely using **Jetpack Compose** with a pure light theme:

```
+---------------------------------------+
|  FtpSync                              |
|  Seamless Windows File Access         |
|                                       |
|  +---------------------------------+  |
|  |         SERVER ACTIVE           |  |
|  |                                 |  |
|  |     ftp://192.168.1.10:2121     |  |
|  |  Enter url in Windows Explorer  |  |
|  |                                 |  |
|  |             [QR CODE]           |  |
|  |                                 |  |
|  +---------------------------------+  |
|                                       |
|  [Data: 1.45 MB]   [Connections: 1]   |
|                                       |
|  [ Reset Stats ]     [ Stop Share ]   |
+---------------------------------------+
```

---

## How it Works 🛠️

```
  +-------------+                     +---------------+
  |   Android   | <=== [Local WiFi] ===> |    Windows    |
  |  (FtpSync)  |                     | File Explorer |
  +-------------+                     +---------------+
  (Runs FTP Server                   (Accesses device files
   on Port 2121)                      directly like local folders)
```

---

## Quick Start Guide 📖

### 1. Windows Pairing (Seamless Setup)
1. Ensure your Android phone and Windows PC are connected to the same Wi-Fi network.
2. Run the server inside the FtpSync app.
3. Open a PowerShell terminal, navigate to the project directory, and run the mounting helper:
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process
   .\Mount-FtpDevice.ps1
   ```
4. Enter the IP address shown in your app. The phone will instantly be mounted under **This PC** in Windows File Explorer as a Network Shortcut!

### 2. Manual Connection
You can also connect manually without any script:
1. Open **Windows File Explorer** (`Win + E`).
2. Type the address displayed in the app (e.g., `ftp://192.168.1.10:2121`) in the address bar and press **Enter**.

---

## Developer Guide 💻

### File Structure
- `app/src/main/java/com/ftpsync/app/MainActivity.kt`: Manages user permissions & foreground service lifecycles.
- `app/src/main/java/com/ftpsync/app/service/FtpServerService.kt`: Custom, lightweight sockets-based FTP server.
- `app/src/main/java/com/ftpsync/app/net/NsdHelper.kt`: Local network mDNS service announcer.
- `app/src/main/java/com/ftpsync/app/ui/screens/DashboardScreen.kt`: Jetpack Compose UI (lightweight, clean bright-mode design).

### Build Requirements
- Android SDK 34
- JDK 17+
- Android Studio Jellyfish or newer
