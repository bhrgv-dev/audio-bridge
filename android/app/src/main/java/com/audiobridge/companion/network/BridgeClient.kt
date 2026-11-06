package com.audiobridge.companion.network

import com.audiobridge.companion.model.ConnectionStatus
import com.audiobridge.companion.util.Prefs
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeout
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.toByteString

import org.json.JSONObject
import java.util.concurrent.TimeUnit

class BridgeClient(
    private val scope: CoroutineScope,
    private val prefs: Prefs,
    private val onStatus: (ConnectionStatus, String) -> Unit
) {
    private val client = OkHttpClient.Builder()
        .pingInterval(20, TimeUnit.SECONDS)
        .build()

    private var socket: WebSocket? = null
    private var disconnectSignal: CompletableDeferred<Unit>? = null
    private var running = false
    private var connected = false
    private var seq = 0

    val isConnected: Boolean get() = connected

    fun connect() {
        if (running) return
        running = true
        scope.launch { runLoop() }
    }

    fun disconnect() {
        running = false
        connected = false
        try { socket?.close(1000, "Client disconnect") } catch (_: Exception) {}
        socket = null
    }

    fun sendPcm(pcm: ByteArray) {
        val s = socket ?: return
        if (!connected) return
        val packet = PacketPacker.pack(pcm, seq++, System.currentTimeMillis(), 2)
        s.send(packet.toByteString())
        if (seq < 0) seq = 0
    }

    private suspend fun runLoop() {
        var attempt = 0
        while (running) {
            onStatus(ConnectionStatus.CONNECTING, "Connecting to ${prefs.getIp()}:${prefs.getPort()}")
            val ok = connectOnce()
            if (ok) {
                attempt = 0
                disconnectSignal?.await()
            }
            if (!running) break
            attempt++
            if (attempt > 6) {
                onStatus(ConnectionStatus.ERROR, "Max reconnection attempts reached")
                running = false
                break
            }
            val delayMs = (1000L * (1 shl minOf(attempt, 4))).coerceAtMost(16000L)
            onStatus(ConnectionStatus.CONNECTING, "Reconnecting in ${delayMs / 1000}s")
            delay(delayMs)
        }
        onStatus(ConnectionStatus.DISCONNECTED, "Disconnected")
    }

    private suspend fun connectOnce(): Boolean {
        val url = "ws://${prefs.getIp()}:${prefs.getPort()}"
        val handshake = JSONObject()
        handshake.put("type", "HANDSHAKE")
        handshake.put("token", prefs.getToken())
        handshake.put("deviceName", prefs.getDeviceName())
        handshake.put("sampleRate", 48000)
        handshake.put("channels", 2)
        handshake.put("version", 1)

        val deferred = CompletableDeferred<Boolean>()
        disconnectSignal = CompletableDeferred()

        val listener = object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                webSocket.send(handshake.toString())
                scope.launch {
                    delay(1000)
                    if (webSocket === socket && !deferred.isCompleted) {
                        connected = true
                        onStatus(ConnectionStatus.CONNECTED, "Connected")
                        deferred.complete(true)
                    }
                }
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                try {
                    val obj = JSONObject(text)
                    if (obj.optString("type") == "HANDSHAKE_REJECT") {
                        val reason = obj.optString("reason", "UNAUTHORIZED")
                        connected = false
                        onStatus(ConnectionStatus.ERROR, "Authentication failed: $reason")
                        if (!deferred.isCompleted) deferred.complete(false)
                        disconnectSignal?.complete(Unit)
                        webSocket.close(4401, reason)
                    }
                } catch (_: Exception) {
                }
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                connected = false
                socket = null
                if (!deferred.isCompleted) deferred.complete(false)
                disconnectSignal?.complete(Unit)
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                connected = false
                socket = null
                onStatus(ConnectionStatus.ERROR, t.message ?: "Network error")
                if (!deferred.isCompleted) deferred.complete(false)
                disconnectSignal?.complete(Unit)
            }
        }

        socket = client.newWebSocket(Request.Builder().url(url).build(), listener)
        return withTimeout(5000L) { deferred.await() }
    }
}
