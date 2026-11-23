# Troubleshooting

### `Error: TELEGRAM_API_ID and TELEGRAM_API_HASH are required`
The `.env` file is missing or in the wrong place. It must be at `~/.config/telegram-saved-to-obsidian/.env` (or in the folder given by `--config-dir`). Check with:
```bash
cat ~/.config/telegram-saved-to-obsidian/.env
```
See [setup-telegram-api.md](setup-telegram-api.md).

### `Error: inbox folder does not exist` / `is not a folder` / `is not writable`
`--inbox` must point to an **existing folder** you can write to. Quote paths with spaces: `--inbox "~/My Vault/0 Inbox"`. If your vault is in iCloud, make sure the folder is downloaded locally. On macOS, if your terminal can't access the folder, grant it access in System Settings → Privacy & Security → Files and Folders (or Full Disk Access).

### `Transcription failed: ... ffmpeg ...` / `No such file or directory: 'ffmpeg'`
Whisper needs ffmpeg to decode Telegram's `.ogg` audio:
```bash
brew install ffmpeg
ffmpeg -version   # must print a version, not an error
```
If ffmpeg is installed but broken (e.g. `Library not loaded: libass`), run `brew reinstall ffmpeg`. Your audio is safe in the cache; retry afterwards.

### `mlx-whisper is not installed` or install fails
`mlx-whisper` only works on **Apple Silicon** Macs (arm64). Check with `uname -m` → it must say `arm64`.
- On Apple Silicon: `uv pip install -e '.[voice]'`. If Python itself is Intel (Rosetta), recreate the venv: `rm -rf .venv && uv venv --python 3.12`.
- On Intel Macs, Linux or Windows: voice notes can't be transcribed; text and images still work and voice notes stay in Telegram.

### First voice note is very slow
The first transcription downloads the Whisper model (~1.6 GB) from Hugging Face. Later runs are fast. Want something lighter? `--model mlx-community/whisper-small-mlx`.

### Transcription failed — did I lose my voice note?
No. The audio is kept for 15 days in `~/.config/telegram-saved-to-obsidian/.audio-cache/`, and the Telegram message is **not** deleted. Fix the cause, then either re-run the import or use the printed `--transcribe-file` command.

### Login: code never arrives / 2FA
- The code is sent **inside the Telegram app** on your other devices, not by SMS.
- If you've enabled two-step verification, you'll be asked for that password after the code.
- `PhoneNumberInvalidError`: use international format, e.g. `+33612345678`.
- `FloodWaitError`: too many attempts — wait the number of seconds shown.

### Session expired / `AuthKeyUnregisteredError` / asked to log in again
You (or Telegram) ended the session, e.g. from Settings → Devices. Delete the session file and log in again:
```bash
rm ~/.config/telegram-saved-to-obsidian/telegram.session
```

### `database is locked`
Another run is still using the session file. Wait for it or close the other terminal.

### Wrong timestamps in file names
Note names use your computer's local time zone. Check your system time zone.

### Some messages were "Skipped (unsupported media)"
Only text, voice notes and images are imported. Videos, stickers, PDFs, links-with-preview-only, etc. are left in Telegram.
