

def migrate(api_source, api_target):
    print("Migrating teams...")

    # Fetch Teams from Existing Org
    source_teams = api_source.teams.list()["data"]
    target_teams = api_target.teams.list()["data"]
    target_team_names = \
        [target_team["attributes"]["name"] for target_team in target_teams]

    # TODO: not sure we can always assume the owners org will be the first in the array.
    # At the very least it"s not prudent, but it"s likely to introduce issues down the line.
    new_org_owners_team_id = source_teams[0]["id"]

    teams_map = {}
    for source_team in source_teams:
        source_team_name = source_team["attributes"]["name"]
        if source_team_name in target_team_names:
            print("\t", source_team_name, "team already exists, skipping...")
            continue

        if source_team_name == "owners":
            # No need to create a team, it's the owners team
            teams_map[source_team["id"]] = new_org_owners_team_id
        else:
            # Build the new team payload
            new_team_payload = {
                "data": {
                    "type": "teams",
                    "attributes": {
                        "name": source_team_name,
                        "organization-access": {
                            "manage-workspaces": \
                                source_team["attributes"]["organization-access"]["manage-workspaces"],
                            "manage-policies": \
                                source_team["attributes"]["organization-access"]["manage-policies"],
                            "manage-vcs-settings": \
                                source_team["attributes"]["organization-access"]["manage-vcs-settings"]
                        }
                    }
                }
            }

            # Create team in the target org
            new_team = api_target.teams.create(new_team_payload)

            # Build Team ID Map
            teams_map[team["id"]] = new_team["data"]["id"]

    print("Teams successfully migrated.")

    return teams_map


def delete_all(api_target):
    # TODO: logging
    teams = api_target.teams.list()['data']
    if teams:
        for team in teams:
            if team['attributes']['name'] != "owners":
                api_target.teams.destroy(team['id'])
