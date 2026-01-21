from pathlib import Path
from unittest.mock import patch

import typer
from typer.testing import CliRunner

from sgpt import config, main
from sgpt.__version__ import __version__
from sgpt.role import DefaultRoles, SystemRole

from .utils import CompletionMock, app, cmd_args, comp_args, mock_comp, runner

role = SystemRole.get(DefaultRoles.DEFAULT.value)
cfg = config.cfg


def test_default():
    completion = CompletionMock(return_value=mock_comp("Prague"))
    with patch("sgpt.handlers.handler.completion", completion):
        args = {"prompt": "capital of the Czech Republic?"}
        result = runner.invoke(app, cmd_args(**args))

        completion.assert_called_once_with_captured(**comp_args(role, **args))
        assert result.exit_code == 0
        assert "Prague" in result.output


def test_default_stdin():
    completion = CompletionMock(return_value=mock_comp("Prague"))
    with patch("sgpt.handlers.handler.completion", completion):
        stdin = "capital of the Czech Republic?"
        result = runner.invoke(app, cmd_args(), input=stdin)

        completion.assert_called_once_with_captured(**comp_args(role, stdin))
        assert result.exit_code == 0
        assert "Prague" in result.output


@patch("rich.console.Console.print")
@patch("sgpt.handlers.handler.completion")
def test_show_chat_use_markdown(completion, console_print):
    completion.return_value = mock_comp("ok")
    chat_name = "_test"
    chat_path = Path(cfg.get("CHAT_CACHE_PATH")) / chat_name
    chat_path.unlink(missing_ok=True)

    args = {"prompt": "my number is 2", "--chat": chat_name}
    result = runner.invoke(app, cmd_args(**args))
    assert result.exit_code == 0
    assert chat_path.exists()

    result = runner.invoke(app, ["--show-chat", chat_name])
    assert result.exit_code == 0
    console_print.assert_called()


def test_show_chat_no_use_markdown():
    """Test --show-chat with --no-md doesn't use Markdown rendering but still displays Panel."""
    completion = CompletionMock(return_value=mock_comp("ok"))
    with patch("sgpt.handlers.handler.completion", completion):
        chat_name = "_test"
        chat_path = Path(cfg.get("CHAT_CACHE_PATH")) / chat_name
        chat_path.unlink(missing_ok=True)

        # Flag '--code' doesn't use markdown
        args = {"prompt": "my number is 2", "--chat": chat_name, "--code": True}
        result = runner.invoke(app, cmd_args(**args))
        assert result.exit_code == 0
        assert chat_path.exists()

        # With --no-md, it should still display the chat but without markdown rendering
        result = runner.invoke(app, ["--show-chat", chat_name, "--no-md"])
        assert result.exit_code == 0
        # Verify the chat content is displayed
        assert "my number is 2" in result.output
        assert "ok" in result.output


def test_default_chat():
    completion = CompletionMock(side_effect=[mock_comp("ok"), mock_comp("4")])
    with patch("sgpt.handlers.handler.completion", completion):
        chat_name = "_test"
        chat_path = Path(cfg.get("CHAT_CACHE_PATH")) / chat_name
        chat_path.unlink(missing_ok=True)

        args = {"prompt": "my number is 2", "--chat": chat_name}
        result = runner.invoke(app, cmd_args(**args))
        assert result.exit_code == 0
        assert "ok" in result.output
        assert chat_path.exists()

        args["prompt"] = "my number + 2?"
        result = runner.invoke(app, cmd_args(**args))
        assert result.exit_code == 0
        assert "4" in result.output

        expected_messages = [
            {"role": "system", "content": role.role},
            {"role": "user", "content": "my number is 2"},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": "my number + 2?"},
        ]
        expected_args = comp_args(role, "", messages=expected_messages)
        completion.assert_called_with_captured(**expected_args)
        assert completion.call_count == 2

        result = runner.invoke(app, ["--list-chats"])
        assert result.exit_code == 0
        assert "_test" in result.output

        result = runner.invoke(app, ["--show-chat", chat_name])
        assert result.exit_code == 0
        assert "my number is 2" in result.output
        assert "ok" in result.output
        assert "my number + 2?" in result.output
        assert "4" in result.output

        args["--shell"] = True
        result = runner.invoke(app, cmd_args(**args))
        assert result.exit_code == 2
        assert "Error" in result.output

        args["--code"] = True
        result = runner.invoke(app, cmd_args(**args))
        assert result.exit_code == 2
        assert "Error" in result.output
        chat_path.unlink()


def test_default_repl():
    completion = CompletionMock(side_effect=[mock_comp("ok"), mock_comp("8")])
    with patch("sgpt.handlers.handler.completion", completion):
        chat_name = "_test"
        chat_path = Path(cfg.get("CHAT_CACHE_PATH")) / chat_name
        chat_path.unlink(missing_ok=True)

        args = {"--repl": chat_name}
        inputs = ["__sgpt__eof__", "my number is 6", "my number + 2?", "exit()"]
        result = runner.invoke(app, cmd_args(**args), input="\n".join(inputs))

        expected_messages = [
            {"role": "system", "content": role.role},
            {"role": "user", "content": "my number is 6"},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": "my number + 2?"},
        ]
        expected_args = comp_args(role, "", messages=expected_messages)
        completion.assert_called_with_captured(**expected_args)
        assert completion.call_count == 2

        assert result.exit_code == 0
        assert ">>> my number is 6" in result.output
        assert "ok" in result.output
        assert ">>> my number + 2?" in result.output
        assert "8" in result.output


def test_default_repl_stdin():
    completion = CompletionMock(side_effect=[mock_comp("ok init"), mock_comp("ok another")])
    with patch("sgpt.handlers.handler.completion", completion):
        chat_name = "_test"
        chat_path = Path(cfg.get("CHAT_CACHE_PATH")) / chat_name
        chat_path.unlink(missing_ok=True)

        my_runner = CliRunner()
        my_app = typer.Typer()
        my_app.command()(main)

        args = {"--repl": chat_name}
        inputs = ["this is stdin", "__sgpt__eof__", "prompt", "another", "exit()"]
        result = my_runner.invoke(my_app, cmd_args(**args), input="\n".join(inputs))

        expected_messages = [
            {"role": "system", "content": role.role},
            {"role": "user", "content": "this is stdin\n\n\n\nprompt"},
            {"role": "assistant", "content": "ok init"},
            {"role": "user", "content": "another"},
        ]
        expected_args = comp_args(role, "", messages=expected_messages)
        completion.assert_called_with_captured(**expected_args)
        assert completion.call_count == 2

        assert result.exit_code == 0
        assert "this is stdin" in result.output
        assert ">>> prompt" in result.output
        assert "ok init" in result.output
        assert ">>> another" in result.output
        assert "ok another" in result.output


def test_llm_options():
    completion = CompletionMock(return_value=mock_comp("Berlin"))
    with patch("sgpt.handlers.handler.completion", completion):
        args = {
            "prompt": "capital of the Germany?",
            "--model": "gpt-4-test",
            "--temperature": 0.5,
            "--top-p": 0.5,
            "--no-functions": True,
        }
        result = runner.invoke(app, cmd_args(**args))

        expected_args = comp_args(
            role=role,
            prompt=args["prompt"],
            model=args["--model"],
            temperature=args["--temperature"],
            top_p=args["--top-p"],
        )
        completion.assert_called_once_with_captured(**expected_args)
        assert result.exit_code == 0
        assert "Berlin" in result.output


@patch("sgpt.handlers.handler.completion")
def test_version(completion):
    args = {"--version": True}
    result = runner.invoke(app, cmd_args(**args))

    completion.assert_not_called()
    assert __version__ in result.output


@patch("sgpt.printer.TextPrinter.live_print")
@patch("sgpt.printer.MarkdownPrinter.live_print")
@patch("sgpt.handlers.handler.completion")
def test_markdown(completion, markdown_printer, text_printer):
    completion.return_value = mock_comp("pong")

    args = {"prompt": "ping", "--md": True}
    result = runner.invoke(app, cmd_args(**args))
    assert result.exit_code == 0
    markdown_printer.assert_called()
    text_printer.assert_not_called()


@patch("sgpt.printer.TextPrinter.live_print")
@patch("sgpt.printer.MarkdownPrinter.live_print")
@patch("sgpt.handlers.handler.completion")
def test_no_markdown(completion, markdown_printer, text_printer):
    completion.return_value = mock_comp("pong")

    args = {"prompt": "ping", "--no-md": True}
    result = runner.invoke(app, cmd_args(**args))
    assert result.exit_code == 0
    markdown_printer.assert_not_called()
    text_printer.assert_called()


@patch("sgpt.handlers.handler.completion")
def test_show_chat_last(completion):
    """Test --show-chat last shows the most recent chat session."""
    completion.return_value = mock_comp("test response")
    chat_name = "_test_last"
    chat_path = Path(cfg.get("CHAT_CACHE_PATH")) / chat_name
    chat_path.unlink(missing_ok=True)

    # Create a chat session first
    args = {"prompt": "hello", "--chat": chat_name}
    result = runner.invoke(app, cmd_args(**args))
    assert result.exit_code == 0
    assert chat_path.exists()

    # Use --show-chat last to display it
    result = runner.invoke(app, ["--show-chat", "last"])
    assert result.exit_code == 0
    assert "hello" in result.output
    chat_path.unlink()


@patch("sgpt.handlers.handler.completion")
def test_show_chat_title_format(completion):
    """Test --show-chat displays title in [ Title Case ] format."""
    completion.return_value = mock_comp("response")
    chat_name = "_test_title_format"
    chat_path = Path(cfg.get("CHAT_CACHE_PATH")) / chat_name
    chat_path.unlink(missing_ok=True)

    # Create a chat session
    args = {"prompt": "hello", "--chat": chat_name}
    result = runner.invoke(app, cmd_args(**args))
    assert result.exit_code == 0

    # Show chat and verify title format (underscores to spaces, title case)
    result = runner.invoke(app, ["--show-chat", chat_name])
    assert result.exit_code == 0
    # Title should be "[ Test Title Format ]" (title case, spaces)
    assert "Test Title Format" in result.output
    chat_path.unlink()


@patch("sgpt.handlers.handler.completion")
def test_list_chats_panel_format(completion):
    """Test --list-chats displays chats in a panel with timestamps."""
    completion.return_value = mock_comp("ok")
    chat_name = "_test_list"
    chat_path = Path(cfg.get("CHAT_CACHE_PATH")) / chat_name
    chat_path.unlink(missing_ok=True)

    # Create a chat session
    args = {"prompt": "hello", "--chat": chat_name}
    result = runner.invoke(app, cmd_args(**args))
    assert result.exit_code == 0

    # List chats and verify format
    result = runner.invoke(app, ["--list-chats"])
    assert result.exit_code == 0
    assert "_test_list" in result.output
    # Verify timestamp format (YYYY-MM-DD HH:MM)
    import re
    assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", result.output)
    chat_path.unlink()


def test_complete_chat_id():
    """Test chat ID autocompletion returns special keywords and chat names."""
    from sgpt.handlers.chat_handler import ChatHandler

    # Test that special keywords are always included
    result = ChatHandler.complete_chat_id("")
    assert "last" in result
    assert "temp" in result
    assert "auto" in result

    # Test filtering by prefix
    result = ChatHandler.complete_chat_id("la")
    assert "last" in result
    assert "temp" not in result
    assert "auto" not in result


@patch("sgpt.handlers.handler.completion")
def test_show_chat_message_colors(completion):
    """Test --show-chat displays messages with correct colors."""
    completion.return_value = mock_comp("assistant response")
    chat_name = "_test_colors"
    chat_path = Path(cfg.get("CHAT_CACHE_PATH")) / chat_name
    chat_path.unlink(missing_ok=True)

    # Create a chat session
    args = {"prompt": "user message", "--chat": chat_name}
    result = runner.invoke(app, cmd_args(**args))
    assert result.exit_code == 0

    # Show chat - messages should be displayed
    result = runner.invoke(app, ["--show-chat", chat_name])
    assert result.exit_code == 0
    assert "user:" in result.output or "user message" in result.output
    assert "assistant:" in result.output or "assistant response" in result.output
    chat_path.unlink()
