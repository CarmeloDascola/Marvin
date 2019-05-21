import asyncio
from concurrent.futures import ThreadPoolExecutor

from cache import Cacher


class Preloader(Cacher):
    _loop: asyncio.AbstractEventLoop

    def __init__(self, loop: asyncio.AbstractEventLoop, *args, **kw):
        super().__init__(*args, **kw)

        self._loop = loop
        loop.create_task(self._task())

    async def _task(self):
        while self._loop.is_running():
            self._loop.run_in_executor(ThreadPoolExecutor(), self.call)
            await asyncio.sleep(self._expire_time)


if __name__ == "__main__":
    from time import time

    async def _check_output(obj):
        _output = obj.output
        await asyncio.sleep(1)
        assert _output == obj.output

        await asyncio.sleep(1)
        assert _output != obj.output

    _loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
    _time_preloader = Preloader(_loop, time, expire_time=2)
    _loop.run_until_complete(_check_output(_time_preloader))