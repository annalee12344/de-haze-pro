type Props = { message?: string };

export function ProcessingState({ message = "Processing image..." }: Props) {
  return (
    <div className="border border-border bg-surface p-10 shadow-panel sm:p-16">
      <div className="flex items-center gap-4">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-border border-t-accent" />
        <p className="font-display text-lg font-medium text-foreground">
          {message}
        </p>
      </div>
      <p className="mt-4 text-[13px] text-muted-foreground">
        Running PyTorch Dark Channel Prior algorithm. This may take 15–20 seconds on CPU.
      </p>
    </div>
  );
}
