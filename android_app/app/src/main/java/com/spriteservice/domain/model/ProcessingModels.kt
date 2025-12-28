package com.spriteservice.domain.model

import java.util.Date

/**
 * Result from uploading an image.
 * 上傳圖片的結果。
 */
data class UploadResult(
    val taskId: String,
    val message: String
)

/**
 * Processing status of a task.
 * 任務的處理狀態。
 */
data class ProcessingStatus(
    val taskId: String,
    val status: String,
    val progress: Int?,
    val message: String?,
    val error: String?,
    val spriteCount: Int?,
    val sizes: List<String>?
) {
    val isComplete: Boolean
        get() = status == "SUCCESS"

    val isFailed: Boolean
        get() = status == "FAILURE"

    val isPending: Boolean
        get() = status == "PENDING" || status == "STARTED"
}

/**
 * Processing history record.
 * 處理歷史記錄。
 */
data class ProcessingHistory(
    val taskId: String,
    val originalFilename: String,
    val status: String,
    val spriteCount: Int?,
    val sizes: List<String>?,
    val localZipPath: String?,
    val createdAt: Date,
    val completedAt: Date?,
    val errorMessage: String?
)
