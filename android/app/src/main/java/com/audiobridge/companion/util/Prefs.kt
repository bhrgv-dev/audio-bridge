package com.audiobridge.companion.util

import android.content.Context
import android.content.SharedPreferences

class Prefs(context: Context) {
    private val sp: SharedPreferences =
        context.getSharedPreferences("audio_bridge_prefs", Context.MODE_PRIVATE)

    fun getIp(): String = sp.getString("ip", "") ?: ""
    fun setIp(v: String) = sp.edit().putString("ip", v).apply()

    fun getPort(): Int = sp.getInt("port", 8766)
    fun setPort(v: Int) = sp.edit().putInt("port", v).apply()

    fun getToken(): String = sp.getString("token", "") ?: ""
    fun setToken(v: String) = sp.edit().putString("token", v).apply()

    fun getDeviceName(): String = sp.getString("device_name", "Android Mobile Device") ?: "Android Mobile Device"
    fun setDeviceName(v: String) = sp.edit().putString("device_name", v).apply()
}
