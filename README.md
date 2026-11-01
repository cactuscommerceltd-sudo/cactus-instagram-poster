# Cactus Commerce Instagram poster

Each morning the daily news agent adds a folder to `posts/` (for example `posts/2026-11-02`)
containing `slide-01.jpg`, `slide-02.jpg`, … and `caption.txt`.

That starts the **Post to Instagram** workflow, which shows the slides and caption, then
**waits for your approval** (the `instagram` environment requires your review).
Approve it in the GitHub app and it publishes the carousel. Reject it and nothing is posted.

- **Check Instagram connection** (Actions tab, Run workflow): safe test, posts nothing.
- Secrets used: `IG_ACCESS_TOKEN`, `IG_USER_ID` (never stored in files).
