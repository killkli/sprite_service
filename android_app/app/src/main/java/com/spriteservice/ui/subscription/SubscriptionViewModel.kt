package com.spriteservice.ui.subscription

import android.app.Activity
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.spriteservice.domain.model.SubscriptionPlan
import com.spriteservice.domain.model.SubscriptionStatus
import com.spriteservice.domain.repository.SubscriptionRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * UI state for subscription screen.
 * 訂閱畫面的 UI 狀態。
 */
data class SubscriptionUiState(
    val currentStatus: SubscriptionStatus = SubscriptionStatus.FREE,
    val availablePlans: List<SubscriptionPlan> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null
)

/**
 * ViewModel for subscription screen.
 * 訂閱畫面的 ViewModel。
 */
@HiltViewModel
class SubscriptionViewModel @Inject constructor(
    private val subscriptionRepository: SubscriptionRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(SubscriptionUiState())
    val uiState: StateFlow<SubscriptionUiState> = _uiState.asStateFlow()

    private var selectedPlan: SubscriptionPlan? = null

    init {
        loadSubscriptionData()
    }

    private fun loadSubscriptionData() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true) }

            // Initialize billing
            subscriptionRepository.initializeBilling()

            // Query current subscription
            subscriptionRepository.queryCurrentSubscription()

            // Query available plans
            subscriptionRepository.queryAvailableSubscriptions()

            // Observe status changes
            subscriptionRepository.subscriptionStatus.collect { status ->
                _uiState.update { it.copy(currentStatus = status) }
            }
        }

        viewModelScope.launch {
            subscriptionRepository.availablePlans.collect { plans ->
                _uiState.update { it.copy(availablePlans = plans, isLoading = false) }
            }
        }
    }

    fun selectPlan(plan: SubscriptionPlan) {
        selectedPlan = plan
        // The actual purchase will be launched from the Activity
        // 實際的購買將從 Activity 啟動
    }

    fun launchPurchase(activity: Activity) {
        val plan = selectedPlan ?: return

        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }

            subscriptionRepository.launchPurchaseFlow(activity, plan.productId)
                .onSuccess {
                    // Purchase flow launched successfully
                    // 購買流程已成功啟動
                    _uiState.update { it.copy(isLoading = false) }
                }
                .onFailure { error ->
                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            error = error.message ?: "Purchase failed"
                        )
                    }
                }
        }
    }
}
