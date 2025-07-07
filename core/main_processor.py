import threading
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import configuration and logging modules
from core.configs import GitHubOperationConfig
from utils.logs import (
    add_log_entry,
    get_group_log_entries,
    clear_group_log_entries,
    initialize_log_collector,
)

# Global variables for repository status tracking
_repo_statuses = {} 
_initial_total_repos_count = 0 # Stores the total count of repositories
_status_lock = threading.Lock() # Lock for thread-safe access to _repo_statuses and _initial_total_repos_count

class AtomicInteger:
    """
    A thread-safe integer counter class.
    Prevents issues that can arise when multiple threads access and modify a value concurrently.
    """
    def __init__(self, value: int = 0):
        self._value = value
        # Use RLock to allow a thread to acquire the lock multiple times.
        self._lock = threading.RLock()

    def get_lock(self) -> threading.RLock:
        """Returns the RLock object for this AtomicInteger instance."""
        return self._lock

    @property
    def value(self) -> int:
        """Returns the current value of the AtomicInteger. Protected by a lock."""
        with self._lock:
            return self._value

    @value.setter
    def value(self, new_value: int):
        """Sets the value of the AtomicInteger. Protected by a lock."""
        with self._lock:
            self._value = new_value


def _listen_for_user_stop_input(stop_event: threading.Event):
    """
    Listens for user input in a separate thread to handle the stop command ('q').
    If the user enters 'q', sets the stop_event to interrupt the main script's operations.
    """
    add_log_entry(None, "\nTo abort: Press 'q' and then Enter.")
    while not stop_event.is_set():
        if sys.stdin.isatty():  # Only receive input in a terminal environment
            try:
                user_input = input().strip().lower()
                if user_input == 'q':
                    add_log_entry(None, "Abort command detected. Current ongoing tasks will complete, but no new tasks will start.")
                    stop_event.set()
                    break
            except EOFError: # If the input stream is unexpectedly closed
                add_log_entry(None, "Input stream closed. Abort listener exiting.")
                stop_event.set()
                break
            except Exception as e: # Handle other exceptions
                add_log_entry(None, f"An unexpected error occurred while processing input: {e}")
                stop_event.set()
                break
        else:
            # In non-terminal environments, don't wait for input, just pause briefly.
            time.sleep(1)
    add_log_entry(None, "Abort command listener thread is exiting.")


def start_abort_listener_thread() -> tuple[threading.Event, threading.Thread]:
    """
    Starts a thread to listen for user input to control script abortion.

    Returns:
        tuple[threading.Event, threading.Thread]: A tuple containing the stop event and the listener thread object.
    """
    stop_event = threading.Event()
    input_listener_thread = threading.Thread(
        target=_listen_for_user_stop_input,
        args=(stop_event,),
        daemon=True  # Set as a daemon thread to terminate with the main thread
    )
    input_listener_thread.start()
    return stop_event, input_listener_thread

#---
## Single Repository Worker Function
#---

def _process_single_repository_worker(
    repo_name: str,
    config: GitHubOperationConfig,
    single_repo_processor_func,
    completed_repos_count: AtomicInteger,
    total_repos_count: int,
) -> bool:
    """
    Worker function to perform Secrets and Variables operations for a single GitHub repository.
    This function checks the global stop event before starting work.

    Args:
        repo_name (str): The full name of the GitHub repository to process (e.g., 'owner/repo').
        config (GitHubOperationConfig): Configuration object required for GitHub operations.
        single_repo_processor_func (callable): The function containing the actual repository processing logic.
                                            (e.g., process_single_repository from github_operations.py)
        completed_repos_count (AtomicInteger): An AtomicInteger object to track the number of completed repositories.
        total_repos_count (int): The total number of repositories.

    Returns:
        bool: True if repository processing was successful, False otherwise.
    """
    success = False  # Set default to False
    try:
        if config.stop_event.is_set():
            # add_log_message(repo_name, "⚠️ Abort command detected. Skipping this repository.")
            return False  # Return False as processing was skipped

        set_repository_in_progress(repo_name) # 리포지토리 처리 시작 전에 'in_progress'로 설정
        # add_log_entry(repo_name, f"[{repo_name}] Starting processing...")

        # Call the function containing the actual repository processing logic
        # This will be process_single_repository defined in github_operations.py
        success = single_repo_processor_func(  # Receive the return value here
            repo_name,
            config.delete_secrets,
            config.delete_variables,
            config.secrets_to_set,
            config.variables_to_set,
            config.force
        )

        # Assuming single_repo_processor_func returns True/False
        add_log_entry(repo_name, f"✅ Repository processing {'completed' if success else 'failed'} (Success: {success}).")

        # Update the count of completed repositories (thread-safe)
        with completed_repos_count.get_lock():
            completed_repos_count.value += 1

        return success  # Return whether the operation was successful

    except Exception as exc:
        add_log_entry(repo_name, f"❌ Error processing repository '{repo_name}': {exc}")
        return False  # Consider it a failure if an error occurs
    finally:
        # Log final status and progress of the worker thread
        if not config.stop_event.is_set():
            add_log_entry(
                None,
                f"Completed Repo: {repo_name}"
            )


#---
## Parallel Repository Processing Function
#---

def process_repositories(
    config: GitHubOperationConfig,
    single_repo_processor_func,
):
    """
    Performs Secrets and Variables operations on the given list of repositories, either in parallel or sequentially.

    Args:
        config (GitHubOperationConfig): Configuration object required for GitHub operations.
        single_repo_processor_func (callable): Function to process a single repository (e.g., process_single_repository).
    """

    start_time = time.time()  # Start time measurement

    initialize_repository_statuses(config.repositories)  # Initialize repository results in the log module
    initialize_log_collector(config.repositories)

    add_log_entry(None, "\n[INFO] You can abort the operation at any time by typing 'q' and pressing Enter.")

    # total, completed, in_progress = get_current_progress_summary()  # Initial progress
    # add_log_entry(None, f"[Progress] Total Repos: {total}, Completed: {completed}, In Progress: {in_progress}")

    if config.max_workers == 1:  # Sequential processing
        add_log_entry(None, "\n--- Starting GitHub Repository Variable/Secret Automation (Sequential Processing) ---")
        for i, repo in enumerate(config.repositories):
            if config.stop_event.is_set():
                add_log_entry(None, "\n⚠️ Abort command detected. Stopping sequential processing.")
                break

            add_log_entry(repo, f"\n[INFO] To abort, type 'q' and press Enter: Currently processing {repo}...")

            try:
                success = single_repo_processor_func(
                    repo,
                    config.delete_secrets,
                    config.delete_variables,
                    config.secrets_to_set,
                    config.variables_to_set,
                    config.force
                )
                set_repository_status(repo, success)
            except Exception as exc:
                add_log_entry(repo, f"❌ Error processing repository '{repo}': {exc}")
                set_repository_status(repo, False)
            finally:
                repo_status_text = 'Success' if get_repository_overall_status(repo) else 'Failure'
                for msg in get_group_log_entries(repo):
                    add_log_entry(None, msg)
                clear_group_log_entries(repo)  # Clear log buffer

            if i < len(config.repositories) - 1 and not config.stop_event.is_set():
                add_log_entry(None, "[INFO] To abort, type 'q' and press Enter.")
                time.sleep(config.sleep_after_repo)

    else:  # Parallel processing
        add_log_entry(None, f"\n--- Starting GitHub Repository Variable/Secret Automation (Parallel Processing, {config.max_workers} concurrent) ---")
        add_log_entry(None, "[INFO] To abort, type 'q' and press Enter.")

        completed_repos_count = AtomicInteger(0)  # Counter for completed repos in parallel processing

        with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
            futures = {}
            for repo in config.repositories:
                if config.stop_event.is_set():
                    add_log_entry(None, "⚠️ Abort command detected. Stopping submission of new repository tasks.")
                    break

                future = executor.submit(
                    _process_single_repository_worker,
                    repo,
                    config,
                    single_repo_processor_func,
                    completed_repos_count,
                    len(config.repositories)
                )
                futures[future] = repo

            # Process completed tasks via as_completed
            for future in as_completed(futures):
                repo = futures[future]

                try:
                    success = future.result()
                    set_repository_status(repo, success)  # Set status based on success returned by worker function
                except Exception as exc:
                    add_log_entry(repo, f"❌ Error processing repository '{repo}' during thread execution: {exc}")
                    set_repository_status(repo, False)
                finally:
                    # Output logs for repositories processed in parallel
                    repo_status_text = 'Success' if get_repository_overall_status(repo) else 'Failure'
                    for msg in get_group_log_entries(repo):
                        add_log_entry(None, msg)
                    clear_group_log_entries(repo)  # Clear log buffer

                    total, completed, in_progress = get_current_progress_summary()
                    if not config.stop_event.is_set():
                        add_log_entry(None, f"[Progress] Total Repos: {total}, Completed: {completed}, In Progress: {in_progress}")

                        cur_time = time.time()
                        elapsed_time = cur_time - start_time
                        add_log_entry(None, f"✨ Elapsed time so far: {elapsed_time:.2f} seconds ✨")

                if not config.stop_event.is_set():
                    add_log_entry(None, "[INFO] To abort, type 'q' and press Enter.")

    add_log_entry(None, "\n--- All repository processing completed ---")

    end_time = time.time()
    elapsed_time = end_time - start_time
    add_log_entry(None, f"\n✨ Overall operation completed! Total time taken: {elapsed_time:.2f} seconds ✨")


def initialize_repository_statuses(repositories: list):
    """
    Initializes the _repo_statuses dictionary and stores the total number of repositories.
    """
    global _repo_statuses, _initial_total_repos_count
    with _status_lock:
        _repo_statuses = {
            repo: {"success": False, "status": "pending"}
            for repo in repositories
        }
        _initial_total_repos_count = len(repositories)

def set_repository_status(repo_name: str, success: bool):
    """
    Sets the success/failure status and progress status for a specific repository.
    """
    with _status_lock:
        if repo_name in _repo_statuses:
            _repo_statuses[repo_name]["success"] = success
            if success:
                _repo_statuses[repo_name]["status"] = "completed"
            else:
                _repo_statuses[repo_name]["status"] = "failed"
        else:
            sys.stdout.write(f"[WARN: Status Update] Repo '{repo_name}' not found in status tracker.\n")
            sys.stdout.flush()

def set_repository_in_progress(repo_name: str):
    """
    Sets the status of a specific repository to 'in_progress'.
    """
    with _status_lock:
        if repo_name in _repo_statuses and _repo_statuses[repo_name]["status"] == "pending":
            _repo_statuses[repo_name]["status"] = "in_progress"
        # If already in_progress or completed/failed, do not change


def get_repository_overall_status(repo_name: str) -> bool:
    """
    Retrieves the final success/failure status for a specific repository.
    """
    with _status_lock:
        return _repo_statuses.get(repo_name, {}).get("success", False)

def get_current_progress_summary() -> tuple:
    """
    Returns a summary of the current repository processing progress.
    (Total repositories, number of completed or failed repositories, number of repositories currently in progress)
    """
    with _status_lock:
        total_repos = _initial_total_repos_count
        completed_or_failed_repos = 0
        in_progress_repos = 0

        for status_data in _repo_statuses.values():
            if status_data["status"] in ["completed", "failed"]:
                completed_or_failed_repos += 1
            elif status_data["status"] == "in_progress":
                in_progress_repos += 1

        return total_repos, completed_or_failed_repos, in_progress_repos