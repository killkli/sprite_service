package com.spriteservice.domain.repository

import com.spriteservice.domain.model.User
import kotlinx.coroutines.flow.Flow

/**
 * Repository interface for authentication operations.
 * 認證操作的 Repository 介面。
 */
interface AuthRepository {

    /**
     * Flow of current user state.
     * 當前用戶狀態的 Flow。
     */
    val currentUser: Flow<User?>

    /**
     * Check if user is logged in.
     * 檢查用戶是否已登入。
     */
    val isLoggedIn: Boolean

    /**
     * Sign in with email and password.
     * 使用電子郵件和密碼登入。
     */
    suspend fun signInWithEmail(email: String, password: String): Result<User>

    /**
     * Sign up with email and password.
     * 使用電子郵件和密碼註冊。
     */
    suspend fun signUpWithEmail(email: String, password: String): Result<User>

    /**
     * Sign in with Google.
     * 使用 Google 登入。
     */
    suspend fun signInWithGoogle(idToken: String): Result<User>

    /**
     * Sign out current user.
     * 登出當前用戶。
     */
    suspend fun signOut()

    /**
     * Send password reset email.
     * 發送密碼重設郵件。
     */
    suspend fun sendPasswordResetEmail(email: String): Result<Unit>

    /**
     * Get current user's ID token for API authentication.
     * 取得當前用戶的 ID Token 用於 API 認證。
     */
    suspend fun getIdToken(): String?
}
