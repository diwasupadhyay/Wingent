from pydantic import BaseModel, Field, field_validator


class CommandRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description='Request prompt for the local agent.')

    @field_validator('prompt')
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError('prompt must not be blank')
        return cleaned


class CommandResponse(BaseModel):
    result: str
