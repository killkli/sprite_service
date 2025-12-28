package com.spriteservice.di

import com.spriteservice.data.repository.AuthRepositoryImpl
import com.spriteservice.data.repository.SpriteRepositoryImpl
import com.spriteservice.data.repository.SubscriptionRepositoryImpl
import com.spriteservice.domain.repository.AuthRepository
import com.spriteservice.domain.repository.SpriteRepository
import com.spriteservice.domain.repository.SubscriptionRepository
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

/**
 * Hilt module for repository bindings.
 * Repository 綁定的 Hilt 模組。
 */
@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {

    @Binds
    @Singleton
    abstract fun bindAuthRepository(
        impl: AuthRepositoryImpl
    ): AuthRepository

    @Binds
    @Singleton
    abstract fun bindSpriteRepository(
        impl: SpriteRepositoryImpl
    ): SpriteRepository

    @Binds
    @Singleton
    abstract fun bindSubscriptionRepository(
        impl: SubscriptionRepositoryImpl
    ): SubscriptionRepository
}
