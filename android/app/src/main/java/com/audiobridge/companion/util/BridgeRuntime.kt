package com.audiobridge.companion.util

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

object BridgeRuntime {
    private val _status = MutableStateFlow("Idle")
    val status: StateFlow<String> = _status

    fun update(s: String) {
        _status.value = s
    }
}
