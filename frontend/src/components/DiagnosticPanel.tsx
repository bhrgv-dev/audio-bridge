import React, { useState } from 'react';
import { Terminal, CheckCircle2, Circle } from 'lucide-react';
import type { AudioDeviceInfo } from '../types';

interface DiagnosticPanelProps {
  isBackendConnected: boolean;
  isServiceRunning: boolean;
  lanIp?: string;
  androidPort?: number;
  availableDevices?: AudioDeviceInfo[];
  selectedDeviceId?: number;
  mobileStatus: string;
  twsStatus: string;
}

export const DiagnosticPanel: React.FC<DiagnosticPanelProps> = ({
  isBackendConnected,
  isServiceRunning,
  lanIp = '127.0.0.1',
  androidPort = 8766,
  availableDevices = [],
  selectedDeviceId,
  mobileStatus,
  twsStatus,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  const selectedDevName =
    availableDevices.find((d) => d.id === selectedDeviceId)?.name ||
    availableDevices.find((d) => d.is_default)?.name ||
    'System Default';

  return (
    <div className="w-full max-w-xl mx-auto px-4 my-2 select-none">
      {/* Toggle Bar */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between py-2 text-[11px] font-mono tracking-wider text-neutral-500 hover:text-neutral-300 transition-colors uppercase border-b border-[#141414]"
      >
        <span className="flex items-center gap-1.5">
          <Terminal className="w-3.5 h-3.5" />
          Live Diagnostics & Ingress Connection
        </span>
        <span>{isOpen ? '— Hide' : '+ View'}</span>
      </button>

      {/* Expanded Diagnostics */}
      {isOpen && (
        <div className="mt-3 p-4 bg-[#0a0a0a] border border-[#1a1a1a] rounded-lg space-y-4 animate-in fade-in duration-150 font-mono text-[11px]">
          {/* Connection Endpoints */}
          <div className="space-y-1.5">
            <span className="text-neutral-400 text-[10px] tracking-wider uppercase block">
              Network Connection Endpoints
            </span>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-neutral-300">
              <div className="p-2 bg-[#060606] border border-[#161616] rounded">
                <span className="text-neutral-500 block text-[10px]">DESKTOP CONTROL</span>
                <span className="text-emerald-400">ws://127.0.0.1:8765</span>
                <span className="text-neutral-500 block text-[9px] mt-0.5">
                  {isBackendConnected ? 'Connected (Loopback)' : 'Offline (Start Backend)'}
                </span>
              </div>
              <div className="p-2 bg-[#060606] border border-[#161616] rounded">
                <span className="text-neutral-500 block text-[10px]">ANDROID INGRESS</span>
                <span className="text-emerald-400">ws://{lanIp}:{androidPort}</span>
                <span className="text-neutral-500 block text-[9px] mt-0.5">
                  Handshake Auth Gated (Token Protected)
                </span>
              </div>
            </div>
          </div>

          {/* Device & State Telemetry */}
          <div className="space-y-1.5 pt-2 border-t border-[#141414]">
            <span className="text-neutral-400 text-[10px] tracking-wider uppercase block">
              Hardware & Endpoint Telemetry
            </span>
            <div className="grid grid-cols-2 gap-2 text-[10px] text-neutral-400">
              <div>
                <span className="text-neutral-600 block">SELECTED OUTPUT:</span>
                <span className="text-neutral-300 truncate block">{selectedDevName}</span>
              </div>
              <div>
                <span className="text-neutral-600 block">TWS OUTPUT STATE:</span>
                <span className={twsStatus === 'Connected' ? 'text-emerald-400' : 'text-neutral-400'}>
                  {twsStatus}
                </span>
              </div>
              <div>
                <span className="text-neutral-600 block">ANDROID STREAM:</span>
                <span className={mobileStatus === 'Connected' ? 'text-emerald-400' : 'text-neutral-400'}>
                  {mobileStatus}
                </span>
              </div>
              <div>
                <span className="text-neutral-600 block">BRIDGE SERVICE:</span>
                <span className={isServiceRunning ? 'text-emerald-400' : 'text-neutral-400'}>
                  {isServiceRunning ? 'RUNNING' : 'STANDBY'}
                </span>
              </div>
            </div>
            <div className="pt-1">
              <span className="text-neutral-600 block">DESKTOP BACKEND:</span>
              <span className={isBackendConnected ? 'text-emerald-400' : 'text-neutral-400'}>
                {isBackendConnected ? 'CONNECTED (127.0.0.1:8765)' : 'OFFLINE'}
              </span>
            </div>
          </div>

          {/* Detected Windows Output Devices */}
          <div className="space-y-1.5 pt-2 border-t border-[#141414]">
            <span className="text-neutral-400 text-[10px] tracking-wider uppercase block">
              Detected Windows Output Devices ({availableDevices.length})
            </span>
            {availableDevices.length > 0 ? (
              <div className="max-h-24 overflow-y-auto space-y-1 pr-1">
                {availableDevices.map((dev) => (
                  <div
                    key={dev.id}
                    className={`flex items-center justify-between text-[10px] px-2 py-1 rounded border ${
                      dev.id === selectedDeviceId
                        ? 'border-emerald-500/40 bg-emerald-950/10 text-emerald-300'
                        : 'border-[#161616] bg-[#060606] text-neutral-400'
                    }`}
                  >
                    <span className="truncate">
                      {dev.name} {dev.is_default ? '(Default)' : ''}
                    </span>
                    <span className="text-neutral-600 ml-2 shrink-0">
                      {dev.is_bluetooth ? 'TWS' : 'SPK'}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[10px] text-neutral-500">
                {isBackendConnected ? 'No output devices detected.' : 'Backend offline — device list unavailable.'}
              </p>
            )}
            <p className="text-[9px] text-neutral-600 mt-1">
              TWS status reflects the selected Windows output device type, not a live audio connection.
            </p>
          </div>
          <div className="space-y-1.5 pt-2 border-t border-[#141414]">
            <span className="text-neutral-400 text-[10px] tracking-wider uppercase block">
              Feature Implementation Status
            </span>
            <div className="grid grid-cols-1 gap-1 text-[11px]">
              <div className="flex items-center justify-between py-0.5 text-neutral-300">
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  WebSocket Control Protocol
                </span>
                <span className="text-emerald-400 text-[10px]">Implemented</span>
              </div>
              <div className="flex items-center justify-between py-0.5 text-neutral-300">
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  Real-Time Windows Output Selection
                </span>
                <span className="text-emerald-400 text-[10px]">Implemented</span>
              </div>
              <div className="flex items-center justify-between py-0.5 text-neutral-300">
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  Buffer Mixer & Soft Limiter
                </span>
                <span className="text-emerald-400 text-[10px]">Implemented</span>
              </div>
              <div className="flex items-center justify-between py-0.5 text-neutral-400">
                <span className="flex items-center gap-1.5">
                  <Circle className="w-3 h-3 text-neutral-600" />
                  Android Companion App (Wi-Fi Capture)
                </span>
                <span className="text-neutral-500 text-[10px]">Pending Phase 3</span>
              </div>
              <div className="flex items-center justify-between py-0.5 text-neutral-400">
                <span className="flex items-center gap-1.5">
                  <Circle className="w-3 h-3 text-neutral-600" />
                  WASAPI Loopback Capture & Live Mix
                </span>
                <span className="text-neutral-500 text-[10px]">Pending Phase 4</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
