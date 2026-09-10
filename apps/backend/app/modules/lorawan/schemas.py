from pydantic import BaseModel, ConfigDict


class CredentialsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Abp10Credentials(CredentialsPayload):
    dev_addr: str
    app_s_key: str
    nwk_s_key: str
    app_key: str


class Abp11Credentials(CredentialsPayload):
    dev_addr: str
    app_s_key: str
    f_nwk_s_int_key: str
    s_nwk_s_int_key: str
    nwk_s_enc_key: str
    app_key: str


class Otaa10Credentials(CredentialsPayload):
    dev_addr: str
    app_key: str


class Otaa11Credentials(CredentialsPayload):
    dev_addr: str
    app_key: str
    nwk_key: str


Credentials = Abp10Credentials | Abp11Credentials | Otaa10Credentials | Otaa11Credentials
