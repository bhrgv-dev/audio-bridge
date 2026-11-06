import React from 'react';
import { Smartphone, Laptop, Headphones, ChevronDown } from 'lucide-react';
import type { MobileStatus, LaptopStatus, TwsStatus, AudioDeviceInfo } from '../types';

interface DeviceIndicatorsProps {
  mobileStatus: MobileStatus;
  laptopStatus: LaptopStatus;
  twsStatus: TwsStatus;
  mobileDeviceName?: string;
  detectedOutputDeviceName?: string;
  availableDevices?: AudioDeviceInfo[];
  selectedDeviceId?: number;
  onSelectDevice?: (deviceId: number) => void;
  lanIp?: string;
  androidPort?: number;
}

export const DeviceIndicators: React.FC<DeviceIndicatorsProps> = ({
  mobileStatus,
  laptopStatus,
  twsStatus,
  mobileDeviceName,
  detectedOutputDeviceName,
  availableDevices = [],
  selectedDeviceId,
  onSelectDevice,
  lanIp = '127.0.0.1',
  androidPort = 8766,
}) => {
  // Mobile status badge style
  const getMobileStatusStyle = () => {
    switch (mobileStatus) {
      case 'Connected':
        return {
          dot: 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]',
          text: 'text-emerald-400',
        };
      case 'Connecting':
        return {
          dot: 'bg-amber-400 animate-pulse shadow-[0_0_8px_rgba(251,191,36,0.5)]',
          text: 'text-amber-300',
        };
      default:
        return {
          dot: 'bg-neutral-600',
          text: 'text-neutral-500',
        };
    }
  };

  // Laptop status badge style
  const getLaptopStatusStyle = () => {
    switch (laptopStatus) {
      case 'Active':
        return {
          dot: 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]',
          text: 'text-emerald-400',
        };
      case 'Ready':
        return {
          dot: 'bg-neutral-400',
          text: 'text-neutral-300',
        };
      default:
        return {
          dot: 'bg-neutral-600',
          text: 'text-neutral-500',
        };
    }
  };

  // TWS status badge style
  const getTwsStatusStyle = () => {
    switch (twsStatus) {
      case 'Connected':
        return {
          dot: 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]',
          text: 'text-emerald-400',
        };
      default:
        return {
          dot: 'bg-neutral-600',
          text: 'text-neutral-500',
        };
    }
  };

  const mobileStyle = getMobileStatusStyle();
  const laptopStyle = getLaptopStatusStyle();
  const twsStyle = getTwsStatusStyle();

  const selectedDevName =
    availableDevices.find((d) => d.id === selectedDeviceId)?.name ||
    availableDevices.find((d) => d.is_default)?.name ||
    'System Default';

  return (
    <div className="w-full max-w-xl mx-auto px-4 pb-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* 1. MOBILE DEVICE */}
        <div className="bg-[#0a0a0a] border border-[#1b1b1b] hover:border-[#272727] transition-all rounded-lg p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-neutral-400 mb-3">
            <span className="text-[11px] font-mono tracking-widest uppercase">
              1. Mobile Device
            </span>
            <Smartphone className="w-4 h-4 text-neutral-500" strokeWidth={1.5} />
          </div>

          <div className="mt-1">
            <div className="flex items-center gap-2">
              <span className={`w-1.5 h-1.5 rounded-full ${mobileStyle.dot}`} />
              <span className={`text-xs font-medium tracking-wider uppercase ${mobileStyle.text}`}>
                {mobileStatus}
              </span>
            </div>
            <p className="text-[11px] text-neutral-500 truncate mt-1">
              {mobileStatus === 'Connected' && mobileDeviceName
                ? mobileDeviceName
                : mobileStatus === 'Connecting'
                ? 'Awaiting Wi-Fi stream...'
                : `Awaiting companion on ws://${lanIp}:${androidPort}`}
            </p>
          </div>
        </div>

        {/* 2. LAPTOP AUDIO */}
        <div className="bg-[#0a0a0a] border border-[#1b1b1b] hover:border-[#272727] transition-all rounded-lg p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-neutral-400 mb-3">
            <span className="text-[11px] font-mono tracking-widest uppercase">
              2. Laptop Audio
            </span>
            <Laptop className="w-4 h-4 text-neutral-500" strokeWidth={1.5} />
          </div>

          <div className="mt-1">
            <div className="flex items-center gap-2">
              <span className={`w-1.5 h-1.5 rounded-full ${laptopStyle.dot}`} />
              <span className={`text-xs font-medium tracking-wider uppercase ${laptopStyle.text}`}>
                {laptopStatus}
              </span>
            </div>
            <p className="text-[11px] text-neutral-500 truncate mt-1">
              {laptopStatus === 'Active'
                ? 'Loopback stream engaged'
                : 'Windows WASAPI ready'}
            </p>
          </div>
        </div>

        {/* 3. TWS OUTPUT */}
        <div className="bg-[#0a0a0a] border border-[#1b1b1b] hover:border-[#272727] transition-all rounded-lg p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-neutral-400 mb-2">
            <span className="text-[11px] font-mono tracking-widest uppercase">
              3. TWS Output
            </span>
            <Headphones className="w-4 h-4 text-neutral-500" strokeWidth={1.5} />
          </div>

          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className={`w-1.5 h-1.5 rounded-full ${twsStyle.dot}`} />
              <span className={`text-xs font-medium tracking-wider uppercase ${twsStyle.text}`}>
                {twsStatus}
              </span>
            </div>

            {/* Interactive Windows Output Device Selector */}
            {availableDevices.length > 0 ? (
              <div className="mt-1 relative">
                <select
                  value={selectedDeviceId ?? ''}
                  onChange={(e) => {
                    const val = e.target.value;
                    if (val !== '' && onSelectDevice) {
                      onSelectDevice(Number(val));
                    }
                  }}
                  className="w-full bg-[#111111] border border-[#222222] hover:border-[#333333] rounded px-2 py-1 text-[10px] font-mono text-neutral-300 truncate focus:outline-none focus:border-neutral-500 appearance-none cursor-pointer pr-6"
                >
                  {availableDevices.map((dev) => (
                    <option key={dev.id} value={dev.id} className="bg-[#111111] text-neutral-200">
                      {dev.name} {dev.is_bluetooth ? '[TWS]' : '[Speaker]'} {dev.is_default ? '(Default)' : ''}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-3 h-3 text-neutral-500 absolute right-2 top-2 pointer-events-none" />
                <p className="text-[10px] text-neutral-400 mt-1 truncate">
                  Selected: {selectedDevName}
                </p>
              </div>
            ) : (
              <p className="text-[11px] text-neutral-500 truncate mt-1">
                {detectedOutputDeviceName || 'Pair earbuds to Windows'}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
