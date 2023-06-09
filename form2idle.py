#!/usr/bin/python
"""
form2idle.py
Copyright (C) 2023 Axel Pirek

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
import argparse
import asyncio
import dataclasses
import json
import sys
import uuid
from datetime import datetime, timedelta


class _RequestJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return f"{{{obj}}}"
        return super().default(obj)


def _response_object_hook(obj):
    if "Id" in obj:
        obj["Id"] = uuid.UUID(obj["Id"])
    return obj


@dataclasses.dataclass
class Request:
    Method: str
    Id: uuid.UUID = dataclasses.field(default_factory=uuid.uuid1)
    Version: int = 1

    def to_json(self) -> str:
        return json.dumps(dataclasses.asdict(self), cls=_RequestJSONEncoder)


@dataclasses.dataclass
class Response:
    Id: uuid.UUID
    Parameters: dict
    ReplyToMethod: str
    Success: bool
    Version: int

    @classmethod
    def from_json(cls, s: str) -> "Response":
        return cls(**json.loads(s, object_hook=_response_object_hook))


class Form2:
    def __init__(self, host: str, port: int = 35):
        self.host = host
        self.port = port
        self._reader: asyncio.StreamReader = None
        self._writer: asyncio.StreamWriter = None

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    async def open(self) -> None:
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)

    async def close(self) -> None:
        self._writer.close()
        await self._writer.wait_closed()
        self._reader = None
        self._writer = None

    async def _call(self, request: Request) -> Response:
        data = bytes(request.to_json(), "utf-8")
        # uint_32 payload size
        self._writer.write(len(data).to_bytes(4, "little"))
        # payload
        self._writer.write(data)
        # terminator
        self._writer.write(bytes([0x00] * 8))

        # uint_32 payload size
        size = int.from_bytes(await self._reader.read(4), "little")
        # payload (in chunks up to 1448 bytes)
        data = bytes()
        while len(data) < size:
            data += await self._reader.read(size - len(data))
        # terminator
        assert await self._reader.read(8) == bytes([0x00] * 8)
        response = Response.from_json(str(data, "utf-8"))
        assert request.Id == response.Id
        return response

    async def get_print_time_remaining(self) -> float:
        status = (await self._call(Request("PROTOCOL_METHOD_GET_STATUS"))).Parameters
        if status["isPrinting"] and (print_time_remaining_ms := status["estimatedPrintTimeRemaining_ms"]) > 0:
            return print_time_remaining_ms / 1000
        else:
            return 0.0


def format_time_remaining(seconds: float) -> str:
    hours = int(seconds / (60 * 60))
    minutes = int(seconds / 60 % 60)
    seconds = int(seconds % 60)
    if hours:
        return f"{hours}:{minutes:02}:{seconds:02}"
    else:
        return f"{minutes:02}:{seconds:02}"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Check if Form 2 printer is idle")
    parser.add_argument("host", metavar="HOST", help="Host name or IP address of printer")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print current time and remaining print time")
    parser.add_argument("-w", "--wait", action="store_true", help="Wait for print to finish")
    parser.add_argument("-e", "--eta", action="store_true", help="Print remaining print time as estimated time of arrival")
    args = parser.parse_args()

    async with Form2(host=args.host) as form2:
        while True:
            now = datetime.now()
            time_remaining = await form2.get_print_time_remaining()
            if time_remaining <= 0:
                return 0
            if args.verbose:
                if args.eta:
                    eta = now + timedelta(seconds=time_remaining)
                    print(f"{now:%Y-%m-%d %H:%M:%S}, {eta:%Y-%m-%d %H:%M:%S}")
                else:
                    print(f"{now:%Y-%m-%d %H:%M:%S}, {format_time_remaining(time_remaining)}")
            if args.wait:
                try:
                    # Preform polls every 5 seconds
                    await asyncio.sleep(5)
                    continue
                except asyncio.CancelledError:
                    return 1
            return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
