package com.audiobridge.companion.ui

import android.app.Activity
import android.content.Intent
import android.media.projection.MediaProjectionManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.audiobridge.companion.service.AudioCaptureService
import com.audiobridge.companion.viewmodel.BridgeViewModel

@Composable
fun MainScreen(viewModel: BridgeViewModel, activity: Activity) {
    val networkMessage = viewModel.networkMessage
    val captureStatus = viewModel.captureStatus

    val projectionManager = activity.getSystemService(MediaProjectionManager::class.java)
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            val intent = Intent(activity, AudioCaptureService::class.java).apply {
                putExtra(AudioCaptureService.EXTRA_RESULT_CODE, result.resultCode)
                putExtra(AudioCaptureService.EXTRA_RESULT_DATA, result.data)
            }
            activity.startForegroundService(intent)
            viewModel.onCaptureStarted()
        } else {
            viewModel.onCaptureDenied()
        }
    }

    Scaffold(containerColor = Color(0xFF050505)) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text("AUDIO BRIDGE", style = MaterialTheme.typography.headlineMedium, color = Color.White)
            Text("Universal Dual Audio Companion", style = MaterialTheme.typography.bodySmall, color = Color.Gray)

            StatusCard("Network", networkMessage)
            StatusCard("Capture", captureStatus)

            OutlinedTextField(
                value = viewModel.ip,
                onValueChange = { viewModel.ip = it },
                label = { Text("Laptop IP") },
                modifier = Modifier.fillMaxWidth(),
                colors = darkFieldColors()
            )
            OutlinedTextField(
                value = viewModel.port,
                onValueChange = { viewModel.port = it },
                label = { Text("Port") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.fillMaxWidth(),
                colors = darkFieldColors()
            )
            OutlinedTextField(
                value = viewModel.token,
                onValueChange = { viewModel.token = it },
                label = { Text("Pairing Token") },
                visualTransformation = PasswordVisualTransformation(),
                modifier = Modifier.fillMaxWidth(),
                colors = darkFieldColors()
            )
            OutlinedTextField(
                value = viewModel.deviceName,
                onValueChange = { viewModel.deviceName = it },
                label = { Text("Device Name") },
                modifier = Modifier.fillMaxWidth(),
                colors = darkFieldColors()
            )

            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(
                    onClick = {
                        viewModel.saveSettings()
                        launcher.launch(projectionManager.createScreenCaptureIntent())
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF10B981))
                ) { Text("Connect") }
                OutlinedButton(onClick = { viewModel.disconnect(activity) }) { Text("Disconnect") }
            }

            Text(
                "Capture only apps that allow playback capture. Audio is not mixed into TWS until Windows capture/mixing is implemented.",
                style = MaterialTheme.typography.bodySmall,
                color = Color.Gray
            )
        }
    }
}

@Composable
private fun StatusCard(title: String, value: String) {
    Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF0A0A0A))) {
        Column(Modifier.padding(12.dp)) {
            Text(title, color = Color.Gray, style = MaterialTheme.typography.labelSmall)
            Text(value, color = Color.White, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
private fun darkFieldColors() = OutlinedTextFieldDefaults.colors(
    focusedBorderColor = Color(0xFF10B981),
    unfocusedBorderColor = Color(0xFF333333),
    focusedLabelColor = Color(0xFF10B981),
    unfocusedLabelColor = Color.Gray,
    cursorColor = Color(0xFF10B981)
)
