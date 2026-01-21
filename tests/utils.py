import copy
from datetime import datetime
from unittest.mock import MagicMock

import typer
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import Choice as StreamChoice
from openai.types.chat.chat_completion_chunk import ChoiceDelta
from typer.testing import CliRunner

from sgpt import main
from sgpt.config import cfg

runner = CliRunner()
app = typer.Typer(add_completion=False)
app.command()(main)


class CompletionMock(MagicMock):
    """
    A mock that captures deep copies of mutable arguments (like messages list)
    at call time, so later modifications don't affect the recorded calls.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.captured_calls = []

    def __call__(self, *args, **kwargs):
        # Deep copy kwargs to capture the state at call time
        captured_kwargs = copy.deepcopy(kwargs)
        self.captured_calls.append({"args": args, "kwargs": captured_kwargs})
        return super().__call__(*args, **kwargs)

    def assert_called_once_with_captured(self, **expected_kwargs):
        """Assert that the mock was called once with the expected kwargs (using captured copy)."""
        assert len(self.captured_calls) == 1, (
            f"Expected 1 call, got {len(self.captured_calls)}"
        )
        actual_kwargs = self.captured_calls[0]["kwargs"]
        assert actual_kwargs == expected_kwargs, (
            f"Expected: {expected_kwargs}\nActual: {actual_kwargs}"
        )

    def assert_called_with_captured(self, **expected_kwargs):
        """Assert that the last call matches the expected kwargs (using captured copy)."""
        assert len(self.captured_calls) > 0, "Expected at least 1 call, got 0"
        actual_kwargs = self.captured_calls[-1]["kwargs"]
        assert actual_kwargs == expected_kwargs, (
            f"Expected: {expected_kwargs}\nActual: {actual_kwargs}"
        )


def mock_comp(tokens_string):
    return [
        ChatCompletionChunk(
            id="foo",
            model=cfg.get("DEFAULT_MODEL"),
            object="chat.completion.chunk",
            choices=[
                StreamChoice(
                    index=0,
                    finish_reason=None,
                    delta=ChoiceDelta(content=token, role="assistant"),
                ),
            ],
            created=int(datetime.now().timestamp()),
        )
        for token in tokens_string
    ]


def cmd_args(prompt="", **kwargs):
    arguments = [prompt]
    for key, value in kwargs.items():
        arguments.append(key)
        if isinstance(value, bool):
            continue
        arguments.append(value)
    arguments.append("--no-cache")
    arguments.append("--no-functions")
    return arguments


def comp_args(role, prompt, **kwargs):
    # Build default messages if not provided
    if "messages" not in kwargs:
        messages = [
            {"role": "system", "content": role.role},
            {"role": "user", "content": prompt},
        ]
    else:
        messages = kwargs.pop("messages")

    return {
        "messages": messages,
        "model": kwargs.pop("model", cfg.get("DEFAULT_MODEL")),
        "max_tokens": kwargs.pop("max_tokens", int(cfg.get("MAX_TOKENS"))),
        "temperature": kwargs.pop("temperature", float(cfg.get("TEMPERATURE"))),
        "top_p": kwargs.pop("top_p", 1.0),
        "stream": True,
        **kwargs,
    }
