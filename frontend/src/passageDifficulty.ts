export function passageDifficulty(text: string) {
  const length = Array.from(text).length;
  return length <= 300 ? 'short' : length <= 500 ? 'medium' : 'long';
}
