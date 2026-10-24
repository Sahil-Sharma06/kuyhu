# Submission checklist

Run the automated part first:

```bash
PERSONAL_PATTERNS='yourname|your.email@example.com|yourgithubhandle' bash scripts/check_submission.sh
```

The script checks the following. Your patterns are passed through the environment and never written to the repo.

- Every git author and committer in history is anonymous or a noreply address.
- No name, email or handle matches in tracked files, commit messages, or any historical version of a file.
- No email addresses, local home-directory paths, `.env` files, keys or coverage databases are tracked.
- The README has the directory structure, local/Docker/test instructions, the AI-usage statement, and a real Vercel link.

## Manual steps (you must do these yourself)

### 1. Set an anonymous git author and rewrite existing history

The current history is authored with a personal name and email, and one commit also contains a since-removed `backend/.coverage` file that embeds local paths. Rewriting the history fixes both.

```bash
git config user.name  "Anonymous Candidate"
git config user.email "anonymous@users.noreply.github.com"

# Option A (simplest): squash everything into one fresh commit
git checkout --orphan clean && git add -A && git commit -m "Wind forecast monitor" \
  && git branch -D main && git branch -m main

# Option B (keeps the per-stage commits): rewrite identities and drop the coverage file
pip install git-filter-repo
git filter-repo --force \
  --name-callback 'return b"Anonymous Candidate"' \
  --email-callback 'return b"anonymous@users.noreply.github.com"' \
  --path backend/.coverage --invert-paths
```

Then re-run `scripts/check_submission.sh` until it passes.

### 2. Create the repository

- [ ] Create a new **public** GitHub repo with a random, non-identifying name (for example `wf-monitor-7k3q`). Use an account or organisation that does not reveal your identity, or confirm that this is allowed.
- [ ] `git remote add origin <url> && git push -u origin main`
- [ ] Check that CI (`.github/workflows/ci.yml`) goes green on GitHub.

### 3. Deploy and verify the Vercel app

- [ ] `vercel login`, then `vercel` and `vercel --prod` from the repo root (see the README).
- [ ] `bash scripts/smoke_deployed.sh https://<project>.vercel.app` passes. It hits every API route, checks the security headers, and runs Playwright against the live URL.
- [ ] Open the live URL in an **incognito** window. Check that it loads with no login wall (turn off Vercel Deployment Protection for production if it's enabled) and that both views work.
- [ ] Replace the `https://<your-project>.vercel.app` placeholder in `README.md`, commit and push.

### 4. Demo video

- [ ] Upload as **Unlisted** on YouTube.
- [ ] Open the link in an **incognito** window to confirm it plays without being signed in.
- [ ] Check that nothing personal is visible in the recording: browser profile avatar, bookmarks bar, terminal prompt (`user@host`), file paths or notifications.

### 5. Final checks and form

- [ ] `PERSONAL_PATTERNS=... bash scripts/check_submission.sh` passes.
- [ ] `make all` (or the commands in the README) passes on a clean clone: `bash scripts/verify_clean_clone.sh <public-repo-url>`.
- [ ] Fill in the submission form with the public repo URL, the live Vercel URL and the unlisted YouTube URL.
