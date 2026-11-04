/** A display estimate only. Saved results always come from the server. */
export function previewTyping(target: string, text: string, elapsedSeconds: number) {
  const expected = Array.from(target);
  const typed = Array.from(text);
  let correct = 0;
  let prefix = 0;
  typed.forEach((character, index) => {
    if (character === expected[index]) {
      correct++;
      if (prefix === index) prefix++;
    }
  });
  return {
    typed_characters: typed.length,
    correct_characters: correct,
    correct_prefix: prefix,
    progress: expected.length ? Math.min(100, typed.length / expected.length * 100) : 0,
    accuracy: typed.length ? correct / typed.length * 100 : 100,
    complete: expected.length > 0 && typed.length === expected.length,
    wpm: elapsedSeconds > 0 ? correct * 12 / elapsedSeconds : 0,
  };
}
