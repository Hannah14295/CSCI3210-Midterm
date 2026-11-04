# Typeway: React + TypeScript frontend

This folder holds the game UI. Django in `../backend/` still stores data,
authenticates players, enforces race rules, validates progress, and saves scores.

## Start from the repository root

```powershell
# Terminal 1
.\.venv\Scripts\python.exe backend\manage.py runserver
```

```powershell
# Terminal 2
npm --prefix frontend run dev
```

Open http://127.0.0.1:5173/. Dependencies have already been installed in this
checkout; use `npm --prefix frontend ci` on a fresh checkout. Run
`npm --prefix frontend run build` for strict TypeScript checks and a production
bundle in `frontend/dist/`.

## Main files: where to change things

| File | Responsibility |
| --- | --- |
| `src/main.tsx` | Starts React; wraps the app in authentication context and an error boundary |
| `src/App.tsx` | Header/navigation; chooses account, lobby, race, or leaderboard screen |
| `src/auth.tsx` | React Context sharing the current user/token, account requests, and local sign-out |
| `src/types.ts` | Strict types and runtime validation schemas for API and WebSocket payloads |
| `src/api.ts` | Fetch requests, authentication headers, JSON parsing, and readable errors |
| `src/hooks/useRace.ts` | Live connection lifecycle, token handshake, race snapshots, and throttled input |
| `src/components/AuthForm.tsx` | Login and registration forms |
| `src/components/Lobby.tsx` | Fetches passages/recent rooms and handles create/join |
| `src/components/RaceRoom.tsx` | Race controls, input, highlighting, participant stats, and saved result |
| `src/components/RaceTrack.tsx` | Presentational canvas animation of player progress |
| `src/components/Leaderboard.tsx` | Fetches and displays paginated completed results |
| `src/components/Notice.tsx` | Reusable accessible error message |
| `src/styles.css` | Colors, spacing, typography, and responsive layout |
| `vite.config.ts` | React tooling and the development proxy to Django |

## Follow a click through the app

1. Lobby's Create a race button submits the selected paragraph ID.
2. `api.ts` sends POST `/api/races/` with the player's token.
3. Vite forwards `/api/` to Django on port 8000.
4. Django saves the race and host participant, then returns JSON.
5. The runtime schema validates that response; TypeScript knows its fields.
6. App opens RaceRoom with the returned ID.
7. `useRace` opens `/ws/races/ID/?auth=token`, forwarded to Django by Vite.
8. After the backend requests authentication, the hook sends the token as a frame.
9. Django checks the player and membership, then sends a race snapshot.
10. React renders the waiting room and participant track.

Clicking Start sends another POST. The backend broadcasts the new running state,
and the hook updates React state. Typing updates local input/highlighting
immediately and sends the latest buffer at most four times per second. Progress
and WPM displays use backend broadcasts, not local guesses.

## State and component separation

- AuthContext contains shared account state, not fast-changing typing input.
- `useRace` contains live race state; its effect closes connections and cancels
  send timers when unmounted. A reconnect button restores server-saved input.
- RaceRoom coordinates data and actions; Passage and RaceTrack render their props.
- Memoization keeps the canvas/passages from unnecessary unrelated rerenders.
- Canvas uses requestAnimationFrame for motion and respects reduced-motion settings.
- Server revisions prevent older updates from moving a displayed player backward.
- No TypeScript `any` types are used. Zod checks received data at runtime, since
  TypeScript alone cannot validate JSON from a server.

## Authentication details

Only the token is kept in per-tab sessionStorage; passwords are not stored.
Refresh validates the token with `/api/auth/me/`. Local sign-out removes the token
from this tab but does not revoke the backend's reusable token. Revocation and
automatic expiry are future improvements.

HTTP requests omit browser cookies and send the explicit token. WebSocket URLs
include `auth=token` (not the credential), which tells Django to ignore any admin
session cookie and request the player's token frame instead. This matters if
the user is signed into admin as Hannah while playing as another account.

## Useful limits to understand

- The lobby shows the first 20 passages and 20 newest races. You can open older
  races by ID. The leaderboard has Previous/Next pagination.
- Opening Leaderboard or returning to the lobby disconnects that screen's live
  connection; opening the room again reconnects and loads saved progress.
- Refresh returns to the lobby, where recent rooms let you reopen your race.
- Reconnection restores accepted server input, so a pending unsent keystroke can
  be lost on disconnect. The UI disables typing until reconnected.
- A disconnected unfinished participant currently keeps the race Running; they
  can return to finish. There is no race timeout/abandonment yet.
- Progress and accuracy are server values; highlight colors are an immediate
  browser preview. Accuracy measures the current buffer, not lifetime mistakes.
- Font downloads use Google Fonts, with system fonts as fallback if offline.
- This proxy applies to the development server, not the built static files.
  Deployment needs same-origin API/WebSocket routing and shared Channels storage
  if multiple Django processes are used.

## Verification performed

- Strict TypeScript checks and Vite production build.
- Backend regression tests, including token-mode WebSocket authentication.
- Browser testing with two temporary local player accounts: register, log in,
  create, join, start, incorrect input, live opponent progress, both finishes,
  and leaderboard results. Temporary QA records were removed afterward.

References:

- https://react.dev/reference/react/useContext
- https://vite.dev/config/server-options.html#server-proxy
