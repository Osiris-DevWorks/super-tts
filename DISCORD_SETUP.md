# Discord Bot Setup

Step-by-step guide for setting up the Discord side of Super TTS. This is the
**same flow** whether you're running the Windows installer (GUI) or running
`main.py` from source (Docker / dev). Only the very last step — *where you
paste the token* — differs between the two.

If anything below feels wrong or missing, see `RAILWAY.md` (cloud deploy) or
`DOCKER.md` (local container) for runtime-specific notes.

---

## What you'll do

1. Create a Discord application + bot user.
2. Enable the privileged intents the bot needs.
3. Copy the bot token.
4. Copy your own Discord user ID (so the bot recognizes you as owner).
5. Generate an OAuth invite URL and add the bot to your server.
6. Paste the token + your owner ID into Super TTS — either via the GUI's
   Settings tab, or via a `.env` file.
7. Configure a monitored channel and try it out.

Plan for ~10 minutes, mostly clicking around the Discord Developer Portal.

---

## 1. Create a Discord application

1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
   Sign in with the Discord account you want to **own** the bot. (This account
   creates the bot and is allowed to manage it; it doesn't have to be the
   account you use to chat in your server.)
2. Click **New Application** (top right).
3. Name it whatever you want — "Super TTS", "Super TTS Local", etc. The name
   shows up in your server when the bot joins, but you can rename later.
4. Accept the terms and click **Create**.

You're now on the application's overview page.

---

## 2. Add a bot user to the application

1. Left sidebar → **Bot**.
2. *(Older accounts may need to click "Add Bot" / "Yes, do it!" — newer accounts
   already have a bot user attached.)*
3. *(Optional)* Give it an avatar and a banner. The username here is what
   appears in your server.

> **Tip:** If you want the bot to be private to you (no one else can invite it
> to their server), scroll down to **Authorization Flow** and turn off
> **Public Bot**. Recommended for personal/home installs.

---

## 3. Enable the required privileged intents

While still on the **Bot** tab, scroll down to **Privileged Gateway Intents**
and turn on **all three**:

- ✅ **Presence Intent** *(safe to leave on; not strictly required)*
- ✅ **Server Members Intent** — needed so the bot can see who is in the server.
- ✅ **Message Content Intent** — **required** so the bot can read what you
  type. Without this, TTS will never trigger because the bot literally can't
  see your messages.

Click **Save Changes** at the bottom.

> **Why this matters:** Discord locks "privileged" intents behind a checkbox
> because they expose more user data. The bot will technically connect without
> them, but slash commands like `/setup add` will work and **TTS auto-reading
> won't**, which is confusing if you're troubleshooting.

---

## 4. Copy the bot token

Still on the **Bot** tab:

1. Under your bot's username/avatar there's a **TOKEN** section.
2. Click **Reset Token** → **Yes, do it!** → **Copy**.
3. Paste it somewhere safe for now (a temporary text file is fine — you'll move
   it into Super TTS in the next step and then delete it).

> **Treat the token like a password.** Anyone with this token can fully
> impersonate your bot. Never paste it in screenshots, public Discord channels,
> or commit it to git. If you ever leak one, come back here and click **Reset
> Token** to invalidate it.

> **Each install needs its own token.** If you're running the cloud-hosted
> Super TTS *and* a local install, give them **separate tokens** (i.e., create
> two Discord applications). Discord only allows one active session per token,
> so sharing one will cause both bots to constantly disconnect each other.

---

## 5. Copy your Discord user ID (for `OWNER_ID`)

The bot uses your user ID to know that *you* are the owner — this is what
unlocks the admin slash commands (`/admin_voice grant-subscription`, etc.).

1. Open your **Discord client** (desktop or web).
2. **User Settings** (gear icon, bottom left) → **Advanced** → enable
   **Developer Mode**.
3. Close settings. Right-click your own name in any channel or member list →
   **Copy User ID**.

You should now have a long number on your clipboard like `167123456789012345`.
Paste it somewhere safe (same temp text file as your token).

> If `Copy User ID` doesn't appear in the right-click menu, Developer Mode
> didn't take. Try toggling it off and on again.

---

## 6. Generate the invite URL and add the bot to your server

You need to be the **owner** (or have **Manage Server**) on whichever server
you're inviting the bot to.

1. Back in the [Developer Portal](https://discord.com/developers/applications),
   open your application → left sidebar → **OAuth2** → **URL Generator**.
2. Under **Scopes**, tick:
   - ✅ `bot`
   - ✅ `applications.commands`
3. A **Bot Permissions** section appears below. Tick at minimum:
   - ✅ **View Channels**
   - ✅ **Send Messages**
   - ✅ **Read Message History**
   - ✅ **Embed Links**
   - ✅ **Connect** *(voice)*
   - ✅ **Speak** *(voice)*
   - ✅ **Use Voice Activity** *(optional, cleaner audio)*
4. Scroll to the bottom and copy the **Generated URL**.
5. Paste it in your browser. Pick your server from the dropdown. Click
   **Authorize**.

The bot now appears in your server's member list, **offline** until you finish
the next step.

---

## 7. Configure Super TTS with your token + owner ID

### If you installed via the Windows installer (GUI)

1. Launch **Super TTS** from the Start Menu.
2. The app opens on the **Settings** tab (it lands here automatically when no
   token is configured).
3. Fill in:
   - **Discord Token** — paste the token from step 4.
   - **Database URL** — pre-filled with the bundled Railway URL. Leave it as
     is unless you've been told otherwise.
   - **Owner ID** — paste the user ID from step 5.
   - **HuggingFace Token** *(optional)* — only needed if HuggingFace
     rate-limits your first-run model download. Get one at
     [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
     (read-only access is fine).
   - **TTS Device** — leave on `auto` unless you have a reason to force CPU
     or CUDA.
4. Click **Save**. The status line at the bottom confirms it wrote
   `%APPDATA%\Osiris DevWorks\Super TTS\.env`.
5. Switch to the **Status** tab and click **Connect**. The dot goes yellow
   ("connecting") then green ("connected") within a few seconds — though the
   *first launch* takes longer because Supertonic downloads ~1–2 GB of ONNX
   models from HuggingFace (cached after that, so subsequent launches are
   fast).

### If you're running from source / Docker / Railway

Create or edit your `.env` file with at minimum:

```ini
DISCORD_TOKEN=<paste from step 4>
DATABASE_URL=postgresql://user:pass@host:port/database
OWNER_ID=<paste from step 5>
LOG_LEVEL=INFO

# Optional
HF_TOKEN=hf_...     # avoid HuggingFace rate limits on first model download
TTS_DEVICE=auto     # auto, cpu, or cuda
```

Then `poetry run python main.py` (dev) or `docker-compose up` (Docker).

> The GUI's `.env` file lives at `%APPDATA%\Osiris DevWorks\Super TTS\.env`.
> It's the same format as the dev `.env` — interchangeable across run modes.

---

## 8. Try it out

Once the bot's online (green dot in the GUI Status tab, or
`Bot is ready! Logged in as <BotName>#1234` in the console):

1. In a Discord text channel, run:
   ```
   /tts setup add channel:#some-channel
   ```
   *(Slash commands appear in Discord's autocomplete after the bot's first
   ready event. If they don't show up immediately, wait ~30 seconds, or press
   Ctrl+R in the Discord desktop app to refresh.)*

2. **Join a voice channel** (you, in Discord — not the bot).

3. Type a message in the monitored text channel. The bot joins your voice
   channel and speaks the message.

4. Try `/tts voice list` to see all available voices, then
   `/tts voice set voice:F1` to pick a different one.

5. *(Owner only)* `/admin_voice grant-subscription user:@someone` to give a
   user access to the voice-claiming feature.

---

## Troubleshooting

### Bot is online but doesn't react to messages

99% of the time this is the **Message Content Intent**. Double-check
step 3 — the toggle has to be on *and* you have to click Save Changes.

If that's set, check the **Logs** tab in the GUI (or console output) when you
type a message. You should see `Synthesizing for user X: ...`. If not, the bot
isn't seeing the message at all — likely an intent or permission issue.

### Bot keeps disconnecting from voice ("WebSocket closed with 4006")

The same Discord token is being used by two processes simultaneously. Either:
- Stop the cloud-hosted instance while testing locally, **or**
- Create a separate Discord application (separate token) for the local install.

See the note at the end of step 4.

### Slash commands don't appear in Discord

- Wait ~30 seconds after the bot's first launch. The first slash sync is
  global and can take a moment to propagate.
- Press **Ctrl+R** in the Discord desktop app to force-refresh the command
  cache.
- Make sure you ticked `applications.commands` in step 6's scopes. If you
  forgot, re-generate the invite URL with both scopes and re-authorize.

### "Application did not respond" on a slash command

This means the bot took >3 seconds to respond. Almost always a slow database
query when the bot machine is far from the database. Recent versions of the
bot defer responses to dodge this; if you're seeing it on a recent build,
open an issue with the command name and the contents of the **Logs** tab.

### `Failed to download model` on first launch

HuggingFace rate-limited you (anonymous downloads have low quotas). Set
**HF_TOKEN** in the GUI Settings tab (or `HF_TOKEN=...` in `.env`), restart,
try again.

### Bot can't join the voice channel ("Failed to join: Connection timeout")

Run `/tts check_perms` while you're in a voice channel. The bot will dump its
effective permissions for that channel. Look for any role/channel overwrite
that's denying **Connect**.

If permissions are fine and it still times out, Discord's voice infrastructure
sometimes has hiccups — wait a minute and try again.

---

## What gets stored where

For your own peace of mind:

- **Token, DB URL, Owner ID, HF Token** — `%APPDATA%\Osiris DevWorks\Super TTS\.env`
  (or your project-root `.env` for dev). Plaintext file, your machine only.
- **Theme + UI preferences** — Windows registry under
  `HKCU\Software\Osiris DevWorks\Super TTS`.
- **Voice ONNX models** — `%USERPROFILE%\.cache\supertonic2\` (~1–2 GB,
  cached after first launch).
- **Logs** — `%LOCALAPPDATA%\Osiris DevWorks\Super TTS\logs\` (when running
  the installer build) or `./logs/` (when running from source).

Nothing leaves your machine except the requests made to Discord, Railway (if
you configured a remote DB URL), and HuggingFace (for the one-time model
download).
