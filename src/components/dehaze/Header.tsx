export function Header({ onUpload }: { onUpload: () => void }) {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-[1400px] items-center gap-8 px-5 sm:px-8">
        <a href="/" className="flex items-baseline gap-2.5">
          <span className="font-display text-[17px] font-semibold tracking-[0.14em] text-foreground">
            DEHAZE
          </span>
          <span className="hidden text-[11px] uppercase tracking-[0.16em] text-muted-foreground sm:inline">
            Image Restoration
          </span>
        </a>

        <nav className="ml-auto hidden items-center gap-7 md:flex">
          {["Workspace", "How it works", "About"].map((item) => (
            <a
              key={item}
              href={`#${item.toLowerCase().replace(/\s+/g, "-")}`}
              className="text-[13px] text-muted-foreground transition-colors hover:text-foreground"
            >
              {item}
            </a>
          ))}
        </nav>

        <button
          type="button"
          onClick={onUpload}
          className="ml-auto rounded-[4px] border border-border bg-surface px-3.5 py-2 text-[13px] font-medium text-foreground transition-colors hover:border-foreground/40 hover:bg-surface-sunken md:ml-0"
        >
          Upload Image
        </button>
      </div>
    </header>
  );
}
