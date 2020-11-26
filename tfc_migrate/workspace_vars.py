

# TODO: catch duplicates, clean up this file, optimize
def migrate(\
        api_source, api_target, workspaces_map, \
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


def migrate_sensitive(api_target, sensitive_variable_data_map):
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


def delete_all(api_target):
    workspaces = api_target.workspaces.list()['data']

    for workspace in workspaces:
        variables = api_target.workspace_vars.list(workspace['id'])['data']
        for variable in variables:
            api_target.workspace_vars.destroy(workspace['id'], variable['id'] )
