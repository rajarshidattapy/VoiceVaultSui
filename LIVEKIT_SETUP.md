# LiveKit Setup for VoiceVault

Voice agents on VoiceVault use LiveKit for real-time audio rooms. This guide gets you from zero to a working agent call.

---

## 1. Create a LiveKit Cloud project

1. Go to [cloud.livekit.io](https://cloud.livekit.io) and sign up (free tier is enough for dev)
2. Click **New Project** → give it a name (e.g. `voicevault-dev`)
3. From the project dashboard, copy:
   - **WebSocket URL** — looks like `wss://your-project-abc123.livekit.cloud`
   - **API Key** — looks like `APIxxxxxxxxxxxxxxxx`
   - **API Secret** — looks like `your_secret_string`

---

## 2. Add credentials to `.env`

```env
LIVEKIT_URL=wss://your-project-abc123.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxxxxxxxxxx
LIVEKIT_API_SECRET=your_secret_string
```

Also add your LLM key for the agent worker (pick whichever provider you want):

```env
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...
```

---

## 3. Install the Python SDK

```bash
cd backend
pip install livekit-api
```

It is already in `requirements.txt`, so `pip install -r requirements.txt` covers this.

---

## 4. Install the LiveKit agent CLI

```bash
pip install livekit-agents
```

The agent worker script (`agent_worker.py`) uses this to connect to a room and handle calls.

---

## 5. Deploy an agent from the UI

1. Start the backend: `python server.py`
2. Start the frontend: `npm run dev`
3. Connect your Sui wallet
4. Go to **Deploy Agent** (`/deploy`)
5. Complete the 4-step wizard — Voice → Template → Configure → Deploy
6. On the Deploy step, copy the **Start Command** shown in the UI, e.g.:

```bash
LIVEKIT_URL=wss://... LIVEKIT_API_KEY=API... LIVEKIT_API_SECRET=... ROOM_NAME=vv-abc123 python agent_worker.py dev
```

7. Paste and run that command in a terminal
8. Click **Talk** on the agent card — it opens a live voice room in your browser

---

## 6. Verify the connection

The backend logs will print:

```
[livekit] token generated for room vv-abc123
```

If credentials are missing, the backend falls back to demo mode and the **Talk** button will show a setup message instead of opening a room.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Talk` button does nothing | Check `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` are set in `.env` |
| `demo-token-*` in logs | Backend did not find credentials — re-check `.env` and restart the server |
| Agent worker crashes immediately | Make sure `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` is set |
| Room connects but no audio | Confirm microphone permissions in the browser |
| `livekit.api` import error | Run `pip install livekit-api` in the backend virtualenv |

---

## Architecture

```
Browser (user)
    ↓  WebRTC
LiveKit Cloud room (vv-<agent-id>)
    ↓  agent SDK
agent_worker.py  ←  ROOM_NAME env var
    ↓  LLM API
OpenAI / Anthropic / Groq
    ↓  TTS
VoiceVault backend  /api/tts/generate
```

Each deployed agent gets its own room name (`vv-<agent-id>`). The agent worker joins that room and handles audio in real time.

 docs/LIVEKIT_SETUP.md — step-by-step guide covering:
  1. Create a LiveKit Cloud project and copy the 3 credentials                                                                                                                                      
  2. Add them to .env
  3. Install livekit-api + livekit-agents                                                                                                                                                           
  4. Deploy from the UI and run the agent worker start command                                                                                                                                    
  5. Troubleshooting table (common errors + fixes)
  6. Architecture diagram showing the full call path

  .env.example — added three new sections:
  - LIVEKIT — URL, API key, API secret with a pointer to the setup guide
  - LLM PROVIDERS — OpenAI, Anthropic, Gemini, Groq keys
  - x402 PAY-PER-USE — default price and uses config