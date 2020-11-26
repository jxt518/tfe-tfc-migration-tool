

# TODO: catch duplicates, clean up this file, optimize
def migrate(api_source, api_target, workspaces_map):
    workspace_to_configuration_version_map = {}

    for workspace_id in workspaces_map:
        workspace_name = api_source.workspaces.show(workspace_id=workspace_id)\
            ["data"]["attributes"]["name"]

        # Fetch configuration versions for the existing workspace
        configuration_versions = api_source.config_versions.list(workspace_id)["data"]

        if configuration_versions:
            latest_configuration_version = configuration_versions[0]

            if latest_configuration_version["attributes"]["source"] == "tfe-api":
                # Build the new configuration version payload
                new_configuration_version_payload = {
                    "data": {
                        "type": "configuration-versions",
                        "attributes": {
                            "auto-queue-runs": latest_configuration_version\
                                ["attributes"]["auto-queue-runs"]
                        }
                    }
                }

                # Create a configuration version in the new organization
                new_configuration_version = api_target.config_versions.create(\
                    workspaces_map[workspace_id], new_configuration_version_payload)["data"]
                workspace_to_configuration_version_map[workspace_name] = \
                    new_configuration_version["id"]

    return workspace_to_configuration_version_map


# TODO: determine why this is different
def migrate_config_files(\
    api_target, workspace_to_configuration_version_map, workspace_to_file_path_map):
    for workspace_name in workspace_to_file_path_map:
        # NOTE: The workspace_to_file_path_map must be created ahead of time
        # with a format of {"workspace_name":"path/to/file"}

        # Upload the configuration file to the new workspace
        api_target.config_versions.upload(\
            workspace_to_file_path_map[workspace_name], \
                workspace_to_configuration_version_map[workspace_name])
