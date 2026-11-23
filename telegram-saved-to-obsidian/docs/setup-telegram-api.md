# Get your Telegram API credentials

The script logs in as **you** (not as a bot), so Telegram needs an `api_id` and `api_hash` tied to your account. It takes about 2 minutes and is free.

## 1. Log in to my.telegram.org

1. Open **https://my.telegram.org** in a browser.
2. Enter the phone number of the Telegram account whose Saved Messages you want to import, in international format (e.g. `+33612345678`).
3. Telegram sends a confirmation code **inside the Telegram app** (a message from the "Telegram" account), not by SMS. Paste it on the website.

## 2. Create an application

1. Click **API development tools**.
2. Fill in the form (only the first three fields matter):
   - **App title**: anything, e.g. `Obsidian importer`
   - **Short name**: 5–32 letters/digits, e.g. `obsidianimport`
   - **Platform**: `Desktop`
   - URL and description can stay empty.
3. Click **Create application**.

> If you get a vague "ERROR" when creating the app, try again a bit later, disable your VPN / ad-blocker, or use another browser. It's a known quirk of the site.

## 3. Copy the values into your `.env`

The page now shows **App api_id** (a number) and **App api_hash** (32 hex characters).

```bash
mkdir -p ~/.config/telegram-saved-to-obsidian
cp examples/.env.example ~/.config/telegram-saved-to-obsidian/.env
```

Edit `~/.config/telegram-saved-to-obsidian/.env`:

```ini
TELEGRAM_API_ID=1234567
TELEGRAM_API_HASH=0123456789abcdef0123456789abcdef
```

> [!CAUTION]
> `api_id` and `api_hash` are **secrets**. Don't share them, don't paste them in screenshots, and never commit the `.env` file. The same goes for `telegram.session`, which is created at first login.

## 4. First login

Run a dry run:

```bash
.venv/bin/python import_telegram.py --inbox ~/path/to/vault/Inbox --dry-run
```

You'll be asked for:

1. your phone number (same format as above),
2. the login code Telegram sends you in the app,
3. your **two-step verification password**, if you've enabled it.

After that the session is saved in `~/.config/telegram-saved-to-obsidian/telegram.session` and you won't be asked again.

Telegram will show a "new login" notification on your other devices — that's expected. You can see (and end) this session in Telegram → Settings → Devices.
