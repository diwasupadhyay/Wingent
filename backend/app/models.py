from pydantic import BaseModel, Field, field_validator


class CommandRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4096, description='Request prompt for the local agent.')
    review_actions: bool = Field(default=False, strict=True)

    @field_validator('prompt')
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError('prompt must not be blank')
        return cleaned


class CommandResponse(BaseModel):
    result: str
