<h1 align="center">Web Application Development</h1>

<p>Midterm: Competitive Typeracer &amp; Speed Typing Arena</p>

<h2>Music Credits</h2>

<p>
  Music: “Autumn Dreams” by Abbynoise on
  <a href="https://uppbeat.io/c/abbynoise">Uppbeat</a><br>
  License code: BXSHEQRGQ1KF7R9D
</p>

## TypeRacer

A multiplayer typing game with live progress, solo practice, and separate leaderboards for WPM and accuracy.

**[Open the game](https://hannah14295.github.io/CSCI3210-Midterm/)**

## Run through GitHub Actions

No local installation or terminal commands are needed to play the hosted game.

1. Open the repository's [Actions page](https://github.com/Hannah14295/CSCI3210-Midterm/actions).
2. Select **Test and deploy frontend**.
3. Click **Run workflow**, choose **main**, and click **Run workflow** again.
4. Wait for **backend-tests**, **frontend-tests**, and **publish-pages** to finish successfully.
5. Open [TypeRacer](https://hannah14295.github.io/CSCI3210-Midterm/).

GitHub Actions tests the project and publishes the frontend to GitHub Pages. The running backend is hosted separately on Render and must also be live. Rerunning the workflow does not redeploy the Render backend.

## Technology

React and TypeScript provide the frontend. Django REST Framework handles accounts and race APIs, Django Channels handles live updates, and Render hosts PostgreSQL and Redis-compatible Key Value storage. GitHub Actions runs checks and publishes the GitHub Pages frontend.
