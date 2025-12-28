package com.spriteservice.di

import android.content.Context
import androidx.room.Room
import com.spriteservice.data.local.SpriteDatabase
import com.spriteservice.data.local.dao.ProcessingHistoryDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

/**
 * Hilt module for database-related dependencies.
 * 資料庫相關依賴的 Hilt 模組。
 */
@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideSpriteDatabase(
        @ApplicationContext context: Context
    ): SpriteDatabase {
        return Room.databaseBuilder(
            context,
            SpriteDatabase::class.java,
            "sprite_database"
        )
            .fallbackToDestructiveMigration()
            .build()
    }

    @Provides
    @Singleton
    fun provideProcessingHistoryDao(database: SpriteDatabase): ProcessingHistoryDao {
        return database.processingHistoryDao()
    }
}
