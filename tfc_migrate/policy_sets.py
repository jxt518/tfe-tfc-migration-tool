

def migrate(\
    api_source, api_target, tfe_vcs_connection_map, workspaces_map, policies_map):
    # Pull policy sets from the old organization
    # TODO: account for larger sizes of policy sets (more than 50)
    source_policy_sets = api_source.policy_sets.list(
        page_size=50, include="policies,workspaces")["data"]
    target_policy_sets = api_target.policy_sets.list(
        page_size=50, include="policies,workspaces")["data"]
    target_policy_set_names = \
        [target_policy_set["attributes"]["name"] for target_policy_set in target_policy_sets]

    policy_sets_map = {}
    for source_policy_set in source_policy_sets:
        source_policy_set_name = source_policy_set["attributes"]["name"]

        if source_policy_set_name in target_policy_set_names:
            print("\t", source_policy_set_name, "policy set already exists, skipping...")
            continue

        new_policy_set_payload = {
            "data": {
                "type": "policy-sets",
                "attributes": {
                    "name": source_policy_set_name,
                    # TODO: should this be description?
                    "description": source_policy_set["attributes"]["name"],
                    "global": source_policy_set["attributes"]["global"],
                    "policies-path": source_policy_set["attributes"]["policies-path"]
                },
                "relationships": {
                }
            }
        }

        if source_policy_set["attributes"]["versioned"]:
            new_policy_set_payload["data"]["attributes"]["vcs-repo"] = {
                "branch": source_policy_set["attributes"]["vcs-repo"]["branch"],
                "identifier": source_policy_set["attributes"]["vcs-repo"]["identifier"],
                "ingress-submodules": source_policy_set\
                    ["attributes"]["vcs-repo"]["ingress-submodules"],
                "oauth-token-id": tfe_vcs_connection_map\
                    [source_policy_set["attributes"]["vcs-repo"]["oauth-token-id"]]
            }

            if not source_policy_set["attributes"]["global"]:
                workspace_ids = source_policy_set["relationships"]["workspaces"]["data"]

                for workspace_id in workspace_ids:
                    workspace_id["id"] = workspaces_map[workspace_id["id"]]

                # Build the new policy set payload
                new_policy_set_payload["data"]["relationships"]["workspaces"] = {
                    "data": workspace_ids
                }
        else:
            policy_ids = source_policy_set["relationships"]["policies"]["data"]

            for policy_id in policy_ids:
                policy_id["id"] = policies_map[policy_id["id"]]

            new_policy_set_payload["data"]["relationships"]["policies"] = {
                "data": policy_ids
            }

            if not source_policy_set["attributes"]["global"]:
                workspace_ids = source_policy_set["relationships"]["workspaces"]["data"]
                for workspace_id in workspace_ids:
                    workspace_id["id"] = workspaces_map[workspace_id["id"]]

                new_policy_set_payload["data"]["relationships"]["workspaces"] = {
                    "data": workspace_ids
                }

        # Create the policy set in the new organization
        new_policy_set = api_target.policy_sets.create(new_policy_set_payload)
        policy_sets_map[policy_set["id"]] = new_policy_set["data"]["id"]

    return policy_sets_map