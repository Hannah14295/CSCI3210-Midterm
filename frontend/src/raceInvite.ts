export function raceInviteUrl(pageUrl: string, raceId: number) {
  const url = new URL(pageUrl);
  url.search = '';
  url.hash = `race=${raceId}`;
  return url.toString();
}

export function invitedRace(hash: string) {
  const match = /^#race=([1-9]\d*)$/.exec(hash);
  const id = match ? Number(match[1]) : NaN;
  return Number.isSafeInteger(id) ? id : null;
}
