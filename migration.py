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
# TODO: break into a real main function
# TODO: break out real write functions
# TODO: replace "configuration" with "config"
# TODO: replace "parameters" with "params"
# TODO: use "source" and "target" rather than "new" and "old"
# TODO: have these functions write their outputs to a file
# TODO: make all functions idempotent.
# TODO: add a flag to a main function to optionally delete everything, or to ignore existing names
# TODO: try not to repeat the try/except blocks
# TODO: create a base migrate class w/ a logger


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
        workspace_to_ssh_key_map, workspace_to_configuration_version_map, \
            policies_map, policy_sets_map, sensitive_policy_set_parameter_data, \
                sensitive_variable_data):
    print("\n")
    print("MIGRATION MAPS:")
    print("teams_map:", teams_map)
    print("\n")
    print("ssh_keys_map:", ssh_keys_map)
    print("\n")
    print("ssh_keys_name_map:", ssh_key_name_map)
    print("\n")
    print("workspaces_map:", workspaces_map)
    print("\n")
    print("workspace_to_ssh_key_map:", workspace_to_ssh_key_map)
    print("\n")
    print("workspace_to_configuration_version_map:",
        workspace_to_configuration_version_map)
    print("\n")
    print("policies_map:", policies_map)
    print("\n")
    print("policy_sets_map:", policy_sets_map)
    print("\n")
    print("sensitive_policy_set_parameter_data:",
        sensitive_policy_set_parameter_data)
    print("\n")
    print("sensitive_variable_data:", sensitive_variable_data)

def write_output(\
    teams_map, ssh_keys_map, ssh_key_name_map, workspaces_map, \
        workspace_to_ssh_key_map, workspace_to_configuration_version_map, \
            policies_map, policy_sets_map, sensitive_policy_set_parameter_data, \
                sensitive_variable_data):

    with open("outputs.txt", "w") as f:
        f.write("teams_map: %s\n\n" % teams_map)
        f.write("ssh_keys_map: %s\n\n" % ssh_keys_map)
        f.write("ssh_key_name_map: %s\n\n" % ssh_key_name_map)
        f.write("workspaces_map: %s\n\n" % workspaces_map)
        f.write("workspace_to_ssh_key_map: %s\n\n" % workspace_to_ssh_key_map)
        f.write("workspace_to_configuration_version_map: %s\n\n" % workspace_to_configuration_version_map)
        f.write("policies_map: %s\n\n" % policies_map)
        f.write("policy_sets_map: %s\n\n" % policy_sets_map)
        f.write("sensitive_policy_set_parameter_data: %s\n\n" % sensitive_policy_set_parameter_data)
        f.write("sensitive_variable_data: %s\n\n" % sensitive_variable_data)


def migrate_to_target(api_source, api_target, write_to_file):
    teams_map = teams.migrate(api_source, api_target)
    # TODO: org_membership_map = org_memberships.migrate(api_source, api_target, teams_map)
    ssh_keys_map, ssh_key_name_map = ssh_keys.migrate_keys(api_source, api_target)
    # TODO: ssh_keys.migrate_key_files(api_target, ssh_key_name_map, ssh_key_file_path_map)
    agent_pool_id = agent_pools.migrate(api_source, api_target, TFE_ORG_SOURCE, TFE_ORG_TARGET)
    workspaces_map, workspace_to_ssh_key_map = \
        workspaces.migrate(api_source, api_target, TFE_VCS_CONNECTION_MAP, agent_pool_id)
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
    # print("workspace sensitive variables successfully migrated")

    workspaces.migrate_ssh_keys(
        api_source, api_target, workspaces_map, workspace_to_ssh_key_map, ssh_keys_map)

    run_triggers.migrate(api_source, api_target, workspaces_map)

    notification_configs.migrate(api_source, api_target, workspaces_map)

    team_access.migrate(api_source, api_target, workspaces_map, teams_map)

    workspace_to_configuration_version_map = config_versions.migrate( \
        api_source, api_target, workspaces_map)

    # TODO: fix logging
    # config_versions.migrate_config_files(\
    #   api_target, workspace_to_configuration_version_map, workspace_to_file_path_map)
    # print("workspace configuration files successfully migrated.")

    policies_map = policies.migrate(api_source, api_target, TFE_TOKEN_SOURCE, TFE_URL_SOURCE)

    policy_sets_map = policy_sets.migrate(\
        api_source, api_target, TFE_VCS_CONNECTION_MAP, workspaces_map, policies_map)

    # NOTE: if you wish to generate a map of Sensitive policy set parameters that can be used to update
    # those values via the migrate_policy_set_sensitive_variables method, pass True as the final argument (defaults to False)
    sensitive_policy_set_parameter_data = \
        policy_set_params.migrate(api_source, api_target, policy_sets_map)

    # TODO: what is this function
    # policy_set_params.migrate_sensitive(api_target, sensitive_policy_set_parameter_data_map)
    # print("policy set sensitive parameters successfully migrated.")

    registry_modules.migrate(api_source, api_target, TFE_VCS_CONNECTION_MAP)

    if write_to_file:
        write_output(teams_map, ssh_keys_map, ssh_key_name_map, workspaces_map, \
                workspace_to_ssh_key_map, workspace_to_configuration_version_map, \
                    policies_map, policy_sets_map, sensitive_policy_set_parameter_data, \
                        sensitive_variable_data)
    else:
        print_output(teams_map, ssh_keys_map, ssh_key_name_map, workspaces_map, \
                workspace_to_ssh_key_map, workspace_to_configuration_version_map, \
                    policies_map, policy_sets_map, sensitive_policy_set_parameter_data, \
                        sensitive_variable_data)


def delete_all_from_target(api):
    workspaces.delete_all(api)
    # ssh_keys.delete_all_keys(api)
    # teams.delete_all_keys(api)
    # policies.delete_all_keys(api)
    # policy_sets.delete_all_keys(api)
    # modules.delete_all_keys(api)
    # TODO: logging


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

    """
    # Migration Outputs
    # TODO: improve this writing logic
    # TODO: write each to it's own file.
    if write_to_file:
    else:
        print("\n")
        print("MIGRATION MAPS:")
        print("teams_map:", teams_map)
        print("\n")
        # print("org_membership_map:", org_membership_map)
        # print("\n")
        print("ssh_keys_map:", ssh_keys_map)
        print("\n")
        print("ssh_keys_name_map:", ssh_key_name_map)
        print("\n")
        print("workspaces_map:", workspaces_map)
        print("\n")
        print("workspace_to_ssh_key_map:", workspace_to_ssh_key_map)
        print("\n")
        print("workspace_to_configuration_version_map:",
            workspace_to_configuration_version_map)
        print("\n")
        print("policies_map:", policies_map)
        print("\n")
        print("policy_sets_map:", policy_sets_map)
        print("\n")
        print("sensitive_policy_set_parameter_data:",
            sensitive_policy_set_parameter_data)
        print("\n")
        print("sensitive_variable_data:", sensitive_variable_data)
    """