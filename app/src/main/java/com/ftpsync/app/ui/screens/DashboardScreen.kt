package com.ftpsync.app.ui.screens

import android.graphics.Bitmap
import android.graphics.Color as AndroidColor
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

    val isRunning = serverState is FtpServerService.ServerState.Running
    val ipAddress = (serverState as? FtpServerService.ServerState.Running)?.ip ?: ""
    val port = (serverState as? FtpServerService.ServerState.Running)?.port ?: 2121
    val ftpUri = if (isRunning) "ftp://$ipAddress:$port" else ""

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
                text = "FtpSync",
                fontSize = 28.sp,
                fontWeight = FontWeight.Bold,
                color = DarkText,
                fontFamily = FontFamily.SansSerif
            )
            Text(
                text = "Seamless Windows File Access",
                fontSize = 14.sp,
                color = SlateGray,
                fontFamily = FontFamily.SansSerif
            )
        }

        // Connection Card
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .padding(vertical = 24.dp)
                .shadow(4.dp, shape = RoundedCornerShape(20.dp), ambientColor = SlateGray),
            colors = CardDefaults.cardColors(containerColor = PureWhite),
            shape = RoundedCornerShape(20.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                // Status Indicator
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(50.dp))
                        .background(if (isRunning) ActiveGreenLight else PrimaryBlueLight)
                        .padding(horizontal = 16.dp, vertical = 6.dp)
                ) {
                    Text(
                        text = if (isRunning) "SERVER ACTIVE" else "SERVER STOPPED",
                        color = if (isRunning) ActiveGreen else PrimaryBlue,
                        fontWeight = FontWeight.Bold,
                        fontSize = 11.sp
                    )
                }

                Spacer(modifier = Modifier.height(24.dp))

                // URI display
                if (isRunning) {
                    Text(
                        text = ftpUri,
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold,
                        color = PrimaryBlue,
                        fontFamily = FontFamily.Monospace
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Enter this URL in Windows File Explorer",
                        fontSize = 12.sp,
                        color = SlateGray
                    )
                    
                    Spacer(modifier = Modifier.height(24.dp))

                    // QR Code
                    val qrBitmap = remember(ftpUri) { generateQrCode(ftpUri) }
                    qrBitmap?.let {
                        Image(
                            bitmap = it.asImageBitmap(),
                            contentDescription = "Connection QR Code",
                            modifier = Modifier
                                .size(140.dp)
                                .border(1.dp, LightGray, RoundedCornerShape(8.dp))
                                .padding(8.dp)
                        )
                    }
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
                    .padding(bottom = 16.dp)
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
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("Data Transferred", fontSize = 11.sp, color = SlateGray)
                            Text(
                                text = formatBytes(bytesTransferred),
                                fontSize = 16.sp,
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
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("Active Connections", fontSize = 11.sp, color = SlateGray)
                            Text(
                                text = "${clients.size} client(s)",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                color = DarkText
                            )
                        }
                    }
                }
            }
        }

        // Action Toggles
        Row(
            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
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
