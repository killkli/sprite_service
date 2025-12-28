package com.spriteservice.domain.model

/**
 * Domain model for User.
 * 用戶領域模型。
 */
data class User(
    val uid: String,
    val email: String?,
    val displayName: String?,
    val photoUrl: String?,
    val isEmailVerified: Boolean
)
