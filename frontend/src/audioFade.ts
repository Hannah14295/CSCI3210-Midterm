/** Fade from the listener's current volume, then stop and rewind the clip. */
export function fadeOutAudio(
  track: Pick<HTMLAudioElement, 'volume' | 'paused' | 'pause' | 'currentTime'>,
  durationMs = 2000,
) {
  const originalVolume = track.volume;
  const startedAt = Date.now();
  let timer: ReturnType<typeof setTimeout> | null = null;
  let cancelled = false;

  function finish() {
    track.volume = 0;
    track.pause();
    track.currentTime = 0;
    // Restore the listener's setting for the next playback, while paused.
    track.volume = originalVolume;
  }

  function step() {
    if (cancelled) return;
    const progress = Math.min(1, (Date.now() - startedAt) / durationMs);
    if (progress >= 1) { timer = null; finish(); return; }
    track.volume = originalVolume * (1 - progress);
    timer = setTimeout(step, 30);
  }

  if (track.paused || originalVolume === 0 || durationMs <= 0) finish();
  else timer = setTimeout(step, 30);

  return () => {
    cancelled = true;
    if (timer !== null) clearTimeout(timer);
    track.volume = originalVolume;
  };
}
