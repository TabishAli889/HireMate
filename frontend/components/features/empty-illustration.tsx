import { useId, type CSSProperties } from "react";
import type { LucideIcon } from "lucide-react";

// CSS variables only resolve inside `style`, not in SVG presentation attributes.
const card: CSSProperties = { fill: "hsl(var(--card))", stroke: "hsl(var(--border))" };
const line = (opacity: number): CSSProperties => ({ fill: "hsl(var(--muted-foreground))", opacity });

/** Soft abstract illustration (floating cards + gradient orb) framing a feature icon. */
export function EmptyIllustration({ icon: Icon }: { icon: LucideIcon }) {
  const gid = `g-${useId().replace(/:/g, "")}`;
  const brand = (opacity: number): CSSProperties => ({ fill: `url(#${gid})`, opacity });

  return (
    <div className="relative h-32 w-44" aria-hidden>
      <svg viewBox="0 0 176 128" className="absolute inset-0 size-full" fill="none">
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" style={{ stopColor: "hsl(var(--gradient-from))" }} />
            <stop offset="100%" style={{ stopColor: "hsl(var(--gradient-to))" }} />
          </linearGradient>
        </defs>
        <ellipse cx="88" cy="66" rx="70" ry="50" style={brand(0.12)} />
        <rect x="14" y="30" width="54" height="38" rx="10" style={card} />
        <rect x="22" y="40" width="30" height="5" rx="2.5" style={line(0.35)} />
        <rect x="22" y="51" width="20" height="5" rx="2.5" style={line(0.2)} />
        <rect x="110" y="62" width="52" height="38" rx="10" style={card} />
        <rect x="118" y="72" width="28" height="5" rx="2.5" style={brand(0.6)} />
        <rect x="118" y="83" width="18" height="5" rx="2.5" style={line(0.2)} />
        <circle cx="146" cy="26" r="4" style={brand(0.5)} />
        <circle cx="30" cy="104" r="3" style={brand(0.4)} />
      </svg>
      <div className="animate-float absolute left-1/2 top-1/2 grid size-16 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-2xl bg-brand text-[hsl(var(--gradient-foreground))] shadow-glow">
        <Icon className="size-7" />
      </div>
    </div>
  );
}
