package com.spriteservice.domain.model

/**
 * Subscription status enum.
 * 訂閱狀態列舉。
 */
enum class SubscriptionStatus {
    FREE,   // 免費用戶
    BASIC,  // 基礎訂閱
    PRO     // 專業訂閱
}

/**
 * Subscription plan details.
 * 訂閱方案詳情。
 */
data class SubscriptionPlan(
    val productId: String,
    val name: String,
    val description: String,
    val price: String,
    val priceMicros: Long,
    val billingPeriod: String
) {
    /**
     * Get daily limit for this plan.
     * 取得此方案的每日限制。
     */
    val dailyLimit: Int
        get() = when (productId) {
            "sprite_basic_monthly" -> 30
            "sprite_pro_monthly" -> Int.MAX_VALUE
            else -> 3
        }

    /**
     * Check if this plan has watermark.
     * 檢查此方案是否有浮水印。
     */
    val hasWatermark: Boolean
        get() = productId != "sprite_basic_monthly" && productId != "sprite_pro_monthly"
}
