import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional

import typer
from click import BadArgumentUsage, BadParameter, UsageError
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..config import cfg
from ..role import DefaultRoles, SystemRole
from ..utils import option_callback
from .handler import Handler

CHAT_CACHE_LENGTH = int(cfg.get("CHAT_CACHE_LENGTH"))
CHAT_CACHE_PATH = Path(cfg.get("CHAT_CACHE_PATH"))


class ChatSession:
    """
    This class is used as a decorator for OpenAI chat API requests.
    The ChatSession class caches chat messages and keeps track of the
    conversation history. It is designed to store cached messages
    in a specified directory and in JSON format.
    """

    def __init__(self, length: int, storage_path: Path):
        """
        Initialize the ChatSession decorator.

        :param length: Integer, maximum number of cached messages to keep.
        """
        self.length = length
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.last_chat_file = self.storage_path / ".last_chat_id"

    def get_last_chat_id(self) -> Optional[str]:
        """Get the last used chat ID."""
        if self.last_chat_file.exists():
            return self.last_chat_file.read_text().strip()
        return None

    def set_last_chat_id(self, chat_id: str) -> None:
        """Set the last used chat ID."""
        self.last_chat_file.write_text(chat_id)

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """
        The Cache decorator.

        :param func: The chat function to cache.
        :return: Wrapped function with chat caching.
        """

        def wrapper(*args: Any, **kwargs: Any) -> Generator[str, None, None]:
            chat_id = kwargs.pop("chat_id", None)
            if not kwargs.get("messages"):
                return
            if not chat_id:
                yield from func(*args, **kwargs)
                return
            previous_messages = self._read(chat_id)
            for message in kwargs["messages"]:
                previous_messages.append(message)
            kwargs["messages"] = previous_messages
            response_text = ""
            for word in func(*args, **kwargs):
                response_text += word
                yield word
            previous_messages.append({"role": "assistant", "content": response_text})
            self._write(kwargs["messages"], chat_id)

        return wrapper

    def _read(self, chat_id: str) -> List[Dict[str, str]]:
        file_path = self.storage_path / chat_id
        if not file_path.exists():
            return []
        parsed_cache = json.loads(file_path.read_text())
        return parsed_cache if isinstance(parsed_cache, list) else []

    def _write(self, messages: List[Dict[str, str]], chat_id: str) -> None:
        file_path = self.storage_path / chat_id
        # Retain the first message since it defines the role
        truncated_messages = (
            messages[:1] + messages[1 + max(0, len(messages) - self.length) :]
        )
        json.dump(truncated_messages, file_path.open("w"))

    def invalidate(self, chat_id: str) -> None:
        file_path = self.storage_path / chat_id
        file_path.unlink(missing_ok=True)

    def rename(self, old_id: str, new_id: str) -> str:
        """
        Rename a chat session file.
        If new_id already exists, append a numeric suffix.
        Returns the final new_id used.
        """
        old_path = self.storage_path / old_id
        if not old_path.exists():
            return old_id

        # Handle name conflicts by adding numeric suffix
        final_id = new_id
        counter = 2
        while (self.storage_path / final_id).exists():
            final_id = f"{new_id}-{counter}"
            counter += 1

        new_path = self.storage_path / final_id
        old_path.rename(new_path)

        # Update last chat ID if it was the renamed one
        if self.get_last_chat_id() == old_id:
            self.set_last_chat_id(final_id)

        return final_id

    def get_messages(self, chat_id: str) -> List[str]:
        messages = self._read(chat_id)
        return [f"{message['role']}: {message['content']}" for message in messages]

    def exists(self, chat_id: Optional[str]) -> bool:
        return bool(chat_id and bool(self._read(chat_id)))

    def list(self) -> List[Path]:
        # Get all files in the folder, excluding hidden files like .last_chat_id.
        files = [f for f in self.storage_path.glob("*") if not f.name.startswith(".")]
        # Sort files by last modification time in ascending order.
        return sorted(files, key=lambda f: f.stat().st_mtime)


class ChatHandler(Handler):
    chat_session = ChatSession(CHAT_CACHE_LENGTH, CHAT_CACHE_PATH)

    def __init__(self, chat_id: str, role: SystemRole, markdown: bool) -> None:
        super().__init__(role, markdown)
        self.chat_id = chat_id
        self.role = role

        # Handle temp chat: only clear if switching from a different chat
        last_chat_id = self.chat_session.get_last_chat_id()
        if last_chat_id and last_chat_id == "temp" and chat_id != "temp":
            # Switching away from temp, clear it
            self.chat_session.invalidate("temp")
        
        # Update last chat ID
        self.chat_session.set_last_chat_id(chat_id)

        self.validate()

    @property
    def initiated(self) -> bool:
        return self.chat_session.exists(self.chat_id)

    @property
    def is_same_role(self) -> bool:
        # TODO: Should be optimized for REPL mode.
        return self.role.same_role(self.initial_message(self.chat_id))

    @classmethod
    def initial_message(cls, chat_id: str) -> str:
        chat_history = cls.chat_session.get_messages(chat_id)
        return chat_history[0] if chat_history else ""

    @staticmethod
    def complete_chat_id(incomplete: str = "") -> List[str]:
        """Autocompletion callback for chat IDs."""
        # Get all chat session names using the class-level chat_session
        chat_session = ChatSession(CHAT_CACHE_LENGTH, CHAT_CACHE_PATH)
        chat_list = chat_session.list()
        chat_names = [chat.name for chat in chat_list]
        # Add special keywords
        special = ["last", "temp", "auto"]
        all_options = special + chat_names
        # Filter by incomplete prefix
        return [name for name in all_options if name.startswith(incomplete)]

    @classmethod
    @option_callback
    def list_ids(cls, value: str) -> None:
        # Prints all existing chat IDs (names only) to the console.
        console = Console()
        chat_list = list(cls.chat_session.list())

        if not chat_list:
            console.print(Panel(
                "[yellow]No chat sessions found.[/yellow]",
                title="[cyan]Available Chat Sessions[/cyan]",
                border_style="cyan"
            ))
            return

        table = Table.grid(expand=True)
        table.add_column(justify="left")
        table.add_column(justify="right", style="dim")

        for chat_path in chat_list:
            modified_at = datetime.fromtimestamp(chat_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            table.add_row(Text(chat_path.name, style="green"), Text(modified_at, style="dim"))

        # Display chat list in a panel
        console.print(
            Panel(
                table,
                title=f"[cyan]Available Chat Sessions ({len(chat_list)})[/cyan]",
                border_style="cyan",
            )
        )

    @classmethod
    def show_messages(cls, chat_id: str, markdown: bool) -> None:
        console = Console()
        color = cfg.get("DEFAULT_COLOR")
        messages = cls.chat_session.get_messages(chat_id)

        if not messages:
            display_name = chat_id.replace("_", " ").title()
            console.print(Panel(
                "[yellow]No messages in this chat session.[/yellow]",
                title=f"[cyan][ {display_name} ][/cyan]",
                border_style="cyan"
            ))
            return

        # Collect all message renderables
        renderables = []

        if "APPLY MARKDOWN" in cls.initial_message(chat_id) and markdown:
            theme = cfg.get("CODE_THEME")
            for message in messages:
                if message.startswith("assistant:"):
                    renderables.append(Markdown(message, code_theme=theme))
                elif message.startswith("user:"):
                    renderables.append(Text(message, style="cyan"))
                elif message.startswith("system:"):
                    renderables.append(Text(message, style="green"))
                else:
                    renderables.append(Text(message, style=color))
                renderables.append(Text(""))  # Add empty line between messages
        else:
            for message in messages:
                if message.startswith("user:"):
                    renderables.append(Text(message, style="cyan"))
                elif message.startswith("system:"):
                    renderables.append(Text(message, style="green"))
                else:
                    renderables.append(Text(message, style=color))

        # Display messages in a panel
        display_name = chat_id.replace("_", " ").title()
        console.print(Panel(
            Group(*renderables),
            title=f"[cyan][ {display_name} ][/cyan]",
            border_style="cyan"
        ))

    def validate(self) -> None:
        if self.initiated:
            chat_role_name = self.role.get_role_name(self.initial_message(self.chat_id))
            if not chat_role_name:
                raise BadParameter(f'Could not determine chat role of "{self.chat_id}"')
            if self.role.name == DefaultRoles.DEFAULT.value:
                # If user didn't pass chat mode, we will use the one that was used to initiate the chat.
                self.role = SystemRole.get(chat_role_name)
            else:
                if not self.is_same_role:
                    raise UsageError(
                        f'Cant change chat role to "{self.role.name}" '
                        f'since it was initiated as "{chat_role_name}" chat.'
                    )

    def make_messages(self, prompt: str) -> List[Dict[str, str]]:
        messages = []
        if not self.initiated:
            messages.append({"role": "system", "content": self.role.role})
        messages.append({"role": "user", "content": prompt})
        return messages

    @chat_session
    def get_completion(self, **kwargs: Any) -> Generator[str, None, None]:
        yield from super().get_completion(**kwargs)

    def handle(self, **kwargs: Any) -> str:  # type: ignore[override]
        return super().handle(**kwargs, chat_id=self.chat_id)
