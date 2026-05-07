"""Help tab — in-app documentation.

A QTextBrowser rendering rich-text help: Discord setup walkthrough, GUI
usage, slash command reference, troubleshooting. Mirrors the content of
DISCORD_SETUP.md but lives in the app so users never have to leave it.

QTextBrowser inherits link/text colors from the active palette, so this
tab is theme-aware without any per-theme logic of its own.
"""
from __future__ import annotations

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget


_HELP_HTML = """
<style>
  h1 { margin-top: 0; }
  h2 { margin-top: 1.5em; padding-top: 0.3em; }
  h3 { margin-top: 1.2em; }
  code { background: rgba(127, 127, 127, 0.18); padding: 1px 5px; border-radius: 3px; }
  pre { background: rgba(127, 127, 127, 0.12); padding: 8px 12px; border-radius: 4px; }
  table { border-collapse: collapse; margin: 0.5em 0; }
  th, td { padding: 6px 12px; text-align: left; vertical-align: top; }
  th { border-bottom: 1px solid rgba(127, 127, 127, 0.4); }
  td { border-bottom: 1px solid rgba(127, 127, 127, 0.18); }
  blockquote { border-left: 3px solid rgba(127, 127, 127, 0.4); margin: 0.6em 0; padding: 0.2em 0.8em; }
</style>

<h1>Super TTS &mdash; Help</h1>

<p>Everything you need to get the bot running and use it from inside Discord.
Plan for ~10 minutes the first time, mostly clicking around the Discord
Developer Portal.</p>

<h3>Quick start</h3>
<ol>
  <li>Create a Discord application + bot, copy the token.</li>
  <li>Paste the token (and your Discord user ID) into the Settings tab, click Save.</li>
  <li>Click Connect on the Status tab. First launch downloads ~1&ndash;2&nbsp;GB of voice models &mdash; subsequent launches are instant.</li>
</ol>

<hr/>

<h2>Discord setup</h2>

<h3>1. Create a Discord application</h3>
<ol>
  <li>Open the
    <a href="https://discord.com/developers/applications">Discord Developer Portal</a>.
    Sign in with the Discord account you want to <b>own</b> the bot. (This
    account creates the bot and is allowed to manage it; it doesn't have to
    be the account you use to chat in your server.)</li>
  <li>Click <b>New Application</b> (top right).</li>
  <li>Name it whatever you want &mdash; "Super TTS", "Super TTS Local", etc.
    The name shows up in your server when the bot joins, but you can rename
    later.</li>
  <li>Accept the terms and click <b>Create</b>.</li>
</ol>

<h3>2. Add a bot user to the application</h3>
<ol>
  <li>Left sidebar &rarr; <b>Bot</b>.</li>
  <li>Older accounts may need to click "Add Bot" / "Yes, do it!" &mdash;
    newer accounts already have a bot user attached.</li>
  <li>(Optional) Give it an avatar and a banner. The username here is what
    appears in your server.</li>
</ol>
<blockquote>
  <b>Tip:</b> If you want the bot to be private to you (no one else can
  invite it to their server), scroll down to <b>Authorization Flow</b> and
  turn off <b>Public Bot</b>. Recommended for personal/home installs.
</blockquote>

<h3>3. Enable the required privileged intents</h3>
<p>While still on the <b>Bot</b> tab, scroll down to <b>Privileged Gateway
Intents</b> and turn on all three:</p>
<ul>
  <li><b>Presence Intent</b> &mdash; safe to leave on; not strictly required.</li>
  <li><b>Server Members Intent</b> &mdash; needed so the bot can see who is
    in the server.</li>
  <li><b>Message Content Intent</b> &mdash; <b>required</b> so the bot can
    read what you type. Without this, TTS will never trigger because the bot
    literally can't see your messages.</li>
</ul>
<p>Click <b>Save Changes</b> at the bottom.</p>
<blockquote>
  <b>Why it matters:</b> Discord locks "privileged" intents behind a checkbox
  because they expose more user data. The bot will technically connect
  without them, but slash commands like <code>/tts setup add</code> will
  work and TTS auto-reading <i>won't</i>, which is confusing if you're
  troubleshooting.
</blockquote>

<h3>4. Copy the bot token</h3>
<ol>
  <li>Under your bot's username/avatar there's a <b>TOKEN</b> section.</li>
  <li>Click <b>Reset Token</b> &rarr; <b>Yes, do it!</b> &rarr; <b>Copy</b>.</li>
  <li>Paste it somewhere safe for now (a temporary text file is fine &mdash;
    you'll move it into Super TTS in the next step and then delete it).</li>
</ol>
<blockquote>
  <b>Treat the token like a password.</b> Anyone with this token can fully
  impersonate your bot. Never paste it in screenshots, public Discord
  channels, or commit it to git. If you ever leak one, come back here and
  click Reset Token to invalidate it.
</blockquote>
<blockquote>
  <b>Each install needs its own token.</b> If you're running cloud-hosted
  Super TTS <i>and</i> a local install, give them separate tokens (i.e.,
  create two Discord applications). Discord only allows one active session
  per token, so sharing one will cause both bots to constantly disconnect
  each other.
</blockquote>

<h3>5. Copy your Discord user ID (for Owner ID)</h3>
<p>The bot uses your user ID to know that <i>you</i> are the owner &mdash;
this is what unlocks the admin slash commands
(<code>/tts admin-voice grant-subscription</code>, etc.).</p>
<ol>
  <li>Open your Discord client (desktop or web).</li>
  <li><b>User Settings</b> (gear icon, bottom left) &rarr; <b>Advanced</b>
    &rarr; enable <b>Developer Mode</b>.</li>
  <li>Close settings. Right-click your own name in any channel or member
    list &rarr; <b>Copy User ID</b>.</li>
</ol>
<p>You should now have a long number on your clipboard like
<code>167123456789012345</code>. Paste it somewhere safe (same temp text
file as your token).</p>
<blockquote>
  If "Copy User ID" doesn't appear in the right-click menu, Developer Mode
  didn't take. Try toggling it off and on again.
</blockquote>

<h3>6. Generate the invite URL and add the bot to your server</h3>
<p>You need to be the <b>owner</b> (or have <b>Manage Server</b>) on
whichever server you're inviting the bot to.</p>
<ol>
  <li>Back in the
    <a href="https://discord.com/developers/applications">Developer Portal</a>,
    open your application &rarr; left sidebar &rarr; <b>OAuth2</b>
    &rarr; <b>URL Generator</b>.</li>
  <li>Under <b>Scopes</b>, tick <code>bot</code> and
    <code>applications.commands</code>.</li>
  <li>A <b>Bot Permissions</b> section appears. Tick at minimum:
    <ul>
      <li>View Channels</li>
      <li>Send Messages</li>
      <li>Read Message History</li>
      <li>Embed Links</li>
      <li>Connect <i>(voice)</i></li>
      <li>Speak <i>(voice)</i></li>
      <li>Use Voice Activity <i>(optional, cleaner audio)</i></li>
    </ul>
  </li>
  <li>Scroll to the bottom and copy the <b>Generated URL</b>.</li>
  <li>Paste it in your browser. Pick your server from the dropdown. Click
    <b>Authorize</b>.</li>
</ol>
<p>The bot now appears in your server's member list, <b>offline</b> until
you finish the next step.</p>

<h3>7. Configure Super TTS with your token + owner ID</h3>
<ol>
  <li>Go to the <b>Settings</b> tab in this app.</li>
  <li>Fill in:
    <ul>
      <li><b>Discord Token</b> &mdash; paste the token from step 4.</li>
      <li><b>Database URL</b> &mdash; pre-filled with the bundled URL.
        Leave it as is unless you've been told otherwise.</li>
      <li><b>Owner ID</b> &mdash; paste the user ID from step 5.</li>
      <li><b>HuggingFace Token</b> <i>(optional)</i> &mdash; only needed if
        HuggingFace rate-limits your first-run model download. Get one at
        <a href="https://huggingface.co/settings/tokens">huggingface.co/settings/tokens</a>
        (read-only access is fine).</li>
      <li><b>TTS Device</b> &mdash; leave on <code>auto</code> unless you
        have a reason to force CPU or CUDA.</li>
    </ul>
  </li>
  <li>Click <b>Save</b>. The status line at the bottom confirms it wrote
    <code>%APPDATA%\\Osiris DevWorks\\Super TTS\\.env</code>.</li>
  <li>Switch to the <b>Status</b> tab and click <b>Connect</b>. The dot goes
    yellow ("connecting") then green ("connected") within a few seconds
    &mdash; though the <i>first launch</i> takes longer because Supertonic
    downloads ~1&ndash;2&nbsp;GB of ONNX models from HuggingFace (cached
    after that, so subsequent launches are fast).</li>
</ol>

<hr/>

<h2>Using the app</h2>

<h3>Status tab</h3>
<p>One panel for everything operational: the bot's connection state on top,
the live log feed below.</p>
<p>The dot at the top has four colors:</p>
<ul>
  <li><b>Gray</b> &mdash; idle, not connected.</li>
  <li><b>Yellow</b> &mdash; connecting, running migrations, logging in.</li>
  <li><b>Green</b> &mdash; bot is connected and ready to handle commands.</li>
  <li><b>Red</b> &mdash; failed; check the log feed below for the cause.</li>
</ul>
<p>The <b>Connect</b> button starts the bot in a worker thread;
<b>Disconnect</b> shuts it down cleanly. After Disconnect, click Connect
again to bring it back up &mdash; no app restart needed.</p>
<p>The lower half is the live log feed. Every line the bot emits flows
here as it happens. The buffer holds the last 2000 lines. Use the
<b>Min level</b> dropdown at the top of the feed to hide noise from the
viewer (display-side only). Click <b>Export</b> to dump the buffer to a
text file when you need to send a bug report.</p>

<h3>Settings tab</h3>
<p>This is the only place you enter credentials. Values are saved to the
<code>.env</code> file at
<code>%APPDATA%\\Osiris DevWorks\\Super TTS\\.env</code> &mdash; the same
file the bot reads on startup. The Theme dropdown is purely cosmetic;
the credential fields need an app restart to take effect (the bot reads
them at thread launch).</p>

<h3>About tab</h3>
<p>Version + project info. Nothing actionable.</p>

<hr/>

<h2>Discord slash commands</h2>

<p>All commands live under the <code>/tts</code> namespace. Type
<code>/tts</code> in any channel and Discord's autocomplete will show
everything available. Most commands reply with an ephemeral message only
you can see.</p>

<h3>Voice channel</h3>
<table>
  <tr><th style="width:38%">Command</th><th>What it does</th></tr>
  <tr>
    <td><code>/tts join</code></td>
    <td>Bot joins your current voice channel. You must be in one already.</td>
  </tr>
  <tr>
    <td><code>/tts leave</code></td>
    <td>Bot leaves the voice channel it's in.</td>
  </tr>
  <tr>
    <td><code>/tts check_perms</code></td>
    <td>Diagnostic. Shows the bot's effective permissions for the voice
      channel you're in &mdash; useful when "Failed to join" errors are
      mysterious.</td>
  </tr>
</table>

<h3>Customization</h3>
<table>
  <tr><th style="width:38%">Command</th><th>What it does</th></tr>
  <tr>
    <td><code>/tts speed &lt;0.5&ndash;2.0&gt;</code></td>
    <td>Set your personal speech speed multiplier. <code>1.0</code> is
      normal, <code>0.5</code> is half-speed, <code>2.0</code> is double.
      Saved per-user.</td>
  </tr>
  <tr>
    <td><code>/tts voice list</code></td>
    <td>Show all available voices, your subscription status, and which
      voices are claimable.</td>
  </tr>
  <tr>
    <td><code>/tts voice set &lt;voice&gt;</code></td>
    <td>Change your TTS voice. Voice IDs are case-insensitive
      (e.g. <code>m3</code> works for <code>M3</code>). Saved per-user.</td>
  </tr>
</table>

<h3>Subscriber-only voice claims</h3>
<p>"Claiming" a voice gives you exclusive use of it &mdash; nobody else on
the bot can use a claimed voice while it's claimed. Public voices
(<code>M1</code>&ndash;<code>M5</code>, <code>F1</code>&ndash;<code>F5</code>)
are always shared and can't be claimed.</p>
<table>
  <tr><th style="width:38%">Command</th><th>What it does</th></tr>
  <tr>
    <td><code>/tts voice claim-voice &lt;voice&gt;</code></td>
    <td>Claim an exclusive voice. Requires an active subscription
      (granted by an admin via <code>/tts admin-voice grant-subscription</code>).
      One claim per user.</td>
  </tr>
  <tr>
    <td><code>/tts voice claim-release</code></td>
    <td>Release your claimed voice so it's available again.</td>
  </tr>
</table>

<h3>Admin: monitored channels</h3>
<p>"Auto-TTS" works in channels added to the monitored list. When you type
in a monitored channel and you're in a voice channel, the bot speaks the
message automatically &mdash; no command needed.</p>
<table>
  <tr><th style="width:38%">Command</th><th>What it does</th></tr>
  <tr>
    <td><code>/tts setup add &lt;channel&gt;</code></td>
    <td>Add a text channel to the monitored list.</td>
  </tr>
  <tr>
    <td><code>/tts setup remove &lt;channel&gt;</code></td>
    <td>Remove a text channel from the monitored list.</td>
  </tr>
  <tr>
    <td><code>/tts setup list</code></td>
    <td>Show all monitored channels in this server.</td>
  </tr>
</table>

<h3>Admin: voice subscriptions (owner only)</h3>
<p>Only the user whose Discord ID matches <b>Owner ID</b> in your Settings
tab (or members with a role literally named "Admin") can run these.</p>
<table>
  <tr><th style="width:38%">Command</th><th>What it does</th></tr>
  <tr>
    <td><code>/tts admin-voice grant-subscription &lt;user&gt; [tier] [expires_at]</code></td>
    <td>Grant a user voice-claiming subscription.
      <code>tier</code> defaults to <code>voice_subscriber</code>;
      <code>expires_at</code> is an ISO date (<code>YYYY-MM-DD</code>) or
      omitted for never.</td>
  </tr>
  <tr>
    <td><code>/tts admin-voice revoke-subscription &lt;user&gt;</code></td>
    <td>Revoke a user's subscription. Also releases any voice they had
      claimed.</td>
  </tr>
  <tr>
    <td><code>/tts admin-voice list-subscriptions</code></td>
    <td>Show all currently active subscriptions, with their claimed voices
      and expiry dates.</td>
  </tr>
  <tr>
    <td><code>/tts admin-voice subscription-info &lt;user&gt;</code></td>
    <td>Show detailed info for one user's subscription &mdash; tier,
      expiry, claimed voice, who granted it.</td>
  </tr>
  <tr>
    <td><code>/tts admin-voice cleanup-expired</code></td>
    <td>Manually trigger the expired-subscription sweep (it also runs
      hourly in the background).</td>
  </tr>
  <tr>
    <td><code>/tts admin-voice reassign-voice &lt;voice&gt; &lt;user&gt;</code></td>
    <td>Force-assign a voice to a specific subscribed user, releasing it
      from anyone who currently has it claimed. The previous owner's
      preference resets to <code>M1</code>.</td>
  </tr>
</table>

<h3>Help inside Discord</h3>
<p>The bot also has its own help command embedded in chat:
<code>/tts help</code> shows a quick reference card you can keep handy.</p>

<hr/>

<h2>Troubleshooting</h2>

<h3>Bot is online but doesn't react to messages</h3>
<p>99% of the time this is the <b>Message Content Intent</b>. Double-check
step 3 of the Discord setup &mdash; the toggle has to be on <i>and</i> you
have to click Save Changes. If that's set, check the log feed at the bottom
of the Status tab when you type a message; you should see
<code>Synthesizing for user X: ...</code>. If nothing logs, the bot isn't
seeing the message at all.</p>

<h3>Bot keeps disconnecting from voice ("WebSocket closed with 4006")</h3>
<p>The same Discord token is being used by two processes simultaneously.
Either stop the cloud-hosted instance while testing locally, or create a
separate Discord application (separate token) for this install.</p>

<h3>Slash commands don't appear in Discord</h3>
<ul>
  <li>Wait ~30 seconds after the bot's first launch &mdash; the first
    slash sync is global and can take a moment to propagate.</li>
  <li>Press <b>Ctrl+R</b> in the Discord desktop app to force-refresh
    the command cache.</li>
  <li>Make sure you ticked <code>applications.commands</code> in
    step 6's scopes. If you forgot, re-generate the invite URL with
    both scopes and re-authorize.</li>
</ul>

<h3>"Application did not respond" on a slash command</h3>
<p>The bot took longer than 3 seconds to respond. Almost always a slow
database query when the bot machine is far from the database.
v0.1.0 defers most response-heavy commands to dodge this; if you still
see it, open an issue with the command name and the contents of the log
feed at the bottom of the Status tab.</p>

<h3>"Failed to download model" on first launch</h3>
<p>HuggingFace rate-limited you (anonymous downloads have low quotas).
Set <b>HuggingFace Token</b> in the Settings tab, restart the app, try
again.</p>

<h3>Bot can't join the voice channel ("Connection timeout")</h3>
<p>Run <code>/tts check_perms</code> while you're in a voice channel. The
bot dumps its effective permissions for that channel &mdash; look for any
role/channel overwrite that's denying <b>Connect</b>. If permissions are
fine and it still times out, Discord's voice infrastructure sometimes has
hiccups; wait a minute and try again.</p>

<hr/>

<h2>Where things are stored on your machine</h2>
<table>
  <tr><th style="width:48%">What</th><th>Where</th></tr>
  <tr>
    <td>Token, DB URL, Owner ID, HF token</td>
    <td><code>%APPDATA%\\Osiris DevWorks\\Super TTS\\.env</code></td>
  </tr>
  <tr>
    <td>Theme + UI preferences</td>
    <td>Windows registry: <code>HKCU\\Software\\Osiris DevWorks\\Super TTS</code></td>
  </tr>
  <tr>
    <td>Voice ONNX models (~1&ndash;2&nbsp;GB)</td>
    <td><code>%USERPROFILE%\\.cache\\supertonic2\\</code></td>
  </tr>
  <tr>
    <td>Logs</td>
    <td><code>%LOCALAPPDATA%\\Osiris DevWorks\\Super TTS\\logs\\</code></td>
  </tr>
</table>
<p>Nothing leaves your machine except the requests made to Discord, your
configured database, and HuggingFace (one-time model download).</p>
"""


class HelpTab(QWidget):
    """In-app help — Discord setup, GUI usage, slash command reference."""

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._browser = QTextBrowser()
        self._browser.setOpenLinks(False)  # we route external links manually
        self._browser.setOpenExternalLinks(False)
        self._browser.anchorClicked.connect(self._on_anchor_clicked)
        self._browser.setHtml(_HELP_HTML)
        layout.addWidget(self._browser)

    def _on_anchor_clicked(self, url: QUrl):
        # We disabled QTextBrowser's built-in link handling because by default
        # it tries to navigate within the document and replaces the rendered
        # HTML with a blank page. Routing every external link through the
        # OS's default browser keeps the help content intact.
        QDesktopServices.openUrl(url)
