---
name: hyperresearch-browser-fetch
description: >-
  Use when the hyperresearch pipeline needs to fetch a URL that the built-in
  web_extract / hpr fetch / curl cannot reach: JS-rendered SPAs, bot-walls,
  captchas, or pages that require a real browser engine to render. Drives a
  headless Chrome on your remote Mac over CDP via an SSH tunnel. This is the
  "browser-fetcher" escalation lane referenced by the hyperresearch step skills.
version: 1.0.0-hermes-port
author: OwenRay (using the proven macos-remote-admin (umbrella) pattern)
license: MIT
---

# hyperresearch browser-fetch — real browser via the remote Mac

The `hyperresearch` pipeline's `hpr fetch` runs from the local Linux host. It is good
for most pages but fails on:

- **JS-rendered SPAs** (the HTML shell has no data; the content is built client-side).
- **Bot-walls / WAFs / 403 / "Unauthorized"** that block the scraper UA or `curl`.
- **Pages that need a real rendering engine** to expose lazy-loaded or scroll-triggered content.

For those, escalate to a **real Chrome** running on your remote Mac
(`$REMOTE_HOST`, user `$REMOTE_USER`), driven over the Chrome DevTools Protocol
(CDP) through an SSH tunnel. This box only needs `chrome-remote-interface`
(npm) to drive it; the heavy rendering happens on the Mac.

## Prerequisites (all verified live 2026-08-02)

- SSH key auth to the Mac, ideally via an SSH config entry named
  `hrmac` that maps to `$REMOTE_HOST` as user `$REMOTE_USER` with your key
  as `IdentityFile`. All snippets below use `ssh hrmac …`; substitute
  `ssh -i <key> "$REMOTE_USER@$REMOTE_HOST"` if you prefer no alias.
- Chrome is installed on the Mac at
  `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`.
- Node + `chrome-remote-interface` on THIS box:
  `npm install chrome-remote-interface@0.3.1` in a scratch dir (or `npm i` from a `package.json` that pins it).
- **No elevated privileges needed** for public-source fetching: we launch
  Chrome on a NON-default profile in headless mode, which binds the debug port
  fine. (The `launchctl asuser` dance in the macos-remote-admin skill is ONLY
  to reach the GUI Keychain for saved-password autofill — not needed here.)

## Step 1 — launch a controllable Chrome on the Mac (non-default profile)

Run over SSH (key auth). A fresh profile avoids the single-instance lock on the
user's live Chrome and the Chrome 136+ "remote debug requires a non-default data
directory" error.

```bash
# Launch headless Chrome on a fresh profile (avoids the live-Chrome single-instance
# lock and the Chrome-136+ "remote debug needs a non-default data dir" error).
ssh hrmac bash -c "'
export PATH=/opt/homebrew/bin:/Applications/Google\ Chrome.app/Contents/MacOS:\$PATH
mkdir -p \$HOME/hyperresearch-browser
nohup \"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome\" \
  --user-data-dir=\$HOME/hyperresearch-browser \
  --remote-debugging-port=9223 --no-first-run --no-default-browser-check \
  --headless=new about:blank >/tmp/hrchrome.log 2>&1 & disown
'"
# Optionally record the pid locally for a precise later kill (capture it FROM the
# mac, since the mac's $HOME != this box's $HOME):
ssh hrmac \
  'pgrep -f "remote-debugging-port=9223" | head -1' > /tmp/hrchrome.pid
cat /tmp/hrchrome.pid
```

Wait ~3s, then verify the port bound:

```bash
ssh hrmac \
  'curl -s http://localhost:9223/json/version'   # -> Browser string
```

If `curl` is refused, re-launch. (Note: your live daily-driver Chrome runs with
`--remote-debugging-port=9222` but on the default profile, and due to the Chrome
136+ quirk that port does NOT actually bind — do not try to reuse it; always
launch your own on 9223.)

## Step 2 — open the SSH tunnel (background)

Use an SSH **control socket** (`-M -S`) so you can cleanly tear the tunnel down
later with `-O exit` instead of `pkill` (a bare `pkill -f` on the tunnel string
can match and kill its own shell). Always pass `-o BatchMode=yes -i <key>` — the
keyed, non-interactive auth is what keeps the tunnel from falling back to a
password prompt (it failed that way once: "Too many authentication failures").

**Make it idempotent** — if a previous run left a tunnel bound to local 9223, a
new `ssh -L` will fail with "Address already in use". So tear down any prior
tunnel first:

```bash
SOCK=/tmp/hrssh_bf.sock
# 1. close any prior tunnel on this socket (best effort)
[ -S "$SOCK" ] && ssh -O exit -S "$SOCK" "$REMOTE_USER@$REMOTE_HOST" 2>/dev/null
rm -f "$SOCK"
# 2. if something still holds local 9223, free it (covers a stale tunnel whose
#    socket we no longer have). 'fuser' is usually present; fall back to lsof.
(command -v fuser >/dev/null && fuser -k 9223/tcp 2>/dev/null) \
  || (command -v lsof >/dev/null && kill $(lsof -tiTCP:9223 -sTCP:LISTEN) 2>/dev/null)
sleep 1
# 3. open the tunnel
ssh -N -f -M -S "$SOCK" -o BatchMode=yes \
  -L 9223:localhost:9223 "$REMOTE_USER@$REMOTE_HOST"
# -f forks to background; maps localhost:9223 -> mac:9223
```

Verify from this box: `curl -s http://localhost:9223/json/version`.

## Step 3 — drive it (example: fetch rendered HTML)

`drive.mjs`:

```js
import CDP from 'chrome-remote-interface';
const target = process.argv[2];
const client = await CDP({ port: 9223 });
const { Page, Runtime, Network } = client;
await Page.enable(); await Network.enable(); await Runtime.enable();
// a real desktop UA beats most bot-walls
await Network.setUserAgentOverride({ userAgent:
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
  + "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36" });
await Page.navigate({ url: target });
// let JS render + any lazy loads settle
await new Promise(r => setTimeout(r, 4000));
const { result } = await Runtime.evaluate({
  expression: "document.documentElement.outerHTML", returnByValue: true });
process.stdout.write(result.value);
await client.close();
```

```bash
node drive.mjs "https://TARGET_URL" > page.html
wc -c page.html   # confirm you got real content, not a shell
```

For bot-walls that still block, add `Network.setExtraHTTPHeaders` (e.g.
`Accept-Language`, a referer) or navigate through a prior "home" page so the
site sees a normal session. For scroll-triggered content, dispatch wheel events
via `Input.dispatchMouseEvent` before reading the DOM.

## Step 4 — when done, clean up

Kill the Mac Chrome **from the Mac** (never via a local `pkill -f` — that matches
against this Linux box's `$HOME`, finds nothing, and leaves a stray Chrome alive;
that is the exact bug that happened once). Use the locally-captured pid, with a
pattern fallback also executed on the Mac. Then tear down the tunnel via its
control socket (`-O exit` — never a bare `pkill` on the tunnel string, which can
match and kill its own shell).

```bash
# 1. kill the controllable Chrome on the Mac (prefer the captured pid)
PID=$(cat /tmp/hrchrome.pid 2>/dev/null)
if [ -n "$PID" ]; then
  ssh hrmac "kill $PID 2>/dev/null"
fi
# fallback: ensure ANY 9223 chrome on the mac is gone
ssh hrmac \
  'for p in $(pgrep -f "remote-debugging-port=9223"); do kill $p 2>/dev/null; done'
rm -f /tmp/hrchrome.pid
# 2. close the tunnel via control socket
ssh -O exit -S "$SOCK" "$REMOTE_USER@$REMOTE_HOST" 2>/dev/null
rm -f "$SOCK"
```

## Gotchas (learned the hard way — see macos-remote-admin skill)

- **Do NOT** try to drive your live Chrome on 9222 — the port doesn't bind
  under Chrome 136+ on the default profile.
- **Saved-password autofill requires the GUI Keychain** (reaching it needs
  the `launchctl asuser` dance). We don't need it for public sources; a plain
  headless launch is enough and avoids that + the PTY dance.
- `errSecInteractionNotAllowed` in `/tmp/hrchrome.log` is harmless here — it is
  only the Keychain lookup for saved passwords, which we don't use.
- macOS 26 (Tahoe) blocks enabling Screen Sharing/VNC headlessly (TCC gate) —
  don't waste time on VNC; CDP needs no GUI.
- If you DO need your logged-in sessions (e.g. fetching a page behind a login),
  use the cookie-extraction recipe ("extract chrome cookies") in the
  `macos-remote-admin` skill — but that needs the Keychain unlocked
  in a GUI session first.

## Where this plugs into the pipeline

- **Step 2 (width-sweep)** and **Step 8/13 (gap-fill fetch)**: when `hpr fetch`
  or `web_extract` returns a shell, a 403, or a bot-wall, escalate here. Write
  the rendered HTML to `research/runs/<vault_tag>/notes/` as a source note and
  proceed as normal.
- The fetched, rendered HTML is a first-class source — cite it like any other
  (`hpr note new --tag <vault_tag> --type source --source <url> --body-file <path>`).
