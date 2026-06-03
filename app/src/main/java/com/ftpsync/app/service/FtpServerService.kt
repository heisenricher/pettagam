package com.ftpsync.app.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.net.wifi.WifiManager
import android.os.Build
import android.os.Environment
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import com.ftpsync.app.MainActivity
import com.ftpsync.app.net.NsdHelper
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import org.apache.ftpserver.FtpServerFactory
import org.apache.ftpserver.ftplet.DefaultFtplet
import org.apache.ftpserver.ftplet.FtpSession
import org.apache.ftpserver.ftplet.FtpRequest
import org.apache.ftpserver.ftplet.FtpletResult
import org.apache.ftpserver.listener.ListenerFactory
import org.apache.ftpserver.usermanager.impl.BaseUser
import org.apache.ftpserver.usermanager.impl.WritePermission

class FtpServerService : Service() {

    private var ftpServer: org.apache.ftpserver.FtpServer? = null
    private var nsdHelper: NsdHelper? = null

    companion object {
        private const val TAG = "FtpServerService"
        private const val CHANNEL_ID = "FtpSyncChannel"
        private const val NOTIFICATION_ID = 1001
        private const val FTP_PORT = 2121

        private val _serverState = MutableStateFlow<ServerState>(ServerState.Stopped)
        val serverState = _serverState.asStateFlow()

        private val _clientConnections = MutableStateFlow<List<String>>(emptyList())
        val clientConnections = _clientConnections.asStateFlow()

        private val _bytesTransferred = MutableStateFlow(0L)
        val bytesTransferred = _bytesTransferred.asStateFlow()

        private val _transferLogs = MutableStateFlow<List<String>>(emptyList())
        val transferLogs = _transferLogs.asStateFlow()

        fun resetStats() {
            _bytesTransferred.value = 0L
        }

        fun addTransferLog(message: String) {
            val timestamp = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault()).format(java.util.Date())
            val entry = "[$timestamp] $message"
            _transferLogs.value = (listOf(entry) + _transferLogs.value).take(30)
        }

        fun clearLogs() {
            _transferLogs.value = emptyList()
        }
    }

    sealed class ServerState {
        object Stopped : ServerState()
        data class Running(val ip: String, val port: Int) : ServerState()
        data class Error(val message: String) : ServerState()
    }

    override fun onCreate() {
        super.onCreate()
        nsdHelper = NsdHelper(this)
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val action = intent?.action
        if (action == "STOP") {
            stopFtpServer()
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
        } else {
            val notification = buildNotification("Starting FTP server...")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                startForeground(
                    NOTIFICATION_ID,
                    notification,
                    android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
                )
            } else {
                startForeground(NOTIFICATION_ID, notification)
            }
            startFtpServer()
        }
        return START_NOT_STICKY
    }

    // Android 15+ enforces a 6-hour timeout for dataSync foreground services
    override fun onTimeout(startId: Int) {
        stopFtpServer()
        stopSelf()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun startFtpServer() {
        if (ftpServer != null && !ftpServer!!.isStopped) return

        try {
            val serverFactory = FtpServerFactory()

            // Configure listener on port 2121
            val listenerFactory = ListenerFactory()
            listenerFactory.port = FTP_PORT
            serverFactory.addListener("default", listenerFactory.createListener())

            // Configure anonymous user with full access to external storage
            val user = BaseUser()
            user.name = "android"
            user.password = "android"
            user.homeDirectory = Environment.getExternalStorageDirectory().absolutePath
            user.authorities = listOf(WritePermission())
            serverFactory.userManager.save(user)

            // Also allow anonymous access
            val anonUser = BaseUser()
            anonUser.name = "anonymous"
            anonUser.password = ""
            anonUser.homeDirectory = Environment.getExternalStorageDirectory().absolutePath
            anonUser.authorities = listOf(WritePermission())
            serverFactory.userManager.save(anonUser)

            // Register ftplet to track connections
            val ftplets = LinkedHashMap<String, org.apache.ftpserver.ftplet.Ftplet>()
            ftplets["tracker"] = ConnectionTracker()
            serverFactory.ftplets = ftplets

            // Start the server
            ftpServer = serverFactory.createServer()
            ftpServer?.start()

            val localIp = getWifiIpAddress()
            _serverState.value = ServerState.Running(localIp, FTP_PORT)
            nsdHelper?.registerService(FTP_PORT)

            updateNotification("FTP server on $localIp:$FTP_PORT")
            Log.d(TAG, "FTP Server started on $localIp:$FTP_PORT")

        } catch (e: Exception) {
            Log.e(TAG, "Failed to start FTP server: ${e.message}", e)
            val errorMsg = if (e.message?.contains("BindException", ignoreCase = true) == true || 
                             e.cause?.message?.contains("BindException", ignoreCase = true) == true) {
                "Port $FTP_PORT is already in use by another app"
            } else {
                e.message ?: "Unknown error occurred"
            }
            _serverState.value = ServerState.Error(errorMsg)
            updateNotification("Failed to start server: $errorMsg")
        }
    }

    private fun stopFtpServer() {
        try {
            ftpServer?.stop()
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping FTP server: ${e.message}")
        }
        ftpServer = null
        nsdHelper?.unregisterService()
        _serverState.value = ServerState.Stopped
        _clientConnections.value = emptyList()
    }

    private fun getWifiIpAddress(): String {
        try {
            val wifiManager = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
            @Suppress("DEPRECATION")
            val wifiInfo = wifiManager.connectionInfo
            val ipInt = wifiInfo.ipAddress
            if (ipInt != 0) {
                return String.format(
                    "%d.%d.%d.%d",
                    ipInt and 0xff,
                    ipInt shr 8 and 0xff,
                    ipInt shr 16 and 0xff,
                    ipInt shr 24 and 0xff
                )
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error getting WiFi IP: ${e.message}")
        }

        // Fallback: enumerate network interfaces
        try {
            val interfaces = java.util.Collections.list(java.net.NetworkInterface.getNetworkInterfaces())
            for (intf in interfaces) {
                val addrs = java.util.Collections.list(intf.inetAddresses)
                for (addr in addrs) {
                    if (!addr.isLoopbackAddress) {
                        val sAddr = addr.hostAddress ?: continue
                        if (sAddr.indexOf(':') < 0) return sAddr
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error enumerating network interfaces: ${e.message}")
        }
        return "127.0.0.1"
    }

    // Ftplet to track client connections
    inner class ConnectionTracker : DefaultFtplet() {
        override fun onConnect(session: FtpSession): FtpletResult {
            val clientAddr = session.clientAddress?.toString() ?: "Unknown"
            val clean = clientAddr.removePrefix("/").substringBefore(":")
            _clientConnections.value = _clientConnections.value + clean
            Log.d(TAG, "Client connected: $clean")
            return FtpletResult.DEFAULT
        }

        override fun onDisconnect(session: FtpSession): FtpletResult {
            val clientAddr = session.clientAddress?.toString() ?: "Unknown"
            val clean = clientAddr.removePrefix("/").substringBefore(":")
            _clientConnections.value = _clientConnections.value - clean
            Log.d(TAG, "Client disconnected: $clean")
            return FtpletResult.DEFAULT
        }

        override fun onUploadEnd(session: FtpSession, request: FtpRequest): FtpletResult {
            val filename = request.argument?.substringAfterLast('/') ?: "unknown"
            addTransferLog("Uploaded: $filename")
            Log.d(TAG, "Upload completed: ${request.argument}")
            return FtpletResult.DEFAULT
        }

        override fun onDownloadEnd(session: FtpSession, request: FtpRequest): FtpletResult {
            val filename = request.argument?.substringAfterLast('/') ?: "unknown"
            addTransferLog("Downloaded: $filename")
            Log.d(TAG, "Download completed: ${request.argument}")
            return FtpletResult.DEFAULT
        }

        override fun onDeleteEnd(session: FtpSession, request: FtpRequest): FtpletResult {
            val filename = request.argument?.substringAfterLast('/') ?: "unknown"
            addTransferLog("Deleted: $filename")
            Log.d(TAG, "Delete completed: ${request.argument}")
            return FtpletResult.DEFAULT
        }
    }

    private fun buildNotification(text: String): Notification {
        val stopIntent = Intent(this, FtpServerService::class.java).apply {
            action = "STOP"
        }
        val stopPendingIntent = PendingIntent.getService(
            this, 0, stopIntent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val mainIntent = Intent(this, MainActivity::class.java)
        val mainPendingIntent = PendingIntent.getActivity(
            this, 0, mainIntent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("FTP-SYNC Active")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.stat_sys_upload_done)
            .setContentIntent(mainPendingIntent)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Stop", stopPendingIntent)
            .setOngoing(true)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .build()
    }

    private fun updateNotification(text: String) {
        val notification = buildNotification(text)
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        notificationManager.notify(NOTIFICATION_ID, notification)
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val name = "FTP Server"
            val descriptionText = "Active FTP server notification"
            val importance = NotificationManager.IMPORTANCE_LOW
            val channel = NotificationChannel(CHANNEL_ID, name, importance).apply {
                description = descriptionText
            }
            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }

    override fun onDestroy() {
        stopFtpServer()
        super.onDestroy()
    }
}
