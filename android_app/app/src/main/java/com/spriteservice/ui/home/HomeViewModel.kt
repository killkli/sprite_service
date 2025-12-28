package com.spriteservice.ui.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.spriteservice.domain.model.ProcessingHistory
import com.spriteservice.domain.repository.SpriteRepository
import com.spriteservice.domain.repository.SubscriptionRepository
import com.spriteservice.domain.usecase.ProcessImageUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * UI state for home screen.
 * 主畫面的 UI 狀態。
 */
data class HomeUiState(
    val history: List<ProcessingHistory> = emptyList(),
    val remainingCount: Int = 0,
    val dailyLimit: Int = 3,
    val isLoading: Boolean = false
)

/**
 * ViewModel for home screen.
 * 主畫面的 ViewModel。
 */
@HiltViewModel
class HomeViewModel @Inject constructor(
    private val spriteRepository: SpriteRepository,
    private val subscriptionRepository: SubscriptionRepository,
    private val processImageUseCase: ProcessImageUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow(HomeUiState())
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    init {
        loadHistory()
        loadUsageInfo()
    }

    private fun loadHistory() {
        viewModelScope.launch {
            spriteRepository.getProcessingHistory().collect { history ->
                _uiState.update { it.copy(history = history) }
            }
        }
    }

    private fun loadUsageInfo() {
        viewModelScope.launch {
            val remaining = processImageUseCase.getRemainingCount()
            val limit = subscriptionRepository.getDailyLimit()

            _uiState.update {
                it.copy(
                    remainingCount = remaining,
                    dailyLimit = limit
                )
            }
        }
    }

    fun refresh() {
        loadUsageInfo()
    }
}
