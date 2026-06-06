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
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.core.EaseOutQuart
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

    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences("ftp_settings", Context.MODE_PRIVATE) }

    var username by remember { mutableStateOf(prefs.getString("username", "android") ?: "android") }
    var password by remember { mutableStateOf(prefs.getString("password", "android") ?: "android") }
    var anonymousAllowed by remember { mutableStateOf(prefs.getBoolean("anonymous_allowed", false)) }

    // Read active IP address. If running, use reported IP; if stopped, scan interfaces.
    val activeIp = if (isRunning) {
        (serverState as FtpServerService.ServerState.Running).ip
    } else {
        remember(serverState) { getLocalNetworkIp() }
    }
    val port = if (isRunning) (serverState as FtpServerService.ServerState.Running).port else 2121
    val isOffline = activeIp == "127.0.0.1"
    val ftpUri = if (isRunning && !isOffline) "ftp://$activeIp:$port" else ""

    // Eased animations for Japandi transitions (600ms, EaseOutQuart)
    val animatedCardHeight by animateDpAsState(
        targetValue = when {
            isRunning -> 220.dp
            else -> 300.dp
        },
        animationSpec = tween(durationMillis = 600, easing = EaseOutQuart)
    )

    val statusBgColor by animateColorAsState(
        targetValue = when {
            isRunning -> SageLight
            isError || isOffline -> CrimsonLight
            else -> ClayLight
        },
        animationSpec = tween(durationMillis = 600, easing = EaseOutQuart)
    )

    val statusTextColor by animateColorAsState(
        targetValue = when {
            isRunning -> ForestGreen
            isError || isOffline -> CrimsonWarning
            else -> ClayAccent
        },
        animationSpec = tween(durationMillis = 600, easing = EaseOutQuart)
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(JapandiBg)
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.SpaceBetween
    ) {
        // App Header
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 16.dp),
            horizontalAlignment = Alignment.Start
        ) {
            Text(
                text = "FTP-SYNC",
                fontSize = 28.sp,
                fontWeight = FontWeight.Bold,
                color = DarkCharcoal,
                fontFamily = FontFamily.SansSerif
            )
            Text(
                text = "Local Windows File Access",
                fontSize = 14.sp,
                color = SandMuted,
                fontFamily = FontFamily.SansSerif
            )
        }

        // Connection Card (Pebbled + Linen Border)
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 12.dp)
                .height(animatedCardHeight)
                .border(BorderStroke(1.dp, LinenBorder), shape = RoundedCornerShape(24.dp)),
            colors = CardDefaults.cardColors(containerColor = JapandiSurface),
            shape = RoundedCornerShape(24.dp)
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
                        .clip(RoundedCornerShape(24.dp))
                        .background(statusBgColor)
                        .padding(horizontal = 14.dp, vertical = 6.dp)
                ) {
                    Text(
                        text = when {
                            isRunning -> "SERVER ACTIVE"
                            isError -> "SERVER ERROR"
                            isOffline -> "OFFLINE"
                            else -> "READY TO SHARE"
                        },
                        color = statusTextColor,
                        fontWeight = FontWeight.Bold,
                        fontSize = 10.sp
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Connection details or errors
                if (isRunning) {
                    Text(
                        text = ftpUri,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = ForestGreen,
                        fontFamily = FontFamily.Monospace
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        text = "Enter this URL in Windows File Explorer",
                        fontSize = 11.sp,
                        color = SandMuted
                    )
                    
                    Spacer(modifier = Modifier.height(6.dp))
                    
                    if (!anonymousAllowed) {
                        Text(
                            text = "Login: $username / Pass: $password",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Medium,
                            color = DarkCharcoal,
                            fontFamily = FontFamily.Monospace
                        )
                    } else {
                        Text(
                            text = "Anonymous Login Enabled",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Medium,
                            color = ForestGreen
                        )
                    }
                    
                    Spacer(modifier = Modifier.height(8.dp))

                    // QR Code
                    val qrBitmap = remember(ftpUri) { generateQrCode(ftpUri) }
                    qrBitmap?.let {
                        Image(
                            bitmap = it.asImageBitmap(),
                            contentDescription = "Connection QR Code",
                            modifier = Modifier
                                .size(80.dp)
                                .border(1.dp, LinenBorder, RoundedCornerShape(8.dp))
                                .padding(2.dp)
                        )
                    }
                } else if (isError) {
                    Text(
                        text = errorMessage,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = CrimsonWarning,
                        fontFamily = FontFamily.SansSerif,
                        modifier = Modifier.padding(horizontal = 12.dp),
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "Make sure no other FTP server is running on port $port and check your connection.",
                        fontSize = 11.sp,
                        color = SandMuted,
                        modifier = Modifier.padding(horizontal = 12.dp),
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center
                    )
                } else if (isOffline) {
                    Text(
                        text = "No local network found",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = CrimsonWarning,
                        fontFamily = FontFamily.SansSerif
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "Please connect to Wi-Fi or turn on Mobile Hotspot to share files with your computer.",
                        fontSize = 11.sp,
                        color = SandMuted,
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                        modifier = Modifier.padding(horizontal = 12.dp)
                    )
                } else {
                    Text(
                        text = "ftp://$activeIp:$port",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = ClayAccent,
                        fontFamily = FontFamily.Monospace
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Tap start to share folders with your computer",
                        fontSize = 11.sp,
                        color = SandMuted
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
                        modifier = Modifier
                            .weight(1f)
                            .padding(end = 8.dp)
                            .border(BorderStroke(1.dp, LinenBorder), shape = RoundedCornerShape(24.dp)),
                        colors = CardDefaults.cardColors(containerColor = JapandiSurface),
                        shape = RoundedCornerShape(24.dp)
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text("Data Transferred", fontSize = 11.sp, color = SandMuted)
                            Text(
                                text = formatBytes(bytesTransferred),
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold,
                                color = DarkCharcoal
                            )
                        }
                    }

                    // Connected Clients Card
                    Card(
                        modifier = Modifier
                            .weight(1f)
                            .padding(start = 8.dp)
                            .border(BorderStroke(1.dp, LinenBorder), shape = RoundedCornerShape(24.dp)),
                        colors = CardDefaults.cardColors(containerColor = JapandiSurface),
                        shape = RoundedCornerShape(24.dp)
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text("Active Connections", fontSize = 11.sp, color = SandMuted)
                            Text(
                                text = "${clients.size} client(s)",
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold,
                                color = DarkCharcoal
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
                    .border(BorderStroke(1.dp, LinenBorder), shape = RoundedCornerShape(24.dp)),
                colors = CardDefaults.cardColors(containerColor = JapandiSurface),
                shape = RoundedCornerShape(24.dp)
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
                            color = DarkCharcoal
                        )
                        TextButton(
                            onClick = { FtpServerService.clearLogs() },
                            contentPadding = PaddingValues(0.dp),
                            modifier = Modifier.height(20.dp)
                        ) {
                            Text("Clear", fontSize = 10.sp, color = CrimsonWarning)
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
                                color = DarkCharcoal
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
                .border(BorderStroke(1.dp, LinenBorder), shape = RoundedCornerShape(24.dp)),
            colors = CardDefaults.cardColors(containerColor = JapandiSurface),
            shape = RoundedCornerShape(24.dp)
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
                        color = DarkCharcoal
                    )
                    Text(
                        text = String.format(Locale.US, "%.2f GB free", freeGb),
                        fontSize = 11.sp,
                        color = ClayAccent,
                        fontWeight = FontWeight.Medium
                    )
                }
                Spacer(modifier = Modifier.height(6.dp))
                LinearProgressIndicator(
                    progress = { percentUsed },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(6.dp)
                        .clip(RoundedCornerShape(3.dp)),
                    color = ClayAccent,
                    trackColor = LinenBorder
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = String.format(Locale.US, "%.2f GB used of %.2f GB total", usedGb, totalGb),
                    fontSize = 10.sp,
                    color = SandMuted
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
                    .border(BorderStroke(1.dp, LinenBorder), shape = RoundedCornerShape(24.dp)),
                colors = CardDefaults.cardColors(containerColor = JapandiSurface),
                shape = RoundedCornerShape(24.dp)
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
                            color = DarkCharcoal
                        )
                        Text(
                            text = if (isSettingsExpanded) "Collapse" else "Configure",
                            fontSize = 12.sp,
                            color = ForestGreen,
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
                            singleLine = true,
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = ForestGreen,
                                unfocusedBorderColor = LinenBorder,
                                focusedLabelColor = ForestGreen,
                                unfocusedLabelColor = SandMuted,
                                focusedTextColor = DarkCharcoal,
                                unfocusedTextColor = DarkCharcoal
                            )
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
                            singleLine = true,
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = ForestGreen,
                                unfocusedBorderColor = LinenBorder,
                                focusedLabelColor = ForestGreen,
                                unfocusedLabelColor = SandMuted,
                                focusedTextColor = DarkCharcoal,
                                unfocusedTextColor = DarkCharcoal
                            )
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
                                    color = DarkCharcoal
                                )
                                Text(
                                    text = "Lets PC connect without password",
                                    fontSize = 11.sp,
                                    color = SandMuted
                                )
                            }
                            Switch(
                                checked = anonymousAllowed,
                                onCheckedChange = {
                                    anonymousAllowed = it
                                    prefs.edit().putBoolean("anonymous_allowed", it).apply()
                                },
                                colors = SwitchDefaults.colors(
                                    checkedThumbColor = JapandiSurface,
                                    checkedTrackColor = ForestGreen,
                                    uncheckedThumbColor = SandMuted,
                                    uncheckedTrackColor = LinenBorder
                                )
                            )
                        }
                    }
                }
            }
        }

        // Action Toggles
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            if (isRunning) {
                OutlinedButton(
                    onClick = { FtpServerService.resetStats() },
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(24.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = CrimsonWarning),
                    border = BorderStroke(1.dp, CrimsonWarning.copy(alpha = 0.5f))
                ) {
                    Text("Reset Stats")
                }
            }

            Button(
                onClick = { onToggleServer(!isRunning) },
                modifier = Modifier.weight(if (isRunning) 2f else 1f),
                shape = RoundedCornerShape(24.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isRunning) CrimsonWarning else ForestGreen,
                    contentColor = JapandiSurface
                ),
                enabled = !isOffline || isRunning
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

private fun getLocalNetworkIp(): String {
    try {
        val interfaces = java.util.Collections.list(java.net.NetworkInterface.getNetworkInterfaces())
        val prioritizedNames = listOf("wlan0", "wlan1", "ap0", "rndis0")
        val sortedInterfaces = interfaces.sortedBy { intf ->
            val index = prioritizedNames.indexOf(intf.name)
            if (index != -1) index else prioritizedNames.size
        }
        for (intf in sortedInterfaces) {
            if (intf.isLoopback || !intf.isUp) continue
            val addrs = java.util.Collections.list(intf.inetAddresses)
            for (addr in addrs) {
                if (!addr.isLoopbackAddress) {
                    val sAddr = addr.hostAddress ?: continue
                    val isIPv4 = sAddr.indexOf(':') < 0
                    if (isIPv4) return sAddr
                }
            }
        }
    } catch (e: Exception) {
        // Ignore
    }
    return "127.0.0.1"
}
