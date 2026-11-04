/** Keep one update awaiting confirmation and combine newer input into one buffer. */
export function createTypingSender(send: (text: string) => void, intervalMs = 250) {
  let pending: { text: string; urgent: boolean } | null = null;
  let inFlight: number | null = null;
  let lastSentAt: number | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let stopped = false;

  function clearTimer() {
    if (timer !== null) clearTimeout(timer);
    timer = null;
  }

  function flush() {
    clearTimer();
    if (stopped || inFlight !== null || !pending) return;
    const { text } = pending;
    pending = null;
    inFlight = Array.from(text).length;
    lastSentAt = Date.now();
    send(text);
  }

  function schedule() {
    if (stopped || inFlight !== null || !pending) return;
    if (pending.urgent) { flush(); return; }
    if (timer !== null) return;
    const wait = lastSentAt === null ? intervalMs : Math.max(0, intervalMs - (Date.now() - lastSentAt));
    if (wait === 0) flush();
    else timer = setTimeout(flush, wait);
  }

  return {
    queue(text: string, complete = false, firstKey = false) {
      if (stopped) return;
      pending = { text, urgent: complete || firstKey };
      schedule();
    },
    acknowledge(typedCharacters: number) {
      if (inFlight === null || typedCharacters < inFlight) return;
      inFlight = null;
      schedule();
    },
    reset() {
      clearTimer();
      pending = null;
      inFlight = null;
    },
    stop() {
      this.reset();
      stopped = true;
    },
  };
}
