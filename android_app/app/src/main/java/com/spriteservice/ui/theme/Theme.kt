package com.spriteservice.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext

/**
 * Dark color scheme for Sprite Service app.
 * 深色主題配色方案。
 */
private val DarkColorScheme = darkColorScheme(
    primary = Purple80,
    secondary = PurpleGrey80,
    tertiary = Pink80,
    background = BackgroundDark,
    surface = SurfaceDark,
    error = ErrorDark
)

/**
 * Light color scheme for Sprite Service app.
 * 淺色主題配色方案。
 */
private val LightColorScheme = lightColorScheme(
    primary = Purple40,
    secondary = PurpleGrey40,
    tertiary = Pink40,
    background = BackgroundLight,
    surface = SurfaceLight,
    error = ErrorLight
)

/**
 * Main theme composable for Sprite Service app.
 * 應用程式的主要主題設定。
 *
 * @param darkTheme Whether to use dark theme. 是否使用深色主題
 * @param dynamicColor Whether to use dynamic color (Android 12+). 是否使用動態顏色
 * @param content The content to be themed. 要套用主題的內容
 */
@Composable
fun SpriteServiceTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        // Use dynamic color on Android 12+ if enabled
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
