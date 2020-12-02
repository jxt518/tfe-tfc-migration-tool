

def migrate(api_source, api_target, workspaces_map):
    print("Migrating notification configs...")

    for workspace_id in workspaces_map:
        # Pull notifications from the old workspace
        notifications = api_source.notification_configs.list(workspace_id)["data"]

        # TODO: catch duplicates
        # TODO: optimize building the payload

        for notification in notifications:
            notification_name = notification["attributes"]["name"]
            if notification["attributes"]["destination-type"] == "email":
                # Build the new notification payload
                new_notification_payload = {
                    "data": {
                        "type": "notification-configurations",
                        "attributes": {
                            "destination-type": notification["attributes"]["destination-type"],
                            "enabled": notification["attributes"]["enabled"],
                            "name": notification_name,
                            "triggers": notification["attributes"]["triggers"]
                        },
                        "relationships": {
                            "users": {
                                "data":  notification["relationships"]["users"]["data"]
                            }
                        }
                    }
                }

                # Add notifications to the target workspace
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
                            "name": notification_name,
                            "token": notification["attributes"]["token"],
                            "url": notification["attributes"]["url"],
                            "triggers": notification["attributes"]["triggers"]
                        }
                    }
                }

                # Add notifications to the target workspace
                api_target.notification_configs.create( \
                    workspaces_map[workspace_id], new_notification_payload)

                print(f"\t notification config %s created..." % notification_name)

    print("Notification configs successfully migrated.")


def delete_all(api_target):
    print("Deleting notification configs...")

    workspaces = api_target.workspaces.list()["data"]

    for workspace in workspaces:
        notifications = api_target.notification_configs.list(workspace["id"])["data"]

        for notification in notifications:
            print(f"\t deleting notification config %s created..." % notification["attributes"]["name"])
            api_target.notification_configs.destroy(notification["id"])

    print("Notification configs deleted.")