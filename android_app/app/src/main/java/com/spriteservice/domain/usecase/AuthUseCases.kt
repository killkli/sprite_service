package com.spriteservice.domain.usecase

import com.spriteservice.domain.model.User
import com.spriteservice.domain.repository.AuthRepository
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject

/**
 * Use case for signing in with email.
 * 使用電子郵件登入的 Use Case。
 */
class SignInWithEmailUseCase @Inject constructor(
    private val authRepository: AuthRepository
) {
    suspend operator fun invoke(email: String, password: String): Result<User> {
        if (email.isBlank()) {
            return Result.failure(IllegalArgumentException("Email cannot be empty"))
        }
        if (password.length < 6) {
            return Result.failure(IllegalArgumentException("Password must be at least 6 characters"))
        }
        return authRepository.signInWithEmail(email, password)
    }
}

/**
 * Use case for signing up with email.
 * 使用電子郵件註冊的 Use Case。
 */
class SignUpWithEmailUseCase @Inject constructor(
    private val authRepository: AuthRepository
) {
    suspend operator fun invoke(email: String, password: String, confirmPassword: String): Result<User> {
        if (email.isBlank()) {
            return Result.failure(IllegalArgumentException("Email cannot be empty"))
        }
        if (password.length < 6) {
            return Result.failure(IllegalArgumentException("Password must be at least 6 characters"))
        }
        if (password != confirmPassword) {
            return Result.failure(IllegalArgumentException("Passwords do not match"))
        }
        return authRepository.signUpWithEmail(email, password)
    }
}

/**
 * Use case for signing in with Google.
 * 使用 Google 登入的 Use Case。
 */
class SignInWithGoogleUseCase @Inject constructor(
    private val authRepository: AuthRepository
) {
    suspend operator fun invoke(idToken: String): Result<User> {
        return authRepository.signInWithGoogle(idToken)
    }
}

/**
 * Use case for signing out.
 * 登出的 Use Case。
 */
class SignOutUseCase @Inject constructor(
    private val authRepository: AuthRepository
) {
    suspend operator fun invoke() {
        authRepository.signOut()
    }
}

/**
 * Use case for observing current user.
 * 觀察當前用戶的 Use Case。
 */
class ObserveCurrentUserUseCase @Inject constructor(
    private val authRepository: AuthRepository
) {
    operator fun invoke(): Flow<User?> {
        return authRepository.currentUser
    }
}

/**
 * Use case for sending password reset email.
 * 發送密碼重設郵件的 Use Case。
 */
class SendPasswordResetEmailUseCase @Inject constructor(
    private val authRepository: AuthRepository
) {
    suspend operator fun invoke(email: String): Result<Unit> {
        if (email.isBlank()) {
            return Result.failure(IllegalArgumentException("Email cannot be empty"))
        }
        return authRepository.sendPasswordResetEmail(email)
    }
}
