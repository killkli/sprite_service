package com.spriteservice.domain.repository

import android.app.Activity
import com.spriteservice.domain.model.SubscriptionPlan
import com.spriteservice.domain.model.SubscriptionStatus
import kotlinx.coroutines.flow.StateFlow

/**
 * Repository interface for subscription operations.
 * 訂閱操作的 Repository 介面。
 */
interface SubscriptionRepository {

    /**
     * Current subscription status.
     * 當前訂閱狀態。
     */
    val subscriptionStatus: StateFlow<SubscriptionStatus>

    /**
     * Available subscription plans.
     * 可用的訂閱方案。
     */
    val availablePlans: StateFlow<List<SubscriptionPlan>>

    /**
     * Initialize billing client.
     * 初始化計費客戶端。
     */
    suspend fun initializeBilling(): Result<Unit>

    /**
     * Query available subscription plans.
     * 查詢可用的訂閱方案。
     */
    suspend fun queryAvailableSubscriptions(): Result<List<SubscriptionPlan>>

    /**
     * Launch purchase flow for a subscription.
     * 啟動訂閱購買流程。
     */
    suspend fun launchPurchaseFlow(activity: Activity, productId: String): Result<Unit>

    /**
     * Query current active subscription.
     * 查詢當前有效訂閱。
     */
    suspend fun queryCurrentSubscription(): Result<SubscriptionStatus>

    /**
     * Get daily processing limit based on subscription.
     * 根據訂閱取得每日處理限制。
     */
    fun getDailyLimit(): Int
}
