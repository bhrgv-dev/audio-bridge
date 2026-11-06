import React from 'react';

export const Header: React.FC = () => {
  return (
    <header className="text-center pt-8 pb-4 select-none">
      <h1 className="tracking-[0.25em] text-sm md:text-base font-semibold text-white/95 uppercase">
        AUDIO BRIDGE
      </h1>
      <p className="tracking-[0.35em] text-[10px] md:text-[11px] text-white/40 mt-1 uppercase font-medium">
        UNIVERSAL DUAL AUDIO SYSTEM
      </p>
    </header>
  );
};

