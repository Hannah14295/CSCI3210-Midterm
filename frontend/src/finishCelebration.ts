/** Only celebrate a newly confirmed finish, not an already completed race. */
export function createFinishCelebration() {
  let sawUnfinished = false;
  let celebrated = false;
  return (finished: boolean | null) => {
    if (finished === null) return false;
    if (!finished) { sawUnfinished = true; return false; }
    if (!sawUnfinished || celebrated) return false;
    celebrated = true;
    return true;
  };
}
