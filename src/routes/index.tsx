import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";

import sampleHazy from "@/assets/sample-hazy.jpg";
import { Header } from "@/components/dehaze/Header";
import { UploadPanel } from "@/components/dehaze/UploadPanel";
import { CompareSlider } from "@/components/dehaze/CompareSlider";
import { ProcessingState } from "@/components/dehaze/ProcessingState";
import {
  Controls,
  PRESETS,
  buildFilter,
  type Adjustments,
  type Preset,
} from "@/components/dehaze/Controls";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "DEHAZE — Image Haze Removal & Restoration Tool" },
      {
        name: "description",
        content:
          "Remove haze, fog, and atmospheric distortion from photos. Upload an image, tune the restoration, and compare before and after side by side.",
      },
      { property: "og:title", content: "DEHAZE — Image Haze Removal & Restoration" },
      {
        property: "og:description",
        content:
          "A precise image restoration workspace: upload, dehaze, compare, download.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

function Index() {
  const [image, setImage] = useState<string | null>(null);
  const [phase, setPhase] = useState<"idle" | "processing" | "ready">("idle");
  const [progress, setProgress] = useState(0);
  const [preset, setPreset] = useState<Preset>("auto");
  const [adjustments, setAdjustments] = useState<Adjustments>(PRESETS.auto);
  const inputRef = useRef<HTMLInputElement>(null);
  const workspaceRef = useRef<HTMLDivElement>(null);

  const start = useCallback((src: string) => {
    setImage(src);
    setPreset("auto");
    setAdjustments(PRESETS.auto);
    setProgress(0);
    setPhase("processing");
  }, []);

  useEffect(() => {
    if (phase !== "processing") return;
    const id = window.setInterval(() => {
      setProgress((p) => {
        if (p >= 100) return 100;
        return p + Math.random() * 9 + 3;
      });
    }, 90);
    return () => window.clearInterval(id);
  }, [phase]);

  useEffect(() => {
    if (phase === "processing" && progress >= 100) {
      const t = window.setTimeout(() => setPhase("ready"), 320);
      return () => window.clearTimeout(t);
    }
  }, [phase, progress]);

  useEffect(() => {
    if (phase !== "idle") {
      workspaceRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [phase]);

  const handleFile = useCallback(
    (file: File) => {
      const reader = new FileReader();
      reader.onload = () => start(String(reader.result));
      reader.readAsDataURL(file);
    },
    [start],
  );

  const filter = buildFilter(adjustments);

  const download = useCallback(() => {
    if (!image) return;
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.filter = filter;
      ctx.drawImage(img, 0, 0);
      const link = document.createElement("a");
      link.href = canvas.toDataURL("image/jpeg", 0.94);
      link.download = "dehazed.jpg";
      link.click();
    };
    img.src = image;
  }, [image, filter]);

  return (
    <div className="min-h-screen bg-background font-sans text-foreground">
      <Header onUpload={() => inputRef.current?.click()} />

      <main className="mx-auto max-w-[1400px] px-5 pb-24 sm:px-8">
        {phase === "idle" && (
          <section className="mx-auto max-w-3xl pt-16 sm:pt-24">
            <h1 className="text-center font-display text-[44px] font-semibold leading-[1.02] tracking-[-0.03em] text-foreground sm:text-[72px]">
              See clearly again.
            </h1>
            <p className="mx-auto mt-5 max-w-xl text-center text-[15px] leading-relaxed text-muted-foreground">
              Remove haze and atmospheric distortion from your images with a simple,
              precise enhancement workflow.
            </p>

            <div className="mt-12 sm:mt-16">
              <UploadPanel
                inputRef={inputRef}
                onFile={handleFile}
                onSample={() => start(sampleHazy)}
              />
            </div>
          </section>
        )}

        <div ref={workspaceRef} id="workspace" className="scroll-mt-20">
          {phase !== "idle" && image && (
            <section className="animate-in fade-in duration-500 pt-10 sm:pt-14">
              <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
                <div>
                  <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                    Workspace
                  </p>
                  <h2 className="mt-1.5 font-display text-2xl font-semibold tracking-[-0.02em] sm:text-3xl">
                    Before → Process → After
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setPhase("idle");
                    setImage(null);
                  }}
                  className="text-[13px] text-muted-foreground transition-colors hover:text-foreground"
                >
                  Use another image
                </button>
              </div>

              {phase === "processing" ? (
                <ProcessingState stage={progress < 50 ? 0 : 1} progress={Math.min(progress, 100)} />
              ) : (
                <div className="animate-in fade-in duration-700 space-y-5">
                  <div className="border border-border bg-surface p-2 shadow-lift sm:p-3">
                    <CompareSlider src={image} filter={filter} />
                  </div>
                  <Controls
                    preset={preset}
                    adjustments={adjustments}
                    onPreset={(p) => {
                      setPreset(p);
                      setAdjustments(PRESETS[p]);
                    }}
                    onChange={(key, value) =>
                      setAdjustments((a) => ({ ...a, [key]: value }))
                    }
                    onReset={() => {
                      setPreset("auto");
                      setAdjustments(PRESETS.auto);
                    }}
                    onDownload={download}
                  />
                </div>
              )}
            </section>
          )}
        </div>

        <section id="how-it-works" className="mt-28 border-t border-border pt-12 scroll-mt-20">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
            How it works
          </p>
          <div className="mt-6 grid gap-10 sm:grid-cols-3">
            {[
              {
                n: "01",
                t: "Upload",
                d: "Drop a hazy photo. Nothing leaves your browser during preview.",
              },
              {
                n: "02",
                t: "Dehaze",
                d: "Atmospheric light is estimated and the transmission map is inverted.",
              },
              {
                n: "03",
                t: "Compare & download",
                d: "Drag the divider to inspect the restoration, then export.",
              },
            ].map((s) => (
              <div key={s.n}>
                <span className="font-mono text-[11px] text-accent">{s.n}</span>
                <h3 className="mt-2 font-display text-base font-semibold">{s.t}</h3>
                <p className="mt-1.5 text-[13px] leading-relaxed text-muted-foreground">{s.d}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="about" className="mt-20 border-t border-border pt-12 scroll-mt-20">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
            About
          </p>
          <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-muted-foreground">
            DEHAZE is a focused computational photography tool for landscape, aerial, and
            urban photography shot through fog, smog, or long-distance atmosphere. No
            presets pretending to be magic — just measurable contrast recovery you can
            verify against the original.
          </p>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-5 py-6 sm:px-8">
          <span className="font-display text-[13px] font-semibold tracking-[0.14em]">DEHAZE</span>
          <span className="font-mono text-[11px] text-muted-foreground">Image Restoration</span>
        </div>
      </footer>
    </div>
  );
}
