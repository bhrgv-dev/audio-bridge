import React from 'react';
import { Activity } from 'lucide-react';

interface BottomStatusProps {
  isBackendConnected: boolean;
  version?: string;
  latencyMs?: number;
}

export const BottomStatus: React.FC<BottomStatusProps> = ({
  isBackendConnected,
  version = 'v1.0.0-phase1',
  latencyMs = 0,
}) => {
  return (
    <footer className="w-full max-w-xl mx-auto px-4 py-4 border-t border-[#151515] text-[11px] font-mono text-neutral-500 flex flex-wrap items-center justify-between gap-2 select-none">
      {/* Backend / Network Bridge Status */}
      <div className="flex items-center gap-2">
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            isBackendConnected
              ? 'bg-emerald-400 shadow-[0_0_6px_#34d399]'
              : 'bg-neutral-600'
          }`}
        />
        <span>
          BRIDGE SERVICE:{' '}
          <span className={isBackendConnected ? 'text-neutral-300' : 'text-neutral-500'}>
            {isBackendConnected ? 'ONLINE (127.0.0.1:8765)' : 'STANDBY'}
          </span>
        </span>
      </div>

      {/* Latency & Mode */}
      <div className="flex items-center gap-4">
        {isBackendConnected && latencyMs > 0 && (
          <span className="flex items-center gap-1 text-neutral-400">
            <Activity className="w-3 h-3 text-neutral-500" />
            {latencyMs}ms
          </span>
        )}
        <span className="text-neutral-600 tracking-wider">{version}</span>
      </div>
    </footer>
  );
};
