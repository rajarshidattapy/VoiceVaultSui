# SwaraOS: Decentralized Voice Ownership & Monetization

![SwaraOS Logo](SwaraOS/image.png)

> **Own Your Voice. Earn Forever.**
>
> A Web3 platform where voice creators own their voice NFTs, license them on a decentralized marketplace, and earn SUI tokens automatically through smart contract royalty distribution.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Current Day Pain Points](#current-day-pain-points)
3. [Solution Overview](#solution-overview)
4. [Key Features](#key-features)
5. [Technology Stack](#technology-stack)
6. [Architecture](#architecture)
7. [Getting Started](#getting-started)
8. [Deployment](#deployment)
9. [How It Works](#how-it-works)
10. [Roadmap](#roadmap)
11. [Contributing](#contributing)
12. [License](#license)

---

## Problem Statement

The voice and audio industry is experiencing explosive growth—but creators are getting **zero compensation** for their voice assets.

### The Broken Status Quo

**Current Landscape**:
- Voice synthesis market: **$2.8B (2023)** → **$5.2B projected (2030)**
- AI voice agents market: **$1.2B** → **Growing 25%+ YoY**
- Voice cloning used by: OpenAI, ElevenLabs, Google, Adobe, etc.
- Creator compensation for their voices: **$0**

**Why This Matters**:
- Your voice is YOUR unique asset—it can't be replicated, faked, or stolen once locked in Web3
- Every time a brand uses your voice in a customer service bot, podcast, or AI agent, you should earn
- Current platforms (ElevenLabs, Synthesia, Runway) capture 100% of revenue; creators earn **nothing**

---

## Current Day Pain Points

### 1. **Creator Pain Points**

#### Problem 1.1: Zero Voice Ownership
**Today's Reality**:
- Upload your voice to ElevenLabs or similar? You get a synthetic voice ID, not ownership
- You can't prove you own it, license it, or prevent unauthorized use
- The platform can modify, delete, or repurpose your voice anytime
- If the platform shuts down (like many AI startups do), your voice data is gone

**Impact**:
- Singers, voice actors, and audiobook narrators can't monetize their voice at scale
- No way to grant selective licenses (e.g., "commercial use only", "time-limited", "geographic restrictions")
- No audit trail of who used your voice and when

**Example**:
```
🎤 Voice Actor Records Voice
  ↓
📤 Uploads to ElevenLabs
  ↓
❌ ElevenLabs owns the voice
  ↓
💰 Brand licenses voice for $5K
  ↓
🎤 Voice Actor gets: $0
```

---

#### Problem 1.2: No Automatic Royalty Distribution
**Today's Reality**:
- If you manage to negotiate a licensing deal, it's a legal nightmare
- Manual invoicing, payment processing, tax compliance
- No standardized royalty contracts
- No way to split royalties among multiple creators (e.g., co-artists, producers)

**Impact**:
- Only A-list celebrities can negotiate licensing deals (require legal teams)
- Indie creators can't viably license their voices (transaction costs exceed revenue)
- Royalty disputes are common; no transparent audit trail

**Example**:
```
Manual Deal Process:
🎤 Voice Creator negotiates with Brand
  ↓
⚖️ Lawyers draft custom contract
  ↓
💸 Brand sends check (slow, expensive)
  ↓
🧮 Creator pays taxes, accountant fees
  ↓
Net: Takes 6 months, costs $2K+ in legal/admin
Result: Deal dies. Too much friction.
```

---

#### Problem 1.3: No Marketplace for Voice Discovery
**Today's Reality**:
- Voice creators can't list their voices for licensing
- Brands that need voices manually search freelance platforms (Upwork, Fiverr) with poor discovery
- No standardized voice licensing marketplace
- No way to buy/sell voices programmatically (for API/agent use)

**Impact**:
- Creators stay invisible; can't sell at scale
- Brands spend weeks finding the right voice
- Price negotiations are opaque and inefficient
- No trust layer (how do you verify a voice's quality, rights, or provenance?)

---

### 2. **Brand / End-User Pain Points**

#### Problem 2.1: Licensing Friction & Legal Uncertainty
**Today's Reality**:
- Brands want to use diverse voices in customer service bots, but licensing is unclear
- Who owns the voice? Do I have rights to commercial use? What about modifications?
- No standardized licensing terms ("commercial OK but not adult content", etc.)
- Legal review takes weeks

**Impact**:
- Brands stick with generic TTS or hire expensive voice actors
- Opportunity cost: Projects delayed waiting for legal clarity
- Risk: Brands accidentally use voices without proper licenses

**Example**:
```
Brand wants to deploy support bot with voice
  ↓
Need diverse, natural voices
  ↓
❌ ElevenLabs: Unclear licensing terms
❌ Synthesia: Limited voice selection
❌ Hiring voice actors: $5K+, 4 weeks
  ↓
Result: Deploy with robotic TTS 😢
```

---

#### Problem 2.2: High Cost for Voice Access
**Today's Reality**:
- ElevenLabs: ~$99/month for limited voice selection
- Custom voice clones: $1K-$10K setup + $99/month
- Voice actor hiring: $500-$5K per session
- Licensing established voice talent: $10K+ per use

**Impact**:
- Startups can't afford premium voices; users get poor UX
- Enterprise projects negotiate bulk deals; limited innovation
- No pay-per-use model; all-or-nothing pricing

---

#### Problem 2.3: No Programmatic Voice Licensing (for AI Agents)
**Today's Reality**:
- As AI agents explode, they need voice APIs
- But there's no "voice licensing API" that handles:
  - Voice discovery
  - Instant licensing (no legal review)
  - Royalty payment + creator crediting
  - Automatic rights management

**Impact**:
- Agents default to text output (no voice)
- Agent developers manually manage licensing deals (doesn't scale)
- No way for agent-to-agent payments for voice use

**Example**:
```
AI Agent wants to speak with user
  ↓
Need voice, licensing, royalty payment
  ↓
❌ No standardized API for this
  ↓
Options:
  1. Use generic TTS (bad UX)
  2. Manually negotiate deal (6 months)
  3. Hire voice actor for every use (expensive)
  ↓
Result: No voice in agent 😢
```

---

### 3. **Platform Ecosystem Pain Points**

#### Problem 3.1: Voice Data Centralization
**Today's Reality**:
- All voice data lives on centralized servers (ElevenLabs, Google, OpenAI)
- Single point of failure: Platform hacked → all voices compromised
- No transparency: Users don't know how their voice data is used/trained
- Vendor lock-in: Can't export your voice, use elsewhere

**Impact**:
- Voice clones can be abused by bad actors
- Creators have zero privacy protections
- Switching costs are extremely high

---

#### Problem 3.2: No Standardized Voice Licensing Contract
**Today's Reality**:
- Each platform has different licensing terms (if they have any)
- No standardized way to encode restrictions:
  - Commercial use? Time limit? Geographic? Derivative works?
  - No smart contract enforcement
- Disputes rely on legal processes (slow, expensive)

**Impact**:
- Trust issues in voice licensing
- Compliance risk for brands
- Creators can't automate royalty enforcement

---

## Solution Overview

### What is SwaraOS?

**SwaraOS** is a decentralized platform for voice ownership, licensing, and monetization built on **Sui blockchain** with **Walrus storage** for content-addressed voice models.

**Core Value Proposition**:

```
┌─────────────────────────────────────────────────────────────────┐
│ For Voice Creators:                                             │
├─────────────────────────────────────────────────────────────────┤
│ ✅ Own your voice as an NFT (on-chain proof of ownership)       │
│ ✅ License to multiple brands (no exclusivity required)         │
│ ✅ Earn SUI tokens automatically (smart contract royalties)     │
│ ✅ Set your own price per use (pay-per-use or subscription)    │
│ ✅ Track usage & earnings via transparent ledger                │
│ ✅ No platform lock-in (your voice, your rules)                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ For Brands & Developers:                                        │
├─────────────────────────────────────────────────────────────────┤
│ ✅ Browse decentralized voice marketplace                       │
│ ✅ Instant licensing (HTTP 402 pay-per-use)                    │
│ ✅ Clear, transparent licensing terms                          │
│ ✅ Programmatic API for voice agents & bots                    │
│ ✅ Royalty payment automated (no middleman)                    │
│ ✅ Use voices in multiple projects without renegotiating       │
└─────────────────────────────────────────────────────────────────┘
```

### How It Solves the Pain Points

| Pain Point | Solution |
|---|---|
| **Zero voice ownership** | Voice NFTs on Sui blockchain prove ownership |
| **No automatic royalties** | Smart contract splits payments (2.5% platform, 10% royalty, 87.5% creator) |
| **No marketplace discovery** | Decentralized marketplace with search & filtering |
| **Licensing friction** | HTTP 402 standard enables instant pay-per-use |
| **High licensing costs** | Creator-direct model reduces costs 60-80% vs. ElevenLabs |
| **No agent licensing API** | Native HTTP 402 support for programmatic access |
| **Data centralization** | Walrus storage + Sui blockchain = decentralized by design |
| **No standardized contracts** | On-chain smart contract enforces terms automatically |

---

## Key Features

### 1. **Voice Registration & NFT Minting**

Creators upload audio → system generates voice fingerprint → mints VoiceIdentity NFT on Sui

**Process**:
```
🎤 Upload Audio (any format)
  ↓
⚡ Process: normalize → fingerprint → create Walrus bundle
  ↓
🔗 Mint VoiceIdentity NFT on Sui
  ↓
✅ Ownership proven on-chain
```

**Data Flow**:
- Audio normalized to 16kHz mono WAV
- Voice embedding generated (256-dim fingerprint)
- Files bundled: embedding.bin, config.json, meta.json, preview.wav
- Stored in Walrus (decentralized, content-addressed)
- VoiceIdentity NFT references Walrus URI

---

### 2. **Decentralized Voice Marketplace**

Browse, search, and license voices from creators

**Features**:
- Full-text search on voice name/description
- Filter by: language, price range, rights (commercial/personal)
- Preview audio (first 5 seconds)
- Creator profile & rating
- Transparent pricing per use

---

### 3. **Pay-Per-Use Voice Licensing (HTTP 402)**

Instant licensing without upfront payment or legal review

**Standard**: HTTP 402 Payment Required (RFC-compliant)

**Flow**:
```
User requests voice via API
  ↓
❌ No license? Server returns HTTP 402 with payment details
  ↓
👤 User pays via Sui wallet (1 transaction)
  ↓
✅ Smart contract:
   - Splits payment (platform fee | royalty | creator earnings)
   - Mints LicensePass NFT to user
   - Records event on-chain
  ↓
User retries API call with payment proof
  ↓
✅ Server verifies payment, grants access
```

**Benefits**:
- No subscription required
- Pay only for what you use
- Atomic payment + access (crypto-native)
- Creator earns immediately

---

### 4. **Smart Contract Royalty Distribution**

Automated, transparent payment splitting

```move
pub fun pay_with_royalty_split(
    payment: Coin<SUI>,
    voice_id: ID,
    creator: address,
    platform: address,
    royalty_recipient: address,
    ctx: &mut TxContext
) {
    // Split automatically:
    // - Platform fee: 2.5%
    // - Royalty: 10% of remainder
    // - Creator: 87.5%
    
    // Mint LicensePass NFT to buyer
    // Emit events for indexing
}
```

**On-Chain Verification**:
- Backend queries Sui RPC to verify LicensePass ownership
- No centralized database needed for licensing

---

### 5. **Voice Agents Powered by Your Voice**

Deploy AI agents that speak with your voice

**Features**:
- Template-based agent creation (Sales, Support, Tutor, Creator Clone)
- System prompt customization
- Multi-language support (Indian languages via Sarvam AI)
- LLM provider selection (GPT-4o, Claude, Gemini, Groq)
- LiveKit integration for real-time voice conversations

---

### 6. **Usage Tracking & Analytics Dashboard**

Creators see:
- Total voices registered
- Number of licenses sold
- Total earnings (SUI)
- Usage by voice
- Trending voices (most licensed)

Brands see:
- Active licenses
- Voice usage metrics
- Royalty costs

---

## Technology Stack

### Frontend
```
Framework        React 18 + TypeScript + Vite
CSS              Tailwind CSS + Shadcn/UI
State Mgmt       React Context + TanStack Query
Blockchain       @mysten/dapp-kit + @mysten/sui SDK
Real-time Voice  LiveKit (WebRTC)
UI Components    40+ Radix UI primitives
HTTP Client      Native Fetch API
```

### Backend
```
Framework        FastAPI 0.115.0
Server           Uvicorn (async ASGI)
Language         Python 3.11+
Audio Process    FFmpeg (normalization, preview)
Storage          Walrus (decentralized blobs)
Blockchain       Sui JSON-RPC client
Database         JSON file (MVP) → PostgreSQL (prod)
Voice AI         Sarvam AI (STT/TTS for Indian languages)
Agent Framework  LiveKit Agents
```

### Blockchain & Storage
```
Blockchain       Sui Testnet
Smart Contracts  Move language
Storage          Walrus (testnet aggregator)
Consensus        Sui's Byzantine Fault Tolerant
Token            SUI (native on Sui)
```

### Infrastructure
```
Backend Hosting  Render (Docker)
Frontend Hosting Vercel (React SPA)
Database         PostgreSQL (production)
CI/CD            GitHub Actions
Monitoring       Sentry (errors), custom logging
```

---

## Architecture

### System Overview

```
┌────────────────────────────────────────────────────────┐
│ USER BROWSER                                           │
│ ┌──────────────────────────────────────────────────┐   │
│ │ React dApp (Vite)                                │   │
│ │ • Voice upload & registration                    │   │
│ │ • Marketplace browse                             │   │
│ │ • Payment flows (HTTP 402)                       │   │
│ │ • Agent deployment                               │   │
│ │ • Sui wallet integration                         │   │
│ └──────────────────────────────────────────────────┘   │
│                     ▲  ▲  ▲                             │
└─────────┬──────────┼──┼──┼──────────────────────────────┘
          │ HTTP/REST│  │  │
          │          │  │  │
          ▼          ▼  ▼  ▼
   ┌──────────────┐ ┌──────────┐ ┌──────────┐
   │ FastAPI      │ │ Sui      │ │ Walrus   │
   │ Backend      │ │ Testnet  │ │ Storage  │
   │ :3000        │ │          │ │ Aggreg.  │
   └──────────────┘ └──────────┘ └──────────┘
        ▲               ▲
        │               │
        ▼               ▼
    ┌─────────────┐ ┌────────────┐
    │ Audio       │ │ Move Smart │
    │ Processing  │ │ Contracts  │
    │ • FFmpeg    │ │ • voice_id │
    │ • Embedding │ │ • payment  │
    └─────────────┘ └────────────┘
```

### Data Flow: Voice Registration to Usage

```
1️⃣ CREATOR: Upload Voice
   Audio → Backend → FFmpeg normalize → Generate embedding
   ↓
   Upload to Walrus → Get walrusUri
   ↓
   Mint VoiceIdentity NFT on Sui
   ↓
   ✅ Voice is now registered

2️⃣ BRAND: Browse Marketplace
   Search voices → Filter by language/price
   ↓
   Select voice, view preview audio

3️⃣ BRAND: Pay for Voice Access
   Call /api/tts/generate
   ↓
   ❌ No license? Return HTTP 402
   ↓
   Brand pays via Sui wallet
   ↓
   Smart contract splits payment:
     • Platform: 2.5%
     • Royalty: 10%
     • Creator: 87.5%
   ↓
   Mints LicensePass NFT to brand

4️⃣ BRAND: Use Voice
   Retry /api/tts/generate with payment proof
   ↓
   Backend verifies LicensePass ownership
   ↓
   ✅ Access granted, generate TTS audio
   ↓
   Return audio/wav blob
```

---

## Getting Started

### Prerequisites

- **Node.js** 18+ (frontend)
- **Python** 3.11+ (backend)
- **Sui Wallet** (testnet account with faucet funds)
- **Git**
- **FFmpeg** (for audio processing)

### Local Development Setup

#### 1. Clone Repository

```bash
git clone https://github.com/yourusername/swaraos.git
cd swaraos
```

#### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
PORT=3000
SUI_RPC_URL=https://fullnode.testnet.sui.io
SUI_NETWORK=testnet
SUI_ADDRESS=0x...          # Your Sui address
SUI_PACKAGE_ID=0x1ad12f0fd...  # Voice contract package ID
WALRUS_STORAGE_MODE=local
WALRUS_EPOCHS=5
EOF

# Start backend
python -m uvicorn server:app --reload --port 3000
```

**Backend runs on**: `http://localhost:3000`

#### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env file
cat > .env.local << EOF
VITE_API_URL=http://localhost:3000
VITE_PROXY_URL=http://localhost:3000
EOF

# Start dev server
npm run dev
```

**Frontend runs on**: `http://localhost:5173`

#### 4. Connect Sui Wallet

1. Install **Sui Wallet** browser extension: https://chromewebstore.google.com/detail/sui-wallet/oimhfgjfgcxeenfjokqfmkfcfhhjofol
2. Create account on **Sui Testnet**
3. Request testnet faucet: https://faucet.testnet.sui.io
4. In app, click "Connect Wallet" and approve

#### 5. Test Voice Upload

1. Go to **Upload** page
2. Select an audio file (MP3, WAV, M4A, OGG)
3. Enter voice name, description, rights, price per use
4. Click "Process Voice" → Backend normalizes, generates embedding, uploads to Walrus
5. Click "Register Voice" → Approve Sui wallet transaction
6. ✅ Voice registered on-chain!

---

## Deployment

### Backend: Render (Docker)

#### 1. Prepare Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Copy & install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY backend/ .

# Expose port
EXPOSE 8080

# Run server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
```

#### 2. Create Render Service

1. Sign up: https://render.com
2. New → Web Service
3. Connect GitHub repository
4. Set environment variables:
   ```
   PORT=8080
   SUI_RPC_URL=https://fullnode.testnet.sui.io
   SUI_PACKAGE_ID=0x1ad12f0fd...
   WALRUS_STORAGE_MODE=remote
   WALRUS_PUBLISHER_URL=https://publisher.walrus-testnet.walrus.space
   ```
5. Deploy!

**Backend URL**: `https://voicevault-backend.onrender.com`

### Frontend: Vercel

#### 1. Create Vercel Project

1. Sign up: https://vercel.com
2. Import GitHub repository
3. Set environment variables:
   ```
   VITE_API_URL=https://voicevault-backend.onrender.com
   VITE_PROXY_URL=https://voicevault-backend.onrender.com
   ```
4. Deploy!

**Frontend URL**: `https://voicevault.vercel.app`

---

## How It Works

### Voice Registration Deep Dive

#### Step 1: Audio Upload & Processing (Backend)

```
User uploads MP3 file (5MB)
  ↓
Backend: voice_model.normalize_audio()
  • FFmpeg: Convert to 16kHz mono WAV
  • Remove silence, normalize volume
  • Output: ~1.5MB WAV
  ↓
Backend: voice_model.generate_embedding()
  • Extract voice fingerprint (SHA256-based)
  • Create 256-dimensional float32 vector
  • Output: embedding.bin (1KB)
  ↓
Backend: voice_model.create_voice_bundle()
  • Collect files:
    - embedding.bin (fingerprint)
    - config.json (format metadata)
    - meta.json (creator info, price, rights)
    - preview.wav (first 5 sec)
  ↓
Backend: walrus.upload_files()
  • For each file:
    - Compute blob_id = SHA256(file_data)
    - Store blob (local or Walrus aggregator)
    - Save metadata
  ↓
Backend: walrus.create_manifest()
  • Bundle all blobs into manifest JSON
  • Upload manifest as blob
  • Get manifest_blob_id
  • Return walrusUri = "walrus://manifest_blob_id"
  ↓
✅ Response:
{
  "walrusUri": "walrus://7K5CW48xk9owzXZMqsMmur77ZAMWZDxYDfZYbcziyZk",
  "previewUrl": "http://localhost:3000/api/walrus/blobs/...",
  "blobs": {
    "embedding.bin": {...},
    "config.json": {...},
    "meta.json": {...},
    "preview.wav": {...}
  }
}
```

#### Step 2: On-Chain Registration (Blockchain)

```
Frontend: User approves registration
  ↓
Create Move transaction:
  tx.moveCall({
    target: "0x1ad12.../voice_identity::register_voice",
    arguments: [
      "My Voice",
      "walrus://7K5CW48xk9...",
      "Commercial",
      1_000_000  // 0.001 SUI in MIST
    ]
  })
  ↓
User signs in Sui Wallet
  ↓
Sui validator executes transaction:
  ├─ Creates VoiceIdentity NFT struct
  ├─ Sets owner = requester_account
  ├─ Stores model_uri, name, rights, price_per_use
  ├─ Appends owner to global VoiceRegistry
  └─ Returns VoiceIdentity object ID
  ↓
✅ Transaction confirmed (2-3 seconds)
```

#### Step 3: Voice Available on Marketplace

```
Frontend fetches all voices from VoiceRegistry
  ↓
For each VoiceIdentity:
  • Download metadata from Walrus
  • Fetch preview audio
  • Display in marketplace
  ↓
Users can:
  ✅ Browse voices
  ✅ Search by name/description
  ✅ Filter by language, price, rights
  ✅ Listen to preview
```

---

### Payment & License Deep Dive

#### Step 1: User Requests Voice

```
Brand calls: POST /api/tts/generate
{
  "modelUri": "walrus://7K5CW48xk9...",
  "text": "Hello, this is a test.",
  "requesterAccount": "0x..."
}
  ↓
Backend checks access:
  1. Is requester the voice owner?
     ✅ YES → Grant access
  2. Does requester have LicensePass (purchased)?
     ✅ YES → Grant access
  3. Does requester have UsagePass (x402)?
     ✅ YES → Grant access
  4. Fresh x402 payment proof?
     ✅ YES → Grant access
  ↓
❌ None of above?
  Return HTTP 402 Payment Required
```

#### Step 2: 402 Payment Response

```
HTTP 402 Payment Required
{
  "x402Version": 1,
  "error": "Payment Required",
  "accepts": [
    {
      "scheme": "exact",
      "network": "sui-testnet",
      "maxAmountRequired": "10000000",    // 0.01 SUI in MIST
      "resource": "/api/tts/generate",
      "description": "Pay 0.01 SUI for 2 uses",
      "payTo": "0x..." (creator),
      "extra": {
        "voice_id": "0x7f...",
        "uses": 2,
        "expires_in_hours": 24
      }
    }
  ]
}
  ↓
Frontend displays:
  "This voice requires payment: 0.01 SUI for 2 uses"
  ↓
User clicks "Pay & Use Voice"
```

#### Step 3: Payment Transaction

```
Frontend: Create Move transaction
  tx.moveCall({
    target: "0x1ad12.../payment::pay_with_royalty_split",
    arguments: [
      payment_coin (0.01 SUI),
      voice_id,
      creator_address,
      platform_address,
      royalty_recipient
    ]
  })
  ↓
User signs in Sui Wallet
  ↓
Sui validator executes:
  ├─ Calculate splits:
  │  ├─ Platform fee: 0.01 * 2.5% = 0.00025 SUI
  │  ├─ Royalty: (0.01 - 0.00025) * 10% = 0.0000975 SUI
  │  └─ Creator: 0.01 - 0.00025 - 0.0000975 = 0.0096525 SUI
  ├─ Transfer payments:
  │  ├─ Platform: 250,000 MIST
  │  ├─ Royalty recipient: 97,500 MIST
  │  └─ Creator: 9,652,500 MIST
  ├─ Mint LicensePass NFT (proof of purchase)
  ├─ Transfer LicensePass to buyer
  └─ Emit events for indexing
  ↓
✅ Transaction confirmed (2-3 seconds)
```

#### Step 4: Access Granted

```
Frontend: Retry POST /api/tts/generate
  Add header: X-Payment-Proof: [tx_digest]
  ↓
Backend: Verify Sui payment
  ├─ Query Sui RPC: Get transaction details
  ├─ Verify:
  │  ├─ Payer = requesterAccount
  │  ├─ Recipient = creator
  │  └─ Amount ≥ min_required
  ├─ Check replay protection (digest not used before)
  └─ Create UsagePass (2 uses, 24hr expiry)
  ↓
Backend: Generate TTS audio
  ├─ Download voice model from Walrus
  ├─ Download preview audio
  ├─ Use for text-to-speech
  ├─ Consume 1 use from UsagePass
  └─ Return audio/wav
  ↓
✅ User receives audio!
```

---

## Use Cases

### 1. **Voice Actor / Singer**

> "I want to monetize my voice without exclusive deals."

**Flow**:
1. Record high-quality audio sample
2. Upload to SwaraOS → Mint Voice NFT
3. Set price per use: 0.01 SUI
4. List on marketplace
5. Every time brand uses voice → Earn SUI automatically
6. Track earnings on dashboard

**Benefits**:
- Own your voice NFT (provable on-chain)
- Non-exclusive (license to unlimited brands)
- Earn from any number of use cases
- No intermediary taking cuts

---

### 2. **AI Customer Support Company**

> "We deploy 100+ support bots. We need diverse voices."

**Flow**:
1. Browse SwaraOS marketplace → Find 10 diverse voices
2. Pay per use via HTTP 402 (small usage = small cost)
3. Deploy bots with diverse voices immediately
4. No licensing lawyer needed
5. Creators get paid automatically

**Benefits**:
- Instant access to diverse voices
- Pay only for what you use
- Transparent, standardized licensing
- Support creators directly

---

### 3. **Podcast / Audiobook Publisher**

> "We want diverse narrators without hiring overhead."

**Flow**:
1. Commission voice actor to record character voice
2. Voice actor mints Voice NFT on SwaraOS
3. Publisher licenses voice exclusively (license type: "exclusive")
4. Publisher uses voice for entire audiobook series
5. Both earn (publisher via audiobook sales, narrator via license)

**Benefits**:
- On-chain proof of licensing
- Automatic royalty splits
- Transparent audit trail
- Fair market pricing

---

### 4. **Indie Game Developer**

> "We need AI characters with realistic voices."

**Flow**:
1. Use Sarvam AI to generate character voice descriptions
2. Search SwaraOS marketplace → Find voices matching character
3. Buy license for voice
4. Integrate via API (HTTP 402 for each use)
5. Game characters speak with diverse, natural voices

**Benefits**:
- Discover voices programmatically
- Pay-per-use (indie budgets)
- Creators get attribution + payment
- No licensing friction

---

## Roadmap

### Phase 1: MVP (Current)
- ✅ Voice registration & NFT minting
- ✅ Decentralized marketplace
- ✅ HTTP 402 pay-per-use licensing
- ✅ Smart contract royalty distribution
- ✅ Basic voice agents

### Phase 2: Scalability (Q3 2024)
- PostgreSQL database (replace JSON store)
- Async audio processing queue
- Real ML embeddings (Resemblyzer/GE2E)
- Voice similarity search
- Signed message authentication

### Phase 3: Advanced Features (Q4 2024)
- Creator analytics dashboard
- Voice marketplace filters (advanced)
- Automated royalty payouts
- Privacy-preserving licenses (ZK proofs)
- Voice agent marketplace

### Phase 4: Mainnet (Q1 2025)
- Sui mainnet deployment
- Security audit + pen test
- GDPR compliance framework
- Enterprise licensing terms
- Multi-chain support (Polygon, etc.)

### Phase 5: Ecosystem (Q2 2025+)
- Voice dubbing service (auto-translate voices)
- Voice authentication (anti-spoofing)
- Creator fund / grants
- Voice derivatives (mixing, effects)
- Cross-chain voice transfers

---

## Contributing

We welcome contributions from developers, designers, and community members!

### How to Contribute

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open Pull Request**

### Development Guidelines

- **Frontend**: Follow React/TypeScript conventions, use Tailwind CSS
- **Backend**: Follow PEP 8, add docstrings, write tests
- **Smart Contracts**: Use Move best practices, add comments
- **Git**: Use descriptive commit messages

### Reporting Issues

Found a bug? Open an issue with:
- Clear description
- Steps to reproduce
- Expected vs. actual behavior
- Screenshots (if UI issue)

---

## Security & Legal

### Security Considerations

- **Audio Privacy**: Preview audio stored publicly; full audio requires license
- **Voice Fingerprints**: Embeddings are content-addressed; can't be reversed
- **Payment Verification**: All transactions verified on-chain
- **Replay Protection**: Used payment digests tracked (prevent double-use)

### Disclaimer

- SwaraOS is provided as-is for voice ownership and licensing
- Users are responsible for licensing rights to audio they upload
- Creators must own rights to voices they register
- Platform not liable for misuse of voices

### GDPR & Privacy

- User data handled per GDPR requirements
- Voice cloning data stored in Walrus (decentralized, CPAL license)
- Users can request data deletion (within blockchain limits)

---

## License

This project is licensed under the **Apache 2.0 License** — see [LICENSE](./LICENSE) file for details.

**Smart Contracts** (Move): Licensed under **CPAL 1.0** (standard for Sui)

---

## Support & Community

### Links

- **Website**: https://swaraos.io (coming soon)
- **GitHub**: https://github.com/yourusername/swaraos
- **Discord**: https://discord.gg/swaraos (coming soon)
- **Twitter**: @SwaraOS
- **Docs**: https://docs.swaraos.io

### Get Help

- **Technical Questions**: GitHub Discussions
- **Bug Reports**: GitHub Issues
- **Feature Requests**: GitHub Discussions
- **General Help**: Discord community

---

## Acknowledgments

Built with:
- **Sui Foundation** for blockchain infrastructure
- **Walrus Protocol** for decentralized storage
- **LiveKit** for real-time voice agents
- **Sarvam AI** for STT/TTS in Indian languages
- Community contributors and supporters

---

**Made with ❤️ by the SwaraOS team**

**Join us in decentralizing voice ownership. Own Your Voice. Earn Forever.**
