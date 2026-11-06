package com.audiobridge.companion.viewmodel

import android.app.Activity
import android.content.Context
import android.content.Intent
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.audiobridge.companion.model.CaptureStatus
import com.audiobridge.companion.model.ConnectionStatus
import com.audiobridge.companion.model.StreamingStatus
import com.audiobridge.companion.service.AudioCaptureService
import com.audiobridge.companion.util.BridgeRuntime
import com.audiobridge.companion.util.Prefs
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue

class BridgeViewModel(app: android.app.Application) : AndroidViewModel(app) {

    val prefs = Prefs(app)

    var ip by mutableStateOf(prefs.getIp())
    var port by mutableStateOf(prefs.getPort().toString())
    var token by mutableStateOf(prefs.getToken())
    var deviceName by mutableStateOf(prefs.getDeviceName())

    var networkMessage by mutableStateOf("Idle")
    var captureStatus by mutableStateOf(CaptureStatus.IDLE.name)
    var connectionStatus by mutableStateOf(ConnectionStatus.DISCONNECTED.name)

    init {
        viewModelScope.launch {
            BridgeRuntime.status.collectLatest { msg ->
                networkMessage = msg
            }
        }
    }

    fun setIp(v: String) { ip = v }
    fun setPort(v: String) { port = v }
    fun setToken(v: String) { token = v }
    fun setDeviceName(v: String) { deviceName = v }

    fun saveSettings() {
        prefs.setIp(ip)
        prefs.setPort(port.toIntOrNull() ?: 8766)
        prefs.setToken(token)
        prefs.setDeviceName(deviceName)
    }

    fun onCaptureStarted() {
        captureStatus = CaptureStatus.CAPTURING.name
    }

    fun onCaptureDenied() {
        captureStatus = CaptureStatus.PERMISSION_REQUIRED.name
    }

    fun disconnect(activity: Activity) {
        val intent = Intent(activity, AudioCaptureService::class.java)
        activity.stopService(intent)
        captureStatus = CaptureStatus.IDLE.name
    }
}
