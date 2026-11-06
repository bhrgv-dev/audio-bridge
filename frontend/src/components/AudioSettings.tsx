import React from 'react';
import { Sliders, Volume2 } from 'lucide-react';

interface AudioSettingsProps {
  isOpen: boolean;
  onToggleOpen: () => void;
  mobileVolume: number;
  laptopVolume: number;
  bufferMode: 'low' | 'balanced' | 'stable';
  onMobileVolumeChange: (val: number) => void;
  onLaptopVolumeChange: (val: number) => void;
  onBufferModeChange: (mode: 'low' | 'balanced' | 'stable') => void;
}

export const AudioSettings: React.FC<AudioSettingsProps> = ({
  isOpen,
  onToggleOpen,
  mobileVolume,
  laptopVolume,
  bufferMode,
  onMobileVolumeChange,
  onLaptopVolumeChange,
  onBufferModeChange,
}) => {
  return (
    <div className="w-full max-w-xl mx-auto px-4 my-2 select-none">
      {/* Toggle Header */}
      <button
        type="button"
        onClick={onToggleOpen}
        className="w-full flex items-center justify-between py-2 text-[11px] font-mono tracking-wider text-neutral-500 hover:text-neutral-300 transition-colors uppercase border-b border-[#141414]"
      >
        <span className="flex items-center gap-1.5">
          <Sliders className="w-3.5 h-3.5" />
          Mixer & Buffer Controls
        </span>
        <span>{isOpen ? '— Hide' : '+ Configure'}</span>
      </button>

      {/* Collapsible Panel */}
      {isOpen && (
        <div className="mt-4 p-4 bg-[#0a0a0a] border border-[#1a1a1a] rounded-lg space-y-4 animate-in fade-in duration-200">
          {/* Mobile Volume */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs text-neutral-400 font-mono">
              <span className="flex items-center gap-1.5">
                <Volume2 className="w-3.5 h-3.5 text-neutral-500" />
                Mobile Input Gain
              </span>
              <span>{mobileVolume}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="150"
              value={mobileVolume}
              onChange={(e) => onMobileVolumeChange(Number(e.target.value))}
              className="w-full h-1 bg-[#1c1c1c] rounded-lg appearance-none cursor-pointer accent-emerald-500"
            />
          </div>

          {/* Laptop Volume */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs text-neutral-400 font-mono">
              <span className="flex items-center gap-1.5">
                <Volume2 className="w-3.5 h-3.5 text-neutral-500" />
                Laptop Audio Mix
              </span>
              <span>{laptopVolume}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="150"
              value={laptopVolume}
              onChange={(e) => onLaptopVolumeChange(Number(e.target.value))}
              className="w-full h-1 bg-[#1c1c1c] rounded-lg appearance-none cursor-pointer accent-emerald-500"
            />
          </div>

          {/* Buffer Latency Selector */}
          <div className="pt-2 border-t border-[#161616]">
            <label className="text-[11px] font-mono text-neutral-500 block mb-2 uppercase">
              Jitter Buffer Strategy
            </label>
            <div className="grid grid-cols-3 gap-2 text-xs font-mono">
              {(
                [
                  { id: 'low', label: 'Ultra-Low (5ms)' },
                  { id: 'balanced', label: 'Balanced (15ms)' },
                  { id: 'stable', label: 'Stable (30ms)' },
                ] as const
              ).map((mode) => (
                <button
                  key={mode.id}
                  type="button"
                  onClick={() => onBufferModeChange(mode.id)}
                  className={`py-1.5 px-2 rounded border text-center transition-all ${
                    bufferMode === mode.id
                      ? 'border-emerald-500/70 bg-emerald-950/20 text-emerald-400'
                      : 'border-[#202020] bg-[#111111] text-neutral-400 hover:border-[#333333]'
                  }`}
                >
                  {mode.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
