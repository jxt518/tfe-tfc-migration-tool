from urllib import request

def migrate(api_source, api_target, TFE_TOKEN_SOURCE, TFE_URL_SOURCE):

    print("Migrating policies...")

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
                "Authorization": "Bearer %s" % (TFE_TOKEN_SOURCE),
                "Content-Type": "application/vnd.api+json"
            }
            policy_download_url = "%s/api/v2/policies/%s/download" % \
                (TFE_URL_SOURCE, source_policy_id)

            # Retrieve the policy content
            policy_request = request.Request(policy_download_url, headers=headers)
            pull_policy = request.urlopen(policy_request)
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

    print("policies successfully migrated.")

    return policies_map


def delete_all(api_target):
    # TODO: logging
    policies = api_target.policies.list()['data']

    if policies:
        for policy in policies:
            api_target.policies.destroy(policy['id'])
