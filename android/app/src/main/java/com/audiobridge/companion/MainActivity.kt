package com.audiobridge.companion

import android.app.Application
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.ui.platform.setViewContentObserver
import com.audiobridge.companion.ui.MainScreen
import com.audiobridge.companion.viewmodel.BridgeViewModel

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val app = applicationContext as Application
        val viewModel = BridgeViewModel(app)
        setContent {
            AudioBridgeTheme {
                MainScreen(viewModel, this@MainActivity)
            }
        }
    }
}