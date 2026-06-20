module voice_vault_sui::agent_identity {
    use std::string::String;

    public struct AgentIdentity has key, store {
        id: UID,
        owner: address,
        voice_id: ID,
        agent_name: String,
        config_uri: String,      // Walrus URI for full agent config JSON
        pricing_model: u64,      // price per call in MIST
        active: bool,
        created_at: u64,
    }

    public struct AgentCreated has copy, drop {
        agent_id: ID,
        owner: address,
        voice_id: ID,
    }

    public fun create_agent(
        voice_id: ID,
        agent_name: String,
        config_uri: String,
        pricing_model: u64,
        ctx: &mut TxContext
    ): AgentIdentity {
        let owner = tx_context::sender(ctx);
        let agent = AgentIdentity {
            id: object::new(ctx),
            owner,
            voice_id,
            agent_name,
            config_uri,
            pricing_model,
            active: true,
            created_at: 0,
        };
        sui::event::emit(AgentCreated {
            agent_id: object::id(&agent),
            owner,
            voice_id,
        });
        agent
    }

    public fun pause_agent(agent: &mut AgentIdentity, ctx: &mut TxContext) {
        assert!(agent.owner == tx_context::sender(ctx), 0);
        agent.active = false;
    }

    public fun resume_agent(agent: &mut AgentIdentity, ctx: &mut TxContext) {
        assert!(agent.owner == tx_context::sender(ctx), 0);
        agent.active = true;
    }

    public fun delete_agent(agent: AgentIdentity, ctx: &mut TxContext) {
        assert!(agent.owner == tx_context::sender(ctx), 0);
        let AgentIdentity { id, .. } = agent;
        object::delete(id);
    }

    public fun get_metadata(agent: &AgentIdentity): (address, ID, String, String, u64, bool) {
        (agent.owner, agent.voice_id, agent.agent_name, agent.config_uri, agent.pricing_model, agent.active)
    }

    public fun is_active(agent: &AgentIdentity): bool { agent.active }
    public fun owner(agent: &AgentIdentity): address { agent.owner }
}
