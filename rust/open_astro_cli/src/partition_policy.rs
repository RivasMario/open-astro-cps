// src/partition_policy.rs

use anyhow::{anyhow, Result};

pub const PART_CODEPLUG: u8 = 0x80;
pub const PART_EEPROM_LOCKED: u8 = 0x81;
pub const PART_TUNING_READONLY: u8 = 0x82;
pub const PART_FW_LOCKED: u8 = 0x85;

pub struct PartitionPolicy {
    pub allow_locked_writes: bool,
}

impl PartitionPolicy {
    pub fn new(allow_locked_writes: bool) -> Self {
        PartitionPolicy {
            allow_locked_writes,
        }
    }

    pub fn check_write(&self, partition: u8) -> Result<()> {
        match partition {
            PART_CODEPLUG => Ok(()),
            PART_EEPROM_LOCKED => {
                if self.allow_locked_writes {
                    Ok(())
                } else {
                    Err(anyhow!("Refusing write to partition 0x81 (EEPROM is locked)"))
                }
            }
            PART_TUNING_READONLY => {
                Err(anyhow!("Refusing write to partition 0x82 (RF tuning/soft-pots are ReadOnly)"))
            }
            PART_FW_LOCKED => {
                if self.allow_locked_writes {
                    Ok(())
                } else {
                    Err(anyhow!("Refusing write to partition 0x85 (FW is locked)"))
                }
            }
            _ => Err(anyhow!("Unknown partition: 0x{:02X}", partition)),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_codeplug_write_allowed() {
        let policy = PartitionPolicy::new(false);
        assert!(policy.check_write(PART_CODEPLUG).is_ok());
    }

    #[test]
    fn test_eeprom_locked_write_allowed() {
        let policy = PartitionPolicy::new(true);
        assert!(policy.check_write(PART_EEPROM_LOCKED).is_ok());
    }

    #[test]
    fn test_eeprom_locked_write_not_allowed() {
        let policy = PartitionPolicy::new(false);
        assert!(policy.check_write(PART_EEPROM_LOCKED).is_err());
    }

    #[test]
    fn test_tuning_readonly_write_always_rejected() {
        let policy = PartitionPolicy::new(true);
        assert!(policy.check_write(PART_TUNING_READONLY).is_err());
    }

    #[test]
    fn test_unknown_partition_rejected() {
        let policy = PartitionPolicy::new(true);
        assert!(policy.check_write(0x99).is_err());
    }
}
