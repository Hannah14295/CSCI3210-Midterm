import { useEffect, useRef, useState } from 'react';
import { fadeOutAudio } from '../audioFade';

// Drop the clip into src/music. Vite handles local and GitHub Pages URLs.
const clips = import.meta.glob<string>('../music/*.{mp3,wav,ogg,m4a}', {
  eager: true, query: '?url', import: 'default',
});
const source = clips['../music/race-music.mp3']
  || clips[Object.keys(clips).sort()[0]];

export function RaceMusic({ playing }: { playing: boolean }) {
  const audio = useRef<HTMLAudioElement>(null);
  const [blocked, setBlocked] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const track = audio.current;
    if (!track) return;
    track.volume = 0.4;
    return () => track.pause();
  }, []);

  useEffect(() => {
    const track = audio.current;
    if (!track || !source) return;
    let active = true;
    if (playing) {
      track.play().catch((problem: unknown) => {
        if (!active) return;
        if (problem instanceof DOMException && problem.name === 'NotAllowedError') setBlocked(true);
        else if (!(problem instanceof DOMException && problem.name === 'AbortError')) setFailed(true);
      });
    } else {
      return fadeOutAudio(track);
    }
    // Changing to the finished state must not pause before the fade can run.
    return () => { active = false; };
  }, [playing]);

  // No player or failed file requests until a music clip has actually been added.
  if (!source) return null;
  return <div className="race-music" hidden={!playing}>
    <span>Race music</span>
    <audio ref={audio} src={source} loop controls preload="none"
      aria-label="Race music playback and volume"
      onPlay={() => { setBlocked(false); setFailed(false); }}
      onError={() => setFailed(true)} />
    {blocked && !failed && <span className="input-help" role="status">Press Play to enable music.</span>}
    {failed && <span className="input-help" role="status">Music is unavailable.</span>}
  </div>;
}
