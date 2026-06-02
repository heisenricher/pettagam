package com.ftpsync.app.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Environment
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import com.ftpsync.app.MainActivity
import com.ftpsync.app.net.NsdHelper
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.BufferedReader
import java.io.DataOutputStream
import java.io.File
import java.io.InputStreamReader
import java.net.InetAddress
import java.net.NetworkInterface
import java.net.ServerSocket
import java.net.Socket
import java.util.Collections

class FtpServerService : Service() {

    private val serviceJob = SupervisorJob()
    private val serviceScope = CoroutineScope(Dispatchers.IO + serviceJob)
    
    private var serverSocket: ServerSocket? = null
    private var isRunning = false
    private var nsdHelper: NsdHelper? = null

    companion object {
        private const val CHANNEL_ID = "FtpSyncChannel"
        private const val NOTIFICATION_ID = 1001

        private val _serverState = MutableStateFlow<ServerState>(ServerState.Stopped)
        val serverState = _serverState.asStateFlow()

        private val _clientConnections = MutableStateFlow<List<String>>(emptyList())
        val clientConnections = _clientConnections.asStateFlow()

        private val _bytesTransferred = MutableStateFlow(0L)
        val bytesTransferred = _bytesTransferred.asStateFlow()

        fun resetStats() {
            _bytesTransferred.value = 0L
        }

        fun addTransferredBytes(bytes: Long) {
            _bytesTransferred.value += bytes
        }
    }

    sealed class ServerState {
        object Stopped : ServerState()
        data class Running(val ip: String, val port: Int) : ServerState()
    }

    override fun onCreate() {
        super.onCreate()
        nsdHelper = NsdHelper(this)
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val action = intent?.action
        if (action == "STOP") {
            stopServer()
            stopSelf()
        } else {
            startForeground(NOTIFICATION_ID, buildNotification("Starting..."))
            startServer()
        }
        return START_NOT_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun startServer() {
        if (isRunning) return
        isRunning = true

        serviceScope.launch {
            try {
                val port = 2121
                serverSocket = ServerSocket(port)
                val localIp = getLocalIpAddress() ?: "127.0.0.1"
                
                _serverState.value = ServerState.Running(localIp, port)
                nsdHelper?.registerService(port)
                
                updateNotification("FTP server listening on $localIp:$port")
                Log.d("FtpServerService", "FTP Server started on $localIp:$port")

                while (isRunning) {
                    val clientSocket = serverSocket?.accept() ?: break
                    serviceScope.launch {
                        handleClient(clientSocket)
                    }
                }
            } catch (e: Exception) {
                Log.e("FtpServerService", "Server error: ${e.message}")
                stopServer()
            }
        }
    }

    private fun stopServer() {
        isRunning = false
        try {
            serverSocket?.close()
        } catch (e: Exception) {
            Log.e("FtpServerService", "Error closing socket: ${e.message}")
        }
        serverSocket = null
        nsdHelper?.unregisterService()
        _serverState.value = ServerState.Stopped
        _clientConnections.value = emptyList()
    }

    private fun handleClient(socket: Socket) {
        val clientAddress = socket.inetAddress.hostAddress ?: "Unknown"
        _clientConnections.value = _clientConnections.value + clientAddress
        Log.d("FtpServerService", "Client connected: $clientAddress")

        var controlWriter: DataOutputStream? = null
        var controlReader: BufferedReader? = null
        try {
            controlWriter = DataOutputStream(socket.getOutputStream())
            controlReader = BufferedReader(InputStreamReader(socket.getInputStream()))

            controlWriter.writeBytes("220 Welcome to FtpSync (Android)\r\n")
            controlWriter.flush()

            var currentDir = Environment.getExternalStorageDirectory()
            var passiveServerSocket: ServerSocket? = null
            var binaryMode = false

            while (isRunning) {
                val line = controlReader.readLine() ?: break
                Log.d("FtpServerService", "Cmd: $line")
                val parts = line.split(" ", limit = 2)
                val cmd = parts[0].uppercase()
                val args = if (parts.size > 1) parts[1] else ""

                when (cmd) {
                    "USER" -> {
                        controlWriter.writeBytes("331 User name okay, need password.\r\n")
                    }
                    "PASS" -> {
                        controlWriter.writeBytes("230 User logged in, proceed.\r\n")
                    }
                    "SYST" -> {
                        controlWriter.writeBytes("215 UNIX Type: L8\r\n")
                    }
                    "PWD" -> {
                        val relative = currentDir.absolutePath.removePrefix(Environment.getExternalStorageDirectory().absolutePath)
                        val display = if (relative.isEmpty()) "/" else relative
                        controlWriter.writeBytes("257 \"$display\" is current directory.\r\n")
                    }
                    "TYPE" -> {
                        binaryMode = (args.uppercase() == "I")
                        controlWriter.writeBytes("200 Type set to $args\r\n")
                    }
                    "PASV" -> {
                        passiveServerSocket?.close()
                        passiveServerSocket = ServerSocket(0) // Random free port
                        val port = passiveServerSocket.localPort
                        val ipParts = getLocalIpAddress()?.split(".") ?: listOf("127", "0", "0", "1")
                        val p1 = port shr 8
                        val p2 = port and 0xFF
                        val pasvResponse = "227 Entering Passive Mode (${ipParts.joinToString(",")},$p1,$p2).\r\n"
                        controlWriter.writeBytes(pasvResponse)
                    }
                    "LIST" -> {
                        controlWriter.writeBytes("150 File status okay; about to open data connection.\r\n")
                        val dataSocket = passiveServerSocket?.accept()
                        if (dataSocket != null) {
                            val dataOut = DataOutputStream(dataSocket.getOutputStream())
                            val files = currentDir.listFiles() ?: emptyArray()
                            for (file in files) {
                                val size = file.length()
                                val name = file.name
                                val typeStr = if (file.isDirectory) "d" else "-"
                                val lineStr = "$typeStr rwxrwxrwx 1 ftp ftp $size Jun 02 12:00 $name\r\n"
                                dataOut.writeBytes(lineStr)
                            }
                            dataOut.flush()
                            dataSocket.close()
                            controlWriter.writeBytes("226 Closing data connection.\r\n")
                        } else {
                            controlWriter.writeBytes("425 Can't open data connection.\r\n")
                        }
                    }
                    "CWD" -> {
                        val targetDir = if (args.startsWith("/")) {
                            File(Environment.getExternalStorageDirectory(), args)
                        } else {
                            File(currentDir, args)
                        }
                        if (targetDir.exists() && targetDir.isDirectory) {
                            currentDir = targetDir
                            controlWriter.writeBytes("250 Directory successfully changed.\r\n")
                        } else {
                            controlWriter.writeBytes("550 Directory not found.\r\n")
                        }
                    }
                    "CDUP" -> {
                        val parent = currentDir.parentFile
                        if (parent != null && parent.absolutePath.startsWith(Environment.getExternalStorageDirectory().absolutePath)) {
                            currentDir = parent
                            controlWriter.writeBytes("250 Directory successfully changed to parent.\r\n")
                        } else {
                            controlWriter.writeBytes("550 Already at root directory.\r\n")
                        }
                    }
                    "RETR" -> {
                        val file = File(currentDir, args)
                        if (file.exists() && !file.isDirectory) {
                            controlWriter.writeBytes("150 Opening binary mode data connection for ${file.name}.\r\n")
                            val dataSocket = passiveServerSocket?.accept()
                            if (dataSocket != null) {
                                val fileInput = file.inputStream()
                                val buffer = ByteArray(8192)
                                var bytesRead: Int
                                val dataOut = dataSocket.getOutputStream()
                                while (fileInput.read(buffer).also { bytesRead = it } != -1) {
                                    dataOut.write(buffer, 0, bytesRead)
                                    addTransferredBytes(bytesRead.toLong())
                                }
                                dataOut.flush()
                                fileInput.close()
                                dataSocket.close()
                                controlWriter.writeBytes("226 Transfer complete.\r\n")
                            } else {
                                controlWriter.writeBytes("425 Can't open data connection.\r\n")
                            }
                        } else {
                            controlWriter.writeBytes("550 File not found.\r\n")
                        }
                    }
                    "STOR" -> {
                        val file = File(currentDir, args)
                        controlWriter.writeBytes("150 Ok to send data.\r\n")
                        val dataSocket = passiveServerSocket?.accept()
                        if (dataSocket != null) {
                            val fileOutput = file.outputStream()
                            val buffer = ByteArray(8192)
                            var bytesRead: Int
                            val dataIn = dataSocket.getInputStream()
                            while (dataIn.read(buffer).also { bytesRead = it } != -1) {
                                fileOutput.write(buffer, 0, bytesRead)
                                addTransferredBytes(bytesRead.toLong())
                            }
                            fileOutput.flush()
                            fileOutput.close()
                            dataSocket.close()
                            controlWriter.writeBytes("226 Transfer complete.\r\n")
                        } else {
                            controlWriter.writeBytes("425 Can't open data connection.\r\n")
                        }
                    }
                    "DELE" -> {
                        val file = File(currentDir, args)
                        if (file.exists() && file.delete()) {
                            controlWriter.writeBytes("250 File deleted successfully.\r\n")
                        } else {
                            controlWriter.writeBytes("550 Could not delete file.\r\n")
                        }
                    }
                    "RMD" -> {
                        val file = File(currentDir, args)
                        if (file.exists() && file.isDirectory && file.delete()) {
                            controlWriter.writeBytes("250 Directory removed successfully.\r\n")
                        } else {
                            controlWriter.writeBytes("550 Could not remove directory.\r\n")
                        }
                    }
                    "MKD" -> {
                        val file = File(currentDir, args)
                        if (file.mkdir()) {
                            controlWriter.writeBytes("257 \"$args\" directory created.\r\n")
                        } else {
                            controlWriter.writeBytes("550 Could not create directory.\r\n")
                        }
                    }
                    "FEAT" -> {
                        controlWriter.writeBytes("211-Features:\r\n UTF8\r\n211 End\r\n")
                    }
                    "OPTS" -> {
                        controlWriter.writeBytes("200 OK\r\n")
                    }
                    "NOOP" -> {
                        controlWriter.writeBytes("200 OK\r\n")
                    }
                    "QUIT" -> {
                        controlWriter.writeBytes("221 Goodbye.\r\n")
                        controlWriter.flush()
                        break
                    }
                    else -> {
                        controlWriter.writeBytes("502 Command not implemented.\r\n")
                    }
                }
                controlWriter.flush()
            }
        } catch (e: Exception) {
            Log.e("FtpServerService", "Client connection error: ${e.message}")
        } finally {
            try {
                socket.close()
            } catch (ignored: Exception) {}
            _clientConnections.value = _clientConnections.value - clientAddress
            Log.d("FtpServerService", "Client disconnected cleanly: $clientAddress")
        }
    }

    private fun getLocalIpAddress(): String? {
        try {
            val interfaces = Collections.list(NetworkInterface.getNetworkInterfaces())
            for (intf in interfaces) {
                val addrs = Collections.list(intf.inetAddresses)
                for (addr in addrs) {
                    if (!addr.isLoopbackAddress) {
                        val sAddr = addr.hostAddress ?: continue
                        val isIPv4 = sAddr.indexOf(':') < 0
                        if (isIPv4) return sAddr
                    }
                }
            }
        } catch (e: Exception) {
            Log.e("FtpServerService", "Error getting IP: ${e.message}")
        }
        return null
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
            .setContentTitle("FtpSync Active")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.stat_sys_upload_done)
            .setContentIntent(mainPendingIntent)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Stop Server", stopPendingIntent)
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
            val name = "FTP Server Channel"
            val descriptionText = "Notifications for active FTP background service"
            val importance = NotificationManager.IMPORTANCE_LOW
            val channel = NotificationChannel(CHANNEL_ID, name, importance).apply {
                description = descriptionText
            }
            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }

    override fun onDestroy() {
        stopServer()
        serviceJob.cancel()
        super.onDestroy()
    }
}
