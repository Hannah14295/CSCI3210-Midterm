# TypeRacer midterm: backend learning milestones

For GitHub Pages + Render hosting, follow the prepared checklist in [DEPLOYMENT.md](DEPLOYMENT.md).

This project currently has a Django backend with paragraph and race models, an admin
page for managing them, a read-only paragraph REST API, and player registration,
login, and current-user APIs. Live typing, saved WPM results, and a historical
leaderboard are available through a developer test page and the React/TypeScript
game frontend in `frontend/`.

## Run the game frontend

Keep two PowerShell terminals open in the repository root:

```powershell
# Terminal 1: Django backend
.\.venv\Scripts\python.exe backend\manage.py runserver
```

```powershell
# Terminal 2: React frontend
npm --prefix frontend run dev
```

Open http://127.0.0.1:5173/. Log in with your existing account, or register a regular
player account. Pick a passage, create a race, share its ID, and start when the
participants have joined. The host can also run a solo practice race. Finish
the passage's full length to save a result, then open Leaderboard in the navigation.
Typing is forward-only: mistakes reduce accuracy and WPM, and the first finisher ends the race.

The game frontend is separate from http://127.0.0.1:8000/admin/. It replaces the
manual API forms with user-facing buttons and forms. For two different players,
open another tab/browser and log in as a different account; tokens are scoped
to each tab's sessionStorage. Some duplicated tabs inherit the original tab's
session storage, so sign out in the duplicate before logging in as another user.

Dependencies are already installed locally. On a new checkout run
`npm --prefix frontend ci` before starting. Build/type-check with:

```powershell
npm --prefix frontend run build
```

See `frontend/README.md` for the frontend code map and request flow. This is a
local development setup; serving the production build with Django and deploying
it require additional hosting configuration.

## Run the project you already have

Open PowerShell in this project folder. These commands use the virtual
environment's Python directly, so you do not need to activate it or change
PowerShell's execution policy.

```powershell
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

Leave that terminal running. Open:

- http://127.0.0.1:8000/api/paragraphs/ to see the saved paragraphs.
- http://127.0.0.1:8000/api/paragraphs/1/ to see the sample paragraph.
- http://127.0.0.1:8000/admin/ to manage paragraphs after creating an admin account.

Stop the server with Ctrl+C. This is Django's local development server.

## Create your own admin account

In a second PowerShell terminal, in the same project folder, run:

```powershell
.\.venv\Scripts\python.exe backend\manage.py createsuperuser
```

Choose your username and password at the prompts. The password will not be
displayed while you type it. You can leave the email blank for this local project.
No admin account or shared password has been created for you.

1. Log in at http://127.0.0.1:8000/admin/.
2. Under Races, select Paragraphs, then Add paragraph.
3. Enter a title and at least 20 characters of typing text, then Save.
4. Refresh http://127.0.0.1:8000/api/paragraphs/.
5. Find your paragraph inside `results`.

The admin page and the API read the same SQLite database. Creating text through
the admin and then seeing it through the API demonstrates the complete data flow.

## Follow one browser request through the code

When you visit `/api/paragraphs/`:

1. `backend/config/urls.py` sends URLs starting with `api/` to the races app.
2. `backend/races/urls.py` maps `paragraphs/` to `ParagraphViewSet` using a router.
3. `backend/races/views.py` queries saved `Paragraph` objects.
4. `backend/races/models.py` describes the table and its fields.
5. `backend/races/serializers.py` chooses the fields exposed to the browser.
6. Django REST Framework returns a response containing those fields as JSON.

Visiting in a browser shows REST Framework's browsable API. A JavaScript `fetch`
request can receive the same information as JSON. You can also use
http://127.0.0.1:8000/api/paragraphs/?format=json to see the JSON directly.

The list response has `count`, `next`, `previous`, and `results`. Pagination limits
each page to 20 paragraphs. A paragraph object looks like:

```json
{
  "id": 1,
  "title": "First practice race",
  "text": "The small blue car waited at the starting line..."
}
```

The text above is shortened just for this example.

## What each Django term means

| Term | Meaning here |
| --- | --- |
| Project (`config`) | Settings and top-level URL routing for the backend |
| App (`races`) | A Python package containing a related set of features |
| Model | A Python class describing stored data |
| Migration | A versioned instruction for creating or changing database tables |
| Serializer | Selects/converts API fields; can validate incoming API data when writes are added |
| ViewSet | Handles related API actions, such as listing and retrieving paragraphs |
| Router | Generates URL patterns for a ViewSet |
| Admin | Django's built-in interface for trusted staff to manage data |

Paragraphs can be read without signing in. The public API rejects creation,
editing, and deletion; paragraph writes go through the staff-only admin page.
Other API views default to requiring authentication in settings. Token
authentication is configured for player requests; session authentication also
supports the browsable API when you are logged in through the admin.

## Database changes

`makemigrations` writes migration files based on changes to models.
`migrate` applies those files to the database. Commit migration files to Git;
do not commit your local database.

```powershell
.\.venv\Scripts\python.exe backend\manage.py makemigrations
.\.venv\Scripts\python.exe backend\manage.py migrate
```

## Checks

```powershell
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py test races
```

Tests cover reading saved paragraphs, missing records, blocked API writes, saving
through the admin, and rejection of paragraphs shorter than 20 characters. They
use a separate temporary test database.

## Set up again on another computer

Use Python 3.14, as used for this local setup, and run from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(50))"
```

Paste the generated value after `DJANGO_SECRET_KEY=` in `backend/.env`, replacing
the placeholder. Then:

```powershell
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py loaddata sample_paragraphs
.\.venv\Scripts\python.exe backend\manage.py createsuperuser
.\.venv\Scripts\python.exe backend\manage.py runserver
```

The sample fixture creates paragraph ID 1. Load it on a fresh database; reloading
it replaces changes to that sample record. You can also skip it and add your own
paragraphs in the admin.

`.env` holds your local secret and development options; `.env.example` documents
the expected variables. `.gitignore` excludes `.env`, the database, the virtual
environment, and temporary files. A generated local secret is already configured
on this computer. Debug mode is enabled for local learning.

## Milestone 2: Race model

Open http://127.0.0.1:8000/admin/races/race/ and choose Add race. Select an existing
paragraph and your user account as host, leave status as Waiting, and save.

`Race` in `backend/races/models.py` stores two foreign keys: `paragraph` points to
a Paragraph, and `host` points to a User. Multiple races can reference the same
paragraph or host. `on_delete=models.PROTECT` prevents deletion of a paragraph or
host while a race references it. The database stores the referenced IDs rather
than duplicating the passage or account. Editing a paragraph therefore changes
the passage seen through its related races; immutable race text will need attention
when gameplay and historical results are implemented.

`Status` defines the available labels: Waiting, Running, and Finished. New races
default to Waiting. Choices validate values in Django forms/model validation;
they do not implement race transitions or timers. Status is manually editable
in the admin at this stage.

`related_name` provides reverse access: `paragraph.races.all()` finds races using
that paragraph, and `user.hosted_races.all()` finds races hosted by that user.
`Meta.ordering` lists newest races first. `__str__` supplies a readable label.

`RaceAdmin` in `backend/races/admin.py` defines list columns, a status filter, and
search by paragraph title or host username. `list_select_related` loads the
paragraph and host alongside each race to avoid separate database queries per row.

`backend/races/migrations/0002_race.py` records the table creation. It has already
been applied locally using `migrate`. No race API endpoints exist yet.

## Milestone 3: Participants

`RaceParticipant` connects one user (`player`) to one race (`race`) and records
`joined_at`. Its database constraint prevents the same player entering the same
race twice. Open http://127.0.0.1:8000/admin/races/raceparticipant/ to add an entry.
Hosts are not automatically entered as competitors yet.

## Milestone 4: Player authentication

| Method and URL | Input | Result |
| --- | --- | --- |
| POST `/api/auth/register/` | username, password | 201: user (id, username) and token |
| POST `/api/auth/login/` | username, password | 200: user (id, username) and token |
| GET `/api/auth/me/` | Authorization header | 200: current user's id and username |

Register and login accept JSON or form data. Validation errors, including invalid
login credentials, return 400. Missing or invalid tokens on protected endpoints
return 401. Register and login share a per-IP limit of 30 requests per minute
using Django's local cache; exceeding it returns 429. A shared cache will be
needed if deployed with multiple workers.

For a browser demonstration, open http://127.0.0.1:8000/api/auth/register/ and use
the POST form near the bottom to create a new practice account. The top may say
"Method GET not allowed" (405): registration accepts POST because it creates
data, whereas entering an address in the browser sends GET. Use the HTML form
tab if available. Then try the login POST form at
http://127.0.0.1:8000/api/auth/login/ using those same credentials.

Both responses include a token. Treat it like a password. Receiving one does not
automatically attach it to later browser requests or sign you into Django admin.
New registered players cannot enter the admin. Your existing admin account can
also log in through this API without registering again.

To see token authentication work, run this in a second PowerShell terminal while
the server is running. Enter a registered username and password at the prompt:

```powershell
$playerCredentials = Get-Credential -Message 'Enter your game account username and password'
$loginBody = @{
    username = $playerCredentials.UserName
    password = $playerCredentials.GetNetworkCredential().Password
} | ConvertTo-Json
$loginResult = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/auth/login/' -ContentType 'application/json' -Body $loginBody
$authHeaders = @{ Authorization = "Token $($loginResult.token)" }
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/auth/me/' -Headers $authHeaders
Remove-Variable playerCredentials,loginBody,loginResult,authHeaders
```

The last request should show your id and username. It doesn't send a username
to choose an account: the backend identifies you from the token. In the browser,
`me/` can instead identify your admin session if you are already signed in there.

The new `accounts` app keeps account features separate from race features:

- `accounts/urls.py` maps the three endpoint addresses to views.
- `accounts/serializers.py` validates registration input, checks Django's password
  rules, hashes passwords via `create_user`, and limits user output to id/username.
- `accounts/views.py` saves an account and token together in a transaction,
  checks login credentials through Django, and returns `request.user` for `me/`.
- `config/settings.py` enables DRF's existing token app and authentication classes.
- `config/urls.py` includes the accounts URLs under `/api/auth/`.

Running `migrate` created DRF's token tables using migrations supplied by that
library. We reused Django's existing User model, so no new account model or
project migration was needed for this milestone.

These are DRF's basic reusable tokens: one per user, no automatic expiry, and
login reuses the existing token. Logout/revocation is not implemented yet. Use
HTTPS when deploying so passwords and tokens are encrypted in transit.

Run all current tests:

```powershell
.\.venv\Scripts\python.exe backend\manage.py test accounts races
```

## Next milestone

Review the working game against the assignment, improve race timeout/disconnect
handling, and prepare the project for submission or deployment as needed.

## Milestone 5: Race APIs

All race endpoints require a token or a logged-in admin session. These lobbies
are discoverable by all authenticated players; they are not private rooms.

| Method and URL | Meaning | Input |
| --- | --- | --- |
| GET `/api/races/` | List races (paginated) | None |
| POST `/api/races/` | Create a waiting race and enter its host | `{"paragraph": 1}` |
| GET `/api/races/{id}/` | Read one race and its participants | None |
| POST `/api/races/{id}/join/` | Enter as the current player | None |
| POST `/api/races/{id}/start/` | Start as the host | None |

Replace `{id}` with an actual race ID. The backend uses the authenticated user
for host/player identity. Submitted host, player, status, and start-time values
cannot override that identity or bypass the action rules. General race editing
and deletion are not exposed through this API.

New API-created races automatically include their host as a participant. Existing
admin-created races are unchanged; enter the host using the join endpoint if
they will compete. Repeating join while waiting returns the existing entry
(200 rather than the initial 201). Once running or finished, join returns 409.
Only the host can start (403 otherwise); the race must be waiting (409 otherwise).
Start records a server-generated `started_at` and changes status to Running. It
does not yet initiate real-time messages, a countdown, or scoring. Repeating
start cannot reset the timestamp. Missing races return 404, invalid paragraphs
400, missing/invalid token authentication 401, and unsupported methods 405.

Try it in the browser while signed into the admin in that same browser:

1. Open http://127.0.0.1:8000/api/races/.
2. In the POST form, select a paragraph and click POST. The response's `id` is
   your new race ID. You should also see yourself in `participants`.
3. Open `/api/races/YOUR_ID/join/` and use its POST button. If you are the host,
   this returns your existing entry. Opening this address initially sends GET,
   so "Method GET not allowed" is expected before you submit POST.
4. Open `/api/races/YOUR_ID/start/` and click POST. The response should show
   `"status": "running"` and a non-null `started_at`.
5. Try POST again: expect 409, because the race is already started.

Registering/logging in through the token API does not create a browser session.
To try another regular player's token from PowerShell, use the login example
above and pass its `$authHeaders` with each request. For instance:

```powershell
# Run after creating $authHeaders, before removing those variables.
$raceBody = @{ paragraph = 1 } | ConvertTo-Json
$newRace = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/races/' -Headers $authHeaders -ContentType 'application/json' -Body $raceBody
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/races/$($newRace.id)/join/" -Headers $authHeaders
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/races/$($newRace.id)/start/" -Headers $authHeaders
```

### Follow a create request

The future React button will send HTTP just like the POST form does. A request
has a method (POST), URL (`/api/races/`), headers (such as Authorization and
Content-Type), and optionally a body (`{"paragraph": 1}`).

1. `config/urls.py` passes `/api/` requests to the races URLs.
2. `races/urls.py` uses the DRF router to select the RaceViewSet create action.
3. Authentication identifies `request.user`; permission checking rejects guests.
4. `RaceSerializer` checks the paragraph exists and selects permitted input fields.
5. `RaceViewSet.perform_create` calls `services.create_race` using `request.user`.
6. The service saves the race and participant together in a transaction. If
   either operation fails, neither save is committed.
7. The serializer converts the result into response data; DRF renders JSON for
   API clients (or its HTML developer page for a browser).
8. HTTP status 201 tells the caller creation succeeded. React will use that
   response to display the new lobby.

`races/services.py` contains create/join/start rules. Join and start use a
transaction and lock the race row on databases supporting row locks. SQLite
does not support those row locks; its IMMEDIATE transaction option in settings
serializes write transactions instead. This small local project uses SQLite;
multi-worker production operation will need a deployment/database review.

The admin remains a trusted manual management interface; directly editing its
status field bypasses the API action rules and does not run the start service.
Use the API start action to create a consistent running race and start timestamp.

Migration `0004_race_started_at.py` adds the nullable start timestamp. Older races
retain their existing state and have no start timestamp until started through
the API from Waiting.

## Milestone 6: Live race connection

Channels and Daphne now enable WebSockets using the same command as before:

```powershell
.\.venv\Scripts\python.exe backend\manage.py runserver
```

Fully stop the old server and restart it after this installation. The startup
output should mention ASGI/Daphne. No new database migration is needed here:
WebSocket routing changes how messages travel, not the saved table structure.

### Two-tab demonstration

1. Sign into the admin at http://127.0.0.1:8000/admin/.
2. Create a new race through http://127.0.0.1:8000/api/races/ using its POST form.
   This automatically enters you as a participant. Note its returned ID.
3. Open http://127.0.0.1:8000/dev/socket/ in two tabs of that same browser.
4. Enter that race ID in both tabs and click Connect in each. Leave Token blank
   when using your admin login. Both should say Connected as your username.
5. Send a test message from one tab. It should appear in both tabs immediately.
6. Disconnect one tab. The other remains usable. Reconnect to receive new messages;
   earlier messages are not stored or replayed.

The demo page is only available while DEBUG is True. It now also tests validated
typing progress (see milestone 7 below), but not WPM scores. Two tabs signed into the same account are two connections
belonging to one player, not two different participants. To test two different
players, use another browser/private window and a different registered account's
token. That account must first join the same race using its authenticated API.
If using an admin-created race, add yourself as a participant before connecting.

### Protocol

Connect to `ws://127.0.0.1:8000/ws/races/ID/` (use `wss` on HTTPS). Django's session
cookie authenticates browsers already signed into admin. Otherwise the server
sends `{"type":"auth.required"}`; send this frame within 10 seconds:

```json
{"type":"authenticate","token":"YOUR_API_TOKEN"}
```

The token travels inside the connection, not in a URL or local storage. The demo
clears the token field when connecting. Only authenticated, active accounts with
a RaceParticipant record for this race can join its broadcast group. Do not use
an account ID as a substitute for authentication.

Successful entry yields a `connected` message with race ID and player identity.
Then send:

```json
{"type":"demo.message","text":"Hello race!"}
```

Every authorized socket in that race, including the sender, receives a message
with type, race ID, player (id and username), and text. The backend supplies race
and player identity; client-supplied identities and score fields are ignored.
Different races use different broadcast groups. Demo messages can be sent in
any race status and do not affect gameplay, save progress, or calculate WPM.
Join/start HTTP actions now broadcast `race.updated` after committing their changes.

Membership, active-account status, and token validity are rechecked when sending
or delivering room messages. Invalid JSON and invalid message shapes return an
error packet. Frames over 16384 characters close with code 1009; binary frames
close with 1003. Each connection permits up to 10 incoming messages per second
(including authentication) before closing with code 4429. Other close codes:

- 4401: authentication missing, invalid, or timed out.
- 4403: account not authorized for this race (or access removed).
- 1000: normal closure.

### Files and concepts

- `config/asgi.py` sends HTTP requests to Django and WebSockets to Channels. It
  checks the connection's Origin against allowed hosts and loads session users.
- `races/routing.py` maps the WebSocket address to `RaceConsumer`.
- `races/consumers.py` handles connect, authenticate, receive, broadcast, and
  disconnect. Consumers handle ongoing connections; HTTP views handle requests.
- `CHANNEL_LAYERS` in settings is the message delivery mechanism. A race has a
  group such as `race.7`; group_send reaches that group's current connections.
- `races/templates/races/socket_test.html` is the small browser test interface.
- `races/test_websockets.py` tests the ASGI application using simulated clients.

The channel layer currently lives in memory in one server process. Restarting
the server drops connections and pending messages. A deployed server with more
than one process needs a shared layer such as Redis; in-memory delivery cannot
communicate between processes. Use HTTPS/WSS when hosting outside localhost.

Reference: https://channels.readthedocs.io/en/stable/topics/channel_layers.html

## Milestone 7: Validated typing progress

Use a **new waiting race** created through the API, connect both tabs on
http://127.0.0.1:8000/dev/socket/, then open the race's start link and click POST
as its host. The start broadcast enables typing in both connected tabs. Type
in one tab: the passage highlights matches/mistakes locally, and both tabs show
the backend's progress and accuracy. Two tabs for the same account share one
participant's progress, not two independent competitors.

`start_race` now copies the paragraph into `Race.race_text`. This fixes the target
for the race, so editing the original Paragraph afterward won't change an active
race. Older running races with no saved copy need to be replaced with a new race
for this demonstration. Manually changing status in admin does not run start logic.

The browser sends its latest complete input buffer at most every 250 milliseconds:

```json
{"type":"typing.update","text":"The small"}
```

`consumers.py` identifies the sender and calls `services.update_typing`. That
service verifies membership, running state, the server start timestamp, and input
length/type. Each update must preserve the previously saved text as its prefix;
deleting or changing earlier characters is rejected. Input cannot exceed the
target length or 2000 characters. It updates the participant in a transaction
and broadcasts `progress.updated` only after saving successfully.

The outgoing event contains player identity, race ID, revision, and:

- `correct_prefix`: number of consecutive correct characters from the beginning.
- `progress`: entered characters / paragraph length * 100, rounded to two decimals.
- `correct_characters`: matching characters at the same positions in the input.
- `accuracy`: correct_characters / current input length * 100. Empty input is
  defined as 100% accuracy with 0% progress. Earlier characters cannot be corrected.
- `complete`: true when the input reaches the saved target's length, even with errors.
- `difference`: a suffix replacement (`start`, `delete_count`, `insert`) comparing
  the old and new buffer. The server computes this rather than trusting a delta.

For target `hello` and input `hexlo`, correct_prefix is 2, progress is 100%, and
accuracy is 80% (four of five positions match). The player finishes with this
mistake preserved. Milestone 8 saves the result and ends the race.

`typed_text` and `revision` are persisted on RaceParticipant. Every accepted update
increments revision so the browser can ignore older progress events delivered
out of order. A reconnect receives the latest race snapshot and `your_text` to
restore its input. Other players' full buffers are not included in snapshots,
but change events include the string differences required for this assignment.

Start/join broadcast a `race.updated` snapshot so connected tabs see the updated
status, shared paragraph, and participants without polling. Progress broadcasts
stay within the race group, with access checked on delivery. Highlighting is a
local preview; displayed progress statistics come from the backend.

Files to inspect:

- `races/typing.py`: plain Python text comparison and difference functions.
- `races/services.py`: rules and database changes for typing updates and start.
- `races/events.py`: race snapshots and group broadcasting.
- `races/consumers.py`: receives packets and calls the service.
- `races/serializers.py`: includes participant metrics and the race paragraph.
- `races/templates/races/socket_test.html`: the test input, highlighting, and bars.
- `races/migrations/0005_...py`: adds race_text, typed_text, and revision fields.

An authenticated client can still paste or programmatically submit text. Comparing
text and using server identity is not proof that a human physically typed it;
this milestone is input validation, not an anti-cheat system.

## Milestone 8: WPM, finish results, and leaderboard

WPM uses five characters as one standardized word, including spaces/punctuation:

```text
WPM = (correct characters / 5) / elapsed minutes
    = correct characters * 12 / elapsed seconds
```

For example, 300 correct characters in 60 seconds is 60 WPM. The live value uses
the latest accepted input and the server's shared race start time. It updates
when input or snapshots arrive, not on a standalone ticking timer. Network and
the demo's up-to-250ms send delay are included in measured time. Final WPM uses
the number of matching characters at their target positions, so errors reduce speed.

`services.update_typing` records `finished_at`, `elapsed_seconds`, and `wpm` on
RaceParticipant on its first full-length submission. Server timestamps supply the duration;
client-supplied scores/times are ignored. Decimal arithmetic rounds WPM to two
places. A finished participant cannot change the result by sending more typing
updates (409). There is one result per player/race entry; a new attempt requires
a new race. Reconnecting restores the same saved result.

The first participant to finish ends the race for everyone. The race status
becomes Finished and further typing submissions are rejected. Finish updates broadcast
both progress.updated (with final WPM and finished_at) and race.updated snapshots.
The React page disables everyone's input; the winner sees "result saved!".
If nobody finishes, the race stays Running; timeout/abandonment handling is not implemented yet.

GET http://127.0.0.1:8000/api/leaderboard/ lists historical completed attempts:

- Public, read-only, paginated (20 per page).
- Ordered by descending saved WPM; ties use earlier finish timestamp, then entry ID.
- Each row includes rank, race ID, player ID/username, final WPM, duration, and finish time.
- Multiple attempts by one player are separate rows, not one personal-best row.
- The winner's completed attempt appears; losers retain partial progress without a completed result.
- Unfinished participants and old entries without a saved result are excluded.
- Rank is global across pages; ties get consecutive ranks in the stated order.

Try it by creating a fresh race through the API, connecting on the test page,
starting through its API link, and typing the complete paragraph. Look for WPM
and "result saved!", then open the leaderboard link. Refreshing/reconnecting
should show the same final WPM. Prior practice buffers are not converted into
scored results retroactively; complete a new race to create one.

Accuracy measures matching positions divided by all entered characters. Input is
append-only, so final accuracy can stay below 100% and mistakes cannot be erased.
WPM comparisons across different
paragraph lengths/difficulties are a simple global historical leaderboard, not
a normalized competitive rating or an anti-cheat system.

Key code locations:

- `typing.py`: calculate_wpm math.
- `services.py`: timing, finish persistence, result locking, and race completion.
- `serializers.py`: live metrics and leaderboard output.
- `views.py`: LeaderboardViewSet and sorted/ranked database query.
- `urls.py`: registers `/api/leaderboard/`.
- `admin.py`: shows saved WPM and finish time as read-only values.
- `migrations/0006_...py`: adds the three result fields.
- `test_results.py`: formula, timing, immutable results, and leaderboard tests.

Useful official references:

- https://docs.djangoproject.com/en/5.2/intro/tutorial01/
- https://docs.djangoproject.com/en/5.2/intro/tutorial02/
- https://www.django-rest-framework.org/tutorial/quickstart/
