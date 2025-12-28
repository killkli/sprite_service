package com.spriteservice.ui.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.spriteservice.domain.model.ProcessingHistory
import java.text.SimpleDateFormat
import java.util.Locale

/**
 * Home screen composable.
 * 主畫面。
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    onNavigateToUpload: () -> Unit,
    onNavigateToSubscription: () -> Unit,
    viewModel: HomeViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Sprite Service") },
                actions = {
                    IconButton(onClick = onNavigateToSubscription) {
                        Icon(Icons.Default.Star, contentDescription = "Subscription")
                    }
                    IconButton(onClick = { /* TODO: Profile */ }) {
                        Icon(Icons.Default.Person, contentDescription = "Profile")
                    }
                }
            )
        },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = onNavigateToUpload,
                icon = { Icon(Icons.Default.Add, contentDescription = null) },
                text = { Text("New Sprite") }
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            // Usage info
            UsageCard(
                remainingCount = uiState.remainingCount,
                dailyLimit = uiState.dailyLimit,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp)
            )

            // History list
            if (uiState.history.isEmpty()) {
                EmptyHistoryMessage(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(16.dp)
                )
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(uiState.history) { item ->
                        HistoryItem(item = item)
                    }
                }
            }
        }
    }
}

@Composable
private fun UsageCard(
    remainingCount: Int,
    dailyLimit: Int,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer
        )
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(
                text = "Today's Usage",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onPrimaryContainer
            )

            Spacer(modifier = Modifier.height(8.dp))

            val used = dailyLimit - remainingCount
            val progress = if (dailyLimit > 0) used.toFloat() / dailyLimit else 0f

            LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(4.dp))

            Text(
                text = "$used / $dailyLimit processed",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onPrimaryContainer
            )
        }
    }
}

@Composable
private fun HistoryItem(
    item: ProcessingHistory,
    modifier: Modifier = Modifier
) {
    val dateFormat = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault())

    Card(
        modifier = modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = item.originalFilename,
                    style = MaterialTheme.typography.titleSmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = dateFormat.format(item.createdAt),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            Spacer(modifier = Modifier.width(8.dp))

            StatusBadge(status = item.status)
        }
    }
}

@Composable
private fun StatusBadge(status: String) {
    val (color, text) = when (status) {
        "SUCCESS" -> MaterialTheme.colorScheme.primary to "Done"
        "FAILURE" -> MaterialTheme.colorScheme.error to "Failed"
        "PENDING", "STARTED" -> MaterialTheme.colorScheme.tertiary to "Processing"
        else -> MaterialTheme.colorScheme.outline to status
    }

    Text(
        text = text,
        style = MaterialTheme.typography.labelMedium,
        color = color
    )
}

@Composable
private fun EmptyHistoryMessage(modifier: Modifier = Modifier) {
    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = "No processing history yet",
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = "Tap the button below to process your first sprite!",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}
