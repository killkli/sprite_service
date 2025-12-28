package com.spriteservice.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.spriteservice.domain.usecase.SignInWithEmailUseCase
import com.spriteservice.domain.usecase.SignInWithGoogleUseCase
import com.spriteservice.domain.usecase.SignUpWithEmailUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * UI state for login screen.
 * 登入畫面的 UI 狀態。
 */
sealed class LoginUiState {
    data object Idle : LoginUiState()
    data object Loading : LoginUiState()
    data object Success : LoginUiState()
    data class Error(val message: String) : LoginUiState()
}

/**
 * ViewModel for login screen.
 * 登入畫面的 ViewModel。
 */
@HiltViewModel
class LoginViewModel @Inject constructor(
    private val signInWithEmailUseCase: SignInWithEmailUseCase,
    private val signUpWithEmailUseCase: SignUpWithEmailUseCase,
    private val signInWithGoogleUseCase: SignInWithGoogleUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow<LoginUiState>(LoginUiState.Idle)
    val uiState: StateFlow<LoginUiState> = _uiState.asStateFlow()

    fun signIn(email: String, password: String) {
        viewModelScope.launch {
            _uiState.value = LoginUiState.Loading

            signInWithEmailUseCase(email, password)
                .onSuccess {
                    _uiState.value = LoginUiState.Success
                }
                .onFailure { error ->
                    _uiState.value = LoginUiState.Error(error.message ?: "Sign in failed")
                }
        }
    }

    fun signUp(email: String, password: String, confirmPassword: String) {
        viewModelScope.launch {
            _uiState.value = LoginUiState.Loading

            signUpWithEmailUseCase(email, password, confirmPassword)
                .onSuccess {
                    _uiState.value = LoginUiState.Success
                }
                .onFailure { error ->
                    _uiState.value = LoginUiState.Error(error.message ?: "Sign up failed")
                }
        }
    }

    fun signInWithGoogle() {
        // TODO: Implement Google Sign-In flow
        // This requires Activity context for Google Sign-In intent
        // 需要 Activity context 來啟動 Google 登入流程
        _uiState.value = LoginUiState.Error("Google Sign-In not yet implemented")
    }
}
