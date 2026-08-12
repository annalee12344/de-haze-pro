import { useCallback, useEffect, useRef, useState } from "react";

type Props = {
  src: string;
  filter: string;
};

export function CompareSlider({ src, filter }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState(50);
  const draggingRef = useRef(false);

  const move = useCallback((clientX: number) => {
    const el = containerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const pct = ((clientX - rect.left) / rect.width) * 100;
    setPosition(Math.min(100, Math.max(0, pct)));
  }, []);

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      if (!draggingRef.current) return;
      e.preventDefault();
      move(e.clientX);
    };
    const onUp = () => {
      draggingRef.current = false;
    };
    window.addEventListener("pointermove", onMove, { passive: false });
    window.addEventListener("pointerup", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  }, [move]);

  return (
    <div
      ref={containerRef}
      className="relative w-full touch-none select-none overflow-hidden bg-surface-sunken"
      onPointerDown={(e) => {
        draggingRef.current = true;
        move(e.clientX);
      }}
    >
      <img
        src={src}
        alt="Original hazy image"
        className="block w-full object-cover"
        draggable={false}
      />

      <div
        className="absolute inset-0 overflow-hidden"
        style={{ clipPath: `inset(0 0 0 ${position}%)` }}
      >
        <img
          src={src}
          alt="Dehazed result"
          className="block w-full object-cover"
          style={{ filter }}
          draggable={false}
        />
      </div>

      <span className="pointer-events-none absolute left-4 top-4 rounded-[3px] bg-foreground/80 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-background">
        Original
      </span>
      <span className="pointer-events-none absolute right-4 top-4 rounded-[3px] bg-accent px-2 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-accent-foreground">
        Dehazed
      </span>

      <div
        className="absolute inset-y-0 w-px bg-background/90"
        style={{ left: `${position}%` }}
      >
        <button
          type="button"
          aria-label="Comparison slider"
          role="slider"
          aria-valuenow={Math.round(position)}
          aria-valuemin={0}
          aria-valuemax={100}
          onKeyDown={(e) => {
            if (e.key === "ArrowLeft") setPosition((p) => Math.max(0, p - 2));
            if (e.key === "ArrowRight") setPosition((p) => Math.min(100, p + 2));
          }}
          onPointerDown={() => {
            draggingRef.current = true;
          }}
          className="absolute left-1/2 top-1/2 flex h-10 w-10 -translate-x-1/2 -translate-y-1/2 cursor-ew-resize items-center justify-center rounded-full border border-border bg-surface shadow-lift transition-transform hover:scale-105"
        >
          <span className="flex gap-[3px]">
            <span className="h-3 w-px bg-foreground/50" />
            <span className="h-3 w-px bg-foreground/50" />
          </span>
        </button>
      </div>
    </div>
  );
}
