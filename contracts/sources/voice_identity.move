module voice_vault_sui::voice_identity {
    use std::string::String;
    use std::vector;

    /// Global on-chain registry of all registered voice owner addresses.
    /// Created once via init() and shared so any transaction can append to it.
    public struct VoiceRegistry has key {
        id: UID,
        voice_owners: vector<address>,
    }

    /// Voice NFT object
    public struct VoiceIdentity has key, store {
        id: UID,
        owner: address,
        name: String,
        model_uri: String, // walrus://<manifest_blob_id>
        rights: String,
        price_per_use: u64,
        created_at: u64
    }

    /// Published once: creates the global VoiceRegistry shared object.
    fun init(ctx: &mut TxContext) {
        transfer::share_object(VoiceRegistry {
            id: object::new(ctx),
            voice_owners: vector::empty(),
        });
    }

    /// Register a voice and append the owner's address to the global registry.
    /// ONE voice per user is enforced externally (checked in the frontend).
    public fun register_voice(
        registry: &mut VoiceRegistry,
        name: String,
        model_uri: String,
        rights: String,
        price_per_use: u64,
        ctx: &mut TxContext
    ): VoiceIdentity {
        let sender = tx_context::sender(ctx);
        let voice = VoiceIdentity {
            id: object::new(ctx),
            owner: sender,
            name,
            model_uri,
            rights,
            price_per_use,
            created_at: 0
        };
        vector::push_back(&mut registry.voice_owners, sender);
        voice
    }

    /// Delete a voice and remove the owner from the global registry.
    public fun delete_voice(
        registry: &mut VoiceRegistry,
        voice: VoiceIdentity,
        ctx: &mut TxContext
    ) {
        let sender = tx_context::sender(ctx);
        assert!(voice.owner == sender, 0);
        remove_owner(registry, sender);
        let VoiceIdentity { id, .. } = voice;
        object::delete(id);
    }

    /// Return all registered voice owner addresses.
    public fun get_voice_owners(registry: &VoiceRegistry): &vector<address> {
        &registry.voice_owners
    }

    /// Read helpers
    public fun get_metadata(voice: &VoiceIdentity):
        (address, String, String, String, u64, u64) {
        (
            voice.owner,
            voice.name,
            voice.model_uri,
            voice.rights,
            voice.price_per_use,
            voice.created_at
        )
    }

    public fun get_voice_id(voice: &VoiceIdentity): ID {
        object::id(voice)
    }

    // ── Internal ──────────────────────────────────────────────────────────────

    fun remove_owner(registry: &mut VoiceRegistry, owner: address) {
        let owners = &mut registry.voice_owners;
        let len = vector::length(owners);
        let i = 0;
        while (i < len) {
            if (*vector::borrow(owners, i) == owner) {
                vector::remove(owners, i);
                return
            };
            i = i + 1;
        }
    }
}
