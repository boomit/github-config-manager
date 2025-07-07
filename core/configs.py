from dataclasses import dataclass, field
from pathlib import Path
import threading

@dataclass
class GitHubOperationConfig:
    """
    Data class to hold configuration information for GitHub repository Secrets and Variables operations.
    """
    organization: str = field(default="") # GitHub organization or user name
    
    # Secrets and Variables to set/update
    secrets_to_set: dict = field(default_factory=dict)
    variables_to_set: dict = field(default_factory=dict)
    
    # Lists of Secret and Variable names to delete
    delete_secrets: list = field(default_factory=list)
    delete_variables: list = field(default_factory=list)

    # Target repositories list (read from file or fetched from GitHub)
    repositories: list[str] = field(default_factory=list) 

    # Parallel processing and control options
    max_workers: int = 1 # Number of repositories to process concurrently
    sleep_after_repo: int = 0 # Sleep duration (seconds) after processing each repository
    force: bool = False # Whether to overwrite Secrets/Variables if they already exist during setting

    # stop_event for inter-thread communication (managed internally by the program)
    stop_event: threading.Event = field(default_factory=threading.Event)

    # Other file paths (can be assigned to this class instance after CLI argument parsing)
    secrets_file: Path | None = None
    values_file: Path | None = None
    delete_secrets_file: Path | None = None 
    delete_variables_file: Path | None = None
    target_repos_file: Path | None = None


    def __post_init__(self):
        """
        Additional validation or setup after initialization.
        """
        if self.max_workers < 1:
            raise ValueError("max_workers must be 1 or greater.")
        if self.sleep_after_repo < 0:
            raise ValueError("sleep_after_repo must be 0 or greater.")