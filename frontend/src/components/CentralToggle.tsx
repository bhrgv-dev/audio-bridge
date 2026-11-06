import React from 'react';

interface CentralToggleProps {
  isActive: boolean;
  isStreamingActive: boolean;
  supportingText?: string;
  isPending?: boolean;
  onToggle: () => void;
}

export const CentralToggle: React.FC<CentralToggleProps> = ({
  isActive,
  isStreamingActive,
  supportingText,
  isPending = false,
  onToggle,
}) => {
  // Determine supporting description based on genuine connection state
  const resolvedSupportingText = !isActive
    ? 'Enable to start the bridge service.'
    : isStreamingActive
    ? 'Bridge running — streams connected (live mix pending implementation).'
    : supportingText || 'Bridge running — awaiting audio stream.';

  return (
    <div className="flex flex-col items-center justify-center my-auto py-10 select-none">
      {/* Switch Button Container */}
      <button
        type="button"
        onClick={onToggle}
        disabled={isPending}
        aria-pressed={isActive}
        className="group relative focus:outline-none cursor-pointer"
      >
        {/* Ambient Soft Glow when Active */}
        <div
          className={`absolute inset-0 rounded-full transition-all duration-700 pointer-events-none blur-xl ${
            isActive
              ? 'bg-emerald-500/25 opacity-100 scale-110'
              : 'bg-transparent opacity-0 scale-90'
          }`}
        />

        {/* Large Switch Pill */}
        <div
          className={`relative w-36 h-20 rounded-full p-2 transition-all duration-500 flex items-center border ${
            isActive
              ? 'bg-neutral-900 border-emerald-500/60 shadow-[0_0_24px_rgba(16,185,129,0.22)]'
              : 'bg-[#101010] border-[#222222] hover:border-[#333333]'
          }`}
        >
          {/* Slider Knob */}
          <div
            className={`w-16 h-16 rounded-full flex items-center justify-center transition-all duration-500 ease-out transform ${
              isActive
                ? 'translate-x-16 bg-emerald-500 shadow-[0_0_16px_rgba(16,185,129,0.6)]'
                : 'translate-x-0 bg-[#282828] group-hover:bg-[#323232]'
            }`}
          >
            {/* Inner Indicator Dot */}
            <div
              className={`w-4 h-4 rounded-full transition-all duration-500 ${
                isActive
                  ? 'bg-white shadow-[0_0_8px_rgba(255,255,255,0.9)]'
                  : 'bg-[#181818]'
              }`}
            />
          </div>
        </div>
      </button>

      {/* Primary State Text */}
      <div className="mt-8 text-center space-y-1.5 transition-all duration-300">
        <div className="flex items-center justify-center gap-2">
          {/* Subtle Live Dot */}
          <span
            className={`w-2 h-2 rounded-full transition-all duration-500 ${
              isActive
                ? 'bg-emerald-400 shadow-[0_0_10px_#34d399] animate-pulse'
                : 'bg-neutral-600'
            }`}
          />
          <h2 className="text-xl md:text-2xl font-medium tracking-[0.18em] text-white uppercase">
            {isActive ? 'DUAL AUDIO ACTIVE' : 'DUAL AUDIO OFF'}
          </h2>
        </div>

        {/* Supporting Explanation */}
        <p className="text-xs md:text-sm text-neutral-400 font-light tracking-wide max-w-xs md:max-w-md mx-auto">
          {resolvedSupportingText}
        </p>
      </div>
    </div>
  );
};
