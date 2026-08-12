type Props = { stage: 0 | 1; progress: number };

export function ProcessingState({ stage, progress }: Props) {
  return (
    <div className="border border-border bg-surface p-10 shadow-panel sm:p-16">
      <p className="font-display text-lg font-medium text-foreground">
        {stage === 0 ? "Analyzing image…" : "Restoring visibility…"}
      </p>
      <p className="mt-1.5 text-[13px] text-muted-foreground">
        Estimating atmospheric light and transmission map.
      </p>
      <div className="mt-8 h-px w-full bg-border">
        <div
          className="h-px bg-accent transition-[width] duration-200 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
      <p className="mt-3 font-mono text-[11px] text-muted-foreground">
        {Math.round(progress)}%
      </p>
    </div>
  );
}
