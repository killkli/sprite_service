package com.spriteservice.ui.upload

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CloudUpload
import androidx.compose.material.icons.filled.Done
import androidx.compose.material.icons.filled.Error
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import coil.compose.AsyncImage

/**
 * Upload screen composable.
 * 上傳畫面。
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun UploadScreen(
    onNavigateBack: () -> Unit,
    viewModel: UploadViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    val imagePickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let { viewModel.selectImage(it) }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Process Sprite") },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Image preview / picker
            ImagePickerBox(
                selectedImageUri = uiState.selectedImageUri,
                isEnabled = uiState is UploadUiState.Idle || uiState is UploadUiState.ImageSelected,
                onClick = { imagePickerLauncher.launch("image/*") },
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(1f)
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Status display
            when (val state = uiState) {
                is UploadUiState.Idle -> {
                    Text(
                        text = "Select an image to process",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                is UploadUiState.ImageSelected -> {
                    Button(
                        onClick = { viewModel.startProcessing() },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Start Processing")
                    }
                }

                is UploadUiState.Uploading -> {
                    ProcessingIndicator(
                        message = "Uploading...",
                        progress = null
                    )
                }

                is UploadUiState.Processing -> {
                    ProcessingIndicator(
                        message = state.message ?: "Processing...",
                        progress = state.progress?.toFloat()?.div(100)
                    )
                }

                is UploadUiState.Success -> {
                    SuccessDisplay(
                        spriteCount = state.spriteCount,
                        onDownload = { viewModel.downloadResult() },
                        onDone = onNavigateBack
                    )
                }

                is UploadUiState.Error -> {
                    ErrorDisplay(
                        message = state.message,
                        onRetry = { viewModel.reset() }
                    )
                }
            }
        }
    }
}

@Composable
private fun ImagePickerBox(
    selectedImageUri: Uri?,
    isEnabled: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(16.dp))
            .border(
                width = 2.dp,
                color = MaterialTheme.colorScheme.outline,
                shape = RoundedCornerShape(16.dp)
            )
            .clickable(enabled = isEnabled, onClick = onClick),
        contentAlignment = Alignment.Center
    ) {
        if (selectedImageUri != null) {
            AsyncImage(
                model = selectedImageUri,
                contentDescription = "Selected image",
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Fit
            )
        } else {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                Icon(
                    imageVector = Icons.Default.CloudUpload,
                    contentDescription = null,
                    modifier = Modifier.size(64.dp),
                    tint = MaterialTheme.colorScheme.primary
                )

                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    text = "Tap to select image",
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun ProcessingIndicator(
    message: String,
    progress: Float?,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        if (progress != null) {
            LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier.fillMaxWidth()
            )
        } else {
            CircularProgressIndicator()
        }

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = message,
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun SuccessDisplay(
    spriteCount: Int,
    onDownload: () -> Unit,
    onDone: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(
            imageVector = Icons.Default.Done,
            contentDescription = null,
            modifier = Modifier.size(64.dp),
            tint = MaterialTheme.colorScheme.primary
        )

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = "Processing Complete!",
            style = MaterialTheme.typography.titleLarge
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = "$spriteCount sprites extracted",
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(24.dp))

        Button(
            onClick = onDownload,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Download Sprites")
        }

        Spacer(modifier = Modifier.height(8.dp))

        Button(
            onClick = onDone,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Done")
        }
    }
}

@Composable
private fun ErrorDisplay(
    message: String,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(
            imageVector = Icons.Default.Error,
            contentDescription = null,
            modifier = Modifier.size(64.dp),
            tint = MaterialTheme.colorScheme.error
        )

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = "Processing Failed",
            style = MaterialTheme.typography.titleLarge,
            color = MaterialTheme.colorScheme.error
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = message,
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(24.dp))

        Button(
            onClick = onRetry,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Try Again")
        }
    }
}
