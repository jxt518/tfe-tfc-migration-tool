# TFC/E Migration Tool

This tool is designed to help automate the migration from one TFE/C Organization to another, whether that’s TFE to TFC, or vice versa.  The following migration operations are currently supported:

* Migrate Teams
* Migrate Organization Membership
   * Note: This sends out an invite to any 'active' members of the source Organization (which must be accepted by the User before they're added to the destination Organization)
* Migrate SSH Keys
    * Note: This transfers all Key names, but not Values (which are write only)
* Migrate SSH Key Files
   * Note: Prior to using this method, the `workspace_to_file_path_map` map must be manually generated using the following format: `{'ssh_key_name':'path/to/file'}`
* Migrate Agent Pools
* Migrate Workspaces
* Migrate State (Either All Versions or Current Version)
* Migrate Workspace Variables
    * Note: For any Variable marked as `Sensitive`, only Key names will be transferred (since Values are write only)
* Migrate Workspace Sensitive Variable Values
   * Note: Prior to using this method, the `sensitive_variable_data_map` map must be manually generated ahead of time. The easiest way to do this is to update the value for each variable in the list returned by the `migrate_workspace_variables` method (**Important:** If you intend on doing this, be sure to pass `True` as the final argument to `migrate_workspace_variables`)
* Migrate Workspace SSH Keys
* Migrate Workspace Run Triggers
* Migrate Workspace Notifications
  * Note: Email Notifications will be migrated, but email address are added based on Username.  If the Usernames do not exist within the New Organization at the time the Notifications are migrated, the triggers will still get migrated, but they will need to be updated once the target Users have confirmed their new Accounts.
* Migrate Workspace Team Access
* Migrate Configuration Versions
* Migrate Configuration Files
   * Note: Prior to using this method, the `workspace_to_file_path_map` map must be manually generated using the following format: `{'workspace_name':'path/to/file'}`
* Migrate Policies
* Migrate Policy Sets
* Migrate Policy Set Parameters
   * Note: For any parameter marked as `Sensitive`, only Key names will be transferred (since Values are write only)
* Migrate Policy Set Sensitive Parameter Values
   * Note: Prior to using this method, the `sensitive_policy_set_parameter_data_map` map must be manually generated ahead of time. The easiest way to do this is to update the value for each variable in the list returned by the `migrate_policy_set_parameters` method (**Important:** If you intend on doing this, be sure to pass `True` as the final argument to `migrate_policy_set_parameters`)
* Migrate Registry Modules
    * Note: Only VCS-backed Module migration is supported currently


## STEPS:
### 1. Install the Python Dependencies
```
pip3 install terrasnek==0.0.11
```

### 2. Set Required Environment Variables for both the Source Org and the New Org
```
# SOURCE ORG
TFE_TOKEN_ORIGINAL = os.getenv("TFE_TOKEN_ORIGINAL", None)
TFE_URL_ORIGINAL = os.getenv("TFE_URL_ORIGINAL", None)
TFE_ORG_ORIGINAL = os.getenv("TFE_ORG_ORIGINAL", None)

api_original = TFC(TFE_TOKEN_ORIGINAL, url=TFE_URL_ORIGINAL)
api_original.set_org(TFE_ORG_ORIGINAL)

# NEW ORG
TFE_TOKEN_NEW = os.getenv("TFE_TOKEN_NEW", None)
TFE_URL_NEW = os.getenv("TFE_URL_NEW", None)
TFE_ORG_NEW = os.getenv("TFE_ORG_NEW", None)
TFE_VCS_CONNECTION_MAP = ast.literal_eval(os.getenv("TFE_VCS_CONNECTION_MAP", None))

api_new = TFC(TFE_TOKEN_NEW, url=TFE_URL_NEW)
api_new.set_org(TFE_ORG_NEW)
```
Note:
* The Token(s) used above must be either a Team or User Token and have the appropriate level of permissions
* The URL(s) used above must follow a format of `https://app.terraform.io`
* The `TFE_VCS_CONNECTION_MAP` will need to be built manually prior to running the migration.  This should be a dict that maps all of the Source Org OAuth Token values to the Destination Org OAuth Token values.  Note that GitHub App connections are not currently supported in this migration tool since those values can not currently be managed via the API.


### 3. Select Desired Functions

Choose which components you want to migrate and comment out any others in [`migration.py`](migration.py).  For example, you may choose whether you want to `migrate_all_state` for your Workspaces or `migrate_current_state`, but you should not select both.  For more insight into what each function does, please refer to the contents of[`functions.py`](functions.py).

### 4. Run the Migration Script
```
python migration.py
```

### NOTES
This migration utility leverages the [Terraform Cloud/Enterprise API](https://www.terraform.io/docs/cloud/api/index.html) and the [terrasnek](https://github.com/dahlke/terrasnek) Python Client for interacting with it.  For security reasons, there are certain Sensitive values that cannot be extracted (ex. Sensitive Variables, Sensitive Policy Set Parameters, and SSH Keys), so those will need to be re-added after the migration is complete (the Keys will, however, be migrated).  For convenience, additional methods have been included to enable Sensitive value migration (Sensitive Variables, Sensitive Policy Set Parameters, and SSH Keys).

**IMPORTANT:** These scripts expect that the destination Organization (i.e TFE_ORG_NEW) is a blank slate and has not had any changes made ahead of time through other means.  If changes have been made to the new Organization prior to using this tool, errors are likely to occur.

If needed (ex. for testing purposes), a set of helper delete functions have been included as well in [`delete_functions.py`](delete_functions.py).
