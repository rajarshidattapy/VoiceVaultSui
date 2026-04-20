module voice_vault_sui::x402_payment {
    use sui::object::{Self, UID, ID};
    use sui::tx_context::{Self, TxContext};
    use sui::transfer;
    use sui::coin::{Self, Coin};
    use sui::clock::{Self, Clock};
    use sui::event;

    // ── Structs ──────────────────────────────────────────────────────────────

    public struct UsagePass has key, store {
        id: UID,
        user: address,
        voice_id: ID,
        uses_remaining: u64,
        expires_at: u64,   // Unix ms
        created_at: u64,   // Unix ms
    }

    // ── Events ────────────────────────────────────────────────────────────────

    public struct UsagePassCreated has copy, drop {
        pass_id: ID,
        user: address,
        voice_id: ID,
        uses: u64,
        expires_at: u64,
    }

    public struct UsageConsumed has copy, drop {
        pass_id: ID,
        user: address,
        voice_id: ID,
        uses_remaining: u64,
    }

    // ── Error codes ───────────────────────────────────────────────────────────

    const ENoUsesRemaining: u64 = 0;
    const EPassExpired: u64    = 1;

    // ── Core functions ────────────────────────────────────────────────────────

    /// Pay for N uses of a voice. Splits royalties then mints UsagePass to caller.
    public fun create_usage_pass<T>(
        mut payment: Coin<T>,
        voice_id: ID,
        creator: address,
        platform: address,
        royalty_recipient: address,
        uses: u64,
        expires_in_ms: u64,
        clock: &Clock,
        ctx: &mut TxContext,
    ) {
        let total = coin::value(&payment);

        let platform_amount  = (total * 250) / 10_000;
        let royalty_amount   = ((total - platform_amount) * 1_000) / 10_000;
        let creator_amount   = total - platform_amount - royalty_amount;

        let platform_coin  = coin::split(&mut payment, platform_amount, ctx);
        let royalty_coin   = coin::split(&mut payment, royalty_amount, ctx);
        // remainder goes to creator
        let _ = creator_amount;

        transfer::public_transfer(platform_coin, platform);
        transfer::public_transfer(royalty_coin, royalty_recipient);
        transfer::public_transfer(payment, creator);

        let payer = tx_context::sender(ctx);
        let now   = clock::timestamp_ms(clock);

        let pass = UsagePass {
            id: object::new(ctx),
            user: payer,
            voice_id,
            uses_remaining: uses,
            expires_at: now + expires_in_ms,
            created_at: now,
        };

        event::emit(UsagePassCreated {
            pass_id: object::uid_to_inner(&pass.id),
            user: payer,
            voice_id,
            uses,
            expires_at: now + expires_in_ms,
        });

        transfer::transfer(pass, payer);
    }

    /// Decrement one use. Aborts if exhausted or expired.
    public fun consume_usage(pass: &mut UsagePass, clock: &Clock) {
        assert!(pass.uses_remaining > 0, ENoUsesRemaining);
        let now = clock::timestamp_ms(clock);
        assert!(now <= pass.expires_at, EPassExpired);

        pass.uses_remaining = pass.uses_remaining - 1;

        event::emit(UsageConsumed {
            pass_id: object::uid_to_inner(&pass.id),
            user: pass.user,
            voice_id: pass.voice_id,
            uses_remaining: pass.uses_remaining,
        });
    }

    /// Non-mutating access check (view).
    public fun has_access(pass: &UsagePass, clock: &Clock): bool {
        let now = clock::timestamp_ms(clock);
        pass.uses_remaining > 0 && now <= pass.expires_at
    }

    public fun uses_remaining(pass: &UsagePass): u64 { pass.uses_remaining }
    public fun expires_at(pass: &UsagePass): u64     { pass.expires_at }
    public fun voice_id(pass: &UsagePass): ID        { pass.voice_id }
}
