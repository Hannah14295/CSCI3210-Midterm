import { useEffect, useRef } from 'react';
import { fadeOutAudio } from '../audioFade';

// Drop the clip into src/music. Vite handles local and GitHub Pages URLs.
const clips = import.meta.glob<string>('../music/*.{mp3,wav,ogg,m4a}', {
  eager: true, query: '?url', import: 'default',
});
const source = clips['../music/race-music.mp3']
  || clips[Object.keys(clips).sort()[0]];

export function RaceMusic({ playing }: { playing: boolean }) {
  const audio = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    const track = audio.current;
    if (!track) return;
    track.volume = 0.4;
    return () => track.pause();
  }, []);

  useEffect(() => {
    const track = audio.current;
    if (!track || !source) return;
    if (playing) {
      track.play().catch(() => {
        // A trusted key/click below retries if the browser blocks autoplay.
      });
    } else {
      return fadeOutAudio(track);
    }
    // Changing to the finished state must not pause before the fade can run.
    return () => {};
  }, [playing]);

  useEffect(() => {
    if (!playing) return;
    const resume = () => {
      const track = audio.current;
      if (track?.paused) void track.play().catch(() => {});
    };
    window.addEventListener('pointerdown', resume);
    window.addEventListener('keydown', resume);
    return () => {
      window.removeEventListener('pointerdown', resume);
      window.removeEventListener('keydown', resume);
    };
  }, [playing]);

  if (!source) return null;
  return <audio ref={audio} src={source} loop hidden preload="none" />;
}
