import { memo, useEffect, useRef } from 'react';
import type { Participant } from '../types';

const colors = ['#d6e84c', '#85c6db', '#efa985', '#c6a9de', '#8ec4a1'];
export const RaceTrack = memo(function RaceTrack({ participants, playerId }: { participants: Participant[]; playerId: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const entries = useRef(participants);
  const positions = useRef(new Map<number, number>());
  useEffect(() => { entries.current = participants; }, [participants]);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    let width = canvas.clientWidth;
    let height = Math.max(1, participants.length) * 80;
    const resize = new ResizeObserver(() => {
      width = canvas.clientWidth;
      height = Math.max(1, entries.current.length) * 80;
      const scale = window.devicePixelRatio || 1;
      canvas.width = width * scale; canvas.height = height * scale;
      ctx.setTransform(scale, 0, 0, scale, 0, 0);
    });
    resize.observe(canvas);
    const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
    let frame = 0;
    function draw() {
      if (!ctx) return;
      ctx.clearRect(0, 0, width, height);
      entries.current.forEach((entry, index) => {
        const y = index * 80 + 42;
        const finish = width - 26;
        ctx.strokeStyle = '#454b50'; ctx.lineWidth = 1; ctx.setLineDash([5, 8]);
        ctx.beginPath(); ctx.moveTo(16, y + 18); ctx.lineTo(finish, y + 18); ctx.stroke();
        ctx.setLineDash([]);
        for (let column = 0; column < 2; column++) for (let row = 0; row < 6; row++) {
          ctx.fillStyle = (column + row) % 2 ? '#31383e' : '#a2a8aa';
          ctx.fillRect(finish + column * 5, y - 10 + row * 5, 5, 5);
        }
        const target = entry.metrics.progress / 100;
        const old = positions.current.get(entry.id) || 0;
        const position = reducedMotion ? target : old + (target - old) * 0.12;
        positions.current.set(entry.id, position);
        const x = 28 + Math.max(0, finish - 68) * position;
        ctx.fillStyle = '#d8dddf'; ctx.font = '12px system-ui';
        ctx.fillText(`${entry.player.username.slice(0, 18)}${entry.player.id === playerId ? ' (you)' : ''}`, 16, y - 20);
        ctx.fillStyle = colors[index % colors.length];
        ctx.beginPath(); ctx.roundRect(x - 17, y - 8, 35, 15, 4); ctx.fill();
        ctx.fillStyle = '#1a2229'; ctx.fillRect(x - 4, y - 5, 10, 9);
        ctx.fillStyle = '#090e12';
        for (const wheelX of [-11, 10]) for (const wheelY of [-11, 7]) ctx.fillRect(x + wheelX, y + wheelY, 7, 5);
      });
      frame = requestAnimationFrame(draw);
    }
    frame = requestAnimationFrame(draw);
    return () => { cancelAnimationFrame(frame); resize.disconnect(); };
  }, [participants.length, playerId]);
  return <div className="track"><div className="track-top"><span>LIVE TRACK</span><span>FINISH ▥</span></div><canvas ref={canvasRef} style={{ height: Math.max(1, participants.length) * 80 }} aria-label="Animated race progress. Player statistics are listed below." /></div>;
});
