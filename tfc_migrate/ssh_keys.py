

# TODO: catch duplicates, clean up this file, optimize
def migrate_keys(api_source, api_target):
    print("Migrating SSH keys...")

    # Fetch SSH Keys from Existing Org
    # NOTE: This does not fetch the Keys themselves
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
            # NOTE: The actual Keys themselves must be added separately afterward
            new_ssh_key = api_target.ssh_keys.create(new_ssh_key_payload)["data"]
            ssh_keys_map[ssh_key["id"]] = new_ssh_key["id"]
            ssh_key_name_map[new_ssh_key["attributes"]["name"]] = \
                new_ssh_key["id"]

    print("SSH keys successfully migrated.")

    return ssh_keys_map, ssh_key_name_map


def migrate_key_files(api_target, ssh_key_name_map, ssh_key_file_path_map):
    """
    NOTE: The ssh_key_file_path_map must be created ahead of time with a format of
    {"ssh_key_name":"path/to/file"}
    """

    print("Migrating SSH key files...")

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

    print("SSH key files successfully migrated.")


def delete_all_keys(api_target):
    print("Deleting SSH keys...")

    ssh_keys = api_target.ssh_keys.list()["data"]
    if ssh_keys:
        for ssh_key in ssh_keys:
            api_target.ssh_keys.destroy(ssh_key['id'])

    print("SSH keys deleted.")
