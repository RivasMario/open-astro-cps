# Homelab AI Function-by-Function Analysis: ASTRO 25 EEPROM & State Persistence

- **Model:** `qwen2.5-coder:14b` (`num_ctx=8192` on TrueNAS RTX 3080)
- **Scope:** Undocumented functions in `NextGen10.dll` and `ByteData10.dll` related to EEPROM, host markers, commit/lock, and state persistence.
- **Total functions analyzed:** 8

---

## 1. `cgIsh10c.dll` — `GetMsbStart` (`10001290`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 12.4s)*

1. **Role**: The function `GetMsbStart` retrieves the most significant byte (MSB) of a value stored at a specific offset (0x80) within the `CcgIshDataLayout` object. This likely indicates the start of a data structure or a flag related to the data layout.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly affect the permanent state on the radio. It appears to be a helper function that retrieves data, which could be used in other operations that manage EEPROM persistence, such as commit or lock/unlock operations.

3. **Key Constants / Opcodes / Calls**: 
   - Offset: 0x80
   - Return type: `uchar` (unsigned char)

4. **Next Bite**: Since this function is a simple data retrieval function, the next step would be to inspect the callers of `GetMsbStart` to understand how the retrieved MSB is used in the context of EEPROM persistence. Look for functions that involve operations like commit, lock, or unlock, which are likely to interact with the EEPROM directly.

---

## 2. `cgIsh10c.dll` — `GetPartitionLayoutMap` (`10002190`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 12.4s)*

1. **Role**: The function `GetPartitionLayoutMap` returns a pointer to a `CMap` object that represents the partition layout map of the radio. This map is used to manage and access different partitions on the radio.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly affect the permanent state on the radio. It is a transport helper function that provides access to the partition layout map, which is crucial for subsequent operations that might involve writing to or reading from specific partitions, thus affecting the radio's state.

3. **Key Constants / Opcodes / Calls**: The function returns a pointer to a `CMap` object located at an offset of `0x80` from the `this` pointer. There are no specific hex constants, opcodes, or error HRESULTs directly observed in the provided code snippet.

4. **Next Bite**: To trace EEPROM persistence, the next callees to inspect would be any functions that interact with the partitions returned by this map, such as functions that read from or write to specific partitions, or functions that handle locking and unlocking of partitions.

---

## 3. `cgIsh10c.dll` — `~CcgIshCpLayout` (`10002f40`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 19.0s)*

1. **Role**: The function `~CcgIshCpLayout` is a destructor for the `CcgIshCpLayout` class. It performs cleanup operations, releasing memory and resources associated with the object.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. It appears to be a transport helper function that manages memory and resources, possibly preparing the object for destruction without affecting the radio's permanent state.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x80`, `0x84`, `0x88`, `0x94`, `0x68`, `0x6c`, `0x78`, `0x48`, `0x28`, `0x2c`, `0x34`, `0x38`, `0x30`, `0x3c`, `0xc`, `0x10`, `0x14`, `0x20`.
   - Calls: `Cleanup`, `operator_delete`, `CPlex::FreeDataChain`, `CString::~CString`, `FUN_10005db0`.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_10005db0`, as it is called with the object pointer and might contain the logic for committing changes or interacting with the radio's persistent storage.

---

## 4. `cgIsh10c.dll` — `GetMsbStart` (`10007860`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 13.8s)*

1. **Role**: The function `GetMsbStart` retrieves a byte value from the object's memory at an offset of 0x20. This value is likely used to determine the most significant bit (MSB) start position for a field layout in the context of the radio's configuration or data structure.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly affect the permanent state on the radio. It appears to be a helper function used to retrieve configuration data that may be relevant to the persistence mechanism, but it does not perform any operations like commit, lock, unlock, or reset.

3. **Key Constants / Opcodes / Calls**: The function accesses a specific offset (0x20) within the object to return a byte value. There are no specific hex constants, opcodes, or error HRESULTs directly observed in the provided code snippet.

4. **Next Bite**: Since this function is a simple data retrieval function, the next step should be to inspect the callers of `GetMsbStart` to understand how this value is used in the context of the radio's configuration or data handling. This will provide insights into how the retrieved value might influence the EEPROM persistence mechanism.

---

## 5. `cgIsh10c.dll` — `cgIshCalculateChecksum` (`10007870`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 23.1s)*

1. **Role**: This function calculates a checksum for a given byte array, likely used for data integrity verification before writing to the radio's EEPROM or flash memory.

2. **EEPROM / Persistence Mechanism**: This function is a transport helper that calculates a checksum, which is crucial for ensuring data integrity before committing changes to the radio's EEPROM or flash memory. It indirectly supports the persistence mechanism by providing a means to verify the correctness of the data before it is written.

3. **Key Constants / Opcodes / Calls**: 
   - Hex constants: `0x1021`, `0x2042`, `0x3063`, etc., which are used in the checksum calculation table.
   - Offsets: `param_1 + 8` and `param_1 + 4` are used to access the size and data of the byte array.
   - No specific opcodes or HRESULTs are directly observed in the code snippet.

4. **Next Bite**: Since this function is primarily a checksum calculator, the next step should be to inspect the callees that use this function, particularly those that involve writing data to the radio's EEPROM or flash memory. Look for functions that call `cgIshCalculateChecksum` and then perform write operations, as these are likely responsible for making the state permanent on the radio.

---

## 6. `cgIsh10c.dll` — `cgIshCalculateDataLayoutSzInBits` (`100087a0`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 15.0s)*

1. **Role**: This function calculates the size of a data layout in bits, likely used for determining the amount of data to be written or read from the radio's memory.

2. **EEPROM / Persistence Mechanism**: The function does not directly handle EEPROM persistence. It appears to be a helper function that calculates data layout size, which is indirectly related to the process of making state permanent on the radio.

3. **Key Constants / Opcodes / Calls**:
   - `0x0c` and `0x80` are offsets used within the function.
   - `CcgIshFieldLayout::GetFieldLayout`, `CcgIshFieldLayout::GetByteOffset`, and `CcgIshFieldLayout::GetMsbStart` are methods called.
   - `cgIshCalcFloatingFldBitOffsetFromEntryStart` and `FUN_100088f0` are other functions called within the function.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `cgIshCalcFloatingFldBitOffsetFromEntryStart` and `FUN_100088f0`, as they are directly invoked within the function and may contain more detailed logic related to data layout and persistence.

---

## 7. `cgIsh10c.dll` — `cgIshCalcFloatingFldBitOffsetFromEntryStart` (`10008840`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 15.4s)*

1. **Role**: This function calculates the bit offset of a floating field from the start of an entry in a data layout. It recursively determines the offset by traversing the field layout and adjusting for byte and bit positions.

2. **EEPROM / Persistence Mechanism**: The function does not directly affect the permanent state on the radio. It appears to be a helper function used in the calculation of offsets, which is indirectly related to how data is structured and potentially written to EEPROM.

3. **Key Constants / Opcodes / Calls**:
   - `0x14` and `0x24` are offsets used to access fields in the `CcgIshFieldLayout` and `CcgIshDataLayout` structures.
   - `CcgIshDataLayout::GetPrevFieldID` and `CcgIshDataLayout::GetFieldLayout` are methods called to navigate the field layout.
   - `FUN_100088f0` is a function pointer that is called with parameters derived from the field layout.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_100088f0`, as it is called with parameters that could be related to the data layout and field positions, which are crucial for understanding how data is written to EEPROM.

---

## 8. `cgIsh10c.dll` — `FUN_1001a1a8` (`1001a1a8`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 19.1s)*

1. **Role**: This function manages a counter (`DAT_1002e29c`) and allocates or frees a memory block (`DAT_1002e2a8`) based on the input parameter (`param_2`). It also initializes or deinitializes a memory block if `param_2` is 1 or 0, respectively.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It appears to manage memory allocation and deallocation, which could be part of a larger process that affects state persistence on the radio. It does not explicitly perform commit, lock, unlock, or reset operations on EEPROM/flash.

3. **Key Constants / Opcodes / Calls**:
   - `DAT_1002e29c`: Counter variable.
   - `DAT_1002e2a8`: Pointer to allocated memory block.
   - `DAT_1002e2a4`: Pointer to the current position in the memory block.
   - `malloc(0x80)`: Allocates 128 bytes of memory.
   - `free(_Memory)`: Frees the allocated memory.
   - `initterm(&DAT_1002c000,&DAT_1002c004)`: Initializes or deinitializes a memory block.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are the functions pointed to by the memory block (`*(code *)*puVar2`). These functions might contain the actual logic for committing changes to EEPROM or handling state persistence.

---
