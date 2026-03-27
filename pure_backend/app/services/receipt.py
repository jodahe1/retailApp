from __future__ import annotations

from abc import ABC, abstractmethod
import logging

from app.models.order import Order

logger = logging.getLogger(__name__)


class ReceiptPrinter(ABC):
    @abstractmethod
    def print_receipt(self, order: Order) -> None:
        raise NotImplementedError


class ConsoleReceiptPrinter(ReceiptPrinter):
    """Offline-friendly default printer abstraction implementation."""

    def print_receipt(self, order: Order) -> None:
        logger.info(
            "receipt_printed order_no=%s final_amount=%s lines=%s",
            order.order_no,
            order.final_amount,
            len(order.lines),
        )
