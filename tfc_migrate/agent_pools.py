

# TODO: catch duplicates, clean up this file, optimize
def migrate(api_source, api_target, TFE_ORG_SOURCE, TFE_ORG_TARGET):
    print("Migrating agent pools...")

    # Fetch agent pools from existing org
    agent_pools = api_source.agents.list_pools()["data"]
    agent_pool_id = None

    if agent_pools:
        # Build the new agent pool payload
        new_agent_pool_payload = {
            "data": {
                "type": "agent-pools"
            }
        }

        new_org_agent_pools = api_target.agents.list_pools()["data"]
        if new_org_agent_pools:
            agent_pool_id = api_target.agents.list_pools()["data"][0]["id"]
        else:
            # Create Agent Pool in New Org
            agent_pool_id = api_target.agents.create_pool(TFE_ORG_TARGET)[
                "data"]["id"]

    print("Agent pools successfully migrated.")
    return agent_pool_id

# TODO: delete function w logging
