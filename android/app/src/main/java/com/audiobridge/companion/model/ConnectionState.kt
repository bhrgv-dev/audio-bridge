package com.audiobridge.companion.model

enum class ConnectionStatus { DISCONNECTED, CONNECTING, CONNECTED, ERROR }
enum class CaptureStatus { IDLE, PERMISSION_REQUIRED, READY, CAPTURING, ERROR }
enum class StreamingStatus { IDLE, STREAMING, STOPPED, ERROR }
