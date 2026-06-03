package com.ftpsync.app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.Settings
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import com.ftpsync.app.service.FtpServerService
import com.ftpsync.app.ui.screens.DashboardScreen
import com.ftpsync.app.ui.theme.FtpSyncTheme

class MainActivity : ComponentActivity() {

    private var isStartingServerFlow = false

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val granted = permissions.entries.all { it.value }
        if (granted) {
            if (isStartingServerFlow) {
                checkStoragePermissionAndStart()
            } else {
                checkStoragePermissionOnly()
            }
        } else {
            Toast.makeText(this, "Permissions required to access files.", Toast.LENGTH_LONG).show()
        }
    }

    private val manageStorageLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            if (Environment.isExternalStorageManager()) {
                if (isStartingServerFlow) {
                    startFtpService()
                }
            } else {
                Toast.makeText(this, "Manage Storage permission is required.", Toast.LENGTH_LONG).show()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Request permissions immediately when opening the app
        requestAppPermissions(autoStart = false)

        setContent {
            FtpSyncTheme {
                Surface(
                    modifier = Modifier.fillMaxSize()
                ) {
                    DashboardScreen(
                        onToggleServer = { start ->
                            if (start) {
                                requestAppPermissions(autoStart = true)
                            } else {
                                stopFtpService()
                            }
                        }
                    )
                }
            }
        }
    }

    private fun requestAppPermissions(autoStart: Boolean) {
        isStartingServerFlow = autoStart
        val permissions = mutableListOf<String>()
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            permissions.add(Manifest.permission.READ_EXTERNAL_STORAGE)
            permissions.add(Manifest.permission.WRITE_EXTERNAL_STORAGE)
        } else {
            // Android 13+
            permissions.add(Manifest.permission.POST_NOTIFICATIONS)
        }

        val allGranted = permissions.all {
            ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED
        }

        if (allGranted) {
            if (autoStart) {
                checkStoragePermissionAndStart()
            } else {
                checkStoragePermissionOnly()
            }
        } else {
            requestPermissionLauncher.launch(permissions.toTypedArray())
        }
    }

    private fun checkStoragePermissionOnly() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            if (!Environment.isExternalStorageManager()) {
                try {
                    val intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION).apply {
                        data = Uri.parse("package:$packageName")
                    }
                    manageStorageLauncher.launch(intent)
                } catch (e: Exception) {
                    val intent = Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION)
                    manageStorageLauncher.launch(intent)
                }
            }
        }
    }

    private fun checkStoragePermissionAndStart() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            if (Environment.isExternalStorageManager()) {
                startFtpService()
            } else {
                try {
                    val intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION).apply {
                        data = Uri.parse("package:$packageName")
                    }
                    manageStorageLauncher.launch(intent)
                } catch (e: Exception) {
                    val intent = Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION)
                    manageStorageLauncher.launch(intent)
                }
            }
        } else {
            startFtpService()
        }
    }

    private fun startFtpService() {
        val intent = Intent(this, FtpServerService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    private fun stopFtpService() {
        val intent = Intent(this, FtpServerService::class.java).apply {
            action = "STOP"
        }
        startService(intent)
    }
}
