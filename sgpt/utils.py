import os
import platform
import shlex
from tempfile import NamedTemporaryFile
from typing import Any, Callable

import typer
from click import BadParameter, UsageError

from sgpt.__version__ import __version__
from sgpt.integration import bash_integration, zsh_integration


def get_edited_prompt() -> str:
    """
    Opens the user's default editor to let them
    input a prompt, and returns the edited text.

    :return: String prompt.
    """
    with NamedTemporaryFile(suffix=".txt", delete=False) as file:
        # Create file and store path.
        file_path = file.name
    editor = os.environ.get("EDITOR", "vim")
    # This will write text to file using $EDITOR.
    os.system(f"{editor} {file_path}")
    # Read file when editor is closed.
    with open(file_path, "r", encoding="utf-8") as file:
        output = file.read()
    os.remove(file_path)
    if not output:
        raise BadParameter("Couldn't get valid PROMPT from $EDITOR")
    return output


def run_command(command: str) -> None:
    """
    Runs a command in the user's shell.
    It is aware of the current user's $SHELL.
    :param command: A shell command to run.
    """
    if platform.system() == "Windows":
        is_powershell = len(os.getenv("PSModulePath", "").split(os.pathsep)) >= 3
        full_command = (
            f'powershell.exe -Command "{command}"'
            if is_powershell
            else f'cmd.exe /c "{command}"'
        )
    else:
        shell = os.environ.get("SHELL", "/bin/sh")
        full_command = f"{shell} -c {shlex.quote(command)}"

    os.system(full_command)


def option_callback(func: Callable) -> Callable:  # type: ignore
    def wrapper(cls: Any, value: str) -> None:
        if not value:
            return
        func(cls, value)
        raise typer.Exit()

    return wrapper


@option_callback
def install_shell_integration(*_args: Any) -> None:
    """
    Installs shell integration. Currently only supports ZSH and Bash.
    Allows user to get shell completions in terminal by using hotkey.
    Replaces current "buffer" of the shell with the completion.
    """
    from pathlib import Path

    # TODO: Add support for Windows.
    shell = os.getenv("SHELL", "")
    if "zsh" in shell:
        typer.echo("Installing ZSH integration...")
        # Install to ~/.zprofile.d/ directory
        integration_dir = Path.home() / ".zprofile.d"
        integration_path = integration_dir / "sgpt.zsh"
        integration_dir.mkdir(parents=True, exist_ok=True)
        integration_path.write_text(zsh_integration.strip() + "\n")
        typer.secho(f"Installed to {integration_path}", fg="green")
    elif "bash" in shell:
        typer.echo("Installing Bash integration...")
        # Install to ~/.bash_profile.d/ directory
        integration_dir = Path.home() / ".bash_profile.d"
        integration_path = integration_dir / "sgpt.sh"
        integration_dir.mkdir(parents=True, exist_ok=True)
        integration_path.write_text(bash_integration.strip() + "\n")
        typer.secho(f"Installed to {integration_path}", fg="green")
    else:
        raise UsageError("ShellGPT integrations only available for ZSH and Bash.")

    typer.echo("Restart your shell to apply changes.")


@option_callback
def get_sgpt_version(*_args: Any) -> None:
    """
    Displays the current installed version of ShellGPT
    """
    typer.echo(f"ShellGPT {__version__}")


def get_completion_script(shell: str = "bash") -> str:
    """Generate shell completion script for sgpt."""
    prog_name = "sgpt"
    complete_var = "_SGPT_COMPLETE"

    if shell == "bash":
        return f'''_sgpt_completion() {{
    local IFS=$'\\n'
    COMPREPLY=( $( env COMP_WORDS="${{COMP_WORDS[*]}}" \\
                   COMP_CWORD=$COMP_CWORD \\
                   {complete_var}=complete_bash $1 ) )
    return 0
}}

complete -o default -F _sgpt_completion {prog_name}
'''
    elif shell == "zsh":
        return f'''#compdef {prog_name}

_sgpt_completion() {{
  eval $(env _TYPER_COMPLETE_ARGS="${{words[1,$CURRENT]}}" {complete_var}=complete_zsh {prog_name})
}}

compdef _sgpt_completion {prog_name}
'''
    elif shell == "fish":
        return (
            f'complete --command {prog_name} --no-files '
            f'--arguments "(env {complete_var}=complete_fish '
            f'_TYPER_COMPLETE_FISH_ACTION=get-args '
            f'_TYPER_COMPLETE_ARGS=(commandline -cp) {prog_name})" '
            f'--condition "env {complete_var}=complete_fish '
            f'_TYPER_COMPLETE_FISH_ACTION=is-args '
            f'_TYPER_COMPLETE_ARGS=(commandline -cp) {prog_name}"'
        )
    else:
        raise UsageError(f"Unsupported shell: {shell}")


def _install_completion_to_path(shell: str) -> str:
    """Install shell completion script to the appropriate location."""
    from pathlib import Path

    script = get_completion_script(shell)
    prog_name = "sgpt"

    if shell == "bash":
        # Use standard ~/.bash_completion.d/ directory
        completion_dir = Path.home() / ".bash_completion.d"
        completion_path = completion_dir / f"{prog_name}-completion.sh"
    elif shell == "zsh":
        completion_dir = Path.home() / ".zfunc"
        completion_path = completion_dir / f"_{prog_name}"
    elif shell == "fish":
        completion_dir = Path.home() / ".config" / "fish" / "completions"
        completion_path = completion_dir / f"{prog_name}.fish"
    else:
        raise UsageError(f"Unsupported shell: {shell}")

    completion_dir.mkdir(parents=True, exist_ok=True)
    completion_path.write_text(script)
    return str(completion_path)


@option_callback
def install_completion(*_args: Any) -> None:
    """
    Installs shell completion script to the appropriate location.
    """
    shell = os.getenv("SHELL", "")
    if "zsh" in shell:
        shell_name = "zsh"
    elif "bash" in shell:
        shell_name = "bash"
    elif "fish" in shell:
        shell_name = "fish"
    else:
        # Try to detect using shellingham
        try:
            import shellingham
            shell_name, _ = shellingham.detect_shell()
        except Exception:
            shell_name = "bash"

    path = _install_completion_to_path(shell_name)
    typer.secho(f"{shell_name} completion installed in {path}", fg="green")
    typer.echo("Completion will take effect once you restart the terminal.")


@option_callback
def show_completion(_cls: Any, shell: str) -> None:
    """
    Shows shell completion script for the specified shell.
    The shell parameter is the value passed to --show-completion option.
    """
    # If shell value is just a truthy flag without specific shell name,
    # detect from environment
    if shell in ("True", "true", "1"):
        shell_env = os.getenv("SHELL", "")
        if "zsh" in shell_env:
            shell = "zsh"
        elif "bash" in shell_env:
            shell = "bash"
        elif "fish" in shell_env:
            shell = "fish"
        else:
            shell = "bash"

    script = get_completion_script(shell)
    typer.echo(script)
