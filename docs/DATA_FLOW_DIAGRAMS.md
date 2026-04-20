# VoiceVault Sui - Data Flow Diagrams & System Architecture

## Table of Contents
1. [High-Level Architecture](#high-level-architecture)
2. [Voice Registration Flow](#voice-registration-flow)
3. [Voice Usage & Payment Flow](#voice-usage--payment-flow)
4. [Data Models & Relationships](#data-models--relationships)
5. [Component Communication](#component-communication)
6. [State Management](#state-management)

---

## High-Level Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          INTERNET USER                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP / Browser
                              ▼
        ┌─────────────────────────────────────────────┐
        │                                             │
        │    FRONTEND (React + TypeScript)           │
        │    - Voice Upload UI                       │
        │    - Marketplace Browse                    │
        │    - Wallet Connection                     │
        │    - Payment Approval                      │
        │    - TTS Generation                        │
        │                                             │
        └──────────┬──────────────┬──────────────────┘
                   │              │
        ┌──────────▼──┐      ┌────▼──────────┐
        │   HTTP/REST │      │ WebSocket or  │
        │   Requests  │      │ JSON-RPC Calls│
        │             │      │               │
        ▼             ▼      ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  BACKEND         │  │  WALRUS          │  │  SUI             │
│  (FastAPI)       │  │  (Blob Storage)  │  │  (Blockchain)    │
│                  │  │                  │  │                  │
│ • Process Voice  │  │ • embedding.bin  │  │ • VoiceIdentity  │
│ • TTS Endpoint   │  │ • config.json    │  │ • Payment Splits │
│ • Walrus Proxy   │  │ • meta.json      │  │ • Events         │
│ • Payment Calc   │  │ • preview.wav    │  │                  │
│                  │  │ • manifests      │  │ Package ID:      │
│ Port: 3000       │  │                  │  │ 0x1ad12f0...     │
│ (HTTP)           │  │ Free reads via   │  │ Network: Testnet │
│                  │  │ Aggregators      │  │                  │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

### Technology Stack by Layer

```
┌────────────────────────────────────────────────────────────┐
│  PRESENTATION LAYER                                        │
├────────────────────────────────────────────────────────────┤
│  React 18 | TypeScript | Vite | Tailwind CSS | Shadcn/UI  │
│  Router | React Hook Form | TanStack Query                │
└────────────────────────────────────────────────────────────┘
                          │
┌────────────────────────────────────────────────────────────┐
│  APPLICATION LAYER                                         │
├────────────────────────────────────────────────────────────┤
│  Custom Hooks | Context API | Wallet Provider             │
│  useVoiceRegister | usePayForInference | useVoicesWithWalrus
└────────────────────────────────────────────────────────────┘
                          │
┌────────────────────────────────────────────────────────────┐
│  INTEGRATION LAYER                                         │
├────────────────────────────────────────────────────────────┤
│  @mysten/dapp-kit | @mysten/sui | Axios | Sonner Toast   │
└────────────────────────────────────────────────────────────┘
                     │         │         │
        ┌────────────┴────┬────┴────┬───┴─────────┐
        │                 │         │             │
   ┌────▼────┐      ┌──────▼──┐ ┌──▼────────┐ ┌─▼──────┐
   │ Backend  │      │ Walrus  │ │ Sui Chain │ │ Others │
   │ FastAPI  │      │ Storage │ │ (JSON-RPC)│ │        │
   └──────────┘      └─────────┘ └───────────┘ └────────┘
```

---

## Voice Registration Flow

### Complete End-to-End: Audio → Blockchain

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      PHASE 1: AUDIO UPLOAD                              │
└─────────────────────────────────────────────────────────────────────────┘

USER (Frontend)
│
├─ Selects audio file
├─ Enters: name, description, rights, price_per_use
│
└─ Clicks: "Process Voice"
   │
   └──────► HTTP POST /api/voice/process
            Form Data: {audio, name, description, owner, voiceId}
            │
            ┌────────────────────────────────────────────────────────┐
            │         BACKEND: voice_model.py                        │
            ├────────────────────────────────────────────────────────┤
            │                                                        │
            │  1. normalize_audio(audio_buffer)                    │
            │     ├─ FFmpeg: Convert to 16kHz mono WAV            │
            │     └─ Output: normalized_audio (bytes)             │
            │                                                        │
            │  2. generate_embedding(normalized_audio)            │
            │     ├─ Extract voice fingerprint                    │
            │     ├─ Create 256-dim float32 vector               │
            │     └─ Output: embedding.bin                        │
            │                                                        │
            │  3. create_voice_bundle(...)                        │
            │     ├─ embedding.bin (1KB)                          │
            │     ├─ config.json (JSON metadata)                  │
            │     ├─ meta.json (creator info)                     │
            │     └─ preview.wav (first 5 sec audio)             │
            │                                                        │
            └────────────────────────────────────────────────────────┘
                │
                └──────► upload_to_walrus(owner, voice_id, bundle)
                         │
                         ┌──────────────────────────────────────┐
                         │     WALRUS BACKEND: walrus.py        │
                         ├──────────────────────────────────────┤
                         │                                      │
                         │ FOR EACH FILE:                      │
                         │ ├─ Compute blob_id = SHA256(data)  │
                         │ ├─ Store blob (local or remote)    │
                         │ ├─ Record in meta.json             │
                         │ └─ Return: {blobId, objectId}      │
                         │                                      │
                         │ THEN:                               │
                         │ ├─ Create manifest JSON:            │
                         │ │  {                                │
                         │ │    "voiceId": "...",             │
                         │ │    "owner": "0x...",             │
                         │ │    "blobs": {                    │
                         │ │      "embedding.bin": {...},    │
                         │ │      "config.json": {...},      │
                         │ │      "meta.json": {...},        │
                         │ │      "preview.wav": {...}       │
                         │ │    }                            │
                         │ │  }                              │
                         │ │                                  │
                         │ ├─ Store manifest as blob          │
                         │ ├─ Get manifest_blob_id           │
                         │ ├─ walrusUri = "walrus://manifest" │
                         │ └─ Return all metadata             │
                         │                                      │
                         └──────────────────────────────────────┘
                         │
                         └──────► HTTP 200 OK
                                 {
                                   "walrusUri": "walrus://abc123",
                                   "manifestBlobId": "abc123",
                                   "previewUrl": "http://...",
                                   "blobs": {...}
                                 }

FRONTEND
│
├─ Receive walrusUri & previewUrl
├─ Display preview audio to user
│
└─ User preview ✓
   │
   └──────────────────────────────────────────────────────────┐


┌─────────────────────────────────────────────────────────────────────────┐
│                  PHASE 2: ON-CHAIN REGISTRATION                         │
└─────────────────────────────────────────────────────────────────────────┘

FRONTEND: useVoiceRegister()
│
├─ Create Transaction (Sui Transaction)
│  │
│  └─ tx.moveCall({
│     target: "0x1ad12.../voice_identity::register_voice",
│     arguments: [
│       tx.pure.string("My Voice"),
│       tx.pure.string("walrus://abc123"),
│       tx.pure.string("Commercial"),
│       tx.pure.u64(1_000_000)  // 0.001 SUI in MIST
│     ]
│  })
│
├─ Sign transaction (Wallet)
│  │
│  └─ User clicks in Sui Wallet extension
│     └─ Approve transaction
│
└─ Execute transaction (signAndExecuteTransaction)
   │
   ┌────────────────────────────────────────────────────────┐
   │         SUI BLOCKCHAIN: voice_identity.move            │
   ├────────────────────────────────────────────────────────┤
   │                                                        │
   │ register_voice(name, model_uri, rights, price):      │
   │ ├─ sender = tx_context::sender()                    │
   │ ├─ Create VoiceIdentity object:                     │
   │ │  {                                                │
   │ │    id: UID::new(ctx),                           │
   │ │    owner: sender,                               │
   │ │    name: "My Voice",                            │
   │ │    model_uri: "walrus://abc123",                │
   │ │    rights: "Commercial",                        │
   │ │    price_per_use: 1_000_000,                    │
   │ │    created_at: now()                            │
   │ │  }                                               │
   │ │                                                   │
   │ ├─ Store in blockchain state                      │
   │ ├─ Emit VoiceRegistered event                     │
   │ └─ Return object ID                               │
   │                                                    │
   └────────────────────────────────────────────────────────┘
   │
   └──────► Transaction Digest: 0xabcd...
            Status: ✓ Success
            Object ID: 0x7f5a...

FRONTEND
│
├─ Wait for confirmation: suiClient.waitForTransaction()
├─ Display: "Voice registered on-chain!"
├─ Show: Object ID, Transaction hash
│
└─ SUCCESS ✓
   └─ User now has voice ownership on blockchain
```

---

## Voice Usage & Payment Flow

### When User Buys & Uses a Voice

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   PHASE 1: VOICE DISCOVERY                              │
└─────────────────────────────────────────────────────────────────────────┘

FRONTEND: useVoicesWithWalrusMetadata(addresses)
│
├─ FOR EACH VOICE ADDRESS:
│  │
│  ├─ Query Sui: suiClient.getOwnedObjects()
│  │  ├─ Filter: StructType = VoiceIdentity
│  │  └─ Returns: Voice object with fields:
│  │     {owner, name, model_uri, rights, price_per_use, ...}
│  │
│  └─ IF model_uri starts with "walrus://":
│     │
│     ├─ Download manifest from Walrus
│     │  └─ manifestBlobId = parse_walrus_uri(model_uri)
│     │  └─ manifest = fetch(aggregator/v1/blobs/{manifestBlobId})
│     │
│     ├─ Extract metadata
│     │  └─ meta.json blob → {name, description, ...}
│     │
│     └─ Create preview URL
│        └─ previewUrl = getPreviewUrl(manifest.blobs["preview.wav"])
│
└─ Render Voice Cards in Marketplace
   ├─ Show: Name, Description, Price, Preview Audio
   └─ Button: "License & Use"

USER
│
└─ Clicks: "License & Use" on a voice
   │
   ├─ Selected Voice: {creator, price, modelUri}
   │
   └─ Proceed to payment


┌─────────────────────────────────────────────────────────────────────────┐
│                   PHASE 2: PAYMENT & SPLITS                             │
└─────────────────────────────────────────────────────────────────────────┘

FRONTEND: usePayForInference()
│
├─ Calculate payment breakdown
│  │
│  └─ backend API: POST /api/payment/breakdown
│     Input: {amount: 0.1}
│     │
│     ┌──────────────────────────────────────────┐
│     │    BACKEND: server.py                    │
│     ├──────────────────────────────────────────┤
│     │ amount = 0.1 SUI = 100_000_000 MIST     │
│     │                                          │
│     │ platform_fee = 100M * 250 / 10000 = 2.5M │
│     │ remaining = 100M - 2.5M = 97.5M        │
│     │ royalty = 97.5M * 1000 / 10000 = 9.75M │
│     │ creator = 97.5M - 9.75M = 87.75M       │
│     │                                          │
│     │ Return: {                               │
│     │   platformFee: 0.0025,                  │
│     │   royalty: 0.009625,                    │
│     │   creator: 0.087375                     │
│     │ }                                        │
│     └──────────────────────────────────────────┘
│     │
│     └──────► FRONTEND Display Breakdown
│
├─ Show user: "This will pay:"
│  ├─ Platform: 0.0025 SUI
│  ├─ Royalty Recipient: 0.009625 SUI
│  └─ Creator: 0.087375 SUI
│
├─ User Approves
│
├─ Create Transaction (Sui)
│  │
│  └─ const tx = new Transaction()
│     │
│     ├─ Create payment coin
│     │  └─ paymentCoin = coinWithBalance({balance: 100_000_000})
│     │
│     └─ tx.moveCall({
│        target: "0x1ad12.../payment::pay_with_royalty_split",
│        typeArguments: ["0x2::sui::SUI"],
│        arguments: [
│          paymentCoin,
│          tx.pure.address(creatorAddress),
│          tx.pure.address(platformAddress),      // 0x00fe9f5...
│          tx.pure.address(royaltyRecipient)
│        ]
│     })
│
├─ User signs in wallet
│
└─ Execute transaction
   │
   ┌────────────────────────────────────────────────────────┐
   │    SUI BLOCKCHAIN: payment::pay_with_royalty_split    │
   ├────────────────────────────────────────────────────────┤
   │                                                        │
   │ INPUT: paymentCoin (100M MIST)                       │
   │                                                        │
   │ STEP 1: Calculate platform fee                       │
   │ ├─ platform_fee = 100M * 250 / 10000 = 2.5M         │
   │ ├─ platform_coin = coin::split(&mut payment, 2.5M)  │
   │ └─ transfer::public_transfer(platform_coin, 0x00...)  │
   │                                                        │
   │ STEP 2: Calculate royalty                            │
   │ ├─ remaining = 100M - 2.5M = 97.5M                  │
   │ ├─ royalty = 97.5M * 1000 / 10000 = 9.75M          │
   │ ├─ royalty_coin = coin::split(&mut payment, 9.75M)  │
   │ └─ transfer::public_transfer(royalty_coin, recipient)│
   │                                                        │
   │ STEP 3: Send creator remainder                       │
   │ ├─ creator_coin = payment (87.75M remaining)        │
   │ └─ transfer::public_transfer(creator_coin, creator)  │
   │                                                        │
   │ STEP 4: Emit events                                  │
   │ ├─ event::emit(PlatformFeePaid {                     │
   │ │   payer: user,                                     │
   │ │   platform: 0x00...,                               │
   │ │   amount: 2.5M                                     │
   │ │ })                                                 │
   │ ├─ event::emit(RoyaltyPaid {                         │
   │ │   payer: user,                                     │
   │ │   recipient: royalty_recipient,                    │
   │ │   amount: 9.75M                                    │
   │ │ })                                                 │
   │ └─ event::emit(PaymentReceived {                     │
   │     from: user,                                      │
   │     to: creator,                                     │
   │     amount: 87.75M                                   │
   │ })                                                    │
   │                                                        │
   └────────────────────────────────────────────────────────┘
   │
   └──────► Transaction Success ✓
            All funds distributed automatically


┌─────────────────────────────────────────────────────────────────────────┐
│                   PHASE 3: VOICE USAGE (TTS)                            │
└─────────────────────────────────────────────────────────────────────────┘

FRONTEND
│
├─ User entered text: "Hello world"
├─ Selected voice: {modelUri: "walrus://...", name: "John's Voice"}
│
└─ Clicked: "Generate Speech"
   │
   └──────► HTTP POST /api/tts/generate
            {
              modelUri: "walrus://abc123",
              text: "Hello world",
              requesterAccount: "0xuser..."
            }
            │
            ┌───────────────────────────────────────────┐
            │   BACKEND: server.py:/api/tts/generate    │
            ├───────────────────────────────────────────┤
            │                                           │
            │ 1. Verify access                         │
            │    └─ verify_walrus_access(modelUri,    │
            │         requesterAccount)                │
            │       └─ Check: User owns or purchased   │
            │                                           │
            │ 2. Download voice files from Walrus      │
            │    ├─ manifestBlobId = parse(modelUri)  │
            │    └─ Download:                          │
            │       ├─ embedding.bin                  │
            │       ├─ config.json                    │
            │       ├─ preview.wav                    │
            │       └─ meta.json                      │
            │                                           │
            │ 3. (PROD) Call Chatterbox TTS            │
            │    ├─ Input: text + reference audio    │
            │    └─ Output: generated_audio.wav       │
            │                                           │
            │ 4. Return audio                          │
            │    └─ audio/wav blob                    │
            │                                           │
            └───────────────────────────────────────────┘
            │
            └──────► HTTP 200 OK
                    Content-Type: audio/wav
                    Body: [audio bytes]

FRONTEND
│
├─ Receive audio blob
├─ Create Object URL: URL.createObjectURL(blob)
├─ Create <audio> element
│
└─ User listens ▶️

SUCCESS ✓
└─ Creator receives payment automatically
   └─ User can use voice again if purchased
```

---

## Data Models & Relationships

### Entity Relationship Diagram

```
┌─────────────────────────────┐
│      VOICE IDENTITY         │
│  (Sui Blockchain Object)    │
├─────────────────────────────┤
│ • id (UID)                  │
│ • owner (address) ────────┐ │
│ • name (String)           │ │
│ • model_uri (String) ──┐  │ │
│ • rights (String)      │  │ │
│ • price_per_use (u64)  │  │ │
│ • created_at (u64)     │  │ │
└─────────────────────────┼──┼─┘
                          │  │
                    ┌─────┘  │
                    │        │
        ┌──────────▼──────────────────────┐
        │    WALRUS MANIFEST              │
        │ (Content-Addressed Storage)     │
        ├─────────────────────────────────┤
        │ • manifestBlobId (walrus://...) │
        │ • voiceId (reference to owner)  │
        │ • owner (reference to Voice)    │
        │ • version                       │
        │ • blobs: {                      │
        │   "embedding.bin": {            │
        │     blobId, size, chunked       │
        │   },                            │
        │   "config.json": {...},         │
        │   "meta.json": {...},           │
        │   "preview.wav": {...}          │
        │ }                               │
        └────────┬───────────────────┬────┘
                 │                   │
        ┌────────▼────┐      ┌───────▼────┐
        │ Walrus Blob │      │ Walrus Blob│
        │ (embedding) │      │ (preview)  │
        └─────────────┘      └────────────┘

RELATIONSHIPS:
- VoiceIdentity.model_uri → Walrus Manifest (via walrus:// URI)
- Manifest.blobs → Multiple Walrus Blobs (content-addressed)
- Manifest.owner → VoiceIdentity.owner (same address)
```

### State Snapshot Examples

**Voice Creation State**:
```
Timeline:
├─ T0: User uploads audio file
├─ T1: Audio normalized (16kHz mono)
├─ T2: Embedding generated (256-dim vector)
├─ T3: Bundle created (4 files)
├─ T4: Files uploaded to Walrus
├─ T5: Manifest created
├─ T6: Manifest uploaded, walrusUri returned
├─ T7: User sees preview in browser
├─ T8: User clicks "Register"
├─ T9: Transaction signed
└─ T10: VoiceIdentity object created on Sui
        (now on blockchain, immutable)
```

**Payment State**:
```
Before Payment:
├─ User coin balance: 1 SUI
├─ Creator coin balance: 100 SUI
└─ Platform balance: 50 SUI

Transaction: pay_with_royalty_split(1 SUI)
├─ Platform fee: 0.0025 SUI
├─ Royalty: 0.009625 SUI
└─ Creator: 0.087375 SUI

After Payment:
├─ User coin balance: 0 SUI (spent 1 SUI)
├─ Creator coin balance: 100.087375 SUI (received)
├─ Royalty recipient: +0.009625 SUI
└─ Platform balance: 50.0025 SUI (received)

Events emitted (queryable on-chain):
├─ PaymentReceived { from: user, to: creator, amount: 87.75M }
├─ RoyaltyPaid { payer: user, recipient, amount: 9.75M }
└─ PlatformFeePaid { payer: user, platform: 0x00..., amount: 2.5M }
```

---

## Component Communication

### Message Flow: Frontend Components

```
┌─ Page: Upload.tsx
│  ├─ Imports: useVoiceRegister, backendApi
│  ├─ User Action: Select audio file
│  │  └─ Call: backendApi.processVoiceModel()
│  │     └─ HTTP POST → Backend → Walrus → Returns walrusUri
│  │
│  └─ User Action: Click "Register"
│     └─ Call: registerVoice() from useVoiceRegister
│        └─ Create Tx → Sign → Broadcast → Sui Blockchain
│

┌─ Hook: useVoiceRegister()
│  ├─ Imports: useSignAndExecuteTransaction, useSuiClient, CONTRACTS
│  ├─ Function: registerVoice(data)
│  │  ├─ Build Transaction
│  │  ├─ Call moveCall({target, arguments})
│  │  ├─ signAndExecute({transaction: tx})
│  │  ├─ waitForTransaction(digest)
│  │  └─ Return: {success, transactionHash}
│  │
│  └─ Used By: Upload.tsx, Dashboard.tsx
│

┌─ Hook: usePayForInference()
│  ├─ Imports: useSignAndExecuteTransaction, CONTRACTS
│  ├─ Function: payForInference(options)
│  │  ├─ Calculate breakdown (local)
│  │  ├─ Build Transaction
│  │  ├─ moveCall("payment::pay_with_royalty_split", {...})
│  │  ├─ signAndExecute()
│  │  └─ Return: {success, transactionHash}
│  │
│  └─ Used By: Marketplace.tsx
│

┌─ Hook: useVoicesWithWalrusMetadata()
│  ├─ Imports: useSuiClient, fetchManifestFromUri, parseMoveString
│  ├─ Function: Fetch voices for array of addresses
│  │  ├─ FOR EACH address:
│  │  │  ├─ suiClient.getOwnedObjects({owner: address, filter: VoiceType})
│  │  │  ├─ Parse Move object fields
│  │  │  ├─ IF walrus URI:
│  │  │  │  ├─ fetchManifestFromUri(modelUri)
│  │  │  │  ├─ Extract meta.json
│  │  │  │  └─ Create preview URL
│  │  │  └─ Return enriched VoiceWithWalrusMetadata
│  │  │
│  │  └─ Return: {voices[], isLoading, error}
│  │
│  └─ Used By: Marketplace.tsx
│

┌─ Component: Marketplace.tsx
│  ├─ Imports: useVoicesWithWalrusMetadata, usePayForInference
│  ├─ On Load:
│  │  ├─ Get voice addresses from registry
│  │  ├─ Call useVoicesWithWalrusMetadata(addresses)
│  │  └─ Wait for voices to load
│  │
│  ├─ Render: Voice cards with preview
│  │  ├─ Show: Name, description, price, preview audio
│  │  └─ Button: "License & Use"
│  │
│  ├─ On Click:
│  │  ├─ Show payment breakdown
│  │  ├─ Call usePayForInference.payForInference()
│  │  ├─ Wait for transaction
│  │  └─ Enable TTS generation
│  │
│  └─ On TTS:
│     ├─ Call backendApi.generateTTS(modelUri, text)
│     ├─ Receive audio blob
│     └─ Play in browser
```

### Message Flow: Frontend ↔ Backend

```
┌─ Client (React)                    ┌─ Server (FastAPI)
│                                    │
├─ POST /api/voice/process           ├─ @app.post("/api/voice/process")
│  Headers: FormData                 │ Request: audio file + metadata
│  Body: {audio, name, owner, ...}   │  │
│                                    │  ├─ voice_model.process_voice_model()
│                                    │  ├─ voice_model.normalize_audio()
│                                    │  ├─ voice_model.generate_embedding()
│                                    │  ├─ voice_model.create_voice_bundle()
│                                    │  ├─ walrus.upload_to_walrus()
│                                    │  └─ Return: {walrusUri, ...}
│  ◄──────────────────────────────────
│  Response: 200 OK + JSON
│
├─ POST /api/tts/generate             ├─ @app.post("/api/tts/generate")
│  Headers: Content-Type: application/json │ Request: {modelUri, text, account}
│  Body: {...}                        │  │
│                                    │  ├─ walrus.verify_walrus_access()
│                                    │  ├─ walrus.download_file() [x3]
│                                    │  ├─ (Optional) Call Chatterbox
│                                    │  └─ Return: audio/wav
│  ◄──────────────────────────────────
│  Response: audio/wav blob
│
├─ POST /api/payment/breakdown        ├─ @app.post("/api/payment/breakdown")
│  Body: {amount}                    │ Request: amount
│                                    │  │
│                                    │  ├─ Calculate: platform_fee, royalty
│                                    │  └─ Return: breakdown JSON
│  ◄──────────────────────────────────
│  Response: 200 OK + JSON
│
├─ POST /api/walrus/download          ├─ @app.post("/api/walrus/download")
│  Body: {uri, filename, account}    │ Request: URI + filename
│                                    │  │
│                                    │  ├─ walrus.download_file()
│                                    │  └─ Return: file bytes
│  ◄──────────────────────────────────
│  Response: file content
```

### Message Flow: Blockchain Integration

```
┌─ Frontend (React/TypeScript)       ┌─ Sui Blockchain
│                                    │
├─ Create Transaction:               ├─
│  const tx = new Transaction()      │
│  tx.moveCall({                     │
│    target: "0x1ad12.../register",  │
│    arguments: [...]                │
│  })                                │
│                                    │
├─ useSignAndExecuteTransaction()    ├─
│  ├─ Show wallet UI                 │
│  ├─ User signs                     │
│  └─ Return signed tx               │
│                                    │
├─ Broadcast to Sui blockchain:      ├─ Transaction enters mempool
│  suiClient.executeTransaction()    │
│                                    │
├─ Wait for confirmation:            ├─ Validators execute
│  suiClient.waitForTransaction()    │  ├─ Call Move function
│                                    │  ├─ Create VoiceIdentity object
│                                    │  ├─ Store in blockchain state
│                                    │  └─ Emit event
│                                    │
│  ◄──────────────────────────────────
│  Transaction digest + result       │
│                                    │
└─ Display success message           └─
   "Voice registered on-chain!"
```

---

## State Management

### React Hook State Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   WalletProvider (Context)                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • currentAccount (from wallet extension)            │   │
│  │ • suiClient (JSON-RPC client)                       │   │
│  │ • signAndExecuteTransaction (wallet function)      │   │
│  │ • autoConnect enabled                               │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────┬──────────────────────────────────────────────┘
               │
               ├─ useSuiWallet()
               │  ├─ Gets: isConnected, address, account, suiClient
               │  └─ Returns: Current wallet state
               │
               ├─ useVoiceMetadata(ownerAddress)
               │  ├─ State: {metadata, isLoading, error}
               │  ├─ Effect: Query VoiceIdentity objects
               │  └─ Auto-refresh on ownerAddress change
               │
               ├─ useVoicesWithWalrusMetadata(addresses[])
               │  ├─ State: {voices[], isLoading, error}
               │  ├─ Effects: Fetch all voice data
               │  ├─ Enrichment: Add Walrus metadata
               │  └─ Cleanup: Revoke blob URLs on unmount
               │
               ├─ useVoiceRegister()
               │  ├─ State: {isRegistering}
               │  ├─ Function: registerVoice(data)
               │  └─ Returns: {success, transactionHash}
               │
               └─ usePayForInference()
                  ├─ State: {isPaying}
                  ├─ Function: payForInference(options)
                  └─ Returns: {success, transactionHash}
```

### Backend State (Stateless, but persistent storage)

```
┌─ Runtime State (Per Request)
│  ├─ Current request context
│  ├─ Temporary file handles
│  └─ Processing job state
│
└─ Persistent State
   ├─ LOCAL MODE: backend/storage/walrus/
   │  ├─ blobs/{blob_id_1}.bin
   │  ├─ blobs/{blob_id_2}.bin
   │  ├─ meta/{blob_id_1}.json
   │  └─ meta/{blob_id_2}.json
   │
   └─ REMOTE MODE: Walrus network
      ├─ Publisher stores blobs
      └─ Aggregators serve them
```

### Local Storage (Browser)

```
localStorage keys:
│
├─ voicevault_voice_registry
│  └─ Value: JSON array of {address, name, registeredAt}
│
├─ React Query cache (auto-managed)
│  ├─ Voice metadata queries
│  ├─ Balance queries
│  └─ (Auto-cleared by React Query stale time)
│
└─ Sui dApp Kit state
   ├─ Connected wallet address
   ├─ Selected account
   └─ Recent transactions (for quick lookup)

Purpose: Persist user selections & cached data across sessions
Clear: Browser DevTools > Application > Clear Storage
```

### Transaction State During Payment

```
BEFORE Payment:
├─ User Account: {balance: 1 SUI, coins: [coin1, coin2, ...]}
└─ Creator Account: {balance: 100 SUI}

DURING Transaction:
├─ User creates paymentCoin object (reserved)
├─ Transaction sent to blockchain
├─ Validators executing (in mempool)
└─ State changing...

AFTER Success:
├─ User Account: {balance: 0 SUI, coins: [coin2, ...]} (coin1 consumed)
├─ Creator Account: {balance: 100.087375 SUI} (received)
├─ Platform Account: {balance: X + 0.0025 SUI}
├─ Royalty Recipient: {balance: Y + 0.009625 SUI}
└─ Events stored on-chain (immutable)

ALL CHANGES ATOMIC: Transaction either all succeeds or all fails
NO PARTIAL UPDATES: Money can't get lost mid-transaction
```

---

## Flow Diagrams Summary

| Flow | Trigger | Duration | Outcome |
|------|---------|----------|---------|
| **Audio Upload** | User selects file | 2-10s | walrusUri returned |
| **Voice Registration** | User clicks "Register" | 3-5s | Object on blockchain |
| **Voice Discovery** | User opens marketplace | 1-5s (per voice) | Metadata + preview loaded |
| **Payment Split** | User buys voice | 3-5s | Funds distributed 3-way |
| **TTS Generation** | User enters text | 0.5-2s | Audio blob returned |

All flows are **asynchronous**, **non-blocking**, and **provide user feedback** via toasts/notifications.

