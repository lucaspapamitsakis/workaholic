/**
 * Formatting helpers for dates and exercise statistics.
 *
 * Why this file exists:
 *  - `new Date("2026-05-24")` parses as UTC midnight and then renders in the
 *    local timezone, shifting display by the UTC offset. In EDT that turns
 *    May 24 into "May 23 8:00 PM". `parseLocalDate` constructs the Date
 *    from local components so the displayed day matches the input string.
 *  - The previous chart formula `(1 / pace) * 1000` produced unitless garbage.
 *    `formatPace` and `paceToMetersPerSecond` are the single source of truth.
 */

export function parseLocalDate(s: string): Date {
  // Accept "YYYY-MM-DD" or full ISO. Pull just the date portion.
  const dateOnly = s.length >= 10 ? s.slice(0, 10) : s;
  const [y, m, d] = dateOnly.split("-").map(Number);
  return new Date(y, (m ?? 1) - 1, d ?? 1);
}

export function formatShortDate(s: string): string {
  return parseLocalDate(s).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

/** Convert pace (sec/m) to speed in m/s. Higher is better; safe for charts. */
export function paceToMetersPerSecond(pace_sec_per_m: number | null | undefined): number | null {
  if (!pace_sec_per_m || pace_sec_per_m <= 0) return null;
  return Math.round((1 / pace_sec_per_m) * 100) / 100;
}

/** Format pace (sec/m) as "M:SS / 500m" — the rowing/running convention. */
export function formatPacePer500m(pace_sec_per_m: number | null | undefined): string {
  if (!pace_sec_per_m || pace_sec_per_m <= 0) return "—";
  const secPer500 = pace_sec_per_m * 500;
  const minutes = Math.floor(secPer500 / 60);
  const seconds = Math.round(secPer500 - minutes * 60);
  return `${minutes}:${seconds.toString().padStart(2, "0")} / 500m`;
}

/** Format duration as compact "Mm SSs" or "SSs". */
export function formatDuration(sec: number | null | undefined): string {
  if (sec == null) return "—";
  if (sec < 60) return `${Math.round(sec)}s`;
  const m = Math.floor(sec / 60);
  const s = Math.round(sec - m * 60);
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

export function formatNumber(n: number | null | undefined, digits = 1): string {
  if (n == null) return "—";
  return n.toLocaleString(undefined, {
    maximumFractionDigits: digits,
  });
}
