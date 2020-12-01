import os
import ast
import argparse
from terrasnek.api import TFC
from tfc_migrate import \
    workspaces, teams, policies, policy_sets, registry_modules, \
        ssh_keys, config_versions, notification_configs, team_access, \
            agent_pools, workspace_vars, run_triggers, state_versions, \
                policy_set_params

# TODO: review imports like urllib / ast
# TODO: use a logger instead of print statements
# TODO: have each module handle it's own output writes
# TODO: confirm all functions are idempotent
# TODO: try not to repeat the try/except blocks
# TODO: logging should have tabs to be more readable
# TODO: create a base migrate class w/ a logger
# TODO: clean up TFE_VCS_CONNECTION_MAP


# Source Org
TFE_TOKEN_SOURCE = os.getenv("TFE_TOKEN_SOURCE", None)
TFE_URL_SOURCE = os.getenv("TFE_URL_SOURCE", None)
TFE_ORG_SOURCE = os.getenv("TFE_ORG_SOURCE", None)

# Target Org
TFE_TOKEN_TARGET = os.getenv("TFE_TOKEN_TARGET", None)
TFE_URL_TARGET = os.getenv("TFE_URL_TARGET", None)
TFE_ORG_TARGET = os.getenv("TFE_ORG_TARGET", None)
TFE_VCS_CONNECTION_MAP = ast.literal_eval(os.getenv("TFE_VCS_CONNECTION_MAP", None))


def print_output(\
    teams_map, ssh_keys_map, ssh_key_name_map, workspaces_map, \
        workspace_to_ssh_key_map, workspace_to_config_version_map, \
            policies_map, policy_sets_map, sensitive_policy_set_parameter_data, \
                sensitive_variable_data):
    lines = [
        "MIGRATION MAPS:",
        "teams_map: %s\n\n" % teams_map,
        "ssh_keys_map: %s\n\n" % ssh_keys_map,
        "ssh_key_name_map: %s\n\n" % ssh_key_name_map,
        "workspaces_map: %s\n\n" % workspaces_map,
        "workspace_to_ssh_key_map: %s\n\n" % workspace_to_ssh_key_map,
        "workspace_to_config_version_map: %s\n\n" % workspace_to_config_version_map,
        "policies_map: %s\n\n" % policies_map,
        "policy_sets_map: %s\n\n" % policy_sets_map,
        "sensitive_policy_set_parameter_data: %s\n\n" % sensitive_policy_set_parameter_data,
        "sensitive_variable_data: %s\n\n" % sensitive_variable_data
    ]

    for line in lines:
        print(line)


def write_output(\
    teams_map, ssh_keys_map, ssh_key_name_map, workspaces_map, \
        workspace_to_ssh_key_map, workspace_to_config_version_map, \
            policies_map, policy_sets_map, sensitive_policy_set_parameter_data, \
                sensitive_variable_data):

        lines = [
            "teams_map: %s\n\n" % teams_map,
            "ssh_keys_map: %s\n\n" % ssh_keys_map,
            "ssh_key_name_map: %s\n\n" % ssh_key_name_map,
            "workspaces_map: %s\n\n" % workspaces_map,
            "workspace_to_ssh_key_map: %s\n\n" % workspace_to_ssh_key_map,
            "workspace_to_config_version_map: %s\n\n" % workspace_to_config_version_map,
            "policies_map: %s\n\n" % policies_map,
            "policy_sets_map: %s\n\n" % policy_sets_map,
            "sensitive_policy_set_parameter_data: %s\n\n" % sensitive_policy_set_parameter_data,
            "sensitive_variable_data: %s\n\n" % sensitive_variable_data
        ]

        with open("outputs.txt", "w") as f:
            f.write("".join(lines))


def migrate_to_target(api_source, api_target, write_to_file):
    teams_map = teams.migrate(api_source, api_target)

    # TODO: use it or remove it
    # TODO: org_membership_map = org_memberships.migrate(api_source, api_target, teams_map)

    ssh_keys_map, ssh_key_name_map = ssh_keys.migrate_keys(api_source, api_target)

    agent_pools_map = agent_pools.migrate(api_source, api_target)

    workspaces_map, workspace_to_ssh_key_map = \
        workspaces.migrate(api_source, api_target, TFE_VCS_CONNECTION_MAP, agent_pools_map)

    # TODO: use it or remove it
    # ssh_keys.migrate_key_files(api_target, ssh_key_name_map, ssh_key_file_path_map)

    workspaces_map, workspace_to_ssh_key_map = \
        workspaces.migrate(api_source, api_target, TFE_VCS_CONNECTION_MAP, agent_pools_map)

    state_versions.migrate_current(api_source, api_target, TFE_ORG_SOURCE, workspaces_map)

    """
    NOTE: if you wish to generate a map of Sensitive variables that can be used to update
    those values via the migrate_workspace_sensitive_variables method, pass True as the
    final argument (defaults to False).
    # TODO: right place for this note?
    """
    # TODO: is this var name accurate?
    sensitive_variable_data = workspace_vars.migrate(
        api_source, api_target, workspaces_map)

    # TODO: doesn't this happen in the normal migrate function now?
    # workspace_vars.migrate_sensitive(api_target, sensitive_variable_data_map)

    workspaces.migrate_ssh_keys(
        api_source, api_target, workspaces_map, workspace_to_ssh_key_map, ssh_keys_map)

    run_triggers.migrate(api_source, api_target, workspaces_map)

    notification_configs.migrate(api_source, api_target, workspaces_map)

    team_access.migrate(api_source, api_target, workspaces_map, teams_map)

    workspace_to_config_version_map = config_versions.migrate( \
        api_source, api_target, workspaces_map)

    # TODO: fix logging
    # config_versions.migrate_config_files(\
    #   api_target, workspace_to_config_version_map, workspace_to_file_path_map)

    policies_map = policies.migrate(api_source, api_target, TFE_TOKEN_SOURCE, TFE_URL_SOURCE)

    policy_sets_map = policy_sets.migrate(\
        api_source, api_target, TFE_VCS_CONNECTION_MAP, workspaces_map, policies_map)

    # NOTE: if you wish to generate a map of Sensitive policy set params that can be used to update
    # those values via the migrate_policy_set_sensitive_variables method, pass True as the final argument (defaults to False)
    sensitive_policy_set_parameter_data = \
        policy_set_params.migrate(api_source, api_target, policy_sets_map)

    # TODO: what is this function
    # policy_set_params.migrate_sensitive(api_target, sensitive_policy_set_parameter_data_map)

    registry_modules.migrate(api_source, api_target, TFE_VCS_CONNECTION_MAP)

    if write_to_file:
        write_output(teams_map, ssh_keys_map, ssh_key_name_map, workspaces_map, \
                workspace_to_ssh_key_map, workspace_to_config_version_map, \
                    policies_map, policy_sets_map, sensitive_policy_set_parameter_data, \
                        sensitive_variable_data)
    else:
        print_output(teams_map, ssh_keys_map, ssh_key_name_map, workspaces_map, \
                workspace_to_ssh_key_map, workspace_to_config_version_map, \
                    policies_map, policy_sets_map, sensitive_policy_set_parameter_data, \
                        sensitive_variable_data)


def delete_all_from_target(api):
    # TODO: confirm all of these before running, since they are destructive

    # Deleting workspaces allows us to skip deleting notification configs,
    # config_versions, state_versions, workspace_vars.
    workspaces.delete_all(api)

    # No need to delete the key files, they get deleted as well.
    ssh_keys.delete_all_keys(api)

    teams.delete_all(api)

    # Delete all the policy sets before deleting the individual policies
    policy_sets.delete_all(api)
    policies.delete_all(api)

    registry_modules.delete_all(api)

    agent_pools.delete_all(api)


def main(api_source, api_target, write_to_file, delete_all):
    if delete_all:
        delete_all_from_target(api_target)
    else:
        migrate_to_target(api_source, api_target, write_to_file)


if __name__ == "__main__":
    """
    All migration outputs are written to a .txt file by default
    If you prefer to have these outputs in the terminal,
    set the write_to_file parameter to False
    """
    parser = argparse.ArgumentParser(description='Migrate from TFE/C to TFE/C.')
    parser.add_argument('--write-output', dest="write_output", action="store_true", help="Write output to a file.")
    parser.add_argument('--delete-all', dest="delete_all", action="store_true", help="Delete all resources from the target API.")
    args = parser.parse_args()

    api_source = TFC(TFE_TOKEN_SOURCE, url=TFE_URL_SOURCE)
    api_source.set_org(TFE_ORG_SOURCE)

    api_target = TFC(TFE_TOKEN_TARGET, url=TFE_URL_TARGET)
    api_target.set_org(TFE_ORG_TARGET)

    main(api_source, api_target, args.write_output, args.delete_all)
