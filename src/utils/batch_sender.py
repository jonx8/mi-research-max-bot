import asyncio
import logging
from typing import List, Callable, Awaitable, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BatchSender(Generic[T]):
    """Утилита для порционной отправки сообщений."""

    def __init__(self, batch_size: int = 25, delay_between_batches: float = 1.0):
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches

    async def send(
            self,
            items: List[T],
            send_func: Callable[[T], Awaitable[None]],
    ) -> None:
        """Отправляет элементы порциями, выполняя send_func для каждого элемента параллельно внутри чанка."""

        if not items:
            return

        chunks = [items[i:i + self.batch_size] for i in range(0, len(items), self.batch_size)]
        total_chunks = len(chunks)

        for idx, chunk in enumerate(chunks):
            tasks = [send_func(item) for item in chunk]
            await asyncio.gather(*tasks, return_exceptions=True)

            if idx < total_chunks - 1:
                logger.info(f"Пауза {self.delay_between_batches}с между чанками ({idx + 1}/{total_chunks})")
                await asyncio.sleep(self.delay_between_batches)
