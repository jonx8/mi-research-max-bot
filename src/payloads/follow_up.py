from maxapi.filters.callback_payload import CallbackPayload


class FollowUpPPA7Payload(CallbackPayload, prefix="follow_up_ppa7"):
    follow_up_id: int
    answer: str
