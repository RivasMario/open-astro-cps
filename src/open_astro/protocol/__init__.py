from .framing import PacketFramer
from .serial_link import RadioSerialLink
from .flasher import AstroFlasher
from .commands import DeviceAddress, CommandResponse, ENTER_PROGRAMMING, TEST_MODE
from .at_interface import ATInterfaceError, ping as at_ping, get_radio_identity as at_get_radio_identity, get_firmware_banner as at_get_firmware_banner

# Note: the real SB9600 CRC algorithm (Paul Banks/M3OSL's GM1200 analysis) is
# GPLv3+, incompatible with this MIT-licensed package, and deliberately kept
# out of src/ -- see tools/sb9600_crc_reference.py and
# docs/CPS_BINARY_ANALYSIS.md section 7.5.

__all__ = [
    "PacketFramer", "RadioSerialLink", "AstroFlasher",
    "DeviceAddress", "CommandResponse", "ENTER_PROGRAMMING", "TEST_MODE",
    "ATInterfaceError", "at_ping", "at_get_radio_identity", "at_get_firmware_banner",
]
