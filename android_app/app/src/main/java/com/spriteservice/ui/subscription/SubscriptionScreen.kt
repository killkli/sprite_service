package com.spriteservice.ui.subscription

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.spriteservice.domain.model.SubscriptionPlan
import com.spriteservice.domain.model.SubscriptionStatus

/**
 * Subscription screen composable.
 * 訂閱畫面。
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SubscriptionScreen(
    onNavigateBack: () -> Unit,
    viewModel: SubscriptionViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Subscription") },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { paddingValues ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Current status card
            item {
                CurrentStatusCard(
                    status = uiState.currentStatus,
                    modifier = Modifier.fillMaxWidth()
                )
            }

            item {
                Text(
                    text = "Choose a Plan",
                    style = MaterialTheme.typography.titleLarge,
                    modifier = Modifier.padding(vertical = 8.dp)
                )
            }

            // Free plan
            item {
                PlanCard(
                    title = "Free",
                    price = "Free",
                    features = listOf(
                        "3 conversions per day",
                        "Basic sizes output",
                        "Watermark included"
                    ),
                    isCurrentPlan = uiState.currentStatus == SubscriptionStatus.FREE,
                    onSelect = { /* Free is default */ },
                    modifier = Modifier.fillMaxWidth()
                )
            }

            // Subscription plans
            items(uiState.availablePlans) { plan ->
                PlanCard(
                    title = plan.name,
                    price = plan.price,
                    features = getPlanFeatures(plan),
                    isCurrentPlan = isCurrentPlan(plan, uiState.currentStatus),
                    onSelect = { viewModel.selectPlan(plan) },
                    isRecommended = plan.productId == "sprite_pro_monthly",
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }
    }
}

@Composable
private fun CurrentStatusCard(
    status: SubscriptionStatus,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = Icons.Default.Star,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onPrimaryContainer
            )

            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(start = 16.dp)
            ) {
                Text(
                    text = "Current Plan",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )

                Text(
                    text = status.name,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )
            }
        }
    }
}

@Composable
private fun PlanCard(
    title: String,
    price: String,
    features: List<String>,
    isCurrentPlan: Boolean,
    onSelect: () -> Unit,
    modifier: Modifier = Modifier,
    isRecommended: Boolean = false
) {
    val cardColors = if (isRecommended) {
        CardDefaults.outlinedCardColors(
            containerColor = MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.3f)
        )
    } else {
        CardDefaults.outlinedCardColors()
    }

    val border = if (isRecommended) {
        BorderStroke(2.dp, MaterialTheme.colorScheme.primary)
    } else {
        BorderStroke(1.dp, MaterialTheme.colorScheme.outline)
    }

    OutlinedCard(
        modifier = modifier,
        colors = cardColors,
        border = border
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            if (isRecommended) {
                Text(
                    text = "RECOMMENDED",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold
                )

                Spacer(modifier = Modifier.height(4.dp))
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold
                )

                Text(
                    text = price,
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.primary
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            features.forEach { feature ->
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.padding(vertical = 4.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Check,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary
                    )

                    Text(
                        text = feature,
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.padding(start = 8.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            Button(
                onClick = onSelect,
                enabled = !isCurrentPlan,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(if (isCurrentPlan) "Current Plan" else "Select")
            }
        }
    }
}

private fun getPlanFeatures(plan: SubscriptionPlan): List<String> {
    return when (plan.productId) {
        "sprite_basic_monthly" -> listOf(
            "30 conversions per day",
            "All sizes output",
            "No watermark"
        )

        "sprite_pro_monthly" -> listOf(
            "Unlimited conversions",
            "Batch processing",
            "Priority queue",
            "API access"
        )

        else -> listOf()
    }
}

private fun isCurrentPlan(plan: SubscriptionPlan, status: SubscriptionStatus): Boolean {
    return when (plan.productId) {
        "sprite_basic_monthly" -> status == SubscriptionStatus.BASIC
        "sprite_pro_monthly" -> status == SubscriptionStatus.PRO
        else -> false
    }
}
