

def migrate(api_source, api_target, workspaces_map):

    print("Migrating run triggers...")

    # TODO: iron out all the naming in this file, it can be really confusing
    for workspace_id in workspaces_map:
        workspace_filters = [
            {
                "keys": ["run-trigger", "type"],
                "value": "inbound"
            }
        ]

        # Pull run triggers from the source workspace
        run_triggers = api_source.run_triggers.list(
            workspace_id, filters=workspace_filters,  page_size=100)["data"]

        if run_triggers:
            for run_trigger in run_triggers:
                source_workspace_id = run_trigger["relationships"]["sourceable"]["data"]["id"]
                target_workspace_id = workspaces_map[source_workspace_id]

                # TODO: check if this source / target combo already exists
                run_trigger_filters = [
                    {
                        "keys": ["run-trigger", "type"],
                        "value": "outbound"
                    }
                ]

                existing_run_triggers = api_target.run_triggers.list(\
                    target_workspace_id, filters=run_trigger_filters)["data"]

                # TODO: Is this the right logic? Is the naming just confusing?
                source_workspace_ids = [trigger["relationships"]["sourceable"]["data"]["id"]\
                    for trigger in existing_run_triggers]

                if target_workspace_id in source_workspace_ids:
                    print(f"\t run trigger for target workspace ID %s already exists, skipping..." \
                        % target_workspace_id)
                    continue

                # Build the new run trigger payload
                new_run_trigger_payload = {
                    "data": {
                        "relationships": {
                            "sourceable": {
                                "data": {
                                    "id": target_workspace_id,
                                    "type": "workspaces"
                                }
                            }
                        }
                    }
                }

                # Add run triggers to the target Workspace
                api_target.run_triggers.create(
                    workspaces_map[workspace_id], new_run_trigger_payload)

                print(f"\t run trigger created for source workspace ID %s to target workspace ID %s..." \
                    % (source_workspace_id, target_workspace_id))

    print("Run triggers successfully migrated.")
