"""What a PAK writes into a KG unit before verifying it."""

from __future__ import annotations

from app.lib.schema import CamelizedBaseStruct


class _MachineKgKeys(CamelizedBaseStruct, tag_field="scheme"):
    """The LoRaWAN keys of a unit; ``scheme`` names the activation type and LoRaWAN version of its batch.

    Hex values are lower case. ABP units also get the AppKey and JoinEUI, as
    PAKs have written them so far.
    """


class MachineKgOtaa10Keys(_MachineKgKeys, tag="otaa-1.0"):
    join_eui: str
    """The AppEUI of LoRaWAN 1.0."""
    app_key: str


class MachineKgOtaa11Keys(_MachineKgKeys, tag="otaa-1.1"):
    join_eui: str
    app_key: str
    nwk_key: str


class MachineKgAbp10Keys(_MachineKgKeys, tag="abp-1.0"):
    dev_addr: str
    nwk_s_key: str
    app_s_key: str
    app_key: str
    join_eui: str


class MachineKgAbp11Keys(_MachineKgKeys, tag="abp-1.1"):
    dev_addr: str
    f_nwk_s_int_key: str
    s_nwk_s_int_key: str
    nwk_s_enc_key: str
    app_s_key: str
    app_key: str
    join_eui: str


MachineKgKeys = MachineKgOtaa10Keys | MachineKgOtaa11Keys | MachineKgAbp10Keys | MachineKgAbp11Keys


class MachineMulticastGroup(CamelizedBaseStruct):
    """A multicast group of the unit's batch."""

    group_id: int
    mc_addr: str
    mc_nwk_s_key: str
    mc_app_s_key: str
    frequency_hz: int
    datarate: int


class MachineKgProvisioning(CamelizedBaseStruct):
    """Everything a PAK writes into a KG unit: its keys and the multicast groups of its batch."""

    dev_eui: str
    keys: MachineKgKeys
    multicast: list[MachineMulticastGroup]
    """Both groups of the batch, by ``groupId``."""
