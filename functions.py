import urllib.request
import hashlib
import base64
import json

# TODO: migrate this to the latest version of terrasnek
# TODO: use "source" and "target" rather than new and old
# TODO: have these functions write their outputs to a file
# TODO: make these functions idempotent
# TODO: make sure to handle all of these that can have collisions.


def _find_existing_team_id(api, team_name):
    teams = api.teams.list()["data"]
    found_team_id = None

    for team in teams:
        if team["attributes"]["name"] == team_name:
            found_team_id = team["id"]

    return found_team_id


def _find_existing_workspace_id(api, workspace_name):
    workspaces = api.workspaces.list()["data"]

    found_workspace_id = None

    for workspace in workspaces:
        if workspace["attributes"]["name"] == workspace_name:
            found_workspace_id = workspace["id"]

    return found_workspace_id


def migrate_teams(api_source, api_target):
    # Fetch Teams from Existing Org
    teams = api_source.teams.list()["data"]

    # TODO: not sure we can always assume the owners org will be the first in the array.
    # At the very least it"s not prudent, but it"s likely to introduce issues down the line.
    new_org_owners_team_id = teams[0]["id"]

    teams_map = {}
    for team in teams:
        if team["attributes"]["name"] == "owners":
            teams_map[team["id"]] = new_org_owners_team_id
        else:
            # Build the new team payload
            new_team_payload = {
                "data": {
                    "type": "teams",
                    "attributes": {
                        "name": team["attributes"]["name"],
                        "organization-access": {
                            "manage-workspaces": \
                                team["attributes"]["organization-access"]["manage-workspaces"],
                            "manage-policies": \
                                team["attributes"]["organization-access"]["manage-policies"],
                            "manage-vcs-settings": \
                                team["attributes"]["organization-access"]["manage-vcs-settings"]
                        }
                    }
                }
            }

            try:
                # Create team in the target org
                new_team = api_target.teams.create(new_team_payload)

                # Build Team ID Map
                teams_map[team["id"]] = new_team["data"]["id"]
            except Exception as err:
                # TODO: team likely already exists, but double check the exception
                # TODO: we should also note that existing teams may be overwritten, or rather, that the target org should be empty.
                existing_team_id = _find_existing_team_id(api_target, team["attributes"]["name"])
                teams_map[team["id"]] = existing_team_id
                print(err)

    return teams_map


def migrate_organization_memberships(api_source, api_target, teams_map):
    organization_membership_map = {}
    # Set proper membership filters
    member_filters = [
        {
            "keys": ["status"],
            "value": "active"
        }
    ]

    org_members = api_source.org_memberships.list_for_org(
        filters=member_filters, page=0, page_size=100)["data"]
    for org_member in org_members:
        for team in org_member["relationships"]["teams"]["data"]:
            team["id"] = teams_map[team["id"]]

        # Build the new User invite payload
        new_user_invite_payload = {
            "data": {
                "attributes": {
                    "email": org_member["attributes"]["email"]
                },
                "relationships": {
                    "teams": {
                        "data": org_member["relationships"]["teams"]["data"]
                    },
                },
                "type": "organization-memberships"
            }
        }

        try:
            new_org_member = api_target.org_memberships.invite(
                new_user_invite_payload)["data"]
        except:
            organization_membership_map[org_member["relationships"]["user"]["data"]["id"]] = \
                org_member["relationships"]["user"]["data"]["id"]

        new_user_id = new_org_member["relationships"]["user"]["data"]["id"]
        organization_membership_map[org_member["relationships"]["user"]["data"]["id"]] = \
            new_user_id

    return organization_membership_map


def migrate_ssh_keys(api_source, api_target):
    # Fetch SSH Keys from Existing Org
    # Note: This does not fetch the Keys themselves
    ssh_keys = api_source.ssh_keys.list()["data"]

    ssh_keys_map = {}
    ssh_key_name_map = {}
    if ssh_keys:
        for ssh_key in reversed(ssh_keys):
            # Build the new Agent Pool Payload
            new_ssh_key_payload = {
                "data": {
                    "type": "ssh-keys",
                    "attributes": {
                        "name": ssh_key["attributes"]["name"],
                        "value": "Replace Me"
                    }
                }
            }

            # Create SSH Key in New Org
            # Note: The actual Keys themselves must be added separately afterward
            new_ssh_key = api_target.ssh_keys.create(new_ssh_key_payload)["data"]
            ssh_keys_map[ssh_key["id"]] = new_ssh_key["id"]
            ssh_key_name_map[new_ssh_key["attributes"]
                             ["name"]] = new_ssh_key["id"]

    return ssh_keys_map, ssh_key_name_map


def migrate_ssh_key_files(api_target, ssh_key_name_map, ssh_key_file_path_map):
    """
    NOTE: The ssh_key_file_path_map must be created ahead of time with a format of
    {"ssh_key_name":"path/to/file"}
    """

    for ssh_key in ssh_key_file_path_map:
        # Pull SSH key data
        get_ssh_key = open(ssh_key_file_path_map[ssh_key], "r")
        ssh_key_data = get_ssh_key.read()

        # Build the new ssh key file payload
        new_ssh_key_file_payload = {
            "data": {
                "type": "ssh-keys",
                "attributes": {
                    "value": ssh_key_data
                }
            }
        }

        # Upload the SSH key file to the new organization
        api_target.ssh_keys.update(ssh_key_name_map[ssh_key], new_ssh_key_file_payload)


def migrate_agent_pools(api_source, api_target, tfe_org_original, tfe_org_new):
    # Fetch agent pools from existing org
    agent_pools = api_source.agents.list_pools()["data"]

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
            agent_pool_id = api_target.agents.create_pool(tfe_org_new)[
                "data"]["id"]
        return agent_pool_id


def migrate_workspaces(api_source, api_target, tfe_vcs_connection_map, agent_pool_id):
    # Fetch workspaces from existing org
    workspaces = api_source.workspaces.list()["data"]
    workspaces_map = {}
    workspace_to_ssh_key_map = {}

    for workspace in workspaces:
        # TODO: Make these normal if/else so they are easier to read
        branch = "" if workspace["attributes"]["vcs-repo"] is None \
            else workspace["attributes"]["vcs-repo"]["branch"]

        ingress_submodules = False if workspace["attributes"]["vcs-repo"] is None \
            else workspace["attributes"]["vcs-repo"]["ingress-submodules"]

        default_branch = True if branch == "" else False

        if workspace["attributes"]["vcs-repo"] is not None:
            if workspace["attributes"]["execution-mode"] == "agent":
                # Build the new workspace payload
                new_workspace_payload = {
                    "data": {
                        "attributes": {
                            "name": workspace["attributes"]["name"],
                            "terraform_version": workspace["attributes"]["terraform-version"],
                            "working-directory": workspace["attributes"]["working-directory"],
                            "file-triggers-enabled": \
                                workspace["attributes"]["file-triggers-enabled"],
                            "allow-destroy-plan": workspace["attributes"]["allow-destroy-plan"],
                            "auto-apply": workspace["attributes"]["auto-apply"],
                            "execution-mode": workspace["attributes"]["execution-mode"],
                            "agent-pool-id": agent_pool_id,
                            "description": workspace["attributes"]["description"],
                            "source-name": workspace["attributes"]["source-name"],
                            "source-url": workspace["attributes"]["source-url"],
                            "queue-all-runs": workspace["attributes"]["queue-all-runs"],
                            "speculative-enabled": workspace["attributes"]["speculative-enabled"],
                            "trigger-prefixes": workspace["attributes"]["trigger-prefixes"],
                            "vcs-repo": {
                                "identifier": workspace["attributes"]["vcs-repo-identifier"],
                                "oauth-token-id": tfe_vcs_connection_map\
                                    [workspace["attributes"]["vcs-repo"]["oauth-token-id"]],
                                "branch": branch,
                                "default-branch": default_branch,
                                "ingress-submodules": ingress_submodules
                            }
                        },
                        "type": "workspaces"
                    }
                }

                try:
                    # Build the new workspace
                    new_workspace = api_target.workspaces.create(new_workspace_payload)
                    new_workspace_id = new_workspace["data"]["id"]
                    workspaces_map[workspace["id"]] = new_workspace_id
                except Exception as err:
                    # TODO: catch the actual exception
                    existing_workspace_id = \
                        _find_existing_workspace_id(api_target, workspace["attributes"]["name"])
                    workspaces_map[workspace["id"]] = existing_workspace_id
                    print(err)

                try:
                    ssh_key = workspace["relationships"]["ssh-key"]["data"]["id"]
                    workspace_to_ssh_key_map[workspace["id"]] = ssh_key
                except:
                    continue
            else:
                # Build the new workspace payload
                new_workspace_payload = {
                    "data": {
                        "attributes": {
                            "name": workspace["attributes"]["name"],
                            "terraform_version": workspace["attributes"]["terraform-version"],
                            "working-directory": workspace["attributes"]["working-directory"],
                            "file-triggers-enabled": \
                                workspace["attributes"]["file-triggers-enabled"],
                            "allow-destroy-plan": workspace["attributes"]["allow-destroy-plan"],
                            "auto-apply": workspace["attributes"]["auto-apply"],
                            "execution-mode": workspace["attributes"]["execution-mode"],
                            "description": workspace["attributes"]["description"],
                            "source-name": workspace["attributes"]["source-name"],
                            "source-url": workspace["attributes"]["source-url"],
                            "queue-all-runs": workspace["attributes"]["queue-all-runs"],
                            "speculative-enabled": workspace["attributes"]["speculative-enabled"],
                            "trigger-prefixes": workspace["attributes"]["trigger-prefixes"],
                            "vcs-repo": {
                                "identifier": workspace["attributes"]["vcs-repo-identifier"],
                                "oauth-token-id": \
                                    tfe_vcs_connection_map[\
                                        workspace["attributes"]["vcs-repo"]["oauth-token-id"]],
                                "branch": branch,
                                "default-branch": default_branch,
                                "ingress-submodules": ingress_submodules
                            }
                        },
                        "type": "workspaces"
                    }
                }

                try:
                    # Build the new Workspace
                    new_workspace = api_target.workspaces.create(new_workspace_payload)
                    new_workspace_id = new_workspace["data"]["id"]

                    workspaces_map[workspace["id"]] = new_workspace_id
                except Exception as err:
                    # TODO: catch the actual exception
                    existing_workspace_id = \
                        _find_existing_workspace_id(api_target, workspace["attributes"]["name"])
                    workspaces_map[workspace["id"]] = existing_workspace_id

                try:
                    ssh_key = workspace["relationships"]["ssh-key"]["data"]["id"]
                    workspace_to_ssh_key_map[workspace["id"]] = ssh_key
                except:
                    continue
        else:
            if workspace["attributes"]["execution-mode"] == "agent":
                # Build the new workspace payload
                new_workspace_payload = {
                    "data": {
                        "attributes": {
                            "name": workspace["attributes"]["name"],
                            "terraform_version": workspace["attributes"]["terraform-version"],
                            "working-directory": workspace["attributes"]["working-directory"],
                            "file-triggers-enabled": \
                                workspace["attributes"]["file-triggers-enabled"],
                            "allow-destroy-plan": workspace["attributes"]["allow-destroy-plan"],
                            "auto-apply": workspace["attributes"]["auto-apply"],
                            "execution-mode": workspace["attributes"]["execution-mode"],
                            "agent-pool-id": agent_pool_id,
                            "description": workspace["attributes"]["description"],
                            "source-name": workspace["attributes"]["source-name"],
                            "source-url": workspace["attributes"]["source-url"],
                            "queue-all-runs": workspace["attributes"]["queue-all-runs"],
                            "speculative-enabled": workspace["attributes"]["speculative-enabled"],
                            "trigger-prefixes": workspace["attributes"]["trigger-prefixes"]
                        },
                        "type": "workspaces"
                    }
                }

                try:
                    # Build the new Workspace
                    new_workspace = api_target.workspaces.create(new_workspace_payload)
                    new_workspace_id = new_workspace["data"]["id"]

                    workspaces_map[workspace["id"]] = new_workspace_id
                except Exception as err:
                    # TODO: catch the actual exception
                    existing_workspace_id = \
                        _find_existing_workspace_id(api_target, workspace["attributes"]["name"])
                    workspaces_map[workspace["id"]] = existing_workspace_id

                try:
                    ssh_key = workspace["relationships"]["ssh-key"]["data"]["id"]
                    workspace_to_ssh_key_map[workspace["id"]] = ssh_key
                except:
                    continue
            else:
                # Build the new workspace payload
                new_workspace_payload = {
                    "data": {
                        "attributes": {
                            "name": workspace["attributes"]["name"],
                            "terraform_version": workspace["attributes"]["terraform-version"],
                            "working-directory": workspace["attributes"]["working-directory"],
                            "file-triggers-enabled": \
                                workspace["attributes"]["file-triggers-enabled"],
                            "allow-destroy-plan": workspace["attributes"]["allow-destroy-plan"],
                            "auto-apply": workspace["attributes"]["auto-apply"],
                            "execution-mode": workspace["attributes"]["execution-mode"],
                            "description": workspace["attributes"]["description"],
                            "source-name": workspace["attributes"]["source-name"],
                            "source-url": workspace["attributes"]["source-url"],
                            "queue-all-runs": workspace["attributes"]["queue-all-runs"],
                            "speculative-enabled": workspace["attributes"]["speculative-enabled"],
                            "trigger-prefixes": workspace["attributes"]["trigger-prefixes"]
                        },
                        "type": "workspaces"
                    }
                }

                try:
                    # Build the new Workspace
                    new_workspace = api_target.workspaces.create(new_workspace_payload)
                    new_workspace_id = new_workspace["data"]["id"]

                    workspaces_map[workspace["id"]] = new_workspace_id
                except Exception as err:
                    # TODO: catch the actual exception
                    existing_workspace_id = \
                        _find_existing_workspace_id(api_target, workspace["attributes"]["name"])
                    workspaces_map[workspace["id"]] = existing_workspace_id

                workspaces_map[workspace["id"]] = new_workspace_id

                try:
                    ssh_key = workspace["relationships"]["ssh-key"]["data"]["id"]
                    workspace_to_ssh_key_map[workspace["id"]] = ssh_key
                except:
                    continue
    return workspaces_map, workspace_to_ssh_key_map


def migrate_all_state(api_source, api_target, tfe_org_original, workspaces_map):
    for workspace_id in workspaces_map:
        workspace_name = api_source.workspaces.show(workspace_id=workspace_id)[
            "data"]["attributes"]["name"]

        # Set proper state filters to pull state versions for each workspace
        state_filters = [
            {
                "keys": ["workspace", "name"],
                "value":  workspace_name
            },
            {
                "keys": ["organization", "name"],
                "value": tfe_org_original
            }
        ]

        state_versions = api_source.state_versions.list(
            filters=state_filters)["data"]
        if state_versions:
            for state_version in reversed(state_versions):
                state_url = state_version["attributes"]["hosted-state-download-url"]
                pull_state = urllib.request.urlopen(state_url)
                state_data = pull_state.read()
                state_serial = json.loads(state_data)["serial"]

                state_hash = hashlib.md5()
                state_hash.update(state_data)
                state_md5 = state_hash.hexdigest()
                state_b64 = base64.b64encode(state_data).decode("utf-8")

                # Build the new state payload
                create_state_version_payload = {
                    "data": {
                        "type": "state-versions",
                        "attributes": {
                            "serial": state_serial,
                            "md5": state_md5,
                            "state": state_b64
                        }
                    }
                }

                # Migrate state to the new Workspace
                api_target.workspaces.lock(workspaces_map[workspace_id], {
                                        "reason": "migration script"})
                api_target.state_versions.create(
                    workspaces_map[workspace_id], create_state_version_payload)
                api_target.workspaces.unlock(workspaces_map[workspace_id])


def migrate_current_state(api_source, api_target, tfe_org_original, workspaces_map):
    for workspace_id in workspaces_map:
        workspace_name = api_source.workspaces.show(workspace_id=workspace_id)[
            "data"]["attributes"]["name"]

        # Set proper state filters to pull state versions for each workspace
        state_filters = [
            {
                "keys": ["workspace", "name"],
                "value":  workspace_name
            },
            {
                "keys": ["organization", "name"],
                "value": tfe_org_original
            }
        ]

        state_versions = api_source.state_versions.list(
            filters=state_filters)["data"]
        if state_versions:
            current_version = api_source.state_versions.get_current(workspace_id)[
                "data"]
            state_url = current_version["attributes"]["hosted-state-download-url"]
            pull_state = urllib.request.urlopen(state_url)
            state_data = pull_state.read()
            state_serial = json.loads(state_data)["serial"]

            state_hash = hashlib.md5()
            state_hash.update(state_data)
            state_md5 = state_hash.hexdigest()
            state_b64 = base64.b64encode(state_data).decode("utf-8")

            # Build the new state payload
            create_state_version_payload = {
                "data": {
                    "type": "state-versions",
                    "attributes": {
                        "serial": state_serial,
                        "md5": state_md5,
                        "state": state_b64
                    }
                }
            }

            # Migrate state to the new workspace
            api_target.workspaces.lock(\
                workspaces_map[workspace_id], {"reason": "migration script"})
            api_target.state_versions.create(\
                workspaces_map[workspace_id], create_state_version_payload)
            api_target.workspaces.unlock(workspaces_map[workspace_id])


def migrate_workspace_variables(\
        api_source, api_target, tfe_org_original, workspaces_map, \
            return_sensitive_variable_data=True):
    sensitive_variable_data = []
    for workspace_id in workspaces_map:
        new_workspace_id = workspaces_map[workspace_id]

        # Pull variables from the old workspace
        workspace_vars = api_source.workspace_vars.list(workspace_id)["data"]

        # Get the variables that may already exist in the new workspace from a previous run
        existing_workspace_vars = api_target.workspace_vars.list(new_workspace_id)["data"]
        existing_variable_names = [var["attributes"]["key"] for var in existing_workspace_vars]

        # TODO: why is this reversed?
        for variable in reversed(workspace_vars):
            variable_key = variable["attributes"]["key"]

            # Make sure we haven't already created this variable in a past run
            if variable_key not in existing_variable_names:
                variable_value = variable["attributes"]["value"]
                variable_category = variable["attributes"]["category"]
                variable_hcl = variable["attributes"]["hcl"]
                variable_description = variable["attributes"]["description"]
                variable_sensitive = variable["attributes"]["sensitive"]

                # Build the new variable payload
                new_variable_payload = {
                    "data": {
                        "type": "vars",
                        "attributes": {
                            "key": variable_key,
                            "value": variable_value,
                            "description": variable_description,
                            "category": variable_category,
                            "hcl": variable_hcl,
                            "sensitive": variable_sensitive
                        }
                    }
                }

                # Migrate variables to the new Workspace
                new_variable = api_target.workspace_vars.create(
                    new_workspace_id, new_variable_payload)["data"]
                new_variable_id = new_variable["id"]

                if variable_sensitive and return_sensitive_variable_data:
                    workspace_name = api_target.workspaces.show(workspace_id=workspace_id)\
                        ["data"]["attributes"]["name"]

                    # Build the sensitive variable map
                    variable_data = {
                        "workspace_name": workspace_name,
                        "workspace_id": new_workspace_id,
                        "variable_id": new_variable_id,
                        "variable_key": variable_key,
                        "variable_value": variable_value,
                        "variable_description": variable_description,
                        "variable_category": variable_category,
                        "variable_hcl": variable_hcl
                    }

                    sensitive_variable_data.append(variable_data)
    return sensitive_variable_data

def migrate_workspace_sensitive_variables(api_target, sensitive_variable_data_map):
    """
    NOTE: The sensitive_variable_data_map map must be created ahead of time. The easiest way to
    do this is to update the value for each variable in the list returned by the
    migrate_workspace_variables method
    """

    for sensitive_variable in sensitive_variable_data_map:
        # Build the new variable payload
        update_variable_payload = {
            "data": {
                "id": sensitive_variable["variable_id"],
                "attributes": {
                    "key": sensitive_variable["variable_key"],
                    "value": sensitive_variable["variable_value"],
                    "description": sensitive_variable["variable_description"],
                    "category": sensitive_variable["variable_category"],
                    "hcl": sensitive_variable["variable_hcl"],
                    "sensitive": "true"
                },
                "type": "vars"
            }
        }

        # Update the sensitive variable value in the new workspace
        api_target.workspace_vars.update(
            sensitive_variable["workspace_id"], \
                sensitive_variable["variable_id"], update_variable_payload)


def migrate_ssh_keys_to_workspaces(\
        api_source, api_target, workspaces_map, workspace_to_ssh_key_map, \
            ssh_keys_map):

    if workspace_to_ssh_key_map:
        for key, value in workspace_to_ssh_key_map.items():
            # Build the new ssh key payload
            new_workspace_ssh_key_payload = {
                "data": {
                    "attributes": {
                        "id": ssh_keys_map[value]
                    },
                    "type": "workspaces"
                }
            }

            # Add SSH Keys to the new Workspace
            api_target.workspaces.assign_ssh_key(
                workspaces_map[key], new_workspace_ssh_key_payload)


def migrate_workspace_run_triggers(api_source, api_target, workspaces_map):

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

                # Add Run Triggers to the new Workspace
                api_target.run_triggers.create(
                    workspaces_map[workspace_id], new_run_trigger_payload)


def migrate_workspace_notifications(api_source, api_target, workspaces_map):
    for workspace_id in workspaces_map:
        # Pull notifications from the old workspace
        notifications = api_source.notification_configs.list(workspace_id)["data"]

        if notifications:
            for notification in notifications:
                if notification["attributes"]["destination-type"] == "email":
                    # Build the new notification payload
                    new_notification_payload = {
                        "data": {
                            "type": "notification-configurations",
                            "attributes": {
                                "destination-type": notification["attributes"]["destination-type"],
                                "enabled": notification["attributes"]["enabled"],
                                "name": notification["attributes"]["name"],
                                "triggers": notification["attributes"]["triggers"]
                            },
                            "relationships": {
                                "users": {
                                    "data":  notification["relationships"]["users"]["data"]
                                }
                            }
                        }
                    }

                    # Add notifications to the new workspace
                    api_target.notification_configs.create(
                        workspaces_map[workspace_id], new_notification_payload)
                else:
                    # Build the new notification payload
                    new_notification_payload = {
                        "data": {
                            "type": "notification-configurations",
                            "attributes": {
                                "destination-type": notification["attributes"]["destination-type"],
                                "enabled": notification["attributes"]["enabled"],
                                "name": notification["attributes"]["name"],
                                "token": notification["attributes"]["token"],
                                "url": notification["attributes"]["url"],
                                "triggers": notification["attributes"]["triggers"]
                            }
                        }
                    }

                    # Add notifications to the new workspace
                    api_target.notification_configs.create(\
                        workspaces_map[workspace_id], new_notification_payload)

def migrate_workspace_team_access(api_source, api_target, workspaces_map, teams_map):
    for workspace_id in workspaces_map:
        # Set proper workspace team filters to pull team access for each workspace
        workspace_team_filters = [
            {
                "keys": ["workspace", "id"],
                "value": workspace_id
            }
        ]

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
                    # Create the Team Workspace Access map for the new Workspace
                    api_target.team_access.add_team_access(new_workspace_team_payload)
                except Exception as err:
                    # TODO
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
                    # Create the Team Workspace Access map for the new Workspace
                    api_target.team_access.add_team_access(new_workspace_team_payload)
                except Exception as err:
                    # TODO
                    print(err)


def migrate_configuration_versions(api_source, api_target, workspaces_map):
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


def migrate_configuration_files(\
    api_target, workspace_to_configuration_version_map, workspace_to_file_path_map):
    for workspace_name in workspace_to_file_path_map:
        # NOTE: The workspace_to_file_path_map must be created ahead of time
        # with a format of {"workspace_name":"path/to/file"}

        # Upload the configuration file to the new workspace
        api_target.config_versions.upload(\
            workspace_to_file_path_map[workspace_name], \
                workspace_to_configuration_version_map[workspace_name])


def migrate_policies(api_source, api_target, tfe_token_original, tfe_url_original):
    # Pull policies from the old organization
    policies = api_source.policies.list()["data"]
    policies_map = {}

    if policies:
        for policy in policies:
            policy_id = policy["id"]

            headers = {
                "Authorization": "Bearer %s" % (tfe_token_original),
                "Content-Type": "application/vnd.api+json"
            }
            policy_download_url = "%s/api/v2/policies/%s/download" % \
                (tfe_url_original, policy_id)

            # Retrieve the policy content
            policy_request = urllib.request.Request(policy_download_url, headers=headers)
            pull_policy = urllib.request.urlopen(policy_request)
            policy_data = pull_policy.read()
            policy_b64 = policy_data.decode("utf-8")

            # Build the new policy payload
            new_policy_payload = {
                "data": {
                    "attributes": {
                        "name": policy["attributes"]["name"],
                        "description": policy["attributes"]["description"],
                        "enforce": [
                            {
                                "path": policy["attributes"]["enforce"][0]["path"],
                                "mode": policy["attributes"]["enforce"][0]["mode"]
                            }
                        ],
                    },
                    "type": "policies"
                }
            }

            # Create the policy in the new organization
            new_policy = api_target.policies.create(new_policy_payload)
            new_policy_id = new_policy["data"]["id"]
            policies_map[policy_id] = new_policy_id

            # Upload the policy content to the new policy in the new organization
            api_target.policies.upload(new_policy_id, policy_b64)

        return policies_map


def migrate_policy_sets(\
    api_source, api_target, tfe_vcs_connection_map, workspaces_map, policies_map):
    # Pull policy sets from the old organization
    policy_sets = api_source.policy_sets.list(
        page_size=50, include="policies,workspaces")["data"]

    policy_sets_map = {}
    for policy_set in policy_sets:
        if policy_set["attributes"]["versioned"]:
            if policy_set["attributes"]["global"]:
                # Build the new policy set payload
                new_policy_set_payload = {
                    "data": {
                        "type": "policy-sets",
                        "attributes": {
                            "name": policy_set["attributes"]["name"],
                            "description": policy_set["attributes"]["name"],
                            "global": policy_set["attributes"]["global"],
                            "policies-path": policy_set["attributes"]["policies-path"],
                            "vcs-repo": {
                                "branch": policy_set["attributes"]["vcs-repo"]["branch"],
                                "identifier": policy_set["attributes"]["vcs-repo"]["identifier"],
                                "ingress-submodules": policy_set\
                                    ["attributes"]["vcs-repo"]["ingress-submodules"],
                                "oauth-token-id": tfe_vcs_connection_map\
                                    [policy_set["attributes"]["vcs-repo"]["oauth-token-id"]]
                            }
                        },
                        "relationships": {
                        }
                    }
                }

                # Create the policy set in the new organization
                new_policy_set = api_target.policy_sets.create(new_policy_set_payload)
                policy_sets_map[policy_set["id"]] = new_policy_set["data"]["id"]
            else:
                workspace_ids = policy_set["relationships"]["workspaces"]["data"]

                for workspace_id in workspace_ids:
                    workspace_id["id"] = workspaces_map[workspace_id["id"]]

                # Build the new policy set payload
                new_policy_set_payload = {
                    "data": {
                        "type": "policy-sets",
                        "attributes": {
                            "name": policy_set["attributes"]["name"],
                            "description": policy_set["attributes"]["name"],
                            "global": policy_set["attributes"]["global"],
                            "policies-path": policy_set["attributes"]["policies-path"],
                            "vcs-repo": {
                                "branch": policy_set["attributes"]["vcs-repo"]["branch"],
                                "identifier": policy_set["attributes"]["vcs-repo"]["identifier"],
                                "ingress-submodules": policy_set\
                                    ["attributes"]["vcs-repo"]["ingress-submodules"],
                                "oauth-token-id": tfe_vcs_connection_map\
                                    [policy_set["attributes"]["vcs-repo"]["oauth-token-id"]]
                            }
                        },
                        "relationships": {
                            "workspaces": {
                                "data": workspace_ids
                            }
                        }
                    }
                }

                # Create the policy set in the new organization
                new_policy_set = api_target.policy_sets.create(new_policy_set_payload)
                policy_sets_map[policy_set["id"]] = new_policy_set["data"]["id"]
        else:
            if policy_set["attributes"]["global"]:
                policy_ids = policy_set["relationships"]["policies"]["data"]

                for policy_id in policy_ids:
                    policy_id["id"] = policies_map[policy_id["id"]]

                # Build the new policy set payload
                new_policy_set_payload = {
                    "data": {
                        "type": "policy-sets",
                        "attributes": {
                            "name": policy_set["attributes"]["name"],
                            "description": policy_set["attributes"]["name"],
                            "global": policy_set["attributes"]["global"],
                        },
                        "relationships": {
                            "policies": {
                                "data": policy_ids
                            }
                        }
                    }
                }

                # Create the policy set in the new organization
                new_policy_set = api_target.policy_sets.create(new_policy_set_payload)
                policy_sets_map[policy_set["id"]] = new_policy_set["data"]["id"]
            else:
                policy_ids = policy_set["relationships"]["policies"]["data"]
                for policy_id in policy_ids:
                    policy_id["id"] = policies_map[policy_id["id"]]

                workspace_ids = policy_set["relationships"]["workspaces"]["data"]
                for workspace_id in workspace_ids:
                    workspace_id["id"] = workspaces_map[workspace_id["id"]]

                # Build the new policy set payload
                new_policy_set_payload = {
                    "data": {
                        "type": "policy-sets",
                        "attributes": {
                            "name": policy_set["attributes"]["name"],
                            "description": policy_set["attributes"]["name"],
                            "global": policy_set["attributes"]["global"],
                        },
                        "relationships": {
                            "policies": {
                                "data": policy_ids
                            },
                            "workspaces": {
                                "data": workspace_ids
                            }
                        }
                    }
                }

                # Create the policy set in the new organization
                new_policy_set = api_target.policy_sets.create(new_policy_set_payload)
                policy_sets_map[policy_set["id"]] = new_policy_set["data"]["id"]

    return policy_sets_map


def migrate_policy_set_parameters(\
    api_source, api_target, policy_sets_map, return_sensitive_variable_data=True):
    sensitive_policy_set_parameter_data = []

    for policy_set_id in policy_sets_map:
        new_policy_set_id = policy_sets_map[policy_set_id]

        # Pull policy sets from the old organization
        policy_set_parameters = api_source.policy_set_params.list(
            policy_set_id)["data"]

        if policy_set_parameters:
            for policy_set_parameter in reversed(policy_set_parameters):
                policy_set_parameter_key = policy_set_parameter["attributes"]["key"]
                policy_set_parameter_value = policy_set_parameter["attributes"]["value"]
                policy_set_parameter_category = policy_set_parameter["attributes"]["category"]
                policy_set_parameter_sensitive = policy_set_parameter["attributes"]["sensitive"]

                # Build the new policy set parameter payload
                new_policy_parameter_payload = {
                    "data": {
                        "type": "vars",
                        "attributes": {
                            "key": policy_set_parameter_key,
                            "value": policy_set_parameter_value,
                            "category": policy_set_parameter_category,
                            "sensitive": policy_set_parameter_sensitive
                        }
                    }
                }

                # Create the policy set parameter in the new organization
                new_parameter = api_target.policy_set_params.create(
                    new_policy_set_id, new_policy_parameter_payload)["data"]
                new_parameter_id = new_parameter["id"]

                if policy_set_parameter_sensitive and return_sensitive_variable_data:
                    policy_set_name = api_target.policy_sets.show(policy_set_id)\
                        ["data"]["attributes"]["name"]

                    # Build the sensitive policy set parameter map
                    parameter_data = {
                        "policy_set_name": policy_set_name,
                        "policy_set_id": new_policy_set_id,
                        "parameter_id": new_parameter_id,
                        "parameter_key": policy_set_parameter_key,
                        "parameter_value": policy_set_parameter_value,
                        "parameter_category": policy_set_parameter_category
                    }

                    sensitive_policy_set_parameter_data.append(parameter_data)

    return sensitive_policy_set_parameter_data


"""
NOTE: The sensitive_policy_set_parameter_data_map map must be created ahead of time. The
easiest way to do this is to update the value for each variable in the list returned by
the migrate_policy_set_parameters method
"""
def migrate_policy_set_sensitive_parameters(api_target, sensitive_policy_set_parameter_data_map):
    for sensitive_policy_set_parameter in sensitive_policy_set_parameter_data_map:
        # Build the new parameter payload
        update_policy_set_parameter_payload = {
            "data": {
                "id": sensitive_policy_set_parameter["parameter_id"],
                "attributes": {
                    "key": sensitive_policy_set_parameter["parameter_key"],
                    "value": sensitive_policy_set_parameter["parameter_value"],
                    "category": "policy-set",
                    "sensitive": "true"
                },
                "type": "vars"
            }
        }

        # Update the sensitive parameter value in the policy set
        api_target.policy_set_params.update(
            sensitive_policy_set_parameter["policy_set_id"], \
                sensitive_policy_set_parameter["parameter_id"], \
                    update_policy_set_parameter_payload)

# TODO: Add support for modules uploaded via the API
def migrate_registry_modules(api_source, api_target, tfe_vcs_connection_map):
    modules = api_source.registry_modules.list()["modules"]

    for module in modules:
        # Pull VCS modules from the old organization
        module_data = api_source.registry_modules.show(module["name"], module["provider"])["data"]

        # Build the new module payload
        new_module_payload = {
            "data": {
                "attributes": {
                    "vcs-repo": {
                        "identifier": module_data["attributes"]["vcs-repo"]["identifier"],
                        "oauth-token-id": \
                            tfe_vcs_connection_map\
                                [module_data["attributes"]["vcs-repo"]["oauth-token-id"]],
                        "display_identifier": module_data\
                            ["attributes"]["vcs-repo"]["display-identifier"]
                    }
                },
                "type": "registry-modules"
            }
        }

        # Create the module in the new organization
        api_target.registry_modules.publish_from_vcs(new_module_payload)
