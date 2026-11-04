/** null hides an invalid/unstarted countdown; zero keeps Go visible until finish. */
export function countdownAt(startsAt: string | null, serverNow: number) {
  if (!startsAt) return null;
  const remaining = Date.parse(startsAt) - serverNow;
  if (!Number.isFinite(remaining)) return null;
  return Math.max(0, Math.min(3, Math.ceil(remaining / 1000)));
}
