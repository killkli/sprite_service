package com.spriteservice

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.spriteservice.ui.SpriteServiceNavHost
import com.spriteservice.ui.theme.SpriteServiceTheme
import dagger.hilt.android.AndroidEntryPoint

/**
 * Main activity for Sprite Service app.
 * 使用 Jetpack Compose 和 Hilt 的主要 Activity。
 */
@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            SpriteServiceTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    SpriteServiceNavHost()
                }
            }
        }
    }
}
