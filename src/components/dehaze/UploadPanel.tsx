import { useRef, useState } from "react";

type Props = {
  onFile: (file: File) => void;
  onSample: () => void;
  inputRef: React.RefObject<HTMLInputElement | null>;
};

export function UploadPanel({ onFile, onSample, inputRef }: Props) {
  const [dragging, setDragging] = useState(false);
  const localRef = useRef<HTMLInputElement>(null);
  const ref = inputRef ?? localRef;

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const file = e.dataTransfer.files?.[0];
          if (file) onFile(file);
        }}
        className={`group relative flex flex-col items-center justify-center px-6 py-16 transition-colors duration-200 sm:py-24 ${
          dragging ? "bg-accent/5" : "bg-surface"
        }`}
        style={{
          boxShadow: dragging
            ? "inset 0 0 0 1px var(--accent)"
            : "inset 0 0 0 1px var(--border)",
        }}
      >
        <div className="pointer-events-none absolute inset-4 border border-dashed border-border/80 sm:inset-6" />

        <div className="relative flex flex-col items-center">
          <div className="mb-6 h-12 w-16 border border-foreground/25">
            <div className="m-1.5 h-3 w-3 rounded-full border border-foreground/25" />
            <div className="mt-2 ml-1.5 h-px w-10 bg-foreground/20" />
            <div className="mt-1.5 ml-1.5 h-px w-6 bg-foreground/15" />
          </div>

          <p className="font-display text-lg font-medium text-foreground">Drop an image here</p>
          <p className="my-2 text-[12px] uppercase tracking-[0.2em] text-muted-foreground">or</p>

          <button
            type="button"
            onClick={() => ref.current?.click()}
            className="rounded-[4px] bg-primary px-5 py-2.5 text-[13px] font-medium text-primary-foreground transition-colors hover:bg-accent"
          >
            Choose an image
          </button>

          <p className="mt-5 font-mono text-[11px] tracking-wide text-muted-foreground">
            JPG, PNG, WEBP · Up to 20 MB
          </p>
        </div>

        <input
          ref={ref}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onFile(file);
            e.target.value = "";
          }}
        />
      </div>

      <div className="mt-5 text-center">
        <button
          type="button"
          onClick={onSample}
          className="border-b border-accent/40 pb-0.5 text-[13px] text-accent transition-colors hover:border-accent"
        >
          Try a sample image
        </button>
      </div>
    </div>
  );
}
