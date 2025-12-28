package com.spriteservice.ui.upload

import android.content.Context
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.spriteservice.domain.usecase.DailyLimitExceededException
import com.spriteservice.domain.usecase.ProcessImageUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.launch
import java.io.File
import java.io.FileOutputStream
import javax.inject.Inject

/**
 * UI state for upload screen.
 * 上傳畫面的 UI 狀態。
 */
sealed class UploadUiState {
    abstract val selectedImageUri: Uri?

    data object Idle : UploadUiState() {
        override val selectedImageUri: Uri? = null
    }

    data class ImageSelected(override val selectedImageUri: Uri) : UploadUiState()

    data class Uploading(override val selectedImageUri: Uri) : UploadUiState()

    data class Processing(
        override val selectedImageUri: Uri,
        val taskId: String,
        val progress: Int? = null,
        val message: String? = null
    ) : UploadUiState()

    data class Success(
        override val selectedImageUri: Uri,
        val taskId: String,
        val spriteCount: Int
    ) : UploadUiState()

    data class Error(
        override val selectedImageUri: Uri?,
        val message: String
    ) : UploadUiState()
}

/**
 * ViewModel for upload screen.
 * 上傳畫面的 ViewModel。
 */
@HiltViewModel
class UploadViewModel @Inject constructor(
    private val processImageUseCase: ProcessImageUseCase,
    @ApplicationContext private val context: Context
) : ViewModel() {

    private val _uiState = MutableStateFlow<UploadUiState>(UploadUiState.Idle)
    val uiState: StateFlow<UploadUiState> = _uiState.asStateFlow()

    private var currentTaskId: String? = null

    fun selectImage(uri: Uri) {
        _uiState.value = UploadUiState.ImageSelected(uri)
    }

    fun startProcessing() {
        val currentState = _uiState.value
        if (currentState !is UploadUiState.ImageSelected) return

        val uri = currentState.selectedImageUri

        viewModelScope.launch {
            _uiState.value = UploadUiState.Uploading(uri)

            try {
                // Copy URI to temp file
                val tempFile = copyUriToTempFile(uri)

                // Upload and get task ID
                val uploadResult = processImageUseCase.uploadImage(tempFile)

                uploadResult.onSuccess { result ->
                    currentTaskId = result.taskId
                    _uiState.value = UploadUiState.Processing(
                        selectedImageUri = uri,
                        taskId = result.taskId
                    )

                    // Start polling for status
                    pollStatus(uri, result.taskId)
                }.onFailure { error ->
                    handleError(uri, error)
                }

                // Clean up temp file
                tempFile.delete()

            } catch (e: Exception) {
                handleError(uri, e)
            }
        }
    }

    private suspend fun pollStatus(uri: Uri, taskId: String) {
        processImageUseCase.pollStatus(taskId)
            .catch { e ->
                _uiState.value = UploadUiState.Error(uri, e.message ?: "Unknown error")
            }
            .collect { status ->
                when {
                    status.isComplete -> {
                        _uiState.value = UploadUiState.Success(
                            selectedImageUri = uri,
                            taskId = taskId,
                            spriteCount = status.spriteCount ?: 0
                        )
                    }

                    status.isFailed -> {
                        _uiState.value = UploadUiState.Error(
                            selectedImageUri = uri,
                            message = status.error ?: "Processing failed"
                        )
                    }

                    else -> {
                        _uiState.value = UploadUiState.Processing(
                            selectedImageUri = uri,
                            taskId = taskId,
                            progress = status.progress,
                            message = status.message
                        )
                    }
                }
            }
    }

    private fun handleError(uri: Uri?, error: Throwable) {
        val message = when (error) {
            is DailyLimitExceededException -> error.message ?: "Daily limit exceeded"
            else -> error.message ?: "An error occurred"
        }
        _uiState.value = UploadUiState.Error(uri, message)
    }

    fun downloadResult() {
        val taskId = currentTaskId ?: return

        viewModelScope.launch {
            processImageUseCase.downloadSprites(taskId)
                .onSuccess { file ->
                    // TODO: Share or open the downloaded file
                    // 可以使用 ShareSheet 或 FileProvider 來分享檔案
                }
                .onFailure { error ->
                    // Show error
                }
        }
    }

    fun reset() {
        currentTaskId = null
        _uiState.value = UploadUiState.Idle
    }

    private fun copyUriToTempFile(uri: Uri): File {
        val inputStream = context.contentResolver.openInputStream(uri)
            ?: throw IllegalArgumentException("Cannot open URI")

        val tempFile = File(context.cacheDir, "upload_${System.currentTimeMillis()}.png")

        inputStream.use { input ->
            FileOutputStream(tempFile).use { output ->
                input.copyTo(output)
            }
        }

        return tempFile
    }
}
