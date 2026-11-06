package com.audiobridge.companion.network

import java.nio.ByteBuffer
import java.nio.ByteOrder

object PacketPacker {
    private const val MAGIC_0: Byte = 0xAB.toByte()
    private const val MAGIC_1: Byte = 0x01.toByte()
    private const val MSG_TYPE_PCM: Byte = 0x02

    fun pack(pcm: ByteArray, seq: Int, timestampMs: Long, channels: Int = 2): ByteArray {
        val buffer = ByteBuffer.allocate(16 + pcm.size)

        buffer.put(MAGIC_0)
        buffer.put(MAGIC_1)
        buffer.put(MSG_TYPE_PCM)
        buffer.put(channels.toByte())
        buffer.putInt(seq)
        buffer.putLong(timestampMs)
        buffer.put(pcm)
        return buffer.array()
    }
}
