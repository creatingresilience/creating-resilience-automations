# creating-resilience-automations

Small, reusable personal automation scripts — mostly for getting things *into* an Obsidian second brain with less friction. Each tool lives in its own folder with its own README, dependencies and docs.

| Tool | What it does |
|---|---|
| [telegram-saved-to-obsidian](telegram-saved-to-obsidian/) | Imports Telegram Saved Messages (text, voice notes transcribed locally, images/albums) into an Obsidian inbox folder. |

More tools will follow.

## Principles

- No secrets in the repo: credentials and sessions live in `~/.config/<tool>/`, and `.gitignore` blocks `.env`, `*.session`, caches and venvs.
- No personal paths: everything is configured by flags or environment variables.
- Destructive actions are documented and have a dry-run.

## License

[MIT](LICENSE)
