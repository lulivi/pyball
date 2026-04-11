# Telegram MarkdownV2 Escaping Design

## Goal
Implement a robust escaping mechanism for Telegram MarkdownV2 to ensure all user-provided data (names, locations, teams) is properly escaped to prevent parsing errors and security issues.

## Scope
- Create a utility function `escape_markdown_v2(text: str) -> str`.
- Apply this utility to all user-provided strings in `pyball/bot/formatters.py`.

## Technical Approach
Telegram's MarkdownV2 requires escaping the following characters in the main text:
`_`, `*`, `[`, `]`, `(`, `)`, `~`, `` ` ``, `>`, `#`, `+`, `-`, `=`, `|`, `{`, `}`, `.`, `!`

Additionally, `\` must be escaped first.

## Implementation Plan
1. Create `pyball/infrastructure/markdown_escape.py` with `escape_markdown_v2`.
2. Update `pyball/bot/formatters.py` to use `escape_markdown_v2` instead of `html.escape`.
3. Verify with unit tests.
