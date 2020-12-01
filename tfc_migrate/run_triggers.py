

# TODO: catch duplicates, clean up this file, optimize
def migrate(api_source, api_target, workspaces_map):

    print("Migrating run triggers...")

    for workspace_id in workspaces_map:
        workspace_filters = [
            {
                "keys": ["run-trigger", "type"],
                "value": "inbound"
            }
        ]

        # Pull Run Triggers from the Old Workspace
        run_triggers = api_source.run_triggers.list(
            workspace_id, filters=workspace_filters,  page_size=100)["data"]

        if run_triggers:
            for run_trigger in run_triggers:
                source_workspace_id = run_trigger["relationships"]["sourceable"]["data"]["id"]

                # Build the new run trigger payload
                new_run_trigger_payload = {
                    "data": {
                        "relationships": {
                            "sourceable": {
                                "data": {
                                    "id": workspaces_map[source_workspace_id],
                                    "type": "workspaces"
                                }
                            }
                        }
                    }
                }

                # Add Run Triggers to the target Workspace
                api_target.run_triggers.create(
                    workspaces_map[workspace_id], new_run_trigger_payload)

    print("Run triggers successfully migrated.")
