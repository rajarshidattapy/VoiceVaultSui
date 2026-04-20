# VoiceVault Sui - Comprehensive Technical Overview

## Executive Summary

**VoiceVault** is a decentralized Web3 platform bridging AI voice technology with blockchain (Sui) to create a marketplace for voice ownership, licensing, and monetization. It combines:

- **Sui Blockchain**: Smart contracts for voice ownership, rights management, and payment distribution
- **Walrus Storage**: Content-addressed decentralized blob storage for voice models and metadata
- **AI Voice Technology**: Voice model generation, embeddings, and TTS via Chatterbox/Gradio
- **FastAPI Backend**: Orchestrates voice processing, Walrus integration, and payment calculations
- **React Frontend**: Web3 dApp for voice creation, registration, marketplace browsing, and licensing

**Core Value Proposition**: "Own Your Voice. Earn Forever." - Creators mint voice NFTs on-chain and earn SUI tokens automatically when users license their voices via smart contract payment splits.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  React Frontend (Vite + TypeScript)                      │   │
│  │  • Voice Upload & Registration                           │   │
│  │  • Marketplace Browse & Search                           │   │
│  │  • TTS Generation & Voice Cloning                        │   │
│  │  • Wallet Integration (Sui dApp Kit)                     │   │
│  │  • Dashboard & Analytics                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            ▲                                      │
│     ┌──────────────────────┼──────────────────────┐              │
│     │                      │                      │              │
└─────┼──────────────────────┼──────────────────────┼──────────────┘
      │ HTTP/REST            │ HTTP/REST            │
      │                      │                      │
      ▼                      ▼                      ▼
┌────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  FastAPI       │  │  Sui Blockchain  │  │  Walrus Storage  │
│  Backend       │  │  (Testnet)       │  │  (Aggregator)    │
│  :8000         │  │                  │  │                  │
├────────────────┤  ├──────────────────┤  ├──────────────────┤
│ • Voice        │  │ • Voice          │  │ • Blob Store     │
│   Processing   │  │   Identity       │  │   (content-addr) │
│ • Embedding    │  │ • Payment        │  │ • Manifest Refs  │
│   Generation   │  │   Distribution   │  │ • Access Control │
│ • Walrus Proxy │  │ • NFT Minting    │  │ • Free Reads     │
│ • TTS Bridge   │  │ • Access Rights  │  │                  │
└────────────────┘  └──────────────────┘  └──────────────────┘
      ▲                      ▲
      │ Internal             │ JSON-RPC
      │ Crypto Ops           │
      │                      │
  ┌───┴─────────────┐        └─────────────────┐
  │  FFmpeg         │                          │
  │  (audio norm)   │                    Sui CLI / SDK
  │                 │
  │  Gradio Client  │
  │  (Chatterbox    │
  │   TTS)          │
  └─────────────────┘
```

---

## 1. BACKEND CODE ANALYSIS

### 1.1 Server Architecture (`backend/server.py`)

**Framework**: FastAPI 0.115.0 with CORS middleware

**Key Endpoints**:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/tts/generate` | POST | Unified TTS generation (Walrus-backed voices or preview) |
| `/api/payment/breakdown` | POST | Calculate platform fee, royalty, and creator splits |
| `/api/voice/process` | POST | Process audio → generate embedding → upload to Walrus |
| `/api/walrus/upload` | POST | Direct Walrus bundle upload |
| `/api/walrus/download` | POST | Download file from Walrus manifest |
| `/api/walrus/delete` | POST | Delete Walrus blob (if deletable) |
| `/api/walrus/blobs/{blob_id}` | GET | Stream Walrus blob directly |

**TTS Generation Flow**:
```python
@app.post("/api/tts/generate")
├─ Input: modelUri (walrus://...), text, requesterAccount
├─ Verify Access Control:
│  └─ walrus_module.verify_walrus_access(modelUri, requesterAccount)
├─ Download Voice Files from Walrus:
│  ├─ embedding.bin (voice characteristics)
│  ├─ config.json (model metadata)
│  └─ preview.wav (sample audio)
├─ Return Preview Audio (or error)
└─ Output: audio/wav Blob
```

**Payment Breakdown Calculation**:
```python
Amount → 100 MIST (example)
├─ Platform Fee (2.5%): 2.5 MIST
├─ Remaining: 97.5 MIST
├─ Royalty (10% of remaining): 9.75 MIST
└─ Creator Gets: 87.75 MIST

Fee Structure Constants:
- PLATFORM_FEE_BPS = 250 (2.5%)
- ROYALTY_BPS = 1000 (10%)
```

**Dependencies**:
- FastAPI, Uvicorn (async API server)
- httpx (async HTTP client for Walrus API calls)
- python-dotenv (environment configuration)
- python-multipart (form data handling)

---

### 1.2 Voice Model Processing (`backend/voice_model.py`)

**Purpose**: Convert raw audio → voice model bundle

**Pipeline**:

```
Raw Audio (WAV/MP3/etc)
    ▼
1. AUDIO NORMALIZATION (normalize_audio)
   ├─ Uses FFmpeg: Convert → 16kHz, mono, WAV
   ├─ Fallback: Pass-through if FFmpeg unavailable
   └─ Output: Normalized WAV bytes
    ▼
2. EMBEDDING GENERATION (generate_embedding)
   ├─ Input: Normalized audio
   ├─ Process: Extract voice characteristics
   │   (Placeholder: hash-based demo; production = trained ML model)
   ├─ Output: 256-dim float32 vector
   └─ Note: In production, use:
   │   • Resemblyzer (voice similarity)
   │   • GE2E (speaker encoding)
   │   • Other speaker verification models
    ▼
3. BUNDLE CREATION (create_voice_bundle)
   ├─ Files Generated:
   │   ├─ embedding.bin (float32 array)
   │   ├─ config.json (model metadata)
   │   ├─ meta.json (creator info, timestamps)
   │   └─ preview.wav (first 5 seconds)
   ├─ config.json Content:
   │   {
   │     "modelVersion": "1.0.0",
   │     "sampleRate": 16000,
   │     "channels": 1,
   │     "format": "wav",
   │     "embeddingSize": 256,
   │     "embeddingFormat": "float32"
   │   }
   ├─ meta.json Content:
   │   {
   │     "name": "Creator's Voice",
   │     "description": "...",
   │     "owner": "0x...",
   │     "voiceId": "voice-123",
   │     "createdAt": 1713607891000,
   │     "modelVersion": "1.0.0"
   │   }
   └─ Output: Bundled files dict
```

**Key Functions**:

```python
normalize_audio(audio_buffer, mime_type) → bytes
└─ Standardizes audio format using FFmpeg

generate_embedding(normalized_audio) → Dict
└─ Creates voice fingerprint (256-dim vector)

create_voice_bundle(...) → Dict
└─ Packages embedding, config, meta, preview

process_voice_model(...) → Dict
└─ Main orchestration function (steps 1-3 above)
```

---

### 1.3 Walrus Storage Integration (`backend/walrus.py`)

**Overview**: Manages content-addressed blob storage with dual modes: local (dev) and remote (production)

**Storage Architecture**:

```
STORAGE_ROOT = backend/storage/walrus/
├── blobs/
│   ├── {blob_id_1}.bin          (raw binary data, SHA256-addressed)
│   ├── {blob_id_2}.bin
│   └── ...
└── meta/
    ├── {blob_id_1}.json         (metadata about each blob)
    ├── {blob_id_2}.json
    └── ...

META FORMAT:
{
  "blobId": "base64_sha256_hash",
  "objectId": "0xhex_object_id",
  "size": 12345,
  "isManifest": false,
  "storedAt": 1713607891000
}
```

**Key Concepts**:

1. **Content Addressing** (`_blob_id_for`):
   ```
   Blob Data → SHA256 Hash → Base64 Encode → Blob ID
   Same content = Same ID (automatic deduplication)
   walrus://blob_id_here ← Format
   ```

2. **Manifest Pattern** (solves multiple files):
   ```json
   {
     "voiceId": "voice-123",
     "owner": "0xabc...",
     "blobs": {
       "embedding.bin": {
         "blobId": "...",
         "objectId": "...",
         "size": 1024
       },
       "config.json": { ... },
       "meta.json": { ... },
       "preview.wav": { ... }
     },
     "walrusUri": "walrus://manifest_blob_id",
     "version": 1
   }
   ```

**Upload Flow** (`upload_to_walrus`):

```
Bundle Files (embedding.bin, config.json, meta.json, preview.wav)
    ▼
FOR EACH FILE:
├─ Store file blob (local or remote)
├─ Get blob_id & object_id
└─ Create blob reference entry
    ▼
CREATE MANIFEST JSON:
├─ Aggregates all blob references
├─ Maps filename → {blobId, objectId, size, chunked}
└─ Sets voice ownership & URI
    ▼
STORE MANIFEST BLOB:
├─ Serialize manifest to JSON bytes
├─ Store as blob (get manifest_blob_id)
└─ walrusUri = "walrus://{manifest_blob_id}"
    ▼
RETURN MANIFEST:
{
  "walrusUri": "walrus://...",
  "manifestBlobId": "...",
  "blobs": {...},
  "previewUrl": "http://aggregator/v1/blobs/...",
  "size": 1024000
}
```

**Download Flow** (`download_file`):

```
Input: manifestBlobId, filename
    ▼
Load Manifest: manifest_bytes = download_from_walrus(manifestBlobId)
    ▼
Parse JSON: manifest = json.loads(manifest_bytes)
    ▼
Find Blob Reference: blob_ref = manifest["blobs"][filename]
    ▼
Download Blob Reference:
├─ IF chunked:
│  └─ Concatenate multiple blobs
└─ ELSE:
   └─ Download single blob
    ▼
Output: file bytes
```

**Remote Mode** (`_upload_remote_blob` / `_download_remote_blob`):

```
Testnet:
- PUBLISHER_URL: https://publisher.walrus-testnet.walrus.space/v1/blobs
- AGGREGATOR_URL: https://aggregator.walrus-testnet.walrus.space/v1/blobs
  (or custom: http://localhost:8000/api/walrus)

HTTP Requests:
- PUT /v1/blobs?epochs=5 → Upload (returns blob_id, object_id)
- GET /v1/blobs/{blob_id} → Download (free read via Aggregator)
```

**Local Mode** (development):

```
_write_local_blob: Writes to backend/storage/walrus/blobs/
_read_local_blob: Reads from local filesystem
_delete_local_blob: Removes local files

Preserves Walrus content-addressing semantics
```

**Key Functions**:

```python
upload_to_walrus(owner_address, voice_id, bundle_files) → Dict
└─ Orchestrates full upload, returns manifest with walrusUri

download_from_walrus(blob_id) → bytes
└─ Retrieves blob (local or remote)

download_file(manifest_blob_id, filename) → bytes
└─ Gets specific file from manifest

load_manifest(manifest_blob_id) → Dict
└─ Deserializes manifest JSON

verify_walrus_access(uri, requester_account) → bool
└─ Placeholder access control (currently permissive)

build_walrus_uri(blob_id) → str
└─ Creates walrus:// URI

parse_walrus_uri(uri) → str
└─ Extracts blob_id from URI
```

---

### 1.4 Compatibility Layer (`backend/shelby.py`)

**Context**: VoiceVault migrated from Shelby (Aptos-based storage) to Walrus (Sui-native)

**Purpose**: Backward compatibility aliases

```python
# Old Shelby API → New Walrus API
verify_shelby_access = verify_walrus_access
delete_from_shelby = delete_from_walrus
download_from_shelby = download_from_walrus
upload_to_shelby = upload_to_walrus
```

**Migration Notes**:
- Walrus eliminates Aptos dependency (single-chain on Sui)
- Free reads via public Aggregators (no micropayment sessions)
- Content-addressed blob IDs (immutable by definition)
- Backward-compatible via this shim layer

---

## 2. FRONTEND STRUCTURE & COMPONENTS

### 2.1 Technology Stack

```json
{
  "core": {
    "React": "18.3.1",
    "TypeScript": "latest",
    "Vite": "bundler",
    "React Router": "6.30.1"
  },
  "blockchain": {
    "@mysten/sui": "2.13.0",
    "@mysten/dapp-kit": "1.0.4"
  },
  "ui": {
    "Tailwind CSS": "with postcss",
    "Shadcn/ui": "Radix UI based",
    "Lucide React": "icons",
    "Recharts": "charting"
  },
  "forms": {
    "React Hook Form": "7.61.1",
    "Zod": "3.25.76",
    "@hookform/resolvers": "3.10.0"
  },
  "state": {
    "@tanstack/react-query": "5.95.2",
    "React Context": "custom hooks"
  },
  "utils": {
    "Axios": "HTTP client (optional)",
    "Sonner": "toast notifications",
    "Date-fns": "date manipulation"
  }
}
```

### 2.2 Directory Structure

```
frontend/src/
├── components/
│   ├── dashboard/           (Creator dashboard, analytics)
│   ├── marketplace/         (Browse, search voices)
│   ├── upload/              (Voice registration form)
│   ├── voice/               (Voice preview, player)
│   ├── wallet/              (Wallet connect, balance)
│   ├── layout/              (Nav, header, footer)
│   ├── landing/             (Hero, features)
│   └── ui/                  (Shadcn components)
├── contexts/
│   └── WalletContext.tsx   (Sui wallet provider setup)
├── hooks/
│   ├── useSuiWallet.ts             (Wallet state)
│   ├── useVoiceRegister.ts         (On-chain registration)
│   ├── usePayForInference.ts       (Payment execution)
│   ├── useVoiceMetadata.ts         (Fetch voice objects)
│   ├── useVoicesWithWalrusMetadata.ts (Voices + Walrus blobs)
│   ├── useMultipleVoiceMetadata.ts (Batch fetch)
│   ├── useVoiceUnregister.ts       (Delete voice object)
│   └── (more hooks)
├── lib/
│   ├── api.ts              (Backend REST client)
│   ├── contracts.ts        (Sui Move contract constants)
│   ├── sui.ts              (Sui client setup)
│   ├── walrus.ts           (Walrus blob client)
│   ├── voiceRegistry.ts    (localStorage registry)
│   ├── chatterbox.ts       (Gradio TTS client)
│   ├── moveUtils.ts        (Move data parsing)
│   ├── utils.ts            (cn() helper)
│   ├── clonedVoices.ts     (Local voice state)
│   └── purchasedVoices.ts  (Owned voices tracking)
├── pages/
│   ├── Index.tsx           (Landing)
│   ├── Dashboard.tsx       (Creator dashboard)
│   ├── Upload.tsx          (Voice upload)
│   ├── Marketplace.tsx     (Browse voices)
│   ├── Deploy.tsx          (Contract deployment)
│   └── Docs.tsx            (Documentation)
├── App.tsx                 (Router + providers)
├── main.tsx                (Entry point)
└── index.css               (Global styles)
```

---

### 2.3 Core Libraries & Modules

#### `lib/sui.ts` - Sui Client Setup
```typescript
export const suiClient = new SuiJsonRpcClient({
  url: getJsonRpcFullnodeUrl('testnet'),
  network: 'testnet',
});

export const formatAddress = (address: string) => 
  `${address.slice(0, 6)}...${address.slice(-4)}`;

export const getAccountBalance = async (address: string): Promise<number>
  // Returns balance in SUI (converts from MIST)
```

#### `contexts/WalletContext.tsx` - Web3 Provider
```typescript
NetworkConfig:
  - testnet: fullnode.testnet.sui.io
  - mainnet: fullnode.sui.io

Providers:
  - QueryClientProvider (TanStack React Query)
  - SuiClientProvider
  - SuiWalletProvider (auto-connect from localStorage)

Enables:
  - useCurrentAccount() → current wallet
  - useSuiClient() → RPC calls
  - useSignAndExecuteTransaction() → sign & submit txs
```

#### `lib/contracts.ts` - Move Contract Interface
```typescript
CONTRACTS = {
  PACKAGE_ID: "0x1ad12f0fd581dbd4fef7a30c9cff9bececfca1da450fe53257791502b3db073d",
  VOICE_IDENTITY: { module: "voice_identity" },
  PAYMENT: { module: "payment" },
  PLATFORM_ADDRESS: "0x00fe9f516cc03adabcb1c521ecb82f9d2c5c9a42102b5e9895939b63d098df70"
}

FEE_STRUCTURE = {
  PLATFORM_FEE_BPS: 250,    // 2.5%
  ROYALTY_BPS: 1000         // 10%
}

Helpers:
- calculatePaymentBreakdown(amount)
- suiToMist(sui) → 1 SUI = 1e9 MIST
- mistToSui(mist)
```

#### `lib/walrus.ts` - Walrus Blob Client
```typescript
Core Functions:
- parseWalrusUri(uri) → blob_id
- buildWalrusUri(blob_id) → "walrus://..."
- getBlobUrl(blob_id) → HTTP URL
- fetchBlob(blob_id) → ArrayBuffer
- fetchManifest(manifestBlobId) → VoiceManifest JSON
- fetchWalrusFile(uri, filename) → ArrayBuffer
- getPreviewUrl(manifest) → URL to preview.wav

Data Structures:
- WalrusBlobRef: {blobId, objectId, size, chunked, blobIds}
- VoiceManifest: {voiceId, owner, blobs: {[filename]: WalrusBlobRef}}
```

#### `lib/api.ts` - Backend REST Client
```typescript
BACKEND_CONFIG = {
  BASE_URL: "http://localhost:3000" (configurable)
  ENDPOINTS: {
    UNIFIED_TTS: "/api/tts/generate",
    PAYMENT_BREAKDOWN: "/api/payment/breakdown",
    VOICE_PROCESS: "/api/voice/process",
    WALRUS_UPLOAD: "/api/walrus/upload",
    WALRUS_DOWNLOAD: "/api/walrus/download",
    WALRUS_DELETE: "/api/walrus/delete"
  }
}

backendApi Methods:
- generateTTS(modelUri, text, requesterAccount) → Blob
- getPaymentBreakdown(amount) → {platformFee, royalty, creator}
- processVoiceModel(audioFile, name, owner, voiceId) → manifest
- uploadToWalrus(account, voiceId, bundleFiles) → uploadResult
- downloadFromWalrus(uri, filename, requesterAccount) → ArrayBuffer
- deleteFromWalrus(uri, account) → {success, message}
```

---

### 2.4 Custom Hooks

#### `useVoiceRegister` - Register Voice On-Chain
```typescript
// Calls voice_identity::register_voice Move function
const { registerVoice, isRegistering } = useVoiceRegister();

registerVoice({
  name: "My Voice",
  modelUri: "walrus://blob_id",
  rights: "Commercial",
  pricePerUse: 0.001  // SUI
}) → { success, transactionHash }

Steps:
1. Create Transaction
2. Call Move function with arguments
3. Sign via wallet
4. Wait for confirmation
5. Return tx digest
```

#### `usePayForInference` - Pay Creator with Royalty Split
```typescript
// Calls payment::pay_with_royalty_split Move function
const { payForInference, isPaying } = usePayForInference();

payForInference({
  creatorAddress: "0x...",
  amount: 0.1,              // SUI
  royaltyRecipient: "0x..." // Optional
}) → { success, transactionHash }

On-Chain Fee Split:
- Input: 0.1 SUI (100 MIST)
- Platform Fee (2.5%): 2.5 MIST → PLATFORM_ADDRESS
- Royalty (10% of remaining): 9.75 MIST → royaltyRecipient
- Creator Receives: 87.75 MIST → creatorAddress
```

#### `useVoiceMetadata` - Fetch Single Voice Object
```typescript
// Query Sui objects by owner
const { metadata, isLoading, error } = useVoiceMetadata(ownerAddress);

Returns:
{
  owner: "0x...",
  voiceId: "voice-123",
  objectId: "0xabc...",  // Sui object ID
  name: "My Voice",
  modelUri: "walrus://...",
  rights: "Commercial",
  pricePerUse: 0.001,
  createdAt: 1713607891000
}

Implementation:
- suiClient.getOwnedObjects({owner, filter: {StructType: VOICE_TYPE}})
- Parse Move object fields
- Convert MIST → SUI
```

#### `useVoicesWithWalrusMetadata` - Voices + Storage Metadata
```typescript
// Fetch voices AND enrich with Walrus blob data
const { voices, isLoading, error } = useVoicesWithWalrusMetadata(addresses);

Process:
1. For each address, fetch on-chain VoiceIdentity object
2. For each voice with walrus:// URI:
   - Load manifest from Walrus
   - Fetch meta.json (name, description)
   - Create preview audio URL from preview.wav blob
3. Merge on-chain + off-chain data

Output: VoiceWithWalrusMetadata[]
{
  ...VoiceMetadata,
  description?: string,
  previewAudioUrl?: string,
  storageProtocol: "walrus" | "unknown"
}
```

#### Other Key Hooks

```typescript
useSuiWallet() → {
  isConnected, address, account, suiClient
}

useVoiceMetadata(address) → {
  metadata, isLoading, error
}

useMultipleVoiceMetadata(addresses) → {
  voices[], isLoading, error
}

useVoiceUnregister() → {
  unregisterVoice(voiceId), isUnregistering
}
```

---

### 2.5 Local Storage & State Management

#### `lib/voiceRegistry.ts` - localStorage Voice Registry
```typescript
// Track registered voices in browser
getRegisteredVoices() → VoiceRegistryEntry[]
addVoiceToRegistry(address, name)
removeVoiceFromRegistry(address)
getVoiceAddresses() → string[]

Purpose: Quick access to marketplace voice list
Storage Key: "voicevault_voice_registry"
```

#### `lib/clonedVoices.ts` - Local Cloned Voice State
```typescript
getClonedVoices() → ClonedVoice[]
addClonedVoice(voice)
removeClonedVoice(voiceId)
clearClonedVoices()

Structure:
{
  voiceId: string,
  name: string,
  audioFile?: File,
  previewUrl?: string
}
```

#### `lib/purchasedVoices.ts` - User's Licensed Voices
```typescript
Track voices user has purchased/licensed
Used for marketplace licensing flow
```

---

## 3. SMART CONTRACTS (Move)

### 3.1 Voice Identity Module

**Location**: `voice_vault_sui/sources/voice_identity.move`

**Purpose**: Represents voice ownership and metadata on-chain

```move
public struct VoiceIdentity has key, store {
  id: UID,                    // Unique identifier
  owner: address,             // Creator's Sui address
  name: String,               // "John Doe's Voice"
  model_uri: String,          // walrus://blob_id (Walrus manifest)
  rights: String,             // "Commercial" | "Personal"
  price_per_use: u64,         // Cost in MIST (1 SUI = 1e9 MIST)
  created_at: u64             // Timestamp
}
```

**Functions**:

```move
public fun register_voice(
  name: String,
  model_uri: String,
  rights: String,
  price_per_use: u64,
  ctx: &mut TxContext
) → VoiceIdentity
// Creates and returns new VoiceIdentity object
// Caller becomes owner

public fun delete_voice(voice: VoiceIdentity, ctx: &mut TxContext)
// Destroys voice object (burn it)
// Only owner can call

public fun get_metadata(voice: &VoiceIdentity)
  → (address, String, String, String, u64, u64)
// Returns: (owner, name, model_uri, rights, price_per_use, created_at)

public fun get_voice_id(voice: &VoiceIdentity) → ID
// Returns object's ID (for lookups)
```

**On-Chain Data Flow**:

```
User Calls: useVoiceRegister.registerVoice({
  name: "My Voice",
  modelUri: "walrus://abc123...",
  rights: "Commercial",
  pricePerUse: 1000000  // 0.001 SUI in MIST
})
  ▼
Frontend Creates Transaction:
  tx.moveCall({
    target: "0x1ad12.../voice_identity::register_voice",
    arguments: [
      tx.pure.string("My Voice"),
      tx.pure.string("walrus://abc123..."),
      tx.pure.string("Commercial"),
      tx.pure.u64(1000000)
    ]
  })
  ▼
Sui Blockchain Executes:
  1. Creates VoiceIdentity object
  2. Sets owner = tx_context::sender()
  3. Stores on-chain
  ▼
Object Created:
  ID: 0x7f5a...
  Owner: 0xuser...
  Transferable: Yes (can be sent to marketplace, staked, etc.)
```

---

### 3.2 Payment Module

**Location**: `voice_vault_sui/sources/payment.move`

**Purpose**: Handles payment splits with automatic fee & royalty distribution

```move
// Fee structure constants
const PLATFORM_FEE_BPS: u64 = 250;      // 2.5% = 250 basis points
const ROYALTY_BPS: u64 = 1000;          // 10% = 1000 basis points
const DENOM: u64 = 10000;               // Basis point denominator

// Event definitions (emitted on-chain)
public struct PaymentReceived has copy, drop {
  from: address,
  to: address,
  amount: u64
}

public struct RoyaltyPaid has copy, drop {
  payer: address,
  recipient: address,
  amount: u64
}

public struct PlatformFeePaid has copy, drop {
  payer: address,
  platform: address,
  amount: u64
}
```

**Core Functions**:

```move
public fun pay_with_royalty_split<T>(
  mut payment: Coin<T>,
  creator: address,
  platform: address,
  royalty_recipient: address,
  ctx: &mut TxContext
)
// Splits payment into 3 transfers:
// 1. platform_fee → platform_address
// 2. royalty → royalty_recipient
// 3. remainder → creator
// 
// Example: 100 MIST input
// ├─ 2.5 MIST → Platform
// ├─ 9.75 MIST → Royalty Recipient
// └─ 87.75 MIST → Creator
// Emits events for all 3 transfers

public fun pay_full_to_creator<T>(
  payment: Coin<T>,
  creator: address,
  ctx: &mut TxContext
)
// Direct payment to creator (no splits)
// Used when no royalty involved
// Emits PaymentReceived event

public fun calculate_payment_breakdown(amount: u64)
  → (u64, u64, u64)
// Returns: (platform_fee, royalty, creator_amount)
// Pure function, no state mutation
// Used for UI calculation before on-chain execution
```

**Payment Flow**:

```
User wants to use voice that costs 1 SUI

Frontend:
  1. Calculate breakdown: calculatePaymentBreakdown(1_000_000_000)
     → (25_000_000 platform, 97_500_000 remaining, 9_750_000 royalty, 87_750_000 creator)
  2. Show user breakdown
  3. User approves in wallet

Transaction:
  const tx = new Transaction();
  const paymentCoin = coinWithBalance({ balance: BigInt(1_000_000_000) });
  
  tx.moveCall({
    target: "0x1ad12.../payment::pay_with_royalty_split",
    typeArguments: ["0x2::sui::SUI"],
    arguments: [
      paymentCoin,
      tx.pure.address(creator_address),
      tx.pure.address(platform_address),
      tx.pure.address(royalty_recipient)
    ]
  });

Blockchain Execution:
  1. Split coin: Take 25_000_000 MIST
  2. Transfer to platform
  3. Emit PlatformFeePaid event
  4. Take 9_750_000 MIST from remainder
  5. Transfer to royalty recipient
  6. Emit RoyaltyPaid event
  7. Transfer 87_750_000 MIST to creator
  8. Emit PaymentReceived event
  
Events on-chain:
  event::emit(PlatformFeePaid { payer: user, platform, amount: 25M })
  event::emit(RoyaltyPaid { payer: user, recipient, amount: 9.75M })
  event::emit(PaymentReceived { from: user, to: creator, amount: 87.75M })
```

---

### 3.3 Module Constants & Deployment

**Published Contract**:
```toml
# voice_vault_sui/Published.toml
[Move.Published]
package = "0x1ad12f0fd581dbd4fef7a30c9cff9bececfca1da450fe53257791502b3db073d"
digest = "..."
```

**Frontend Constants** (`lib/contracts.ts`):
```typescript
PACKAGE_ID: "0x1ad12f0fd581dbd4fef7a30c9cff9bececfca1da450fe53257791502b3db073d"
PLATFORM_ADDRESS: "0x00fe9f516cc03adabcb1c521ecb82f9d2c5c9a42102b5e9895939b63d098df70"
```

---

## 4. DATA FLOW & ARCHITECTURE

### 4.1 Voice Registration Flow (Full End-to-End)

```
┌─ PHASE 1: VOICE CREATION (Frontend Upload)
│
├─ User uploads audio file (Upload.tsx)
│  └─ Selects: name, description, rights, price_per_use
│
├─ Frontend calls: backendApi.processVoiceModel(audioFile, ...)
│  
│  BACKEND: server.py:/api/voice/process
│  ├─ Receive FormData (audio, name, description, owner, voiceId)
│  ├─ Call voice_model.process_voice_model()
│  │  ├─ normalize_audio() → 16kHz mono WAV (uses FFmpeg)
│  │  ├─ generate_embedding() → 256-dim float32 vector
│  │  └─ create_voice_bundle() → {embedding.bin, config.json, meta.json, preview.wav}
│  ├─ Call walrus_module.upload_to_walrus()
│  │  ├─ FOR EACH FILE: _store_file_reference()
│  │  │  └─ Compute blob_id = SHA256(data)
│  │  │  └─ Upload or write locally
│  │  │  └─ Create blob reference entry
│  │  ├─ CREATE MANIFEST JSON
│  │  │  {
│  │  │    "voiceId": "voice-123",
│  │  │    "owner": "0xuser...",
│  │  │    "blobs": {
│  │  │      "embedding.bin": {blobId: "...", size: 1024, ...},
│  │  │      "config.json": {...},
│  │  │      "meta.json": {...},
│  │  │      "preview.wav": {...}
│  │  │    }
│  │  │  }
│  │  ├─ Store manifest as blob → manifest_blob_id
│  │  ├─ walrusUri = "walrus://{manifest_blob_id}"
│  │  └─ RETURN: {walrusUri, manifestBlobId, blobs: {...}, previewUrl}
│  └─ RETURN upload result to frontend
│
├─ Frontend receives: {walrusUri: "walrus://...", previewUrl: "http://..."}
└─ Preview URL displayed to user


┌─ PHASE 2: ON-CHAIN REGISTRATION (Smart Contract)
│
├─ User confirms voice in Dashboard
│  └─ Clicks "Register Voice On-Chain"
│
├─ Frontend calls: useVoiceRegister.registerVoice({
│    name: "My Voice",
│    modelUri: "walrus://blob_id",
│    rights: "Commercial",
│    pricePerUse: 0.001
│  })
│
├─ Hook creates & signs Transaction:
│  const tx = new Transaction();
│  const voice = tx.moveCall({
│    target: "0x1ad12.../voice_identity::register_voice",
│    arguments: [
│      tx.pure.string("My Voice"),
│      tx.pure.string("walrus://blob_id"),
│      tx.pure.string("Commercial"),
│      tx.pure.u64(1_000_000)  // 0.001 SUI in MIST
│    ]
│  });
│  tx.transferObjects([voice], senderAddress);
│
├─ User signs in wallet (Sui Wallet extension)
│
├─ signAndExecuteTransaction() sends to Sui blockchain
│
├─ Sui Validator Executes:
│  ├─ Call Move function
│  ├─ Create VoiceIdentity object with owner = signer
│  ├─ Store in blockchain state
│  ├─ Transfer object to owner
│  └─ Return txDigest
│
├─ Frontend waits for confirmation: suiClient.waitForTransaction(txDigest)
│
└─ SUCCESS: Voice object created on-chain with ID 0xabc...


┌─ PHASE 3: MARKETPLACE DISCOVERY (When Others Browse)
│
├─ Marketplace.tsx needs to list all voices
│  └─ Query voice registry from localStorage
│
├─ For each registered voice address:
│  └─ Call useVoicesWithWalrusMetadata(addresses)
│
├─ Hook fetches ALL voice data:
│  ├─ ON-CHAIN: suiClient.getOwnedObjects({
│  │    owner: address,
│  │    filter: {StructType: "0x1ad12.../voice_identity::VoiceIdentity"}
│  │  })
│  │  → Returns VoiceIdentity object with fields:
│  │    {owner, name, model_uri, rights, price_per_use, ...}
│  │
│  └─ OFF-CHAIN: For each voice with walrus:// URI:
│     ├─ fetchManifestFromUri(model_uri)
│     │  └─ Download manifest blob from Walrus
│     │  └─ Parse JSON
│     ├─ Extract meta.json from manifest
│     │  └─ Gets actual name, description
│     └─ Create preview audio URL
│        └─ getPreviewUrl() from preview.wav blob reference
│
├─ Frontend renders voice card:
│  ├─ Name + Description (from Walrus meta)
│  ├─ Preview audio player (with blob URL)
│  ├─ Price per use
│  └─ "License & Use" button
│
└─ User can listen to preview + see details


┌─ PHASE 4: VOICE USAGE & PAYMENT (When User Buys)
│
├─ User enters text in TTS UI
│  └─ Selects a marketplace voice
│
├─ User clicks "Generate Speech"
│  └─ Frontend shows payment breakdown:
│     ├─ Input: 0.1 SUI
│     ├─ Platform: 2.5% = 0.0025 SUI → 0x00fe9f5...
│     ├─ Royalty: 10% of remaining = 0.009625 SUI → Royalty recipient
│     └─ Creator: 87.375 SUI → Voice creator
│
├─ User approves payment in wallet
│
├─ Frontend calls: usePayForInference({
│    creatorAddress: "0xcreator...",
│    amount: 0.1,
│    royaltyRecipient: "0xroyalty..."
│  })
│
├─ Hook creates & signs Transaction:
│  const paymentCoin = coinWithBalance({balance: 100_000_000});
│  tx.moveCall({
│    target: "0x1ad12.../payment::pay_with_royalty_split",
│    typeArguments: ["0x2::sui::SUI"],
│    arguments: [
│      paymentCoin,
│      creatorAddress,
│      platformAddress,
│      royaltyRecipient
│    ]
│  });
│
├─ Sui Blockchain Executes:
│  ├─ coin::split() platform fee
│  ├─ transfer to platform
│  ├─ coin::split() royalty
│  ├─ transfer to royalty recipient
│  ├─ transfer remainder to creator
│  └─ emit 3 events
│
├─ Frontend waits for confirmation
│
├─ SUCCESS: Funds distributed
│  └─ Creator receives 87.375 SUI
│  └─ Platform receives 0.0025 SUI
│  └─ Royalty recipient receives 0.009625 SUI
│
├─ Frontend calls backend TTS endpoint:
│  backendApi.generateTTS(
│    modelUri: "walrus://blob_id",
│    text: "Hello world",
│    requesterAccount: userAddress
│  )
│
├─ BACKEND: server.py:/api/tts/generate
│  ├─ Verify access: verify_walrus_access(modelUri, userAddress)
│  ├─ Download from Walrus:
│  │  ├─ embedding.bin (voice characteristics)
│  │  ├─ config.json (model metadata)
│  │  └─ preview.wav (sample audio)
│  ├─ Return preview.wav as response
│  └─ (In production: call Chatterbox to generate actual TTS)
│
├─ Frontend receives audio blob
│  └─ Create <audio> element with blob URL
│  └─ User listens to generated speech
│
└─ COMPLETE: Voice used, creator paid automatically
```

---

### 4.2 Data Model Relationships

```
┌────────────────────────────────────────────────────────────────┐
│  FRONTEND BROWSER (React State)                                │
└────────────────────────────────────────────────────────────────┘
              ▲                           │
              │                           │ user actions
              │                           ▼
        ┌─────────────────────────────────────────────┐
        │  React Context + Hooks                      │
        ├─────────────────────────────────────────────┤
        │ • WalletProvider (Sui wallet state)         │
        │ • useVoiceMetadata (voice queries)          │
        │ • useVoicesWithWalrusMetadata (enrichment)  │
        │ • useVoiceRegister (on-chain actions)       │
        │ • usePayForInference (payments)             │
        └─────────────────────────────────────────────┘
              │
              │ HTTP/JSON
              ▼
┌────────────────────────────────────────────────────────────────┐
│  BACKEND PYTHON SERVER (FastAPI)                               │
├────────────────────────────────────────────────────────────────┤
│ • server.py (REST endpoints)                                   │
│ • voice_model.py (audio processing)                            │
│ • walrus.py (storage orchestration)                            │
│ • shelby.py (compatibility shim)                               │
└────────────────────────────────────────────────────────────────┘
       │                               │
       │                               ▼
       │                    ┌──────────────────────┐
       │                    │  WALRUS STORAGE      │
       │                    ├──────────────────────┤
       │ HTTP PUT/GET       │ • Manifests          │
       │ POST blobs         │ • Embeddings         │
       │ (local or remote)  │ • Configs            │
       │                    │ • Preview audio      │
       │                    │ • Voice metadata     │
       │                    │ Content-addressed    │
       │                    │ (SHA256 blob IDs)    │
       │                    └──────────────────────┘
       │                               ▲
       │                               │
       │ JSON-RPC                      │ Aggregator API
       ▼                               │
┌────────────────────────────────────────────────────────────────┐
│  SUI BLOCKCHAIN (Testnet)                                      │
├────────────────────────────────────────────────────────────────┤
│ ┌──────────────────┐    ┌─────────────────────┐                │
│ │ VOICE_IDENTITY   │    │ PAYMENT             │                │
│ │ Module           │    │ Module              │                │
│ ├──────────────────┤    ├─────────────────────┤                │
│ │ • register_voice │    │ • pay_with_royalty_ │                │
│ │ • delete_voice   │    │   split             │                │
│ │ • get_metadata   │    │ • pay_full_to_      │                │
│ │ • get_voice_id   │    │   creator           │                │
│ │                  │    │ • calculate_payment │                │
│ │ Stores:          │    │   _breakdown        │                │
│ │ VoiceIdentity    │    │                     │                │
│ │ objects          │    │ Emits Events:       │                │
│ │ (per creator)    │    │ • PaymentReceived   │                │
│ │                  │    │ • RoyaltyPaid       │                │
│ │                  │    │ • PlatformFeePaid   │                │
│ └──────────────────┘    └─────────────────────┘                │
│                                                                 │
│ Transaction History:                                            │
│ ├─ Voice registration (tx digest)                              │
│ ├─ Payment splits (with events)                                │
│ └─ Coin transfers (immutable ledger)                            │
│                                                                 │
│ Wallet State:                                                   │
│ ├─ Owned objects (VoiceIdentity objects)                        │
│ ├─ Coin balance (SUI MIST)                                      │
│ └─ Transaction history                                         │
│                                                                 │
│ Package:                                                        │
│ ID: 0x1ad12f0fd581dbd4fef7a30c9cff9bececfca1da450fe53257791502b3db073d
└────────────────────────────────────────────────────────────────┘
```

---

### 4.3 Storage & State Persistence

```
┌─ BLOCKCHAIN STATE (Immutable, On-Chain)
│
├─ VoiceIdentity Objects:
│  ├─ owner: 0xuser1...
│  ├─ name: "John's Voice"
│  ├─ model_uri: "walrus://abc123"
│  ├─ rights: "Commercial"
│  ├─ price_per_use: 1000000 (MIST)
│  └─ created_at: 1713607891000
│
├─ Payment Events (queryable):
│  ├─ PaymentReceived { from, to, amount }
│  ├─ RoyaltyPaid { payer, recipient, amount }
│  └─ PlatformFeePaid { payer, platform, amount }
│
└─ Coin Objects:
   ├─ Owner's SUI balance
   └─ Transaction history


┌─ WALRUS STORAGE STATE (Content-Addressed, Distributed)
│
├─ Manifest Blobs:
│  ├─ blob_id = SHA256(manifest_json)
│  └─ Content:
│     {
│       "voiceId": "voice-123",
│       "owner": "0xuser1",
│       "blobs": {
│         "embedding.bin": {blobId: "...", size: 1024},
│         "config.json": {...},
│         "meta.json": {...},
│         "preview.wav": {...}
│       }
│     }
│
├─ Embedding Blobs:
│  ├─ blob_id = SHA256(embedding_bytes)
│  └─ Content: 256-dim float32 vector (1024 bytes)
│
├─ Config Blobs:
│  ├─ blob_id = SHA256(config_json)
│  └─ Content: {sampleRate, channels, format, embeddingSize}
│
├─ Metadata Blobs:
│  ├─ blob_id = SHA256(meta_json)
│  └─ Content: {name, description, owner, voiceId, createdAt}
│
└─ Preview Audio Blobs:
   ├─ blob_id = SHA256(preview_wav)
   └─ Content: WAV audio (~5 seconds @ 16kHz)


┌─ BROWSER LOCAL STORAGE (Transient)
│
├─ voicevault_voice_registry: [
│   {address: "0xabc...", name: "John's Voice", registeredAt: ...},
│   {address: "0xdef...", name: "Jane's Voice", registeredAt: ...}
│  ]
│
├─ React Query Cache:
│  ├─ Query results (voice metadata, balances)
│  └─ Auto-refresh on stale
│
└─ dApp Kit State:
   ├─ Connected wallet address
   ├─ Selected account
   └─ Recent transactions


┌─ BACKEND LOCAL STORAGE (Development Only)
│
├─ backend/storage/walrus/blobs/
│  ├─ {blob_id_1}.bin
│  ├─ {blob_id_2}.bin
│  └─ ...
│
└─ backend/storage/walrus/meta/
   ├─ {blob_id_1}.json
   ├─ {blob_id_2}.json
   └─ ...

(In production: uses remote Walrus Publisher/Aggregator)
```

---

## 5. HOW AI INTEGRATES WITH BLOCKCHAIN

### 5.1 Voice Model Pipeline (AI → Blockchain)

```
RAW AUDIO FILE
  ▼
[BACKEND AI PROCESSING]
├─ FFmpeg Normalization
│  └─ 16kHz, mono, PCM format
├─ Embedding Generation
│  └─ Extract voice fingerprint (256-dim vector)
├─ Bundle Creation
│  └─ {embedding.bin, config.json, meta.json, preview.wav}
  ▼
[WALRUS STORAGE]
├─ Content-address each file
│  └─ blob_id = SHA256(data)
├─ Create manifest
│  └─ Maps filenames → blob references
└─ Store manifest blob
   └─ walrusUri = "walrus://manifest_blob_id"
  ▼
[BLOCKCHAIN REGISTRATION]
├─ User calls: registerVoice()
├─ Create VoiceIdentity object
│  └─ model_uri = "walrus://manifest_blob_id"
├─ Store on Sui blockchain
└─ User now owns voice on-chain

RESULT: Voice model registered and owned as an on-chain object
        AI fingerprint → blockchain reference → transferable asset
```

### 5.2 Voice Usage & TTS (Blockchain → AI)

```
USER WANTS TO USE A VOICE
  ▼
[BLOCKCHAIN PAYMENT]
├─ Lookup VoiceIdentity object
├─ Read model_uri (Walrus reference)
├─ Read price_per_use
├─ Call pay_with_royalty_split() with SUI coins
├─ Funds distributed:
│  ├─ Platform fee
│  ├─ Royalty recipient
│  └─ Creator
  ▼
[BACKEND VOICE RETRIEVAL]
├─ Download from Walrus manifest:
│  ├─ embedding.bin
│  ├─ config.json
│  └─ preview.wav
├─ Access control (paid user has permission)
  ▼
[AI TTS GENERATION]
├─ Input: Text to synthesize
├─ Voice model: Use embedding + preview audio
├─ Call Chatterbox (Gradio) with voice clone
├─ Generate speech in target voice
  ▼
RETURN: Audio file (wav format)

RESULT: Blockchain payment triggers AI voice synthesis
        On-chain ownership enforced via smart contract
        Automatic royalty distribution
```

### 5.3 Voice Cloning Technology Stack

**Current Implementation**:
- **Chatterbox** (Gradio API by ResembleAI)
  - Zero-shot voice cloning
  - Takes reference audio + text
  - Returns synthesized speech in that voice

**Integration** (`frontend/src/lib/chatterbox.ts`):
```typescript
chatterboxVoiceClone(text, audioFile, params)
// Connects to: ResembleAI/Chatterbox Gradio space
// Passes: text, audio_prompt (reference voice)
// Returns: generated speech blob

// Parameters:
// - exaggeration: 0-1 (voice expressiveness)
// - temperature: 0-1 (randomness)
// - seed: for reproducibility
// - cfgw: classifier-free guidance weight
// - vadTrim: voice activity detection
```

**Backend TTS Endpoint** (`server.py:/api/tts/generate`):
```python
# In production: Would call Chatterbox here
# Current: Returns preview.wav from Walrus

# Expected flow:
@app.post("/api/tts/generate")
├─ Verify payment (optional in current version)
├─ Download embedding.bin, config.json, preview.wav
├─ Call chatterbox_client.predict()
│  ├─ Pass text
│  ├─ Pass preview.wav as voice reference
│  └─ Get generated audio
├─ Return generated audio blob
└─ Stream to user
```

---

## 6. WALRUS STORAGE & DATA MANAGEMENT

### 6.1 Storage Modes

**Local Mode** (Development):
```
WALRUS_STORAGE_MODE=local
WALRUS_PUBLISHER_URL=local
WALRUS_AGGREGATOR_URL=http://localhost:3000/api/walrus

Operations:
- PUT: backend/storage/walrus/blobs/{blob_id}.bin
- GET: backend/storage/walrus/blobs/{blob_id}.bin
- DELETE: Remove local files

Metadata:
- backend/storage/walrus/meta/{blob_id}.json
```

**Remote Mode** (Production):
```
WALRUS_STORAGE_MODE=remote
WALRUS_PUBLISHER_URL=https://publisher.walrus-testnet.walrus.space
WALRUS_AGGREGATOR_URL=https://aggregator.walrus-testnet.walrus.space
WALRUS_EPOCHS=5
WALRUS_DELETABLE=true

Operations:
- PUT: HTTP PUT {PUBLISHER}/v1/blobs?epochs=5
  └─ Returns: {blobId, objectId}
- GET: HTTP GET {AGGREGATOR}/v1/blobs/{blob_id}
  └─ Free reads via public Aggregator
- DELETE: Sui transaction to burn Blob object
  └─ If deletable=true
```

### 6.2 Manifest Pattern (Bundle Multiple Files)

**Problem**: Voice model requires multiple files (embedding, config, meta, preview)
Walrus stores single blobs. How to reference multiple blobs?

**Solution**: Manifest Pattern
```json
{
  "voiceId": "voice-123",
  "owner": "0xuser...",
  "blobs": {
    "embedding.bin": {
      "blobId": "abc123...",
      "objectId": "0x...",
      "size": 1024,
      "chunked": false
    },
    "config.json": {
      "blobId": "def456...",
      "objectId": "0x...",
      "size": 256,
      "chunked": false
    },
    "meta.json": {
      "blobId": "ghi789...",
      "objectId": "0x...",
      "size": 512,
      "chunked": false
    },
    "preview.wav": {
      "blobId": "jkl012...",
      "objectId": "0x...",
      "size": 160000,
      "chunked": false
    }
  },
  "manifestBlobId": "manifest_blob_id",
  "walrusUri": "walrus://manifest_blob_id",
  "version": 1
}

STORED AS: Single Walrus blob
blob_id = SHA256(above JSON)
walrusUri = "walrus://blob_id"

USAGE:
1. Download manifest from Walrus using walrusUri
2. For each file needed:
   - Look up filename in manifest.blobs
   - Get blobId
   - Download that blob
```

### 6.3 Access Control

**Current Implementation**:
```python
def verify_walrus_access(uri: str, requester_account: str) -> bool:
  """Placeholder access control"""
  try:
    manifest = load_manifest(parse_walrus_uri(uri))
    owner = str(manifest.get("owner", ""))
    
    # Owner always has access
    if owner and requester_account and owner.lower() == requester_account.lower():
      return True
    
    # Otherwise allow (permissive default)
    return True
  except:
    return False
```

**Intended Logic**:
- Voice owner: Always has access
- Non-owners: Can access if they:
  - Paid for usage (payment recorded on-chain)
  - Have license from owner
  - Both would require marketplace purchase flow

**Current Status**: Payment check happens before TTS in hook, but backend is permissive

---

## 7. KEY DEPENDENCIES & LIBRARIES

### 7.1 Frontend Dependencies

```json
{
  "@mysten/sui": "2.13.0",           // Sui JSON-RPC client
  "@mysten/dapp-kit": "1.0.4",       // Sui wallet integration
  "@gradio/client": "2.1.0",         // TTS API client (Chatterbox)
  
  "react": "18.3.1",
  "react-router-dom": "6.30.1",      // Routing
  "react-hook-form": "7.61.1",       // Form state management
  "zod": "3.25.76",                  // Schema validation
  
  "tailwindcss": "latest",           // Styling
  "@radix-ui/react-*": "latest",     // UI components (accordion, dialog, etc.)
  "lucide-react": "0.462.0",         // Icons
  "recharts": "2.15.4",              // Charts & analytics
  
  "@tanstack/react-query": "5.95.2", // Data fetching & caching
  "sonner": "1.7.4",                 // Toast notifications
  "date-fns": "3.6.0",               // Date utilities
  
  "vite": "bundler",                 // Build tool
  "eslint": "linter",
  "typescript": "language"
}
```

### 7.2 Backend Dependencies

```
fastapi==0.115.0              # Web framework
uvicorn[standard]==0.30.0     # ASGI server
python-dotenv==1.1.0          # Environment variables
httpx==0.27.0                 # Async HTTP client
python-multipart==0.0.9       # Form data parsing

Optional (not in requirements.txt yet):
- PIL/Pillow (image processing)
- scipy (audio processing)
- numpy (numerical computing)
- torch/tensorflow (ML model inference)
- ffmpeg-python (audio normalization via Python)
```

### 7.3 System Dependencies

```
FFmpeg (for audio normalization)
- Used by: voice_model.py::normalize_audio()
- Install: apt-get install ffmpeg (Linux), brew install ffmpeg (Mac)
- Check: which ffmpeg

Python 3.8+
Node.js 18+
npm 9+
```

---

## 8. KEY INTEGRATION POINTS

### 8.1 Frontend ↔ Backend

```
frontend/src/lib/api.ts (HTTP Client)
│
├─ POST /api/voice/process
│  ├─ Input: {audio, name, description, owner, voiceId}
│  └─ Output: {walrusUri, manifestBlobId, previewUrl, bundle}
│
├─ POST /api/tts/generate
│  ├─ Input: {modelUri, text, requesterAccount}
│  └─ Output: audio/wav blob
│
├─ POST /api/walrus/upload
│  ├─ Input: {bundleFiles: {embedding, config, meta, preview}}
│  └─ Output: {walrusUri, manifestBlobId}
│
├─ POST /api/walrus/download
│  ├─ Input: {uri, filename, requesterAccount}
│  └─ Output: ArrayBuffer (file content)
│
├─ POST /api/walrus/delete
│  ├─ Input: {uri, account}
│  └─ Output: {success}
│
└─ POST /api/payment/breakdown
   ├─ Input: {amount}
   └─ Output: {platformFee, royalty, creator}
```

### 8.2 Frontend ↔ Blockchain (Sui)

```
frontend/src/contexts/WalletContext.tsx (Provider)
│
├─ WalletProvider wraps app
├─ Enables: @mysten/dapp-kit hooks
│
useVoiceRegister (Hook)
├─ Calls: tx.moveCall("voice_identity::register_voice")
├─ Input: {name, modelUri, rights, pricePerUse}
└─ Output: {success, transactionHash}

usePayForInference (Hook)
├─ Calls: tx.moveCall("payment::pay_with_royalty_split")
├─ Input: {creatorAddress, amount, royaltyRecipient}
└─ Output: {success, transactionHash}

useVoiceMetadata (Hook)
├─ Calls: suiClient.getOwnedObjects()
├─ Filter: StructType = VoiceIdentity
└─ Output: VoiceMetadata[]
```

### 8.3 Blockchain ↔ Walrus

```
Frontend stores Walrus URI in VoiceIdentity.model_uri (on-chain)
┌─ "walrus://blob_id_of_manifest"
│
└─ Manifest blob contains references to:
   ├─ embedding.bin
   ├─ config.json
   ├─ meta.json
   └─ preview.wav

On-Chain Access:
- Move contract stores model_uri string
- Can be read by any caller
- Frontend uses URI to fetch voice files from Walrus
- Access control at frontend/backend level
```

### 8.4 Backend ↔ Walrus

```
backend/walrus.py (Storage Module)
│
├─ LOCAL MODE (dev):
│  ├─ Write: backend/storage/walrus/blobs/{blob_id}.bin
│  ├─ Read: backend/storage/walrus/blobs/{blob_id}.bin
│  └─ Delete: Remove local files
│
└─ REMOTE MODE (prod):
   ├─ Write: HTTP PUT {PUBLISHER}/v1/blobs
   ├─ Read: HTTP GET {AGGREGATOR}/v1/blobs/{blob_id}
   └─ Delete: Sui transaction (burn blob object)

Orchestration:
- upload_to_walrus: Handles all file uploads + manifest
- download_from_walrus: Fetches single blob
- download_file: Gets file from manifest
- load_manifest: Deserializes manifest JSON
```

---

## 9. OPERATIONAL FLOWS

### 9.1 Complete User Journey: Creator Perspective

```
1. CREATOR ONBOARDING
   ├─ Visit landing page (Index.tsx)
   ├─ Connect wallet (WalletProvider, Sui extension)
   ├─ Navigate to Upload (Upload.tsx)

2. VOICE UPLOAD
   ├─ Record or upload audio file
   ├─ Enter name, description, rights, price
   ├─ Frontend: backendApi.processVoiceModel()
   ├─ Backend processes audio (2-10 seconds)
   ├─ Walrus stores bundle (uploads files)
   ├─ Frontend receives walrusUri + preview URL

3. ON-CHAIN REGISTRATION
   ├─ Creator previews voice (plays audio)
   ├─ Clicks "Register On-Chain"
   ├─ useVoiceRegister.registerVoice()
   ├─ User signs transaction in wallet
   ├─ VoiceIdentity object created on Sui
   ├─ Object ID assigned

4. MARKETPLACE LISTING
   ├─ Voice appears in marketplace
   ├─ Name + preview visible to others
   ├─ Price per use displayed

5. EARNINGS TRACKING
   ├─ Creator visits Dashboard
   ├─ Sees payment events (from smart contract)
   ├─ Tracks total earnings
   ├─ Views usage analytics
```

### 9.2 Complete User Journey: Consumer Perspective

```
1. MARKETPLACE DISCOVERY
   ├─ Visit Marketplace (Marketplace.tsx)
   ├─ Browse available voices
   ├─ See preview audio for each
   ├─ Read name, description, price

2. VOICE SELECTION & LICENSING
   ├─ Click "License Voice" button
   ├─ See payment breakdown:
   │  ├─ 2.5% platform fee
   │  ├─ 10% royalty recipient
   │  └─ 87.5% to creator
   ├─ Approve payment in wallet
   ├─ usePayForInference() executes
   ├─ SUI transferred with splits

3. VOICE USAGE
   ├─ Enter text to synthesize
   ├─ Select licensed voice
   ├─ Click "Generate Speech"
   ├─ Backend calls TTS API
   ├─ Returns audio in user's browser
   ├─ User can listen, download

4. MULTIPLE USES
   ├─ For each use, repeat steps 2-3
   ├─ Creator receives payment each time
   ├─ Can use same voice indefinitely once licensed
```

---

## 10. SECURITY & CONSIDERATIONS

### 10.1 Current Implementation

**Strengths**:
- ✅ On-chain ownership via Sui blockchain
- ✅ Smart contract payment distribution (immutable)
- ✅ Content-addressed Walrus storage (immutable IDs)
- ✅ Wallet-based authentication
- ✅ No centralized database of passwords

**Areas for Enhancement**:
- ⚠️ Access control is permissive (placeholder)
- ⚠️ No license enforcement (anyone can use after paying once)
- ⚠️ Embedding generation is placeholder (hash-based, not real ML)
- ⚠️ Backend should validate payment before TTS
- ⚠️ Consider rate limiting on TTS endpoint
- ⚠️ CORS currently allows all origins

### 10.2 Recommended Hardening

```python
# server.py - Add CORS restrictions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Restrict origins
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["content-type"],
)

# server.py - Add rate limiting
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/api/tts/generate")
@limiter.limit("5/minute")
async def tts_generate(request: Request):
    ...

# walrus.py - Real access control
def verify_walrus_access(uri: str, requester_account: str) -> bool:
    # Query blockchain: Did this account pay?
    # Check: Is there a payment receipt from tx history?
    # Return: True if payment recorded
    ...

# server.py - Validate before TTS
@app.post("/api/tts/generate")
async def tts_generate(request: Request):
    ...
    if model_uri.startswith("walrus://"):
        # THIS SHOULD CHECK PAYMENT RECEIPT
        has_access = verify_walrus_access(model_uri, requester_account)
        if not has_access:
            return JSONResponse(
                {"error": "No purchase record found"},
                status_code=403
            )
    ...
```

---

## 11. DEPLOYMENT TARGETS

### 11.1 Current Setup (Development)

```
Frontend: http://localhost:5173 (Vite dev server)
Backend: http://localhost:8000 (FastAPI uvicorn)
Blockchain: Sui testnet
Storage: Local filesystem (backend/storage/walrus/)
```

### 11.2 Production Deployment

**Frontend**:
- Deploy to Vercel, Netlify, or GitHub Pages
- See: `vercel.json` and `nginx.conf` in frontend/

**Backend**:
- Deploy to Render.com
- See: `render.yaml` in project root
- Docker: `backend/Dockerfile`

**Blockchain**:
- Switch to `mainnet` in WalletProvider
- Update contract package ID if redeployed

**Storage**:
- Set `WALRUS_STORAGE_MODE=remote`
- Configure Walrus testnet or mainnet endpoints

```bash
# Production environment variables
WALRUS_STORAGE_MODE=remote
WALRUS_PUBLISHER_URL=https://publisher.walrus.space  # (or testnet)
WALRUS_AGGREGATOR_URL=https://aggregator.walrus.space
WALRUS_EPOCHS=365  # longer retention for mainnet
WALRUS_DELETABLE=false  # disable deletion for mainnet
```

---

## 12. FUTURE ENHANCEMENT OPPORTUNITIES

```
┌─ AI/ML IMPROVEMENTS
├─ Replace placeholder embedding with real model
│  ├─ Resemblyzer (voice similarity)
│  ├─ GE2E (speaker encoding)
│  └─ Or train custom model on voice dataset
├─ Integrate real TTS synthesis
│  ├─ Chatterbox API (Gradio)
│  ├─ ElevenLabs API
│  └─ Or run local TTS model
└─ Add voice effects & processing
   ├─ Pitch shifting
   ├─ Speed adjustment
   └─ Emotional tone control

┌─ BLOCKCHAIN FEATURES
├─ NFT marketplace integration
│  └─ Transfer voice ownership
├─ Royalty tracking on-chain
│  └─ Automatic creator payments
├─ Staking/governance
│  └─ Community voting on platform features
└─ Cross-chain bridges
   └─ Interoperability with Ethereum, Solana

┌─ MARKETPLACE FEATURES
├─ Advanced voice search
│  ├─ Filter by creator, language, style
│  └─ Similar voice recommendations
├─ Voice bundles & collections
│  └─ Creator packages (3 voices for discounted price)
├─ Voice licensing tiers
│  └─ Personal vs commercial vs enterprise
└─ Creator reputation system
   └─ Ratings, reviews, verification badges

┌─ INFRASTRUCTURE
├─ Scale Walrus deployment
│  └─ Multiple regions for low-latency access
├─ Database for analytics
│  └─ PostgreSQL for searchable indexes
├─ CDN for audio delivery
│  └─ CloudFlare or similar
└─ API rate limiting & monetization
   └─ Charge API consumers

┌─ REGULATORY
├─ Voice consent & attribution
│  ├─ Verify creator owns voice rights
│  └─ Disallow deepfakes
├─ Terms of service enforcement
│  ├─ Prohibited uses (misinformation, fraud)
│  └─ Content moderation
└─ International compliance
   └─ GDPR, CCPA, data privacy laws
```

---

## Summary

**VoiceVault Sui** is a sophisticated three-layer architecture:

1. **Frontend (React)**: Web3 dApp for voice creation, registration, and marketplace
2. **Backend (FastAPI)**: Voice processing pipeline + Walrus storage orchestration
3. **Blockchain (Sui Move)**: Ownership contracts + automatic payment distribution

**Data Flow**: Audio → Embedding → Walrus Bundle → On-Chain URI → Marketplace → Payment → TTS → Output

**Key Innovation**: Combines AI voice technology with smart contract payment automation and decentralized storage for true creator ownership and transparent monetization.

**Status**: MVP deployed on Sui testnet with local Walrus storage. Production-ready for mainnet deployment with enhanced access control and real TTS integration.

