import json
from pathlib import Path
from typing import Dict, Generator, List

import requests
import typer
import re

from .cache import Cache
from .config import SHELL_GPT_CONFIG_PATH, cfg

CACHE_LENGTH = int(cfg.get("CACHE_LENGTH"))
CACHE_PATH = Path(cfg.get("CACHE_PATH"))
REQUEST_TIMEOUT = int(cfg.get("REQUEST_TIMEOUT"))
DISABLE_STREAMING = str(cfg.get("DISABLE_STREAMING"))


class OpenAIClient:
    cache = Cache(CACHE_LENGTH, CACHE_PATH)

    def __init__(self, api_host: str, api_key: str) -> None:
        self.__api_key = api_key
        self.api_host = api_host

    @cache
    def _request(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        temperature: float = 1,
        top_probability: float = 1,
    ) -> Generator[str, None, None]:
        """
        Make request to OpenAI API, read more:
        https://platform.openai.com/docs/api-reference/chat

        :param messages: List of messages {"role": user or assistant, "content": message_string}
        :param model: String gpt-3.5-turbo or gpt-3.5-turbo-0301
        :param temperature: Float in 0.0 - 2.0 range.
        :param top_probability: Float in 0.0 - 1.0 range.
        :return: Response body JSON.
        """
        stream = DISABLE_STREAMING == "false"
        data = {
            "messages": messages,
            "model": model,
            "parameters": {
                "frequence_penalty": 1,
                "temperature": temperature,
                "top_p": top_probability,
                "top_k": 50,
                "max_new_tokens": 2048,
            },
        }
        endpoint = f"{self.api_host}/api/models/conversation"
        if stream:
            endpoint += "_stream"
        response = requests.post(
            endpoint,
            # Hide API key from Rich traceback.
            headers={
                "Content-Type": "application/json",
                "X-API-KEY": f"{self.__api_key}",
            },
            json=data,
            timeout=REQUEST_TIMEOUT,
            stream=stream,
        )
        # Check if OPENAI_API_KEY is valid
        if response.status_code == 401 or response.status_code == 403:
            typer.secho(
                f"Invalid OpenAI API key, update your config file: {SHELL_GPT_CONFIG_PATH}",
                fg="red",
            )
        response.raise_for_status()
        # TODO: Optimise.
        # https://github.com/openai/openai-python/blob/237448dc072a2c062698da3f9f512fae38300c1c/openai/api_requestor.py#L98
        if not stream:
            data = response.json()
            yield data["generated_text"]  # type: ignore
            return
        for line in response.iter_lines():
            data = line.lstrip(b"data: ").decode("utf-8")
            if data == "[DONE]":  # type: ignore
                break
            if data == "event: ping" or not data:
                continue
            if re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6}', data):
                continue
            data = json.loads(data)  # type: ignore
            if "generated_text" not in data:
                continue
            yield data["generated_text"]

    def get_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        temperature: float = 1,
        top_probability: float = 1,
        caching: bool = True,
    ) -> Generator[str, None, None]:
        """
        Generates single completion for prompt (message).

        :param messages: List of dict with messages and roles.
        :param model: String gpt-3.5-turbo or gpt-3.5-turbo-0301.
        :param temperature: Float in 0.0 - 1.0 range.
        :param top_probability: Float in 0.0 - 1.0 range.
        :param caching: Boolean value to enable/disable caching.
        :return: String generated completion.
        """
        yield from self._request(
            messages,
            model,
            temperature,
            top_probability,
            caching=caching,
        )
