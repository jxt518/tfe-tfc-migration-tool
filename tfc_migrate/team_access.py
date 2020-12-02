

def migrate(api_source, api_target, workspaces_map, teams_map):

    print("Migrating team access...")

    for workspace_id in workspaces_map:
        # Set proper workspace team filters to pull team access for each workspace
        workspace_team_filters = [
            {
                "keys": ["workspace", "id"],
                "value": workspace_id
            }
        ]

        # TODO: list existing team access to catch duplicates rather than try/except
        # TODO: optimize the payload creation

        # Pull teams from the old workspace
        workspace_teams = api_source.team_access.list(filters=workspace_team_filters)["data"]
        for workspace_team in workspace_teams:
            if workspace_team["attributes"]["access"] == "custom":
                # Build the new team access payload
                new_workspace_team_payload = {
                    "data": {
                        "attributes": {
                            "access": workspace_team["attributes"]["access"],
                            "runs": workspace_team["attributes"]["runs"],
                            "variables": workspace_team["attributes"]["variables"],
                            "state-versions": workspace_team["attributes"]["state-versions"],
                            "plan-outputs": "none",
                            "sentinel-mocks": workspace_team["attributes"]["sentinel-mocks"],
                            "workspace-locking": workspace_team["attributes"]["workspace-locking"]
                        },
                        "relationships": {
                            "workspace": {
                                "data": {
                                    "type": "workspaces",
                                    "id": workspaces_map[workspace_id]
                                }
                            },
                            "team": {
                                "data": {
                                    "type": "teams",
                                    "id": teams_map\
                                        [workspace_team["relationships"]["team"]["data"]["id"]]
                                }
                            }
                        },
                        "type": "team-workspaces"
                    }
                }

                try:
                    # Create the Team Workspace Access map for the target workspace
                    api_target.team_access.add_team_access(new_workspace_team_payload)
                except Exception as err:
                    # TODO: what is this really doing?
                    print(err)
            else:
                # Build the new team access payload
                new_workspace_team_payload = {
                    "data": {
                        "attributes": {
                            "access": workspace_team["attributes"]["access"],
                        },
                        "relationships": {
                            "workspace": {
                                "data": {
                                    "type": "workspaces",
                                    "id": workspaces_map[workspace_id]
                                }
                            },
                            "team": {
                                "data": {
                                    "type": "teams",
                                    "id": teams_map\
                                        [workspace_team["relationships"]["team"]["data"]["id"]]
                                }
                            }
                        },
                        "type": "team-workspaces"
                    }
                }

                try:
                    # Create the Team Workspace Access map for the target workspace
                    api_target.team_access.add_team_access(new_workspace_team_payload)
                except Exception as err:
                    # TODO: what is this really doing?
                    print(err)

    print("Team access successfully migrated.")
