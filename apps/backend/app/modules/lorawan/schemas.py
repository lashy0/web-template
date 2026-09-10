from pydantic import BaseModel, ConfigDict


class CredentialsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Abp10Credentials(CredentialsPayload):
    devAddr: str
    appSKey: str
    nwkSKey: str
    appKey: str


class Abp11Credentials(CredentialsPayload):
    devAddr: str
    appSKey: str
    fNwkSIntKey: str
    sNwkSIntKey: str
    nwkSEncKey: str
    appKey: str


class Otaa10Credentials(CredentialsPayload):
    devAddr: str
    appKey: str


class Otaa11Credentials(CredentialsPayload):
    devAddr: str
    appKey: str
    nwkKey: str


Credentials = Abp10Credentials | Abp11Credentials | Otaa10Credentials | Otaa11Credentials
