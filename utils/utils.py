import sys
import json
import subprocess
from pathlib import Path

# Import function for logging messages
from utils.logs import add_log_entry


def read_key_value_pairs(file_path: Path, item_type: str = "settings", repo_name: str = None) -> dict:
    """
    Reads a file with 'KEY="VALUE"' or 'KEY='VALUE'' format and returns it as a dictionary.

    Args:
        file_path (Path): The path to the file to read.
        item_type (str): A label indicating the type of items in the file (for log messages, e.g., "secrets").
        repo_name (str | None): The name of the repository related to this operation (None for global messages).

    Returns:
        dict: A dictionary containing the parsed key-value pairs.
    """
    if not file_path:
        add_log_entry(repo_name, f"Warning: No file path provided for {item_type} file.")
        return {}

    parsed_data = {}
    try:
        add_log_entry(repo_name, f"Reading {item_type} from file '{file_path.name}'...")
        with open(file_path.resolve(), 'rb') as f:
            for line_num, raw_line in enumerate(f, 1):
                line = raw_line.decode('utf-8', errors='ignore').strip()
                if not line or line.startswith('#'):
                    continue

                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove quotes
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]

                    if key:
                        parsed_data[key] = value
                    else:
                        add_log_entry(repo_name, f"Warning ({file_path.name}:{line_num}): Invalid line format (no key found): '{line}'")
                else:
                    add_log_entry(repo_name, f"Warning ({file_path.name}:{line_num}): Invalid line format (no equals sign found): '{line}'")
    except Exception as e:
        add_log_entry(repo_name, f"❌ Error: An unexpected error occurred while reading {item_type} file '{file_path.name}': {e}")
        return {}

    if not parsed_data:
        add_log_entry(repo_name, f"Warning: No valid data to read from {item_type} file '{file_path.name}'.")
    else:
        add_log_entry(repo_name, f"✅ Read {len(parsed_data)} items from {item_type} file '{file_path.name}'.")
    return parsed_data


def read_list_from_file(file_path: Path, list_type: str = "list", repo_name: str = None) -> list:
    """
    Reads a list of items, one per line, from a file and returns them as a list.
    Primarily used for deletion lists or target repository lists.

    Args:
        file_path (Path): The path to the file to read.
        list_type (str): A label indicating the type of list (for log messages, e.g., "delete list").
        repo_name (str | None): The name of the repository related to this operation (None for global messages).

    Returns:
        list: A list containing the parsed items.
    """
    if not file_path:
        add_log_entry(repo_name, f"Warning: No file path provided for {list_type} file.")
        return []

    try:
        with open(file_path.resolve(), 'r', encoding='utf-8') as f:
            items = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        add_log_entry(repo_name, f"✅ Read {len(items)} items from {list_type}: {file_path.name}")
        return items
    except Exception as e:
        add_log_entry(repo_name, f"❌ Error: An unexpected error occurred while reading {list_type} file '{file_path.name}': {e}")
        return []


def validate_file_path(path: Path, label: str, repo_name: str = None) -> Path | None:
    """
    Validates if the given path points to a valid file.

    Args:
        path (Path): The path to the file to validate.
        label (str): A label describing the path (for log messages, e.g., "secret config file").
        repo_name (str | None): The name of the repository related to this operation (None for global messages).

    Returns:
        Path | None: A Path object if the file exists and is valid, otherwise None.
    """
    if path is None:
        return None

    add_log_entry(repo_name, f"Validating file path: '{label}' path '{path}' (Type: {type(path).__name__})")

    try:
        if not isinstance(path, Path):
            add_log_entry(repo_name, f"❌ Error: Provided path for '{label}' is not a valid Path object: {path}")
            return None
        if not path.exists():
            add_log_entry(repo_name, f"❌ Error: '{label}' file does not exist: {path.resolve()}")
            return None
        if not path.is_file():
            add_log_entry(repo_name, f"❌ Error: '{label}' path is a directory, not a file: {path.resolve()}")
            return None
        return path
    except Exception as e:
        add_log_entry(repo_name, f"❌ Error: An exception occurred while processing '{label}' file ({path}): {e}")
        return None


def execute_subprocess_command(command: list, shell: bool = False) -> tuple[str, str]:
    """
    Executes an external command and returns its standard output (stdout) and standard error (stderr).
    All log messages generated by this function are recorded as global logs (repo_name=None).

    Args:
        command (list): The command and its arguments to execute.
        shell (bool): Whether to execute the command through the shell. Defaults to False.

    Returns:
        tuple[str, str]: A tuple containing (stdout string, stderr string).

    Raises:
        subprocess.CalledProcessError: If the command returns a non-zero exit code.
        FileNotFoundError: If the command executable is not found.
        Exception: For any other unexpected errors during command execution.
    """
    cmd_str = ' '.join(command)
    
    try:
        process = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            check=True
        )
        stdout_decoded = process.stdout.decode('utf-8', errors='replace').strip()
        stderr_decoded = process.stderr.decode('utf-8', errors='replace').strip()

        return stdout_decoded, stderr_decoded

    except subprocess.CalledProcessError as e:
        error_stdout = e.stdout.decode('utf-8', errors='replace').strip() if e.stdout else ""
        error_stderr = e.stderr.decode('utf-8', errors='replace').strip() if e.stderr else ""
        
        add_log_entry(None, f"❌ Command execution error: {cmd_str}")
        add_log_entry(None, f"❌ Stderr: {error_stderr}")
        raise # Re-raise the exception for the caller to handle
    except FileNotFoundError:
        add_log_entry(None, f"❌ Command failed: '{command[0]}' not found. Check your PATH.")
        sys.exit(1) # Exiting the program is appropriate in this case
    except Exception as e:
        add_log_entry(None, f"❌ An unexpected error occurred during command execution ('{cmd_str}'): {e}")
        raise


def parse_json_string(json_string: str, error_context: str = "JSON parsing", repo_name: str = None):
    """
    Parses a JSON string and returns the result.

    Args:
        json_string (str): The JSON string to parse.
        error_context (str): A description of the context for error messages (e.g., "repository secret list").
        repo_name (str | None): The name of the repository related to this operation (None for global messages).

    Returns:
        any: The parsed JSON object (dict or list), or None if parsing fails.
    """
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        add_log_entry(repo_name, f"🚨 DEBUG: JSON parsing error! Context: {error_context}. Error: {e}")
        add_log_entry(repo_name, f"🚨 DEBUG: problematic_json_string: '''{json_string}'''")
        return None
    except Exception as e:
        add_log_entry(repo_name, f"Warning: An unexpected error occurred during {error_context}: {e}")
        return None


def read_text_file_content(file_path: Path, repo_name: str = None) -> str:
    """
    Reads the entire content of a specified text file as a string.

    Args:
        file_path (Path): The path to the file to read.
        repo_name (str | None): The name of the repository related to this operation (None for global messages).

    Returns:
        str: The content of the file.

    Raises:
        FileNotFoundError: If the file cannot be found.
        Exception: For any other file reading errors.
    """
    try:
        with open(file_path.resolve(), 'r', encoding='utf-8') as f:
            content = f.read().strip()
        return content
    except FileNotFoundError:
        add_log_entry(repo_name, f"Error: File '{file_path.resolve()}' not found.")
        raise
    except Exception as e:
        add_log_entry(repo_name, f"Error: An unexpected error occurred while reading file '{file_path.resolve()}': {e}")
        raise