import os
import ast
from terrasnek.api import TFC
from functions import *
from tfc_migrate import \
    workspaces, teams, policies, policy_sets, registry_modules, \
        ssh_keys, config_versions, notification_configs, team_access


# SOURCE ORG
TFE_TOKEN_ORIGINAL = os.getenv("TFE_TOKEN_ORIGINAL", None)
TFE_URL_ORIGINAL = os.getenv("TFE_URL_ORIGINAL", None)
TFE_ORG_ORIGINAL = os.getenv("TFE_ORG_ORIGINAL", None)

api_source = TFC(TFE_TOKEN_ORIGINAL, url=TFE_URL_ORIGINAL)
api_source.set_org(TFE_ORG_ORIGINAL)

# NEW ORG
TFE_TOKEN_NEW = os.getenv("TFE_TOKEN_NEW", None)
TFE_URL_NEW = os.getenv("TFE_URL_NEW", None)
TFE_ORG_NEW = os.getenv("TFE_ORG_NEW", None)
TFE_VCS_CONNECTION_MAP = ast.literal_eval(os.getenv("TFE_VCS_CONNECTION_MAP", None))

api_new = TFC(TFE_TOKEN_NEW, url=TFE_URL_NEW)
api_new.set_org(TFE_ORG_NEW)

# TODO: use a logger instead of print statements
# TODO: break into a real main function
# TODO: break out real write functions


if __name__ == "__main__":
    """
    All migration outputs are written to a .txt file by default
    If you prefer to have these outputs in the terminal,
    set the write_to_file parameter to False
    """
    write_to_file = True

    print("Migrating teams...")
    teams_map = teams.migrate(api_source, api_new)
    print("Teams successfully migrated.")

    # org_membership_map = \
    #   migrate_org_memberships(api_source, api_new, teams_map)
    # print("organization memberships successfully migrated")

    print("Migrating SSH keys...")
    ssh_keys_map, ssh_key_name_map = ssh_keys.migrate_keys(api_source, api_new)
    print("SSH keys successfully migrated.")

    # migrate_ssh_key_files(api_new, ssh_key_name_map, ssh_key_file_path_map)
    # print("ssh key files successfully migrated")

    print("Migrating agent pools...")
    agent_pool_id = migrate_agent_pools(
        api_source, api_new, TFE_ORG_ORIGINAL, TFE_ORG_NEW)
    print("Agent pools successfully migrated.")

    print("Migrating workspaces...")
    workspaces_map, workspace_to_ssh_key_map = \
        workspaces.migrate(api_source, api_new, TFE_VCS_CONNECTION_MAP, agent_pool_id)
    print("Workspaces successfully migrated.")

    # migrate_all_state(api_source, api_new, TFE_ORG_ORIGINAL, workspaces_map)
    print("Migrating current states...")
    migrate_current_state(api_source, api_new,
                          TFE_ORG_ORIGINAL, workspaces_map)
    print("Current states successfully migrated.")

    """
    NOTE: if you wish to generate a map of Sensitive variables that can be used to update
    those values via the migrate_workspace_sensitive_variables method, pass True as the
    final argument (defaults to False).
    """
    print("Migrating workspace variables...")
    # TODO: is this var name accurate?
    sensitive_variable_data = migrate_workspace_variables(
        api_source, api_new, workspaces_map)
    print("Workspace variables successfully migrated.")

    # migrate_workspace_sensitive_variables(api_new, sensitive_variable_data_map)
    # print("workspace sensitive variables successfully migrated")

    print("Migrating SSH keys for workspaces...")
    migrate_ssh_keys_to_workspaces(
        api_source, api_new, workspaces_map, workspace_to_ssh_key_map, ssh_keys_map)
    print("SSH keys for workspaces successfully migrated.")

    print("Migrating run triggers...")
    migrate_workspace_run_triggers(api_source, api_new, workspaces_map)
    print("Run triggers successfully migrated.")

    print("Migrating notification configs...")
    notification_configs.migrate(api_source, api_new, workspaces_map)
    print("notifications successfully migrated.")

    print("Migrating team access...")
    team_access.migrate(api_source, api_new, workspaces_map, teams_map)
    print("Team access successfully migrated.")

    print("Migrating config versions...")
    workspace_to_configuration_version_map = config_versions.migrate( \
        api_source, api_new, workspaces_map)
    print("workspace configuration versions successfully migrated.")

    # migrate_configuration_files(\
    #   api_new, workspace_to_configuration_version_map, workspace_to_file_path_map)
    # print("workspace configuration files successfully migrated.")

    print("Migrating policies...")
    policies_map = policies.migrate(
        api_source, api_new, TFE_TOKEN_ORIGINAL, TFE_URL_ORIGINAL)
    print("policies successfully migrated.")

    print("Migrating policy sets...")
    policy_sets_map = policy_sets.migrate(\
        api_source, api_new, TFE_VCS_CONNECTION_MAP, workspaces_map, policies_map)
    print("Policy sets successfully migrated.")

    # NOTE: if you wish to generate a map of Sensitive policy set parameters that can be used to update
    # those values via the migrate_policy_set_sensitive_variables method, pass True as the final argument (defaults to False)
    print("Migrating policy set parameters...")
    sensitive_policy_set_parameter_data = migrate_policy_set_parameters(
        api_source, api_new, policy_sets_map)
    print("Policy set parameters successfully migrated.")

    # migrate_policy_set_sensitive_parameters(api_new, sensitive_policy_set_parameter_data_map)
    # print("policy set sensitive parameters successfully migrated.")

    print("Migrating registry modules...")
    registry_modules.migrate(api_source, api_new, TFE_VCS_CONNECTION_MAP)
    print("Registry modules successfully migrated.")

    # Migration Outputs
    # TODO: improve this writing logic
    if write_to_file:
        with open("outputs.txt", "w") as f:
            f.write("teams_map: %s\n\n" % teams_map)
            # f.write("org_membership_map: %s\n\n" % org_membership_map)
            f.write("ssh_keys_map: %s\n\n" % ssh_keys_map)
            f.write("ssh_key_name_map: %s\n\n" % ssh_key_name_map)
            f.write("workspaces_map: %s\n\n" % workspaces_map)
            f.write("workspace_to_ssh_key_map: %s\n\n" % workspace_to_ssh_key_map)
            f.write("workspace_to_configuration_version_map: %s\n\n" % workspace_to_configuration_version_map)
            f.write("policies_map: %s\n\n" % policies_map)
            f.write("policy_sets_map: %s\n\n" % policy_sets_map)
            f.write("policy_sets_map: %s\n\n" % policy_sets_map)
            f.write("sensitive_policy_set_parameter_data: %s\n\n" % sensitive_policy_set_parameter_data)
            f.write("sensitive_variable_data: %s\n\n" % sensitive_variable_data)
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
