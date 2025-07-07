import sys

from core.cli_parser import parse_arguments
from core.github_operations import (
    get_repositories_from_github,
    display_and_confirm_actions,
    process_single_repository,
)
from utils.utils import read_key_value_pairs, read_list_from_file, validate_file_path
from core.main_processor import start_abort_listener_thread, process_repositories # Renamed from 'threads' to 'main_processor'
from utils.logs import add_log_entry
from core.configs import GitHubOperationConfig

def main():
    """
    Main function to parse arguments, configure GitHub operations,
    and initiate the processing of repositories.
    """
    args = parse_arguments() 
    
    # Create GitHubOperationConfig object and assign arguments
    config = GitHubOperationConfig(
        organization=args.organization,
        max_workers=args.workers,
        sleep_after_repo=args.sleep,
        force=args.force
    )

    add_log_entry(None, f"Configured GitHub Organization/User: {config.organization}")

    # Read secrets to set from file
    if args.secrets_file:
        secrets_file_path = validate_file_path(args.secrets_file, "secret configuration file")
        if secrets_file_path: # Ensure file path is valid before reading
            config.secrets_to_set = read_key_value_pairs(secrets_file_path, "secrets")
    
    # Read variables to set from file
    if args.values_file:
        values_file_path = validate_file_path(args.values_file, "variable configuration file")
        if values_file_path: # Ensure file path is valid before reading
            config.variables_to_set = read_key_value_pairs(values_file_path, "variables")
    
    # Read secrets to delete from file
    if args.ds:
        ds_file = validate_file_path(args.ds, "secret deletion list file")
        if ds_file: # Ensure file path is valid before reading
            config.delete_secrets = read_list_from_file(ds_file, "secret deletion list")
    
    # Read variables to delete from file
    if args.dv:
        dv_file = validate_file_path(args.dv, "variable deletion list file")
        if dv_file: # Ensure file path is valid before reading
            config.delete_variables = read_list_from_file(dv_file, "variable deletion list")

    # Determine target repositories
    if args.tr:
        try:
            with open(args.tr.resolve(), 'r', encoding='utf-8') as f:
                target_repo_names = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                # Prepend organization if not already 'owner/repo' format
                config.repositories = [f"{config.organization}/{r}" if '/' not in r else r for r in target_repo_names]
            add_log_entry(None, f"📌 '--tr' option used: {len(config.repositories)} specific repositories designated.")
        except Exception as e:
            add_log_entry(None, f"❌ Error processing '--tr' file: {e}")
            sys.exit(1)
    else:
        config.repositories = get_repositories_from_github(config.organization)
    
    # Exit if no repositories to process
    if not config.repositories:
        add_log_entry(None, "No repositories to process. Exiting script.")
        sys.exit(0)

    # Display and confirm actions
    display_and_confirm_actions(
        config.delete_secrets,
        config.delete_variables,
        config.secrets_to_set,
        config.variables_to_set,
        config.repositories,
        config.sleep_after_repo,
        config.max_workers,
        config.force
    )

    # Start the abort listener thread and assign the stop event to config
    config.stop_event, _ = start_abort_listener_thread() 

    # Process repositories using the main processor function
    process_repositories(
        config,
        process_single_repository
    )
        
if __name__ == "__main__":
    main()