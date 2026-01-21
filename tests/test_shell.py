import os
from pathlib import Path
from unittest.mock import patch

from sgpt.config import cfg
from sgpt.role import DefaultRoles, SystemRole

from .utils import CompletionMock, app, cmd_args, comp_args, mock_comp, runner


def test_shell():
    role = SystemRole.get(DefaultRoles.SHELL.value)
    completion = CompletionMock(return_value=mock_comp("git commit -m test"))
    with patch("sgpt.handlers.handler.completion", completion):
        args = {"prompt": "make a commit using git", "--shell": True}
        result = runner.invoke(app, cmd_args(**args))

        completion.assert_called_once_with_captured(**comp_args(role, args["prompt"]))
        assert "git commit" in result.output
        assert "[E]xecute, [M]odify, [D]escribe, [A]bort:" in result.output


@patch("sgpt.printer.TextPrinter.live_print")
@patch("sgpt.printer.MarkdownPrinter.live_print")
def test_shell_no_markdown(markdown_printer, text_printer):
    completion = CompletionMock(return_value=mock_comp("git commit -m test"))
    with patch("sgpt.handlers.handler.completion", completion):
        args = {"prompt": "make a commit using git", "--shell": True, "--md": True}
        runner.invoke(app, cmd_args(**args))

        # Should ignore --md for --shell option and output text without markdown.
        markdown_printer.assert_not_called()
        text_printer.assert_called()


def test_shell_stdin():
    role = SystemRole.get(DefaultRoles.SHELL.value)
    completion = CompletionMock(return_value=mock_comp("ls -l | sort"))
    with patch("sgpt.handlers.handler.completion", completion):
        args = {"prompt": "Sort by name", "--shell": True}
        stdin = "What is in current folder"
        result = runner.invoke(app, cmd_args(**args), input=stdin)

        expected_prompt = f"{stdin}\n\n{args['prompt']}"
        completion.assert_called_once_with_captured(**comp_args(role, expected_prompt))
        assert "ls -l | sort" in result.output
        assert "[E]xecute, [M]odify, [D]escribe, [A]bort:" in result.output


def test_describe_shell():
    role = SystemRole.get(DefaultRoles.DESCRIBE_SHELL.value)
    completion = CompletionMock(return_value=mock_comp("lists the contents of a folder"))
    with patch("sgpt.handlers.handler.completion", completion):
        args = {"prompt": "ls", "--describe-shell": True}
        result = runner.invoke(app, cmd_args(**args))

        completion.assert_called_once_with_captured(**comp_args(role, args["prompt"]))
        assert result.exit_code == 0
        assert "lists" in result.output


def test_describe_shell_stdin():
    role = SystemRole.get(DefaultRoles.DESCRIBE_SHELL.value)
    completion = CompletionMock(return_value=mock_comp("lists the contents of a folder"))
    with patch("sgpt.handlers.handler.completion", completion):
        args = {"--describe-shell": True}
        stdin = "What is in current folder"
        result = runner.invoke(app, cmd_args(**args), input=stdin)

        expected_prompt = f"{stdin}"
        completion.assert_called_once_with_captured(**comp_args(role, expected_prompt))
        assert result.exit_code == 0
        assert "lists" in result.output


@patch("os.system")
def test_shell_run_description(system):
    completion = CompletionMock(side_effect=[mock_comp("echo hello"), mock_comp("prints hello")])
    with patch("sgpt.handlers.handler.completion", completion):
        args = {"prompt": "echo hello", "--shell": True}
        inputs = "__sgpt__eof__\nd\ne\n"
        result = runner.invoke(app, cmd_args(**args), input=inputs)
        shell = os.environ.get("SHELL", "/bin/sh")
        system.assert_called_once_with(f"{shell} -c 'echo hello'")
        assert result.exit_code == 0
        assert "echo hello" in result.output
        assert "prints hello" in result.output


def test_shell_chat():
    role = SystemRole.get(DefaultRoles.SHELL.value)
    completion = CompletionMock(side_effect=[mock_comp("ls"), mock_comp("ls | sort")])
    with patch("sgpt.handlers.handler.completion", completion):
        chat_name = "_test"
        chat_path = Path(cfg.get("CHAT_CACHE_PATH")) / chat_name
        chat_path.unlink(missing_ok=True)

        args = {"prompt": "list folder", "--shell": True, "--chat": chat_name}
        result = runner.invoke(app, cmd_args(**args))
        assert "ls" in result.output
        assert chat_path.exists()

        args["prompt"] = "sort by name"
        result = runner.invoke(app, cmd_args(**args))
        assert "ls | sort" in result.output

        expected_messages = [
            {"role": "system", "content": role.role},
            {"role": "user", "content": "list folder"},
            {"role": "assistant", "content": "ls"},
            {"role": "user", "content": "sort by name"},
        ]
        expected_args = comp_args(role, "", messages=expected_messages)
        completion.assert_called_with_captured(**expected_args)
        assert completion.call_count == 2

        args["--code"] = True
        result = runner.invoke(app, cmd_args(**args))
        assert result.exit_code == 2
        assert "Error" in result.output
        chat_path.unlink()
        # TODO: Shell chat can be recalled without --shell option.


@patch("os.system")
def test_shell_repl(mock_system):
    role = SystemRole.get(DefaultRoles.SHELL.value)
    completion = CompletionMock(side_effect=[mock_comp("ls"), mock_comp("ls | sort")])
    with patch("sgpt.handlers.handler.completion", completion):
        chat_name = "_test"
        chat_path = Path(cfg.get("CHAT_CACHE_PATH")) / chat_name
        chat_path.unlink(missing_ok=True)

        args = {"--repl": chat_name, "--shell": True}
        inputs = ["__sgpt__eof__", "list folder", "sort by name", "e", "exit()"]
        result = runner.invoke(app, cmd_args(**args), input="\n".join(inputs))
        shell = os.environ.get("SHELL", "/bin/sh")
        mock_system.assert_called_once_with(f"{shell} -c 'ls | sort'")

        expected_messages = [
            {"role": "system", "content": role.role},
            {"role": "user", "content": "list folder"},
            {"role": "assistant", "content": "ls"},
            {"role": "user", "content": "sort by name"},
        ]
        expected_args = comp_args(role, "", messages=expected_messages)
        completion.assert_called_with_captured(**expected_args)
        assert completion.call_count == 2

        assert result.exit_code == 0
        assert ">>> list folder" in result.output
        assert "ls" in result.output
        assert ">>> sort by name" in result.output
        assert "ls | sort" in result.output


@patch("sgpt.handlers.handler.completion")
def test_shell_and_describe_shell(completion):
    args = {"prompt": "ls", "--describe-shell": True, "--shell": True}
    result = runner.invoke(app, cmd_args(**args))

    completion.assert_not_called()
    assert result.exit_code == 2
    assert "Error" in result.output


def test_shell_no_interaction():
    role = SystemRole.get(DefaultRoles.SHELL.value)
    completion = CompletionMock(return_value=mock_comp("git commit -m test"))
    with patch("sgpt.handlers.handler.completion", completion):
        args = {
            "prompt": "make a commit using git",
            "--shell": True,
            "--no-interaction": True,
        }
        result = runner.invoke(app, cmd_args(**args))

        completion.assert_called_once_with_captured(**comp_args(role, args["prompt"]))
        assert result.exit_code == 0
        assert "git commit" in result.output
        assert "[E]xecute" not in result.output
