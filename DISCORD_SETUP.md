# Discord Bot Setup Instructions

Follow these steps to register and configure the super-tts bot with Discord.

## 1. Create a Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Name it "super-tts" (or your preferred name)
4. Accept the terms and click "Create"

## 2. Create a Bot User

1. In the left sidebar, click "Bot"
2. Click "Add Bot"

## 3. Get Your Bot Token

1. Under the bot name, you'll see a "TOKEN" section
2. Click "Reset Token"
3. Copy the token
4. **Add to `.env` file**:
   ```
   DISCORD_TOKEN=<your_token_here>
   ```

## 4. Set Bot Permissions

1. Go to "OAuth2" → "URL Generator" in the left sidebar
2. Under **Scopes**, check:
   - `bot`
3. Under **Permissions**, check:
   - `Send Messages`
   - `Connect` (voice)
   - `Speak` (voice)
   - `Use Slash Commands`
   - `Embed Links`
4. Copy the generated URL at the bottom

## 5. Invite Bot to Your Server

1. Open the generated OAuth2 URL in your browser
2. Select your Discord server
3. Click "Authorize"

## 6. Enable Required Intents

1. In Developer Portal, go to the "Bot" section
2. Scroll down to "Intents"
3. Enable:
   - `Message Content Intent`
   - `Server Members Intent`
   - `Guild Voice States`

## 7. Start the Bot

Once you've completed all steps:

```bash
python main.py
```

Or with a specific log level:

```bash
python main.py DEBUG
```

The bot should now appear online in your Discord server and respond to slash commands!
