package com.spriteservice.domain.usecase

import com.spriteservice.domain.model.ProcessingStatus
import com.spriteservice.domain.model.UploadResult
import com.spriteservice.domain.repository.SpriteRepository
import com.spriteservice.domain.repository.SubscriptionRepository
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import java.io.File
import javax.inject.Inject

/**
 * Use case for processing an image.
 * 處理圖片的 Use Case。
 */
class ProcessImageUseCase @Inject constructor(
    private val spriteRepository: SpriteRepository,
    private val subscriptionRepository: SubscriptionRepository
) {
    /**
     * Check if user can process more images today.
     * 檢查用戶今日是否還能處理更多圖片。
     */
    suspend fun canProcessToday(): Boolean {
        val todayCount = spriteRepository.getTodayProcessingCount()
        val dailyLimit = subscriptionRepository.getDailyLimit()
        return todayCount < dailyLimit
    }

    /**
     * Get remaining processing count for today.
     * 取得今日剩餘的處理次數。
     */
    suspend fun getRemainingCount(): Int {
        val todayCount = spriteRepository.getTodayProcessingCount()
        val dailyLimit = subscriptionRepository.getDailyLimit()
        return (dailyLimit - todayCount).coerceAtLeast(0)
    }

    /**
     * Upload and process an image.
     * 上傳並處理圖片。
     */
    suspend fun uploadImage(file: File): Result<UploadResult> {
        if (!canProcessToday()) {
            return Result.failure(DailyLimitExceededException())
        }
        return spriteRepository.uploadImage(file)
    }

    /**
     * Poll for processing status until complete.
     * 輪詢處理狀態直到完成。
     */
    fun pollStatus(taskId: String, intervalMs: Long = 2000): Flow<ProcessingStatus> = flow {
        var status: ProcessingStatus
        do {
            val result = spriteRepository.getProcessingStatus(taskId)
            if (result.isFailure) {
                throw result.exceptionOrNull() ?: Exception("Unknown error")
            }
            status = result.getOrThrow()
            emit(status)

            if (!status.isComplete && !status.isFailed) {
                delay(intervalMs)
            }
        } while (!status.isComplete && !status.isFailed)
    }

    /**
     * Download processed sprites.
     * 下載處理完成的 sprites。
     */
    suspend fun downloadSprites(taskId: String): Result<File> {
        return spriteRepository.downloadSprites(taskId)
    }
}

/**
 * Exception for daily limit exceeded.
 * 超出每日限制的例外。
 */
class DailyLimitExceededException : Exception("Daily processing limit exceeded. Please upgrade your subscription.")
