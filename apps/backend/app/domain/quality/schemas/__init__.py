"""Quality API schemas."""

from app.domain.quality.schemas._defect_group import (
    DefectGroup,
    DefectGroupCreate,
    DefectGroupUpdate,
)
from app.domain.quality.schemas._defect_type import (
    DefectType,
    DefectTypeCreate,
    DefectTypeGroup,
    DefectTypeUpdate,
)
from app.domain.quality.schemas._machine_keys import (
    MachineKgAbp10Keys,
    MachineKgAbp11Keys,
    MachineKgKeys,
    MachineKgOtaa10Keys,
    MachineKgOtaa11Keys,
    MachineKgProvisioning,
    MachineMulticastGroup,
)
from app.domain.quality.schemas._pak_check import PakCheck, PakCheckDefectGroup
from app.domain.quality.schemas._verification import (
    VerificationSession,
    VerificationSessionComplete,
    VerificationSessionDetail,
    VerificationSessionOpen,
    VerificationSessionPak,
    VerificationSessionResult,
    VerificationSlotSession,
    VerificationSlotStep,
    VerificationStep,
    VerificationStepComplete,
    VerificationStepResult,
    VerificationStepStart,
)

__all__ = (
    "DefectGroup",
    "DefectGroupCreate",
    "DefectGroupUpdate",
    "DefectType",
    "DefectTypeCreate",
    "DefectTypeGroup",
    "DefectTypeUpdate",
    "MachineKgAbp10Keys",
    "MachineKgAbp11Keys",
    "MachineKgKeys",
    "MachineKgOtaa10Keys",
    "MachineKgOtaa11Keys",
    "MachineKgProvisioning",
    "MachineMulticastGroup",
    "PakCheck",
    "PakCheckDefectGroup",
    "VerificationSession",
    "VerificationSessionComplete",
    "VerificationSessionDetail",
    "VerificationSessionOpen",
    "VerificationSessionPak",
    "VerificationSessionResult",
    "VerificationSlotSession",
    "VerificationSlotStep",
    "VerificationStep",
    "VerificationStepComplete",
    "VerificationStepResult",
    "VerificationStepStart",
)
