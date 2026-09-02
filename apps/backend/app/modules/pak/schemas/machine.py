from pydantic import BaseModel, Field, SecretStr


class PakTokenRequest(BaseModel):
    client_id: str = Field(min_length=1, max_length=255)
    access_key: SecretStr = Field(min_length=1)


class PakTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    scope: str
