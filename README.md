# TypeRacer midterm: milestone 1

This project currently has a Django backend with a paragraph database, an admin
page for managing paragraphs, and a read-only REST API. Multiplayer, player
registration/login, scores, and the React frontend come in later milestones.

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
Other future API views default to requiring authentication in settings. Player
Token/JWT authentication still needs to be implemented in a later milestone.

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

## Next milestone

Add the `Race` and `RaceParticipant` models and learn their relationships to
Django's existing `User` model and the `Paragraph` model. After that, add player
authentication and create/join/start race APIs before introducing WebSockets.

Useful official references:

- https://docs.djangoproject.com/en/5.2/intro/tutorial01/
- https://docs.djangoproject.com/en/5.2/intro/tutorial02/
- https://www.django-rest-framework.org/tutorial/quickstart/
