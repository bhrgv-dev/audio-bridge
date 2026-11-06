# AUDIO BRIDGE
### Universal Dual-Device TWS Audio Mixer

A software audio bridge enabling simultaneous audio listening from an Android mobile phone and a Windows PC through **any** standard Bluetooth TWS earbuds or headphones (Hammer, boAt, Noise, JBL, Sony, Samsung, Realme, OnePlus, Apple AirPods, etc.) without requiring hardware Multipoint support.

---

## Dual-Port Network Architecture

AUDIO BRIDGE explicitly separates local UI control from LAN audio ingress to ensure security, low latency, and modularity:

```
┌────────────────────────────────────────────────────────┐
│                   WINDOWS PC                           │
│                                                        │
│  [ React Frontend UI ]                                 │
│         │                                              │
│         │ Local WebSocket (ws://127.0.0.1:8765)        │
│         ▼                                              │
│  [ Desktop Control Server ]                            │
│         │                                              │
│         │ (Internal State & Gain Control)              │
│         ▼                                              │
│  [ Audio Mixer Foundation ] ◄──────┐                   │
│         │                          │                   │
│         ▼                          │ Verified PCM      │
│  [ Windows TWS Output ]            │ Float32 Stream    │
│                                    │                   │
│  [ Android Ingress Server ] ───────┘                   │
│    (Configurable Bind Host: 8766)                      │
│         ▲                                              │
└─────────┼──────────────────────────────────────────────┘
          │
          │ Wi-Fi LAN Connection (ws://<LAN_IP>:8766)
          │ 1. Initial Handshake Auth (JSON)
          │ 2. Binary Audio Frames (Audio Bridge Protocol v1)
          │
   [ Android Mobile Phone ]
```

---

## Network Connection Endpoints

| Service | Host Interface | Port | Purpose | Security |
| :--- | :--- | :--- | :--- | :--- |
| **Desktop Control** | `127.0.0.1` (Local-only loopback) | `8765` | UI State Sync, Start/Stop, Gain, Buffer Strategy | Strictly isolated to local loopback |
| **Android Audio Ingress** | Configurable (`0.0.0.0` or specific LAN IP) | `8766` | Receiving binary PCM audio from companion app | Handshake-only token authentication |

### Bind Address & Security Implications
- **Default Bind Address (`0.0.0.0`)**: Listens on all available IPv4 interfaces (Wi-Fi, Ethernet, VPN tunnels, and virtual adapters). Suitable for typical home Wi-Fi setups where the phone connects across the local subnet.
- **Hardened Single-Interface Binding**: On shared or public networks, users can restrict listening exclusively to their specific Wi-Fi interface by setting the environment variable:
  ```cmd
  set AUDIO_BRIDGE_ANDROID_HOST=192.168.1.100
  ```
  This guarantees that traffic arriving on other adapters (Ethernet, VPNs, virtual bridge networks) is rejected by the OS network stack.

---

## Security Hardening (Phase 2.6)

1. **Handshake-Only Authentication**: Authentication via URL query parameter (`?token=...`) is strictly prohibited to prevent credential leakage in HTTP server logs, access traces, and proxy histories. Clients must authenticate within a 3-second timeout using an initial JSON `HANDSHAKE` frame:
   ```json
   {
     "type": "HANDSHAKE",
     "token": "<session_token>",
     "deviceName": "Pixel 8 Pro",
     "sampleRate": 48000,
     "channels": 2,
     "version": 1
   }
   ```
2. **Strict Binary Frame Gating**: Binary PCM frames sent prior to successful handshake authentication are rejected immediately with close code `4401`, discarding any unverified payload data.
3. **Authentication Timeout**: Sockets failing to authenticate within `auth_timeout_seconds` (default 3.0s) are closed with code `4408`.
4. **Client Concurrency Control**: Enforces a maximum number of concurrent active mobile devices (`max_android_clients = 1`). Extra connection attempts are safely rejected with code `1008`.
5. **Duplicate Handshake Safe Rejection**: Authenticated connections sending duplicate handshake attempts receive an error acknowledgment without terminating the audio stream.
6. **Zero Token Leakage**: Tokens never appear in terminal output, exception traces, or log files. Logging uses sanitized masked previews (`ab***3f`).
7. **Constant-Time Verification**: Verification uses `hmac.compare_digest` to prevent timing attacks.
8. **Memory & Size Caps**: Ingress packets are capped at `16 KB` per frame to prevent buffer flooding.

---

## Binary Audio Packet Protocol (v1)

Audio is transmitted using binary WebSocket frames rather than JSON arrays:

### Header Structure (Fixed 16 Bytes)
```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|       Magic (0xAB01)          | MsgType (0x02)| Channels (0x02|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Sequence Number                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+                     Timestamp (Milliseconds)                  +
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     Raw PCM Audio Payload ...                 |
|            (Signed 16-bit Little-Endian, interleaved)         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- **Magic** (`2 bytes`): `b"\xAB\x01"`.
- **Message Type** (`1 byte`): `0x02` (`TYPE_PCM_AUDIO`).
- **Channels** (`1 byte`): `0x02` (Stereo) or `0x01` (Mono).
- **Sequence Number** (`4 bytes`, uint32): Packet counter.
- **Timestamp** (`8 bytes`, uint64): Millisecond Unix epoch timestamp.
- **Payload**: Raw Little-Endian signed 16-bit PCM bytes. Converted into float32 normalized in `[-1.0, 1.0]` and queued in `MobileAudioInput`.

---

## Automated Test Suite

Run all automated unit and integration tests (**29 tests passing**):

```cmd
cd e:\tws\backend
.venv\Scripts\python -m pytest -v
```

Tests cover:
- Binary protocol packing, unpacking, and validation.
- Malformed packet rejection (truncated headers, invalid magic, unaligned payloads, oversized frames).
- Handshake-only JSON authentication.
- Rejection of unauthenticated binary frames.
- Rejection of URL query-parameter token attempts.
- Authentication timeout enforcement.
- Safe rejection of duplicate handshakes on authenticated sockets.
- Concurrency limit enforcement (rejecting secondary clients).
- Routing of verified PCM audio into `MobileAudioInput`.
- Clean disconnection handling and resource release.
- Windows audio device detection and Bluetooth heuristics.
- Audio buffer mixing, gain adjustments, and soft clipping saturation.
- Desktop WebSocket control server commands.

---

## How to Launch

### 1. Launch Backend
```cmd
cd e:\tws\backend
.venv\Scripts\python main.py
```

### 2. Launch Frontend
```cmd
cd e:\tws\frontend
npm run dev
```
Open `http://localhost:5173`.

---

## Current Limitations (Prior to Phase 3 & 4)

1. **Android App (Phase 3)**:
   - Ingress server and binary protocol are verified and listening on port `8766`. The Kotlin companion app with `AudioPlaybackCapture` will be built in Phase 3.
2. **WASAPI Loopback Capture (Phase 4)**:
   - System audio mixing is in `Ready` state. Windows loopback capture will be added in Phase 4.
3. **End-to-End Live Stream Mixing (Phase 4 & 5)**:
   - Real-time mixing engine and output routing to the selected TWS Bluetooth device are scheduled for Phases 4 and 5.
