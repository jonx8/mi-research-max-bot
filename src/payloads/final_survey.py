from maxapi.filters.callback_payload import CallbackPayload


class FinalPPA30Payload(CallbackPayload, prefix="final_ppa30"):
    survey_id: int
    answer: str


class FinalPPA7Payload(CallbackPayload, prefix="final_ppa7"):
    survey_id: int
    answer: str


class FinalQuitAttemptsPayload(CallbackPayload, prefix="final_quit_attempts"):
    survey_id: int
    answer: str

