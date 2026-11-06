package com.audiobridge.companion.service

import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import com.audiobridge.companion.util.BridgeRuntime
import com.audiobridge.companion.util.Prefs
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

class AudioCaptureService : Service() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private lateinit var prefs: Prefs
    private lateinit var bridgeClient: com.audiobridge.companion.network.BridgeClient
    private var running = false

    override fun onCreate() {
        super.onCreate()
        prefs = Prefs(this)
        bridgeClient = com.audiobridge.companion.network.BridgeClient(scope, prefs) { _, msg ->
            BridgeRuntime.update(msg)
        }
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val resultCode = intent?.getIntExtra(EXTRA_RESULT_CODE, 0) ?: 0
        val resultData = intent?.getParcelableExtra<Intent>(EXTRA_RESULT_DATA)

        startForegroundCompat()

        if (resultCode != 0 && resultData != null && mediaProjection == null) {
            val mgr = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as android.media.projection.MediaProjectionManager
            mediaProjection = mgr.getMediaProjection(resultCode, resultData)
            mediaProjection?.registerCallback(object : android.media.projection.MediaProjection.Callback() {
                override fun onStop() { stopCapture("Media projection stopped") }
            }, null)
        }

        if (mediaProjection == null) {
            BridgeRuntime.update("Capture permission required")
            stopSelf()
            return START_NOT_STICKY
        }

        if (!running) {
            running = true
            bridgeClient.connect()
            startCapture()
        }

        return START_STICKY
    }

    private var mediaProjection: android.media.projection.MediaProjection? = null
    private var audioRecord: android.media.AudioRecord? = null
    private var captureJob: kotlinx.coroutines.Job? = null

    private fun startForegroundCompat() {
        val notification = androidx.core.app.NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("AUDIO BRIDGE")
            .setContentText("Streaming audio to laptop")
            .setSmallIcon(com.audiobridge.companion.R.drawable.ic_launcher)
            .setOngoing(true)
            .build()
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun startCapture() {
        val projection = mediaProjection ?: return
        val captureConfig = android.media.AudioPlaybackCaptureConfiguration.Builder(projection)
            .addMatchingUsage(android.media.AudioAttributes.USAGE_MEDIA)
            .addMatchingUsage(android.media.AudioAttributes.USAGE_GAME)
            .addMatchingUsage(android.media.AudioAttributes.USAGE_UNKNOWN)
            .build()

        val format = android.media.AudioFormat.Builder()
            .setEncoding(android.media.AudioFormat.ENCODING_PCM_16BIT)
            .setSampleRate(SAMPLE_RATE)
            .setChannelMask(android.media.AudioFormat.CHANNEL_IN_STEREO)
            .build()

        val minBuf = android.media.AudioRecord.getMinBufferSize(
            SAMPLE_RATE,
            android.media.AudioFormat.CHANNEL_IN_STEREO,
            android.media.AudioFormat.ENCODING_PCM_16BIT
        )
        val record = android.media.AudioRecord.Builder()
            .setAudioFormat(format)
            .setBufferSizeInBytes(minBuf * 2)
            .setAudioPlaybackCaptureConfig(captureConfig)
            .build()

        audioRecord = record
        record.startRecording()
        BridgeRuntime.update("Capturing audio")

        captureJob = scope.launch {
            val shortBuf = ShortArray(FRAME_SAMPLES * CHANNELS)
            while (running) {
                val read = record.read(shortBuf, 0, shortBuf.size)
                if (read > 0) {
                    val byteBuf = java.nio.ByteBuffer.allocate(read * 2).order(java.nio.ByteOrder.LITTLE_ENDIAN)
                    for (i in 0 until read) byteBuf.putShort(shortBuf[i])
                    bridgeClient.sendPcm(byteBuf.array())
                } else if (read < 0) {
                    BridgeRuntime.update("Audio capture error: $read")
                    break
                }
            }
        }
    }

    private fun stopCapture(reason: String) {
        running = false
        captureJob?.cancel()
        try { audioRecord?.stop() } catch (_: Exception) {}
        audioRecord?.release()
        audioRecord = null
        mediaProjection?.stop()
        mediaProjection = null
        bridgeClient.disconnect()
        BridgeRuntime.update(reason)
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        stopCapture("Service destroyed")
        scope.cancel()
        super.onDestroy()
    }

    private fun createNotificationChannel() {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            val channel = android.app.NotificationChannel(
                CHANNEL_ID,
                "AUDIO BRIDGE",
                android.app.NotificationManager.IMPORTANCE_LOW
            )
            getSystemService(android.app.NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        const val EXTRA_RESULT_CODE = "result_code"
        const val EXTRA_RESULT_DATA = "result_data"
        const val CHANNEL_ID = "audio_bridge_channel"
        const val NOTIFICATION_ID = 1001
        const val SAMPLE_RATE = 48000
        const val CHANNELS = 2
        const val FRAME_SAMPLES = 1024
    }
}
