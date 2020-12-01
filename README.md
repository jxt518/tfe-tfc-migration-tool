# TFC/E Migration Tool

This tool is designed to help automate the migration from one TFE/l Organization to another, whether that’s TFE to TFC, or vice versa.

## Steps

### 1. Install the Python Dependencies

```bash
pip3 install terrasnek==0.0.11
```

### 2. Set Required Environment Variables for both the Source Org and the New Org

```bash
# Source Org
export TFE_TOKEN_SOURCE="foo"
export TFE_URL_SOURCE="https://app.terraform.io"
export TFE_ORG_SOURCE="bar"

# Target Org
export TFE_TOKEN_TARGET="foo"
export TFE_URL_TARGET="https://app.terraform.io"
export TFE_ORG_TARGET="bar"

export TFE_VCS_CONNECTION_MAP={\"source\": \"ot-foo\", \"target\" :\"ot-bar\"}
```

NOTE:

* The Token(s) used above must be either a Team or User Token and have the appropriate level of permissions
* The URL(s) used above must follow a format of `https://app.terraform.io`
* The `TFE_VCS_CONNECTION_MAP` will need to be built manually prior to running the migration.  This should be a dict that maps all of the Source Org OAuth Token values to the Destination Org OAuth Token values.  NOTE that GitHub App connections are not currently supported in this migration tool since those values can not currently be managed via the API.

### 3. Select Desired Functions

- TODO: add these as flags?

Choose which components you want to migrate and comment out any others in [`migration.py`](migration.py).  For example, you may choose whether you want to `migrate_all_state` for your Workspaces or `migrate_current_state`, but you should not select both.  For more insight into what each function does, please refer to the contents of[`functions.py`](functions.py).

### 4. Run the Migration Script

```bash
python migration.py
```

## Supported Operations

The following migration operations are currently supported:

* Migrate Teams
* Migrate Organization Membership
   * NOTE: This sends out an invite to any 'active' members of the source Organization (which must be accepted by the User before they're added to the destination Organization)
* Migrate SSH Keys
    * NOTE: This transfers all Key names, but not Values (which are write only)
* Migrate SSH Key Files
   * NOTE: Prior to using this method, the `workspace_to_file_path_map` map must be manually generated using the following format: `{'ssh_key_name':'path/to/file'}`
* Migrate Agent Pools
* Migrate Workspaces
* Migrate State (Either All Versions or Current Version)
* Migrate Workspace Variables
    * NOTE: For any Variable marked as `Sensitive`, only Key names will be transferred (since Values are write only)
* Migrate Workspace Sensitive Variable Values
   * NOTE: Prior to using this method, the `sensitive_variable_data_map` map must be manually generated ahead of time. The easiest way to do this is to update the value for each variable in the list returned by the `migrate_workspace_variables` method (**Important:** If you intend on doing this, be sure to pass `True` as the final argument to `migrate_workspace_variables`)
* Migrate Workspace SSH Keys
* Migrate Workspace Run Triggers
* Migrate Workspace Notifications
  * NOTE: Email Notifications will be migrated, but email address are added based on Username.  If the Usernames do not exist within the target organization at the time the Notifications are migrated, the triggers will still get migrated, but they will need to be updated once the target Users have confirmed their new Accounts.
* Migrate Workspace Team Access
* Migrate Config Versions
* Migrate Config Files
   * NOTE: Prior to using this method, the `workspace_to_file_path_map` map must be manually generated using the following format: `{'workspace_name':'path/to/file'}`
* Migrate Policies
* Migrate Policy Sets
* Migrate Policy Set params
   * NOTE: For any parameter marked as `Sensitive`, only Key names will be transferred (since Values are write only)
* Migrate Policy Set Sensitive Parameter Values
   * NOTE: Prior to using this method, the `sensitive_policy_set_parameter_data_map` map must be manually generated ahead of time. The easiest way to do this is to update the value for each variable in the list returned by the `migrate_policy_set_parameters` method (**Important:** If you intend on doing this, be sure to pass `True` as the final argument to `migrate_policy_set_parameters`)
* Migrate Registry Modules
    * NOTE: Only VCS-backed Module migration is supported currently


### NOTES

This migration utility leverages the [Terraform Cloud/Enterprise API](https://www.terraform.io/docs/cloud/api/index.html) and the [terrasnek](https://github.com/dahlke/terrasnek) Python Client for interacting with it.  For security reasons, there are certain Sensitive values that cannot be extracted (ex. Sensitive Variables, Sensitive Policy Set params, and SSH Keys), so those will need to be re-added after the migration is complete (the Keys will, however, be migrated).  For convenience, additional methods have been included to enable Sensitive value migration (Sensitive Variables, Sensitive Policy Set params, and SSH Keys).

**IMPORTANT:** These scripts expect that the destination Organization (i.e TFE_ORG_TARGET) is a blank slate and has not had any changes made ahead of time through other means.  If changes have been made to the target organization prior to using this tool, errors are likely to occur.

### TODO

- add the new flag migrate / delete logic
- verify that all these steps can be copy pasted.
