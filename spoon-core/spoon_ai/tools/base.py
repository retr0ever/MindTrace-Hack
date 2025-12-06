from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, Field


class BaseTool(ABC, BaseModel):
    name: str = Field(description="The name of the tool")
    description: str = Field(description="A description of the tool")
    parameters: dict = Field(description="The parameters of the tool")

    model_config = {
        "arbitrary_types_allowed": True
    }


    async def __call__(self, *args, **kwargs) -> Any:
        return await self.execute(*args, **kwargs)

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        raise NotImplementedError("Subclasses must implement this method")

    def to_param(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

class ToolFailure(Exception):
    """Exception to indicate a tool execution failure."""
    def __init__(self, message: str, *, cause: Exception = None):
        super().__init__(message)
        self.cause = cause

class ToolResult(BaseModel):
    output: Any = Field(default=None)
    error: Optional[str] = Field(default=None)
    system: Optional[str] = Field(default=None)

    def __bool__(self):
        fields = type(self).model_fields
        return any(getattr(self, attr) for attr in fields.keys())

    def __add__(self, other: "ToolResult") -> "ToolResult":
        def combine_fields(field: Optional[str], other_field: Optional[str], concatenate: bool = False):
            if field and other_field:
                if concatenate:
                    return field + other_field
                raise ValueError("Cannot concatenate non-string fields")
            return field or other_field

        return ToolResult(
            output=combine_fields(self.output, other.output),
            error=combine_fields(self.error, other.error),
            system=combine_fields(self.system, other.system),
        )

    def __str__(self) -> str:
        return f"Error: {self.error}" if self.error else f"Output: {self.output}"

    def replace(self, **kwargs) -> "ToolResult":
        return type(self)(**{**self.model_dump(), **kwargs})
