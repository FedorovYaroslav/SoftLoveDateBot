import asyncio
import subprocess
from collections.abc import AsyncGenerator
from typing import Any

from aiogram.client.session.base import BaseSession
from aiogram.methods import TelegramMethod
from aiogram.methods.base import TelegramType


class CurlSession(BaseSession):
    """
    Telegram API transport через curl + SOCKS5 Happ Plus.

    Используется вместо стандартного aiohttp,
    потому что curl уже проверен и стабильно работает
    через Happ Plus.
    """

    def __init__(
        self,
        proxy: str = "127.0.0.1:10808",
        timeout: float = 60.0,
    ):
        super().__init__(timeout=timeout)
        self.proxy = proxy

    async def close(self) -> None:
        pass

    async def make_request(
        self,
        bot,
        method: TelegramMethod[TelegramType],
        timeout: int | None = None,
    ) -> TelegramType:

        request_timeout = timeout or int(self.timeout)

        url = self.api.api_url(
            token=bot.token,
            method=method.__api_method__,
        )

        files: dict[str, Any] = {}

        prepared_data = {}

        for key, value in method.model_dump(warnings=False).items():
            prepared_value = self.prepare_value(
                value,
                bot=bot,
                files=files,
            )

            if prepared_value is not None:
                prepared_data[key] = prepared_value

        command = [
            "curl",
            "--silent",
            "--show-error",
            "--location",
            "--socks5-hostname",
            self.proxy,
            "--connect-timeout",
            "15",
            "--max-time",
            str(request_timeout + 15),
        ]

        for key, value in prepared_data.items():
            command.extend(
                [
                    "--form-string",
                    f"{key}={value}",
                ]
            )

        command.append(url)

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                command,
                capture_output=True,
                timeout=request_timeout + 20,
            )
        except subprocess.TimeoutExpired as error:
            raise TimeoutError(
                f"Telegram API request timed out after "
                f"{request_timeout + 20} seconds"
            ) from error

        content = result.stdout.decode(
            "utf-8",
            errors="replace",
        )

        if result.returncode != 0:
            error_text = result.stderr.decode(
                "utf-8",
                errors="replace",
            )

            raise RuntimeError(
                f"curl error while calling Telegram API: "
                f"{error_text.strip()}"
            )

        response = self.check_response(
            bot=bot,
            method=method,
            status_code=200,
            content=content,
        )

        return response.result

    async def stream_content(
        self,
        url: str,
        headers: dict[str, Any] | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes, None]:

        command = [
            "curl",
            "--silent",
            "--show-error",
            "--location",
            "--socks5-hostname",
            self.proxy,
            "--connect-timeout",
            "15",
            "--max-time",
            str(timeout),
            url,
        ]

        result = await asyncio.to_thread(
            subprocess.run,
            command,
            capture_output=True,
            timeout=timeout + 10,
        )

        if result.returncode != 0:
            error_text = result.stderr.decode(
                "utf-8",
                errors="replace",
            )

            raise RuntimeError(
                f"curl stream error: {error_text.strip()}"
            )

        data = result.stdout

        for position in range(0, len(data), chunk_size):
            yield data[position:position + chunk_size]