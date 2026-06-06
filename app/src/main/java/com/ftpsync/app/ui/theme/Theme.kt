package com.ftpsync.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val LightColorScheme = lightColorScheme(
    primary = ForestGreen,
    onPrimary = JapandiSurface,
    primaryContainer = SageLight,
    onPrimaryContainer = ForestGreen,
    background = JapandiBg,
    onBackground = DarkCharcoal,
    surface = JapandiSurface,
    onSurface = DarkCharcoal,
    surfaceVariant = LinenBorder,
    onSurfaceVariant = SandMuted
)

@Composable
fun FtpSyncTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LightColorScheme,
        content = content
    )
}
