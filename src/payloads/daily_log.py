from maxapi.filters.callback_payload import CallbackPayload


class DailyLogPayload(CallbackPayload, prefix="daily_log"):
    log_id: int
    answer: str