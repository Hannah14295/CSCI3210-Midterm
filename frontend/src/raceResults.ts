import type { Race, Participant } from './types';

type FinalScore = Participant & { wpm: number; accuracy: number; elapsed_seconds: number };

export function raceResults(race: Race) {
  if (race.status !== 'finished' || race.participants.length === 0) return null;
  const scores = race.participants.filter((entry): entry is FinalScore =>
    Boolean(entry.finished_at)
    && entry.wpm !== null && Number.isFinite(entry.wpm)
    && entry.accuracy !== null && Number.isFinite(entry.accuracy)
    && entry.elapsed_seconds !== null && Number.isFinite(entry.elapsed_seconds),
  );
  // A partial or older snapshot must never announce the race's final winners.
  if (scores.length !== race.participants.length) return null;
  scores.sort((a, b) => b.wpm - a.wpm || b.accuracy - a.accuracy
    || a.elapsed_seconds - b.elapsed_seconds || a.id - b.id);
  const bestWpm = Math.max(...scores.map(entry => entry.wpm));
  const bestAccuracy = Math.max(...scores.map(entry => entry.accuracy));
  return {
    scores,
    speedWinners: scores.filter(entry => entry.wpm === bestWpm),
    accuracyWinners: scores.filter(entry => entry.accuracy === bestAccuracy),
  };
}

export type RaceResults = NonNullable<ReturnType<typeof raceResults>>;
