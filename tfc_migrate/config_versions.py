

def migrate(api_source, api_target, workspaces_map):
    print("Migrating config versions...")

    workspace_to_config_version_map = {}

    for workspace_id in workspaces_map:
        workspace_name = api_source.workspaces.show(workspace_id=workspace_id)\
            ["data"]["attributes"]["name"]

        # Fetch config versions for the existing workspace
        config_versions = api_source.config_versions.list(workspace_id)["data"]

        if config_versions:
            latest_config_version = config_versions[0]

            if latest_config_version["attributes"]["source"] == "tfe-api":
                # Build the new config version payload
                new_config_version_payload = {
                    "data": {
                        "type": "configuration-versions",
                        "attributes": {
                            "auto-queue-runs": latest_config_version\
                                ["attributes"]["auto-queue-runs"]
                        }
                    }
                }

                # Create a config version in the target organization
                new_config_version = api_target.config_versions.create(\
                    workspaces_map[workspace_id], new_config_version_payload)["data"]
                workspace_to_config_version_map[workspace_name] = \
                    new_config_version["id"]

    print("Config versions successfully migrated.")
    return workspace_to_config_version_map


# TODO: determine why this is different
def migrate_config_files(\
    api_target, workspace_to_config_version_map, workspace_to_file_path_map):
    for workspace_name in workspace_to_file_path_map:
        # NOTE: The workspace_to_file_path_map must be created ahead of time
        # with a format of {"workspace_name":"path/to/file"}

        # TODO: logging
        # Upload the config file to the target workspace
        api_target.config_versions.upload(\
            workspace_to_file_path_map[workspace_name], \
                workspace_to_config_version_map[workspace_name])
