import { useEffect, useRef } from 'react';
import { createFinishCelebration } from '../finishCelebration';

const colors = ['#ff0052', '#60a5fa', '#843b98', '#fbbf24', '#34d399'];

function launchConfetti(canvas: HTMLCanvasElement) {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const context = canvas.getContext('2d');
  if (!context) return;
  let width = window.innerWidth;
  let height = window.innerHeight;
  function resize() {
    width = window.innerWidth; height = window.innerHeight;
    const scale = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = width * scale; canvas.height = height * scale;
    context!.setTransform(scale, 0, 0, scale, 0, 0);
  }
  resize();
  window.addEventListener('resize', resize);
  canvas.style.display = 'block';
  // The top layer keeps confetti visible above the final-results dialog too.
  try { canvas.showPopover?.(); } catch { /* Fixed-position fallback. */ }
  const origins = [
    { x: 0.08, y: 0.7, direction: 1 },
    { x: 0.5, y: 0.98, direction: 0 },
    { x: 0.92, y: 0.7, direction: -1 },
  ];
  const pieces = Array.from({ length: 480 }, (_, index) => {
    const origin = origins[index % origins.length];
    return {
      x: width * origin.x, y: height * origin.y,
      vx: origin.direction === 0 ? (Math.random() - 0.5) * 900 : origin.direction * (100 + Math.random() * 620),
      vy: -400 - Math.random() * 550,
      rotation: Math.random() * Math.PI,
      spin: (Math.random() - 0.5) * 12,
      size: 6 + Math.random() * 7,
      color: colors[index % colors.length],
    };
  });
  const start = performance.now();
  let previous = start;
  let frame = 0;
  function stop() {
    cancelAnimationFrame(frame);
    window.removeEventListener('resize', resize);
    context!.clearRect(0, 0, width, height);
    try { canvas.hidePopover?.(); } catch { /* Already closed. */ }
    canvas.style.display = 'none';
  }
  function draw(now: number) {
    const elapsed = (now - start) / 1000;
    if (elapsed >= 4.5) { stop(); return; }
    const delta = Math.min((now - previous) / 1000, 0.05);
    previous = now;
    context!.clearRect(0, 0, width, height);
    context!.globalAlpha = Math.min(1, Math.max(0, (4.5 - elapsed) / 1));
    for (const piece of pieces) {
      piece.vx *= Math.exp(-0.5 * delta);
      piece.vy += 900 * delta;
      piece.x += piece.vx * delta; piece.y += piece.vy * delta;
      piece.rotation += piece.spin * delta;
      context!.save();
      context!.translate(piece.x, piece.y);
      context!.rotate(piece.rotation);
      context!.fillStyle = piece.color;
      context!.fillRect(-piece.size / 2, -piece.size / 2, piece.size, piece.size * 0.6);
      context!.restore();
    }
    frame = requestAnimationFrame(draw);
  }
  frame = requestAnimationFrame(draw);
  return stop;
}

export function FinishConfetti({ finished }: { finished: boolean | null }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const celebrate = useRef(createFinishCelebration());
  useEffect(() => {
    if (celebrate.current(finished) && canvas.current) return launchConfetti(canvas.current);
  }, [finished]);
  return <canvas ref={canvas} className="finish-confetti" popover="manual" aria-hidden="true" />;
}
