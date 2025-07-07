import sys
import threading

# Manages detailed logs for all groups.
# { "group_name": {"logs": list} }
_all_group_logs = {}  # Stores detailed logs per group
_log_lock = threading.Lock()  # Lock for thread-safe access to _all_group_logs and console output


def initialize_log_collector(group_names: list):
    """
    Initializes the _all_group_logs dictionary.
    Each group will simply contain a list of logs.

    Args:
        group_names (list): A list of group names (e.g., repository names) to initialize.
    """
    global _all_group_logs
    with _log_lock:
        _all_group_logs = {
            name: {"logs": []}
            for name in group_names
        }


def add_log_entry(group_name: str | None, message: str, store: bool = True, is_prompt: bool = False):
    """
    Adds a message to a specific group's log collector and prints it to the console.
    This function is designed to be thread-safe.

    Args:
        group_name (str | None): The name of the group to add the message to (e.g., repository name).
                                 If None, it's treated as a global message and only printed to console.
        message (str): The message to log.
        store (bool): Whether to store the message in _all_group_logs. If False, it's only printed to console.
                      Defaults to True.
        is_prompt (bool): True if the message is a user input prompt.
                          If it's a prompt, no newline character is added after the message.
                          Defaults to False.
    """
    with _log_lock:
        # Console output is always performed.


        # Log storage logic
        if store and group_name is not None:
            if group_name not in _all_group_logs:
                # Log a warning to console if group is missing, but don't store the message
                sys.stdout.write(f"[WARN: Missing Log Group - '{group_name}'] Message not stored: {message}\n")
                sys.stdout.flush()
            else:
                _all_group_logs[group_name]["logs"].append(message)
        else:
            if is_prompt:
                sys.stdout.write(message)
            else:
                sys.stdout.write(f"{message}\n")
            sys.stdout.flush()

def get_group_log_entries(group_name: str) -> list:
    """
    Retrieves the log entries for a specific group.

    Args:
        group_name (str): The name of the group whose logs are to be retrieved.

    Returns:
        list: A list of log messages for the specified group. Returns an empty list if the group does not exist.
    """
    with _log_lock:
        return _all_group_logs.get(group_name, {}).get("logs", [])


def clear_group_log_entries(group_name: str):
    """
    Deletes (clears) the log entries for a specific group from memory.

    Args:
        group_name (str): The name of the group whose logs are to be cleared.
    """
    with _log_lock:
        if group_name in _all_group_logs:
            _all_group_logs[group_name]["logs"] = []
        else:
            sys.stdout.write(f"[WARN: Clear Logs] Group '{group_name}' not found in collector.\n")
            sys.stdout.flush()