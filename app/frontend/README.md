# Real Estate Assistant — Frontend

A single-page streaming chat UI for a Real Estate AI assistant. Built with
Next.js 14 (App Router), TypeScript, Tailwind CSS, and shadcn/ui.

## Features

- One clean chat surface with streaming AI answers (custom SSE protocol).
- Each AI answer shows an intent badge (SQL / Policy / Recommendation / Chat).
- "Show details" panel reveals the SQL the bot ran (syntax-highlighted, with a
  copy button and row count) and/or the policy sources it cited.
- Clickable starter prompts on the empty state.
- Multiline composer: Enter to send, Shift+Enter for a newline.
- Dark mode by default, with a light/dark toggle.
- Responsive down to mobile widths.

## Getting started

```bash
npm install
npm run dev
```

Open http://localhost:3000.

## Configuration

The app talks to the backend at `NEXT_PUBLIC_API_URL` (defaults to
`http://localhost:8000`). To override, copy the example env file:

```bash
cp .env.local.example .env.local
```

## Project structure

- `app/page.tsx` — the chat page.
- `app/layout.tsx` — root layout + theme provider.
- `components/` — UI: message bubble, composer, details panel, SQL block, etc.
- `components/ui/` — shadcn/ui primitives.
- `lib/chat-client.ts` — the SSE streaming client (`fetch` + ReadableStream).
- `lib/types.ts` — shared types matching the backend contract.
- `store/chat-store.ts` — Zustand chat state.
