

def migrate(api_source, api_target, tfe_token_original, tfe_url_original):
    # Pull policies from the old organization
    source_policies = api_source.policies.list()["data"]
    target_policies = api_target.policies.list()["data"]
    target_policy_names = \
        [target_policy["attributes"]["name"] for target_policy in target_policies]
    policies_map = {}

    if source_policies:
        for source_policy in source_policies:
            source_policy_name = source_policy["attributes"]["name"],
            if source_policy_name in target_policy_names:
                print("\t", source_policy_name, "policy already exists, skipping...")
                continue
            source_policy_id = source_policy["id"]

            headers = {
                "Authorization": "Bearer %s" % (tfe_token_original),
                "Content-Type": "application/vnd.api+json"
            }
            policy_download_url = "%s/api/v2/policies/%s/download" % \
                (tfe_url_original, source_policy_id)

            # Retrieve the policy content
            policy_request = urllib.request.Request(policy_download_url, headers=headers)
            pull_policy = urllib.request.urlopen(policy_request)
            policy_data = pull_policy.read()
            policy_b64 = policy_data.decode("utf-8")

            # Build the new policy payload
            new_policy_payload = {
                "data": {
                    "attributes": {
                        "name": source_policy_name,
                        "description": source_policy["attributes"]["description"],
                        "enforce": [
                            {
                                "path": source_policy["attributes"]["enforce"][0]["path"],
                                "mode": source_policy["attributes"]["enforce"][0]["mode"]
                            }
                        ],
                    },
                    "type": "policies"
                }
            }

            new_policy_id = None

            # Create the policy in the new organization
            new_policy = api_target.policies.create(new_policy_payload)
            new_policy_id = new_policy["data"]["id"]
            policies_map[policy_id] = new_policy_id

            # Upload the policy content to the new policy in the new organization
            api_target.policies.upload(new_policy_id, policy_b64)

    return policies_map
