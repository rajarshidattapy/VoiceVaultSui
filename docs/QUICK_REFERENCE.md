# VoiceVault Sui - Quick Reference Guide

## Project Overview

**Name**: VoiceVault Sui  
**Tagline**: "Own Your Voice. Earn Forever."  
**Status**: MVP (Sui testnet)  
**Type**: Web3 Voice Marketplace with AI & Blockchain

## Key Statistics

- **Frontend**: React 18 + TypeScript + Vite
- **Backend**: Python FastAPI (5 core endpoints)
- **Blockchain**: Sui Move (2 modules: voice_identity, payment)
- **Storage**: Walrus (content-addressed blob storage)
- **Total Lines**: ~3000 LOC (excluding node_modules)

---

## Architecture at a Glance

```
┌──────────────────┐
│   React Frontend │
│   (Vite)         │
└────────┬─────────┘
         │ HTTP
         ▼
┌──────────────────┐      ┌──────────────────┐
│  FastAPI Backend │◄────►│  Walrus Storage  │
│  (Voice Process) │      │  (Blobs)         │
└────────┬─────────┘      └──────────────────┘
         │ JSON-RPC
         ▼
┌──────────────────┐
│  Sui Blockchain  │
│  (Voice Owned    │
│   + Payments)    │
└──────────────────┘
```

---

## Core File Locations

### Frontend
| File | Purpose |
|------|---------|
| `frontend/src/hooks/useVoiceRegister.ts` | Register voice on-chain |
| `frontend/src/hooks/usePayForInference.ts` | Execute payment with splits |
| `frontend/src/hooks/useVoicesWithWalrusMetadata.ts` | Fetch voices + storage metadata |
| `frontend/src/lib/contracts.ts` | Sui contract constants |
| `frontend/src/lib/walrus.ts` | Walrus blob client |
| `frontend/src/lib/api.ts` | Backend REST client |
| `frontend/src/contexts/WalletContext.tsx` | Sui wallet provider |

### Backend
| File | Purpose |
|------|---------|
| `backend/server.py` | FastAPI server (5 endpoints) |
| `backend/voice_model.py` | Audio processing pipeline |
| `backend/walrus.py` | Walrus storage integration |
| `backend/shelby.py` | Backward compatibility layer |

### Smart Contracts
| File | Purpose |
|------|---------|
| `voice_vault_sui/sources/voice_identity.move` | Voice ownership object |
| `voice_vault_sui/sources/payment.move` | Payment split logic (2.5% platform, 10% royalty, 87.5% creator) |

### Documentation
| File | Purpose |
|------|---------|
| `docs/README.md` | Project overview & features |
| `docs/sui.md` | Sui integration guide |
| `docs/WALRUS.md.md` | Walrus storage architecture |
| `docs/integration.md` | API setup & endpoints |

---

## Key Endpoints (Backend)

```
POST /api/voice/process
  Input: audio file + metadata
  Output: {walrusUri, previewUrl}
  Purpose: Process audio → upload to Walrus

POST /api/tts/generate
  Input: modelUri + text
  Output: audio blob
  Purpose: Generate speech in voice

POST /api/payment/breakdown
  Input: amount
  Output: {platformFee, royalty, creator}
  Purpose: Calculate payment splits

POST /api/walrus/upload
  Input: bundleFiles
  Output: {walrusUri, manifestBlobId}
  Purpose: Direct Walrus upload

POST /api/walrus/download
  Input: uri + filename
  Output: file bytes
  Purpose: Download from Walrus manifest
```

---

## On-Chain Transactions (Smart Contracts)

### 1. Register Voice
```
Function: voice_identity::register_voice
Input: name, modelUri, rights, pricePerUse
Effect: Creates VoiceIdentity object owned by caller
Output: Object ID on blockchain
```

### 2. Pay for Voice Usage
```
Function: payment::pay_with_royalty_split
Input: amount, creator, platform, royalty_recipient
Effect: Splits & transfers SUI coins
  - 2.5% to platform
  - 10% to royalty recipient
  - 87.5% to creator
Emits: 3 events (PaymentReceived, RoyaltyPaid, PlatformFeePaid)
```

---

## Data Models

### VoiceIdentity (On-Chain)
```typescript
{
  id: UID,                    // Unique identifier
  owner: address,             // Creator's Sui address
  name: String,               // "John's Voice"
  model_uri: String,          // "walrus://blob_id"
  rights: String,             // "Commercial" | "Personal"
  price_per_use: u64,         // Cost in MIST
  created_at: u64             // Timestamp
}
```

### Voice Manifest (Walrus)
```json
{
  "voiceId": "voice-123",
  "owner": "0xuser...",
  "blobs": {
    "embedding.bin": {
      "blobId": "...",
      "size": 1024,
      "chunked": false
    },
    "config.json": {...},
    "meta.json": {...},
    "preview.wav": {...}
  },
  "walrusUri": "walrus://blob_id",
  "version": 1
}
```

---

## Fee Structure

```
Input: 1 SUI (1,000,000,000 MIST)

Platform Fee:    2.5%  =  25,000,000 MIST → Platform
Remaining:    975,000,000 MIST
Royalty:       10%   =  97,500,000 MIST → Royalty Recipient
Creator:               = 877,500,000 MIST → Creator
```

**Constants** (defined in Move + frontend):
- `PLATFORM_FEE_BPS`: 250 (basis points)
- `ROYALTY_BPS`: 1000 (basis points)

---

## State Management Strategy

```
┌─ BLOCKCHAIN STATE (Immutable)
├─ VoiceIdentity objects (per creator)
├─ Coin balances (per address)
└─ Transaction history (events)

┌─ WALRUS STATE (Content-Addressed)
├─ Voice embeddings
├─ Metadata & configs
└─ Preview audio

┌─ BROWSER STATE (Transient)
├─ Connected wallet
├─ Voice registry (localStorage)
└─ React Query cache

┌─ BACKEND STATE (Ephemeral)
├─ Active processing jobs
├─ Temporary files during upload
└─ Request context
```

---

## Common Workflows

### Workflow 1: Create & Register Voice

```
User → Upload Audio
  ↓
Backend: Normalize → Embed → Bundle
  ↓
Walrus: Store files → Create manifest
  ↓
Backend: Return walrusUri
  ↓
Frontend: Display preview
  ↓
User → Click "Register On-Chain"
  ↓
Frontend: Create transaction
  ↓
User: Sign in wallet
  ↓
Sui: Execute register_voice()
  ↓
Success: VoiceIdentity created
```

### Workflow 2: Use Voice & Pay

```
User → Select marketplace voice
  ↓
Frontend: Show payment breakdown
  ↓
User → Click "License & Use"
  ↓
Frontend: Create payment transaction
  ↓
User: Sign in wallet
  ↓
Sui: Execute pay_with_royalty_split()
  ↓
Funds distributed (3-way split)
  ↓
Frontend: Call TTS endpoint
  ↓
Backend: Download voice from Walrus
  ↓
Generate speech (preview or Chatterbox)
  ↓
Return audio to user
```

### Workflow 3: Browse Marketplace

```
Frontend: Query voice registry
  ↓
For each registered address:
  ├─ Fetch VoiceIdentity from Sui
  ├─ Extract model_uri (walrus://)
  ├─ Download manifest from Walrus
  ├─ Extract meta.json
  └─ Create preview audio URL
  ↓
Display voice cards
```

---

## Environment Variables

### Frontend (`.env`)
```env
VITE_API_URL=http://localhost:3000
VITE_WALRUS_AGGREGATOR_URL=http://localhost:3000/api/walrus
VITE_SUI_VOICE_REGISTRY_ID=0x
```

### Backend (`.env`)
```env
# Storage
WALRUS_STORAGE_MODE=local  # or "remote"
WALRUS_PUBLISHER_URL=https://publisher.walrus-testnet.walrus.space
WALRUS_AGGREGATOR_URL=http://localhost:3000/api/walrus
WALRUS_EPOCHS=5
WALRUS_DELETABLE=true

# API
PORT=3000
```

---

## Development Checklist

- [ ] Install Node.js 18+, Python 3.8+, FFmpeg
- [ ] Clone repository
- [ ] Frontend: `npm install`, `npm run dev` (port 5173)
- [ ] Backend: `pip install -r requirements.txt`, `python server.py` (port 3000)
- [ ] Sui CLI: Configure wallet
- [ ] Connect to Sui testnet
- [ ] Deploy contracts: `sui client call --function init_registry ...`
- [ ] Update `PACKAGE_ID` in frontend
- [ ] Open browser: http://localhost:5173

---

## Common Issues & Solutions

### Issue: "Cannot connect to Sui wallet"
**Solution**: Install Sui Wallet browser extension, ensure network = testnet

### Issue: "Voice processing takes too long"
**Solution**: Check FFmpeg installed (`which ffmpeg`), check backend logs

### Issue: "Preview audio not playing"
**Solution**: Verify Walrus aggregator URL in .env, check CORS settings

### Issue: "Transaction failed"
**Solution**: 
- Check wallet has SUI balance
- Verify contract package ID matches deployed version
- Check transaction limits / gas

### Issue: "Walrus blob not found"
**Solution**:
- Verify WALRUS_STORAGE_MODE matches actual setup
- Check local storage directory exists: `backend/storage/walrus/`
- For remote: verify publisher/aggregator URLs are accessible

---

## Performance Tips

1. **Voice Processing**: Audio normalization is bottleneck (FFmpeg)
   - Optimize: GPU acceleration if available
   - Cache: Normalize common formats once

2. **Walrus Uploads**: Large files (embeddings) may be chunked
   - Monitor: MAX_BLOB_SIZE setting (10MB default)
   - Optimize: Compress before upload if possible

3. **Frontend Marketplace**: Loading all voices is O(n)
   - Optimize: Paginate or use infinite scroll
   - Cache: Use React Query with stale-while-revalidate

4. **TTS Generation**: Chatterbox API is network-dependent
   - Optimize: Local TTS model if possible
   - Cache: Store generated audio results

---

## Security Considerations

### Current Status
- ✅ On-chain ownership verified
- ✅ Payment splits immutable (Move contract)
- ⚠️ Access control is permissive
- ⚠️ No license enforcement

### Recommendations
1. Implement real access control in `verify_walrus_access()`
2. Add rate limiting to TTS endpoint
3. Restrict CORS to trusted origins
4. Validate backend payment before TTS
5. Audit Move contract security
6. Use testnet for all testing before mainnet

---

## Deployment

### Local Development
```bash
# Terminal 1: Frontend
cd frontend && npm run dev  # http://localhost:5173

# Terminal 2: Backend
cd backend && python server.py  # http://localhost:3000
```

### Production (Render)
See `render.yaml` for Render.com deployment configuration

### Production (Docker)
```bash
# Backend
docker build -f backend/Dockerfile -t voicevault-backend .
docker run -e WALRUS_STORAGE_MODE=remote -p 3000:3000 voicevault-backend

# Frontend
docker build -f frontend/Dockerfile -t voicevault-frontend .
docker run -p 80:80 voicevault-frontend
```

---

## Testing Checklist

### Unit Tests
- [ ] Payment calculation (fee, royalty, creator split)
- [ ] Audio normalization (FFmpeg output)
- [ ] Walrus URI parsing

### Integration Tests
- [ ] Voice upload end-to-end
- [ ] Voice registration transaction
- [ ] Payment split transaction
- [ ] Voice marketplace loading

### Manual Tests
- [ ] Upload audio, see preview
- [ ] Register voice, check blockchain
- [ ] Buy voice, see payment split
- [ ] Generate TTS, hear output
- [ ] Check creator balance increased

---

## Useful Commands

### Sui CLI
```bash
sui client active-address
sui client gas
sui client call --function init_registry --package 0x... --module voice_identity
sui client query-events --type PaymentReceived
```

### Backend
```bash
# Start server
python backend/server.py

# Check logs
tail -f backend/logs.txt

# Process single audio file
curl -X POST http://localhost:3000/api/voice/process \
  -F "audio=@sample.wav" \
  -F "name=Test" \
  -F "owner=0xabc..." \
  -F "voiceId=test-123"
```

### Frontend
```bash
npm run dev          # Start dev server
npm run build        # Build for production
npm run lint         # Check for errors
npm run preview      # Preview production build
```

---

## Architecture Decision Records (ADRs)

### ADR 1: Why Walrus over IPFS?
- Walrus = Sui-native (single blockchain)
- IPFS = Decentralized but requires external infrastructure
- Walrus offers: Free reads via Aggregators, on-chain Blob objects

### ADR 2: Why Move over Rust?
- Move = Sui's native language, safer resource model
- Rust = Powerful but steeper learning curve
- Move guarantees no double-spends, no use-after-free

### ADR 3: Why FastAPI over Node.js?
- FastAPI = Python ecosystem (ML libraries, audio processing)
- Node.js = Simpler JavaScript but fewer ML libraries
- Python enables real embedding models (Resemblyzer, GE2E, etc.)

### ADR 4: Why Embed vs Normalize?
- Current: Placeholder hash-based embedding (demo)
- Production: Use trained model (Resemblyzer, GE2E, speaker encoder)
- Reason: Real embeddings enable voice similarity, cloning, recognition

---

## Metrics to Track

```
User Metrics:
├─ Total voices registered
├─ Total earnings (all-time, last 30 days)
├─ Average price per use
└─ Monthly active users

Technical Metrics:
├─ Audio processing time (avg, p95, p99)
├─ Walrus upload latency
├─ TTS generation time
├─ Smart contract execution gas
└─ Backend response times

Business Metrics:
├─ Platform fees collected
├─ Creator payouts
├─ Voice usage count
└─ Marketplace growth rate
```

---

## Next Steps

### Phase 1 (MVP - Current)
- ✅ Voice registration
- ✅ Walrus storage
- ✅ Payment splits
- ✅ Marketplace browsing

### Phase 2 (Enhancement)
- [ ] Real embedding model
- [ ] Real TTS synthesis
- [ ] License enforcement
- [ ] Creator reputation

### Phase 3 (Scale)
- [ ] Multi-language support
- [ ] Voice effects & editing
- [ ] Creator dashboard analytics
- [ ] Mainnet deployment

### Phase 4 (Ecosystem)
- [ ] NFT marketplace
- [ ] Cross-chain interop
- [ ] API monetization
- [ ] Creator governance

---

## Resources

**Documentation**:
- Sui Docs: https://docs.sui.io
- Walrus Docs: https://docs.walrus.xyz
- Move Guide: https://move-language.github.io

**Tools**:
- Sui Explorer: https://suiscan.xyz (testnet)
- Walrus Publisher: https://publisher.walrus-testnet.walrus.space
- dApp Kit: https://sdk.mysten.com

**Community**:
- Sui Discord: https://discord.gg/sui
- Walrus Community: https://community.walrus.xyz

