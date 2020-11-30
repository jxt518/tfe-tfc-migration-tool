

def migrate(api_source, api_target, tfe_vcs_connection_map, agent_pools_map, TFE_URL_TARGET):
    print("Migrating workspaces...")

    # Fetch workspaces from existing org
    source_workspaces = api_source.workspaces.list()["data"]
    target_workspaces = api_target.workspaces.list()["data"]
    
    target_workspaces_data = {}
    for target_workspace in target_workspaces:
        target_workspaces_data[target_workspace["attributes"]["name"]] = target_workspace["id"]

    workspaces_map = {}
    workspace_to_ssh_key_map = {}

    for source_workspace in source_workspaces:
        source_workspace_name = source_workspace["attributes"]["name"]
        source_workspace_id = source_workspace["id"]

        if source_workspace_name in target_workspaces_data:
            workspaces_map[source_workspace_id] = target_workspaces_data[source_workspace_name]
            print("\t", source_workspace_name, "workspace already exists, skipping...")
            continue

        branch = "" if source_workspace["attributes"]["vcs-repo"] is None \
            else source_workspace["attributes"]["vcs-repo"]["branch"]

        ingress_submodules = False if source_workspace["attributes"]["vcs-repo"] is None \
            else source_workspace["attributes"]["vcs-repo"]["ingress-submodules"]

        default_branch = True if branch == "" else False

        new_workspace_payload = {
            "data": {
                "attributes": {
                    "name": source_workspace_name,
                    "terraform_version": source_workspace["attributes"]["terraform-version"],
                    "working-directory": source_workspace["attributes"]["working-directory"],
                    "file-triggers-enabled": \
                        source_workspace["attributes"]["file-triggers-enabled"],
                    "allow-destroy-plan": source_workspace["attributes"]["allow-destroy-plan"],
                    "auto-apply": source_workspace["attributes"]["auto-apply"],
                    "execution-mode": source_workspace["attributes"]["execution-mode"],
                    "description": source_workspace["attributes"]["description"],
                    "source-name": source_workspace["attributes"]["source-name"], 
                    "source-url": source_workspace["attributes"]["source-url"],
                    "queue-all-runs": source_workspace["attributes"]["queue-all-runs"],
                    "speculative-enabled": source_workspace["attributes"]["speculative-enabled"],
                    "trigger-prefixes": source_workspace["attributes"]["trigger-prefixes"],
                },
                "type": "workspaces"
            }
        }

        # Set agent pool ID unless target is TFE
        if source_workspace["attributes"]["execution-mode"] == "agent" and 'app.terraform.io' in TFE_URL_TARGET:
            new_workspace_payload["data"]["attributes"]["agent-pool-id"] = agent_pools_map[source_workspace["relationships"]["agent-pool"]["data"]["id"]]

        if source_workspace["attributes"]["vcs-repo"] is not None:
            new_workspace_payload["data"]["attributes"]["vcs-repo"] = {
                "identifier": source_workspace["attributes"]["vcs-repo-identifier"],
                "oauth-token-id": tfe_vcs_connection_map\
                    [source_workspace["attributes"]["vcs-repo"]["oauth-token-id"]],
                "branch": branch,
                "default-branch": default_branch,
                "ingress-submodules": ingress_submodules
            }

        # Build the new workspace
        new_workspace = api_target.workspaces.create(new_workspace_payload)
        new_workspace_id = new_workspace["data"]["id"]
        workspaces_map[workspace["id"]] = new_workspace_id

        try:
            ssh_key = workspace["relationships"]["ssh-key"]["data"]["id"]
            workspace_to_ssh_key_map[workspace["id"]] = ssh_key
        except:
            # TODO
            continue

    print("Workspaces successfully migrated.")
    return workspaces_map, workspace_to_ssh_key_map


def migrate_ssh_keys(\
        api_source, api_target, workspaces_map, workspace_to_ssh_key_map, \
            ssh_keys_map):

    print("Migrating SSH keys for workspaces...")

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
            api_target.workspaces.assign_ssh_key(\
                workspaces_map[key], new_workspace_ssh_key_payload)

    print("SSH keys for workspaces successfully migrated.")


def delete_all(api_target):
    # TODO: logging
    workspaces = api_target.workspaces.list()['data']

    if workspaces:
        for workspace in workspaces:
            api_target.workspaces.destroy(workspace['id'])
