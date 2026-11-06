"""Message and state data models for AUDIO BRIDGE."""

from dataclasses import dataclass, asdict, field
from typing import Optional, Literal, Dict, Any, List

MobileStatus = Literal["Disconnected", "Connecting", "Connected"]
LaptopStatus = Literal["Ready", "Active"]
TwsStatus = Literal["Not connected", "Connected"]

@dataclass
class AudioDeviceInfo:
    id: int
    name: str
    is_default: bool
    is_bluetooth: bool
    max_output_channels: int
    default_samplerate: float
    host_api: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class StateUpdate:
    mobileStatus: MobileStatus
    laptopStatus: LaptopStatus
    twsStatus: TwsStatus
    mobileName: str
    outputDevice: str
    latency: int
    mobileVolume: int
    laptopVolume: int
    bufferMode: str
    isServiceRunning: bool
    lanIp: str = ""
    androidPort: int = 8766
    selectedDeviceId: Optional[int] = None
    availableDevices: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "STATE_UPDATE",
            **asdict(self)
        }
