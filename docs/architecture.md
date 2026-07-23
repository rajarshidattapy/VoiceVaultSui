# VoiceVault Sui Architecture

This document describes the current repository architecture for VoiceVault Sui. It is written from the source code in this repo, not from an external product description.

VoiceVault is a Web3 voice marketplace and voice-agent platform on Sui. Creators process a voice sample, store the generated voice bundle through the backend's Walrus integration, register the bundle URI on-chain, sell access in the marketplace, and optionally deploy LiveKit-based voice agents that use the registered voice metadata.

## System At A Glance

```text
Browser
  React/Vite dApp
  Sui wallet extension
  localStorage purchase cache
        |
        | HTTP REST
        v
FastAPI backend
  voice processing
  Walrus proxy and local/remote storage
  Murf TTS bridge
  x402 payment verification and local usage passes
  agent create/deploy/join APIs
        |
        +---------------------> Sui JSON-RPC
        |                       VoiceIdentity, LicensePass, payments
        |
        +---------------------> Walrus Publisher/Aggregator
        |                       voice bundle blobs and manifests
        |
        +---------------------> Murf API
        |                       generated speech
        |
        +---------------------> LiveKit Cloud
        |                       real-time agent rooms
        |
        +---- starts locally --> swaraos_mcp_server.py
        |
        +---- starts locally --> agent_worker.py
                                OpenAI Realtime voice agent
```

The active runtime is centered on:

- `frontend/`: React, TypeScript, Vite, Tailwind, shadcn/Radix UI, Sui dApp Kit.
- `backend/`: FastAPI API server plus storage, TTS, payment, LiveKit, MCP, and agent modules.
- `contracts/`: Sui Move package for voice identity, payments, agent identity, and x402-style usage passes.
- `deploy/` and root deployment files: Render, Vercel, AWS ECS/Amplify examples.
- `docs/`: setup, deployment, data-flow, and integration notes.

`agentmcp/backend/` is a legacy/prototype backend. It contains an older SQLite-centered SwaraOS/Monad-era API, Sarvam/Chatterbox integrations, and duplicated agent files. The root README, root Dockerfile, `render.yaml`, and frontend API clients all point to the active `backend/` implementation.

## Repository Map

```text
VoiceVaultSui/
  README.md
  architecture.md
  Dockerfile
  render.yaml
  .env.example

  backend/
    server.py                 Active FastAPI server
    voice_model.py            Audio normalization, placeholder embedding, bundle creation
    walrus.py                 Walrus/local storage abstraction and access checks
    x402.py                   Sui payment-proof verification for HTTP 402 flow
    usage_store.py            JSON-backed usage-pass store
    agent_store.py            JSON-backed deployed-agent store
    agent_index.py            Search/discovery over deployed agents
    livekit_service.py        LiveKit tokens, dispatch, room helpers
    agent_worker.py           LiveKit/OpenAI realtime voice-agent worker
    swaraos_mcp_server.py     MCP server exposing agent network tools
    shelby.py                 Legacy wrapper over Walrus helpers
    requirements.txt
    Dockerfile
    scripts/

  frontend/
    src/
      App.tsx                 Route tree and providers
      contexts/               Sui wallet + React Query provider
      pages/                  Landing, marketplace, dashboard, upload, deploy, docs
      components/             Layout, voice, marketplace, dashboard, x402, UI primitives
      hooks/                  Wallet, Sui object, payment, registry, Walrus metadata hooks
      lib/                    Backend clients, contract helpers, Walrus helpers, local caches
    package.json
    vite.config.ts
    vercel.json
    nginx.conf

  contracts/
    Move.toml
    Published.toml
    sources/
      voice_identity.move
      payment.move
      agent_identity.move
      x402_payment.move
    tests/

  agentmcp/
    backend/                  Legacy/prototype backend
    monad_readme.md           Older product/readme material

  deploy/
    vercel.env.example
    aws/
      ecs-task-definition.example.json
      amplify.yml.example
      frontend.env.example
      README.md

  docs/
    AWS_DEPLOYMENT_PLAN.md
    FULL_STACK_DEPLOYMENT.md
    RENDER_DEPLOYMENT.md
    LIVEKIT_SETUP.md
    WALRUS.md.md
    DATA_FLOW_DIAGRAMS.md
    TECHNICAL_OVERVIEW.md
    ...
```

## Frontend Architecture

The frontend is a Vite React single-page app. It uses:

- React 18 and TypeScript.
- React Router for page routing.
- `@mysten/dapp-kit` and `@mysten/sui` for Sui wallet and transaction flows.
- TanStack Query through `WalletContext.tsx`.
- Tailwind CSS and shadcn/Radix primitives for UI.
- `sonner` and the local toast components for user feedback.

### Providers And Routes

`frontend/src/App.tsx` wraps the app in:

- `HelmetProvider`
- `WalletProvider`
- `TooltipProvider`
- toast providers
- `BrowserRouter`

Routes:

| Route | Component | Access | Purpose |
| --- | --- | --- | --- |
| `/` | `Index` | Public | Landing page |
| `/marketplace` | `Marketplace` | Wallet-gated | Browse and buy registered voices |
| `/dashboard` | `Dashboard` | Wallet-gated | Creator/user dashboard |
| `/upload` | `Upload` | Wallet-gated | Process voice, register voice, generate TTS |
| `/deploy` | `Deploy` | Wallet-gated | Create and deploy voice agents |
| `/docs` | `Docs` | Public | In-app docs |
| `*` | `NotFound` | Public | Fallback |

`ProtectedRoute` enforces wallet connection for the core app flows.

### Wallet And Sui Client

`frontend/src/contexts/WalletContext.tsx` creates network config for Sui testnet and mainnet, then defaults to testnet:

```text
QueryClientProvider
  SuiClientProvider(defaultNetwork="testnet")
    SuiWalletProvider(autoConnect)
```

Most Sui access is through dApp Kit hooks:

- `useCurrentAccount`
- `useSuiClient`
- `useSignAndExecuteTransaction`

### Contract Helpers

`frontend/src/lib/contracts.ts` defines the deployed package constants, fee constants, and SUI/MIST conversion helpers.

`frontend/src/lib/voiceContract.ts` builds arguments for:

- `voice_identity::register_voice`
- `voice_identity::delete_voice`

It checks the normalized Move function signature so the frontend can support deployed contract shapes that do or do not require an explicit `VoiceRegistry` argument. For the current contracts in `contracts/sources`, the registry argument is required.

`frontend/src/lib/paymentContract.ts` builds arguments for:

- `payment::pay_with_royalty_split`

It detects whether the deployed payment contract expects the newer 5-argument shape that mints `LicensePass`, or an older 4-argument shape that only splits payment.

### Important Hooks

| Hook | Responsibility |
| --- | --- |
| `useSuiWallet` / `use-wallet` | Convenience wrapper for current wallet state |
| `useVoiceRegister` | Builds, signs, and confirms `register_voice` transactions |
| `useVoiceUnregister` | Verifies ownership and signs `delete_voice` transactions |
| `useVoiceMetadata` | Fetches the connected wallet's `VoiceIdentity` objects |
| `useMarketplaceVoices` | Discovers marketplace voices from Sui transactions and enriches them with Walrus metadata |
| `useVoicesWithWalrusMetadata` | Fetches voice objects for owners and merges in manifest metadata |
| `usePayForInference` | Executes full license purchase via `payment::pay_with_royalty_split` |
| `useX402Pay` | Performs simple SUI transfer and asks backend to create a local usage pass |

### API Clients

`frontend/src/lib/api.ts` is the core backend REST client. It resolves the backend URL from:

1. `VITE_PROXY_URL`
2. `VITE_API_URL`
3. `VITE_BACKEND_URL`
4. `http://localhost:8000`

It exposes:

- `generateTTS`
- `getPaymentBreakdown`
- `processVoiceModel`
- `uploadToWalrus`
- `downloadFromWalrus`
- `deleteFromWalrus`
- `downloadModelFile`
- `deleteModelBundle`

`frontend/src/lib/agentApi.ts` wraps the agent endpoints:

- create, list, deploy, pause, resume, delete, join, talk.

`frontend/src/lib/walrus.ts` can fetch manifests and blobs directly from the configured aggregator URL. When `VITE_WALRUS_AGGREGATOR_URL` points at the backend proxy, blob reads go through `GET /api/walrus/blobs/{blob_id}`.

### Frontend Persistence

The browser stores purchased voices in `localStorage` under:

```text
voicevault_purchased_voices
```

Records include voice IDs, object IDs, owner, buyer, model URI, transaction hash, price, and license mode. This cache is only a UX convenience. Real access is checked by the backend through owner access, `LicensePass`, usage passes, or transaction proof.

## Backend Architecture

`backend/server.py` is the active FastAPI application. It loads env files in this order:

1. `backend/.env`
2. project root `.env`
3. `frontend/.env`

The backend configures CORS from `CORS_ORIGINS`, `CORS_ALLOW_CREDENTIALS`, and `CORS_ALLOW_ORIGIN_REGEX`, defaulting to local dev origins.

### Backend Modules

| Module | Role |
| --- | --- |
| `server.py` | HTTP API, orchestration, CORS, helper-process lifecycle |
| `voice_model.py` | Converts uploaded audio into a voice model bundle |
| `walrus.py` | Content-addressed storage, local/remote Walrus modes, manifests, access checks |
| `x402.py` | Verifies Sui transfer digests and builds HTTP 402 responses |
| `usage_store.py` | JSON usage-pass records for x402-style pay-per-use |
| `agent_store.py` | JSON agent configs in `storage/agents.json` |
| `agent_index.py` | Token-based live-agent discovery |
| `livekit_service.py` | LiveKit tokens, agent dispatch, participant removal |
| `agent_worker.py` | LiveKit worker using OpenAI Realtime and optional MCP tools |
| `swaraos_mcp_server.py` | MCP server for agent discovery, delegation, and room invitation |
| `shelby.py` | Backward-compatible import wrapper |

### Voice Processing Pipeline

`POST /api/voice/process` receives multipart form data:

- `audio`
- `name`
- `description`
- `owner`
- `voiceId`

The backend then:

1. Reads the uploaded audio.
2. Calls `voice_model.process_voice_model`.
3. Normalizes audio with FFmpeg to 16 kHz mono WAV if FFmpeg is installed.
4. Generates a deterministic hash-based placeholder embedding.
5. Creates a bundle:
   - `embedding.bin`
   - `config.json`
   - `meta.json`
   - `preview.wav`
6. Uploads the bundle through `walrus.upload_to_walrus`.
7. Returns the manifest URI and blob references.

Important implementation note: `voice_model.py` explicitly marks embedding generation as a placeholder. It does not run a production speaker-embedding model yet.

### Walrus Storage Abstraction

`backend/walrus.py` supports two modes:

| Mode | Env | Behavior |
| --- | --- | --- |
| Local | `WALRUS_STORAGE_MODE=local` | Stores content-addressed blobs under `backend/storage/walrus` or `VOICEVAULT_STORAGE_DIR` |
| Remote | `WALRUS_STORAGE_MODE=remote` | Uses Walrus Publisher/Aggregator HTTP APIs |

Local storage layout:

```text
backend/storage/
  walrus/
    blobs/
      {blobId}.bin
    meta/
      {blobId}.json
  agents.json
  usage_passes.json
  agent_worker.log
  agent_network_mcp.log
```

The manifest pattern is central. Walrus stores blobs, but VoiceVault voice models need multiple files. The backend stores each file as a blob, then stores a manifest blob that maps file names to blob references.

Manifest shape:

```json
{
  "voiceId": "voice_...",
  "owner": "0x...",
  "blobs": {
    "embedding.bin": {
      "blobId": "...",
      "objectId": "0x...",
      "size": 1024
    },
    "config.json": {
      "blobId": "...",
      "objectId": "0x...",
      "size": 123
    },
    "meta.json": {
      "blobId": "...",
      "objectId": "0x...",
      "size": 456
    },
    "preview.wav": {
      "blobId": "...",
      "objectId": "0x...",
      "size": 160000
    }
  },
  "version": 1,
  "storageMode": "local",
  "manifestBlobId": "...",
  "manifestObjectId": "0x...",
  "walrusUri": "walrus://...",
  "size": 123456,
  "previewUrl": "http://..."
}
```

Large files are chunked when they exceed `WALRUS_MAX_BLOB_SIZE`; the manifest entry then contains `chunked`, `blobIds`, and `objectIds`.

### TTS And Access Control

`POST /api/tts/generate` supports:

- `murf://...` URIs: direct Murf TTS.
- `walrus://...` URIs: access-checked voice usage, then Murf TTS.

For `walrus://` models the backend requires `requesterAccount` and checks access in this order:

1. Owner access through `walrus.verify_walrus_access`.
2. On-chain `payment::LicensePass` ownership through Sui RPC.
3. Local x402 usage pass from `usage_store`.
4. Fresh `X-Payment-Proof` header verified through `x402.verify_sui_payment`.
5. Legacy marketplace purchase transaction proof through `walrus.verify_purchase_transaction`.

If none pass, the backend returns HTTP 402 with payment requirements from `x402.make_402_response`.

After access passes, the backend verifies that key Walrus bundle files exist, then calls Murf. Current synthesized output is configured by `MURF_VOICE_ID` or request fields. The stored voice embedding is not yet used to drive Murf custom cloning.

Important implementation note: `frontend/src/lib/murfVoice.ts` has a `murfVoiceClone` helper, but it currently ignores the uploaded reference audio and delegates to normal backend Murf TTS.

### Payment Paths

There are two payment experiences:

1. Full license purchase:
   - Frontend calls `payment::pay_with_royalty_split` on Sui.
   - Current Move contract mints a `LicensePass` object to the buyer.
   - Frontend caches the purchase locally for UX.
   - Backend verifies `LicensePass` ownership for future TTS.

2. x402-style pay-per-use:
   - Frontend sends a direct SUI transfer to the creator.
   - Backend verifies the transaction digest through Sui RPC.
   - Backend creates a local JSON `UsagePass`.
   - TTS consumes one use when generation succeeds.

The Move package also contains an on-chain `x402_payment` module with `UsagePass`, but the active frontend/backend x402 path currently uses backend-local `usage_store.py`, not that Move module.

### Agent Runtime

Agents are created through `POST /api/agent/create`. The backend stores configs in `agents.json` with fields such as:

- `id`
- `owner`
- `status`
- `room_name`
- `agent_name`
- `template_id`
- `system_prompt`
- `skills`
- `language`
- `llm_provider`
- `price_per_call`
- `voice_name`
- `voice_uri`
- `voice_id`
- `x402_enabled`
- `x402_price_sui`
- `x402_uses`

Deployment flow:

1. Frontend creates an agent config.
2. Frontend calls `POST /api/agent/deploy/{agent_id}`.
3. Backend prepares a LiveKit room token and join URL.
4. Backend ensures the MCP server is running unless disabled.
5. Backend ensures the LiveKit agent worker is running unless externally supervised.
6. Backend dispatches the configured LiveKit agent into the `vv-{agent_id}` room.
7. Agent status becomes `live`.

`agent_worker.py` registers a named LiveKit agent server. It:

- Loads agent config from `agents.json`.
- Uses OpenAI Realtime via `livekit-plugins-openai`.
- Builds prompt instructions from the agent config.
- Optionally connects to the MCP server.
- Provides a `transfer_call_to_agent` tool for live handoff.
- Can park the source agent silently after a handoff.

`swaraos_mcp_server.py` exposes MCP tools:

- `discover_agents`
- `get_agent_card`
- `delegate_to_agent`
- `invite_agent_to_room`
- `invite_best_agent_to_room`

The active worker allows only discovery/card/delegation tools through the MCP server and implements live room transfer through its own function tool.

## Move Contract Architecture

The Sui package is in `contracts/`. `Published.toml` records the testnet package:

```text
0x1ad12f0fd581dbd4fef7a30c9cff9bececfca1da450fe53257791502b3db073d
```

The README lists the active shared voice registry object as:

```text
0xfad2808bcd104197b53b1fddede5f25d5c16303b147d280c2aa7ff69d27e5d59
```

### `voice_identity.move`

Defines:

- `VoiceRegistry`: shared registry with `voice_owners: vector<address>`.
- `VoiceIdentity`: owned voice object with owner, name, model URI, rights, price, timestamp.

Key functions:

- `init`: creates and shares `VoiceRegistry`.
- `register_voice`: creates a `VoiceIdentity` and appends sender to registry.
- `delete_voice`: deletes a voice and removes owner from registry.
- `get_voice_owners`
- `get_metadata`
- `get_voice_id`

The source comment says one voice per user is enforced externally. The frontend enforces this by checking for existing `VoiceIdentity` objects before registration.

### `payment.move`

Defines:

- `LicensePass`: owned proof of purchase for a `VoiceIdentity`.
- `LicenseIssued`, `PaymentReceived`, `RoyaltyPaid`, `PlatformFeePaid` events.

Fee constants:

- Platform fee: 250 bps, or 2.5%.
- Royalty: 1000 bps, or 10% of the remaining amount after platform fee.

Key functions:

- `pay_with_royalty_split<T>`:
  - Splits payment to platform, royalty recipient, and creator.
  - Mints `LicensePass` to buyer.
  - Emits payment/license events.
- `pay_full_to_creator<T>`
- `calculate_payment_breakdown`
- `license_voice_id`
- `license_buyer`

### `agent_identity.move`

Defines on-chain `AgentIdentity` with owner, voice ID, config URI, pricing, active flag, and created time.

Key functions:

- `create_agent`
- `pause_agent`
- `resume_agent`
- `delete_agent`
- `get_metadata`
- `is_active`
- `owner`

Current frontend/backend agent deployment uses backend JSON storage, not this module directly.

### `x402_payment.move`

Defines on-chain `UsagePass` with user, voice ID, uses remaining, expiry, and created time.

Key functions:

- `create_usage_pass<T>`
- `consume_usage`
- `has_access`
- `uses_remaining`
- `expires_at`
- `voice_id`

Current x402 runtime uses backend-local JSON passes instead of this Move module.

## Main Runtime Workflows

### 1. Voice Creation And Registration

```text
User opens /upload
  |
  | record/upload audio, name, description
  v
frontend backendApi.processVoiceModel
  |
  | POST /api/voice/process
  v
backend voice_model.process_voice_model
  |
  | normalize audio, create embedding/config/meta/preview
  v
backend walrus.upload_to_walrus
  |
  | store files and manifest
  v
returns walrus://{manifestBlobId}
  |
  | frontend autofills VoiceRegistrationForm
  v
frontend useVoiceRegister
  |
  | Sui wallet signs voice_identity::register_voice
  v
Sui stores VoiceIdentity(model_uri = walrus://...)
```

### 2. Marketplace Discovery

```text
User opens /marketplace
  |
  v
useMarketplaceVoices
  |
  | query Sui transaction blocks for voice_identity::register_voice
  | collect object IDs and owners
  | fetch VoiceIdentity objects
  | parse Move string fields
  v
frontend Walrus helper fetches manifest and meta.json
  |
  | enrich name, description, preview URL
  v
Marketplace renders VoiceMarketplaceCard grid
```

Marketplace does not depend on a centralized voice index. It derives voices from Sui chain data and Walrus manifests.

### 3. Full License Purchase And TTS

```text
User clicks Buy Voice
  |
  v
usePayForInference builds payment transaction
  |
  | payment::pay_with_royalty_split<SUI>
  v
Sui splits payment and mints LicensePass
  |
  v
frontend caches purchase in localStorage
  |
  v
User opens /upload and chooses purchased voice
  |
  v
POST /api/tts/generate
  |
  | backend checks LicensePass ownership through Sui RPC
  | backend checks Walrus bundle files
  | backend calls Murf
  v
audio blob returned to browser
```

### 4. x402 Pay-Per-Use TTS

```text
User clicks Try on marketplace card
  |
  v
useX402Pay transfers SUI to creator
  |
  v
POST /api/x402/create-pass
  |
  | backend verifies tx digest through Sui RPC
  | backend stores local usage pass
  v
POST /api/tts/generate
  |
  | backend finds usage pass
  | consumes one use
  | calls Murf
  v
audio returned
```

If a direct TTS call lacks access, the backend responds with HTTP 402 and a payment requirement payload.

### 5. Agent Deployment And LiveKit Call

```text
User opens /deploy
  |
  | app fetches user's registered VoiceIdentity
  v
user picks template and config
  |
  v
POST /api/agent/create
  |
  | backend stores config in agents.json
  v
POST /api/agent/deploy/{agent_id}
  |
  | backend prepares room token
  | starts MCP server if needed
  | starts LiveKit worker if needed
  | dispatches agent to room
  v
agent status = live
  |
  v
POST /api/agent/talk/{agent_id}
  |
  | returns LiveKit join URL/token
  v
browser opens LiveKit room
```

### 6. Agent Delegation And Handoff

```text
LiveKit worker receives user request
  |
  | if specialist help is needed:
  v
MCP discover_agents / delegate_to_agent
  |
  | private text delegation
  v
source agent summarizes answer

or:

LiveKit worker calls transfer_call_to_agent
  |
  | backend discovers or targets another agent
  | backend dispatches target to same LiveKit room
  v
source agent says short handoff line
  |
  v
source agent parks itself silently
```

### 7. Voice Deletion

```text
User opens /upload with existing registered voice
  |
  v
VoiceRegistrationForm detects existing VoiceIdentity
  |
  v
useVoiceUnregister signs voice_identity::delete_voice
  |
  v
backendApi.deleteModelBundle
  |
  | POST /api/walrus/delete
  | local mode deletes manifest and unreferenced blobs
  | remote mode deletion is not implemented by backend helper
```

## Active Backend API Surface

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/healthz` | Health check |
| `POST` | `/api/tts/generate` | Generate TTS for `murf://` or access-checked `walrus://` voice |
| `POST` | `/api/payment/breakdown` | Calculate display payment breakdown |
| `POST` | `/api/voice/process` | Process uploaded audio and store a Walrus bundle |
| `POST` | `/api/walrus/upload` | Upload a bundle directly |
| `GET` | `/api/walrus/blobs/{blob_id}` | Backend Walrus aggregator/proxy route |
| `POST` | `/api/walrus/download` | Download one file from a Walrus manifest |
| `POST` | `/api/walrus/delete` | Delete local Walrus bundle if caller is owner |
| `POST` | `/api/agent/create` | Create JSON-backed agent config |
| `GET` | `/api/agent/list?owner=...` | List owner's agents |
| `GET` | `/api/agent/worker-status` | Report worker/MCP process state |
| `GET` | `/api/agent/discover` | Search live agents by skill/language |
| `POST` | `/api/agent/register-skill` | Update agent skills and language |
| `POST` | `/api/agent/delegate/{agent_id}` | Ask another live agent for text answer |
| `POST` | `/api/agent/invite/{agent_id}` | Dispatch another agent into a LiveKit room |
| `GET` | `/api/agent/{agent_id}` | Fetch public/full agent config |
| `POST` | `/api/agent/deploy/{agent_id}` | Mark live and prepare LiveKit room |
| `POST` | `/api/agent/pause/{agent_id}` | Pause an agent |
| `POST` | `/api/agent/resume/{agent_id}` | Resume an agent |
| `DELETE` | `/api/agent/{agent_id}` | Delete an agent |
| `POST` | `/api/agent/join/{agent_id}` | Create LiveKit join token for participant |
| `POST` | `/api/agent/talk/{agent_id}` | Create LiveKit talk session for live agent |
| `GET` | `/api/x402/requirements` | Return HTTP 402 payment requirements |
| `POST` | `/api/x402/verify` | Verify payment proof without issuing pass |
| `POST` | `/api/x402/create-pass` | Verify proof and create local usage pass |
| `POST` | `/api/x402/consume` | Consume one local usage-pass use |
| `GET` | `/api/x402/status` | Check active usage pass |
| `GET` | `/api/x402/passes` | List user's usage passes |

Implementation note: `/api/payment/breakdown` uses an `Octas` naming convention and a `100_000_000` multiplier in `server.py`, while the Sui frontend transaction helpers use MIST with `1_000_000_000` MIST per SUI. The on-chain transaction path is the source of settlement truth.

## Environment Configuration

Only variable names are listed here. Do not commit real secrets.

### Frontend

The frontend only receives variables prefixed with `VITE_`:

```env
VITE_API_URL=
VITE_PROXY_URL=
VITE_BACKEND_URL=
VITE_WALRUS_AGGREGATOR_URL=
VITE_SUI_NETWORK=
VITE_SUI_RPC_URL=
VITE_SUI_PACKAGE_ID=
VITE_SUI_VOICE_REGISTRY_ID=
VITE_CHATTERBOX_SPACE=
VITE_OMNI_VOICE_SPACE=
```

### Backend Core

```env
PORT=
BACKEND_URL=
VOICEVAULT_STORAGE_DIR=
API_SECRET_KEY=
CORS_ORIGINS=
CORS_ALLOW_CREDENTIALS=
CORS_ALLOW_ORIGIN_REGEX=
LOG_LEVEL=
```

### Sui

```env
SUI_ADDRESS=
SUI_ALIAS=
SUI_NETWORK=
SUI_RPC_URL=
SUI_FULL_NODE_URL=
SUI_GAS_BUDGET=
SUI_PACKAGE_ID=
SUI_UPGRADE_CAPABILITY=
SUI_VOICE_REGISTRY_ID=
```

### Walrus

```env
WALRUS_STORAGE_MODE=
WALRUS_PUBLISHER_URL=
WALRUS_AGGREGATOR_URL=
WALRUS_EPOCHS=
WALRUS_DELETABLE=
WALRUS_MAX_BLOB_SIZE=
```

### TTS

```env
MURF_API_KEY=
MURF_KEY=
MURF_VOICE_ID=
MURF_LOCALE=
MURF_FORMAT=
MURF_SAMPLE_RATE=
MURF_MODEL_VERSION=
MURF_STYLE=
MURF_PITCH=
MURF_RATE=
MURF_VARIATION=
```

### LiveKit And Agent Network

```env
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
LIVEKIT_AGENT_NAME=
LIVEKIT_AGENT_HTTP_PORT=
LIVEKIT_AGENT_MODE=
LIVEKIT_AGENT_EXTERNAL=
LIVEKIT_AGENT_MANAGED=
LIVEKIT_WORKER_STARTUP_GRACE_SECONDS=
OPENAI_API_KEY=
OPENAI_REALTIME_VOICE=
AGENT_DELEGATION_MODEL=
AGENT_NETWORK_MCP_ENABLED=
AGENT_NETWORK_MCP_URL=
AGENT_NETWORK_MCP_REQUIRED=
MCP_HOST=
MCP_PORT=
MCP_STARTUP_GRACE_SECONDS=
MAX_DELEGATION_DEPTH=
AGENT_HANDOFF_PARK_FALLBACK_SECONDS=
AGENT_INITIAL_REPLY_WAIT_SECONDS=
AGENT_STRICT_USER_IDENTITY=
```

### x402

```env
X402_DEFAULT_PRICE_MIST=
X402_DEFAULT_USES=
```

## Deployment Architecture

### Local Development

Backend:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python server.py
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

`frontend/vite.config.ts` sets the dev server port to `6969`, so the local app is normally `http://localhost:6969` unless Vite chooses another port.

### Render

`render.yaml` deploys a Docker web service named `voicevault-backend` using the root `Dockerfile`. That Dockerfile:

- Starts from `python:3.11-slim`.
- Installs `backend/requirements.txt`.
- Copies `backend/`.
- Sets `PORT=8080`.
- Runs `python server.py`.

### Frontend Hosting

`frontend/vercel.json` configures Vercel for a Vite build and rewrites all routes to `index.html` so React Router works after refresh.

`frontend/nginx.conf` supports static hosting behind nginx.

### AWS

`deploy/aws/` contains examples for the AWS plan:

- ECS Fargate task definition for API, MCP, and worker containers.
- Amplify build spec for frontend.
- Amplify frontend env example.

The AWS docs indicate a production target of:

- Backend: ECS/Fargate.
- Frontend: Amplify Hosting.
- Secrets: AWS Secrets Manager.
- Runtime persistence: EFS.

## Security And Trust Boundaries

### What Is Trustless Or On-Chain

- Voice ownership is represented by Sui `VoiceIdentity` objects.
- Full license purchases can mint Sui `LicensePass` objects.
- Payment splitting is handled inside Move for the full purchase flow.
- Walrus blob IDs are content-addressed.

### What Is Backend-Trusted

- Audio processing and bundle creation.
- Murf API calls.
- Local Walrus mode.
- Local x402 usage passes.
- Agent configs in `agents.json`.
- LiveKit room token issuance.
- MCP server and agent delegation behavior.

### Important Hardening Areas

- Replace placeholder voice embeddings with a real model if voice similarity or cloning depends on them.
- Move x402 usage passes fully on-chain if backend-local passes are not acceptable.
- Add server-side rate limiting for TTS and upload endpoints.
- Keep CORS restricted in production.
- Keep Murf, LiveKit, OpenAI, and wallet/private keys out of frontend env.
- Remote Walrus deletion currently requires wallet-signed Sui operations and is not implemented by the backend helper.
- `agent_store.py` and `usage_store.py` are JSON-file stores; use a real database or durable shared volume for multi-instance deployment.

## Legacy `agentmcp/backend`

`agentmcp/backend/` is retained but is not the active backend described by the root README or deployment files. It includes:

- A separate FastAPI app titled `SwaraOS API`.
- SQLite persistence in `storage/voicevault.db`.
- Legacy endpoints such as `/api/voice/upload`, `/api/voice/list`, `/api/audio/{voice_id}`.
- Monad/Web3-era x402 verification in its `x402.py`.
- Sarvam and Chatterbox integrations.
- A copy of Walrus/storage and agent modules that diverges from active `backend/`.

Treat it as historical/prototype code unless a task explicitly targets it.

## Known Implementation Notes

- Active marketplace discovery is chain-derived, not database-derived.
- Frontend registration prevents more than one voice per wallet, but the Move contract itself does not enforce uniqueness.
- The backend TTS path verifies bundle files but uses Murf for actual output; the stored embedding is not yet used for synthesis.
- `murfVoiceClone` currently ignores the uploaded sample and performs regular Murf TTS.
- `payment::pay_with_royalty_split` mints `LicensePass` in the current source, but frontend code still supports older deployments that did not.
- The Move test file is a placeholder and does not currently exercise contract behavior.
- Several older docs contain stale diagrams or mojibake; prefer this document plus current source files for architecture decisions.

## Verification Commands

Common checks for this repo:

```powershell
cd frontend
npm install
npm run build
```

```powershell
cd backend
python -m py_compile server.py walrus.py voice_model.py agent_store.py usage_store.py livekit_service.py
```

```powershell
cd contracts
sui move build
```

Use the Sui and Walrus commands only in an environment where those CLIs and credentials are configured.
