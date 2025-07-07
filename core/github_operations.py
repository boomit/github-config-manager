import subprocess
import sys
import threading
import time

from utils.utils import (
    execute_subprocess_command,
    parse_json_string,
)

from utils.logs import (
    add_log_entry,
)


def _get_existing_items_from_repo(repo_name: str, item_type: str) -> set:
    """
    Retrieves a list of Secrets or Variables for a given repository via GH CLI.

    Args:
        repo_name (str): The name of the repository (e.g., 'owner/repo').
        item_type (str): The type of item to retrieve ('secret' or 'variable').

    Returns:
        set: A set of item names.
    """
    if item_type == 'secret':
        command = ['gh', 'secret', 'list', '--repo', repo_name, '--json', 'name']
        context_label = "Secret"
    elif item_type == 'variable':
        command = ['gh', 'variable', 'list', '--repo', repo_name, '--json', 'name']
        context_label = "Variable"
    else:
        add_log_entry(repo_name, f"❌ Error: Unknown item type '{item_type}'. Must be 'secret' or 'variable'.")
        return set()

    try:
        stdout_str = run_gh_command(command, repo_name)
        
        if not stdout_str: # If empty string or None
            add_log_entry(repo_name, f"[{repo_name}] Warning: {context_label} list for repository '{repo_name}' is empty or could not be retrieved.")
            return set()

        data = parse_json_string(stdout_str, f"{context_label} list for repository '{repo_name}'")
        
        if data is None: # If JSON parsing failed
            add_log_entry(repo_name, f"[{repo_name}] Warning: Failed to parse {context_label} JSON for repository '{repo_name}'.")
            return set()

        # Extract names and return as a set
        return {item['name'] for item in data if 'name' in item} # Ensure 'name' key exists
    except Exception as e:
        # GH CLI might return an error if no Secrets/Variables exist, so warn and return empty set
        add_log_entry(repo_name, f"[{repo_name}] Warning: Failed to retrieve {context_label} list for repository '{repo_name}': {e}")
        return set()


def _log_and_fetch_existing_repo_items(repo_name: str) -> tuple[set, set]:
    """
    Fetches existing Secret and Variable lists for a repository, logs them, and returns them.
    """
    log_prefix = f"[{repo_name}]"

    # Fetch and log existing Secrets
    existing_secrets = list_repository_secrets(repo_name)
    if existing_secrets:
        add_log_entry(repo_name, f"{log_prefix} 🔑 Existing Secrets: {', '.join(sorted(list(existing_secrets)))}")
    else:
        add_log_entry(repo_name, f"{log_prefix} 🔑 No existing Secrets found.")
    
    # Fetch and log existing Variables
    existing_variables = list_repository_variables(repo_name)
    if existing_variables:
        add_log_entry(repo_name, f"{log_prefix} ⚙️ Existing Variables: {', '.join(sorted(list(existing_variables)))}")
    else:
        add_log_entry(repo_name, f"{log_prefix} ⚙️ No existing Variables found.")
    
    return existing_secrets, existing_variables


def run_gh_command(command: list, repo_name: str = None) -> str:
    """
    Executes a GitHub CLI command and returns its standard output.
    Handles common errors like 404 for non-existent secrets/variables during deletion.

    Args:
        command (list): The command and its arguments to execute.
        repo_name (str | None): The repository name relevant to the command, for logging.

    Returns:
        str: The decoded standard output of the command.

    Raises:
        subprocess.CalledProcessError: If the command returns a non-zero exit code for unhandled errors.
        FileNotFoundError: If the 'gh' executable is not found.
        ValueError: If a secret/variable value is missing for set operations.
        Exception: For any other unexpected errors.
    """
    log_prefix = f"[{repo_name}] " if repo_name else ""
    try:
        stdout_decoded, stderr_decoded = execute_subprocess_command(command, False)
        
        if stderr_decoded:
            add_log_entry(repo_name, f"{log_prefix}DEBUG: STDERR: '{stderr_decoded}'")

        return stdout_decoded
    except subprocess.CalledProcessError as e:
        error_stderr = e.stderr.decode('utf-8', errors='replace').strip() if e.stderr else ""
        
        if "HTTP 404" in error_stderr and ("secret delete" in ' '.join(command) or "variable delete" in ' '.join(command)):
            add_log_entry(repo_name, f"{log_prefix}Warning: HTTP 404 - Item does not exist, cannot delete. Proceeding to next step.")
            return "" # Return empty string for 404 on delete, as it's not a hard error
        if "flag needs an argument: --body" in error_stderr:
            add_log_entry(repo_name, f"{log_prefix}❌ Error: '--body' argument missing value. Value might be empty.")
            raise ValueError("Secret/Variable value missing error") from e
        
        add_log_entry(repo_name, f"{log_prefix}Fatal error occurred (GH CLI command execution): {e}. Stderr: {error_stderr}")
        raise 
    except FileNotFoundError:
        add_log_entry(repo_name, f"{log_prefix}❌ GitHub CLI (gh) not found. Please ensure it is installed and in your PATH.")
        raise FileNotFoundError("GitHub CLI (gh) not found") from None
    except Exception as e:
        add_log_entry(repo_name, f"{log_prefix}❌ An unexpected error occurred during gh command execution: {e}")
        raise e


def delete_github_secret(repo_name: str, secret_name: str) -> bool:
    """Deletes a Secret from the specified repository."""
    command = ['gh', 'secret', 'delete', secret_name, '--repo', repo_name]
    try:
        add_log_entry(repo_name, f"[{repo_name}] Deleting Secret '{secret_name}'...")
        run_gh_command(command, repo_name) 
        add_log_entry(repo_name, f"[{repo_name}] ✅ Successfully deleted Secret '{secret_name}'.")
        return True
    except Exception as e:
        add_log_entry(repo_name, f"[{repo_name}] ❌ Failed to delete Secret '{secret_name}': {e}")
        return False

def delete_github_variable(repo_name: str, var_name: str) -> bool:
    """Deletes a Variable from the specified repository."""
    command = ['gh', 'variable', 'delete', var_name, '--repo', repo_name]
    try:
        add_log_entry(repo_name, f"[{repo_name}] Deleting Variable '{var_name}'...")
        run_gh_command(command, repo_name)
        add_log_entry(repo_name, f"[{repo_name}] ✅ Successfully deleted Variable '{var_name}'.")
        return True
    except Exception as e:
        add_log_entry(repo_name, f"[{repo_name}] ❌ Failed to delete Variable '{var_name}': {e}")
        return False


def set_github_secret(repo_name: str, secret_name: str, secret_value: str, force: bool, existing_secrets: set) -> bool:
    """
    Sets/updates a Secret in the specified repository.
    If 'force' is True, it will set unconditionally; otherwise, it skips if the secret already exists.
    'existing_secrets' is a pre-fetched list of existing secrets.
    """
    try:
        if not force and secret_name in existing_secrets:
            add_log_entry(repo_name, f"[{repo_name}] Warning: Secret '{secret_name}' already exists. Skipping (no update) as '--force' option is not enabled.")
            return True 

        add_log_entry(repo_name, f"[{repo_name}] Setting/updating Secret '{secret_name}'...")
        command = ['gh', 'secret', 'set', secret_name, '--repo', repo_name, '--body', secret_value]
        run_gh_command(command, repo_name)
        add_log_entry(repo_name, f"[{repo_name}] ✅ Successfully set/updated Secret '{secret_name}'.")
        return True
    except Exception as e:
        add_log_entry(repo_name, f"[{repo_name}] ❌ Failed to set/update Secret '{secret_name}': {e}")
        return False


def set_github_variable(repo_name: str, var_name: str, var_value: str, force: bool, existing_variables: set) -> bool:
    """
    Sets/updates a Variable in the specified repository.
    If 'force' is True, it will set unconditionally; otherwise, it skips if the variable already exists.
    'existing_variables' is a pre-fetched list of existing variables.
    """
    try:
        if not force and var_name in existing_variables:
            add_log_entry(repo_name, f"[{repo_name}] Warning: Variable '{var_name}' already exists. Skipping (no update) as '--force' option is not enabled.")
            return True 

        add_log_entry(repo_name, f"[{repo_name}] Setting/updating Variable '{var_name}'...")
        command = ['gh', 'variable', 'set', var_name, '--repo', repo_name, '--body', var_value]
        run_gh_command(command, repo_name)
        add_log_entry(repo_name, f"[{repo_name}] ✅ Successfully set/updated Variable '{var_name}'.")
        return True
    except Exception as e:
        add_log_entry(repo_name, f"[{repo_name}] ❌ Failed to set/update Variable '{var_name}': {e}")
        return False


def get_repositories_from_github(organization_name: str) -> list[str]:
    """
    Retrieves a list of all public and private repositories for a given GitHub organization or user.
    """
    # repo_name is None for global messages
    add_log_entry(None, f"⚙️ Fetching repository list for GitHub organization/user '{organization_name}'...")
    all_repositories = set()

    # Fetch public repositories
    public_repo_command = ["gh", "repo", "list", organization_name, "--json", "name,owner", "-L", "9999", "--visibility", "public"]
    try:
        public_repo_list_json_str = run_gh_command(public_repo_command)
        if public_repo_list_json_str:
            public_repos_data = parse_json_string(public_repo_list_json_str, "[Global] Public Repository JSON Parsing")
            if public_repos_data:
                for repo in public_repos_data:
                    all_repositories.add(f"{repo['owner']['login']}/{repo['name']}")
                add_log_entry(None, f"    ✔️ Added {len(public_repos_data)} public repositories.")
    except Exception as e:
        add_log_entry(None, f"❌ Failed to fetch public repository list: {e}")
        pass # Continue even if public repo fetching fails

    # Fetch private repositories
    private_repo_command = ["gh", "repo", "list", organization_name, "--json", "name,owner", "-L", "9999", "--visibility", "private"]
    try:
        private_repo_list_json_str = run_gh_command(private_repo_command)
        if private_repo_list_json_str:
            private_repos_data = parse_json_string(private_repo_list_json_str, "[Global] Private Repository JSON Parsing")
            if private_repos_data:
                for repo in private_repos_data:
                    all_repositories.add(f"{repo['owner']['login']}/{repo['name']}")
                add_log_entry(None, f"    ✔️ Added {len(private_repos_data)} private repositories.")
    except Exception as e:
        add_log_entry(None, f"❌ Failed to fetch private repository list: {e}")
        pass # Continue even if private repo fetching fails

    final_repositories = sorted(list(all_repositories))
    if not final_repositories:
        add_log_entry(None, f"⚠️ Warning: No repositories found to process for organization/user '{organization_name}'.")
        return []
    else:
        add_log_entry(None, f"✅ Successfully fetched {len(final_repositories)} repositories from '{organization_name}'.")
        return final_repositories
        
def list_repository_secrets(repo_name: str) -> set:
    """Returns a set of Secret names for the repository."""
    return _get_existing_items_from_repo(repo_name, 'secret')

def list_repository_variables(repo_name: str) -> set:
    """Returns a set of Variable names for the repository."""
    return _get_existing_items_from_repo(repo_name, 'variable')


def process_single_repository(
    repo_name: str,
    delete_secrets_list: list,
    delete_variables_list: list,
    secrets_to_set_dict: dict,
    variables_to_set_dict: dict,
    force: bool
) -> bool:
    """
    Processes a single repository by deleting specified secrets/variables
    and setting/updating others.

    Args:
        repo_name (str): The full name of the repository (e.g., 'owner/repo').
        delete_secrets_list (list): List of secret names to delete.
        delete_variables_list (list): List of variable names to delete.
        secrets_to_set_dict (dict): Dictionary of secret_name: secret_value to set/update.
        variables_to_set_dict (dict): Dictionary of variable_name: variable_value to set/update.
        force (bool): If True, existing secrets/variables will be overwritten.

    Returns:
        bool: True if all operations for the repository were successful, False otherwise.
    """
    log_prefix = f"[{repo_name}]"
    overall_success = True

    try:
        # Fetch and log existing Secret and Variable lists once
        existing_secrets, existing_variables = _log_and_fetch_existing_repo_items(repo_name)

        # Delete secrets
        if delete_secrets_list:
            # Only delete secrets that are in both the delete_secrets_list AND existing_secrets
            secrets_to_actually_delete = set(delete_secrets_list).intersection(existing_secrets)
            
            if secrets_to_actually_delete:
                add_log_entry(repo_name, f"{log_prefix}    Secrets to delete (existing and requested): {list(secrets_to_actually_delete)}")
                for secret_name in secrets_to_actually_delete:
                    if not delete_github_secret(repo_name, secret_name):
                        overall_success = False
            else:
                add_log_entry(repo_name, f"{log_prefix}    No secrets found to delete from the repository (intersection with requested list is empty).")
        # else:
        #    add_log_entry(repo_name, f"{log_prefix}    No secrets requested for deletion.")

        # Delete variables
        if delete_variables_list:
            # Only delete variables that are in both the delete_variables_list AND existing_variables
            variables_to_actually_delete = set(delete_variables_list).intersection(existing_variables)

            if variables_to_actually_delete:
                add_log_entry(repo_name, f"{log_prefix}    Variables to delete (existing and requested): {list(variables_to_actually_delete)}")
                for var_name in variables_to_actually_delete:
                    if not delete_github_variable(repo_name, var_name):
                        overall_success = False
            else:
                add_log_entry(repo_name, f"{log_prefix}    No variables found to delete from the repository (intersection with requested list is empty).")
        # else:
        #    add_log_entry(repo_name, f"{log_prefix}    No variables requested for deletion.")


        # Fetch and log existing Secret and Variable lists once
        existing_secrets, existing_variables = _log_and_fetch_existing_repo_items(repo_name)


        # Set/Update secrets
        if secrets_to_set_dict:
            add_log_entry(repo_name, f"{log_prefix}    Secrets to set/update: {list(secrets_to_set_dict.keys())}")
            for secret_name, secret_value in secrets_to_set_dict.items():
                if not set_github_secret(repo_name, secret_name, secret_value, force=force, existing_secrets=existing_secrets):
                    overall_success = False
        # else:
        #    add_log_entry(repo_name, f"{log_prefix}    No secrets to set.")

        # Set/Update variables
        if variables_to_set_dict:
            add_log_entry(repo_name, f"{log_prefix}    Variables to set/update: {list(variables_to_set_dict.keys())}")
            for var_name, var_value in variables_to_set_dict.items():
                if not set_github_variable(repo_name, var_name, var_value, force=force, existing_variables=existing_variables):
                    overall_success = False
        # else:
        #    add_log_entry(repo_name, f"{log_prefix}    No variables to set.")
        

        if overall_success:
            add_log_entry(repo_name, f"{log_prefix} ✅ Successfully processed repository '{repo_name}'.")
        else:
            add_log_entry(repo_name, f"{log_prefix} ❌ Some operations failed for repository '{repo_name}'.")
            
        return overall_success

    except Exception as e:
        add_log_entry(repo_name, f"{log_prefix} ❌ A fatal error occurred while processing repository '{repo_name}': {e}")
        add_log_entry(repo_name, f"{log_prefix} 💀 Repository '{repo_name}' operation failed.")
        return False
    


def display_and_confirm_actions(
    delete_secrets_list: list,
    delete_variables_list: list,
    secrets_to_set_dict: dict,
    variables_to_set_dict: dict,
    repositories: list,
    sleep_time: int,
    max_workers: int,
    force: bool
):
    """
    Displays a summary of GitHub operations to the user and asks for confirmation to proceed.
    All output is handled via 'add_log_entry'.
    """
    # Set repo_name to None for global messages.
    add_log_entry(None, "\n" + "=" * 50)
    add_log_entry(None, "🚨 Please CONFIRM the following GitHub operations 🚨")
    add_log_entry(None, "=" * 50)

    add_log_entry(None, "\nSecrets to Delete:")
    if delete_secrets_list:
        for secret in delete_secrets_list:
            add_log_entry(None, f"  - {secret}")
    else:
        add_log_entry(None, "  (None)")

    add_log_entry(None, "\nVariables to Delete:")
    if delete_variables_list:
        for var in delete_variables_list:
            add_log_entry(None, f"  - {var}")
    else:
        add_log_entry(None, "  (None)")

    add_log_entry(None, "\nSecrets to Add/Update:")
    if secrets_to_set_dict:
        for secret_name in secrets_to_set_dict.keys():
            add_log_entry(None, f"  - {secret_name}")
    else:
        add_log_entry(None, "  (None)")

    add_log_entry(None, "\nVariables to Add/Update:")
    if variables_to_set_dict:
        for var_name in variables_to_set_dict.keys():
            add_log_entry(None, f"  - {var_name}")
    else:
        add_log_entry(None, "  (None)")

    add_log_entry(None, "\nTarget Repositories:")
    if repositories:
        for repo in repositories:
            add_log_entry(None, f"  - {repo}")
    else:
        add_log_entry(None, "  (None - potential error)")
    add_log_entry(None, f"\nTotal {len(repositories)} repositories.")

    if max_workers == 1:
        add_log_entry(None, f"\nWill pause {sleep_time} seconds after processing each repository.")
    else:
        add_log_entry(None, f"\nWill process {max_workers} repositories concurrently.")

    add_log_entry(None, f"\n💡 '--force' option enabled: {'Yes' if force else 'No'}")
    if force:
        add_log_entry(None, "    (When setting Secrets/Variables, existing ones will be overwritten.)")
    else:
        add_log_entry(None, "    (When setting Secrets/Variables, new ones will be added; existing ones will be skipped.)")

    add_log_entry(None, "\n" + "=" * 50)

    while True:
        add_log_entry(None, "Do you want to proceed? (Y/N): ", is_prompt=True)
        confirm = input().strip().upper()
        if confirm == 'Y':
            break
        elif confirm == 'N':
            add_log_entry(None, "Operation cancelled by user.")
            sys.exit(0)
        else:
            add_log_entry(None, "Invalid input. Please enter 'Y' or 'N'.")
    add_log_entry(None, "=" * 50 + "\n")