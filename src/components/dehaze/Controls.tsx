export type Preset = "auto" | "mild" | "balanced" | "strong";

export type Adjustments = {
  haze: number;
  contrast: number;
  brightness: number;
  saturation: number;
};

export const PRESETS: Record<Preset, Adjustments> = {
  auto: { haze: 62, contrast: 55, brightness: 48, saturation: 58 },
  mild: { haze: 32, contrast: 45, brightness: 50, saturation: 52 },
  balanced: { haze: 60, contrast: 56, brightness: 47, saturation: 60 },
  strong: { haze: 88, contrast: 68, brightness: 44, saturation: 72 },
};

export function buildFilter(a: Adjustments) {
  const contrast = 1 + (a.contrast - 50) / 60 + a.haze / 85;
  const brightness = 1 + (a.brightness - 50) / 130 - a.haze / 320;
  const saturate = 1 + (a.saturation - 50) / 50 + a.haze / 110;
  return `contrast(${contrast.toFixed(3)}) brightness(${brightness.toFixed(
    3,
  )}) saturate(${saturate.toFixed(3)})`;
}


type Props = {
  preset: Preset;
  adjustments: Adjustments;
  onPreset: (p: Preset) => void;
  onChange: (key: keyof Adjustments, value: number) => void;
  onReset: () => void;
  onDownload: () => void;
};

const FIELDS: { key: keyof Adjustments; label: string }[] = [
  { key: "haze", label: "Haze Removal" },
  { key: "contrast", label: "Contrast" },
  { key: "brightness", label: "Brightness" },
  { key: "saturation", label: "Saturation" },
];

export function Controls({
  preset,
  adjustments,
  onPreset,
  onChange,
  onReset,
  onDownload,
}: Props) {
  return (
    <div className="border border-border bg-surface shadow-panel">
      <div className="flex flex-col gap-6 p-5 sm:p-7 lg:flex-row lg:items-start lg:gap-10">
        <div className="lg:w-56 lg:shrink-0">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
            Dehazing
          </p>
          <div className="mt-3 grid grid-cols-2 gap-px bg-border p-px sm:grid-cols-4">
            {(["auto", "mild", "balanced", "strong"] as const).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => onPreset(p)}
                className={`px-2 py-2 text-[12px] capitalize transition-colors ${
                  preset === p
                    ? "bg-primary text-primary-foreground"
                    : "bg-surface text-muted-foreground hover:bg-surface-sunken hover:text-foreground"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
            Fine adjustment
          </p>
          <div className="mt-3 grid gap-x-10 gap-y-4 sm:grid-cols-2">
            {FIELDS.map(({ key, label }) => (
              <label key={key} className="block">
                <span className="flex items-baseline justify-between text-[13px] text-foreground">
                  {label}
                  <span className="font-mono text-[11px] text-muted-foreground">
                    {adjustments[key]}
                  </span>
                </span>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={adjustments[key]}
                  onChange={(e) => onChange(key, Number(e.target.value))}
                  className="dehaze-range mt-2 w-full"
                />
              </label>
            ))}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 border-t border-border px-5 py-4 sm:px-7">
        <button
          type="button"
          onClick={onReset}
          className="text-[13px] text-muted-foreground transition-colors hover:text-foreground"
        >
          Reset
        </button>
        <button
          type="button"
          onClick={onDownload}
          className="rounded-[4px] bg-primary px-5 py-2.5 text-[13px] font-medium text-primary-foreground transition-colors hover:bg-accent"
        >
          Download Image
        </button>
      </div>
    </div>
  );
}
