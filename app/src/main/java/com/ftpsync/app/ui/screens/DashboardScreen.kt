package com.ftpsync.app.ui.screens

import android.graphics.Bitmap
import android.graphics.Color as AndroidColor
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import android.content.Context
import android.os.Environment
import android.os.StatFs
import androidx.compose.foundation.clickable
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.ui.platform.LocalContext
import com.ftpsync.app.service.FtpServerService
import com.ftpsync.app.ui.theme.*
import com.google.zxing.BarcodeFormat
import com.google.zxing.qrcode.QRCodeWriter
import java.util.Locale

@Composable
fun DashboardScreen(
    onToggleServer: (Boolean) -> Unit
) {
    val serverState by FtpServerService.serverState.collectAsState()
    val clients by FtpServerService.clientConnections.collectAsState()
    val bytesTransferred by FtpServerService.bytesTransferred.collectAsState()
    val logs by FtpServerService.transferLogs.collectAsState()

    val isRunning = serverState is FtpServerService.ServerState.Running
    val isError = serverState is FtpServerService.ServerState.Error
    val errorMessage = (serverState as? FtpServerService.ServerState.Error)?.message ?: ""

    val ipAddress = (serverState as? FtpServerService.ServerState.Running)?.ip ?: ""
    val port = (serverState as? FtpServerService.ServerState.Running)?.port ?: 2121
    val ftpUri = if (isRunning) "ftp://$ipAddress:$port" else ""

    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences("ftp_settings", Context.MODE_PRIVATE) }
    
    var username by remember { mutableStateOf(prefs.getString("username", "android") ?: "android") }
    var password by remember { mutableStateOf(prefs.getString("password", "android") ?: "android") }
    var anonymousAllowed by remember { mutableStateOf(prefs.getBoolean("anonymous_allowed", false)) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(OffWhite)
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.SpaceBetween
    ) {
        // App Header
        Column(
            modifier = Modifier.fillMaxWidth().padding(top = 16.dp),
            horizontalAlignment = Alignment.Start
        ) {
            Text(
                text = "FTP-SYNC",
                fontSize = 28.sp,
                fontWeight = FontWeight.Bold,
                color = DarkText,
                fontFamily = FontFamily.SansSerif
            )
            Text(
                text = "Local Windows File Access",
                fontSize = 14.sp,
                color = SlateGray,
                fontFamily = FontFamily.SansSerif
            )
        }

        // Connection Card
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 16.dp)
                .then(if (isRunning) Modifier.height(210.dp) else Modifier.weight(1f)),
            colors = CardDefaults.cardColors(containerColor = PureWhite),
            shape = RoundedCornerShape(20.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(20.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                // Status Indicator
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(50.dp))
                        .background(
                            when {
                                isRunning -> ActiveGreenLight
                                isError -> WarningRed.copy(alpha = 0.1f)
                                else -> PrimaryBlueLight
                            }
                        )
                        .padding(horizontal = 16.dp, vertical = 6.dp)
                ) {
                    Text(
                        text = when {
                            isRunning -> "SERVER ACTIVE"
                            isError -> "SERVER ERROR"
                            else -> "SERVER STOPPED"
                        },
                        color = when {
                            isRunning -> ActiveGreen
                            isError -> WarningRed
                            else -> PrimaryBlue
                        },
                        fontWeight = FontWeight.Bold,
                        fontSize = 11.sp
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Connection details or errors
                if (isRunning) {
                    Text(
                        text = ftpUri,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold,
                        color = PrimaryBlue,
                        fontFamily = FontFamily.Monospace
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Enter this URL in Windows File Explorer",
                        fontSize = 11.sp,
                        color = SlateGray
                    )
                    
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    if (!anonymousAllowed) {
                        Text(
                            text = "Login: $username / Pass: $password",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Medium,
                            color = DarkText,
                            fontFamily = FontFamily.Monospace
                        )
                    } else {
                        Text(
                            text = "Anonymous Login Enabled",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Medium,
                            color = ActiveGreen
                        )
                    }
                    
                    Spacer(modifier = Modifier.height(10.dp))

                    // QR Code
                    val qrBitmap = remember(ftpUri) { generateQrCode(ftpUri) }
                    qrBitmap?.let {
                        Image(
                            bitmap = it.asImageBitmap(),
                            contentDescription = "Connection QR Code",
                            modifier = Modifier
                                .size(90.dp)
                                .border(1.dp, LightGray, RoundedCornerShape(8.dp))
                                .padding(4.dp)
                        )
                    }
                } else if (isError) {
                    Text(
                        text = errorMessage,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = WarningRed,
                        fontFamily = FontFamily.SansSerif,
                        modifier = Modifier.padding(horizontal = 12.dp),
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Make sure no other FTP server is running on port $port and check your connection.",
                        fontSize = 12.sp,
                        color = SlateGray,
                        modifier = Modifier.padding(horizontal = 12.dp),
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center
                    )
                } else {
                    Text(
                        text = "Not hosting",
                        fontSize = 18.sp,
                        color = SlateGray
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Tap start to enable file sharing",
                        fontSize = 12.sp,
                        color = SlateGray
                    )
                }
            }
        }

        // Stats & Clients Dashboard
        if (isRunning) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 8.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    // Transferred Card
                    Card(
                        modifier = Modifier.weight(1f).padding(end = 8.dp),
                        colors = CardDefaults.cardColors(containerColor = PureWhite),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text("Data Transferred", fontSize = 11.sp, color = SlateGray)
                            Text(
                                text = formatBytes(bytesTransferred),
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold,
                                color = DarkText
                            )
                        }
                    }

                    // Connected Clients Card
                    Card(
                        modifier = Modifier.weight(1f).padding(start = 8.dp),
                        colors = CardDefaults.cardColors(containerColor = PureWhite),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text("Active Connections", fontSize = 11.sp, color = SlateGray)
                            Text(
                                text = "${clients.size} client(s)",
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold,
                                color = DarkText
                            )
                        }
                    }
                }
            }
        }

        // Live Transfer Logs Card
        if (isRunning && logs.isNotEmpty()) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(110.dp)
                    .padding(bottom = 8.dp)
                    .shadow(2.dp, shape = RoundedCornerShape(16.dp), ambientColor = SlateGray),
                colors = CardDefaults.cardColors(containerColor = PureWhite),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(
                    modifier = Modifier.padding(12.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Activity Log",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = DarkText
                        )
                        TextButton(
                            onClick = { FtpServerService.clearLogs() },
                            contentPadding = PaddingValues(0.dp),
                            modifier = Modifier.height(20.dp)
                        ) {
                            Text("Clear", fontSize = 10.sp, color = WarningRed)
                        }
                    }
                    Spacer(modifier = Modifier.height(2.dp))
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(2.dp)
                    ) {
                        items(logs) { log ->
                            Text(
                                text = log,
                                fontSize = 10.sp,
                                fontFamily = FontFamily.Monospace,
                                color = DarkText
                            )
                        }
                    }
                }
            }
        }

        // Device Storage Statistics Card
        val storageInfo = remember { getStorageInfo() }
        val totalGb = storageInfo.totalSpace.toDouble() / (1024.0 * 1024.0 * 1024.0)
        val freeGb = storageInfo.freeSpace.toDouble() / (1024.0 * 1024.0 * 1024.0)
        val usedGb = storageInfo.usedSpace.toDouble() / (1024.0 * 1024.0 * 1024.0)
        val percentUsed = if (totalGb > 0) (usedGb / totalGb).toFloat() else 0f

        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 12.dp)
                .shadow(2.dp, shape = RoundedCornerShape(16.dp), ambientColor = SlateGray),
            colors = CardDefaults.cardColors(containerColor = PureWhite),
            shape = RoundedCornerShape(16.dp)
        ) {
            Column(
                modifier = Modifier.padding(12.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Device Storage",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        color = DarkText
                    )
                    Text(
                        text = String.format(Locale.US, "%.2f GB free", freeGb),
                        fontSize = 11.sp,
                        color = PrimaryBlue,
                        fontWeight = FontWeight.Medium
                    )
                }
                Spacer(modifier = Modifier.height(6.dp))
                LinearProgressIndicator(
                    progress = { percentUsed },
                    modifier = Modifier.fillMaxWidth().height(6.dp).clip(RoundedCornerShape(3.dp)),
                    color = PrimaryBlue,
                    trackColor = LightGray
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = String.format(Locale.US, "%.2f GB used of %.2f GB total", usedGb, totalGb),
                    fontSize = 10.sp,
                    color = SlateGray
                )
            }
        }

        // Access Settings Card (only shown when server is stopped)
        if (!isRunning) {
            var isSettingsExpanded by remember { mutableStateOf(false) }
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 12.dp)
                    .shadow(2.dp, shape = RoundedCornerShape(16.dp), ambientColor = SlateGray),
                colors = CardDefaults.cardColors(containerColor = PureWhite),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { isSettingsExpanded = !isSettingsExpanded },
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Access Settings",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                            color = DarkText
                        )
                        Text(
                            text = if (isSettingsExpanded) "Collapse" else "Configure",
                            fontSize = 12.sp,
                            color = PrimaryBlue,
                            fontWeight = FontWeight.Medium
                        )
                    }

                    if (isSettingsExpanded) {
                        Spacer(modifier = Modifier.height(16.dp))

                        OutlinedTextField(
                            value = username,
                            onValueChange = {
                                username = it
                                prefs.edit().putString("username", it).apply()
                            },
                            label = { Text("Username") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true
                        )

                        Spacer(modifier = Modifier.height(12.dp))

                        OutlinedTextField(
                            value = password,
                            onValueChange = {
                                password = it
                                prefs.edit().putString("password", it).apply()
                            },
                            label = { Text("Password") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true
                        )

                        Spacer(modifier = Modifier.height(12.dp))

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(
                                    text = "Allow Anonymous Login",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Medium,
                                    color = DarkText
                                )
                                Text(
                                    text = "Lets PC connect without password",
                                    fontSize = 11.sp,
                                    color = SlateGray
                                )
                            }
                            Switch(
                                checked = anonymousAllowed,
                                onCheckedChange = {
                                    anonymousAllowed = it
                                    prefs.edit().putBoolean("anonymous_allowed", it).apply()
                                }
                            )
                        }
                    }
                }
            }
        }

        // Action Toggles
        Row(
            modifier = Modifier.fillMaxWidth().padding(bottom = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            if (isRunning) {
                OutlinedButton(
                    onClick = { FtpServerService.resetStats() },
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = WarningRed),
                    border = BorderStroke(1.dp, WarningRed.copy(alpha = 0.5f))
                ) {
                    Text("Reset Stats")
                }
            }

            Button(
                onClick = { onToggleServer(!isRunning) },
                modifier = Modifier.weight(if (isRunning) 2f else 1f),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isRunning) WarningRed else PrimaryBlue
                )
            ) {
                Text(
                    text = if (isRunning) "Stop Share" else "Start Sharing",
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 16.sp
                )
            }
        }
    }
}

private fun generateQrCode(text: String): Bitmap? {
    return try {
        val writer = QRCodeWriter()
        val bitMatrix = writer.encode(text, BarcodeFormat.QR_CODE, 256, 256)
        val width = bitMatrix.width
        val height = bitMatrix.height
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.RGB_565)
        for (x in 0 until width) {
            for (y in 0 until height) {
                bitmap.setPixel(x, y, if (bitMatrix.get(x, y)) AndroidColor.BLACK else AndroidColor.WHITE)
            }
        }
        bitmap
    } catch (e: Exception) {
        null
    }
}

private fun formatBytes(bytes: Long): String {
    if (bytes <= 0) return "0 B"
    val units = arrayOf("B", "KB", "MB", "GB", "TB")
    val digitGroups = (Math.log10(bytes.toDouble()) / Math.log10(1024.0)).toInt()
    return String.format(Locale.US, "%.2f %s", bytes / Math.pow(1024.0, digitGroups.toDouble()), units[digitGroups])
}

private data class StorageInfo(
    val totalSpace: Long,
    val freeSpace: Long,
    val usedSpace: Long
)

private fun getStorageInfo(): StorageInfo {
    return try {
        val path = Environment.getExternalStorageDirectory()
        val stat = StatFs(path.path)
        val blockSize = stat.blockSizeLong
        val totalBlocks = stat.blockCountLong
        val availableBlocks = stat.availableBlocksLong
        val total = totalBlocks * blockSize
        val free = availableBlocks * blockSize
        StorageInfo(total, free, total - free)
    } catch (e: Exception) {
        StorageInfo(0L, 0L, 0L)
    }
}
