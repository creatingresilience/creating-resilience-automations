# Telegram Saved Messages → Obsidian

Use Telegram's **Saved Messages** as a quick-capture inbox, then pull everything into your Obsidian vault with one command:

| You send to Saved Messages | You get in your inbox folder |
|---|---|
| A text message | `2026-11-23 09-14-02.md` containing the text |
| A voice note | `2026-11-23 09-15-40.md` containing the **transcript** (local Whisper, no cloud) |
| A photo or an album | `2026-11-23 09-17-11.md` with the caption and `![[...]]` embeds; images go to `_assets/` |

Example note created from a 3-photo album with a caption:

```markdown
Whiteboard from Monday's workshop

![[2026-11-23 09-17-11 (1).jpg]]
![[2026-11-23 09-17-11 (2).jpg]]
![[2026-11-23 09-17-11 (3).jpg]]
```

> [!WARNING]
> **A real run deletes the imported messages from Telegram** (that's what keeps Saved Messages empty, like an inbox).
> Always start with `--dry-run`, and use `--keep` if you want to keep the messages.

## Requirements

- **Python 3.10+** (3.12 recommended). The easiest way is [`uv`](https://docs.astral.sh/uv/).
- A **Telegram account** and your own `api_id` / `api_hash` from https://my.telegram.org — [step-by-step guide](docs/setup-telegram-api.md).
- For **voice notes only**:
  - a Mac with **Apple Silicon** (M1/M2/M3/M4) — transcription uses [`mlx-whisper`](https://github.com/ml-explore/mlx-examples/tree/main/whisper);
  - **ffmpeg** (`brew install ffmpeg`). Telegram sends voice notes as compressed Opus audio in an `.ogg` file, and Whisper can't read that format directly: it calls ffmpeg to turn the audio into the raw 16 kHz waveform the model needs. Without ffmpeg, every transcription fails (your audio stays safe in the cache and the message stays in Telegram).

  Text and images work on any OS. Without voice support, voice notes are left untouched in Telegram.

## Quickstart

```bash
# 1. Get the code
git clone https://github.com/creatingresilience/creating-resilience-automations.git
cd creating-resilience-automations/telegram-saved-to-obsidian

# 2. Create a Python 3.12 environment and install
uv venv --python 3.12
uv pip install -e .            # text + images
uv pip install -e '.[voice]'   # + voice transcription (Apple Silicon only)
brew install ffmpeg            # needed for voice

# 3. Add your Telegram API credentials (see docs/setup-telegram-api.md)
mkdir -p ~/.config/telegram-saved-to-obsidian
cp examples/.env.example ~/.config/telegram-saved-to-obsidian/.env
open -e ~/.config/telegram-saved-to-obsidian/.env   # paste your api_id and api_hash

# 4. First run = dry run. It asks for your phone number and the login code
#    Telegram sends you (and your 2FA password if you have one).
.venv/bin/python import_telegram.py --inbox ~/path/to/vault/Inbox --dry-run

# 5. Real run (writes notes, then deletes the imported messages from Telegram)
.venv/bin/python import_telegram.py --inbox ~/path/to/vault/Inbox
```

Tip: put `OBSIDIAN_INBOX=/path/to/vault/Inbox` in the `.env` file and you can drop `--inbox`.

## Options

| Flag | Default | What it does |
|---|---|---|
| `--inbox PATH` | `$OBSIDIAN_INBOX` | Folder where notes are written. Must already exist. |
| `--assets-dir PATH` | `<inbox>/_assets` | Where images are saved. |
| `--dry-run` | off | Show what would happen. Writes nothing, deletes nothing. |
| `--keep` | off | Write notes but **don't** delete the messages from Telegram. |
| `--limit N` | `100` | How many recent messages to fetch per run. |
| `--language CODE` | auto-detect | Language of your voice notes (`en`, `fr`, `es`…). Setting it improves accuracy. |
| `--model REPO` | `mlx-community/whisper-large-v3-turbo` | Whisper model used for transcription. |
| `--config-dir PATH` | `~/.config/telegram-saved-to-obsidian` | Where `.env`, the login session and the audio cache live. Also `$TSO_CONFIG_DIR`. |
| `--transcribe-file AUDIO` | — | Offline: transcribe one audio file (e.g. from the cache after a failure) into the inbox. |

Run `python import_telegram.py --help` for the same list.

## Where your data lives

Everything private stays **outside the repo**, in `~/.config/telegram-saved-to-obsidian/`:

| File | What it is |
|---|---|
| `.env` | Your `api_id` / `api_hash`. Secret. |
| `telegram.session` | Your logged-in Telegram session. **Treat it like a password**: anyone with it can read your account. |
| `.audio-cache/` | Downloaded voice notes, kept 15 days as a safety net. |

## More docs

- [Get your Telegram API credentials](docs/setup-telegram-api.md)
- [Usage & recipes](docs/usage.md)
- [How it works](docs/how-it-works.md)
- [Troubleshooting](docs/troubleshooting.md)

## Limitations

- Voice transcription runs only on Apple Silicon Macs.
- Only Saved Messages is imported (not other chats).
- Unsupported media (videos, stickers, files that aren't images, etc.) is skipped and left in Telegram.
- Uses your **user account** via Telegram's MTProto API (Telethon), not a bot.

## Credits & license

Original script by **Alexandre**, adapted for public use by Carole Waihai.
MIT license — see [LICENSE](../LICENSE).
