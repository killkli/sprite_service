package com.spriteservice

import android.app.Application
import dagger.hilt.android.HiltAndroidApp

/**
 * Application class for Sprite Service Android app.
 * 使用 Hilt 進行依賴注入的 Application 類別。
 */
@HiltAndroidApp
class SpriteServiceApp : Application() {

    override fun onCreate() {
        super.onCreate()
        // Initialize any app-wide configurations here
        // 在此初始化應用程式範圍的配置
    }
}
