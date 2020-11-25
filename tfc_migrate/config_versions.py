

def migrate(api_target, workspace_to_configuration_version_map, workspace_to_file_path_map):
    for workspace_name in workspace_to_file_path_map:
        # NOTE: The workspace_to_file_path_map must be created ahead of time
        # with a format of {"workspace_name":"path/to/file"}

        # Upload the configuration file to the new workspace
        api_target.config_versions.upload(\
            workspace_to_file_path_map[workspace_name], \
                workspace_to_configuration_version_map[workspace_name])
