package com.spriteservice.domain.repository

import com.spriteservice.domain.model.ProcessingHistory
import com.spriteservice.domain.model.ProcessingStatus
import com.spriteservice.domain.model.UploadResult
import kotlinx.coroutines.flow.Flow
import java.io.File

/**
 * Repository interface for sprite processing operations.
 * Sprite 處理操作的 Repository 介面。
 */
interface SpriteRepository {

    /**
     * Upload an image for processing.
     * 上傳圖片進行處理。
     */
    suspend fun uploadImage(file: File): Result<UploadResult>

    /**
     * Get the processing status of a task.
     * 取得任務的處理狀態。
     */
    suspend fun getProcessingStatus(taskId: String): Result<ProcessingStatus>

    /**
     * Download the processed sprites.
     * 下載處理完成的 sprites。
     */
    suspend fun downloadSprites(taskId: String): Result<File>

    /**
     * Get processing history.
     * 取得處理歷史記錄。
     */
    fun getProcessingHistory(): Flow<List<ProcessingHistory>>

    /**
     * Get today's processing count.
     * 取得今日處理次數。
     */
    suspend fun getTodayProcessingCount(): Int

    /**
     * Delete a history record.
     * 刪除歷史記錄。
     */
    suspend fun deleteHistory(taskId: String)
}
