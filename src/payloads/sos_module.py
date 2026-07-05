from maxapi.filters.callback_payload import CallbackPayload


class TechniquePayload(CallbackPayload, prefix="sos_technique"):
    technique_id: str


class NewTechniquesPayload(CallbackPayload, prefix="sos_new_techniques"):
    pass


class HelpedPayload(CallbackPayload, prefix="sos_helped"):
    pass


class AnalyzeCravingPayload(CallbackPayload, prefix="analyze_craving"):
    pass


class BeginAnalysisPayload(CallbackPayload, prefix="begin_craving_analysis"):
    pass
