

# TODO: catch duplicates, clean up this file, optimize
# TODO: is this different than the workspace_notifications file?
def migrate(api_source, api_target, workspaces_map):
    for workspace_id in workspaces_map:
        # Pull notifications from the old workspace
        notifications = api_source.notification_configs.list(workspace_id)["data"]

        if notifications:
            for notification in notifications:
                if notification["attributes"]["destination-type"] == "email":
                    # Build the new notification payload
                    new_notification_payload = {
                        "data": {
                            "type": "notification-configurations",
                            "attributes": {
                                "destination-type": notification["attributes"]["destination-type"],
                                "enabled": notification["attributes"]["enabled"],
                                "name": notification["attributes"]["name"],
                                "triggers": notification["attributes"]["triggers"]
                            },
                            "relationships": {
                                "users": {
                                    "data":  notification["relationships"]["users"]["data"]
                                }
                            }
                        }
                    }

                    # Add notifications to the new workspace
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
                                "name": notification["attributes"]["name"],
                                "token": notification["attributes"]["token"],
                                "url": notification["attributes"]["url"],
                                "triggers": notification["attributes"]["triggers"]
                            }
                        }
                    }

                    # Add notifications to the new workspace
                    api_target.notification_configs.create(\
                        workspaces_map[workspace_id], new_notification_payload)


def delete_all(api_target):
    workspaces = api_target.workspaces.list()['data']

    for workspace in workspaces:
        notifications = api_target.notification_configs.list(workspace['id'])['data']

        if notifications:
            for notification in notifications:
                api_target.notification_configs.destroy(notification['id'])

