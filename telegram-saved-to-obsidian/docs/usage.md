# Usage & recipes

All commands assume you're in `telegram-saved-to-obsidian/` and installed with `uv` (see the [README](../README.md)).

## The safe routine

```bash
# 1. See what would happen
.venv/bin/python import_telegram.py --inbox ~/Vault/Inbox --dry-run

# 2. Do it
.venv/bin/python import_telegram.py --inbox ~/Vault/Inbox
```

Dry-run output looks like:

```
Logged in as Ada
DRY RUN — nothing will be written or deleted.
4 message(s) found
  📝 Text: 2026-11-23 09-14-02.md
    → [dry-run] would create 2026-11-23 09-14-02.md
  🎤 Voice: 2026-11-23 09-15-40.md
    → [dry-run] would transcribe and create 2026-11-23 09-15-40.md
  🖼️  Album (2 images): 2026-11-23 09-17-11.md
    → [dry-run] would download _assets/2026-11-23 09-17-11 (1)<ext>
    → [dry-run] would download _assets/2026-11-23 09-17-11 (2)<ext>
    → [dry-run] would create 2026-11-23 09-17-11.md

Done: 3 note(s) would be created in /Users/you/Vault/Inbox (4 message(s) processed)
```

## Recipes

**Try it without losing anything** — write the notes but leave Telegram untouched:

```bash
.venv/bin/python import_telegram.py --inbox ~/Vault/Inbox --keep
```

Note: running again later without `--keep` will import those same messages a second time (with `(1)` suffixes).

**Set the language of your voice notes** (better accuracy than auto-detect):

```bash
.venv/bin/python import_telegram.py --inbox ~/Vault/Inbox --language fr
```

**Use a smaller / faster Whisper model**:

```bash
.venv/bin/python import_telegram.py --inbox ~/Vault/Inbox --model mlx-community/whisper-small-mlx
```

**Put images somewhere else** (e.g. your vault's attachments folder):

```bash
.venv/bin/python import_telegram.py --inbox ~/Vault/Inbox --assets-dir ~/Vault/Attachments
```

Obsidian resolves `![[file.jpg]]` by name, so embeds still work.

**Import more than 100 messages** in one go:

```bash
.venv/bin/python import_telegram.py --inbox ~/Vault/Inbox --limit 500
```

**Retry a failed transcription** from the audio cache:

```bash
.venv/bin/python import_telegram.py --inbox ~/Vault/Inbox \
  --transcribe-file "~/.config/telegram-saved-to-obsidian/.audio-cache/2026-11-23 09-15-40.ogg"
```

(Or simply run the normal import again: the Telegram message wasn't deleted, so it will be retried.)

**Skip `--inbox` every time** — add to `~/.config/telegram-saved-to-obsidian/.env`:

```ini
OBSIDIAN_INBOX=/Users/you/Vault/Inbox
```

**Shell alias** (in `~/.zshrc`):

```bash
alias tg2obs='~/code/creating-resilience-automations/telegram-saved-to-obsidian/.venv/bin/python ~/code/creating-resilience-automations/telegram-saved-to-obsidian/import_telegram.py'
```

**Separate accounts / vaults** — give each its own config dir:

```bash
.venv/bin/python import_telegram.py --config-dir ~/.config/tg-work --inbox ~/WorkVault/Inbox
```
