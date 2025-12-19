"""
Core модуль - базовая инфраструктура системы.

Включает state machine, manifest, audit log, config и exceptions.
"""

from .state_machine import UnitState, UnitStateMachine, ALLOWED_TRANSITIONS, validate_state_transition
from .manifest import (
    load_manifest,
    save_manifest,
    create_manifest_v2,
    update_manifest_operation,
    update_manifest_state,
)
from .audit import AuditLogger
from .config import (
    INPUT_DIR,
    PROCESSING_DIR,
    MERGE_DIR,
    READY2DOCLING_DIR,
    get_cycle_paths,
    init_directory_structure,
    get_pending_paths,
)
from .exceptions import (
    PreprocessingError,
    StateTransitionError,
    ManifestError,
    OperationError,
    QuarantineError,
)

__all__ = [
    # State Machine
    "UnitState",
    "UnitStateMachine",
    "ALLOWED_TRANSITIONS",
    "validate_state_transition",
    # Manifest
    "load_manifest",
    "save_manifest",
    "create_manifest_v2",
    "update_manifest_operation",
    "update_manifest_state",
    # Audit
    "AuditLogger",
    # Config
    "INPUT_DIR",
    "PROCESSING_DIR",
    "MERGE_DIR",
    "READY2DOCLING_DIR",
    "get_cycle_paths",
    "init_directory_structure",
    "get_pending_paths",
    # Exceptions
    "PreprocessingError",
    "StateTransitionError",
    "ManifestError",
    "OperationError",
    "QuarantineError",
]

