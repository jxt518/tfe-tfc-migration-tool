import base64
import hashlib
import json
from urllib import request

# TODO: catch duplicates, clean up this file, optimize
# TODO: get rid of all state function if we aren't going to use it
def migrate_all(api_source, api_target, TFE_ORG_SOURCE, workspaces_map):
    # TODO: logging
    # TODO: get rid of this function if we aren't using it
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
                "value": TFE_ORG_SOURCE
            }
        ]

        state_versions = api_source.state_versions.list(
            filters=state_filters)["data"]
        if state_versions:
            for state_version in reversed(state_versions):
                state_url = state_version["attributes"]["hosted-state-download-url"]
                pull_state = request.urlopen(state_url)
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


def migrate_current(api_source, api_target, TFE_ORG_SOURCE, workspaces_map):

    print("Migrating current state versions...")

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
                "value": TFE_ORG_SOURCE
            }
        ]

        state_versions = api_source.state_versions.list(
            filters=state_filters)["data"]
        if state_versions:
            current_version = api_source.state_versions.get_current(workspace_id)[
                "data"]
            state_url = current_version["attributes"]["hosted-state-download-url"]
            pull_state = request.urlopen(state_url)
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

    print("Current state versions successfully migrated.")

# TODO: delete function w logging
