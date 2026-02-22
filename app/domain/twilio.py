from typing import Protocol


class CallProviderPort(Protocol):
    def create_call(
        self,
        to: str,
        from_number: str,
        url: str,
        status_callback_url: str | None = None,
    ) -> str:
        ...


class TwimlBuilderPort(Protocol):
    def build_voice(
        self,
        resident_name: str,
        visitor_name: str,
        visit_id: str,
        base_url: str | None,
    ) -> str:
        ...

    def build_handle_input(
        self,
        digit: str,
        resident_name: str,
        visitor_name: str,
        visit_id: str,
        base_url: str | None,
    ) -> str:
        ...


class AccessDecisionNotifierPort(Protocol):
    def notify_decision(
        self,
        decision: str,
        resident_name: str,
        visitor_name: str,
        digit: str,
        visit_id: str,
        call_sid: str | None,
    ) -> None:
        ...
