import os
import re
import uuid

# To allow users to use arrow keys in the REPL.
import readline  # noqa: F401
import sys

import typer
from click import BadArgumentUsage
from click.types import Choice
from prompt_toolkit import PromptSession

from sgpt.config import cfg
from sgpt.function import get_openai_schemas
from sgpt.handlers.chat_handler import ChatHandler
from sgpt.handlers.default_handler import DefaultHandler
from sgpt.handlers.repl_handler import ReplHandler
from sgpt.llm_functions.init_functions import install_functions as inst_funcs
from sgpt.role import DefaultRoles, SystemRole
from sgpt.utils import (
    get_edited_prompt,
    get_sgpt_version,
    install_completion,
    install_shell_integration,
    run_command,
    show_completion,
)


def generate_chat_name(prompt: str, model: str) -> str:
    """
    Generate a short chat name based on the user's prompt using AI.
    Returns a sanitized name suitable for use as a filename.
    """
    from sgpt.handlers.handler import additional_kwargs, completion

    name_prompt = (
        "Based on the following user message, generate a very short descriptive name "
        "(2-5 words, max 50 characters) for this chat session. "
        "Use only lowercase English letters, numbers, and hyphens. "
        "No spaces, no special characters. Output ONLY the name, nothing else.\n\n"
        f"User message: {prompt[:500]}"  # Limit prompt length
    )

    try:
        response = completion(
            model=model,
            messages=[{"role": "user", "content": name_prompt}],
            max_tokens=100,
            temperature=0.35,
            **additional_kwargs,
        )
        # Extract the generated name
        generated_name = response.choices[0].message.content.strip()
        # Sanitize: only keep alphanumeric and hyphens, limit length
        sanitized = re.sub(r"[^a-z0-9\-]", "-", generated_name.lower())
        sanitized = re.sub(r"-+", "-", sanitized).strip("-")  # Remove duplicate/trailing hyphens
        sanitized = sanitized[:50]  # Limit length
        return sanitized if sanitized else f"chat-{uuid.uuid4().hex[:8]}"
    except Exception:
        # Fallback to UUID-based name if AI generation fails
        return f"chat-{uuid.uuid4().hex[:8]}"


def main(
    prompt: str = typer.Argument(
        "",
        show_default=False,
        help="The prompt to generate completions for.",
    ),
    model: str = typer.Option(
        cfg.get("DEFAULT_MODEL"),
        help="Large language model to use.",
    ),
    max_tokens: int = typer.Option(
        cfg.get("MAX_TOKENS"),
        min=0,
        max=128000,
        help="Max tokens of generated output.",
    ),
    temperature: float = typer.Option(
        cfg.get("TEMPERATURE"),
        min=0.0,
        max=2.0,
        help="Randomness of generated output.",
    ),
    top_p: float = typer.Option(
        1.0,
        min=0.0,
        max=1.0,
        help="Limits highest probable tokens (words).",
    ),
    md: bool = typer.Option(
        cfg.get("PRETTIFY_MARKDOWN") == "true",
        help="Prettify markdown output.",
    ),
    shell: bool = typer.Option(
        False,
        "--shell",
        "-s",
        help="Generate and execute shell commands.",
        rich_help_panel="Assistance Options",
    ),
    interaction: bool = typer.Option(
        cfg.get("SHELL_INTERACTION") == "true",
        help="Interactive mode for --shell option.",
        rich_help_panel="Assistance Options",
    ),
    describe_shell: bool = typer.Option(
        False,
        "--describe-shell",
        "-d",
        help="Describe a shell command.",
        rich_help_panel="Assistance Options",
    ),
    code: bool = typer.Option(
        False,
        "--code",
        "-c",
        help="Generate only code.",
        rich_help_panel="Assistance Options",
    ),
    functions: bool = typer.Option(
        cfg.get("TWCC_USE_FUNCTIONS") == "true",
        help="Allow function calls.",
        rich_help_panel="Assistance Options",
    ),
    editor: bool = typer.Option(
        False,
        help="Open $EDITOR to provide a prompt.",
    ),
    cache: bool = typer.Option(
        True,
        help="Cache completion results.",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version.",
        callback=get_sgpt_version,
    ),
    _install_completion: bool = typer.Option(
        False,
        "--install-completion",
        help="Install completion for the current shell.",
        callback=install_completion,
    ),
    _show_completion: str = typer.Option(
        None,
        "--show-completion",
        help="Show completion for specified shell (bash/zsh/fish).",
        callback=show_completion,
    ),
    chat: str = typer.Option(
        None,
        help='Follow conversation with id. Use "temp" for quick session, '
        '"auto" for AI-generated name, "last" to resume last session.',
        rich_help_panel="Chat Options",
        autocompletion=ChatHandler.complete_chat_id,
    ),
    resume: bool = typer.Option(
        False,
        "--resume",
        "-r",
        help="Resume last chat session.",
        rich_help_panel="Chat Options",
    ),
    repl: str = typer.Option(
        None,
        help="Start a REPL (Read–eval–print loop) session.",
        rich_help_panel="Chat Options",
        autocompletion=ChatHandler.complete_chat_id,
    ),
    show_chat: str = typer.Option(
        None,
        help="Show all messages from provided chat id.",
        rich_help_panel="Chat Options",
        autocompletion=ChatHandler.complete_chat_id,
    ),
    list_chats: bool = typer.Option(
        False,
        "--list-chats",
        "-lc",
        help="List all existing chat ids.",
        callback=ChatHandler.list_ids,
        rich_help_panel="Chat Options",
    ),
    role: str = typer.Option(
        None,
        help="System role for GPT model.",
        rich_help_panel="Role Options",
    ),
    create_role: str = typer.Option(
        None,
        help="Create role.",
        callback=SystemRole.create,
        rich_help_panel="Role Options",
    ),
    show_role: str = typer.Option(
        None,
        help="Show role.",
        callback=SystemRole.show,
        rich_help_panel="Role Options",
    ),
    list_roles: bool = typer.Option(
        False,
        "--list-roles",
        "-lr",
        help="List roles.",
        callback=SystemRole.list,
        rich_help_panel="Role Options",
    ),
    install_integration: bool = typer.Option(
        False,
        help="Install shell integration (ZSH and Bash only)",
        callback=install_shell_integration,
        hidden=True,  # Hiding since should be used only once.
    ),
    install_functions: bool = typer.Option(
        False,
        help="Install default functions.",
        callback=inst_funcs,
        hidden=True,  # Hiding since should be used only once.
    ),
) -> None:
    stdin_passed = not sys.stdin.isatty()

    if stdin_passed:
        stdin = ""
        # TODO: This is very hacky.
        # In some cases, we need to pass stdin along with inputs.
        # When we want part of stdin to be used as a init prompt,
        # but rest of the stdin to be used as a inputs. For example:
        # echo "hello\n__sgpt__eof__\nThis is input" | sgpt --repl temp
        # In this case, "hello" will be used as a init prompt, and
        # "This is input" will be used as "interactive" input to the REPL.
        # This is useful to test REPL with some initial context.
        for line in sys.stdin:
            if "__sgpt__eof__" in line:
                break
            stdin += line
        prompt = f"{stdin}\n\n{prompt}" if prompt else stdin
        try:
            # Switch to stdin for interactive input.
            if os.name == "posix":
                sys.stdin = open("/dev/tty", "r")
            elif os.name == "nt":
                sys.stdin = open("CON", "r")
        except OSError:
            # Non-interactive shell.
            pass

    if show_chat:
        # Handle --show-chat last
        if show_chat == "last":
            last_chat_id = ChatHandler.chat_session.get_last_chat_id()
            if last_chat_id:
                show_chat = last_chat_id
            else:
                raise BadArgumentUsage("No previous chat session found.")
        ChatHandler.show_messages(show_chat, md)
        return

    if sum((shell, describe_shell, code)) > 1:
        raise BadArgumentUsage(
            "Only one of --shell, --describe-shell, and --code options can be used at a time."
        )

    if chat and repl:
        raise BadArgumentUsage("--chat and --repl options cannot be used together.")

    if chat and resume:
        raise BadArgumentUsage("--chat and --resume options cannot be used together.")

    # Handle --chat last (same as --resume but using --chat syntax)
    if chat == "last":
        last_chat_id = ChatHandler.chat_session.get_last_chat_id()
        if last_chat_id:
            chat = last_chat_id
            typer.secho(f"[ Resuming chat session: {chat} ]", fg="cyan", err=True)
        else:
            raise BadArgumentUsage("No previous chat session found.")

    if resume:
        # Get the last used chat session
        chat_sessions = ChatHandler.chat_session.list()
        if chat_sessions:
            # Use the last modified chat session
            chat = chat_sessions[-1].name
            typer.secho(f"[ Resuming chat session: {chat} ]", fg="cyan", err=True)
        else:
            # If no chat session exists, create a default one
            chat = "default"
            typer.secho("[ No previous chat session found. Starting new default session. ]", fg="cyan", err=True)

    if editor and stdin_passed:
        raise BadArgumentUsage("--editor option cannot be used with stdin input.")

    if editor:
        prompt = get_edited_prompt()

    role_class = (
        DefaultRoles.check_get(shell, describe_shell, code)
        if not role
        else SystemRole.get(role)
    )

    function_schemas = (get_openai_schemas() or None) if functions else None

    if repl:
        # Will be in infinite loop here until user exits with Ctrl+C.
        ReplHandler(repl, role_class, md).handle(
            init_prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            caching=cache,
            functions=function_schemas,
        )

    # Use DefaultHandler for single-shot modes (--shell, --code, --describe-shell)
    # unless explicitly using --chat to maintain conversation history
    if chat or (not shell and not code and not describe_shell):
        # Use ChatHandler for persistent conversations
        explicit_chat = chat is not None  # Track if user explicitly specified --chat
        is_auto_chat = chat == "auto"

        if not chat:
            chat = "default"

        # Handle --chat auto: use temporary ID first, then rename after completion
        if is_auto_chat:
            temp_chat_id = f"auto-{uuid.uuid4().hex[:8]}"
            chat = temp_chat_id

        # Clear default chat unless --resume or explicit --chat was used
        if chat == "default" and not explicit_chat and not resume:
            ChatHandler.chat_session.invalidate(chat)

        full_completion = ChatHandler(chat, role_class, md).handle(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            caching=cache,
            functions=function_schemas,
        )

        # After completion, generate AI-based name for auto chat
        if is_auto_chat:
            generated_name = generate_chat_name(prompt, model)
            final_name = ChatHandler.chat_session.rename(temp_chat_id, generated_name)
            typer.secho(f"\n[ Chat session created: {final_name} ]", fg="cyan", err=True)
    else:
        # Use DefaultHandler for single-shot interactions
        full_completion = DefaultHandler(role_class, md).handle(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            caching=cache,
            functions=function_schemas,
        )

    session: PromptSession[str] = PromptSession()

    while shell and interaction:
        option = typer.prompt(
            text="[E]xecute, [M]odify, [D]escribe, [A]bort",
            type=Choice(("e", "m", "d", "a", "y"), case_sensitive=False),
            default="e" if cfg.get("DEFAULT_EXECUTE_SHELL_CMD") == "true" else "a",
            show_choices=False,
            show_default=False,
        )
        if option in ("e", "y"):
            # "y" option is for keeping compatibility with old version.
            run_command(full_completion)
        elif option == "m":
            full_completion = session.prompt("", default=full_completion)
            continue
        elif option == "d":
            DefaultHandler(DefaultRoles.DESCRIBE_SHELL.get_role(), md).handle(
                full_completion,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                caching=cache,
                functions=function_schemas,
            )
            continue
        break


# Create Typer app (disable built-in completion, use custom implementation)
app = typer.Typer(
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=False,
)
app.command()(main)


def entry_point() -> None:
    app()


if __name__ == "__main__":
    entry_point()
