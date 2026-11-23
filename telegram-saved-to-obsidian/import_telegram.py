#!/usr/bin/env python3
"""
Import Telegram "Saved Messages" into an Obsidian inbox folder.

- Text messages   -> one Markdown note per message.
- Voice messages  -> downloaded, transcribed locally with mlx-whisper
                     (Apple Silicon only), transcript saved as a note.
- Images / albums -> files saved to <inbox>/_assets/ and embedded with ![[...]];
                     an album (same Telegram grouped_id) becomes one note.
- After a note is written successfully, the source message is deleted from
  Telegram (unless --keep is given).

Voice safety net: audio is cached in <config-dir>/.audio-cache/ for 15 days
BEFORE transcription. If transcription fails, the audio is kept and the
Telegram message is NOT deleted. Retry with either:
    python import_telegram.py --inbox PATH          (re-runs the whole import)
    python import_telegram.py --inbox PATH --transcribe-file CACHED.ogg

Setup (see README.md and docs/setup-telegram-api.md):
    1. Get api_id / api_hash at https://my.telegram.org
    2. Put them in ~/.config/telegram-saved-to-obsidian/.env
       (or export TELEGRAM_API_ID / TELEGRAM_API_HASH)
    3. First run asks for your phone number + login code; the session is
       then stored in the config dir.

Originally written by Alexandre; adapted for public use.
"""

import argparse
import asyncio
import os
import sys
import time
from datetime import timezone
from pathlib import Path

APP_NAME = "telegram-saved-to-obsidian"
DEFAULT_CONFIG_DIR = Path(
    os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
) / APP_NAME
DEFAULT_CONFIG_DISPLAY = f"~/.config/{APP_NAME}"
DEFAULT_MODEL ="mlx-community/whisper-large-v3-turbo"
CACHE_RETENTION_DAYS = 15


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def read_env_file(path):
    """Parse a simple KEY=VALUE .env file. Returns {} if it doesn't exist."""
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def load_credentials(env_file_values):
    """Get api_id / api_hash from the process environment first, then the .env file."""
    api_id = os.environ.get("TELEGRAM_API_ID") or env_file_values.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH") or env_file_values.get("TELEGRAM_API_HASH")
    if not api_id or not api_hash:
        sys.exit(
            "Error: TELEGRAM_API_ID and TELEGRAM_API_HASH are required.\n"
            "Put them in the .env file of your config dir "
            f"(default: {DEFAULT_CONFIG_DIR / '.env'}) or export them.\n"
            "See docs/setup-telegram-api.md to get them from https://my.telegram.org."
        )
    try:
        return int(api_id), api_hash
    except ValueError:
        sys.exit(f"Error: TELEGRAM_API_ID must be a number, got {api_id!r}.")


def resolve_inbox(cli_value, env_file_values):
    """Inbox from --inbox, else $OBSIDIAN_INBOX, else OBSIDIAN_INBOX in .env."""
    raw = cli_value or os.environ.get("OBSIDIAN_INBOX") or env_file_values.get("OBSIDIAN_INBOX")
    if not raw:
        sys.exit(
            "Error: no inbox folder given.\n"
            "Use --inbox /path/to/vault/Inbox or set OBSIDIAN_INBOX."
        )
    inbox = Path(raw).expanduser().resolve()
    if not inbox.exists():
        sys.exit(f"Error: inbox folder does not exist: {inbox}")
    if not inbox.is_dir():
        sys.exit(f"Error: inbox path is not a folder: {inbox}")
    if not os.access(inbox, os.W_OK):
        sys.exit(f"Error: inbox folder is not writable: {inbox}")
    return inbox


# ---------------------------------------------------------------------------
# Message helpers
# ---------------------------------------------------------------------------

def is_voice_message(message):
    """True if the message is a voice note."""
    from telethon.tl.types import DocumentAttributeAudio, MessageMediaDocument

    if not message.media or not isinstance(message.media, MessageMediaDocument):
        return False
    doc = message.media.document
    if not doc:
        return False
    return any(isinstance(a, DocumentAttributeAudio) and a.voice for a in doc.attributes)


def is_image_message(message):
    """True if the message carries an image (native photo or image document)."""
    from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto

    if not message.media:
        return False
    if isinstance(message.media, MessageMediaPhoto):
        return True
    if isinstance(message.media, MessageMediaDocument):
        doc = message.media.document
        return bool(doc and doc.mime_type and doc.mime_type.startswith("image/"))
    return False


def image_extension(message):
    """File extension (with dot) for an image message. Defaults to .jpg."""
    from telethon.tl.types import MessageMediaPhoto

    if isinstance(message.media, MessageMediaPhoto):
        return ".jpg"  # Telegram converts native photos to JPEG.
    ext = getattr(message.file, "ext", None) if message.file else None
    return ext or ".jpg"


def group_messages(messages):
    """Group messages by grouped_id (albums). Returns groups oldest-first."""
    groups = []
    index_by_gid = {}
    for msg in reversed(messages):  # Telethon returns newest first
        gid = msg.grouped_id
        if gid is None:
            groups.append([msg])
        elif gid in index_by_gid:
            groups[index_by_gid[gid]].append(msg)
        else:
            index_by_gid[gid] = len(groups)
            groups.append([msg])
    return groups


def unique_note_path(inbox, stem):
    """Return inbox/<stem>.md, adding ' (1)', ' (2)'... if it already exists."""
    path = inbox / f"{stem}.md"
    counter = 1
    while path.exists():
        path = inbox / f"{stem} ({counter}).md"
        counter += 1
    return path


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

def transcribe_audio(audio_path, model, language):
    """Transcribe an audio file with mlx-whisper (Apple Silicon only)."""
    try:
        import mlx_whisper
    except ImportError as e:
        raise RuntimeError(
            "mlx-whisper is not installed (voice support needs Apple Silicon). "
            "Install with: uv pip install -e '.[voice]'"
        ) from e

    kwargs = {"path_or_hf_repo": model}
    if language:
        kwargs["language"] = language
    result = mlx_whisper.transcribe(str(audio_path), **kwargs)
    return result["text"].strip()


def purge_old_cache(cache_dir):
    """Delete cached audio older than CACHE_RETENTION_DAYS."""
    if not cache_dir.exists():
        return
    cutoff = time.time() - CACHE_RETENTION_DAYS * 86400
    for f in cache_dir.iterdir():
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink()
            print(f"  🗑️  Purged cached audio (>{CACHE_RETENTION_DAYS} days): {f.name}")


def transcribe_file_only(args, inbox):
    """--transcribe-file mode: transcribe one cached audio file into the inbox."""
    audio = Path(args.transcribe_file).expanduser().resolve()
    if not audio.is_file():
        sys.exit(f"Error: audio file not found: {audio}")
    filepath = unique_note_path(inbox, audio.stem)
    print(f"🎤 Transcribing {audio.name} ...")
    try:
        text = transcribe_audio(audio, args.model, args.language)
    except Exception as e:  # noqa: BLE001
        sys.exit(f"Error: transcription failed: {e}")
    filepath.write_text(text, encoding="utf-8")
    print(f"  → {filepath}")
    print("Note: the original Telegram message (if still there) was not touched.")


# ---------------------------------------------------------------------------
# Main import
# ---------------------------------------------------------------------------

async def run_import(args, inbox, config_dir, env_file_values):
    from telethon import TelegramClient

    api_id, api_hash = load_credentials(env_file_values)
    assets_dir = (
        Path(args.assets_dir).expanduser().resolve() if args.assets_dir else inbox / "_assets"
    )
    cache_dir = config_dir / ".audio-cache"
    session_file = config_dir / "telegram"  # Telethon appends ".session"

    config_dir.mkdir(parents=True, exist_ok=True)
    try:
        config_dir.chmod(0o700)
    except OSError:
        pass

    client = TelegramClient(str(session_file), api_id, api_hash)
    await client.start()

    me = await client.get_me()
    print(f"Logged in as {me.first_name}")
    if args.dry_run:
        print("DRY RUN — nothing will be written or deleted.")
    elif args.keep:
        print("--keep — messages will NOT be deleted from Telegram.")

    messages = await client.get_messages("me", limit=args.limit)
    if not messages:
        print("No messages in Saved Messages.")
        await client.disconnect()
        return

    print(f"{len(messages)} message(s) found")

    processed = []
    notes_created = 0
    purge_old_cache(cache_dir)

    for group in group_messages(messages):
        first = group[0]
        local_dt = first.date.replace(tzinfo=timezone.utc).astimezone()
        stem = local_dt.strftime("%Y-%m-%d %H-%M-%S")
        filepath = unique_note_path(inbox, stem)
        note_stem = filepath.stem

        image_msgs = [m for m in group if is_image_message(m)]

        if image_msgs:
            label = "Image" if len(image_msgs) == 1 else f"Album ({len(image_msgs)} images)"
            print(f"  🖼️  {label}: {filepath.name}")
            notes_created += 1
            caption = next((m.text for m in group if m.text), "")

            if args.dry_run:
                for i, _ in enumerate(image_msgs):
                    suffix = "" if len(image_msgs) == 1 else f" ({i + 1})"
                    print(f"    → [dry-run] would download {assets_dir.name}/{note_stem}{suffix}<ext>")
                print(f"    → [dry-run] would create {filepath.name}")
                processed.extend(group)
                continue

            assets_dir.mkdir(parents=True, exist_ok=True)
            embeds = []
            for i, img_msg in enumerate(image_msgs):
                ext = image_extension(img_msg)
                suffix = "" if len(image_msgs) == 1 else f" ({i + 1})"
                asset_path = assets_dir / f"{note_stem}{suffix}{ext}"
                await img_msg.download_media(file=str(asset_path))
                embeds.append(f"![[{asset_path.name}]]")
                print(f"    → {assets_dir.name}/{asset_path.name}")

            body = (caption + "\n\n" if caption else "") + "\n".join(embeds) + "\n"
            filepath.write_text(body, encoding="utf-8")
            print(f"    → {filepath.name}")
            processed.extend(group)

        elif len(group) == 1 and is_voice_message(first):
            msg = first
            print(f"  🎤 Voice: {filepath.name}")
            notes_created += 1

            if args.dry_run:
                print(f"    → [dry-run] would transcribe and create {filepath.name}")
                processed.append(msg)
                continue

            # Download into the persistent cache BEFORE transcribing.
            cache_dir.mkdir(parents=True, exist_ok=True)
            audio_path = cache_dir / f"{note_stem}.ogg"
            await msg.download_media(file=str(audio_path))

            # If transcription fails: keep the audio, do NOT delete the message.
            print("    → Transcribing...")
            try:
                text = transcribe_audio(audio_path, args.model, args.language)
            except Exception as e:  # noqa: BLE001 — any failure must keep the message
                notes_created -= 1
                print(f"    ⚠️  Transcription failed: {e}")
                print(f"    → Audio kept in cache for {CACHE_RETENTION_DAYS} days; "
                      "Telegram message NOT deleted. Retry with:")
                print(f'      python import_telegram.py --inbox "{inbox}" '
                      f'--transcribe-file "{audio_path}"')
                continue

            filepath.write_text(text, encoding="utf-8")
            print(f"    → {filepath.name} (audio cached for {CACHE_RETENTION_DAYS} days)")
            processed.append(msg)

        elif len(group) == 1 and first.text:
            msg = first
            print(f"  📝 Text: {filepath.name}")
            notes_created += 1

            if args.dry_run:
                print(f"    → [dry-run] would create {filepath.name}")
                processed.append(msg)
                continue

            filepath.write_text(msg.text, encoding="utf-8")
            print(f"    → {filepath.name}")
            processed.append(msg)

        else:
            ids = ", ".join(str(m.id) for m in group)
            print(f"  ⏭️  Skipped (unsupported media), message id(s): {ids}")

    if processed and not args.dry_run and not args.keep:
        print(f"\nDeleting {len(processed)} message(s) from Telegram...")
        await client.delete_messages("me", [m.id for m in processed])
        print("Saved Messages cleaned up.")

    verb = "would be created" if args.dry_run else "created"
    print(f"\nDone: {notes_created} note(s) {verb} in {inbox} "
          f"({len(processed)} message(s) processed)")
    await client.disconnect()


def build_parser():
    parser = argparse.ArgumentParser(
        prog="import_telegram.py",
        description=(
            "Import Telegram Saved Messages (text, voice, images) into an Obsidian "
            "inbox folder. By default, messages are DELETED from Telegram once their "
            "note is written — always try --dry-run first."
        ),
        epilog=(
            "Credentials: TELEGRAM_API_ID / TELEGRAM_API_HASH from the environment or "
            f"from <config-dir>/.env (default config dir: {DEFAULT_CONFIG_DISPLAY})."
        ),
    )
    parser.add_argument(
        "--inbox", metavar="PATH",
        help="Folder where notes are written (e.g. your vault's inbox). "
             "Defaults to $OBSIDIAN_INBOX or OBSIDIAN_INBOX in the .env file.",
    )
    parser.add_argument(
        "--assets-dir", metavar="PATH",
        help="Folder for downloaded images (default: <inbox>/_assets).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would happen without writing files or deleting messages.",
    )
    parser.add_argument(
        "--keep", action="store_true",
        help="Write notes but do NOT delete the messages from Telegram.",
    )
    parser.add_argument(
        "--limit", type=int, default=100, metavar="N",
        help="Maximum number of recent messages to fetch (default: 100).",
    )
    parser.add_argument(
        "--language", metavar="CODE",
        help="Whisper language code for voice notes, e.g. en, fr, es. "
             "Default: auto-detect.",
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, metavar="REPO",
        help=f"mlx-whisper model (Hugging Face repo). Default: {DEFAULT_MODEL}.",
    )
    parser.add_argument(
        "--config-dir", metavar="PATH",
        help="Where .env, the Telegram session and the audio cache live "
             f"(default: $TSO_CONFIG_DIR or {DEFAULT_CONFIG_DISPLAY}).",
    )
    parser.add_argument(
        "--transcribe-file", metavar="AUDIO",
        help="Don't connect to Telegram: just transcribe one audio file "
             "(e.g. from the audio cache after a failed run) into the inbox.",
    )
    return parser


def main():
    args = build_parser().parse_args()
    if args.limit < 1:
        sys.exit("Error: --limit must be at least 1.")

    config_dir = Path(
        args.config_dir or os.environ.get("TSO_CONFIG_DIR") or DEFAULT_CONFIG_DIR
    ).expanduser().resolve()
    env_file_values = read_env_file(config_dir / ".env")
    inbox = resolve_inbox(args.inbox, env_file_values)

    if args.transcribe_file:
        transcribe_file_only(args, inbox)
        return

    asyncio.run(run_import(args, inbox, config_dir, env_file_values))


if __name__ == "__main__":
    main()
