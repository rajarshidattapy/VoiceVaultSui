# VoiceVault Sui

VoiceVault is a Web3 voice marketplace and agent platform on Sui. Creators can process a voice sample, store the generated bundle on Walrus, register the voice on-chain, sell access through the marketplace, and deploy LiveKit voice agents.

The current runtime uses:

- Sui Move contracts for voice identity, payments, and license/pass checks
- Walrus for voice bundle storage
- FastAPI backend for Walrus access, TTS, LiveKit, and agent APIs
- React/Vite frontend for marketplace, upload, purchase, deploy, and call flows
- Murf TTS through the backend for generated speech

## Features

- Register voice identities on Sui
- Store voice bundles on Walrus
- Discover registered voices from the marketplace
- Buy voices and track purchased access in the app
- Generate TTS from purchased voices after backend access verification
- Deploy voice agents backed by LiveKit
- Let deployed agents call/invite other deployed agents into the same room
- Keep invited agents in-room while the previous agent stays muted/silent
- Use readable agent names in LiveKit instead of raw generated IDs

## Project Structure

```text
VoiceVaultSui/
  backend/
    server.py                 FastAPI server
    agent_worker.py           LiveKit agent worker
    livekit_service.py        LiveKit token/room helpers
    walrus.py                 Walrus storage and Sui access checks
    voice_model.py            Voice bundle generation
    storage/                  Local runtime storage
  frontend/
    src/
      pages/
        Upload.tsx            Voice processing, registration, purchased voice TTS
        Marketplace.tsx       Voice discovery and purchase
        Deploy.tsx            Agent deployment
      lib/
        api.ts                Backend API client
        murfVoice.ts          Murf-backed TTS wrapper
        paymentContract.ts    Payment transaction helper
        voiceContract.ts      Voice contract transaction helper
        purchasedVoices.ts    Local purchased voice cache
  voice_vault_sui/
    sources/                  Move contracts
  docs/
```

## Prerequisites

- Node.js 18+
- Python 3.10+
- Sui wallet browser extension
- Sui CLI if you are publishing contracts
- LiveKit account for voice agent calls
- Murf API key for TTS generation

## Environment

Use separate env files for frontend and backend.

### Backend

Create `backend/.env` from `backend/.env.example`.

Required for core backend:

```env
PORT=8000
BACKEND_URL=http://localhost:8000

SUI_NETWORK=testnet
SUI_RPC_URL=https://fullnode.testnet.sui.io
SUI_FULL_NODE_URL=https://fullnode.testnet.sui.io:443
SUI_PACKAGE_ID=0x...
SUI_VOICE_REGISTRY_ID=0x...

WALRUS_STORAGE_MODE=local
WALRUS_PUBLISHER_URL=https://publisher.walrus-testnet.walrus.space
WALRUS_AGGREGATOR_URL=http://localhost:8000/api/walrus
WALRUS_EPOCHS=5
WALRUS_DELETABLE=true
WALRUS_MAX_BLOB_SIZE=10485760
```

Required for purchased voice TTS:

```env
MURF_API_KEY=your_murf_api_key
MURF_VOICE_ID=Ken
MURF_LOCALE=en-US
MURF_FORMAT=WAV
MURF_SAMPLE_RATE=44100
```

Required for deployed voice agents:

```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
OPENAI_API_KEY=your_openai_api_key
```

Do not put `MURF_API_KEY` in `frontend/.env`. The backend calls Murf so the key is not exposed in browser bundles.

### Frontend

Create `frontend/.env` from `frontend/.env.example`.

```env
VITE_API_URL=http://localhost:8000
VITE_PROXY_URL=http://localhost:8000
VITE_BACKEND_URL=http://localhost:8000

VITE_SUI_NETWORK=testnet
VITE_SUI_RPC_URL=https://fullnode.testnet.sui.io
VITE_SUI_PACKAGE_ID=0x...
VITE_SUI_VOICE_REGISTRY_ID=0x...

VITE_WALRUS_AGGREGATOR_URL=http://localhost:8000/api/walrus
```

Only variables prefixed with `VITE_` should be used by the frontend.

## Install

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python server.py
```

Backend runs on `http://localhost:8000`.

If port `8000` is already in use, stop the old server process or run the backend on another port and update the frontend API env values.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend usually runs on `http://localhost:5173`.

## Deployment

The active production deployment plan targets AWS:

- Backend: Amazon ECS on AWS Fargate with API, MCP, and LiveKit worker containers
- Frontend: AWS Amplify Hosting
- Runtime secrets: AWS Secrets Manager
- Persistent runtime state: Amazon EFS

See [docs/AWS_DEPLOYMENT_PLAN.md](docs/AWS_DEPLOYMENT_PLAN.md).

## Main Workflows

### Register a Voice

1. Open `/upload`.
2. Connect a Sui wallet.
3. Record or upload an audio sample.
4. Process the voice model.
5. Register the generated Walrus URI on Sui.
6. The voice becomes discoverable in `/marketplace`.

### Buy and Use a Voice

1. Open `/marketplace`.
2. Buy a listed voice with Sui.
3. Open `/upload`.
4. Select the purchased voice under the TTS section.
5. Enter text and generate speech.

The backend verifies access before TTS. It accepts owner access, on-chain license access, and legacy purchase transaction proof where applicable.

### Murf TTS Notes

Murf runtime TTS uses a Murf `voiceId`, configured with `MURF_VOICE_ID`. The default is `Ken`, a male voice.

Murf custom voice cloning is not an instant reference-audio cloning API. Murf's cloning product is an enterprise process where the custom voice is created by Murf and later exposed as a voice available to your account. After Murf gives you a custom voice ID, set:

```env
MURF_VOICE_ID=your_custom_murf_voice_id
```

### Deploy a Voice Agent

1. Open `/deploy`.
2. Select an owned voice.
3. Choose an agent template.
4. Configure prompt, provider, and pricing.
5. Deploy the agent.
6. Use the generated LiveKit room/call link to talk to it.

Agents can invite another deployed agent into the same LiveKit room when the conversation requires handoff or specialist support.

## Smart Contracts

The current Sui testnet deployment uses this package:

```text
0x1ad12f0fd581dbd4fef7a30c9cff9bececfca1da450fe53257791502b3db073d
```

Explorer:

- [Sui Explorer - Package](https://suiexplorer.com/object/0x1ad12f0fd581dbd4fef7a30c9cff9bececfca1da450fe53257791502b3db073d?network=testnet)

Modules in the package:

| Module | Purpose |
| --- | --- |
| `voice_identity` | Registers voice ownership and stores voice metadata such as name, voice ID, and Walrus model URI |
| `payment` | Handles royalty split payments and purchase/license logic |
| `agent_identity` | Stores deployed agent identity/config metadata on-chain |

The active shared voice registry object is:

```text
0xfad2808bcd104197b53b1fddede5f25d5c16303b147d280c2aa7ff69d27e5d59
```

Explorer:

- [Sui Explorer - Voice Registry](https://suiexplorer.com/object/0xfad2808bcd104197b53b1fddede5f25d5c16303b147d280c2aa7ff69d27e5d59?network=testnet)

## API Overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/voice/process` | Process uploaded audio into a voice bundle |
| `POST` | `/api/walrus/upload` | Upload a voice bundle |
| `POST` | `/api/walrus/download` | Download a file from a voice bundle |
| `POST` | `/api/walrus/delete` | Delete a voice bundle |
| `POST` | `/api/tts/generate` | Generate TTS after access checks |
| `POST` | `/api/payment/breakdown` | Calculate payment split |
| `POST` | `/api/agent/create` | Create an agent config |
| `GET` | `/api/agent/list?owner=...` | List owner agents |
| `POST` | `/api/agent/deploy/:id` | Deploy/start agent |
| `POST` | `/api/agent/join/:id` | Get LiveKit room token |

## Verification

Common checks:

```powershell
cd frontend
npm run build
```

```powershell
python -m py_compile backend\server.py backend\walrus.py
```

## Troubleshooting

### Backend cannot bind to port 8000

Another backend process is already running. Stop it or use a different port and update:

```env
VITE_API_URL=http://localhost:<port>
VITE_PROXY_URL=http://localhost:<port>
VITE_BACKEND_URL=http://localhost:<port>
```

### Murf key not working

Put the key in `backend/.env`:

```env
MURF_API_KEY=your_murf_api_key
```

Then restart `python server.py`.

### Purchased voice does not appear in Upload

Make sure the voice appears in `/marketplace`, purchase transaction succeeded, and the backend can download `meta.json` from the Walrus bundle.

### Agent joins but does not speak

Check backend logs, `backend/storage/agent_worker.log`, LiveKit credentials, and `OPENAI_API_KEY`.

## License

MIT
