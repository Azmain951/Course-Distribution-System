# Deploying the Course Choice Form to GitHub Pages

The form (`docs/index.html`) needs two things to go live:
1. A free **Firebase** project, to store submissions (GitHub Pages only serves
   static files — it can't run a database itself).
2. **GitHub Pages** turned on for this repository, pointed at the `docs/` folder.

Total time: about 10 minutes, no coding required beyond copy/paste.

---

## Part 1 — Create the Firebase project (free)

1. Go to **https://console.firebase.google.com** and sign in with any Google account.
2. Click **Add project**. Give it a name (e.g. `cse-course-choice`). You can
   disable Google Analytics when asked — not needed here.
3. Once the project is created, click the **Web icon (`</>`)** on the project
   overview page to register a new web app. Give it any nickname. You do
   **not** need "Firebase Hosting" — leave that unchecked, since GitHub Pages
   is doing the hosting.
4. Firebase will show you a code snippet that looks like this:
   ```js
   const firebaseConfig = {
     apiKey: "AIzaSy...",
     authDomain: "cse-course-choice.firebaseapp.com",
     projectId: "cse-course-choice",
     storageBucket: "cse-course-choice.appspot.com",
     messagingSenderId: "123456789012",
     appId: "1:123456789012:web:abcdef123456"
   };
   ```
   **Copy this whole block.**

## Part 2 — Enable Firestore (the database)

1. In the left sidebar of the Firebase console, go to **Build → Firestore Database**.
2. Click **Create database**. Choose **Start in production mode**. Pick any
   region close to you (e.g. `asia-south1` for South Asia).
3. Once it's created, go to the **Rules** tab and replace the default rules
   with the contents of this repo's `firestore.rules` file. Click **Publish**.
   (These rules allow the form to read/write without requiring teachers to
   log in — see the comments in that file for the security tradeoff.)

## Part 3 — Connect the form to Firebase

1. Open `docs/index.html` in any text editor.
2. Find this block near the top of the second `<script>` tag:
   ```js
   const firebaseConfig = {
     apiKey: "YOUR_API_KEY",
     authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
     ...
   };
   ```
3. Replace it with the real config block you copied in Part 1.
4. Save the file.

## Part 4 — Turn on GitHub Pages

1. Push this repo to GitHub (see the main `README.md` for the `git remote
   add` / `git push` commands) if you haven't already.
2. On GitHub, go to your repo's **Settings → Pages**.
3. Under **Build and deployment → Source**, choose **Deploy from a branch**.
4. Under **Branch**, choose `main` and the folder `/docs`. Click **Save**.
5. GitHub will give you a URL like:
   ```
   https://<your-username>.github.io/<repo-name>/
   ```
   That's the link to share with all 58 teachers. It can take a minute or two
   to go live the first time.

## Verifying it works

1. Open the URL from Part 4.
2. If you see a red "Setup needed" banner, the Firebase config in
   `docs/index.html` wasn't saved correctly — double check Part 3.
3. If the form loads normally, pick a teacher name, submit a test set of
   choices, then switch to the **All submissions** tab — you should see it
   listed. Check the Firebase console (**Firestore Database → Data**) too —
   you should see a document under `app_data` named `choice_response:<sl_no>`.
4. Delete your test submission from the Firestore console before sending the
   real link out.

## Updating the form later

Any time you edit `docs/index.html` (new teacher added, course list changed,
etc.), just commit and push again — GitHub Pages redeploys automatically
within a minute or two of every push to `main`.
