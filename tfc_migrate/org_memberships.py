

# TODO: catch duplicates, clean up this file, optimize
def migrate(api_source, api_target, teams_map):
    print("Migrating org memberships...")

    org_membership_map = {}
    # Set proper membership filters
    member_filters = [
        {
            "keys": ["status"],
            "value": "active"
        }
    ]

    org_members = api_source.org_memberships.list_for_org( \
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
            new_org_member = api_target.org_memberships.invite( \
                new_user_invite_payload)["data"]
        except:
            org_membership_map[org_member["relationships"]["user"]["data"]["id"]] = \
                org_member["relationships"]["user"]["data"]["id"]

        new_user_id = new_org_member["relationships"]["user"]["data"]["id"]
        org_membership_map[org_member["relationships"]["user"]["data"]["id"]] = \
            new_user_id

    print("Org memberships migrated.")

    return org_membership_map

# TODO: delete function w logging