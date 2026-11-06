export type MobileStatus = 'Disconnected' | 'Connecting' | 'Connected';
export type LaptopStatus = 'Ready' | 'Active';
export type TwsStatus = 'Not connected' | 'Connected';

export interface AudioDeviceInfo {
  id: number;
  name: string;
  is_default: boolean;
  is_bluetooth: boolean;
  max_output_channels: number;
  default_samplerate: number;
  host_api: string;
}

export interface BridgeState {
  isActive: boolean;
  mobileStatus: MobileStatus;
  laptopStatus: LaptopStatus;
  twsStatus: TwsStatus;
  connectedMobileDeviceName?: string;
  detectedOutputDeviceName?: string;
  isBackendConnected: boolean;
  latencyMs: number;
  mobileVolume: number; // 0 - 150
  laptopVolume: number; // 0 - 150
  bufferMode: 'low' | 'balanced' | 'stable';
  lanIp?: string;
  androidPort?: number;
  selectedDeviceId?: number;
  availableDevices?: AudioDeviceInfo[];
}
