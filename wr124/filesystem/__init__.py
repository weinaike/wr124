from .file_edit import *
from .shell_tool import *


# Define a mapping of tool names to functions
tool_mapping = {
    # "get_environment": get_environment,
    "write_file": write_file,
    "read_file": read_file,
    "list_directory": list_directory,
    "get_working_directory": get_working_directory,
    "run_command": run_command,
    "glob_search": glob_search,
    "merge_patch": merge_patch,
    "rollback_merge_patch": rollback_merge_patch
}