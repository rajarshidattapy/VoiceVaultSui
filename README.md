# VoiceVault

**Own Your Voice. Deploy Your Agent. Earn Forever.**

VoiceVault is a decentralized Web3 platform for creating, owning, and monetizing AI voice models on the Sui blockchain. Users can train custom AI voice models, mint on-chain ownership NFTs, deploy autonomous voice agents powered by LiveKit, and earn crypto every time someone uses their voice. It bridges the gap between voice creators and consumers through a transparent, decentralized marketplace with cryptographic proof of rights and automated payment distribution.

![License](https://img.shields.io/badge/license-MIT-blue)
![Status](https://img.shields.io/badge/status-active-brightgreen)

---

## 🌟 Features

### Voice Ownership
- **Voice Registration** — Train and register custom AI voice models on-chain as NFTs
- **Global Registry** — On-chain `VoiceRegistry` shared object makes all voices globally discoverable (no localStorage dependency)
- **Voice Marketplace** — Browse, search, and license voices from creators worldwide
- **On-chain License Pass** — Purchasing a voice mints a `LicensePass` object to your wallet; backend verifies it instead of trusting internal DB logic

### Agent Deployment (`/deploy`)
- **4-step wizard** — Voice → Template → Configure → Deploy
- **5 agent templates** — Sales Agent, Support Agent, Tutor Agent, Creator Clone, Custom
- **LLM choice** — GPT-4o, Claude 3.5 Sonnet, Gemini 1.5 Pro, Groq Llama 3
- **Pay-per-call pricing** — Set a SUI price per call; payment split handled on-chain
- **LiveKit integration** — Generates a voice room and agent worker start command on deploy
- **Agent dashboard** — See all deployed agents, live/paused status, call count, earnings

### Payments & Access Control
- **Royalty split** — Every payment automatically splits: 2.5% platform fee, 10% royalty, remainder to creator
- **On-chain access verification** — Backend queries Sui RPC for `LicensePass` ownership; no permissive placeholder logic
- **Revenue tracking** — Creator earnings visible in the dashboard

---

## 🏗️ Tech Stack

### Frontend
- **Framework**: React 18 + TypeScript
- **Bundler**: Vite
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui + Radix UI
- **Web3**: `@mysten/sui`, `@mysten/dapp-kit`
- **State**: React Context + TanStack Query
- **Charts**: Recharts

### Backend
- **Language**: Python 3.8+
- **API Framework**: FastAPI + Uvicorn
- **Storage**: Walrus (content-addressed blob storage)
- **Voice runtime**: LiveKit Agents (`livekit-api`)
- **Agent store**: JSON-backed flat file store (`storage/agents.json`)

### Blockchain
- **Language**: Move 2024
- **Network**: Sui testnet / mainnet
- **Modules**: `voice_identity`, `payment`, `agent_identity`

---

## 📋 Prerequisites

- **Node.js** 18+
- **Python** 3.8+
- **Sui CLI** (for contract deployment)
- **Sui Wallet** browser extension
- **LiveKit account** (optional — required for live voice rooms)

---

## 🚀 Installation

### 1. Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python server.py              # http://localhost:8000
```

### 3. Smart Contracts

```bash
cd voice_vault_sui
sui client publish --gas-budget 50000000
```

After publishing, copy the **Package ID** and the **VoiceRegistry shared object ID** from the output into `.env`.

---

## ⚙️ Environment Variables

Copy `.env` at the project root and fill in your values:

```env
# ── Sui ──────────────────────────────────────────────
SUI_NETWORK=testnet
SUI_RPC_URL=https://fullnode.testnet.sui.io
SUI_PACKAGE_ID=0x<your_package_id>
SUI_VOICE_REGISTRY_ID=0x<registry_shared_object_id>

# ── Frontend (Vite) ───────────────────────────────────
VITE_SUI_PACKAGE_ID=0x<your_package_id>
VITE_SUI_VOICE_REGISTRY_ID=0x<registry_shared_object_id>
VITE_API_URL=http://localhost:8000

# ── Walrus ────────────────────────────────────────────
WALRUS_STORAGE_MODE=local          # or "remote"
WALRUS_PUBLISHER_URL=https://publisher.walrus-testnet.walrus.space

# ── LiveKit (required for live voice agent rooms) ─────
# Get credentials at https://cloud.livekit.io
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret

# ── LLM providers (used by the agent worker) ──────────
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

---

## 📁 Project Structure

```
VoiceVaultSui/
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Index.tsx          Landing page
│       │   ├── Marketplace.tsx    Voice discovery & purchase
│       │   ├── Upload.tsx         Voice model processing & registration
│       │   ├── Deploy.tsx         Agent deployment wizard + dashboard
│       │   └── Dashboard.tsx      Creator earnings & analytics
│       ├── hooks/
│       │   ├── useVoiceMetadata.ts
│       │   ├── useGlobalRegistry.ts   On-chain registry query
│       │   ├── useVoiceRegister.ts
│       │   ├── useVoiceUnregister.ts
│       │   └── usePayForInference.ts  Payment + LicensePass mint
│       └── lib/
│           ├── contracts.ts       Package ID, registry ID, fee constants
│           ├── agentApi.ts        Agent CRUD + deploy API client
│           ├── voiceRegistry.ts   (legacy — superseded by on-chain registry)
│           ├── purchasedVoices.ts Local cache of purchased voices
│           └── walrus.ts          Walrus manifest fetch helpers
│
├── backend/
│   ├── server.py          FastAPI app + all routes
│   ├── agent_store.py     JSON-backed agent store
│   ├── livekit_service.py LiveKit token generation
│   ├── walrus.py          Walrus storage + verify_license_pass()
│   ├── voice_model.py     Voice embedding + bundle generation
│   └── storage/
│       ├── walrus/        Local Walrus blob store
│       └── agents.json    Deployed agent configs
│
├── voice_vault_sui/
│   └── sources/
│       ├── voice_identity.move   VoiceIdentity NFT + VoiceRegistry
│       ├── payment.move          Royalty split + LicensePass mint
│       └── agent_identity.move   AgentIdentity on-chain object
│
└── docs/
```

---

## 🎯 Usage

### Running the Application

```bash
# Terminal 1 — backend
cd backend && python server.py

# Terminal 2 — frontend
cd frontend && npm run dev
```

### Creating & Registering a Voice

1. Connect your Sui wallet
2. Go to **Create Voice** (`/upload`)
3. Record or upload a voice sample
4. Process the model → uploads bundle to Walrus
5. Register on-chain → mints a `VoiceIdentity` NFT to your wallet
6. Your voice appears in the global marketplace immediately

### Purchasing a Voice

1. Browse **Marketplace** (`/marketplace`)
2. Click **Buy Voice** on any listing
3. Approve the SUI transaction — a `LicensePass` NFT is minted to your wallet
4. Go to **Create Voice** → use the purchased voice for TTS generation

### Deploying a Voice Agent

1. Go to **Deploy Agent** (`/deploy`)
2. **Step 1 — Voice**: Confirm your registered on-chain voice
3. **Step 2 — Template**: Pick Sales Agent, Support Agent, Tutor, Creator Clone, or Custom
4. **Step 3 — Configure**: Set agent name, system prompt, LLM provider, and price per call (SUI)
5. **Step 4 — Deploy**: Review summary → click **Deploy Agent**
6. Copy the displayed worker start command and run it in a terminal:

```bash
LIVEKIT_URL=wss://... LIVEKIT_API_KEY=... LIVEKIT_API_SECRET=... ROOM_NAME=vv-<id> python agent_worker.py dev
```

7. Click **Talk** on your agent card to open the live voice room
8. Callers pay your configured SUI price per call, split on-chain automatically

---

## 🔐 Smart Contracts

### `voice_identity.move`
- `VoiceRegistry` — shared object; all registered voice owners appended on every `register_voice` call
- `VoiceIdentity` — owned NFT per creator with name, Walrus URI, rights, price
- `register_voice(registry, ...)` — appends owner to global registry
- `delete_voice(registry, ...)` — removes owner from registry

### `payment.move`
- `LicensePass` — owned NFT minted to the buyer on every successful purchase
- `pay_with_royalty_split(payment, voice_id, ...)` — splits coins and mints `LicensePass` in a single transaction
- Fee structure: **2.5% platform fee**, **10% royalty**, remainder to creator

### `agent_identity.move`
- `AgentIdentity` — on-chain object linking a voice to a deployed agent config
- `create_agent`, `pause_agent`, `resume_agent`, `delete_agent`
- Emits `AgentCreated` event on deployment

---

## 📡 API Reference

### Voice

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/voice/process` | Process audio → generate embedding bundle → upload to Walrus |
| POST | `/api/tts/generate` | Generate speech (owner or valid `LicensePass` required) |
| POST | `/api/walrus/upload` | Upload a voice bundle to Walrus |
| POST | `/api/walrus/download` | Download a file from a Walrus bundle |
| POST | `/api/walrus/delete` | Delete a voice bundle (owner only) |

### Payments

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/payment/breakdown` | Calculate platform fee + royalty + creator split |

### Agent Deploy

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/agent/create` | Create a new agent config |
| GET | `/api/agent/list?owner=` | List all agents for an owner address |
| GET | `/api/agent/:id` | Get a single agent |
| POST | `/api/agent/deploy/:id` | Mark agent live, generate LiveKit room + token |
| POST | `/api/agent/pause/:id` | Pause agent |
| POST | `/api/agent/resume/:id` | Resume agent |
| DELETE | `/api/agent/:id` | Delete agent |
| POST | `/api/agent/join/:id` | Get a user token to join the agent's room |

---

## 🏃 Development

```bash
# Frontend
npm run dev          # Dev server
npm run build        # Production build
npm run lint         # ESLint
npm run type-check   # TypeScript check

# Backend
python server.py     # Dev server (auto-reloads with uvicorn --reload)
```

---

## 📦 Production Deployment

```bash
# Frontend
cd frontend && npm run build     # outputs to dist/

# Backend
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker server:app

# Or Docker
docker build -t voicevault-backend ./backend
docker run -p 8000:8000 --env-file .env voicevault-backend
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes
4. Open a Pull Request

Code style: ESLint for frontend, PEP 8 for backend, Move style guide for contracts.

---

## 📄 License

MIT — see [LICENSE](../LICENSE).

## 🔗 Links

- [Sui Documentation](https://docs.sui.io)
- [Walrus](https://walrus.site)
- [LiveKit Agents](https://github.com/livekit/agents)
- [dApp Kit](https://github.com/MystenLabs/sui)
