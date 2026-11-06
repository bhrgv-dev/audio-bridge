import { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { CentralToggle } from './components/CentralToggle';
import { DeviceIndicators } from './components/DeviceIndicators';
import { BottomStatus } from './components/BottomStatus';
import { AudioSettings } from './components/AudioSettings';
import { DiagnosticPanel } from './components/DiagnosticPanel';
import { bridgeClient } from './services/bridgeClient';
import type { MobileStatus, LaptopStatus, TwsStatus, AudioDeviceInfo } from './types';

export default function App() {
  // Primary Dual Audio Toggle State
  const [isActive, setIsActive] = useState<boolean>(false);

  // Device and Engine States
  const [mobileStatus, setMobileStatus] = useState<MobileStatus>('Disconnected');
  const [laptopStatus, setLaptopStatus] = useState<LaptopStatus>('Ready');
  const [twsStatus, setTwsStatus] = useState<TwsStatus>('Not connected');

  // Device Labels & Selection
  const [connectedMobileName, setConnectedMobileName] = useState<string>('');
  const [detectedOutputName, setDetectedOutputName] = useState<string>('');
  const [availableDevices, setAvailableDevices] = useState<AudioDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | undefined>(undefined);

  // Network Endpoints (from backend)
  const [lanIp, setLanIp] = useState<string>('127.0.0.1');
  const [androidPort, setAndroidPort] = useState<number>(8766);

  // Backend / Network Link
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(false);
  const [latencyMs, setLatencyMs] = useState<number>(0);

  // Audio Engine Mixer Settings
  const [showSettings, setShowSettings] = useState<boolean>(false);
  const [mobileVolume, setMobileVolume] = useState<number>(100);
  const [laptopVolume, setLaptopVolume] = useState<number>(100);
  const [bufferMode, setBufferMode] = useState<'low' | 'balanced' | 'stable'>('balanced');

  // Connect to backend WebSocket and synchronize state
  useEffect(() => {
    bridgeClient.connect();

    const unsubscribe = bridgeClient.subscribe((data) => {
      if (data.type === 'WS_STATUS') {
        setIsBackendConnected(data.connected);
        if (!data.connected) {
          if (isActive) {
            setMobileStatus('Connecting');
            setLaptopStatus('Ready');
          }
        }
      } else if (data.type === 'STATE_UPDATE') {
        if (data.mobileStatus) setMobileStatus(data.mobileStatus);
        if (data.laptopStatus) setLaptopStatus(data.laptopStatus);
        if (data.twsStatus) setTwsStatus(data.twsStatus);
        if (data.mobileName !== undefined) setConnectedMobileName(data.mobileName);
        if (data.outputDevice) setDetectedOutputName(data.outputDevice);
        if (typeof data.latency === 'number') setLatencyMs(data.latency);
        if (typeof data.isServiceRunning === 'boolean') {
          setIsActive(data.isServiceRunning);
        }
        if (typeof data.mobileVolume === 'number') {
          setMobileVolume(data.mobileVolume);
        }
        if (typeof data.laptopVolume === 'number') {
          setLaptopVolume(data.laptopVolume);
        }
        if (data.bufferMode) {
          setBufferMode(data.bufferMode);
        }
        if (data.lanIp) setLanIp(data.lanIp);
        if (data.androidPort) setAndroidPort(data.androidPort);
        if (data.selectedDeviceId !== undefined) setSelectedDeviceId(data.selectedDeviceId);
        if (Array.isArray(data.availableDevices)) {
          setAvailableDevices(data.availableDevices);
        }
      }
    });

    return () => {
      unsubscribe();
    };
  }, [isActive]);

  // Handle Central Toggle
  const handleToggle = () => {
    const nextState = !isActive;
    setIsActive(nextState);

    if (nextState) {
      // Start bridge service on backend
      bridgeClient.send('START_BRIDGE', {
        mobileVolume,
        laptopVolume,
        bufferMode,
      });

      // Truthful state reporting:
      if (!isBackendConnected) {
        setMobileStatus('Connecting');
        setLaptopStatus('Ready');
      }
    } else {
      // Stop bridge service
      bridgeClient.send('STOP_BRIDGE');
      setLaptopStatus('Ready');
      setMobileStatus('Disconnected');
      setConnectedMobileName('');
      setLatencyMs(0);
    }
  };

  // Select audio output device
  const handleSelectDevice = (deviceId: number) => {
    setSelectedDeviceId(deviceId);
    bridgeClient.send('SELECT_OUTPUT_DEVICE', { deviceId });
  };

  // Audio Mixer volume & buffer handlers
  const handleMobileVolumeChange = (vol: number) => {
    setMobileVolume(vol);
    bridgeClient.send('SET_MOBILE_VOLUME', { volume: vol });
  };

  const handleLaptopVolumeChange = (vol: number) => {
    setLaptopVolume(vol);
    bridgeClient.send('SET_LAPTOP_VOLUME', { volume: vol });
  };

  const handleBufferModeChange = (mode: 'low' | 'balanced' | 'stable') => {
    setBufferMode(mode);
    bridgeClient.send('SET_BUFFER_MODE', { mode });
  };

  // Calculate genuine active streaming state
  const isStreamingActive =
    isActive &&
    isBackendConnected &&
    mobileStatus === 'Connected' &&
    laptopStatus === 'Active';

  // Supporting status message that does NOT claim mixing until actually implemented
  const supportingText = !isActive
    ? 'Enable to start the bridge service.'
    : !isBackendConnected
    ? 'Bridge enabled — waiting for desktop backend service.'
    : mobileStatus !== 'Connected'
    ? 'Bridge running — waiting for Android companion to stream audio.'
    : 'Bridge running — mobile stream connected (live audio mix pending implementation).';

  return (
    <div className="min-h-screen bg-[#050505] text-white flex flex-col justify-between selection:bg-neutral-800 selection:text-white font-sans antialiased">
      {/* 1. TOP HEADER */}
      <Header />

      {/* 2. EXACT CENTER: LARGE MODERN TOGGLE SWITCH */}
      <main className="flex-1 flex flex-col justify-center items-center px-4">
        <CentralToggle
          isActive={isActive}
          isStreamingActive={isStreamingActive}
          supportingText={supportingText}
          onToggle={handleToggle}
        />

        {/* 3. DEVICE STATUS INDICATORS WITH OUTPUT SELECTOR */}
        <DeviceIndicators
          mobileStatus={mobileStatus}
          laptopStatus={laptopStatus}
          twsStatus={twsStatus}
          mobileDeviceName={connectedMobileName}
          detectedOutputDeviceName={detectedOutputName}
          availableDevices={availableDevices}
          selectedDeviceId={selectedDeviceId}
          onSelectDevice={handleSelectDevice}
          lanIp={lanIp}
          androidPort={androidPort}
        />

        {/* 4. AUDIO MIXER & BUFFER CONTROLS */}
        <AudioSettings
          isOpen={showSettings}
          onToggleOpen={() => setShowSettings(!showSettings)}
          mobileVolume={mobileVolume}
          laptopVolume={laptopVolume}
          bufferMode={bufferMode}
          onMobileVolumeChange={handleMobileVolumeChange}
          onLaptopVolumeChange={handleLaptopVolumeChange}
          onBufferModeChange={handleBufferModeChange}
        />

        {/* 5. LIVE DIAGNOSTIC & INGRESS INFO SECTION */}
        <DiagnosticPanel
          isBackendConnected={isBackendConnected}
          isServiceRunning={isActive}
          lanIp={lanIp}
          androidPort={androidPort}
          availableDevices={availableDevices}
          selectedDeviceId={selectedDeviceId}
          mobileStatus={mobileStatus}
          twsStatus={twsStatus}
        />
      </main>

      {/* 6. BOTTOM STATUS BAR & VERSION */}
      <BottomStatus
        isBackendConnected={isBackendConnected}
        version="v1.0.0-demo"
        latencyMs={latencyMs}
      />
    </div>
  );
}
