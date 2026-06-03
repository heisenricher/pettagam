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

    private var pendingServerStart = false

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.entries.all { it.value }
        if (allGranted) {
            handlePermissionsGranted()
        } else {
            Toast.makeText(this, "Permissions are required for FTP-SYNC to work.", Toast.LENGTH_LONG).show()
        }
    }

    private val manageStorageLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) {
        // User returned from the "All Files Access" settings screen
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R && Environment.isExternalStorageManager()) {
            if (pendingServerStart) {
                pendingServerStart = false
                startFtpService()
            }
        } else {
            Toast.makeText(this, "File access permission is required.", Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            FtpSyncTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    DashboardScreen(
                        onToggleServer = { shouldStart ->
                            if (shouldStart) {
                                pendingServerStart = true
                                ensureAllPermissionsAndStart()
                            } else {
                                stopFtpService()
                            }
                        }
                    )
                }
            }
        }

        // Request notification permission on launch (Android 13+)
        requestNotificationPermissionIfNeeded()
    }

    override fun onResume() {
        super.onResume()
        // Re-check storage permission when returning from settings
        if (pendingServerStart && hasAllFilesAccess()) {
            pendingServerStart = false
            startFtpService()
        }
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
            ) {
                requestPermissionLauncher.launch(arrayOf(Manifest.permission.POST_NOTIFICATIONS))
            }
        }
    }

    private fun ensureAllPermissionsAndStart() {
        // Step 1: Check runtime permissions
        val neededPermissions = mutableListOf<String>()

        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            // Android 12 and below need legacy storage permissions
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_EXTERNAL_STORAGE)
                != PackageManager.PERMISSION_GRANTED
            ) {
                neededPermissions.add(Manifest.permission.READ_EXTERNAL_STORAGE)
            }
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.WRITE_EXTERNAL_STORAGE)
                != PackageManager.PERMISSION_GRANTED
            ) {
                neededPermissions.add(Manifest.permission.WRITE_EXTERNAL_STORAGE)
            }
        } else {
            // Android 13+ needs notification permission
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
            ) {
                neededPermissions.add(Manifest.permission.POST_NOTIFICATIONS)
            }
        }

        if (neededPermissions.isNotEmpty()) {
            requestPermissionLauncher.launch(neededPermissions.toTypedArray())
            return
        }

        // Step 2: Check MANAGE_EXTERNAL_STORAGE (Android 11+)
        handlePermissionsGranted()
    }

    private fun handlePermissionsGranted() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            if (!Environment.isExternalStorageManager()) {
                // Redirect to settings to grant "All Files Access"
                try {
                    val intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION).apply {
                        data = Uri.parse("package:$packageName")
                    }
                    manageStorageLauncher.launch(intent)
                } catch (e: Exception) {
                    val intent = Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION)
                    manageStorageLauncher.launch(intent)
                }
                return
            }
        }

        // All permissions granted, start the service
        if (pendingServerStart) {
            pendingServerStart = false
            startFtpService()
        }
    }

    private fun hasAllFilesAccess(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            Environment.isExternalStorageManager()
        } else {
            true
        }
    }

    private fun startFtpService() {
        val prefs = getSharedPreferences("ftp_settings", MODE_PRIVATE)
        val username = prefs.getString("username", "android") ?: "android"
        val password = prefs.getString("password", "android") ?: "android"
        val anonymousAllowed = prefs.getBoolean("anonymous_allowed", false)

        val intent = Intent(this, FtpServerService::class.java).apply {
            putExtra("username", username)
            putExtra("password", password)
            putExtra("anonymousAllowed", anonymousAllowed)
        }
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
