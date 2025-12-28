package com.spriteservice.ui

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.spriteservice.ui.auth.LoginScreen
import com.spriteservice.ui.home.HomeScreen
import com.spriteservice.ui.subscription.SubscriptionScreen
import com.spriteservice.ui.upload.UploadScreen

/**
 * Navigation routes for the app.
 * 應用程式的導航路由定義。
 */
object Routes {
    const val LOGIN = "login"
    const val HOME = "home"
    const val UPLOAD = "upload"
    const val SUBSCRIPTION = "subscription"
}

/**
 * Main navigation host for Sprite Service app.
 * 主要導航控制器，管理畫面間的切換。
 */
@Composable
fun SpriteServiceNavHost(
    navController: NavHostController = rememberNavController()
) {
    NavHost(
        navController = navController,
        startDestination = Routes.LOGIN
    ) {
        composable(Routes.LOGIN) {
            LoginScreen(
                onLoginSuccess = {
                    navController.navigate(Routes.HOME) {
                        popUpTo(Routes.LOGIN) { inclusive = true }
                    }
                }
            )
        }

        composable(Routes.HOME) {
            HomeScreen(
                onNavigateToUpload = {
                    navController.navigate(Routes.UPLOAD)
                },
                onNavigateToSubscription = {
                    navController.navigate(Routes.SUBSCRIPTION)
                }
            )
        }

        composable(Routes.UPLOAD) {
            UploadScreen(
                onNavigateBack = {
                    navController.popBackStack()
                }
            )
        }

        composable(Routes.SUBSCRIPTION) {
            SubscriptionScreen(
                onNavigateBack = {
                    navController.popBackStack()
                }
            )
        }
    }
}
