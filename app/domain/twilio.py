from typing import Protocol


class CallProviderPort(Protocol):
    def create_call(self, to: str, from_number: str, url: str) -> str:
        ...


class TwimlBuilderPort(Protocol):
    def build_voice(
        self,
        resident_name: str,
        visitor_name: str,
        plate: str,
        base_url: str | None,
    ) -> str:
        ...

    def build_handle_input(
        self,
        digit: str,
        resident_name: str,
        visitor_name: str,
        plate: str,
        base_url: str | None,
    ) -> str:
        ...
