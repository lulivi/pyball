# QR Code on Match Start — Design Spec

**Date:** 2026-04-19

## Summary

When `/start_match` is executed, send a QR code image to each admin with the match tracking URL as the photo caption, replacing the current plain-text message.

## Dependencies

Add `qrcode[pil]>=8,<9` to `dependencies` in `pyproject.toml`.

## QR Generation

Add a helper function `generate_qr_bytes(url: str) -> BytesIO` in `pyball/bot/handlers/meetup.py`. It uses `qrcode.make(url)`, saves the result to an in-memory `BytesIO` buffer as PNG, and returns it seeked to position 0. No class, no state — pure function.

## Handler Change

In `start_match_handler` (`pyball/bot/handlers/meetup.py`), replace the `send_message` call with `send_photo`:

- `photo`: the `BytesIO` returned by `generate_qr_bytes(url)`
- `caption`: `f"🔗 Enlace del partido:\n{url}"` (same text as the current message)

The QR is generated once and reused across all admins (seek back to 0 between sends).

## Error Handling

No change to existing error handling. QR generation is in-memory and does not introduce new failure modes beyond what `qrcode` itself raises (which would propagate as unhandled exceptions, consistent with current behavior).

## Tests

In the unit test for `start_match_handler`: mock `generate_qr_bytes` and assert `send_photo` is called per admin with the correct `caption`. Assert `send_message` is not called.
