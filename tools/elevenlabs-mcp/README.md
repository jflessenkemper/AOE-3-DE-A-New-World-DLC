# ElevenLabs MCP Helper

This is a small local MCP server for voice generation workflows tied to A New World AI.

## What it exposes

- `list_voices`: inspect your ElevenLabs account voices.
- `get_models`: inspect available speech models.
- `text_to_speech`: generate speech and return base64 audio that can be written into your asset pipeline.

## Batch Generation

- `npm run generate:leader-tts` reads both `resources/audio/standard_leader_manifest.json` and `resources/audio/revolution_leader_manifest.json`.
- Copy `voice-map.example.json` to `voice-map.json` and assign one ElevenLabs voice ID per leader key.
- Output is written to `sound/voices/<leaderKey>/`.

## Setup

1. Rotate any key that was ever pasted into chat.
2. Copy `.env.example` to `.env`.
3. Put the fresh key into `ELEVENLABS_API_KEY`.
4. Install dependencies with `npm install` in this folder.
5. Copy `voice-map.example.json` to `voice-map.json` and fill in voice IDs.
6. Run `npm run check`.
7. Run `npm start` for MCP usage, or `npm run generate:leader-tts` for batch audio output.

## Notes

- The server uses stdio transport, which is the normal MCP shape for local tool integration.
- Audio output is returned as base64 so your downstream script or client can decide where to write files.
- This project is intentionally separate from the AoE3 mod files.