# How it works

## Connection

The script uses [Telethon](https://docs.telethon.dev/) to talk to Telegram's MTProto API **as your user account** (a bot can't read your Saved Messages). The first run logs in interactively; Telethon stores the session in `<config-dir>/telegram.session` so later runs are silent.

## Message loop

1. Fetch the `--limit` most recent messages from the peer `"me"` (Saved Messages).
2. **Group** them: messages that share a Telegram `grouped_id` (an album) become one group; every other message is its own group. Groups are processed **oldest first**.
3. For each group, pick a note name from the first message's timestamp, converted to your local time zone: `YYYY-MM-DD HH-MM-SS.md`.
4. Handle the group by type:

| Group contains | Result |
|---|---|
| At least one image (native photo, or a file with an `image/*` type) | Images downloaded to the assets folder as `<note name>.jpg` (or `<note name> (1).jpg`, `(2)`… for albums). Note = caption (if any) + one `![[...]]` embed per image. |
| A single voice note | Audio downloaded to the cache, transcribed, transcript written as the note. |
| A single text message | The text is written as the note. |
| Anything else | Skipped and left in Telegram. |

5. Each message whose note was written successfully is added to a "processed" list.
6. At the end, unless `--dry-run` or `--keep`, all processed messages are **deleted from Telegram** in one call.

## File naming & collisions

If `2026-11-23 09-14-02.md` already exists (two messages in the same second, or a re-import), the next one becomes `2026-11-23 09-14-02 (1).md`, then `(2)`, etc. Existing notes are never overwritten. Image files reuse the final note name, so they never collide either.

## Voice notes and the safety net

```
download → <config-dir>/.audio-cache/<note name>.ogg
        → transcribe (mlx-whisper, decodes via ffmpeg)
            ├─ success → write note → message marked for deletion
            └─ failure → keep audio, DON'T delete the Telegram message, print a retry command
```

- Audio is cached **before** transcription so a crash never loses a recording.
- Cached files older than **15 days** are purged at the start of each run.
- The Whisper model (default `mlx-community/whisper-large-v3-turbo`, ~1.6 GB) is downloaded from Hugging Face on first use and cached in `~/.cache/huggingface/`. Transcription itself runs **locally** — audio never leaves your Mac.

## What is never touched

- Notes already in your inbox (no overwrite).
- Messages that failed or were skipped (they stay in Telegram).
- Any chat other than Saved Messages.
