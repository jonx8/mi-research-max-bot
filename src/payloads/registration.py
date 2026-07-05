from maxapi.filters.callback_payload import CallbackPayload

class ConsentPayload(CallbackPayload, prefix="consent"):
    choice: str


class GenderPayload(CallbackPayload, prefix="gender"):
    value: str


class ClinicCenterPayload(CallbackPayload, prefix="clinic_center"):
    center: str


class QuitAttemptsPayload(CallbackPayload, prefix="quit_attempts"):
    value: str


class VapePayload(CallbackPayload, prefix="vape"):
    value: str


class SmokerHouseholdPayload(CallbackPayload, prefix="smoker_household"):
    value: str


class MedicalHelpPayload(CallbackPayload, prefix="medical_help"):
    value: str


class StartQuestionnairePayload(CallbackPayload, prefix="start_q"):
    q_type: str


class AnswerPayload(CallbackPayload, prefix="answer"):
    q_type: str
    q_idx: int
    ans_idx: int


class BackPayload(CallbackPayload, prefix="back"):
    target: str




