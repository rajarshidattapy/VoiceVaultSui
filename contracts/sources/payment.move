module voice_vault_sui::payment {

    use sui::coin::{Self, Coin};
    use sui::event;

    const PLATFORM_FEE_BPS: u64 = 250;
    const ROYALTY_BPS: u64 = 1000;
    const DENOM: u64 = 10000;

    // ── On-chain license object ───────────────────────────────────────────────

    /// Proof-of-purchase minted to the buyer on every successful payment.
    /// The backend verifies ownership of this object instead of trusting its DB.
    public struct LicensePass has key, store {
        id: UID,
        voice_id: ID,    // VoiceIdentity object ID that was licensed
        buyer: address,
        issued_at: u64,
    }

    // ── Events ────────────────────────────────────────────────────────────────

    public struct LicenseIssued has copy, drop {
        voice_id: ID,
        buyer: address,
    }

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

    // ── Payment functions ─────────────────────────────────────────────────────

    /// Split payment among platform, royalty recipient, and creator, then mint
    /// a LicensePass and transfer it to the buyer.
    public fun pay_with_royalty_split<T>(
        mut payment: Coin<T>,
        voice_id: ID,
        creator: address,
        platform: address,
        royalty_recipient: address,
        ctx: &mut TxContext
    ) {
        let sender = tx_context::sender(ctx);
        let total = coin::value(&payment);

        assert!(total > 0, 0);

        let platform_fee = total * PLATFORM_FEE_BPS / DENOM;
        let remaining = total - platform_fee;
        let royalty = remaining * ROYALTY_BPS / DENOM;

        let platform_coin = coin::split(&mut payment, platform_fee, ctx);
        let royalty_coin = coin::split(&mut payment, royalty, ctx);

        transfer::public_transfer(platform_coin, platform);
        transfer::public_transfer(royalty_coin, royalty_recipient);
        transfer::public_transfer(payment, creator);

        // Mint LicensePass and send to buyer — backend verifies this instead of
        // trusting centralised DB logic.
        let license = LicensePass {
            id: object::new(ctx),
            voice_id,
            buyer: sender,
            issued_at: 0,
        };
        transfer::public_transfer(license, sender);

        event::emit(LicenseIssued { voice_id, buyer: sender });

        event::emit(PlatformFeePaid {
            payer: sender,
            platform,
            amount: platform_fee
        });

        event::emit(RoyaltyPaid {
            payer: sender,
            recipient: royalty_recipient,
            amount: royalty
        });

        event::emit(PaymentReceived {
            from: sender,
            to: creator,
            amount: total - platform_fee - royalty
        });
    }

    public fun pay_full_to_creator<T>(
        payment: Coin<T>,
        creator: address,
        ctx: &mut TxContext
    ) {
        let sender = tx_context::sender(ctx);
        let amount = coin::value(&payment);

        transfer::public_transfer(payment, creator);

        event::emit(PaymentReceived {
            from: sender,
            to: creator,
            amount
        });
    }

    public fun calculate_payment_breakdown(
        amount: u64
    ): (u64, u64, u64) {
        let platform_fee = amount * PLATFORM_FEE_BPS / DENOM;
        let remaining = amount - platform_fee;
        let royalty = remaining * ROYALTY_BPS / DENOM;
        let creator_amount = remaining - royalty;

        (platform_fee, royalty, creator_amount)
    }

    // ── View helpers ──────────────────────────────────────────────────────────

    public fun license_voice_id(pass: &LicensePass): ID { pass.voice_id }
    public fun license_buyer(pass: &LicensePass): address { pass.buyer }
}
