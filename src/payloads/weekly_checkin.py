from maxapi.filters.callback_payload import CallbackPayload


class WeeklyCheckInStatusPayload(CallbackPayload, prefix="weekly_status"):
    checkin_id: int
    answer: str


class WeeklyCheckInCravingPayload(CallbackPayload, prefix="weekly_craving"):
    checkin_id: int
    craving: int


class WeeklyCheckInMoodPayload(CallbackPayload, prefix="weekly_mood"):
    checkin_id: int
    mood: str
