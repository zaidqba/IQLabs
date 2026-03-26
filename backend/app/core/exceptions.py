"""IQ-RAD Domain Exception Hierarchy"""


class IQRADBaseError(Exception):
    """Base for all IQ-RAD application exceptions."""


class AuthenticationError(IQRADBaseError):
    """Invalid credentials or token."""


class AccountLockedError(IQRADBaseError):
    """User account is locked after repeated failures."""


class InsufficientPermissionsError(IQRADBaseError):
    """User does not have required permissions for this action."""


class ResourceNotFoundError(IQRADBaseError):
    """Requested resource does not exist."""


class ValidationError(IQRADBaseError):
    """Business-rule validation failure."""


class SignatureError(IQRADBaseError):
    """Electronic signature verification failed."""


class DeviceConnectionError(IQRADBaseError):
    """Cannot connect to or communicate with a device."""


class DataQualityError(IQRADBaseError):
    """Received data fails quality/integrity checks."""


class NTPSyncError(IQRADBaseError):
    """NTP clock synchronization check failed."""


class ImmutabilityViolationError(IQRADBaseError):
    """Attempted to modify an immutable compliance record."""
