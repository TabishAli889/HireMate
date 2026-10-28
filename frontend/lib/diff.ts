export interface DiffPart {
  text: string;
  type: "same" | "added" | "removed";
}

/** Word-level diff (LCS) between two short texts, e.g. an original and a rewritten resume bullet. */
export function diffWords(before: string, after: string): { before: DiffPart[]; after: DiffPart[] } {
  const a = before.split(/(\s+)/).filter(Boolean);
  const b = after.split(/(\s+)/).filter(Boolean);
  const norm = (w: string) => w.toLowerCase().replace(/[.,;:!?()"“”]/g, "");

  // lcs[i][j] = length of the longest common subsequence of a[i..] and b[j..]
  const lcs: number[][] = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i--) {
    for (let j = b.length - 1; j >= 0; j--) {
      const row = lcs[i] as number[];
      row[j] = norm(a[i] as string) === norm(b[j] as string) ? (lcs[i + 1]?.[j + 1] ?? 0) + 1 : Math.max(lcs[i + 1]?.[j] ?? 0, row[j + 1] ?? 0);
    }
  }

  const left: DiffPart[] = [];
  const right: DiffPart[] = [];
  let i = 0;
  let j = 0;
  while (i < a.length && j < b.length) {
    const wa = a[i] as string;
    const wb = b[j] as string;
    if (norm(wa) === norm(wb)) {
      left.push({ text: wa, type: "same" });
      right.push({ text: wb, type: "same" });
      i++;
      j++;
    } else if ((lcs[i + 1]?.[j] ?? 0) >= (lcs[i]?.[j + 1] ?? 0)) {
      left.push({ text: wa, type: /^\s+$/.test(wa) ? "same" : "removed" });
      i++;
    } else {
      right.push({ text: wb, type: /^\s+$/.test(wb) ? "same" : "added" });
      j++;
    }
  }
  for (; i < a.length; i++) left.push({ text: a[i] as string, type: /^\s+$/.test(a[i] as string) ? "same" : "removed" });
  for (; j < b.length; j++) right.push({ text: b[j] as string, type: /^\s+$/.test(b[j] as string) ? "same" : "added" });
  return { before: left, after: right };
}
