# Homelab AI Function-by-Function Analysis: ASTRO 25 EEPROM & State Persistence

- **Model:** `qwen2.5-coder:14b` (`num_ctx=8192` on TrueNAS RTX 3080)
- **Scope:** Undocumented functions in `NextGen10.dll` and `ByteData10.dll` related to EEPROM, host markers, commit/lock, and state persistence.
- **Total functions analyzed:** 349

---

## 1. `EncatenComponent.dll` — `FUN_10001c34` (`10001c34`)
- **Keywords:** has-strings
- **Strings:** `REGISTRY, Module`

*(qwen2.5-coder:14b, 20.3s)*

1. **Role**: This function appears to handle the registration and configuration of a module, likely related to the CPS/NextGen10/ByteData10 system. It processes the module's file path, handles string manipulations, and interacts with a registry-like structure.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be more of a transport helper, preparing and registering the module with a registry-like structure. It does not explicitly commit changes to EEPROM or handle lock/unlock mechanisms directly.

3. **Key Constants / Opcodes / Calls**:
   - `0x1001b2d0`: Offset to a module handle.
   - `0x100180fc`: Constant used in `FUN_10001dac`.
   - `0x100180e8`: Constant used in `FUN_1000206b` or `FUN_10001ee9`.
   - `FUN_100098d4`, `FUN_10001d87`, `FUN_100099f0`, `FUN_10001dac`, `FUN_1000206b`, `FUN_10001ee9`, `FUN_10001e81`, `FUN_10009901`: Various function calls within the code.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000206b` and `FUN_10001ee9`, as they are conditionally called based on a flag and might handle the actual registration or persistence logic.

---

## 2. `EncatenComponent.dll` — `FUN_10002571` (`10002571`)
- **Keywords:** has-strings
- **Strings:** `TYPELIB, TYPELIB, TYPELIB, TYPELIB, CLSID, CLSID, Delete, NoRemove`

*(qwen2.5-coder:14b, 24.4s)*

1. **Role**: This function appears to handle operations related to registry-like key management, including creating, deleting, and modifying keys and values. It processes strings to determine actions such as `Delete`, `ForceRemove`, and `NoRemove`.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by managing registry-like keys and values. It does not directly interact with EEPROM or flash storage but may involve operations that trigger underlying storage commits or locks. The function calls other functions that could potentially handle these operations.

3. **Key Constants / Opcodes / Calls**:
   - **Strings**: `"Delete"`, `"ForceRemove"`, `"NoRemove"`, `"CLSID"`, `"TYPELIB"`
   - **Error HRESULTs**: `-0x7ffdfff7` (indicating an error)
   - **Callees**: `FUN_1000221f`, `FUN_10002ef0`, `FUN_10002bcd`, `FUN_10002ad5`, `FUN_10002a97`, `FUN_10002e44`, `FUN_10002e79`, `RegCreateKeyExA`, `RegCloseKey`, `RegDeleteKeyA`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000221f`, `FUN_10002ef0`, and `FUN_10002bcd`, as they are directly involved in processing the strings and could potentially handle the actual storage operations.

---

## 3. `EncatenComponent.dll` — `FUN_1000367d` (`1000367d`)
- **Keywords:** has-strings
- **Strings:** `UnRegisterTypeLib, oleaut32.dll`

*(qwen2.5-coder:14b, 17.7s)*

1. **Role**: This function appears to unregister a type library and clean up resources related to COM objects. It handles error checking and resource management, including freeing strings and releasing COM interfaces.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be a utility function for managing COM resources, which may be indirectly related to the transport layer but does not explicitly handle state persistence on the radio.

3. **Key Constants / Opcodes / Calls**:
   - `0x100181e0`: String "oleaut32.dll"
   - `0x100181cc`: String "UnRegisterTypeLib"
   - `FUN_1000347d`: Likely a function to load a type library.
   - `FUN_100098d4`: An initialization or setup function.
   - `LoadLibraryA` and `GetProcAddress`: Used to load and get the address of `UnRegisterTypeLib` from `oleaut32.dll`.
   - `FreeLibrary`: Frees the loaded DLL.
   - `SysFreeString`: Frees a BSTR string.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000347d` and the functions pointed to by the vtable entries at offsets `0x1c` and `0x30` in the `ITypeLib` object. These functions might have more direct interactions with the radio's storage or state management.

---

## 4. `EncatenComponent.dll` — `FUN_10004407` (`10004407`)
- **Keywords:** has-strings
- **Strings:** `filePackageEncrypted, filePackageComments, filePackageDestinationPath, filePackageDestinationInfo, filePackageFormatVersion, D00.01.01, D00.01.01, filePackageNumber`

*(qwen2.5-coder:14b, 34.1s)*

1. **Role**: This function appears to handle the processing and storage of various file package components, likely preparing and writing them to the radio's EEPROM or flash memory.

2. **EEPROM / Persistence Mechanism**: The function interacts with the radio's EEPROM by preparing and writing file packages. It uses several opcodes and functions to ensure data is written correctly and persistently, including handling locks, unlocking security, and possibly committing changes to the EEPROM.

3. **Key Constants / Opcodes / Calls**:
   - **Hex Constants**: `0x0100`, `0x0101`, `0x0102`, `0x0103`, `0x0106`, `0x0107`, `0x000C`, `0x000D`, `0x0012`
   - **Offsets**: `0x10`, `0x18`, `0x20`, `0x24`, `0x28`, `0x2c`, `0x30`, `0x34`, `0x38`, `0x3c`
   - **Error HRESULTs**: `0x8007000e`
   - **Callees**: `FUN_100098d4`, `FUN_10007a30`, `FUN_10008070`, `FUN_10001643`, `FUN_100076b0`, `FUN_1000489c`, `FUN_100072ae`, `FUN_100091ac`, `FUN_10009160`, `FUN_100018fa`, `FUN_10007b00`

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_10007b00` and `FUN_100018fa`, as they are directly involved in writing data to the radio and handling file packages.

---

## 5. `EncatenComponent.dll` — `FUN_100048c1` (`100048c1`)
- **Keywords:** has-strings
- **Strings:** `filePackage, fileData, fileItem`

*(qwen2.5-coder:14b, 29.6s)*

1. **Role**: This function appears to manage the initialization and finalization of some component or state within the CPS/NextGen10/ByteData10 system, possibly related to file handling or data processing.

2. **EEPROM / Persistence Mechanism**: The function involves several calls that could be related to EEPROM persistence, such as `FUN_10007bd0`, `FUN_100076b0`, and `FUN_10007730`, which might involve writing or committing data to EEPROM. It also uses `InterlockedIncrement` to manage reference counts, which could be part of a larger state management or synchronization mechanism.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x82`, `0x81`, `0x10`, `0xc`, `0x10`, `0x14`, `0x1c`, `0x8`
   - Offsets: `unaff_EBP + -0x10`, `unaff_EBP + -0x18`, `unaff_EBP + -4`, `unaff_EBP + -0x11`, `unaff_EBP + -0x1c`
   - Callees: `FUN_100098d4`, `FUN_10001643`, `FUN_10007bd0`, `FUN_100011ba`, `FUN_100076b0`, `FUN_100061cd`, `FUN_10006231`, `FUN_10006295`, `FUN_100062f9`, `FUN_1000635d`, `FUN_10006425`, `FUN_10006489`, `FUN_10004af8`, `FUN_100063c1`, `FUN_10007730`, `FUN_1000489c`, `FUN_10004a8e`

4. **Next Bite**: The callees `FUN_10007bd0`, `FUN_100076b0`, and `FUN_10007730` should be inspected next to trace EEPROM persistence, as they are directly involved in data handling and might include the actual commit or write operations to EEPROM.

---

## 6. `EncatenComponent.dll` — `FUN_10004c0a` (`10004c0a`)
- **Keywords:** has-strings
- **Strings:** `fileSourcePath`

*(qwen2.5-coder:14b, 21.5s)*

1. **Role**: This function appears to handle the initialization and cleanup of a variant structure, possibly related to file operations or data handling. It initializes a variant, copies data, and clears the variant afterward. It also checks for success and sets a flag based on the operation's outcome.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that manages data structures and possibly handles file paths, but does not explicitly commit changes to EEPROM or flash. It may be involved in preparing data for storage or transmission.

3. **Key Constants / Opcodes / Calls**:
   - `0x10004c0a`: Function address.
   - `0x100098d4`, `0x10001643`, `0x10007900`, `0x100011ba`, `0x10009160`, `0x10004d27`, `0x10008240`, `0x1000603e`: Addresses of other functions called within this function.
   - `0x0`: Null pointer checks.
   - `0x88`: Offset for stack allocation.
   - `0x10`: Offset for data pointer.
   - `0x34`, `0x44`: Offsets for variant structures.
   - `0xc`: Offset for exception list.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10007900`, `FUN_10004d27`, and `FUN_10008240`. These functions may contain the actual logic for data handling, commit operations, or interactions with the radio's storage.

---

## 7. `EncatenComponent.dll` — `FUN_10005153` (`10005153`)
- **Keywords:** has-strings
- **Strings:** `fileName`

*(qwen2.5-coder:14b, 14.7s)*

1. **Role**: The function `FUN_10005153` appears to be a high-level control function that orchestrates multiple operations, likely related to managing the state or configuration of the radio. It calls two other functions, `FUN_10001643` and `FUN_10005099`, which are responsible for specific tasks.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. Instead, it seems to be a transport helper that manages the flow of operations, possibly ensuring that changes are committed or locked appropriately before proceeding. It may indirectly influence state persistence by ensuring that operations are completed in the correct order.

3. **Key Constants / Opcodes / Calls**: The function does not contain any specific hex constants, offsets, error HRESULTs, or opcodes. It only calls two other functions, `FUN_10001643` and `FUN_10005099`.

4. **Next Bite**: To trace EEPROM persistence, the next callees to inspect are `FUN_10001643` and `FUN_10005099`. These functions are likely responsible for the actual operations that affect the radio's state, including any interactions with EEPROM or flash storage.

---

## 8. `EncatenComponent.dll` — `FUN_10005178` (`10005178`)
- **Keywords:** has-strings
- **Strings:** `fileVersion`

*(qwen2.5-coder:14b, 12.6s)*

1. **Role**: This function appears to be a high-level orchestrator that calls two other functions, `FUN_10001643` and `FUN_10005099`, likely to perform some operations related to the radio's state or configuration.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly interact with EEPROM or flash storage. It is more likely a transport helper or a higher-level function that manages the sequence of operations needed to ensure state persistence on the radio.

3. **Key Constants / Opcodes / Calls**: 
   - No specific hex constants, offsets, error HRESULTs, or opcodes are directly visible in the provided code snippet.
   - The function calls `FUN_10001643` and `FUN_10005099`.

4. **Next Bite**: To trace EEPROM persistence, the next callees to inspect are `FUN_10001643` and `FUN_10005099`. These functions are likely to contain the actual logic for interacting with the radio's storage or managing its state.

---

## 9. `EncatenComponent.dll` — `FUN_1000519d` (`1000519d`)
- **Keywords:** has-strings
- **Strings:** `fileDestinationInfo`

*(qwen2.5-coder:14b, 17.0s)*

1. **Role**: The function `FUN_1000519d` appears to be a wrapper or coordinator function that calls two other functions, `FUN_10001643` and `FUN_10005099`, without any direct manipulation of data or state within itself. It likely serves as a higher-level interface or sequence manager for operations related to the radio's state or configuration.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly manipulate EEPROM or flash storage. It is more likely a transport helper or a higher-level manager that orchestrates operations involving EEPROM persistence through its callees. The actual persistence mechanisms, such as commit, lock/unlock, or reset, are likely handled within `FUN_10001643` or `FUN_10005099`.

3. **Key Constants / Opcodes / Calls**: 
   - No specific hex constants, offsets, error HRESULTs, or opcodes are directly visible in the provided code snippet.
   - The function calls `FUN_10001643` and `FUN_10005099`, which are the primary callees to inspect for EEPROM persistence mechanisms.

4. **Next Bite**: To trace EEPROM persistence, the next callees to inspect are `FUN_10001643` and `FUN_10005099`. These functions are likely where the actual operations related to EEPROM commit, lock/unlock, or other persistence mechanisms are implemented.

---

## 10. `EncatenComponent.dll` — `FUN_100051c2` (`100051c2`)
- **Keywords:** has-strings
- **Strings:** `fileType`

*(qwen2.5-coder:14b, 12.1s)*

1. **Role**: The function `FUN_100051c2` appears to be a helper function that orchestrates a sequence of operations, likely related to file handling or processing, as indicated by the referenced string "fileType".

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that manages the flow of operations without explicitly committing changes to permanent storage. It may indirectly affect persistence through the operations it calls.

3. **Key Constants / Opcodes / Calls**: The function calls `FUN_10001643` and `FUN_10005099`. There are no specific hex constants, offsets, error HRESULTs, or opcodes directly visible in the provided code snippet.

4. **Next Bite**: To trace EEPROM persistence, inspect the callees `FUN_10001643` and `FUN_10005099` next. These functions are likely responsible for the actual operations that might involve committing changes to permanent storage.

---

## 11. `EncatenComponent.dll` — `FUN_100051e7` (`100051e7`)
- **Keywords:** has-strings
- **Strings:** `fileSize`

*(qwen2.5-coder:14b, 16.7s)*

1. **Role**: This function appears to handle string operations, possibly related to file size or path, and involves COM object interactions. It allocates and frees a BSTR, and calls other functions to perform operations like `VariantClear` and error handling.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that manages string data and COM objects, which may be part of a larger process that affects EEPROM persistence.

3. **Key Constants / Opcodes / Calls**:
   - `0x1000522f` and `0x10005244` are addresses within the function.
   - `0x8007000e` is an HRESULT error code.
   - `FUN_100098d4`, `FUN_10001643`, `FUN_10005099`, `FUN_10007004`, and `FUN_10009160` are function calls within the code.
   - `VariantClear` is a COM function used to clear a VARIANTARG structure.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10007004` and `FUN_10009160`, as they are directly involved in operations that could affect the state or error handling of the process.

---

## 12. `EncatenComponent.dll` — `FUN_10005296` (`10005296`)
- **Keywords:** has-strings
- **Strings:** `fileDateTime`

*(qwen2.5-coder:14b, 15.6s)*

1. **Role**: The function `FUN_10005296` appears to be a helper function that orchestrates a series of operations, likely related to managing the state or configuration of the radio. It calls two other functions, `FUN_10001643` and `FUN_10005099`, which are responsible for specific tasks.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to be a transport helper that ensures the state is properly managed and synchronized between the host and the radio. It may involve locking, unlocking, or preparing for state changes, but the direct impact on EEPROM persistence is indirect.

3. **Key Constants / Opcodes / Calls**: The function does not contain any specific hex constants, offsets, error HRESULTs, or opcodes. It only calls two other functions, `FUN_10001643` and `FUN_10005099`, without any immediate parameters or constants visible in the decompiled code snippet.

4. **Next Bite**: To trace EEPROM persistence, the next callees to inspect are `FUN_10001643` and `FUN_10005099`. These functions are likely responsible for the actual operations related to state management and may contain the necessary logic for committing changes to EEPROM or handling locks/unlocks.

---

## 13. `EncatenComponent.dll` — `FUN_100052bb` (`100052bb`)
- **Keywords:** has-strings
- **Strings:** `fileSourcePath`

*(qwen2.5-coder:14b, 17.1s)*

1. **Role**: The function `FUN_100052bb` appears to be a wrapper or coordinator function that calls two other functions, `FUN_10001643` and `FUN_10005099`, without any direct operations on the stack or local variables. It likely orchestrates a sequence of operations related to file handling or processing.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly interact with the EEPROM or flash storage to make state permanent. It is more likely a transport helper or a higher-level function that manages the flow of operations, possibly involving the use of known opcodes like `0x0106` (EnterMode/Session) or `0x000C` (OP_UNLOCK) through the underlying transport mechanism.

3. **Key Constants / Opcodes / Calls**: 
   - No specific hex constants, offsets, error HRESULTs, or opcodes are directly observed in the provided code snippet.
   - The function calls `FUN_10001643` and `FUN_10005099`, which are the primary callees to inspect for further details.

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_10001643` and `FUN_10005099`. These functions are likely responsible for the actual operations that might involve EEPROM or flash storage, such as committing changes, locking/unlocking, or handling file operations that affect the radio's permanent state.

---

## 14. `EncatenComponent.dll` — `FUN_100052e0` (`100052e0`)
- **Keywords:** has-strings
- **Strings:** `fileComments`

*(qwen2.5-coder:14b, 15.5s)*

1. **Role**: The function `FUN_100052e0` appears to be a high-level control function that orchestrates multiple operations, likely related to configuration or state management of the radio. It calls two other functions, `FUN_10001643` and `FUN_10005099`, which are responsible for specific tasks.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper or a wrapper function that manages the sequence of operations needed to ensure state persistence on the radio. It might involve setting up or tearing down locks, preparing for state changes, or ensuring that all necessary operations are completed before proceeding.

3. **Key Constants / Opcodes / Calls**: The function does not contain any specific hex constants, opcodes, or direct calls to EEPROM-related functions. It calls two other functions, `FUN_10001643` and `FUN_10005099`, which may contain the actual logic for EEPROM operations.

4. **Next Bite**: To trace EEPROM persistence, the next callees to inspect are `FUN_10001643` and `FUN_10005099`. These functions are likely to contain the detailed logic for handling EEPROM operations, including commit, lock/unlock, or other state persistence mechanisms.

---

## 15. `EncatenComponent.dll` — `FUN_100058fa` (`100058fa`)
- **Keywords:** has-strings
- **Strings:** `fileItem`

*(qwen2.5-coder:14b, 20.2s)*

1. **Role**: This function appears to handle file operations, possibly related to reading or writing configuration files. It checks for file existence, processes the file content, and manages exceptions.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that manages file operations and exceptions, which could be part of a larger process that eventually affects EEPROM persistence.

3. **Key Constants / Opcodes / Calls**:
   - `0xfff85ede`: An HRESULT value indicating an error.
   - `FUN_100098d4`, `FUN_100078c0`, `FUN_10007a00`, `FUN_10001643`, `FUN_10001132`, `FUN_100059b1`, `FUN_100011ba`, `__CxxThrowException_8`: These are the function calls within the decompiled code.
   - `unaff_EBP + -0xd`, `unaff_EBP + -0x14`, `unaff_EBP + -4`, `unaff_EBP + -0xe`, `unaff_EBP + -0x18`, `unaff_EBP + -0x1c`, `unaff_EBP + -0xc`: These are offsets used for local variables or function parameters.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_100078c0`, `FUN_10007a00`, and `FUN_100059b1`, as they are directly involved in processing the file content and could potentially interact with the radio's storage mechanisms.

---

## 16. `EncatenComponent.dll` — `FUN_10005ed6` (`10005ed6`)
- **Keywords:** has-strings
- **Strings:** `fileData`

*(qwen2.5-coder:14b, 22.7s)*

1. **Role**: This function appears to handle some form of data processing or state management, possibly involving file data and operations related to unlocking or locking security mechanisms. It checks conditions, calls other functions, and manages states indicated by specific values.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by calling functions that likely handle EEPROM operations, such as unlocking security mechanisms (`FUN_10007c90`), committing changes (`FUN_10007e00`), and possibly writing to EEPROM. It also manages states that could be related to EEPROM persistence, such as setting flags (`*(undefined1 *)(unaff_EBP + -0x11) = 1;`).

3. **Key Constants / Opcodes / Calls**:
   - `FUN_100058fa()`: Likely checks a condition related to file data.
   - `FUN_10001643()`: Sets a state flag (`*(undefined1 *)(unaff_EBP + -4)`).
   - `FUN_10005b57()`: Another function that might be related to processing or committing data.
   - `FUN_100011ba()`: Calls with pointers, possibly related to resource management or cleanup.
   - `FUN_10007c90(this, uVar2)`: Likely involves unlocking or validating security mechanisms.
   - `FUN_100079d0(this, *(undefined4 *)(unaff_EBP + 8))`: Possibly writes or processes data.
   - `FUN_10007e00(this)`: Likely commits changes or finalizes operations.

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_10007c90`, `FUN_100079d0`, and `FUN_10007e00`, as they are directly involved in operations that could affect the EEPROM or permanent state on the radio.

---

## 17. `EncatenComponent.dll` — `FUN_1000603e` (`1000603e`)
- **Keywords:** has-strings
- **Strings:** `fileData, fileSize, fileDateTime`

*(qwen2.5-coder:14b, 22.6s)*

1. **Role**: This function appears to handle file operations, possibly related to configuration or data management on a device, likely involving reading, writing, and processing file data.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by managing file data and potentially invoking operations that could involve EEPROM or flash storage. It does not directly call known opcodes for EEPROM commit or lock/unlock but may involve COM method calls that handle these operations.

3. **Key Constants / Opcodes / Calls**:
   - `0x0100` (ReadIsh), `0x0101` (WriteIsh), `0x0102` (Prepare Write), `0x0103` (DelIshTypes), `0x0106` (EnterMode/Session), `0x0107` (UnlockSecurity LFSR 0x51E88D21), `0x000C` (OP_UNLOCK), `0x000D` (OP_LOCK with 16-byte UUID), `0x0012` (GetRadioUUID).
   - COM method calls: `FUN_10007c90`, `FUN_10007d30`, `FUN_10007e00`, `FUN_100057c3`, `FUN_10007b00`, `FUN_100011ba`, `FUN_10009160`, `FUN_10006f94`.
   - HRESULT: `VariantClear` error handling.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10007b00` and `FUN_10006f94`, as they are directly involved in processing file data and may contain calls to underlying storage operations.

---

## 18. `EncatenComponent.dll` — `FUN_100061cd` (`100061cd`)
- **Keywords:** has-strings
- **Strings:** `fileName`

*(qwen2.5-coder:14b, 14.9s)*

1. **Role**: This function appears to manage a process involving file operations and state management, possibly related to configuration or data handling on the radio.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by managing memory buffers and potentially invoking operations that could lead to EEPROM/flash commit. It sets up and tears down buffers, which could be crucial for ensuring data integrity and persistence.

3. **Key Constants / Opcodes / Calls**:
   - `0x1000621f`: A memory address used in an error handling context.
   - `FUN_100098d4`, `FUN_100018fa`, `FUN_10001643`, `FUN_10005fa3`, `FUN_100011ba`: These are the function calls within the function, which may include operations related to memory management, error handling, or state transitions.

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_100018fa`, `FUN_10001643`, and `FUN_10005fa3`, as they are directly involved in setting up and managing the state and buffers that could lead to EEPROM/flash operations.

---

## 19. `EncatenComponent.dll` — `FUN_10006231` (`10006231`)
- **Keywords:** has-strings
- **Strings:** `fileVersion`

*(qwen2.5-coder:14b, 15.2s)*

1. **Role**: This function appears to manage some form of initialization or setup process, possibly related to file versioning or configuration, as indicated by the referenced string "fileVersion". It involves multiple function calls and manipulates local stack variables.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be more of a transport helper or configuration management function, possibly setting up state or markers that could influence subsequent operations affecting EEPROM persistence.

3. **Key Constants / Opcodes / Calls**:
   - `0x10006283`: A memory address used in a conditional call.
   - `FUN_100098d4`, `FUN_100018fa`, `FUN_10001643`, `FUN_10005fa3`, `FUN_100011ba`: Specific function calls within the function.
   - `unaff_EBP`: A stack pointer reference used for local variable manipulation.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_100018fa`, `FUN_10001643`, and `FUN_10005fa3`, as they are directly involved in the setup process and could potentially interact with EEPROM or other storage mechanisms.

---

## 20. `EncatenComponent.dll` — `FUN_10006295` (`10006295`)
- **Keywords:** has-strings
- **Strings:** `fileDestinationInfo`

*(qwen2.5-coder:14b, 14.1s)*

1. **Role**: This function appears to manage a process involving file operations and state transitions, possibly related to configuration or data handling on the radio.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by managing file operations and state transitions. It likely involves setting up and tearing down operations, possibly including locking and unlocking mechanisms to ensure data integrity during these operations.

3. **Key Constants / Opcodes / Calls**:
   - `0x100062e7`: A specific address used in error handling.
   - `FUN_100098d4`, `FUN_100018fa`, `FUN_10001643`, `FUN_10005fa3`, `FUN_100011ba`: These are the function calls within the code snippet.
   - `auStack_20` and `auStackY_a4`: These are stack-based arrays used in the function.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_10005fa3`, as it is directly involved in the state transition logic and may contain calls to functions responsible for committing changes to EEPROM or handling locks/unlocks.

---

## 21. `EncatenComponent.dll` — `FUN_100062f9` (`100062f9`)
- **Keywords:** has-strings
- **Strings:** `fileType`

*(qwen2.5-coder:14b, 15.2s)*

1. **Role**: This function appears to manage some form of state or data processing, possibly related to file handling or configuration, as indicated by the "fileType" string reference. It initializes and manipulates buffers, calls other functions, and checks for non-null pointers before performing cleanup.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be more of a transport helper or data processing function, possibly preparing data for transmission or storage. It does not explicitly commit changes to EEPROM or handle lock/unlock mechanisms directly.

3. **Key Constants / Opcodes / Calls**:
   - **Strings**: "fileType"
   - **Function Calls**: `FUN_100098d4`, `FUN_100018fa`, `FUN_10001643`, `FUN_10005fa3`, `FUN_100011ba`
   - **Stack Manipulation**: Uses stack-based buffers (`auStackY_a4`, `auStack_20`)

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_100018fa`, `FUN_10001643`, and `FUN_10005fa3`. These functions might contain more direct interactions with storage or state management.

---

## 22. `EncatenComponent.dll` — `FUN_1000635d` (`1000635d`)
- **Keywords:** has-strings
- **Strings:** `fileSourcePath`

*(qwen2.5-coder:14b, 14.0s)*

1. **Role**: This function appears to manage a process involving file operations and state transitions, possibly related to configuration or data handling on the radio.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by managing memory buffers and possibly invoking other functions that handle EEPROM operations. It does not directly perform EEPROM commit or reset operations but may be involved in preparing or finalizing data that will be written to EEPROM.

3. **Key Constants / Opcodes / Calls**:
   - `0x100063af`: A memory address used in an error handling context.
   - `FUN_100098d4`, `FUN_100018fa`, `FUN_10001643`, `FUN_10005fa3`, `FUN_100011ba`: These are the function calls within the code snippet.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_100018fa`, `FUN_10001643`, and `FUN_10005fa3`, as they are directly involved in the process and may contain the logic for handling EEPROM operations.

---

## 23. `EncatenComponent.dll` — `FUN_100063c1` (`100063c1`)
- **Keywords:** has-strings
- **Strings:** `fileComments`

*(qwen2.5-coder:14b, 14.4s)*

1. **Role**: This function appears to manage some form of state or configuration on the radio, possibly related to file comments or metadata, by interacting with various internal functions and handling exceptions.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. It seems to be more of a transport helper or state management function that may indirectly affect persistence through its interactions with other components.

3. **Key Constants / Opcodes / Calls**:
   - `0x10006413`: A potential error HRESULT or code.
   - `FUN_100098d4`, `FUN_100018fa`, `FUN_10001643`, `FUN_10005fa3`, `FUN_100011ba`: Internal function calls that may handle specific operations.
   - `auStack_20`, `auStackY_a4`: Stack-based buffers used for data storage or processing.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_100018fa`, `FUN_10001643`, and `FUN_10005fa3`, as they are directly involved in processing and potentially committing changes.

---

## 24. `EncatenComponent.dll` — `FUN_10006425` (`10006425`)
- **Keywords:** has-strings
- **Strings:** `fileDateTime`

*(qwen2.5-coder:14b, 16.8s)*

1. **Role**: This function appears to manage some form of state or configuration on the radio, possibly involving file operations or data handling. It initializes and manipulates buffers, calls other functions, and checks for errors.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. It seems to be more of a transport helper, managing data buffers and possibly preparing data for transmission or storage. It does not explicitly commit changes to EEPROM or flash; however, it may be involved in the process of preparing data for such operations.

3. **Key Constants / Opcodes / Calls**:
   - `0x10006477`: A specific address used in an error handling context.
   - `FUN_100098d4`, `FUN_100018fa`, `FUN_10001643`, `FUN_10005fa3`, `FUN_100011ba`: These are the function calls made within the function.
   - `auStack_20` and `auStackY_a4`: Buffers used in the function.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_100018fa`, `FUN_10001643`, and `FUN_10005fa3`. These functions may contain more detailed operations related to data handling, buffer management, or state preparation, which could be indirectly related to EEPROM persistence.

---

## 25. `EncatenComponent.dll` — `FUN_10006489` (`10006489`)
- **Keywords:** has-strings
- **Strings:** `fileSize`

*(qwen2.5-coder:14b, 16.9s)*

1. **Role**: This function appears to manage some form of data processing or state handling, possibly related to file operations or data storage, as indicated by the presence of the string "fileSize" and the use of buffers (`auStackY_a4` and `auStack_20`).

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be more of a transport helper or data processing function that may indirectly contribute to state persistence by preparing or managing data that could be written to EEPROM later. It does not explicitly perform commit, lock, unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**: 
   - `0x100064db`: A memory address used in an error handling context.
   - `FUN_100098d4`, `FUN_100018fa`, `FUN_10001643`, `FUN_10005fa3`, `FUN_100011ba`: These are the function calls within the function, which may be related to data processing, error handling, or other operations.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_100018fa`, `FUN_10001643`, and `FUN_10005fa3`, as they are directly involved in the data processing flow and may contain the logic for handling EEPROM operations or state persistence.

---

## 26. `EncatenComponent.dll` — `FUN_10006503` (`10006503`)
- **Keywords:** has-strings
- **Strings:** `filePackageDestinationInfo`

*(qwen2.5-coder:14b, 14.8s)*

1. **Role**: The function `FUN_10006503` appears to be a wrapper or coordinator that calls two other functions, `FUN_10001643` and `FUN_1000581f`, without any direct operations on the stack or local variables. It likely orchestrates a sequence of operations related to file handling or data processing.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly interact with the EEPROM or flash storage. It is more likely a transport helper or a higher-level function that manages the flow of operations, possibly involving the use of undocumented opcodes or mechanisms to ensure state persistence on the radio.

3. **Key Constants / Opcodes / Calls**: 
   - No specific hex constants, offsets, error HRESULTs, or opcodes are directly visible in the provided code snippet.
   - The function calls `FUN_10001643` and `FUN_1000581f`, which are the primary callees.

4. **Next Bite**: To trace EEPROM persistence, the next callees to inspect are `FUN_10001643` and `FUN_1000581f`. These functions are likely to contain the actual operations related to file handling or data processing that might involve EEPROM or flash storage operations.

---

## 27. `EncatenComponent.dll` — `FUN_10006528` (`10006528`)
- **Keywords:** has-strings
- **Strings:** `filePackageDestinationPath`

*(qwen2.5-coder:14b, 14.6s)*

1. **Role**: The function `FUN_10006528` appears to be a high-level control function that orchestrates multiple operations, likely related to system initialization or configuration. It calls two other functions, `FUN_10001643` and `FUN_1000581f`, which are responsible for specific tasks.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly manipulate EEPROM or flash storage. Instead, it acts as a transport helper by calling other functions that may handle EEPROM persistence. The actual mechanics of making state permanent on the radio are likely handled within the called functions.

3. **Key Constants / Opcodes / Calls**: 
   - No specific hex constants, offsets, error HRESULTs, or opcodes are directly visible in the provided code snippet.
   - The function calls `FUN_10001643` and `FUN_1000581f`, which are the primary callees.

4. **Next Bite**: To trace EEPROM persistence, the next callees to inspect are `FUN_10001643` and `FUN_1000581f`. These functions are likely responsible for the actual operations related to EEPROM persistence, such as committing changes, locking/unlocking, or flushing data.

---

## 28. `EncatenComponent.dll` — `FUN_1000654d` (`1000654d`)
- **Keywords:** has-strings
- **Strings:** `filePackageName`

*(qwen2.5-coder:14b, 14.0s)*

1. **Role**: The function `FUN_1000654d` appears to be a high-level orchestrator that calls two other functions, `FUN_10001643` and `FUN_1000581f`, which likely perform specific operations related to the radio's state or configuration.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly handle EEPROM persistence. It is more likely a transport helper or a higher-level function that manages the sequence of operations needed to ensure state persistence on the radio. The actual persistence mechanisms, such as committing changes to EEPROM or handling locks, are likely handled by the called functions.

3. **Key Constants / Opcodes / Calls**: The function does not contain any specific hex constants, opcodes, or error HRESULTs. It only calls two other functions, `FUN_10001643` and `FUN_1000581f`, without any additional parameters or constants.

4. **Next Bite**: To trace EEPROM persistence, the next callees to inspect are `FUN_10001643` and `FUN_1000581f`. These functions are likely responsible for the actual operations related to state persistence on the radio.

---

## 29. `EncatenComponent.dll` — `FUN_10006572` (`10006572`)
- **Keywords:** has-strings
- **Strings:** `filePackageNumber`

*(qwen2.5-coder:14b, 14.5s)*

1. **Role**: The function `FUN_10006572` appears to be a high-level control function that orchestrates multiple operations, likely related to managing the state of the radio. It calls two other functions, `FUN_10001643` and `FUN_1000581f`, which are responsible for specific tasks.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to be a transport helper that manages the flow of operations, possibly ensuring that changes are committed and secured before proceeding. It may involve locking and unlocking mechanisms to ensure data integrity.

3. **Key Constants / Opcodes / Calls**: The function does not contain any specific hex constants, opcodes, or direct calls to EEPROM manipulation functions. It calls two other functions, `FUN_10001643` and `FUN_1000581f`, which might contain the actual EEPROM persistence logic.

4. **Next Bite**: To trace EEPROM persistence, the next callees to inspect are `FUN_10001643` and `FUN_1000581f`. These functions are likely to contain the detailed logic for committing changes to EEPROM, handling locks, and ensuring state persistence.

---

## 30. `EncatenComponent.dll` — `FUN_10006597` (`10006597`)
- **Keywords:** has-strings
- **Strings:** `filePackageComments`

*(qwen2.5-coder:14b, 13.0s)*

1. **Role**: This function appears to be a wrapper or coordinator that calls two other functions, `FUN_10001643` and `FUN_1000581f`, without any direct operations on the stack or local variables. Its primary role is to sequence these two function calls.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly interact with EEPROM or manage state persistence. It is likely a transport helper or a higher-level function that orchestrates operations related to state persistence by calling other functions.

3. **Key Constants / Opcodes / Calls**: 
   - No specific hex constants, offsets, error HRESULTs, or opcodes are directly observable in the provided code snippet.
   - The function calls `FUN_10001643` and `FUN_1000581f`.

4. **Next Bite**: To trace EEPROM persistence, the next callees to inspect are `FUN_10001643` and `FUN_1000581f`. These functions are likely responsible for the actual operations related to state persistence, such as committing changes to EEPROM or managing locks.

---

## 31. `EncatenComponent.dll` — `FUN_10006674` (`10006674`)
- **Keywords:** has-strings
- **Strings:** `filePackageDestinationInfo`

*(qwen2.5-coder:14b, 12.5s)*

1. **Role**: This function appears to allocate memory for a string, perform some operations, and handle exceptions. It seems to be part of a larger process involving string manipulation and possibly error handling.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more of a utility function for string handling and error management.

3. **Key Constants / Opcodes / Calls**:
   - `0x8007000e`: HRESULT for memory allocation failure.
   - `FUN_100098d4`, `FUN_10009160`, `FUN_10001643`, `FUN_100065bc`: These are the function calls within the function, which may involve string operations or error handling.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10001643` and `FUN_100065bc`, as they are the primary operations performed after string allocation and before exception handling.

---

## 32. `EncatenComponent.dll` — `FUN_100066de` (`100066de`)
- **Keywords:** has-strings
- **Strings:** `filePackageDestinationPath`

*(qwen2.5-coder:14b, 14.5s)*

1. **Role**: This function appears to allocate a string, perform some operations, and handle exceptions. It seems to be part of a larger process involving string manipulation and possibly error handling.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more of a utility function for string handling and error management.

3. **Key Constants / Opcodes / Calls**:
   - `0x8007000e`: HRESULT error code indicating an invalid argument.
   - `FUN_100098d4`, `FUN_10009160`, `FUN_10001643`, `FUN_100065bc`: These are the function calls within the function.
   - `SysAllocString`: Allocates a BSTR (Basic String) from a Unicode string.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_100098d4`, `FUN_10009160`, `FUN_10001643`, and `FUN_100065bc`. These functions might contain the actual logic for interacting with the radio's storage or managing its state.

---

## 33. `EncatenComponent.dll` — `FUN_10006748` (`10006748`)
- **Keywords:** has-strings
- **Strings:** `filePackageName`

*(qwen2.5-coder:14b, 13.5s)*

1. **Role**: This function appears to allocate memory for a string, perform some operations, and handle exceptions. It likely involves string manipulation and possibly error handling related to memory allocation.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more related to memory management and string handling, which could be part of a larger process involving EEPROM persistence.

3. **Key Constants / Opcodes / Calls**:
   - `0x8007000e`: HRESULT error code for insufficient memory.
   - `FUN_100098d4`, `FUN_10009160`, `FUN_10001643`, `FUN_100065bc`: Specific function calls within the code.
   - `SysAllocString`: COM function for allocating a BSTR (Basic String).

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10001643` and `FUN_100065bc`. These functions might contain the actual logic for interacting with the radio's storage or handling the state persistence mechanism.

---

## 34. `EncatenComponent.dll` — `FUN_100067b2` (`100067b2`)
- **Keywords:** has-strings
- **Strings:** `filePackageNumber`

*(qwen2.5-coder:14b, 12.6s)*

1. **Role**: This function appears to allocate a string, perform some operations, and handle exceptions. It seems to be part of a larger process involving string manipulation and possibly error handling.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that manages string data and possibly handles errors. It does not explicitly commit changes to EEPROM or manage locks/unlocks.

3. **Key Constants / Opcodes / Calls**:
   - `0x8007000e`: HRESULT error code indicating an out-of-memory condition.
   - `FUN_100098d4`, `FUN_10009160`, `FUN_10001643`, `FUN_100065bc`: These are the function calls within the code snippet.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10001643` and `FUN_100065bc`. These functions might contain the actual logic for handling EEPROM operations or state persistence.

---

## 35. `EncatenComponent.dll` — `FUN_1000681c` (`1000681c`)
- **Keywords:** has-strings
- **Strings:** `filePackageComments`

*(qwen2.5-coder:14b, 13.1s)*

1. **Role**: This function appears to allocate a string, perform some operations, and handle exceptions. It likely involves memory management and possibly string manipulation within the context of a larger system.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that manages memory and possibly handles exceptions, but does not explicitly commit changes to permanent storage.

3. **Key Constants / Opcodes / Calls**:
   - `0x8007000e`: HRESULT error code indicating an out-of-memory condition.
   - `FUN_100098d4`, `FUN_10009160`, `FUN_10001643`, `FUN_100065bc`: These are function calls within the code, possibly related to memory management, error handling, or other operations.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10001643` and `FUN_100065bc`, as they are directly invoked and might contain operations related to memory management or storage operations.

---

## 36. `EncatenComponent.dll` — `FUN_10006886` (`10006886`)
- **Keywords:** has-strings
- **Strings:** `filePackage`

*(qwen2.5-coder:14b, 15.9s)*

1. **Role**: This function appears to manage the state of a component, possibly related to file operations or package handling, and it interacts with other functions to perform various operations like setting flags, handling exceptions, and checking conditions.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. It seems to be more of a transport helper or state management function that might indirectly affect persistence through its interactions with other components or functions.

3. **Key Constants / Opcodes / Calls**:
   - `0x10006886`: Function address.
   - `0x100098d4`, `0x10001643`, `0x10005b57`, `0x100011ba`, `0x10007bd0`: Addresses of other functions called within this function.
   - `0x84`: Offset used in stack allocation.
   - `0x10`: Offset added to `extraout_ECX` in the call to `FUN_10007bd0`.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10005b57` and `FUN_10007bd0`, as they are directly involved in the operations that might affect the state or persistence of the component.

---

## 37. `EncatenComponent.dll` — `FUN_10006aa7` (`10006aa7`)
- **Keywords:** has-strings
- **Strings:** `filePackage, fileItem, fileName, fileVersion, fileDestinationInfo,  and @,  and @`

*(qwen2.5-coder:14b, 23.9s)*

1. **Role**: This function appears to manage the state and persistence of data on a radio device, likely handling operations such as committing changes, locking/unlocking, and ensuring data integrity.

2. **EEPROM / Persistence Mechanism**: The function involves multiple calls to `FUN_10005bac`, `FUN_1000489c`, and `FUN_10001643`, which suggest operations related to data validation, state management, and possibly committing changes to EEPROM or flash. It also sets various states (1-16) that could indicate different stages of the persistence process.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x100`, `0x101`, `0x102`, `0x103`, `0x106`, `0x107`, `0x0C`, `0x0D`, `0x12`
   - Offsets: `-0x18`, `-4`, `-0x14`
   - Error HRESULTs: None explicitly shown, but state transitions (1-16) could indicate error handling.
   - Callees: `FUN_100098d4`, `FUN_10001643`, `FUN_10005bac`, `FUN_10005b57`, `FUN_1000489c`, `FUN_10006e74`, `FUN_10001624`

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_10005bac`, `FUN_1000489c`, and `FUN_10001643`, as they are repeatedly called throughout the function and likely handle core operations related to data validation, state management, and committing changes.

---

## 38. `EncatenComponent.dll` — `FUN_10006f94` (`10006f94`)
- **Keywords:** has-strings
- **Strings:** `%m/%d/%y %I:%M:%S %p`

*(qwen2.5-coder:14b, 13.7s)*

1. **Role**: This function appears to format a timestamp string and return it as a BSTR. It likely serves as a helper function for generating formatted date and time strings.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistent storage mechanisms. It seems to be a utility function for string formatting.

3. **Key Constants / Opcodes / Calls**:
   - String format: `"%m/%d/%y %I:%M:%S %p"`
   - HRESULT: `0x8007000e` (ERROR_OUTOFMEMORY)
   - Callees: `FUN_1000ad44`, `FUN_1000abe4`, `FUN_1000a332`, `FUN_100091ac`, `FUN_10009160`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000ad44`, `FUN_1000abe4`, and `FUN_1000a332`, as they are involved in the process of generating and formatting the timestamp string.

---

## 39. `EncatenComponent.dll` — `FUN_1000717e` (`1000717e`)
- **Keywords:** has-strings
- **Strings:** `Motorola, 352FEFDA-4965-11D5-A218-0060B0FC83F1, Licenses`

*(qwen2.5-coder:14b, 18.9s)*

1. **Role**: This function retrieves the computer name, processes it with a function related to "Motorola," and checks for a specific registry key and value. It then calls another function (`FUN_1000af14`) with the processed computer name and the registry value.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. It appears to be a transport helper function that checks for licensing information in the registry and processes it, which could be part of a larger mechanism for ensuring the software is properly licensed before making changes to the radio's state.

3. **Key Constants / Opcodes / Calls**:
   - Strings: "Motorola", "352FEFDA-4965-11D5-A218-0060B0FC83F1", "Licenses"
   - Registry keys: `HKEY_LOCAL_MACHINE\SOFTWARE\Licenses\{352FEFDA-4965-11D5-A218-0060B0FC83F1}`
   - Registry value size: 0x1f (31 bytes)
   - Function calls: `GetComputerNameA`, `FUN_10007238`, `RegOpenKeyA`, `RegQueryValueA`, `RegCloseKey`, `FUN_1000af14`

4. **Next Bite**: The next function to inspect for tracing EEPROM persistence is `FUN_1000af14`, as it is called with the processed computer name and the registry value, and it likely contains the logic for interacting with the radio's EEPROM or flash memory.

---

## 40. `EncatenComponent.dll` — `FUN_100072ae` (`100072ae`)
- **Keywords:** has-strings
- **Strings:** `Copyright (c) %s Motorola, Inc. All rights reserved.`

*(qwen2.5-coder:14b, 15.3s)*

1. **Role**: This function appears to handle some form of initialization or setup, possibly related to copyright information or versioning, as indicated by the referenced string "Copyright (c) %s Motorola, Inc. All rights reserved."

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more of a utility function that prepares data for transport or display.

3. **Key Constants / Opcodes / Calls**:
   - String: "Copyright (c) %s Motorola, Inc. All rights reserved."
   - Calls: `FUN_1000ad44`, `FUN_1000abe4`, `FUN_1000a332`, `FUN_1000b0a9`
   - Data: `DAT_100184e0`, `DAT_1001b380`, `s_Copyright__c___s_Motorola__Inc__A_100184a8`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000ad44`, `FUN_1000abe4`, and `FUN_1000a332`, as they are directly involved in processing and preparing data, which could potentially interact with EEPROM or flash storage.

---

## 41. `EncatenComponent.dll` — `FUN_1000a915` (`1000a915`)
- **Keywords:** has-strings
- **Strings:** `am/pm`

*(qwen2.5-coder:14b, 17.1s)*

1. **Role**: This function appears to process and interpret a sequence of bytes, possibly related to configuration or data manipulation for a radio device. It handles different byte values and performs actions based on these values, including setting specific markers and possibly writing to a buffer.

2. **EEPROM / Persistence Mechanism**: The function does not directly commit data to EEPROM or flash. Instead, it seems to prepare data for writing by setting markers and possibly copying data to a buffer. The actual persistence mechanism (committing to EEPROM/flash) is likely handled elsewhere in the code, possibly by another function that this one calls.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x27`, `0x41`, `0x48`, `0x4d`, `0x61`, `0x68`, `0x6d`, `0x73`, `0x74`, `0x79`
   - Strings: `"am/pm"`
   - Callees: `FUN_1000dc30`, `FUN_1000a447`

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_1000a447`, as it is called with parameters that suggest it might handle the actual writing or committing of data to the radio's storage.

---

## 42. `EncatenComponent.dll` — `entry` (`1000b1d4`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 17.5s)*

1. **Role**: The `entry` function appears to be a central handler within the `EncatenComponent.dll` that manages different operations based on the `param_2` value. It likely acts as a dispatcher for various operations, possibly including initialization, processing, and finalization tasks.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to manage the flow of operations that might involve these storage mechanisms. It calls other functions (`FUN_1000b0fb`, `FUN_10002f40`) which could potentially handle the actual persistence operations. The function also checks and calls a function pointer stored at `DAT_1001cc2c` if it is not null, which might be responsible for EEPROM operations.

3. **Key Constants / Opcodes / Calls**:
   - `param_2` values: 0, 1, 2, 3
   - Function pointers: `DAT_1001cc2c`
   - Called functions: `FUN_1000b0fb`, `FUN_10002f40`
   - Potential opcode or state handling: `DAT_1001b4b0`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000b0fb` and `FUN_10002f40`. These functions are directly invoked based on the `param_2` value and might contain the logic for handling EEPROM operations or state persistence.

---

## 43. `EncatenComponent.dll` — `FUN_1000be85` (`1000be85`)
- **Keywords:** has-strings
- **Strings:** `__GLOBAL_HEAP_SELECTED, __MSVCRT_HEAP_SELECT`

*(qwen2.5-coder:14b, 14.6s)*

1. **Role**: This function checks the Windows version and environment variables related to heap selection. It then processes the environment variable `__MSVCRT_HEAP_SELECT` to extract and manipulate specific strings. If certain conditions are met, it calls another function (`FUN_1000fcf2`) with the processed string.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. It appears to be a transport helper function that processes environment variables and calls other functions based on the environment settings. It does not explicitly handle EEPROM commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**:
   - Windows version check: `GetVersionExA`
   - Environment variable retrieval: `GetEnvironmentVariableA`
   - String manipulation: `_strncmp`, `_strstr`, `_strchr`
   - Function call: `FUN_1000fcf2`
   - Error handling: `FUN_1000be58`

4. **Next Bite**: The next function to inspect for EEPROM persistence is `FUN_1000fcf2`, as it is called with the processed string and may contain the actual logic for interacting with the radio's EEPROM or flash memory.

---

## 44. `EncatenComponent.dll` — `FUN_1000e833` (`1000e833`)
- **Keywords:** has-strings
- **Strings:** `null), null), null)`

*(qwen2.5-coder:14b, 36.1s)*

1. **Role**: This function appears to parse and process a command string, likely related to configuration or data manipulation on a radio device. It handles various cases based on the input characters and possibly interacts with other functions to perform specific operations.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to prepare data or settings that may be written to EEPROM later. It involves calls to functions that could handle locking, unlocking, or committing changes, but the direct persistence mechanism is not explicitly shown in the provided code snippet.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x20`, `0x23`, `0x2a`, `0x2b`, `0x2d`, `0x30`, `0x49`, `0x68`, `0x6c`, `0x77`, `0x67`, `0x58`, `0x43`, `0x45`, `0x47`, `0x53`, `0x5a`, `0x69`, `0x80`, `0x800`, `0x8000`, `0x830`, `0x810`, `0x40000000`, `0x80000000`.
   - Offsets: `DAT_10014a28`, `DAT_10014a48`, `PTR_DAT_1001a750`, `PTR_DAT_1001ac18`.
   - Error HRESULTs: Not explicitly shown, but typical HRESULTs like `0x80070057` (E_INVALIDARG) could be returned.
   - Callees: `FUN_1000ef74`, `FUN_1000f012`, `FUN_1000f02f`, `FUN_100109cb`, `FUN_1000f01f`.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000ef74`, `FUN_1000f012`, `FUN_1000f02f`, and `FUN_100109cb`. These functions are likely responsible for handling specific operations that could involve committing changes to EEPROM or managing locks.

---

## 45. `EncatenComponent.dll` — `FUN_1000f6be` (`1000f6be`)
- **Keywords:** has-strings
- **Strings:** `R6009
- not enough space for environment
, R6009
- not enough space for environment
, R6009
- not enough space for environment
, Microsoft Visual C++ Runtime Library, Runtime Error!

Program: , <program name unknown>`

*(qwen2.5-coder:14b, 18.6s)*

1. **Role**: This function appears to handle error reporting and logging, specifically for runtime errors related to insufficient space for the environment or other critical issues. It writes error messages to the standard error handle and, in some cases, displays a runtime error dialog.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with the radio's EEPROM or flash memory. Instead, it focuses on error handling and reporting, which may indirectly affect the system's state by ensuring that critical errors are logged and communicated.

3. **Key Constants / Opcodes / Calls**:
   - Error message strings: "R6009\r\n- not enough space for environment\r\n", "Microsoft Visual C++ Runtime Library", "Runtime Error!\n\nProgram: ", "<program name unknown>".
   - Function calls: `GetStdHandle`, `WriteFile`, `GetModuleFileNameA`, `FUN_1000d500`, `FUN_1000d510`, `FUN_10010b75`.
   - Constants: `0xfffffff4` (standard error handle), `0x104` (buffer size for module file name), `0x12010` (error dialog type).

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000d500`, `FUN_1000d510`, and `FUN_10010b75`, as they handle the construction and display of error messages. These functions might interact with system logging mechanisms that could be related to state persistence.

---

## 46. `EncatenComponent.dll` — `FUN_10010b75` (`10010b75`)
- **Keywords:** has-strings
- **Strings:** `GetLastActivePopup, GetActiveWindow, MessageBoxA, user32.dll`

*(qwen2.5-coder:14b, 12.0s)*

1. **Role**: This function appears to load the `user32.dll` library and retrieves the addresses of `MessageBoxA`, `GetActiveWindow`, and `GetLastActivePopup` functions. It then calls these functions to display a message box based on the active window and the last active popup.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be a utility function for displaying messages and managing windows, which could be part of a larger process that indirectly affects state persistence.

3. **Key Constants / Opcodes / Calls**:
   - `user32.dll` is loaded.
   - `MessageBoxA`, `GetActiveWindow`, and `GetLastActivePopup` are retrieved via `GetProcAddress`.
   - The function calls these retrieved functions to display a message box.

4. **Next Bite**: Since the function does not directly interact with EEPROM or flash storage, the next step should be to inspect the callers of this function to see if they involve any operations related to state persistence or EEPROM management.

---

## 47. `PBT2.dll` — `FUN_10001a9c` (`10001a9c`)
- **Keywords:** has-strings
- **Strings:** `*** Error: ***	%d
`

*(qwen2.5-coder:14b, 10.2s)*

1. **Role**: This function appears to be responsible for error handling, specifically for reporting errors with a format string that includes an error code (`%d`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with the EEPROM or flash storage to make state permanent. It seems to be a utility function for error reporting.

3. **Key Constants / Opcodes / Calls**: 
   - String: `"*** Error: ***\t%d\n"`
   - Callee: `FUN_10010991`
   - Parameter: `param_1` (which is likely an error code)

4. **Next Bite**: The next callee to inspect is `FUN_10010991`, as it is responsible for actually printing the error message. This function might have more direct interactions with the transport layer or other system components that could be related to EEPROM persistence.

---

## 48. `PBT2.dll` — `FUN_100034dd` (`100034dd`)
- **Keywords:** has-strings
- **Strings:** `Error Creating S-Record Output!, Error Populating Partition!, Error mounting partition: , Error Mounting Partition!, ish_init error: , ISH Initialization Error!, Fatal error.  Terminating..., Fatal error.  Terminating...`

*(qwen2.5-coder:14b, 72.0s)*

1. **Role**: This function appears to handle configuration file parsing and error handling for a device, likely related to radio settings. It checks for configuration file errors, processes configuration tags, and manages memory allocation and deallocation.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper that processes configuration data and may indirectly influence persistence through error handling and configuration validation, but does not explicitly commit changes to EEPROM or flash.

3. **Key Constants / Opcodes / Calls**:
   - Error strings: "Error Creating S-Record Output!", "Error Populating Partition!", "Error mounting partition: ", "ish_init error: ", "Fatal error. Terminating...", "Malloc Error - Cannot Allocate Memory", "Invalid Input!", "Input error on pass #", ": Expected 'TAG =', received: '"
   - Hex constants: `0x10003555`, `0x10003563`, `0x10003576`, `0x10003599`, `0x100035a8`, `0x1000360f`, `0x1000362e`, `0x1000363c`, `0x10003650`, `0x1000365e`, `0x10003673`, `0x1000367e`, `0x100036e7`, `0x100036f7`, `0x100038c6`, `0x100038d4`, `0x100038e7`, `0x100038f5`, `0x1000390a`, `0x10003924`, `0x1000392d`, `0x10003933`, `0x1000394d`, `0x10003964`, `0x1000396c`, `0x10003974`, `0x10003993`, `0x100039a1`, `0x100039b4`, `0x100039c2`, `0x100039d6`, `0x10003714`, `0x1000372a`, `0x1000373f`, `0x1000379b`, `0x100037a9`, `0x100037bc`, `0x100037ca`, `0x100037df`, `0x100037ef`, `0x10003811`, `0x10003849`, `0x10003852`, `0x10003858`, `0x10003861`, `0x10003867`
   - Callees: `FUN_10010f74`, `FUN_10009dc8`, `FUN_10009358`, `FUN_100093c9`, `FUN_100086f8`, `FUN_10008684`, `FUN_100084e3`, `FUN_1000a47f`, `FUN_10008b61`, `FUN_10008c28`, `FUN_10008cb3`, `FUN_1000a080`, `FUN_10008cbe`, `FUN_1000a5e3`, `FUN_1000abbc`, `FUN_10008927`, `FUN_1000ac67`, `FUN_10007787`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000a080`, `FUN_1000a5e3`, and `FUN_1000abbc`, as they are involved in file operations and configuration parsing, which could be critical for understanding how configuration changes are applied and persisted.

---

## 49. `PBT2.dll` — `FUN_100041df` (`100041df`)
- **Keywords:** has-strings
- **Strings:** `Error Populating Partition!, Error mounting partition: , Error Mounting Partition!, ish_init error: , ISH Initialization Error!, Fatal error.  Terminating..., Fatal error.  Terminating..., Fatal error.  Terminating...`

*(qwen2.5-coder:14b, 38.2s)*

1. **Role**: This function appears to handle configuration and data file operations, including error checking, memory allocation, and processing configuration tags. It seems to be a critical part of the initialization and setup process for the radio's configuration.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it appears to manage memory allocation, file operations, and configuration parsing. It may indirectly affect persistence by ensuring that configuration data is correctly loaded and processed before any EEPROM operations are performed.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x100041df`, `0x10004327`, `0x10004348`, `0x1000480f`
   - Error strings: "Error Populating Partition!", "Error mounting partition: ", "Malloc Error - Cannot Allocate Memory", "Invalid Input!"
   - Function calls: `FUN_10010f74`, `FUN_10009dc8`, `FUN_10009929`, `FUN_10009358`, `FUN_1000a0de`, `FUN_100086f8`, `FUN_10008684`, `FUN_1000a47f`, `FUN_10008b61`, `FUN_10008c28`, `FUN_10009d48`, `FUN_10009adb`, `FUN_1000a080`, `FUN_10008cbe`, `FUN_1000940f`, `FUN_1000a5e3`, `FUN_1000abbc`, `FUN_10007787`, `FUN_100084e3`, `FUN_10008927`, `FUN_1000ac67`

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_10009d48`, which is called with parameters related to memory allocation and data processing. This function might be responsible for writing data to memory, which could be a step in the EEPROM commit process.

---

## 50. `PBT2.dll` — `FUN_10005496` (`10005496`)
- **Keywords:** has-strings
- **Strings:** `Error:  only S2 and S3 records supported. , , only S2 and S3 records supported., Invalid S-record input: , Invalid S-record input: , Invalid S-record input: `

*(qwen2.5-coder:14b, 27.8s)*

1. **Role**: This function appears to process S-record input, specifically handling S2 and S3 records, and manages error handling for unsupported record types.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. It seems to be a transport helper that processes data records and may trigger other functions that handle EEPROM persistence, but this is not explicitly shown in the provided code snippet.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x100054f5`, `0x10005503`, `0x1000551a`, `0x1000553f`, `0x1000558e`, `0x100055a9`, `0x100055d0`
   - Strings: "Error: only S2 and S3 records supported.", "Invalid S-record input:"
   - Callees: `FUN_10010f74`, `FUN_10009d9c`, `FUN_100086f8`, `FUN_10008684`, `FUN_1000adbb`, `FUN_1000ae44`, `FUN_100086e4`, `FUN_100084e3`, `FUN_10009dc8`, `FUN_1000a47f`, `FUN_10008b61`, `FUN_10008c28`

4. **Next Bite**: The callees `FUN_10009d9c`, `FUN_100086f8`, `FUN_10008684`, `FUN_1000adbb`, `FUN_1000ae44`, `FUN_100086e4`, `FUN_100084e3`, `FUN_10009dc8`, `FUN_1000a47f`, `FUN_10008b61`, and `FUN_10008c28` should be inspected next to trace EEPROM persistence, as they are likely responsible for handling the actual data processing and storage operations.

---

## 51. `PBT2.dll` — `FUN_10005a35` (`10005a35`)
- **Keywords:** has-strings
- **Strings:** `Input error:  Expected 'TYPE = ', received: ', Input error:  Expected TYPE = , Input error:  Expected 'ID = ', received: ', , Received: , , Received: , Input error:  Expected ID = , Error: Hex conversion failed.  Cannot continue., Error: Hex conversion failed.  Cannot continue. `

*(qwen2.5-coder:14b, 50.0s)*

1. **Role**: This function appears to handle input parsing and validation, possibly for configuration data, and manages state transitions and error handling related to the radio's configuration process.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by managing input validation and state transitions. It does not directly perform EEPROM writes or commits but is involved in the process of ensuring data integrity and correctness before any permanent changes are made.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x0100`, `0x0101`, `0x0102`, `0x0103`, `0x0106`, `0x0107`, `0x000C`, `0x000D`, `0x0012`.
   - Error strings: "Input error: Expected 'TYPE = '", "Input error: Expected TYPE = ", "Input error: Expected 'ID = '", "Error: Hex conversion failed. Cannot continue.", "Error: Checksum does not calculate. Invalid S-record:", "Error: Address does not verify. Invalid S-record:", "Error: inconsistent S-record types within the same item."
   - Callees: `FUN_1000a5e3`, `FUN_1000abbc`, `FUN_1000bceb`, `FUN_100086f8`, `FUN_10008684`, `FUN_1000adbb`, `FUN_1000ae44`, `FUN_1000aecd`, `FUN_100086e4`, `FUN_100084e3`, `FUN_10009dc8`, `FUN_1000a47f`, `FUN_1000ac67`, `FUN_10004fa6`, `FUN_1000af4e`, `FUN_10009c13`, `FUN_10005496`.

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_1000a5e3`, `FUN_1000abbc`, `FUN_1000bceb`, `FUN_100086f8`, `FUN_10008684`, `FUN_1000adbb`, `FUN_1000ae44`, `FUN_1000aecd`, `FUN_100086e4`, `FUN_100084e3`, `FUN_10009dc8`, `FUN_1000a47f`, `FUN_1000ac67`, `FUN_10004fa6`, `FUN_1000af4e`, `FUN_10009c13`, and `FUN_10005496`. These functions are involved in input handling, error checking, and state transitions, which are critical for understanding how permanent state changes are managed on the radio.

---

## 52. `PBT2.dll` — `FUN_10006780` (`10006780`)
- **Keywords:** has-strings
- **Strings:** `Input error:  Expected 'TYPE = ', received: ', Input error:  Expected TYPE = , Input error:  Expected 'ID = ', received: ', , Received: , , Received: , Input error:  Expected ID = , Error: Hex conversion failed.  Cannot continue., Error: Hex conversion failed.  Cannot continue. `

*(qwen2.5-coder:14b, 37.1s)*

1. **Role**: This function appears to handle input validation and processing, possibly related to configuration or data transfer for the radio. It checks for specific input patterns and errors, and seems to manage state transitions or operations based on these checks.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to manage state transitions and error handling, which could indirectly affect persistence by ensuring data integrity and proper state management before committing changes to the radio's storage.

3. **Key Constants / Opcodes / Calls**:
   - **Error Messages**: "Input error: Expected 'TYPE = ', received: '", "Input error: Expected TYPE = ", "Input error: Expected 'ID = ', received: '", "Error: Hex conversion failed. Cannot continue.", "Error: Checksum does not calculate. Invalid S-record: ", "Error: Address does not verify. Invalid S-record: ".
   - **Function Calls**: `FUN_1000a080`, `FUN_1000bceb`, `FUN_1000a47f`, `FUN_10008b61`, `FUN_10008c28`, `FUN_100093c9`, `FUN_10008cb3`, `FUN_10009dc8`, `FUN_10009358`, `FUN_100086f8`, `FUN_10008684`, `FUN_1000adbb`, `FUN_1000ae44`, `FUN_1000aecd`, `FUN_100086e4`, `FUN_100084e3`, `FUN_1000a5e3`, `FUN_1000abbc`, `FUN_10009c13`, `FUN_10004fa6`.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000a47f`, `FUN_10008b61`, and `FUN_10008c28`, as they are involved in state transitions and could be responsible for committing changes to the radio's storage.

---

## 53. `PBT2.dll` — `FUN_10007787` (`10007787`)
- **Keywords:** has-strings
- **Strings:** ` bytes., ERROR:  Unrecognized value ", Error:  Unrecognized value ", OPTIMIZE,           for a non-READ_WRITE (read_only) partition.  Need at least 1 but , Error:  There is an insufficent number of blocks allocated for a non-READ_WRITE (read_only) partition. 
Need at least 1, but requested only , FALSE, FALSE`

**ERROR querying homelab AI:** `timed out`

---

## 54. `PBT2.dll` — `FUN_1000825f` (`1000825f`)
- **Keywords:** has-strings
- **Strings:** `Invalid address in S-record: , Invalid address in S-record: , Invalid address in S-record: , Error:  Invalid address in , Error:  Invalid address in , Error:  Invalid address in `

*(qwen2.5-coder:14b, 23.7s)*

1. **Role**: This function appears to handle some form of data processing or validation, possibly related to S-records, and manages error handling and state transitions within the application.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. It seems to be more of a transport helper or data validation function that might indirectly influence state persistence through error handling and state transitions.

3. **Key Constants / Opcodes / Calls**:
   - Strings: "Invalid address in S-record: ", "Error:  Invalid address in "
   - Calls: `FUN_10010f74`, `FUN_10009dc8`, `FUN_10009c13`, `FUN_10005496`, `FUN_1000533e`, `FUN_1000544a`, `FUN_100086f8`, `FUN_10008684`, `FUN_1000adbb`, `FUN_100086e4`, `FUN_100084e3`, `FUN_10009dc8`, `FUN_1000a47f`, `FUN_10008b61`, `FUN_10008c28`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10005496`, `FUN_1000533e`, `FUN_1000544a`, `FUN_100086f8`, `FUN_10008684`, `FUN_1000adbb`, `FUN_100086e4`, and `FUN_100084e3`, as they are involved in error handling and state transitions that might affect EEPROM persistence.

---

## 55. `PBT2.dll` — `FUN_100084e3` (`100084e3`)
- **Keywords:** has-strings
- **Strings:** `
Error Code - , 
Error Code - , 
Error Code - `

*(qwen2.5-coder:14b, 14.6s)*

1. **Role**: This function appears to handle error messages and state management, possibly related to communication or configuration operations on the radio.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. It seems to manage state markers and possibly locks, but does not explicitly commit changes to persistent storage. It may be part of a larger process that ensures state persistence.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x30`, `0x40`
   - Strings: `"\nError Code - "`, `&DAT_1002d208`
   - Function calls: `FUN_10010f74`, `FUN_1001acef`, `FUN_10009dc8`, `FUN_10009c13`, `FUN_10009b63`, `MessageBoxA`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1001acef`, `FUN_10009dc8`, and `FUN_10009c13`, as they are involved in state management and might interact with persistent storage.

---

## 56. `PBT2.dll` — `uflow` (`10008d87`)
- **Keywords:** named

*(qwen2.5-coder:14b, 14.7s)*

1. **Role**: The `uflow` function is a virtual method in the `std::basic_streambuf<char, std::char_traits<char>>` class, responsible for reading the next character from the input sequence. It checks if the input sequence is empty and, if not, increments the get pointer and returns the character at the new position.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly handle EEPROM persistence or state commitment. It is a standard stream buffer operation and is likely part of a larger mechanism that manages data flow, possibly related to communication protocols or data handling but not directly involved in making state permanent on the radio.

3. **Key Constants / Opcodes / Calls**: 
   - The function calls a method pointed to by `*(int *)this + 0x10`, which is likely a virtual function call related to input sequence management.
   - The function uses `_Gninc(this)`, which increments the get pointer of the stream buffer.
   - The return value `-1` indicates an error or end-of-file condition.

4. **Next Bite**: The next callee to inspect for EEPROM persistence would be the method pointed to by `*(int *)this + 0x10`, as it is the primary operation that could be related to input sequence management or data handling, which might be indirectly involved in state persistence mechanisms.

---

## 57. `PBT2.dll` — `FUN_1000a890` (`1000a890`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 19.5s)*

1. **Role**: This function appears to handle error checking and exception handling, possibly related to locale settings or configuration. It checks for missing locale facets and throws an exception if necessary, while also managing some form of resource allocation or initialization.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be more of a transport helper or configuration management function, possibly involved in setting up or validating state before any EEPROM operations occur.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_1000a9e4`, `FUN_1000be76`
   - Global variables: `DAT_10037d34`, `DAT_10034e94`, `DAT_10030a98`, `DAT_1003747c`
   - Pointer: `&PTR_LAB_1002e664`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000a9b4`, `FUN_1001e175`, and `FUN_1000be76`, as they are involved in resource management and initialization processes that might be related to setting up or committing state to EEPROM.

---

## 58. `PBT2.dll` — `~ctype<>` (`1000ab9c`)
- **Keywords:** named

*(qwen2.5-coder:14b, 14.2s)*

1. **Role**: This function is a destructor for a `std::ctype` object, responsible for cleaning up resources associated with the object. It sets up pointers and conditionally calls a cleanup function.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash storage. It appears to be a transport helper function, possibly involved in managing resources or state within the application, but not directly related to making state permanent on the radio.

3. **Key Constants / Opcodes / Calls**: 
   - `PTR_FUN_1002e634`: A pointer to a function.
   - `param_1[5]`: A condition checked to determine if a cleanup function should be called.
   - `FUN_10010949`: A cleanup function called if `param_1[5]` is non-zero.
   - `PTR_LAB_1002e538`: Another pointer set in the function.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_10010949`, as it is conditionally called based on the state of `param_1[5]` and could potentially handle resource cleanup or state management related to the radio's permanent storage.

---

## 59. `PBT2.dll` — `FUN_1000aff7` (`1000aff7`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 20.6s)*

1. **Role**: This function appears to handle error checking and initialization, possibly related to locale settings or resource allocation. It throws an exception if certain conditions are met and initializes a global variable if another condition is satisfied.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to manage resources and handle exceptions, which could be part of a larger process that affects state persistence.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_1001ea2d`, `FUN_1001eae6`, `FUN_1000bec4`
   - Global variables: `DAT_10037d3c`, `DAT_10034e94`, `DAT_10030a98`, `DAT_10037480`
   - Pointers: `PTR_LAB_1002e664`, `PTR_FUN_1002e5e8`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, and `FUN_1000bec4`, as they are involved in critical operations that could be related to state management or resource allocation.

---

## 60. `PBT2.dll` — `operator=` (`1000ba87`)
- **Keywords:** named

*(qwen2.5-coder:14b, 13.8s)*

1. **Role**: This function is an overloaded assignment operator for `std::ostreambuf_iterator<char,struct std::char_traits<char> >`. It attempts to write a character to the associated output stream buffer and sets the iterator to an end-of-sequence state if the write fails.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly interact with EEPROM or manage state persistence on the radio. It is a transport helper function that may be part of a larger mechanism responsible for writing data to the radio's memory.

3. **Key Constants / Opcodes / Calls**: 
   - `0x10009f72`: A function pointer or offset that likely handles the actual write operation to the output stream buffer.
   - `0xffffffff`: An error code indicating that the write operation failed.
   - `0x1`: A value used to set the iterator to an end-of-sequence state if the write fails.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_10009f72`, which is responsible for the actual write operation to the output stream buffer. This function should be analyzed to understand how it interacts with the radio's memory and whether it involves any EEPROM commit or lock/unlock operations.

---

## 61. `PBT2.dll` — `FUN_1000baf5` (`1000baf5`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 18.7s)*

1. **Role**: This function appears to handle locale-related initialization and error handling. It checks for locale settings, throws an exception if missing, and initializes a locale object if necessary.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more focused on locale settings and error management.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_1000bd97`, `FUN_1000bf12`, `FUN_1001d8cd`
   - Global variables: `DAT_10037d38`, `DAT_10034e94`, `DAT_10030a98`, `DAT_10037484`
   - Exception handling: `__CxxThrowException_8`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000a9b4`, `FUN_1000bf12`, and any other functions that might interact with storage or state management, such as `FUN_1000bd97`. These functions could potentially handle the actual commit or locking mechanisms.

---

## 62. `PBT2.dll` — `FUN_1000bbb9` (`1000bbb9`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 19.3s)*

1. **Role**: This function appears to handle locale-related initialization or configuration, possibly setting up locale facets or handling exceptions related to missing locale settings. It checks for locale availability and throws an exception if missing, otherwise initializes a locale object.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more related to locale settings and exception handling, which are not directly tied to making state permanent on the radio.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_1000bd0d`, `FUN_1000bf60`, `FUN_1001d8cd`
   - Global data: `DAT_10037d2c`, `DAT_10034e94`, `DAT_10030a98`, `DAT_10037488`, `PTR_LAB_1002e664`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000a9b4`, `FUN_1000bd0d`, and `FUN_1000bf60`. These functions might have deeper interactions with the radio's storage mechanisms.

---

## 63. `PBT2.dll` — `FUN_1000c011` (`1000c011`)
- **Keywords:** has-strings
- **Strings:** `false`

*(qwen2.5-coder:14b, 14.5s)*

1. **Role**: This function appears to populate a structure at the memory address specified by `param_1` with various data, including strings and possibly status indicators. It seems to be preparing data for further processing or transmission.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It appears to be a transport helper function that prepares data for transmission, possibly related to state persistence, but does not perform any direct commit or lock operations on the radio's storage.

3. **Key Constants / Opcodes / Calls**:
   - `FUN_10012018()`: A function call that returns a pointer to an array of `undefined4`.
   - `FUN_1000c18e()`: A function call that takes a string and returns an `undefined4` value.
   - `s_false_10034ec8`: A string constant with the value "false".
   - `DAT_10034ec0`: A data reference.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10012018` and `FUN_1000c18e`. These functions might provide more insight into how data is prepared and potentially interact with storage mechanisms.

---

## 64. `PBT2.dll` — `FUN_1000d4ae` (`1000d4ae`)
- **Keywords:** has-strings
- **Strings:** `Motorola Copyright 2001 Licensed`

*(qwen2.5-coder:14b, 10.4s)*

1. **Role**: This function allocates a string containing the copyright notice "Motorola Copyright 2001 Licensed" and assigns it to a global variable `DAT_100374b4`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanism. It appears to be a utility function for managing string resources.

3. **Key Constants / Opcodes / Calls**:
   - String: "Motorola Copyright 2001 Licensed"
   - Global variable: `DAT_100374b4`
   - Function call: `SysAllocString`

4. **Next Bite**: Since this function is primarily concerned with string allocation and does not involve any direct interaction with EEPROM or persistence mechanisms, there is no specific callee to inspect next for tracing EEPROM persistence. Further analysis should focus on other functions that handle EEPROM operations or state persistence.

---

## 65. `PBT2.dll` — `FUN_1000d522` (`1000d522`)
- **Keywords:** has-strings
- **Strings:** `Motorola, 352FEFDA-4965-11D5-A218-0060B0FC83F1, Licenses`

*(qwen2.5-coder:14b, 15.9s)*

1. **Role**: This function retrieves the computer name and checks for a specific registry key and value related to licenses. It then calls another function (`FUN_1001221f`) with the computer name and the registry value.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. It appears to be a transport helper function that checks for licensing information and may be involved in the overall state management process, but it does not explicitly handle EEPROM persistence.

3. **Key Constants / Opcodes / Calls**:
   - Strings: "Motorola", "352FEFDA-4965-11D5-A218-0060B0FC83F1", "Licenses"
   - Registry keys: `HKEY_LOCAL_MACHINE\SOFTWARE\Licenses\{352FEFDA-4965-11D5-A218-0060B0FC83F1}`
   - Registry value size: 0x1f (31 bytes)
   - Function call: `FUN_1001221f`

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_1001221f`, as it is called with the computer name and the registry value, and it likely contains the logic for handling the state persistence on the radio.

---

## 66. `PBT2.dll` — `FUN_1000d66a` (`1000d66a`)
- **Keywords:** has-strings
- **Strings:** `REGISTRY, Module`

*(qwen2.5-coder:14b, 19.1s)*

1. **Role**: This function appears to handle the registration and configuration of a module, likely related to the CPS/NextGen10/ByteData10 system. It processes module file paths, handles string conversions, and interacts with the Windows registry.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to manage module registration and configuration, which could indirectly affect state persistence by ensuring the correct settings are applied. It does not explicitly call any known opcodes for EEPROM commit or lock/unlock operations.

3. **Key Constants / Opcodes / Calls**:
   - **Strings**: "REGISTRY", "Module"
   - **Error HRESULT**: `0x8007000e`
   - **Function Calls**: `FUN_10010f74`, `FUN_1000d83e`, `FUN_1000d92f`, `FUN_10010949`, `FUN_1000d85a`, `FUN_1000db17`, `FUN_1000d997`
   - **Constants**: `0x104`, `0x224`, `0x57`, `0x8007000e`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000db17` and `FUN_1000d997`, as they are conditionally called based on a flag and could potentially handle the actual registration or configuration that affects state persistence.

---

## 67. `PBT2.dll` — `FUN_1000e01d` (`1000e01d`)
- **Keywords:** has-strings
- **Strings:** `TYPELIB, TYPELIB, TYPELIB, TYPELIB, CLSID, CLSID, Delete, NoRemove`

*(qwen2.5-coder:14b, 22.6s)*

1. **Role**: The function `FUN_1000e01d` appears to handle operations related to registry keys and values, possibly managing settings or configurations for the radio. It processes strings to determine actions like deleting, removing, or modifying registry entries.

2. **EEPROM / Persistence Mechanism**: The function interacts with the Windows registry, which is a common mechanism for storing configuration data. It does not directly interact with EEPROM or flash memory, but it may indirectly affect the radio's persistent state by updating settings that are later written to the radio's memory. The function does not explicitly call any known opcodes for EEPROM/flash commit or reset.

3. **Key Constants / Opcodes / Calls**:
   - **Strings**: "Delete", "NoRemove", "ForceRemove", "CLSID"
   - **Error HRESULTs**: `-0x7ffdfff7` (indicating an error)
   - **Callees**: `FUN_1000dccb`, `FUN_1000e99c`, `FUN_1000e679`, `RegCreateKeyExA`, `RegCloseKey`, `RegDeleteKeyA`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000e99c` and `FUN_1000e679`, as they are involved in modifying registry entries and could potentially trigger operations that affect the radio's persistent state.

---

## 68. `PBT2.dll` — `FUN_1000f104` (`1000f104`)
- **Keywords:** has-strings
- **Strings:** `UnRegisterTypeLib, oleaut32.dll`

*(qwen2.5-coder:14b, 21.9s)*

1. **Role**: This function appears to unregister a type library and clean up resources related to COM objects. It handles error checking and resource management, including freeing strings and releasing COM interfaces.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more of a utility function for managing COM resources, which might be indirectly related to state persistence through higher-level operations.

3. **Key Constants / Opcodes / Calls**:
   - `HRESULT HVar2`: Used for error checking.
   - `0x1c` and `0x30`: Offsets used to access function pointers in the COM interface.
   - `LoadLibraryA("oleaut32.dll")`: Loads the `oleaut32.dll` library.
   - `GetProcAddress(hModule, "UnRegisterTypeLib")`: Retrieves the address of the `UnRegisterTypeLib` function.
   - `SysFreeString(*(BSTR *)(unaff_EBP + -0x14))`: Frees a BSTR string.
   - `FUN_10010f74()`: An initial function call at the start.
   - `FUN_1000ef04()`: A function call to register a type library.
   - `(**(code **)(**(int **)(unaff_EBP + -0x10) + 0x1c))`: Calls a method on a COM interface.
   - `(**(code **)(**(int **)(unaff_EBP + -0x10) + 0x30))`: Calls another method on a COM interface.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000ef04` and the methods accessed via the COM interface offsets `0x1c` and `0x30`. These might involve more direct interactions with the radio's state or storage mechanisms.

---

## 69. `PBT2.dll` — `~exception` (`10011ed5`)
- **Keywords:** named

*(qwen2.5-coder:14b, 10.6s)*

1. **Role**: This function is the destructor for an exception class. It sets the vtable pointer of the object to a new value and calls a cleanup function if a specific condition is met.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It appears to be a general-purpose cleanup routine.

3. **Key Constants / Opcodes / Calls**: 
   - `PTR_FUN_1002d55c`: A pointer to a function.
   - `*(int *)(this + 8) != 0`: Checks a condition at offset 8 of the object.
   - `FUN_10010f93`: A cleanup function called if the condition is met.

4. **Next Bite**: The next callee to inspect is `FUN_10010f93` to trace any potential interactions with EEPROM persistence or other storage mechanisms.

---

## 70. `PBT2.dll` — `entry` (`1001268b`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 15.3s)*

1. **Role**: This function appears to be an entry point for handling different operations on a module, possibly related to radio configuration or state management. It checks the operation type (`param_2`) and delegates tasks to other functions based on the operation code.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to manage operations that might involve state persistence, such as committing changes or handling locks. It calls other functions (`FUN_100125b2`, `FUN_1000e9ec`) that could be responsible for actual EEPROM operations.

3. **Key Constants / Opcodes / Calls**:
   - `param_2` values: 0, 1, 2, 3
   - `DAT_10037570`, `DAT_10039224`: Global data pointers
   - `FUN_100125b2`, `FUN_1000e9ec`: Function pointers or callees
   - `0x0`: Success indicator

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_100125b2` and `FUN_1000e9ec`. These functions are likely responsible for the actual operations that affect the radio's permanent state.

---

## 71. `PBT2.dll` — `FUN_1001366d` (`1001366d`)
- **Keywords:** has-strings
- **Strings:** `null), null), null)`

*(qwen2.5-coder:14b, 30.5s)*

1. **Role**: This function appears to parse and process a configuration or command string, likely related to radio settings or operations. It handles various cases based on the input characters and possibly updates internal state or settings.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. It seems to be more of a transport helper, possibly preparing data for transmission or handling received data. It may indirectly affect persistence through calls to other functions that handle EEPROM operations.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x20`, `0x23`, `0x2a`, `0x2b`, `0x2d`, `0x30`, `0x49`, `0x68`, `0x6c`, `0x77`, `0x67`, `0x58`, `0x43`, `0x45`, `0x47`, `0x53`, `0x5a`, `0x69`
   - Offsets: `DAT_1002d5ac`, `DAT_1002d5cc`, `PTR_DAT_10035700`, `PTR_DAT_10035590`
   - Error HRESULTs: Not explicitly shown in the provided code snippet.
   - Callees: `FUN_10013dae`, `FUN_10013e4c`, `FUN_10013e69`, `FUN_1001740b`, `FUN_10013e59`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10013dae`, `FUN_10013e4c`, `FUN_10013e69`, `FUN_1001740b`, and `FUN_10013e59`. These functions are likely responsible for handling specific operations that could involve EEPROM or flash storage.

---

## 72. `PBT2.dll` — `FUN_10014a9f` (`10014a9f`)
- **Keywords:** has-strings
- **Strings:** `LC_CTYPE, LC_COLLATE, LC_COLLATE`

*(qwen2.5-coder:14b, 19.5s)*

1. **Role**: This function appears to handle locale-related settings or configurations, possibly parsing and setting locale categories like LC_CTYPE and LC_COLLATE. It checks input parameters, processes locale strings, and interacts with other functions to apply these settings.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be more of a transport helper, managing locale settings and possibly triggering other functions that handle EEPROM persistence indirectly.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x13`, `0x100381c8`, `0x100381cc`, `0x100356bc`, `0x100356f5`, `0x100356f9`
   - Strings: `"LC_CTYPE"`, `"LC_COLLATE"`
   - Function calls: `FUN_100128a1`, `FUN_10018360`, `_strncmp`, `_strlen`, `_strncpy`, `FUN_10014ce5`, `FUN_10014eb9`, `FUN_10014e00`, `FUN_10012902`, `FUN_10010949`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10014ce5` and `FUN_10014eb9`, as they are involved in processing and applying locale settings, which might indirectly trigger EEPROM operations.

---

## 73. `PBT2.dll` — `FUN_10014e00` (`10014e00`)
- **Keywords:** has-strings
- **Strings:** `LC_CTYPE, LC_COLLATE`

*(qwen2.5-coder:14b, 20.2s)*

1. **Role**: This function appears to manage a buffer (`DAT_100356bc`) and checks for string equality across multiple entries. It returns a pointer to a result based on the comparison outcome.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that manages data buffers and performs string comparisons. It does not explicitly handle commit, lock, unlock, or reset operations related to EEPROM persistence.

3. **Key Constants / Opcodes / Calls**:
   - `DAT_100356bc`: A pointer to a dynamically allocated buffer.
   - `0x351`: The size of the buffer allocated by `_malloc`.
   - `FUN_10014fd1`: A function that appears to perform some operation on the buffer, possibly setting or resetting its contents.
   - `FUN_10015ef0`: A function that takes the buffer and another pointer (`&DAT_1002d6f8`) as arguments.
   - `FUN_10010949`: A function that is called if the string comparison is successful, possibly to finalize or process the buffer.
   - `PTR_DAT_100356c8`: A pointer to an array of strings or pointers to strings.
   - `PTR_DAT_100356d4`: A pointer to a result or a final destination.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10014fd1`, `FUN_10015ef0`, and `FUN_10010949`. These functions may contain the actual logic for handling the buffer's contents, which could be related to EEPROM persistence.

---

## 74. `PBT2.dll` — `FUN_10016108` (`10016108`)
- **Keywords:** has-strings
- **Strings:** `KERNEL32`

*(qwen2.5-coder:14b, 13.1s)*

1. **Role**: This function checks if a specific processor feature is present by calling `IsProcessorFeaturePresent` from the `KERNEL32` module. If the feature is not present, it calls another function `FUN_100160ca`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with EEPROM or manage state persistence on the radio. It appears to be a utility function for processor feature detection.

3. **Key Constants / Opcodes / Calls**:
   - `GetModuleHandleA("KERNEL32")`: Retrieves a handle to the `KERNEL32` module.
   - `GetProcAddress(hModule, "IsProcessorFeaturePresent")`: Retrieves the address of the `IsProcessorFeaturePresent` function.
   - `(*pFVar1)(0)`: Calls `IsProcessorFeaturePresent` with a parameter of `0`.
   - `FUN_100160ca()`: A function called if `IsProcessorFeaturePresent` is not available.

4. **Next Bite**: The next function to inspect for EEPROM persistence is `FUN_100160ca`, as it is called when the processor feature check fails.

---

## 75. `PBT2.dll` — `FUN_10016290` (`10016290`)
- **Keywords:** has-strings
- **Strings:** `e+000`

*(qwen2.5-coder:14b, 12.5s)*

1. **Role**: This function appears to format a string based on input parameters and possibly modify a buffer. It conditionally calls another function (`FUN_10016532`) and manipulates the buffer content based on the input parameters.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a helper function for string manipulation and does not involve any direct commit, lock, unlock, or reset operations related to persistent storage.

3. **Key Constants / Opcodes / Calls**:
   - String `"e+000"` is referenced.
   - Calls `FUN_10016532` and `FUN_10015ee0`.
   - Hex constants like `0x2d` and `0x45` are used.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10016532` and `FUN_10015ee0`, as they are directly invoked by this function and might contain the logic related to EEPROM operations.

---

## 76. `PBT2.dll` — `FUN_10017181` (`10017181`)
- **Keywords:** has-strings
- **Strings:** `R6009
- not enough space for environment
, R6009
- not enough space for environment
, R6009
- not enough space for environment
, Microsoft Visual C++ Runtime Library, Runtime Error!

Program: , <program name unknown>`

*(qwen2.5-coder:14b, 15.6s)*

1. **Role**: This function appears to handle error reporting and logging, specifically for runtime errors related to insufficient space for the environment. It writes error messages to the standard error handle and, in some cases, displays a runtime error dialog.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with the radio's EEPROM or flash memory. It seems to be more focused on error handling and reporting rather than managing the radio's persistent state.

3. **Key Constants / Opcodes / Calls**:
   - Error message strings: "R6009\r\n- not enough space for environment\r\n"
   - Runtime error dialog title: "Microsoft Visual C++ Runtime Library"
   - Error message prefix: "Runtime Error!\n\nProgram: "
   - Function calls: `GetStdHandle`, `WriteFile`, `GetModuleFileNameA`, `FUN_10015ee0`, `FUN_10015ef0`, `FUN_10019bbd`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10015ee0`, `FUN_10015ef0`, and `FUN_10019bbd`, as they are responsible for constructing and displaying the error message. These functions might have deeper interactions with the system or the radio's state management.

---

## 77. `PBT2.dll` — `FUN_10018b01` (`10018b01`)
- **Keywords:** has-strings
- **Strings:** `Mexico, Spanish`

*(qwen2.5-coder:14b, 17.8s)*

1. **Role**: This function appears to search for a locale identifier (`param_1`) within a predefined list and copies the corresponding locale-specific string to the buffer pointed to by `param_3`. If the locale is not found in the list, it falls back to using the `GetLocaleInfoA` function to retrieve the locale information.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. It is a transport helper function that retrieves locale-specific data, which could be used in subsequent operations that might affect the radio's state. However, it does not explicitly handle commit, lock/unlock, or reset operations related to EEPROM persistence.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x1a`, `0x2c`, `0x10035ce0`, `0x10035cec`, `0x10035cf4`
   - Offsets: `0x10035ce4`, `0x10035cf0`, `0x10035cf8`, `0x10035cfc`, `0x10035d04`
   - Callee: `GetLocaleInfoA`

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `GetLocaleInfoA`, as it is called when the locale identifier is not found in the predefined list. This function might interact with the system's locale database, which could be related to the radio's state persistence mechanisms.

---

## 78. `PBT2.dll` — `FUN_10019bbd` (`10019bbd`)
- **Keywords:** has-strings
- **Strings:** `GetLastActivePopup, GetActiveWindow, MessageBoxA, user32.dll`

*(qwen2.5-coder:14b, 16.2s)*

1. **Role**: This function appears to load the `user32.dll` library and retrieves the addresses of `MessageBoxA`, `GetActiveWindow`, and `GetLastActivePopup` functions. It then calls these functions to display a message box associated with the active window.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It is more likely a helper function for user interface operations rather than managing persistent state on the radio.

3. **Key Constants / Opcodes / Calls**: 
   - `DAT_100377ec`: Address of `MessageBoxA`
   - `DAT_100377f0`: Address of `GetActiveWindow`
   - `DAT_100377f4`: Address of `GetLastActivePopup`
   - `LoadLibraryA("user32.dll")`: Loads the user32.dll library
   - `GetProcAddress`: Retrieves the address of a function in the loaded DLL

4. **Next Bite**: Since this function is primarily concerned with user interface operations, the next callees to inspect for EEPROM persistence should be those related to communication with the radio, such as functions that use the known opcodes (e.g., `0x0100`, `0x0101`, `0x0106`, etc.). These functions are more likely to handle the actual state persistence on the radio.

---

## 79. `PBT2.dll` — `FUN_10019e05` (`10019e05`)
- **Keywords:** has-strings
- **Strings:** `Monday, Sunday, Sunday`

*(qwen2.5-coder:14b, 10.1s)*

1. **Role**: This function appears to concatenate strings from a set of pointers, likely related to date or time information, into a single formatted string. It uses colons (`:`) as separators and allocates memory for the resulting string.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be a utility function for string manipulation, possibly used in preparing data for transport or logging.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x3a` (colon `:`)
   - Function calls: `FUN_10015ee0`, `_strlen`, `_malloc`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10015ee0` and any other functions that might interact with storage or transport mechanisms.

---

## 80. `PBT2.dll` — `FUN_10019e94` (`10019e94`)
- **Keywords:** has-strings
- **Strings:** `February, January, January`

*(qwen2.5-coder:14b, 13.1s)*

1. **Role**: This function appears to concatenate strings from a series of structures, likely related to configuration or status information, into a single formatted string. It uses colons (`:`) as separators and allocates memory for the resulting string.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a helper function for formatting data, possibly for display or logging purposes. It does not involve any explicit commit, lock, unlock, or reset operations related to EEPROM persistence.

3. **Key Constants / Opcodes / Calls**:
   - **Strings**: "February", "January"
   - **Function Calls**: `FUN_10015ee0`, `_strlen`, `_malloc`
   - **Memory Offsets**: `PTR_PTR_10036488`, `0x38`, `0x68`, `-0xc`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10015ee0`, as it is called twice within the loop and may handle the actual data formatting or conversion that could be related to EEPROM operations.

---

## 81. `PBT2.dll` — `FUN_10019f29` (`10019f29`)
- **Keywords:** has-strings
- **Strings:** `H:mm:ss, dddd, MMMM dd, yyyy, dddd, MMMM dd, yyyy, M/d/yy, M/d/yy, February, January, January`

*(qwen2.5-coder:14b, 17.0s)*

1. **Role**: This function appears to allocate memory and construct a data structure by concatenating strings from various sources, possibly related to configuration or state information for the radio.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper that prepares data for transmission or storage, but does not commit changes to permanent storage itself.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x2b`, `0x1a`, `0x26`, `0x27`, `0x28`, `0x29`, `0x2a`, `0x98`, `0x9c`, `0xa0`, `0xa4`, `0xa8`
   - Offsets: `0x38`, `0x1c`
   - Callees: `FUN_100110e0`, `FUN_10015ee0`
   - Strings: `"H:mm:ss"`, `"dddd, MMMM dd, yyyy"`, `"M/d/yy"`, `"February"`, `"January"`, `"Monday"`, `"Sunday"`

4. **Next Bite**: The callees `FUN_100110e0` and `FUN_10015ee0` should be inspected next to trace how the data is constructed and potentially persisted.

---

## 82. `PBT2.dll` — `FUN_1001a723` (`1001a723`)
- **Keywords:** has-strings
- **Strings:** `am/pm`

*(qwen2.5-coder:14b, 17.7s)*

1. **Role**: This function processes a byte stream, likely related to configuration or data handling for a radio device. It appears to interpret specific byte sequences and perform actions based on them, possibly modifying internal state or preparing data for transmission.

2. **EEPROM / Persistence Mechanism**: The function does not directly commit data to EEPROM or flash. Instead, it seems to prepare data for further processing or transmission, possibly setting up markers or flags that indicate changes that need to be persisted. It does not explicitly handle locking, unlocking, or resetting the device.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x27`, `0x41`, `0x48`, `0x4d`, `0x61`, `0x68`, `0x6d`, `0x73`, `0x74`, `0x79`
   - Strings: `"am/pm"`
   - Function calls: `FUN_10016a30`, `FUN_1001a255`
   - Offsets: `0x98`, `0x9c`

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_1001a255`, as it is called with parameters that suggest it might handle the actual processing or transmission of data, which could involve committing changes to permanent storage.

---

## 83. `PBT2.dll` — `FUN_1001b57e` (`1001b57e`)
- **Keywords:** has-strings
- **Strings:** `1#QNAN, 1#INF, 1#IND, 1#SNAN`

*(qwen2.5-coder:14b, 22.2s)*

1. **Role**: This function appears to handle the conversion of floating-point numbers to a string representation, possibly for display or storage purposes. It processes various edge cases, including NaN, infinity, and underflow conditions.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that formats data for transmission or storage, but does not commit changes to permanent storage itself.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x7fff`, `0x80000000`, `0x40000000`, `0xc0000000`, `0x3ffe`, `0x15`, `0x4d10`, `-0x134312f4`.
   - Strings: `"1#QNAN"`, `"1#INF"`, `"1#IND"`, `"1#SNAN"`.
   - Calls: `FUN_10015ee0`, `FUN_1001bf54`, `FUN_1001bd34`, `FUN_1001af8b`, `FUN_1001afb9`, `___add_12`.

4. **Next Bite**: The callees `FUN_10015ee0`, `FUN_1001bf54`, `FUN_1001bd34`, `FUN_1001af8b`, `FUN_1001afb9`, and `___add_12` should be inspected next to trace any potential interactions with EEPROM persistence or data formatting that might affect permanent state on the radio.

---

## 84. `PBT2.dll` — `uflow` (`1001d0fb`)
- **Keywords:** named

*(qwen2.5-coder:14b, 16.0s)*

1. **Role**: The `uflow` function is a virtual method in a stream buffer class, responsible for reading the next character from the input sequence. It checks if the input is available and returns the next character if successful, or a special value (`0xffff`) if the input is exhausted.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly handle EEPROM persistence. It appears to be a transport helper function that interacts with the input stream, possibly related to reading data from the radio. It does not explicitly commit changes to EEPROM, lock/unlock, or reset the device.

3. **Key Constants / Opcodes / Calls**: 
   - The function calls another function through a vtable pointer at offset `0x10` of the `param_1` object.
   - It checks the return value of this call (`sVar1`), which is compared to `-1` to determine if the input is exhausted.
   - The function `Gninc` is called with `param_1` to increment the stream buffer position.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is the function pointed to by the vtable at offset `0x10` of `param_1`. This function (`**(code **)(*param_1 + 0x10))()`) is responsible for reading the next character from the input stream and should be analyzed to understand how it interacts with the radio's EEPROM or other persistent storage mechanisms.

---

## 85. `PBT2.dll` — `Gninc` (`1001d73e`)
- **Keywords:** named

*(qwen2.5-coder:14b, 12.6s)*

1. **Role**: The function `Gninc` appears to be a part of a stream buffer implementation, specifically decrementing a counter at offset `0x2c` and incrementing another counter at offset `0x1c` within the object pointed to by `param_1`.

2. **EEPROM / Persistence Mechanism**: This function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that manages internal state counters, possibly related to buffer management or flow control, but does not affect permanent state persistence on the radio.

3. **Key Constants / Opcodes / Calls**: The function uses offsets `0x2c` and `0x1c` to access and modify integer values within the object. There are no specific hex constants, opcodes, error HRESULTs, or direct calls to other functions or COM vtable offsets visible in the provided code snippet.

4. **Next Bite**: Since this function does not directly interact with EEPROM or flash storage, the next step should be to trace the call stack and inspect the callees that use this function, particularly those that might involve operations related to EEPROM persistence or state management.

---

## 86. `PBT2.dll` — `FUN_1001d8e2` (`1001d8e2`)
- **Keywords:** has-strings
- **Strings:** `ios::eofbit set, ios::failbit set, ios::badbit set, ios::badbit set, ios::badbit set`

*(qwen2.5-coder:14b, 15.8s)*

1. **Role**: This function appears to handle exceptions and error conditions, setting specific error messages based on the state of certain flags and throwing exceptions if necessary.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more involved in error handling and state management rather than making state permanent on the radio.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x000C` (OP_UNLOCK), `0x000D` (OP_LOCK with 16-byte UUID)
   - Strings: "ios::eofbit set", "ios::failbit set", "ios::badbit set"
   - Callees: `FUN_10010f74`, `FUN_10009dc8`, `FUN_1000a0de`, `FUN_1001d97e`, `__CxxThrowException_8`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10010f74`, `FUN_10009dc8`, `FUN_1000a0de`, and `FUN_1001d97e`, as they may contain logic related to state management or error handling that could be indirectly related to making state permanent on the radio.

---

## 87. `PBT2.dll` — `FUN_1001dc62` (`1001dc62`)
- **Keywords:** has-strings
- **Strings:** `invalid ios::iword/pword index, invalid ios::iword/pword index, invalid ios::iword/pword index`

*(qwen2.5-coder:14b, 18.6s)*

1. **Role**: This function appears to manage a linked list of entries, possibly related to configuration or state management within the radio's software. It handles cases where an entry with a specific index (`iVar1`) is not found and creates a new one if necessary.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper or configuration management function that may be involved in preparing or managing data before it is written to persistent storage. It does not explicitly handle commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**:
   - `0x18` offset used to access a pointer in the `extraout_ECX` structure.
   - `0x10` size used in `operator_new` to allocate memory for a new entry.
   - `"invalid ios::iword/pword index"` error string.
   - `FUN_10010f74`, `FUN_10009dc8`, `FUN_1000a0de`, `FUN_1001d97e`, `FUN_10020442` are called within the function.
   - `__CxxThrowException_8` is used for exception handling.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10010f74`, `FUN_1001d97e`, and `FUN_10020442`, as they are called within the function and may involve more direct interactions with the radio's persistent storage.

---

## 88. `PBT2.dll` — `FUN_1001ddfb` (`1001ddfb`)
- **Keywords:** has-strings
- **Strings:** `string too long, string too long, string too long`

*(qwen2.5-coder:14b, 13.8s)*

1. **Role**: This function appears to handle an error condition by preparing and throwing an exception with the message "string too long". It involves copying a string, setting up an exception object, and then throwing it.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanisms. It seems to be a utility function for error handling.

3. **Key Constants / Opcodes / Calls**:
   - String: "string too long"
   - Calls: `FUN_10010f74`, `FUN_10009dc8`, `FUN_1000a0de`, `FUN_1001de55`, `__CxxThrowException_8`
   - Offsets: `-0x20`, `-0xd`, `-4`, `-0x3c`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10010f74`, `FUN_10009dc8`, `FUN_1000a0de`, and `FUN_1001de55`, as they may contain the actual logic related to EEPROM operations or state persistence.

---

## 89. `PBT2.dll` — `FUN_1001e027` (`1001e027`)
- **Keywords:** has-strings
- **Strings:** `invalid string position, invalid string position, invalid string position`

*(qwen2.5-coder:14b, 14.8s)*

1. **Role**: This function appears to handle an error condition by setting up an exception with the message "invalid string position" and then throwing it. It seems to be part of error handling logic within the application.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanisms. It is more likely involved in error handling and reporting.

3. **Key Constants / Opcodes / Calls**:
   - String: "invalid string position"
   - Function calls: `FUN_10010f74`, `FUN_10009dc8`, `FUN_1000a0de`, `FUN_1001de55`, `__CxxThrowException_8`
   - Pointer: `&PTR_LAB_1002e500`
   - Data reference: `&DAT_100318c8`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10010f74`, `FUN_10009dc8`, `FUN_1000a0de`, and `FUN_1001de55`, as they may contain logic related to error handling or state management that could be indirectly related to EEPROM persistence.

---

## 90. `PBT2.dll` — `FUN_1001f2e9` (`1001f2e9`)
- **Keywords:** has-strings
- **Strings:** `0123456789abcdefABCDEF`

*(qwen2.5-coder:14b, 26.4s)*

1. **Role**: This function appears to process and validate input data, possibly related to configuration or state changes for a radio device. It involves checking and manipulating strings, handling different character sets, and performing conditional operations based on input values.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to be involved in preparing data for persistence by validating and transforming input strings. It may be part of a larger process where other functions handle the actual commit to EEPROM or flash.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x0100`, `0x0101`, `0x0102`, `0x0103`, `0x0106`, `0x0107`, `0x000C`, `0x000D`, `0x0012`
   - Strings: `"0123456789abcdefABCDEF"`
   - Function calls: `FUN_10010f74`, `FUN_1000baf5`, `FUN_10024827`, `FUN_1001fcac`, `FUN_1001f9b0`, `FUN_10009dc8`, `FUN_1001f96a`, `FUN_10009d9c`, `FUN_10009bba`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1001fcac` and `FUN_1001f9b0`. These functions are called multiple times within the code and may handle the actual data processing or state changes that eventually lead to committing data to EEPROM or flash.

---

## 91. `PBT2.dll` — `Peek` (`1001f9d2`)
- **Keywords:** named

*(qwen2.5-coder:14b, 14.9s)*

1. **Role**: The `Peek` function appears to be a method within a stream buffer iterator class, likely used to retrieve the next character from the input stream without advancing the iterator. It checks if the stream pointer is valid, retrieves the next character, and updates the iterator state accordingly.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistent storage mechanisms. It is more likely a utility function for stream handling, possibly used in the context of data transmission or processing.

3. **Key Constants / Opcodes / Calls**: 
   - `FUN_1000a71e`: A function pointer or offset that retrieves the next character from the stream.
   - `0xffffffff`: An error code indicating the end of the stream or an invalid state.
   - `*(char *)((int)param_1 + 5)`: The location where the retrieved character is stored.
   - `*(undefined1 *)(param_1 + 1) = 1`: Sets a flag indicating the end of the stream.

4. **Next Bite**: The next callee to inspect for EEPROM persistence would be `FUN_1000a71e`, as it is responsible for retrieving the next character from the stream. This function might interact with the underlying data source, which could involve persistent storage operations.

---

## 92. `PBT2.dll` — `FUN_1001f9f6` (`1001f9f6`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 19.2s)*

1. **Role**: This function appears to handle locale-related initialization and error handling. It checks for locale facets, throws exceptions if missing, and initializes locale-specific data structures.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more focused on locale initialization and error management.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `__CxxThrowException_8`, `operator_new`, `FUN_1001ea2d`, `FUN_1001eae6`, `FUN_1001fceb`
   - Data references: `DAT_10037d30`, `DAT_10030a98`, `DAT_10037d40`
   - Pointers: `PTR_LAB_1002e664`, `PTR_FUN_1002e608`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1001e175`, `FUN_1001e1cb`, `FUN_1001ea2d`, and `FUN_1001eae6`. These functions might have deeper interactions with the radio's storage mechanisms.

---

## 93. `PBT2.dll` — `FUN_10020442` (`10020442`)
- **Keywords:** has-strings
- **Strings:** `bad allocation`

*(qwen2.5-coder:14b, 18.1s)*

1. **Role**: This function appears to handle an error condition, specifically a "bad allocation" scenario. It sets a flag, logs the error, and throws an exception.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage to make state permanent. It seems to be more of a transport helper function that handles error conditions.

3. **Key Constants / Opcodes / Calls**:
   - `DAT_10037d58 & 1`: Checks a flag.
   - `DAT_10037d58 | 1`: Sets a flag.
   - `FUN_1002048d(&DAT_10037d60,"bad allocation")`: Logs the error message "bad allocation".
   - `FUN_10010adc(0x10020502)`: Calls another function with a specific address.
   - `FUN_100204ea(local_10,0x10037d60)`: Calls another function with a local buffer and a specific address.
   - `__CxxThrowException_8(local_10,&DAT_10031dd8)`: Throws an exception.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1002048d`, `FUN_10010adc`, and `FUN_100204ea`. These functions might contain more detailed logic related to error handling, logging, or other transport mechanisms that could indirectly affect state persistence.

---

## 94. `PBT2.dll` — `FUN_10021e15` (`10021e15`)
- **Keywords:** has-strings
- **Strings:** `%.0Lf`

*(qwen2.5-coder:14b, 21.0s)*

1. **Role**: This function appears to handle the formatting and conversion of a double-precision floating-point number into a string, possibly for display or logging purposes. It also involves some conditional logic based on the value of the double and interacts with other functions to perform additional operations.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be more of a helper function for data formatting and conversion, which might be part of a larger process that ultimately affects EEPROM persistence. The function does not explicitly call any known opcodes for EEPROM operations like commit, lock, or unlock.

3. **Key Constants / Opcodes / Calls**:
   - `0x30` (hex constant used in `FUN_10020401` call)
   - `0x20` (offset used to access a double-precision floating-point number)
   - `0x10` (offset used to access an integer)
   - `0x8c` (offset used for a stack buffer)
   - `FUN_10010f74`, `FUN_100106d3`, `FUN_10011f77`, `FUN_10020401`, `FUN_10010612`, `FUN_10024595`, `FUN_10023ca6` (callees)
   - `DAT_1002d504` (global data reference)

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10024595` and `FUN_10023ca6`, as they are the last two functions called in the sequence and might involve more direct interactions with the radio's storage or state management.

---

## 95. `PBT2.dll` — `~ctype<>` (`1002241f`)
- **Keywords:** named

*(qwen2.5-coder:14b, 12.0s)*

1. **Role**: This function is a destructor for a `std::ctype` object, responsible for cleaning up resources associated with the object. It sets a pointer to a function and conditionally calls another function if a specific condition is met.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. It appears to be a transport helper function, possibly managing resources related to the communication protocol.

3. **Key Constants / Opcodes / Calls**: 
   - `PTR_FUN_1002e7ec`: A pointer to a function.
   - `param_1[5]`: A condition checked in the code.
   - `FUN_10010949`: A function called conditionally.
   - `PTR_LAB_1002e538`: Another pointer to a function.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_10010949`, as it is conditionally called and may contain logic related to resource management or state persistence.

---

## 96. `PBT2.dll` — `~time_put<>` (`1002245b`)
- **Keywords:** named

*(qwen2.5-coder:14b, 13.4s)*

1. **Role**: This function appears to be a destructor for a `std::time_put` object, which is responsible for formatting and outputting time-related data to an output stream. It cleans up resources associated with the object.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that manages resources related to time formatting, possibly in the context of data transmission or logging.

3. **Key Constants / Opcodes / Calls**: 
   - `PTR_FUN_1002e6b8`: A pointer to a function, possibly related to resource cleanup.
   - `FUN_10010949`: A function call that takes a pointer to a `LPVOID` parameter, which could be related to resource management or cleanup.
   - `PTR_LAB_1002e538`: A pointer to a label, possibly indicating a state or transition in the cleanup process.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_10010949`, as it is directly called within the function and could be responsible for managing resources or states related to data persistence.

---

## 97. `PBT2.dll` — `FUN_1002263a` (`1002263a`)
- **Keywords:** has-strings
- **Strings:** `0123456789abcdefABCDEF`

*(qwen2.5-coder:14b, 26.5s)*

1. **Role**: This function appears to handle state management and synchronization between the host and the radio, likely involving data transfer and validation processes.

2. **EEPROM / Persistence Mechanism**: The function manipulates state markers and checks for specific conditions to determine if changes should be committed to EEPROM. It involves locking and unlocking mechanisms, possibly to ensure data integrity during the process. The function also interacts with the radio's EEPROM through various opcodes and state transitions.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x30`, `0x2b`, `0x2d`, `0x78`, `0x58`, `0x16`, `0x10`, `0x8`, `0xe00`, `0x400`, `0x800`.
   - Opcodes: Not explicitly mentioned, but likely involves opcodes for reading, writing, and managing EEPROM state.
   - Calls: `FUN_10020401`, `FUN_10024cf6`, `FUN_1002457e`, `FUN_1002580f`, `FUN_100244f1`, `FUN_10009dc8`, `FUN_1001f96a`, `FUN_1002025d`, `_memchr`, `Peek`.

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_1002580f`, `FUN_100244f1`, and `FUN_1002025d`, as they are directly involved in state validation, commit, and possibly data manipulation processes.

---

## 98. `PBT2.dll` — `FUN_10023373` (`10023373`)
- **Keywords:** has-strings
- **Strings:** `false`

*(qwen2.5-coder:14b, 15.5s)*

1. **Role**: This function initializes a structure at the memory location pointed to by `param_1`. It sets various fields, including two short values, a 4-byte value, and two pointers to strings.

2. **EEPROM / Persistence Mechanism**: The function does not directly affect the permanent state on the radio. It appears to be a transport helper function that prepares data structures for communication.

3. **Key Constants / Opcodes / Calls**:
   - `s_false_10034ec8`: A string constant "false".
   - `DAT_10034ec0`: Another string constant.
   - `FUN_10012018()`: A function call that returns a pointer to an array of `undefined4`.
   - `FUN_10020401()`: A function called twice to set two short values.
   - `FUN_1000c18e()`: A function called to set a 4-byte value.
   - `FUN_10025704()`: A function called twice to set two pointers to strings.

4. **Next Bite**: The callees `FUN_10020401` and `FUN_1000c18e` should be inspected next to trace how the data is being prepared and potentially how it relates to the EEPROM persistence mechanism.

---

## 99. `PBT2.dll` — `FUN_1002430d` (`1002430d`)
- **Keywords:** has-strings
- **Strings:** `:Sun:Sunday:Mon:Monday:Tue:Tuesday:Wed:Wednesday:Thu:Thursday:Fri:Friday:Sat:Saturday`

*(qwen2.5-coder:14b, 13.6s)*

1. **Role**: This function appears to handle the retrieval and processing of a string, possibly related to days of the week. It checks a parameter for a non-null string, processes it, and then returns either a predefined string or a string from the parameter.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that processes strings and does not involve any direct commit, lock, unlock, or reset operations on the radio's permanent state.

3. **Key Constants / Opcodes / Calls**:
   - Referenced strings: `":Sun:Sunday:Mon:Monday:Tue:Tuesday:Wed:Wednesday:Thu:Thursday:Fri:Friday:Sat:Saturday"`
   - Callees: `FUN_10019e05`, `FUN_1000a0de`, `FUN_10010949`

4. **Next Bite**: The callees `FUN_10019e05`, `FUN_1000a0de`, and `FUN_10010949` should be inspected next to trace any potential interactions with EEPROM persistence or other state management mechanisms.

---

## 100. `PBT2.dll` — `FUN_10024353` (`10024353`)
- **Keywords:** has-strings
- **Strings:** `:Jan:January:Feb:February:Mar:March:Apr:April:May:May:Jun:June:Jul:July:Aug:August:Sep:September:Oct:October:Nov:November:Dec:December`

*(qwen2.5-coder:14b, 16.0s)*

1. **Role**: This function appears to handle the retrieval and formatting of a date string, possibly for display or logging purposes. It checks for a non-null string from a previous function call, copies it to a buffer, and then determines which date string to use based on a condition.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more of a utility function for string manipulation and does not involve any direct operations that would make state permanent on the radio.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x10`, `0x18`, `0x14`
   - Strings: `":Jan:January:Feb:February:Mar:March:Apr:April:May:May:Jun:June:Jul:July:Aug:August:Sep:September:Oct:October:Nov:November:Dec:December"`
   - Function calls: `FUN_10019e94`, `FUN_1000a0de`, `FUN_10010949`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10019e94`, `FUN_1000a0de`, and `FUN_10010949`. These functions might have more direct interactions with the radio's storage mechanisms.

---

## 101. `PBT2.dll` — `Peek` (`10024538`)
- **Keywords:** named

*(qwen2.5-coder:14b, 13.6s)*

1. **Role**: The `Peek` function appears to be a part of the input stream buffer iterator implementation, likely used to read the next character from the input stream without advancing the iterator. It checks if the input stream is valid, retrieves the next character, and updates the iterator's state accordingly.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanism. It is more of a utility function for stream handling.

3. **Key Constants / Opcodes / Calls**: 
   - `FUN_1002455f`: A function pointer or offset that is called to retrieve the next character from the input stream.
   - `*(short *)((int)param_1 + 6)`: An offset used to store the retrieved character.
   - `*(undefined1 *)(param_1 + 1) = 1`: Sets a flag indicating the end of the stream.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_1002455f`, as it is responsible for retrieving the next character from the input stream. This function might interact with the underlying data source, which could involve EEPROM or other storage mechanisms.

---

## 102. `PBT2.dll` — `FUN_10024a19` (`10024a19`)
- **Keywords:** has-strings
- **Strings:** `+v$x+v$xv$+xv+$xv$+x+$vx+$vx$v+x+$vx$+vx+v $+v $v $+v+ $v $++$ v+$ v$ v++$ v$ +v`

*(qwen2.5-coder:14b, 15.1s)*

1. **Role**: This function appears to construct a string based on input parameters and then calls another function (`FUN_100110e0`) with this string and other parameters. It seems to be part of a larger process that involves string manipulation and function calls.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It constructs a string that might be used in a subsequent operation that affects the radio's permanent state. The function's role is more indirect, likely preparing data for a command that will handle the actual persistence.

3. **Key Constants / Opcodes / Calls**:
   - String: `"+v$x+v$xv$+xv+$xv$+x+$vx+$vx$v+x+$vx$+vx+v $+v $v $+v+ $v $++$ v+$ v$ v++$ v$ +v"`
   - Offset: `0x28` (used to check a character in the `this` pointer)
   - Callee: `FUN_100110e0`

4. **Next Bite**: The next function to inspect for tracing EEPROM persistence is `FUN_100110e0`, as it is called with the constructed string and other parameters. This function is likely responsible for sending the command to the radio or handling the data further.

---

## 103. `PBT2.dll` — `FUN_10024a7a` (`10024a7a`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 18.2s)*

1. **Role**: This function appears to handle locale-related initialization and error handling. It checks for locale facets, throws exceptions if missing, and initializes a locale object if necessary.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more focused on locale settings and error management.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_10025742`, `FUN_100259c6`, `FUN_1001d8cd`
   - Global data: `DAT_10037d88`, `DAT_10034e94`, `DAT_10030a98`, `DAT_10037da0`
   - Exception handling: `__CxxThrowException_8`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10025742` and `FUN_100259c6`, as they are directly involved in the initialization of the locale object and might have deeper interactions with the radio's storage mechanisms.

---

## 104. `PBT2.dll` — `FUN_10024b3e` (`10024b3e`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 22.9s)*

1. **Role**: This function appears to handle error checking and exception handling, possibly related to locale settings or configuration. It checks for missing locale facets and throws an exception if necessary. It also manages some form of resource allocation or initialization.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be more of a transport helper or configuration management function, possibly setting up or validating state before any EEPROM operations occur.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `__CxxThrowException_8`, `operator_new`, `FUN_1001ea2d`, `FUN_1001eae6`, `FUN_10025a14`
   - Offsets: `unaff_EBP + -0x10`, `unaff_EBP + -4`, `unaff_EBP + 8`, `unaff_EBP + 0x10`, `unaff_EBP + -0x1c`, `unaff_EBP + -0xc`
   - Global variables: `DAT_10037d8c`, `DAT_10034e94`, `DAT_10030a98`, `DAT_10037da4`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10025a14` and any functions called by `FUN_1001e175` or `FUN_1001e1cb`, as these might be responsible for actual state management or configuration operations that could involve EEPROM.

---

## 105. `PBT2.dll` — `FUN_10024c1a` (`10024c1a`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 17.7s)*

1. **Role**: This function appears to handle locale-related initialization and error handling. It checks for locale settings, throws exceptions if missing, and initializes locale-specific data structures.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more focused on locale settings and error management, which are not directly related to making state permanent on the radio.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_1001ea2d`, `FUN_1001eae6`, `FUN_10025a62`
   - Data references: `DAT_10037d7c`, `DAT_10030a98`, `DAT_10037da8`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10025a62` and any functions called by `FUN_1001e175` or `FUN_1001e1cb`, as they might involve more direct interactions with the radio's storage mechanisms.

---

## 106. `PBT2.dll` — `FUN_10024cf6` (`10024cf6`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 16.8s)*

1. **Role**: This function appears to handle locale-related initialization and error handling. It checks for locale settings, allocates memory if necessary, and throws an exception if locale settings are missing.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more focused on locale settings and exception handling.

3. **Key Constants / Opcodes / Calls**:
   - String: "missing locale facet"
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_1002584e`, `FUN_10025ab0`
   - Global variables: `DAT_10037d6c`, `DAT_10037dac`, `DAT_10030a98`
   - Exception handling: `__CxxThrowException_8`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1002584e` and `FUN_10025ab0`, as they are called conditionally and might involve more direct interactions with the radio's storage.

---

## 107. `PBT2.dll` — `FUN_10024dba` (`10024dba`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 17.2s)*

1. **Role**: This function appears to handle locale-related initialization and error handling. It checks for locale settings, throws exceptions if missing, and initializes a locale object if necessary.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more focused on locale settings and error management.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_100258a7`, `FUN_10025afe`
   - Data references: `DAT_10037d80`, `DAT_10030a98`, `DAT_10037db0`, `s_missing_locale_facet_10034e94`, `PTR_LAB_1002e664`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_100258a7` and `FUN_10025afe`, as they are directly involved in the initialization process and might interact with the underlying storage mechanisms.

---

## 108. `PBT2.dll` — `FUN_10024e7e` (`10024e7e`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 16.9s)*

1. **Role**: This function appears to handle locale-related initialization and error handling. It checks for locale facets, throws exceptions if missing, and initializes a locale object if necessary.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more related to locale settings and error management.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_100258fb`, `FUN_10025b4c`
   - Global variables: `DAT_10037d74`, `DAT_10037db4`, `DAT_10030a98`
   - Exception handling: `__CxxThrowException_8`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_100258fb` and `FUN_10025b4c`, as they are involved in the initialization of the locale object and might have deeper interactions with the radio's storage mechanisms.

---

## 109. `PBT2.dll` — `FUN_10024f42` (`10024f42`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 17.5s)*

1. **Role**: This function appears to handle locale-related initialization and error handling. It checks for locale settings, throws exceptions if missing, and initializes locale-specific data structures.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more focused on locale settings and error handling, which are not directly related to making state permanent on the radio.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_1001ea2d`, `FUN_1001eae6`, `FUN_10025b9a`
   - Data references: `DAT_10037d70`, `DAT_10030a98`, `DAT_10037db8`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1001e175`, `FUN_1001e1cb`, and `FUN_10025b9a`. These functions might have deeper interactions with the radio's storage mechanisms.

---

## 110. `PBT2.dll` — `FUN_1002501e` (`1002501e`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 15.3s)*

1. **Role**: This function appears to handle locale-related initialization and error handling. It checks for locale settings, throws exceptions if missing, and initializes locale-related data structures.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more focused on locale settings and error management, which are not directly related to making state permanent on the radio.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `__CxxThrowException_8`, `operator_new`, `FUN_1001ea2d`, `FUN_1001eae6`, `FUN_1001d8cd`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1001e175` and `FUN_1001e1cb`, as they are involved in locale checks and might indirectly affect state persistence through locale settings.

---

## 111. `PBT2.dll` — `FUN_100250fa` (`100250fa`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 18.2s)*

1. **Role**: This function appears to handle locale-related initialization and error handling. It checks for locale settings, throws exceptions if missing, and initializes locale-specific data structures.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more focused on locale settings and error management.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_10025dbc`, `FUN_10025c36`
   - Global data: `DAT_10037d98`, `DAT_10037dc0`, `s_missing_locale_facet_10034e94`, `PTR_LAB_1002e664`, `DAT_10030a98`, `PTR_FUN_1002e710`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10025dbc` and `FUN_10025c36`, as they are directly involved in initializing locale-specific data structures and might have deeper interactions with the underlying storage mechanisms.

---

## 112. `PBT2.dll` — `FUN_100251c9` (`100251c9`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 17.9s)*

1. **Role**: This function appears to handle error checking and exception handling, possibly related to locale settings or configuration. It checks for missing locale facets and throws an exception if necessary.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more involved in error handling and configuration checks rather than state persistence mechanisms.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_10025dbc`, `FUN_10025c84`
   - Data references: `DAT_10037d78`, `DAT_10030a98`, `DAT_10037dc4`
   - Pointers: `PTR_LAB_1002e664`, `PTR_FUN_1002e6e4`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10025dbc` and `FUN_10025c84`, as they are directly invoked within the function and might contain more detailed logic related to state persistence or configuration.

---

## 113. `PBT2.dll` — `FUN_10025298` (`10025298`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 17.2s)*

1. **Role**: This function appears to handle locale-related initialization and error handling. It checks for locale settings, throws an exception if missing, and initializes a locale object if necessary.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more focused on locale settings and error handling, which are not directly related to making state permanent on the radio.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_1002596d`, `FUN_10025cd2`
   - Global variables: `DAT_10037d84`, `DAT_10037dc8`, `DAT_10030a98`, `PTR_LAB_1002e664`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1002596d` and `FUN_10025cd2`, as they are called conditionally and might involve more direct interactions with the radio's storage.

---

## 114. `PBT2.dll` — `FUN_1002535c` (`1002535c`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 17.9s)*

1. **Role**: This function appears to handle error checking and exception handling, possibly related to locale settings or configuration. It checks for missing locale facets and throws an exception if necessary. It also manages memory allocation and initialization for a specific object.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be more of a transport helper or configuration management function, possibly involved in setting up or validating state before any EEPROM operations occur.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_100257a2`, `FUN_10025d20`
   - Global variables: `DAT_10037d94`, `DAT_10037dcc`, `DAT_10030a98`, `PTR_LAB_1002e664`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_100257a2` and `FUN_10025d20`, as they are called conditionally and might involve more direct interactions with the radio's storage.

---

## 115. `PBT2.dll` — `FUN_10025420` (`10025420`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 17.5s)*

1. **Role**: This function appears to handle locale-related initialization and error handling. It checks for locale settings, throws exceptions if missing, and initializes a locale object if necessary.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more focused on locale settings and error management.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_100254e4`, `FUN_10025d6e`
   - Global data: `DAT_10037d90`, `DAT_10037dd0`, `s_missing_locale_facet_10034e94`, `DAT_10030a98`, `PTR_LAB_1002e664`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_100254e4` and `FUN_10025d6e`, as they are called conditionally and might involve more direct interactions with the radio's storage.

---

## 116. `PBT2.dll` — `FUN_100268d9` (`100268d9`)
- **Keywords:** has-strings
- **Strings:** `%.0Lf`

*(qwen2.5-coder:14b, 17.9s)*

1. **Role**: This function appears to handle some form of data processing and formatting, possibly related to a timer or countdown mechanism. It manipulates a double value, formats it into a string, and then performs some operations on it.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that formats data for transmission or further processing. It does not explicitly commit changes to EEPROM or handle lock/unlock mechanisms.

3. **Key Constants / Opcodes / Calls**:
   - `0x1002d770` and `0x1002e838` are addresses of global variables.
   - `0x1002e830` is a multiplier used in a calculation.
   - `FUN_10010f74`, `FUN_10009dc8`, `FUN_10011f77`, `FUN_10009bba`, `FUN_10009c13`, and `FUN_1002791c` are function calls within the code.
   - The string `"%.0Lf"` is used in formatting a double value.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10011f77` and `FUN_10009c13`, as they handle string formatting and data transmission, which could be related to committing changes to the radio's permanent storage.

---

## 117. `PBT2.dll` — `~time_put<>` (`10027010`)
- **Keywords:** named

*(qwen2.5-coder:14b, 13.8s)*

1. **Role**: This function appears to be a destructor for a `std::time_put` object, responsible for cleaning up resources associated with time formatting in output streams. It sets pointers to specific functions and calls another function (`FUN_10010949`) with a parameter derived from the input pointer.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function, possibly involved in managing the state of the output stream or related resources, but not directly responsible for making state permanent on the radio.

3. **Key Constants / Opcodes / Calls**: 
   - `PTR_FUN_1002e9b8`: A pointer to a function.
   - `FUN_10010949`: A function call with a parameter derived from the input pointer.
   - `PTR_LAB_1002e538`: Another pointer to a function or label.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_10010949`. This function call is likely where the actual resource cleanup or state management occurs, and it may have more direct interactions with the radio's storage mechanisms.

---

## 118. `PBT2.dll` — `FUN_10028209` (`10028209`)
- **Keywords:** has-strings
- **Strings:** `+v$x+v$xv$+xv+$xv$+x+$vx+$vx$v+x+$vx$+vx+v $+v $v $+v+ $v $++$ v+$ v$ v++$ v$ +v`

*(qwen2.5-coder:14b, 15.8s)*

1. **Role**: This function appears to construct a string based on input parameters and then calls another function (`FUN_100110e0`) with this string and other parameters. It seems to be part of a larger process involving state management or communication with the radio.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it constructs a string that might be used in a communication protocol to manage state persistence on the radio. The actual persistence mechanism would likely be handled by other functions or opcodes not shown here.

3. **Key Constants / Opcodes / Calls**:
   - String: `"+v$x+v$xv$+xv+$xv$+x+$vx+$vx$v+x+$vx$+vx+v $+v $v $+v+ $v $++$ v+$ v$ v++$ v$ +v"`
   - Offset: `0x28`
   - Callee: `FUN_100110e0`
   - Parameters: `param_1`, `param_2`, `param_3`, `param_4`

4. **Next Bite**: The next function to inspect for tracing EEPROM persistence is `FUN_100110e0`, as it is called with the constructed string and other parameters. This function likely handles the actual communication or processing that could involve state persistence on the radio.

---

## 119. `PBT2.dll` — `FUN_1002826a` (`1002826a`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 18.0s)*

1. **Role**: This function appears to handle locale-related initialization and error handling. It checks for locale settings, throws an exception if missing, and initializes a locale object if necessary.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more focused on locale settings and error management.

3. **Key Constants / Opcodes / Calls**:
   - String: "missing locale facet"
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_100288d0`, `FUN_10028a5c`, `FUN_1001d8cd`
   - Data references: `DAT_10037e24`, `DAT_10037e28`, `s_missing_locale_facet_10034e94`, `PTR_LAB_1002e664`, `DAT_10030a98`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_100288d0` and `FUN_10028a5c`, as they are called conditionally and might involve more direct interactions with the radio's storage.

---

## 120. `PBT2.dll` — `FUN_1002832e` (`1002832e`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 18.0s)*

1. **Role**: This function appears to handle locale-related initialization and error handling. It checks for locale settings, throws an exception if missing, and initializes a locale object if necessary.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more focused on locale settings and error management.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_10028924`, `FUN_10028aaa`, `FUN_1001d8cd`
   - Global data: `DAT_10037e18`, `DAT_10037e2c`, `DAT_10030a98`, `s_missing_locale_facet_10034e94`, `PTR_LAB_1002e664`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10028924` and `FUN_10028aaa`, as they are called conditionally and might involve more direct interactions with the radio's storage.

---

## 121. `PBT2.dll` — `FUN_100283f2` (`100283f2`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 19.1s)*

1. **Role**: This function appears to handle locale-related initialization and error handling. It checks for locale settings, throws exceptions if missing, and initializes locale-specific data structures.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more focused on locale settings and error handling, which are not directly related to making state permanent on the radio.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_1001ea2d`, `FUN_1001eae6`, `FUN_10028af8`, `FUN_1001d8cd`
   - Data references: `DAT_10037e20`, `DAT_10037e30`, `s_missing_locale_facet_10034e94`, `PTR_LAB_1002e664`, `DAT_10030a98`, `PTR_FUN_1002ea4c`

4. **Next Bite**: The function `FUN_10028af8` should be inspected next to trace any potential interactions with EEPROM persistence, as it is called conditionally based on the locale initialization.

---

## 122. `PBT2.dll` — `FUN_100284ce` (`100284ce`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 19.8s)*

1. **Role**: This function appears to handle error checking and exception handling, possibly related to locale settings or configuration. It checks for missing locale facets and throws an exception if necessary. It also manages some kind of resource allocation or initialization.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be more of a transport helper or configuration management function, possibly setting up state or resources needed for subsequent operations that might affect EEPROM persistence.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `__CxxThrowException_8`, `operator_new`, `FUN_1001ea2d`, `FUN_1001eae6`, `FUN_10028b46`
   - Global data: `DAT_10037e08`, `DAT_10030a98`, `DAT_10037e34`
   - Pointer: `PTR_LAB_1002e664`, `PTR_FUN_1002ea3c`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10028b46` and any functions called by `FUN_1001eae6`, as these might be responsible for setting up or committing state changes that affect EEPROM persistence.

---

## 123. `PBT2.dll` — `FUN_100285aa` (`100285aa`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 19.0s)*

1. **Role**: This function appears to handle locale-related initialization and error handling. It checks for locale settings, throws an exception if missing, and initializes a locale object if necessary.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more focused on locale settings and exception handling, which are not directly related to making state permanent on the radio.

3. **Key Constants / Opcodes / Calls**:
   - String: "missing locale facet"
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_10028ccc`, `FUN_10028b94`
   - Global data: `DAT_10037e1c`, `DAT_10037e38`, `s_missing_locale_facet_10034e94`, `PTR_LAB_1002e664`, `DAT_10030a98`, `PTR_FUN_1002ea10`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10028ccc` and `FUN_10028b94`, as they are directly involved in the initialization of the locale object and might have deeper interactions with the radio's storage mechanisms.

---

## 124. `PBT2.dll` — `FUN_10028679` (`10028679`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 18.1s)*

1. **Role**: This function appears to handle error checking and exception handling, possibly related to locale settings or configuration. It checks for missing locale facets and throws an exception if necessary.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more focused on configuration and error handling rather than state persistence mechanisms.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_10028ccc`, `FUN_10028be2`
   - Data references: `DAT_10037e0c`, `DAT_10037e3c`, `s_missing_locale_facet_10034e94`, `PTR_LAB_1002e664`, `DAT_10030a98`, `PTR_FUN_1002e9e4`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10028ccc` and `FUN_10028be2`, as they are directly involved in creating and managing an object that might be related to state persistence.

---

## 125. `PBT2.dll` — `FUN_10028748` (`10028748`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 17.4s)*

1. **Role**: This function appears to handle locale-related initialization and error handling. It checks for locale settings, throws exceptions if missing, and initializes a locale object if necessary.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more focused on locale settings and error handling, which are not directly related to making state permanent on the radio.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_10028996`, `FUN_10028c30`
   - Global variables: `DAT_10037e10`, `DAT_10037e40`, `DAT_10030a98`
   - Exception handling: `__CxxThrowException_8`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10028996` and `FUN_10028c30`, as they are called conditionally and might involve more direct interactions with the radio's storage mechanisms.

---

## 126. `PBT2.dll` — `FUN_1002880c` (`1002880c`)
- **Keywords:** has-strings
- **Strings:** `missing locale facet`

*(qwen2.5-coder:14b, 17.5s)*

1. **Role**: This function appears to handle locale-related initialization and error handling. It checks for locale facets, throws exceptions if missing, and initializes a locale object if necessary.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more focused on locale settings and error management.

3. **Key Constants / Opcodes / Calls**:
   - String: `"missing locale facet"`
   - Function calls: `FUN_10010f74`, `FUN_1001d831`, `FUN_1000a9b4`, `FUN_1001e175`, `FUN_1001e1cb`, `FUN_10011e4e`, `operator_new`, `FUN_100289ef`, `FUN_10028c7e`
   - Global data: `DAT_10037e14`, `DAT_10037e44`, `s_missing_locale_facet_10034e94`, `DAT_10030a98`, `PTR_LAB_1002e664`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_100289ef` and `FUN_10028c7e`, as they are called conditionally and might involve more direct interactions with the radio's storage.

---

## 127. `RemoteProtocols01.dll` — `FID_conflict:_AfxIsEqualGUID` (`100015b0`)
- **Keywords:** named

*(qwen2.5-coder:14b, 12.3s)*

1. **Role**: This function checks if two GUIDs (Globally Unique Identifiers) are equal by comparing their individual components (Data1, Data2, Data3, and Data4).

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with EEPROM or manage state persistence on the radio. It is a utility function used for GUID comparison, which is likely part of a larger mechanism for ensuring data integrity or managing session states.

3. **Key Constants / Opcodes / Calls**: The function does not contain any specific hex constants, opcodes, error HRESULTs, or direct calls to other functions that are directly related to EEPROM or state persistence. It focuses solely on comparing the fields of two GUID structures.

4. **Next Bite**: Since this function is a GUID comparison utility, the next step should be to trace how it is used within the larger context of the application. Look for calls to this function in other parts of the codebase, particularly in functions that handle session management, security, or data transactions, as these are more likely to involve interactions with EEPROM or state persistence mechanisms.

---

## 128. `RemoteProtocols01.dll` — `~CComBSTR` (`10001920`)
- **Keywords:** named

*(qwen2.5-coder:14b, 10.9s)*

1. **Role**: The `~CComBSTR` function is a destructor for the `CComBSTR` class in the ATL (Active Template Library) library. It releases the memory allocated for a BSTR (Basic String) object by calling `SysFreeString`.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It is a memory management function that helps in freeing resources, which is an indirect transport helper.

3. **Key Constants / Opcodes / Calls**: The function calls `SysFreeString`, which is a Windows API function to free a BSTR. There are no specific hex constants, offsets, error HRESULTs, or other callees (`FUN_*` / COM vtable offsets) observed in the provided code snippet.

4. **Next Bite**: Since this function is primarily a memory management function, there is no specific callee related to EEPROM persistence to inspect next. The focus should be on other functions that handle EEPROM operations or state management.

---

## 129. `RemoteProtocols01.dll` — `Clear` (`10003350`)
- **Keywords:** named

*(qwen2.5-coder:14b, 12.1s)*

1. **Role**: The `Clear` function checks if a pointer (`param_1`) is not null. If it's not null, it calls another function (`FUN_100033f0`) with the pointer's value and then sets the pointer to null. This function is likely used to clean up or reset a resource.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly interact with EEPROM or flash storage. It appears to be a transport helper function that manages resource cleanup, which could be part of a larger process that affects state persistence on the radio.

3. **Key Constants / Opcodes / Calls**: 
   - The function checks if `*param_1` is not null.
   - It calls `FUN_100033f0` with the pointer's value.
   - It sets `*param_1` to null after the call.

4. **Next Bite**: The next callee to inspect is `FUN_100033f0` to understand how it contributes to the resource cleanup and potentially affects state persistence on the radio.

---

## 130. `RemoteProtocols01.dll` — `QueryInterface` (`10003b90`)
- **Keywords:** named

*(qwen2.5-coder:14b, 12.0s)*

1. **Role**: The `QueryInterface` function is a standard COM method used to query an object for the interfaces it supports. It checks if the requested interface is supported and returns a pointer to it if available.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly affect the permanent state on the radio. It is a transport helper function used to manage COM interface queries, which is part of the communication protocol but does not involve direct EEPROM operations like commit, lock/unlock, or reset.

3. **Key Constants / Opcodes / Calls**: 
   - The function calls `ATL::CAccessibleProxy::_InternalQueryInterface`, which is a COM internal method for querying interfaces.
   - No specific hex constants, offsets, error HRESULTs, or direct EEPROM-related opcodes are observed in the provided code snippet.

4. **Next Bite**: To trace EEPROM persistence, the next callee to inspect should be `ATL::CAccessibleProxy::_InternalQueryInterface`. This method is responsible for handling the actual interface querying and might involve deeper COM interactions that could be related to EEPROM operations.

---

## 131. `RemoteProtocols01.dll` — `~CAccessibleProxy` (`10004130`)
- **Keywords:** named

*(qwen2.5-coder:14b, 11.2s)*

1. **Role**: The function `~CAccessibleProxy` is a destructor for the `CAccessibleProxy` class. It is responsible for cleaning up resources associated with an instance of this class.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. It appears to be a transport helper function that manages the lifecycle of an object, possibly related to communication protocols.

3. **Key Constants / Opcodes / Calls**: 
   - The function checks if `this` is `NULL` and adjusts the pointer to `local_c` accordingly.
   - It calls `FUN_10004350` with the adjusted pointer, which is likely a cleanup or finalization routine.

4. **Next Bite**: The next callee to inspect is `FUN_10004350` to understand how it handles the cleanup or finalization of the `CAccessibleProxy` object, as it may involve interactions with the radio's state or communication protocols.

---

## 132. `RemoteProtocols01.dll` — `SafeRWList<>` (`100042c0`)
- **Keywords:** named

*(qwen2.5-coder:14b, 14.4s)*

1. **Role**: The `SafeRWList` function initializes a thread-safe list structure, likely used for managing concurrent access to a collection of objects. It sets up a critical section and calls two other functions to perform additional initialization.

2. **EEPROM / Persistence Mechanism**: This function is a transport helper. It does not directly affect the permanent state on the radio (EEPROM/flash commit, host markers, lock/unlock, reset, etc.). Instead, it ensures thread safety for operations that might involve these persistent states.

3. **Key Constants / Opcodes / Calls**: 
   - `FUN_10008610`: This function is called first, possibly for initializing the list structure.
   - `FUN_10004160`: This function is called second, likely for initializing a critical section at `param_1 + 1`.
   - No specific hex constants, opcodes, or error HRESULTs are directly observed in the provided code snippet.

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_10008610` and `FUN_10004160`. These functions are responsible for the actual initialization and might contain calls to other functions that handle EEPROM persistence or related operations.

---

## 133. `RemoteProtocols01.dll` — `QueryInterface` (`10004570`)
- **Keywords:** named

*(qwen2.5-coder:14b, 11.7s)*

1. **Role**: The `QueryInterface` function is a standard COM method used to query an object for the interfaces it supports. It checks if the requested interface is supported and returns a pointer to it if available.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly affect the permanent state on the radio. It is a transport helper function used to manage COM interface queries, which is part of the communication protocol but not directly involved in EEPROM commit or lock/unlock operations.

3. **Key Constants / Opcodes / Calls**: 
   - The function calls `ATL::CAccessibleProxy::_InternalQueryInterface`, which is a COM internal method for querying interfaces.
   - No specific hex constants, offsets, error HRESULTs, or direct EEPROM-related opcodes are observed in the provided code snippet.

4. **Next Bite**: To trace EEPROM persistence, the next callee to inspect should be `ATL::CAccessibleProxy::_InternalQueryInterface`. This method is responsible for handling the actual interface querying and might involve deeper COM operations that could be related to EEPROM persistence.

---

## 134. `RemoteProtocols01.dll` — `InlineIsEqualUnknown` (`10004770`)
- **Keywords:** named

*(qwen2.5-coder:14b, 11.5s)*

1. **Role**: This function checks if a given GUID is equal to the GUID for the `IUnknown` interface. It returns 1 if they are equal, otherwise 0.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly affect the permanent state on the radio. It is likely used for interface identification and does not involve EEPROM commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**: 
   - GUID comparison constants: `0x00000000`, `0x0000`, `0x0000`, `0xc0`, `0x46000000`.

4. **Next Bite**: Since this function is primarily for interface identification, the next step should be to trace calls to other functions that might involve EEPROM persistence, such as those handling opcodes like `0x0106` (EnterMode/Session) or `0x0107` (UnlockSecurity).

---

## 135. `RemoteProtocols01.dll` — `ConnectToConnectionPoint` (`100047c0`)
- **Keywords:** named

*(qwen2.5-coder:14b, 13.1s)*

1. **Role**: The `ConnectToConnectionPoint` function is a method of the `CDHtmlEventSink` class that appears to delegate the task of connecting to a connection point to another function, `FUN_10007f40`. It takes parameters including an `IUnknown` pointer, a GUID, and a pointer to an unsigned long.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly handle EEPROM persistence or state commitment. It is more of a transport helper function that delegates the actual connection logic to another function.

3. **Key Constants / Opcodes / Calls**: The function calls `FUN_10007f40` with the `this` pointer, `IUnknown` pointer (`param_1`), GUID pointer (`param_2`), and a pointer to an unsigned long (`param_3`). There are no specific hex constants, opcodes, or error HRESULTs directly visible in the provided code snippet.

4. **Next Bite**: To trace EEPROM persistence, the next callee to inspect is `FUN_10007f40`. This function is likely where the actual connection logic, including any EEPROM persistence mechanisms, is handled.

---

## 136. `RemoteProtocols01.dll` — `QueryInterface` (`100048d0`)
- **Keywords:** named

*(qwen2.5-coder:14b, 11.6s)*

1. **Role**: The `QueryInterface` function is a standard COM method used to query an object for the interfaces it supports. It checks if the requested interface is supported and returns a pointer to it if available.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly affect the permanent state on the radio. It is a transport helper function used to manage COM interfaces and does not involve EEPROM commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**: 
   - The function calls `ATL::CAccessibleProxy::_InternalQueryInterface`, which is a COM internal method.
   - No specific hex constants, offsets, error HRESULTs, or opcodes are directly observed in the provided code snippet.

4. **Next Bite**: The next callee to inspect for EEPROM persistence would be `ATL::CAccessibleProxy::_InternalQueryInterface`. This method is responsible for handling the actual interface querying and might involve more detailed operations related to COM interface management, which could be indirectly related to EEPROM persistence through COM interface interactions.

---

## 137. `RemoteProtocols01.dll` — `QueryInterface` (`10004b50`)
- **Keywords:** named

*(qwen2.5-coder:14b, 12.1s)*

1. **Role**: The `QueryInterface` function is a standard COM method used to query an object for the interfaces it supports. It checks if the requested interface is supported and returns a pointer to it if available.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly affect the permanent state on the radio. It is a transport helper function used to manage COM interfaces, which is part of the communication protocol but not directly involved in EEPROM commit or lock/unlock operations.

3. **Key Constants / Opcodes / Calls**: 
   - The function calls `ATL::CAccessibleProxy::_InternalQueryInterface`, which is a COM internal method.
   - No specific hex constants, offsets, error HRESULTs, or direct EEPROM-related opcodes are observed in the provided code snippet.

4. **Next Bite**: To trace EEPROM persistence, the next callee to inspect would be `ATL::CAccessibleProxy::_InternalQueryInterface`, as it is the primary method handling the interface query logic. Further analysis of this method might reveal more about how interfaces are managed and potentially interact with the radio's EEPROM or flash storage.

---

## 138. `RemoteProtocols01.dll` — `~CAccessibleProxy` (`10004d20`)
- **Keywords:** named

*(qwen2.5-coder:14b, 12.3s)*

1. **Role**: The function `~CAccessibleProxy` is a destructor for the `CAccessibleProxy` class in the `ATL` namespace. It is responsible for cleaning up resources associated with an instance of `CAccessibleProxy`.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. It appears to be a transport helper function that manages the lifecycle of an object, possibly related to communication protocols but not directly involved in making state permanent on the radio.

3. **Key Constants / Opcodes / Calls**: 
   - The function checks if `this` is `NULL` and adjusts the pointer `local_c` accordingly.
   - It calls `FUN_10001f4b` with `local_c` as an argument. The exact behavior of this function is not clear from the provided code snippet.

4. **Next Bite**: The next callee to inspect is `FUN_10001f4b` to understand its role in the object's cleanup process and whether it interacts with the radio's EEPROM or flash memory.

---

## 139. `RemoteProtocols01.dll` — `CAsyncPropExchange` (`10004da0`)
- **Keywords:** named

*(qwen2.5-coder:14b, 15.1s)*

1. **Role**: The `CAsyncPropExchange` constructor initializes an object with a given parameter, setting up pointers to various functions and storing the parameter in an object field. It appears to be part of a larger class responsible for asynchronous property exchange.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly handle EEPROM persistence. It seems to be a transport helper or initialization function that sets up the environment for other operations that might affect EEPROM persistence.

3. **Key Constants / Opcodes / Calls**: 
   - `FUN_10009110`: A function pointer that is called during initialization.
   - `PTR_FUN_1000d684`, `PTR_LAB_1000d674`, `PTR_LAB_1000d63c`: Pointers to other functions or labels.
   - `0x14`: The offset where the parameter is stored in the object.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10009110` and the functions pointed to by `PTR_FUN_1000d684`, `PTR_LAB_1000d674`, and `PTR_LAB_1000d63c`. These functions might contain the actual logic for handling EEPROM persistence.

---

## 140. `RemoteProtocols01.dll` — `CAsyncPropExchange` (`10004ea0`)
- **Keywords:** named

*(qwen2.5-coder:14b, 13.1s)*

1. **Role**: The `CAsyncPropExchange` constructor initializes an object with a given parameter, setting up pointers to various functions and storing the parameter in an object field. It appears to be part of a larger class responsible for asynchronous property exchange.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or manage state persistence. It seems to be a transport helper function that sets up internal state for communication.

3. **Key Constants / Opcodes / Calls**:
   - `FUN_10008d70`: A function pointer that is called during initialization.
   - `PTR_FUN_1000d720`, `PTR_LAB_1000d710`, `PTR_LAB_1000d6d8`: Pointers to other functions or labels.
   - `0x14`: The offset where the parameter is stored in the object.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_10008d70`, as it is called during the initialization of the object and might contain more relevant logic for state management or communication setup.

---

## 141. `RemoteProtocols01.dll` — `CAsyncPropExchange` (`10004fa0`)
- **Keywords:** named

*(qwen2.5-coder:14b, 15.3s)*

1. **Role**: The `CAsyncPropExchange` constructor initializes an object with a given parameter, setting up pointers to various functions and storing the parameter in an object field. It appears to be part of a larger class responsible for asynchronous property exchange.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly handle EEPROM persistence. It initializes the object and sets up function pointers, which suggests it is a transport helper or part of a larger mechanism that manages state persistence indirectly.

3. **Key Constants / Opcodes / Calls**: 
   - `0x10001000`: A function pointer or offset.
   - `&PTR_FUN_1000d7bc`, `&PTR_LAB_1000d7ac`, `&PTR_LAB_1000d774`: Pointers to other functions or labels.
   - `0x14`: Offset where the parameter is stored in the object.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10001000` and the functions pointed to by `&PTR_FUN_1000d7bc`, `&PTR_LAB_1000d7ac`, and `&PTR_LAB_1000d774`. These functions may contain the actual logic for handling EEPROM persistence or further initialization steps.

---

## 142. `RemoteProtocols01.dll` — `FUN_100052e0` (`100052e0`)
- **Keywords:** has-strings
- **Strings:** `REGISTRY, REGISTRY, REGISTRY, Module`

*(qwen2.5-coder:14b, 20.6s)*

1. **Role**: This function appears to handle the registration and configuration of a module, possibly related to the radio's operation. It retrieves the module's file path, processes it, and registers it with some form of registry or configuration system.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to manage module registration and configuration, which could indirectly affect state persistence by ensuring the correct settings are applied. It does not explicitly call any functions related to EEPROM commit, lock/unlock, or reset.

3. **Key Constants / Opcodes / Calls**:
   - `0x8007000e`: HRESULT indicating an invalid argument.
   - `0x10010b40`: A data pointer used in `FUN_10005680`.
   - `0x0`: Null pointer used in several comparisons and assignments.
   - `FUN_10007dd0`, `FUN_10005680`, `FUN_10005700`, `FUN_10005740`, `FUN_10005ce0`, `FUN_10005900`: Various function calls within the function.
   - `u_REGISTRY_1000f9c0`: A constant used in registry operations.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10005ce0` and `FUN_10005900`, as they are conditionally called based on the `param_3` value and could potentially handle the actual registration or configuration that affects state persistence.

---

## 143. `RemoteProtocols01.dll` — `FUN_100059d0` (`100059d0`)
- **Keywords:** has-strings
- **Strings:** `Failed to LoadResource 
, Failed to FindResource on ID:%s TYPE:%s
, Failed to FindResource on ID:%s TYPE:%s
, Failed to FindResource on ID:%d TYPE:%s
, Failed to FindResource on ID:%d TYPE:%s
, Failed to LoadLibrary on %s
`

*(qwen2.5-coder:14b, 19.7s)*

1. **Role**: This function appears to load a library, find a resource within that library, and then process that resource. It handles errors related to loading the library and finding the resource, returning an error code if something goes wrong.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. It seems to be a transport helper function that loads resources, which could be used by other functions to manage the radio's state. It does not explicitly handle commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**:
   - `LoadLibraryExA` and `FreeLibrary` for loading and freeing the library.
   - `FindResourceA` and `LoadResource` for finding and loading the resource.
   - `SizeofResource` to get the size of the resource.
   - `FUN_10005e10`, `FUN_10009aa0`, `FUN_10005980`, `FUN_10009760`, `FUN_10005cc0`, and `FUN_10005e40` are other functions called within this function.
   - Error handling using `GetLastError` and returning HRESULTs.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10005e40` and `FUN_10005cc0`, as they are directly involved in processing the resource after it is loaded. These functions might contain the logic for interacting with the radio's EEPROM or handling state persistence.

---

## 144. `RemoteProtocols01.dll` — `FUN_10005e40` (`10005e40`)
- **Keywords:** has-strings
- **Strings:** `Failed to register, cleaning up!
, Syntax error, expecting a {, found a %s
, HKeyFromString failed on %s
`

*(qwen2.5-coder:14b, 15.9s)*

1. **Role**: This function appears to parse a configuration string and register settings with a COM object, handling errors and cleaning up resources if registration fails.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. It seems to be a transport helper that interacts with COM objects to manage settings, possibly indirectly affecting state persistence through COM method calls.

3. **Key Constants / Opcodes / Calls**:
   - Strings: "Failed to register, cleaning up!\n", "Syntax error, expecting a {, found a %s\n", "HKeyFromString failed on %s\n"
   - Calls: `FUN_10009aa0`, `FUN_10006430`, `FUN_100061e0`, `FUN_100060f0`, `FUN_100060d0`, `FUN_10006960`, `FUN_10006140`, `CoTaskMemFree`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10006960` and `FUN_10006140`, as they are directly involved in processing the configuration strings and interacting with COM objects, which could potentially affect state persistence.

---

## 145. `RemoteProtocols01.dll` — `FUN_100061e0` (`100061e0`)
- **Keywords:** has-strings
- **Strings:** `NextToken : Unexpected End of File
`

*(qwen2.5-coder:14b, 18.9s)*

1. **Role**: This function appears to parse and process a string input, possibly extracting tokens or data from a command or configuration string. It handles different cases based on the initial character of the input string and processes subsequent characters until a delimiter or end of string is reached.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that processes input data but does not explicitly handle commit, lock, unlock, or reset operations related to EEPROM persistence. The function might be part of a larger process where such operations are handled elsewhere.

3. **Key Constants / Opcodes / Calls**:
   - `CharNextA`: Used to move to the next character in the string.
   - `FUN_10006140`, `FUN_100060d0`, `FUN_100063e0`, `FUN_10006180`: These are other functions called within this function, possibly for parsing or processing specific parts of the input string.
   - `'\'`: Used as a delimiter in the input string processing.
   - `0x1000`: An offset used in pointer arithmetic to ensure buffer bounds are not exceeded.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10006140`, `FUN_100060d0`, `FUN_100063e0`, and `FUN_10006180`. These functions might contain the actual logic for handling EEPROM operations or might call other functions that do.

---

## 146. `RemoteProtocols01.dll` — `FUN_10006430` (`10006430`)
- **Keywords:** has-strings
- **Strings:** `Error no closing % found
`

*(qwen2.5-coder:14b, 18.7s)*

1. **Role**: This function processes a string input, handling '%' characters to replace them with corresponding values, and appears to be part of a larger image processing or data manipulation routine.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that processes strings and possibly prepares data for transmission or further processing, but does not handle the actual commit or locking of state on the radio.

3. **Key Constants / Opcodes / Calls**:
   - `0x10006620`, `0x10006660`, `0x10006680`, `0x10006720`, `0x100067e0`, `0x10006910`, `0x100060d0`: These are the addresses of other functions called within this function.
   - `0x1f`: A limit on the length of a substring that can be processed.
   - `0x7ff8fff2`, `0x7fffbffb`: Error codes returned if certain conditions are not met.
   - `Gdiplus::Image::GetLastStatus`: A call to get the status of an image processing operation.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_100067e0` and `FUN_10006720`, as they are involved in processing and potentially writing data that could be related to state persistence on the radio.

---

## 147. `RemoteProtocols01.dll` — `GetLastStatus` (`100067b0`)
- **Keywords:** named

*(qwen2.5-coder:14b, 11.9s)*

1. **Role**: The function `GetLastStatus` retrieves the last status of an image object and resets the internal status to a default value. It is likely used to check the success or failure of previous operations on the image.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It is a transport helper function that deals with the status of image operations, which is unrelated to EEPROM commit, lock/unlock, or reset mechanisms.

3. **Key Constants / Opcodes / Calls**: 
   - `Status` enum: This is a return type indicating the status of the image operation.
   - Offset `0x8`: This is where the status is stored within the `Image` object.
   - `0`: The default status value used to reset the internal status.

4. **Next Bite**: Since this function is a transport helper and does not directly interact with EEPROM persistence, there is no specific callee to inspect next for tracing EEPROM persistence. Further analysis should focus on other functions that handle image operations and their interactions with the radio's storage mechanisms.

---

## 148. `RemoteProtocols01.dll` — `FUN_100067e0` (`100067e0`)
- **Keywords:** has-strings
- **Strings:** `Map Entry not found
`

*(qwen2.5-coder:14b, 12.5s)*

1. **Role**: This function appears to be a wrapper or handler for processing a specific operation, likely related to map entries, as indicated by the referenced string "Map Entry not found\n". It calls other functions to perform its task and returns an integer result.

2. **EEPROM / Persistence Mechanism**: The function does not directly handle EEPROM persistence mechanisms such as commit, lock/unlock, or flash/EEPROM flush. It seems to be more of a transport helper or a higher-level operation handler that may indirectly affect state persistence through the operations it manages.

3. **Key Constants / Opcodes / Calls**: 
   - Referenced string: "Map Entry not found\n"
   - Callee functions: `FUN_10008bd0`, `FUN_10006850`, `FUN_10005780`

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_10006850`, as it is directly called within this function and may contain the logic for handling the specific operation related to map entries, which could involve state persistence mechanisms.

---

## 149. `RemoteProtocols01.dll` — `FUN_10006960` (`10006960`)
- **Keywords:** has-strings
- **Strings:** `ForceRemove, NoRemove, Delete, Deleting Key %s
, Deleting non-empty subkey %s by force
, Ending Recovery Mode
, Creating key %s
, Deleting %s
`

*(qwen2.5-coder:14b, 37.6s)*

1. **Role**: This function appears to handle operations related to registry key management, including deletion, creation, and manipulation of registry keys. It processes commands based on the input string and performs actions like deleting keys, handling recovery mode, and managing registry entries.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. Instead, it manipulates registry keys, which are likely mapped to EEPROM or flash storage by the underlying system. It uses functions like `FUN_100061e0` and `FUN_10007d20` to perform operations that could affect the permanent state of the radio, but the exact mechanism of how these changes are committed to EEPROM is not clear from this function alone.

3. **Key Constants / Opcodes / Calls**:
   - **Strings**: "ForceRemove", "NoRemove", "Delete", "Deleting Key %s\n", "Deleting non-empty subkey %s by force\n", "Ending Recovery Mode\n", "Creating key %s\n", "Deleting %s\n", "Num Els = %d\n"
   - **Function Calls**: `FUN_100061e0`, `FUN_10007230`, `FUN_10008610`, `FUN_10006910`, `FUN_100060d0`, `FUN_10007b70`, `FUN_10007250`, `FUN_100073b0`, `FUN_10001e80`, `FUN_10007d20`, `FUN_10007360`, `FUN_100072f0`, `FUN_10009aa0`, `FUN_10001b10`, `FUN_10007bc0`, `FUN_10007c40`, `ATL::CRegKey::Close`, `FUN_10007270`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_100061e0`, `FUN_10007d20`, and `FUN_10007360`. These functions are called multiple times and could be responsible for committing changes to the permanent state of the radio.

---

## 150. `RemoteProtocols01.dll` — `Close` (`100072b0`)
- **Keywords:** named

*(qwen2.5-coder:14b, 12.3s)*

1. **Role**: The `Close` function is a method of the `ATL::CRegKey` class, responsible for closing a registry key. It checks if the registry key handle is valid, closes it using `RegCloseKey`, and then sets the handle to `0`.

2. **EEPROM / Persistence Mechanism**: This function does not directly interact with the radio's EEPROM or flash memory. It is a transport helper function used to manage registry keys, which are not directly related to the radio's persistent storage mechanisms.

3. **Key Constants / Opcodes / Calls**: 
   - `RegCloseKey`: The Windows API function called to close the registry key.
   - `HRESULT` return value: `local_8` holds the result of `RegCloseKey`, which is returned by the function.

4. **Next Bite**: Since this function is a registry key management function and does not interact with the radio's persistent storage, there is no specific callee to inspect next for tracing EEPROM persistence. The focus should shift to other functions that directly handle communication with the radio or manage its persistent storage.

---

## 151. `RemoteProtocols01.dll` — `FUN_100074e0` (`100074e0`)
- **Keywords:** has-strings
- **Strings:** `Binary Data does not fall on BYTE boundries
, Setting Value %d at %s
, Setting Value %s at %s
, default, default, default, default, %s Type not supported
`

*(qwen2.5-coder:14b, 23.8s)*

1. **Role**: This function appears to handle setting values on a device, likely a radio, based on the type of data provided. It processes different data types and writes them to the device's memory.

2. **EEPROM / Persistence Mechanism**: The function interacts with the device's memory, specifically handling different data types and writing them to the appropriate locations. It uses `RegSetValueExA` to set values in the registry, which could be related to EEPROM persistence. The function also calls `FUN_100079b0` and `FUN_10007980`, which might be responsible for committing changes to the device's memory.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x80004005`, `0x204`, `0x80070000`
   - Offsets: `0xffc`, `0x11`, `0x13`
   - Error HRESULTs: `0x80004005`
   - Callees: `FUN_10009aa0`, `FUN_100061e0`, `FUN_100079f0`, `FUN_100060d0`, `FUN_10006140`, `FUN_100079b0`, `FUN_10007aa0`, `FUN_10005630`, `VarUI4FromStr`, `FUN_10007980`

4. **Next Bite**: The callees `FUN_100079b0` and `FUN_10007980` should be inspected next to trace EEPROM persistence, as they are directly involved in setting values on the device.

---

## 152. `RemoteProtocols01.dll` — `FUN_10007aa0` (`10007aa0`)
- **Keywords:** has-strings
- **Strings:** `Bogus value %c passed as binary Hex value
`

*(qwen2.5-coder:14b, 13.8s)*

1. **Role**: This function converts a single hexadecimal character to its corresponding integer value. It handles both uppercase and lowercase hexadecimal digits.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function appears to be a utility for parsing hexadecimal data, which could be part of a larger process that affects EEPROM persistence, but it does not directly interact with EEPROM or manage state persistence on its own.

3. **Key Constants / Opcodes / Calls**: 
   - Hexadecimal character ranges: `0x30` to `0x39` (0-9), `0x41` to `0x46` (A-F), `0x61` to `0x66` (a-f).
   - Error message string: `"Bogus value %c passed as binary Hex value\n"`.

4. **Next Bite**: Since this function is a helper for parsing hexadecimal data, the next step would be to inspect the callers of this function to understand how the parsed data is used in the context of EEPROM persistence. Look for functions that handle data transmission or storage operations, such as those involving `WriteIsh`, `Prepare Write`, or `EnterMode/Session` opcodes.

---

## 153. `RemoteProtocols01.dll` — `FUN_10007bc0` (`10007bc0`)
- **Keywords:** has-strings
- **Strings:** `Should not be here!!
`

*(qwen2.5-coder:14b, 11.7s)*

1. **Role**: This function queries information about a registry key and checks if the key has any subkeys. It returns `true` if the key has subkeys and `false` otherwise.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with the radio's EEPROM or flash memory. It appears to be a utility function for registry operations, which may be used in a broader context to manage state persistence.

3. **Key Constants / Opcodes / Calls**: 
   - `RegQueryInfoKeyA`: Windows API function to retrieve information about a registry key.
   - `LVar1`: Variable to store the result of `RegQueryInfoKeyA`.
   - `local_8`: Variable to store the number of subkeys in the registry key.

4. **Next Bite**: Since this function is a registry utility, the next step would be to trace how it is used within the broader context of the application. Look for calls to this function and analyze the surrounding code to understand its role in managing state persistence.

---

## 154. `RemoteProtocols01.dll` — `FUN_10007c40` (`10007c40`)
- **Keywords:** has-strings
- **Strings:** `RegQueryInfoKey Failed `

*(qwen2.5-coder:14b, 14.6s)*

1. **Role**: This function queries information about a registry key and checks for the presence of a specific value within that key. It returns `true` if the key exists and contains a non-empty value, otherwise `false`.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. It appears to be a helper function for registry operations, which might be used in a broader context to manage configuration or state persistence indirectly.

3. **Key Constants / Opcodes / Calls**:
   - `RegQueryInfoKeyA`: Windows API call to query information about a registry key.
   - `RegEnumValueA`: Windows API call to enumerate values within a registry key.
   - `0x1000`: Size of the buffer used for storing the registry value name.
   - `0x10007c7c`: A memory address used in the function.
   - `FUN_10009aa0`: A function call within the function.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_10009aa0`, as it is called at the beginning of the function and might contain logic related to registry operations or state management that could be relevant to the radio's permanent state.

---

## 155. `RemoteProtocols01.dll` — `FUN_10008510` (`10008510`)
- **Keywords:** has-strings
- **Strings:** `UnRegisterTypeLib, oleaut32.dll`

*(qwen2.5-coder:14b, 19.9s)*

1. **Role**: This function appears to handle the registration and unregistration of a type library, likely related to COM (Component Object Model) operations. It initializes COM objects, loads the `oleaut32.dll` library, and calls functions to register and unregister a type library based on the provided parameters.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. It seems to be a transport helper function that manages COM resources, which may be indirectly related to state persistence through COM-based communication protocols.

3. **Key Constants / Opcodes / Calls**:
   - `0x1c` and `0x30`: Offsets in the COM vtable for specific function calls.
   - `LoadLibraryA("oleaut32.dll")`: Loads the `oleaut32.dll` library.
   - `GetProcAddress(hModule, "UnRegisterTypeLib")`: Retrieves the address of the `UnRegisterTypeLib` function.
   - `FUN_10008610`, `FUN_10008440`, `FUN_10008630`, `FUN_10001b10`, `FUN_10001ae0`: Various function calls within the code.
   - `ATL::CComBSTR::~CComBSTR`: Destructor for the `CComBSTR` class.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10008630` and `FUN_10001b10`, as they are involved in the initialization and cleanup of COM objects, which might have deeper interactions with the radio's state management.

---

## 156. `RemoteProtocols01.dll` — `ocscpy` (`10008990`)
- **Keywords:** named

*(qwen2.5-coder:14b, 11.4s)*

1. **Role**: The `ocscpy` function is a wide-character string copy function, similar to `wcscpy`, but with additional length calculation and memory allocation. It copies the content of `param_2` to `param_1` after allocating sufficient memory.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly affect the permanent state on the radio. It is a helper function for string manipulation and does not involve EEPROM commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**: 
   - `lstrlenW`: Function to calculate the length of a wide-character string.
   - `FUN_10009760`: A function pointer or address that likely handles memory allocation and copying.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_10009760`, as it is responsible for memory allocation and copying, which could be part of a larger operation that affects the radio's permanent state.

---

## 157. `RemoteProtocols01.dll` — `entry` (`10009db4`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 16.1s)*

1. **Role**: This function appears to handle different operations based on the `param_2` value, potentially involving initialization, processing, and cleanup tasks. It delegates tasks to other functions based on the operation code and checks for success or failure conditions.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to manage state transitions and possibly invokes other functions that could handle EEPROM persistence. It checks for success or failure and may involve unlocking or locking mechanisms, but the direct impact on EEPROM persistence is indirect.

3. **Key Constants / Opcodes / Calls**:
   - `param_2` values: 0, 1, 2, 3
   - `DAT_10010bf8`: A global variable used when `param_2` is 0.
   - `DAT_10011198`: A pointer to a function that might handle specific operations.
   - `FUN_10009cdb`: A function called multiple times for different operations.
   - `FUN_10003760`: Another function called when `param_2` is 1.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10009cdb` and `FUN_10003760`, as they are invoked multiple times and might contain the logic for handling EEPROM operations or state persistence.

---

## 158. `RemoteProtocols01.dll` — `FUN_1000b4c5` (`1000b4c5`)
- **Keywords:** has-strings
- **Strings:** `R6009
- not enough space for environment
, R6009
- not enough space for environment
, R6009
- not enough space for environment
, Microsoft Visual C++ Runtime Library, Runtime Error!

Program: , <program name unknown>`

*(qwen2.5-coder:14b, 16.5s)*

1. **Role**: This function appears to handle error reporting and logging, specifically for runtime errors related to insufficient space for the environment. It writes error messages to the standard error handle and constructs a detailed error message if a runtime error occurs.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with the radio's EEPROM or flash memory. Instead, it focuses on error handling and reporting, which is indirectly related to the transport layer but does not involve making state permanent on the radio.

3. **Key Constants / Opcodes / Calls**:
   - Error message strings: "R6009\r\n- not enough space for environment\r\n", "Microsoft Visual C++ Runtime Library", "Runtime Error!\n\nProgram: ", "<program name unknown>".
   - Function calls: `GetStdHandle`, `WriteFile`, `GetModuleFileNameA`, `FUN_10009670`, `FUN_10009680`, `FUN_1000bdd6`.

4. **Next Bite**: The callees `FUN_10009670`, `FUN_10009680`, and `FUN_1000bdd6` should be inspected next to trace further details on how error messages are constructed and displayed. These functions might contain additional logic related to error handling or logging that could provide insights into the transport layer's behavior.

---

## 159. `RemoteProtocols01.dll` — `FUN_1000bdd6` (`1000bdd6`)
- **Keywords:** has-strings
- **Strings:** `GetLastActivePopup, GetActiveWindow, MessageBoxA, user32.dll`

*(qwen2.5-coder:14b, 19.9s)*

1. **Role**: This function appears to be a wrapper around Windows API calls to display a message box. It loads the `user32.dll` library and retrieves the addresses of `MessageBoxA`, `GetActiveWindow`, and `GetLastActivePopup` functions. It then uses these functions to determine the active window and its last active popup, and finally displays a message box with the provided parameters.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with the radio's EEPROM or flash memory. It is likely used for user interaction or error handling, which may indirectly affect the state persistence by prompting the user to take action.

3. **Key Constants / Opcodes / Calls**:
   - `DAT_10010dcc`: Address of `MessageBoxA` function.
   - `DAT_10010dd0`: Address of `GetActiveWindow` function.
   - `DAT_10010dd4`: Address of `GetLastActivePopup` function.
   - `LoadLibraryA("user32.dll")`: Loads the `user32.dll` library.
   - `GetProcAddress`: Retrieves the address of a function in a loaded DLL.
   - `MessageBoxA`: Displays a message box with the provided parameters.

4. **Next Bite**: The next callees to inspect for EEPROM persistence would be any functions that interact with the radio's memory or state, such as those handling opcodes like `0x0100` (ReadIsh), `0x0101` (WriteIsh), `0x0106` (EnterMode/Session), or `0x000C` (OP_UNLOCK). These functions are more likely to involve direct operations on the radio's EEPROM or flash memory.

---

## 160. `UdcDrIsh10c.dll` — `FUN_10001010` (`10001010`)
- **Keywords:** has-strings
- **Strings:** `FALSE`

*(qwen2.5-coder:14b, 9.7s)*

1. **Role**: This function initializes a `CString` object with the string "FALSE" from a global data location (`DAT_10011794`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanism. It appears to be a utility function for string handling.

3. **Key Constants / Opcodes / Calls**: 
   - String: "FALSE" (`s_FALSE_10011424`)
   - Global data: `DAT_10011794`

4. **Next Bite**: Since this function is primarily a string initialization utility, there is no direct call to inspect for EEPROM persistence. However, if the `CString` object is used in subsequent operations, those should be traced to understand its role in the overall persistence mechanism.

---

## 161. `UdcDrIsh10c.dll` — `FUN_10001050` (`10001050`)
- **Keywords:** has-strings
- **Strings:** `FALSE`

*(qwen2.5-coder:14b, 9.3s)*

1. **Role**: The function `FUN_10001050` initializes a `CString` object with the string "FALSE" from a global data location.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function appears to be a string initialization routine and does not directly interact with the radio's EEPROM or state persistence mechanisms.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"FALSE"` at `s_FALSE_10011424`
   - Global data reference: `DAT_1001173c`

4. **Next Bite**: Since this function does not directly relate to EEPROM persistence, the next step should be to trace the call graph to identify where this function is called and what other functions it interacts with, particularly those that might involve EEPROM operations.

---

## 162. `UdcDrIsh10c.dll` — `FUN_100010d0` (`100010d0`)
- **Keywords:** has-strings
- **Strings:** `DISPLAY_LAST`

*(qwen2.5-coder:14b, 10.7s)*

1. **Role**: The function `FUN_100010d0` initializes a `CString` object with the string "DISPLAY_LAST" from the global data at `DAT_1001176c`.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper function that initializes a string for display purposes.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"DISPLAY_LAST"` at `s_DISPLAY_LAST_10011434`.
   - Global data reference: `DAT_1001176c`.

4. **Next Bite**: Since this function is primarily a string initialization, the next step should be to inspect the caller of `FUN_100010d0` to see how it integrates with other operations that might involve EEPROM persistence. Look for calls to functions that handle EEPROM operations or state management.

---

## 163. `UdcDrIsh10c.dll` — `FUN_10001110` (`10001110`)
- **Keywords:** has-strings
- **Strings:** `APPEND`

*(qwen2.5-coder:14b, 10.2s)*

1. **Role**: The function `FUN_10001110` initializes a `CString` object with the string "APPEND" from the data at offset `0x10011444`.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper function that initializes a string for further processing.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"APPEND"` at offset `0x10011444`.
   - No specific hex constants, opcodes, or HRESULTs observed in the provided code snippet.

4. **Next Bite**: Since this function initializes a string, the next step should be to inspect the callees or the context in which this function is used to understand how the string "APPEND" is utilized in the broader context of EEPROM persistence.

---

## 164. `UdcDrIsh10c.dll` — `FUN_100012d0` (`100012d0`)
- **Keywords:** has-strings
- **Strings:** `INVALID`

*(qwen2.5-coder:14b, 9.4s)*

1. **Role**: This function initializes a `CString` object with the string "INVALID" from a global data location (`DAT_100117b0`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with EEPROM or flash storage. It appears to be a utility function for error handling or logging.

3. **Key Constants / Opcodes / Calls**: 
   - String: "INVALID" (`s_INVALID_10011468`)
   - Global data: `DAT_100117b0`

4. **Next Bite**: Since this function is primarily involved in string handling and does not directly interact with EEPROM or flash storage, there is no immediate next callee to inspect for EEPROM persistence. Further analysis should focus on other functions that handle EEPROM operations or state persistence.

---

## 165. `UdcDrIsh10c.dll` — `Am_Registered_Type` (`10001ac0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 14.4s)*

1. **Role**: The function `Am_Registered_Type::Am_Registered_Type` is a constructor for the `Am_Registered_Type` class. It initializes the object by setting its virtual function table pointer (`vftable_`) to a predefined address.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It is a transport helper function that sets up the object's virtual function table, which is likely used for method dispatching but does not involve EEPROM commit, lock/unlock, or other persistence mechanisms.

3. **Key Constants / Opcodes / Calls**: The function sets the first pointer of the object (`this`) to a vftable address (`_vftable_`). There are no specific hex constants, opcodes, or error HRESULTs observed in the provided code snippet.

4. **Next Bite**: Since this function is a constructor and primarily sets up the object's vftable, the next callees to inspect for EEPROM persistence should be the methods associated with this vftable. Specifically, look at the methods related to `ReadIsh`, `WriteIsh`, `Prepare Write`, `DelIshTypes`, `EnterMode/Session`, `UnlockSecurity`, `OP_UNLOCK`, `OP_LOCK`, and `GetRadioUUID` to trace how they interact with the radio's permanent state.

---

## 166. `UdcDrIsh10c.dll` — `Am_Registered_Type` (`10001ad0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 9.8s)*

1. **Role**: This function is a copy constructor for the `Am_Registered_Type` class. It initializes the object by setting its vtable pointer to `_vftable_`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanism. It is likely involved in object management rather than state persistence.

3. **Key Constants / Opcodes / Calls**: 
   - Vtable pointer assignment: `*(undefined ***)this = &_vftable_;`
   - No specific hex constants, opcodes, or error HRESULTs observed in the provided code snippet.

4. **Next Bite**: Since this function is a copy constructor and does not directly interact with EEPROM, the next step should be to inspect the vtable methods (`_vftable_`) to see if any of them involve EEPROM operations or state persistence mechanisms.

---

## 167. `UdcDrIsh10c.dll` — `Am_Wrapper` (`10001ae0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.6s)*

1. **Role**: The `Am_Wrapper` function is a constructor for the `Am_Wrapper` class. It initializes the object by setting its virtual function table pointer (`vftable_`) to a predefined address.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with the EEPROM or handle state persistence mechanisms. It appears to be a setup function for the class instance.

3. **Key Constants / Opcodes / Calls**: 
   - `0x1ae0`: The memory address of the function.
   - `0x41`: The first instruction of the function, which is likely a `mov` instruction setting up the `this` pointer.
   - `undefined ***this = &_vftable_;`: This line sets the vftable pointer of the `Am_Wrapper` instance to a predefined vftable address.

4. **Next Bite**: Since this function is a constructor and does not directly interact with EEPROM or state persistence, the next step should be to inspect the vtable (`_vftable_`) to see which methods are available and how they might interact with the radio's state. Specifically, look for methods that involve communication with the radio or handling of opcodes related to state persistence.

---

## 168. `UdcDrIsh10c.dll` — `Am_Wrapper` (`10001af0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.7s)*

1. **Role**: The `Am_Wrapper` function is a constructor for the `Am_Wrapper` class. It initializes the object by setting its vtable pointer to `_vftable_`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with the EEPROM or handle state persistence. It appears to be a part of the class initialization process.

3. **Key Constants / Opcodes / Calls**: 
   - Hex constant: `0x1af0` (address of the function)
   - Vtable pointer: `_vftable_`
   - No specific opcodes or HRESULTs are observed in the provided code snippet.

4. **Next Bite**: Since this function is a constructor and does not directly interact with EEPROM or state persistence, the next step should be to inspect the vtable (`_vftable_`) to identify which methods are called and how they might interact with the radio's EEPROM or state persistence mechanisms.

---

## 169. `UdcDrIsh10c.dll` — `operator=` (`10001b00`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.1s)*

1. **Role**: This function is an assignment operator for the `Am_Constraint` class. It appears to perform a shallow copy of the `Am_Constraint` object pointed to by `param_1` into the object pointed to by `this`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any other persistent storage mechanisms. It seems to be a utility function for object management rather than state persistence.

3. **Key Constants / Opcodes / Calls**: None. The function does not contain any specific hex constants, offsets, error HRESULTs, or calls to other functions that are relevant to EEPROM persistence.

4. **Next Bite**: Since this function does not involve any direct interaction with EEPROM or state persistence, there is no specific callee to inspect next for tracing EEPROM persistence. Further analysis should focus on other functions or classes that might be involved in managing the radio's state.

---

## 170. `UdcDrIsh10c.dll` — `ID` (`10001b10`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.3s)*

1. **Role**: This function retrieves an identifier (`ID`) from the object pointed to by `this`, likely used to identify the method or object within the context of the class `Am_Method_Wrapper`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function appears to be a simple accessor method that does not directly interact with EEPROM or handle state persistence mechanisms. It retrieves an ID, which could be used in higher-level operations that manage EEPROM persistence.

3. **Key Constants / Opcodes / Calls**: The function accesses a pointer at offset `0x8` from the `this` pointer and returns the value pointed to by that pointer. There are no specific hex constants, opcodes, or error HRESULTs directly observable in the provided code snippet.

4. **Next Bite**: Since the function is a simple accessor, the next step should be to inspect the class `Am_Method_Wrapper` and its methods to understand how the retrieved ID is used. Specifically, look for methods that interact with EEPROM or handle state persistence, such as those that might use the ID to call other functions or methods that perform write operations or manage locks.

---

## 171. `UdcDrIsh10c.dll` — `Am_Method_Wrapper` (`10001b20`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.1s)*

1. **Role**: The `Am_Method_Wrapper` function is a copy constructor for the `Am_Method_Wrapper` class. It initializes a new instance by copying the vtable pointer and two member variables from an existing instance.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or handle state persistence. It appears to be a utility function for object management rather than data storage operations.

3. **Key Constants / Opcodes / Calls**: 
   - Vtable pointer assignment: `*(undefined ***)this = &Am_Registered_Type::_vftable_;`
   - Member variable copying: `*(undefined4 *)(this + 4) = *(undefined4 *)(param_1 + 4);` and `*(undefined4 *)(this + 8) = *(undefined4 *)(param_1 + 8);`

4. **Next Bite**: Since this function is primarily concerned with object initialization, the next step should be to inspect the vtable methods (`_vftable_`) to see if any of them involve EEPROM operations or state persistence mechanisms.

---

## 172. `UdcDrIsh10c.dll` — `operator=` (`10001b50`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.4s)*

1. **Role**: This function is an assignment operator for the `Am_Method_Wrapper` class. It copies the contents of one `Am_Method_Wrapper` object to another by copying the values of two member variables from the source object to the destination object.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any other persistent storage mechanisms. It appears to be a utility function for copying object states, which may be part of a larger process involving state persistence.

3. **Key Constants / Opcodes / Calls**: The function copies two `undefined4` values from the source object (`param_1`) to the destination object (`this`). There are no specific hex constants, opcodes, error HRESULTs, or callees (`FUN_*` / COM vtable offsets) observed in the provided code snippet.

4. **Next Bite**: Since this function does not directly interact with EEPROM or other persistent storage, there is no specific callee to inspect next for tracing EEPROM persistence. Further analysis would involve tracing higher-level functions that use `Am_Method_Wrapper` and interact with the radio's persistent storage mechanisms.

---

## 173. `UdcDrIsh10c.dll` — `Am_Value` (`10001b70`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.7s)*

1. **Role**: The `Am_Value` constructor initializes an instance of the `Am_Value` class by setting the first two bytes of the object to 0 and the next four bytes to 0. This likely prepares the object for subsequent operations.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanism. It appears to be a basic initialization routine for an object.

3. **Key Constants / Opcodes / Calls**: 
   - `0x0000`: The value being set in the first two bytes of the object.
   - `0x00000000`: The value being set in the next four bytes of the object.

4. **Next Bite**: Since this function does not involve any direct interaction with EEPROM or persistence, there is no specific callee to inspect next for tracing EEPROM persistence. Further analysis should focus on other functions that might interact with the radio's EEPROM or state management.

---

## 174. `UdcDrIsh10c.dll` — `Am_Value` (`10001b80`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.2s)*

1. **Role**: The `Am_Value` function initializes an object of the `Am_Value` class. It sets the first two bytes of the object to `0x09` and assigns a pointer to a byte array (`param_1`) to the fourth byte of the object.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly affect the permanent state on the radio. It appears to be a constructor or initialization function that sets up an object, which may be used in subsequent operations that do affect persistence.

3. **Key Constants / Opcodes / Calls**: 
   - The first two bytes of the object are set to `0x09`.
   - The fourth byte of the object is set to the pointer `param_1`.

4. **Next Bite**: Since this function is a constructor and does not directly interact with EEPROM or persistence, the next step should be to inspect the methods or functions that use instances of `Am_Value`. Look for calls to methods that might involve operations like `EnterMode`, `OP_LOCK`, `OP_UNLOCK`, or any other opcodes that affect the state persistence on the radio.

---

## 175. `UdcDrIsh10c.dll` — `Am_Value` (`10001ba0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.0s)*

1. **Role**: The `Am_Value` function initializes an object of type `Am_Value` by setting its first two bytes to `0x0002` and the next four bytes to the value of `param_1`. This appears to be a constructor for the `Am_Value` class, setting up initial state for an object.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly interact with EEPROM or any persistence mechanism. It is likely a transport helper function that sets up an object for subsequent operations that may involve state persistence.

3. **Key Constants / Opcodes / Calls**: 
   - The function sets the first two bytes of the object to `0x0002`.
   - It stores the value of `param_1` at an offset of 4 bytes from the object's base address.

4. **Next Bite**: Since this function is a constructor and does not directly interact with EEPROM, the next step should be to inspect the methods or functions that use instances of `Am_Value`. Look for calls to methods that might involve operations like `EnterMode`, `OP_LOCK`, `OP_UNLOCK`, or any other opcodes that could affect state persistence on the radio.

---

## 176. `UdcDrIsh10c.dll` — `Am_Value` (`10001bc0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.7s)*

1. **Role**: The `Am_Value` function initializes an object of type `Am_Value` by setting its first two bytes to `0x0003` and the next four bytes to the value of `param_1`. This appears to be a constructor for the `Am_Value` class, setting up initial state for an object.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanism. It seems to be a utility function for setting up object state, possibly in preparation for operations that might affect EEPROM.

3. **Key Constants / Opcodes / Calls**: 
   - `0x0003`: The first two bytes of the object are set to this value.
   - `param_1`: The next four bytes of the object are set to this value, which could be a pointer or a specific value used in subsequent operations.

4. **Next Bite**: Since this function is a constructor and does not directly interact with EEPROM, the next step should be to inspect the methods or functions that use instances of `Am_Value`. Look for calls to methods that might involve EEPROM operations, such as `ReadIsh`, `WriteIsh`, or other opcodes that affect the radio's state.

---

## 177. `UdcDrIsh10c.dll` — `Am_Value` (`10001be0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.2s)*

1. **Role**: The `Am_Value` function initializes an object of type `Am_Value` by setting its first two bytes to `0x0004` and the fourth byte to the boolean value passed as `param_1`.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a constructor or initialization function for an object, possibly used in managing data but not directly involved in EEPROM commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**: 
   - Hex constant: `0x0004`
   - No specific opcodes or HRESULTs are observed in the provided code snippet.

4. **Next Bite**: Since this function is primarily an initializer, the next step should be to inspect the class methods or other functions that interact with this object to understand how it might be used in the context of EEPROM persistence. Look for calls to methods that involve writing to partitions or handling opcodes related to EEPROM operations.

---

## 178. `UdcDrIsh10c.dll` — `Am_Value` (`10001c00`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.3s)*

1. **Role**: The `Am_Value` function initializes an object of type `Am_Value` by setting its first member to `5` and its second member to the provided floating-point parameter.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function appears to be a constructor for an object and does not directly interact with EEPROM or any persistence mechanisms. It is likely used in a broader context to manage data that may eventually be written to EEPROM, but the direct persistence mechanism is not evident from this function alone.

3. **Key Constants / Opcodes / Calls**: 
   - `0x0005`: The value `5` is assigned to the first member of the `Am_Value` object.
   - `this + 4`: The second member of the `Am_Value` object is set to the provided floating-point parameter.

4. **Next Bite**: Since this function does not directly interact with EEPROM or any persistence mechanisms, the next step should be to trace how instances of `Am_Value` are used within the program. Look for calls to other functions that might involve writing to EEPROM or managing state persistence, such as functions that use the `Am_Value` object in operations related to the known opcodes or partitions.

---

## 179. `UdcDrIsh10c.dll` — `Am_Value` (`10001c20`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.6s)*

1. **Role**: The `Am_Value` function initializes an object of type `Am_Value` by setting its first two bytes to `0x07` and the fourth byte to the value of `param_1`. This appears to be a constructor for the `Am_Value` class, setting up initial state for an object.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanism. It seems to be a helper function for setting up object state, possibly in preparation for operations that might affect EEPROM.

3. **Key Constants / Opcodes / Calls**: 
   - Hex constant: `0x07` (set as the first two bytes of the object).
   - Offset: `this[4]` (sets the fourth byte of the object to `param_1`).

4. **Next Bite**: Since this function does not directly interact with EEPROM, the next step would be to inspect the callees or methods that use `Am_Value` objects, particularly those that involve operations on partitions or opcodes related to EEPROM persistence. Look for functions that call `Am_Value` and then perform operations like `WriteIsh`, `Prepare Write`, or `EnterMode/Session`.

---

## 180. `UdcDrIsh10c.dll` — `Am_Value` (`10001c40`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.6s)*

1. **Role**: The `Am_Value` function initializes an object of the `Am_Value` class. It sets the first two bytes of the object to `0x000A` and assigns a function pointer to the fourth byte of the object.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper or initialization function that sets up an object for later use.

3. **Key Constants / Opcodes / Calls**: 
   - `0x000A` is assigned to the first two bytes of the object.
   - A function pointer (`param_1`) is assigned to the fourth byte of the object.

4. **Next Bite**: Since this function does not directly interact with EEPROM or persistence, the next step should be to inspect the function pointer (`param_1`) that is assigned to the object. This function pointer might be responsible for handling EEPROM operations or persistence mechanisms.

---

## 181. `UdcDrIsh10c.dll` — `Am_Demon_Queue` (`10001c60`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.8s)*

1. **Role**: The function `Am_Demon_Queue::Am_Demon_Queue` is a constructor for the `Am_Demon_Queue` class. It initializes an instance of `Am_Demon_Queue` by setting a pointer to an `Am_Value_List_Data` object within the instance.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly affect the permanent state on the radio. It is likely a transport helper function that sets up internal data structures for subsequent operations that may involve EEPROM persistence.

3. **Key Constants / Opcodes / Calls**: 
   - No specific hex constants, offsets, error HRESULTs, or callees are observed in the provided code snippet. The function simply assigns a pointer to an `Am_Value_List_Data` object.

4. **Next Bite**: Since this function is a constructor and does not directly interact with EEPROM, the next step should be to inspect the callees or methods that are called on instances of `Am_Demon_Queue` to understand how EEPROM persistence is managed. Look for methods that involve operations like `EnterMode`, `UnlockSecurity`, or any other opcodes that might affect the radio's state.

---

## 182. `UdcDrIsh10c.dll` — `operator==` (`10001c70`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.5s)*

1. **Role**: This function is an overloaded equality operator for the `Am_String` class, comparing the current string object with a provided C-style string (`char*`). It likely returns an integer indicating whether the two strings are equal.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with the radio's EEPROM or flash memory. It appears to be a utility function for string comparison, which is part of the transport layer's operations but does not affect the permanent state of the radio.

3. **Key Constants / Opcodes / Calls**: 
   - The function calls another `operator==` method (`::Am_String::operator==`), which suggests it might be part of a class hierarchy or a method override.
   - No specific hex constants, offsets, error HRESULTs, or direct calls to EEPROM/flash operations are observed in the provided code snippet.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence would be `::Am_String::operator==`, as it is the method being called within the current function. This will help determine if there are any deeper interactions with the radio's storage mechanisms.

---

## 183. `UdcDrIsh10c.dll` — `Am_Load_Save_Context` (`10001c80`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.9s)*

1. **Role**: The `Am_Load_Save_Context` function initializes an object by setting its first member to zero. This is a common pattern for constructors in C++ to ensure that the object is in a known state.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with EEPROM or any persistence mechanism. It appears to be a constructor for an object that may be involved in managing context or state, but the actual persistence logic is not evident from this snippet.

3. **Key Constants / Opcodes / Calls**: The function sets the first member of the object to zero (`*(undefined4 *)this = 0;`). There are no specific hex constants, offsets, error HRESULTs, or callees observed in the provided code snippet.

4. **Next Bite**: Since this function is a constructor and does not directly interact with EEPROM, the next step would be to inspect the class methods or other functions that this object might interact with, particularly those that involve state management or communication with the radio. Look for methods that might call into the transport layer or handle EEPROM operations.

---

## 184. `UdcDrIsh10c.dll` — `IsEmpty` (`10001c90`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 14.9s)*

1. **Role**: The `IsEmpty` function checks if the internal state of an `Am_Map_CStr2Int` object is empty by examining an integer value at an offset of 8 from the object's base address. It returns `true` if the integer is 0, indicating that the object is empty; otherwise, it returns `false`.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It is a utility function used to determine the state of an internal data structure, which may be part of a larger process involving EEPROM persistence. It is likely used in conjunction with other functions to manage and verify the state of data before committing it to EEPROM.

3. **Key Constants / Opcodes / Calls**: The function checks the value at offset 8 of the object. There are no specific hex constants, opcodes, error HRESULTs, or callees (`FUN_*` / COM vtable offsets) observed in the provided code snippet.

4. **Next Bite**: Since this function is a simple check and does not directly interact with EEPROM, the next step should be to trace the calls to this function and inspect the surrounding code to understand how it fits into the larger process of managing and committing data to EEPROM. Look for calls to other functions that might involve EEPROM operations, such as `WriteIsh`, `Prepare Write`, or `EnterMode/Session`.

---

## 185. `UdcDrIsh10c.dll` — `Count` (`10001ca0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.0s)*

1. **Role**: The `Count` function retrieves an integer value from the object's memory, likely representing the number of elements or entries in a collection or map managed by the `Am_Map_CStr2Int` class.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function appears to be a simple accessor method and does not directly interact with EEPROM or handle state persistence mechanisms like commit, lock/unlock, or reset.

3. **Key Constants / Opcodes / Calls**: The function accesses an integer value at an offset of 8 bytes from the `this` pointer. There are no specific hex constants, opcodes, or error HRESULTs observed in the provided code snippet.

4. **Next Bite**: Since this function is a simple accessor, the next step would be to inspect the class's constructor or any other methods that modify the state of the object, as they might interact with EEPROM or other persistence mechanisms.

---

## 186. `UdcDrIsh10c.dll` — `Am_Map_Int2Str` (`10001cb0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 9.5s)*

1. **Role**: This function is a copy constructor for the `Am_Map_Int2Str` class. It initializes a new instance of `Am_Map_Int2Str` by copying the data from an existing instance.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with the radio's EEPROM or handle state persistence. It appears to be a utility function for managing internal state within the application.

3. **Key Constants / Opcodes / Calls**: 
   - No specific hex constants, offsets, error HRESULTs, or callees are observed in the provided code snippet.

4. **Next Bite**: Since this function is a copy constructor and does not interact with EEPROM or persistence mechanisms, there is no immediate next callee to inspect for tracing EEPROM persistence. Further analysis should focus on other functions that handle data storage or communication with the radio.

---

## 187. `UdcDrIsh10c.dll` — `operator=` (`10001ce0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.8s)*

1. **Role**: This function is an assignment operator for the `Am_Map_CStr2Int` class. It copies the contents of one `Am_Map_CStr2Int` object to another by copying the values of three member variables (`this + 4`, `this + 8`, `this + 0xc`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanism. It appears to be a utility function for copying object states, which may be part of a larger process involving state persistence.

3. **Key Constants / Opcodes / Calls**: The function copies three member variables from the source object to the destination object. No specific hex constants, opcodes, error HRESULTs, or callees are observed in the provided code snippet.

4. **Next Bite**: Since this function is a simple assignment operator, the next step would be to inspect the larger context in which this function is used. Specifically, look at the classes and methods that call this function to understand how object states are managed and persisted. Additionally, inspect any methods that interact with the radio's EEPROM or flash memory to trace the persistence mechanism.

---

## 188. `UdcDrIsh10c.dll` — ``default_constructor_closure'` (`10001d00`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.3s)*

1. **Role**: This function acts as a default constructor closure for the `Am_Map_Int2Str` class, initializing an instance with a specific parameter (`0x17`).

2. **EEPROM / Persistence Mechanism**: This function indirectly contributes to the EEPROM persistence mechanism by invoking the constructor of `Am_Map_Int2Str` with a parameter that likely influences the initialization of internal state or configuration. It does not directly perform operations like commit, lock/unlock, or reset but sets up the environment necessary for these operations.

3. **Key Constants / Opcodes / Calls**: The key constant observed is `0x17`, which is passed to the constructor. There are no direct references to opcodes, error HRESULTs, or specific callees in the provided code snippet.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `::Am_Map_Int2Str::Am_Map_Int2Str(this,0x17)`. This constructor might contain the logic for setting up the internal state or configuration that affects EEPROM persistence.

---

## 189. `UdcDrIsh10c.dll` — `Am_MapIterator_Int2Str` (`10001d70`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.0s)*

1. **Role**: The function `Am_MapIterator_Int2Str::Am_MapIterator_Int2Str` is a constructor for the `Am_MapIterator_Int2Str` class. It initializes an instance of this class using the provided `Am_Map_Int2Str` object.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper function that initializes an iterator for a map, which is likely used in higher-level operations that may involve EEPROM persistence.

3. **Key Constants / Opcodes / Calls**: 
   - The function calls `::Am_MapIterator_Int2Str::Init(this, param_1)`, which is likely where the initialization logic resides.
   - No specific hex constants, offsets, error HRESULTs, or other direct EEPROM-related operations are observed in the provided code snippet.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence would be `::Am_MapIterator_Int2Str::Init`. This function is responsible for the actual initialization and might contain calls to other functions that handle EEPROM operations or state persistence.

---

## 190. `UdcDrIsh10c.dll` — ``default_constructor_closure'` (`10001d90`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.2s)*

1. **Role**: This function serves as the default constructor closure for the `Am_MapIterator_Int2Str` class, initializing an instance of `Am_MapIterator_Int2Str` by calling the `Init` method with a null pointer cast to `Am_Map_Int2Str*`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanisms. It appears to be a part of the initialization process for an iterator class, which is likely used in higher-level operations that may affect state persistence.

3. **Key Constants / Opcodes / Calls**: 
   - `::Am_MapIterator_Int2Str::Init(this,(Am_Map_Int2Str *)0x0);` - Calls the `Init` method with a null pointer.

4. **Next Bite**: The `Init` method should be inspected next to trace any potential interactions with EEPROM persistence or other state management mechanisms.

---

## 191. `UdcDrIsh10c.dll` — `HashValue` (`10001da0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.8s)*

1. **Role**: The `HashValue` function computes a hash value for a given string. It appears to be part of a mapping mechanism that associates strings with integers, possibly for indexing or lookup purposes.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It is likely a utility function used in the context of data handling or mapping, but it does not involve EEPROM commit, lock/unlock, reset, or state persistence operations.

3. **Key Constants / Opcodes / Calls**: 
   - The function uses the modulus operator (`%`) with a value retrieved from `*(int *)(this + 4)`, which suggests a size or capacity value.
   - The bitwise right shift (`>> 0x1f`) and XOR (`^`) operations are used in the hash calculation.
   - There are no specific hex constants, opcodes, or direct calls to other functions that indicate EEPROM or persistence operations.

4. **Next Bite**: Since this function is primarily involved in string-to-integer mapping, the next step would be to inspect the class or methods that use this hash value. Specifically, look at how the hash value is used in the context of data storage or retrieval, which might involve interactions with EEPROM or other persistent storage mechanisms.

---

## 192. `UdcDrIsh10c.dll` — `KeyComp` (`10001dc0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.4s)*

1. **Role**: The `KeyComp` function is a simple comparison function that subtracts one integer (`param_2`) from another (`param_1`) and returns the result. It is likely used to compare keys in a map or dictionary-like structure.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It is a transport helper function used for comparing keys, which is part of the internal logic of the `Am_Map_Int2Str` class.

3. **Key Constants / Opcodes / Calls**: None observed in the provided code snippet. The function does not use any specific hex constants, opcodes, error HRESULTs, or make any function calls.

4. **Next Bite**: Since this function is a simple comparison function, the next step would be to inspect the class methods that use this function, particularly those related to map operations, to understand how they interact with the radio's EEPROM or persistent state.

---

## 193. `UdcDrIsh10c.dll` — `Am_Instance_Iterator` (`10001dd0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.3s)*

1. **Role**: The `Am_Instance_Iterator` function is a constructor for the `Am_Instance_Iterator` class. It initializes an instance of the class by copying another instance's data members, specifically handling two `Am_Object` instances.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper function, managing object initialization rather than EEPROM commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**: 
   - No specific hex constants, opcodes, or error HRESULTs are directly observed in the provided code snippet.
   - The function calls `Am_Object::Am_Object` twice, which suggests it is related to object initialization.

4. **Next Bite**: To trace EEPROM persistence, the next callees to inspect would be `Am_Object::Am_Object` and any other methods that might be involved in object initialization or state management within the `UdcDrIsh10c.dll` library.

---

## 194. `UdcDrIsh10c.dll` — `operator=` (`10001e30`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 15.0s)*

1. **Role**: This function is an assignment operator for the `Am_Instance_Iterator` class. It copies the state of another `Am_Instance_Iterator` object to the current object by calling the assignment operator of the base `Am_Object` class twice, once for the object itself and once for the object at an offset of 4 bytes.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanism. It appears to be a utility function for copying object states, which may be part of a larger process involving persistence.

3. **Key Constants / Opcodes / Calls**: 
   - `FUN_*` / COM vtable offsets: None observed in the provided code snippet.
   - HRESULTs: None observed in the provided code snippet.
   - Hex constants: None observed in the provided code snippet.
   - Offsets: The function calls the assignment operator of the base `Am_Object` class twice, once for the object itself (`this`) and once for the object at an offset of 4 bytes (`this + 4`).

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence should be the assignment operator of the `Am_Object` class, as it is called twice within this function. These calls might contain more detailed logic related to object state management, which could be indirectly related to EEPROM persistence.

---

## 195. `UdcDrIsh10c.dll` — `~Am_Instance_Iterator` (`10001e60`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 9.2s)*

1. **Role**: This function is the destructor for the `Am_Instance_Iterator` class. It ensures proper cleanup by calling destructors for embedded `Am_Object` instances.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It appears to be a cleanup routine that ensures objects are properly destroyed.

3. **Key Constants / Opcodes / Calls**: 
   - Calls to `Am_Object::~Am_Object` for cleanup.
   - No specific hex constants, offsets, error HRESULTs, or transport-related opcodes are observed in the provided code snippet.

4. **Next Bite**: The next callees to inspect for EEPROM persistence would be `Am_Object::~Am_Object` methods, as they might contain the actual logic for handling state persistence or cleanup related to EEPROM operations.

---

## 196. `UdcDrIsh10c.dll` — `Am_Slot_Iterator` (`10001eb0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.1s)*

1. **Role**: The `Am_Slot_Iterator` function is a copy constructor for the `Am_Slot_Iterator` class. It initializes a new instance of `Am_Slot_Iterator` by copying the contents of an existing instance.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It is a transport helper function used for object initialization and copying.

3. **Key Constants / Opcodes / Calls**: 
   - No specific hex constants, offsets, error HRESULTs, or callees are observed in the provided code snippet.

4. **Next Bite**: Since this function is primarily involved in object copying, the next callees to inspect for EEPROM persistence should be those related to object management or state handling within the `Am_Object` class, such as `Am_Object::Am_Object` or any other methods that might involve state persistence or commit operations.

---

## 197. `UdcDrIsh10c.dll` — `operator=` (`10001ed0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.6s)*

1. **Role**: This function is an assignment operator for the `Am_Slot_Iterator` class. It copies the contents of one `Am_Slot_Iterator` object to another, including both the base class (`Am_Object`) and derived class (`Am_Slot_Iterator`) members.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function itself does not directly interact with EEPROM or manage state persistence. It appears to be a utility function for object copying, which may be part of a larger process involving state management.

3. **Key Constants / Opcodes / Calls**: 
   - No specific hex constants, offsets, error HRESULTs, or direct callees to `FUN_*` or COM vtable offsets are observed in the provided code snippet.

4. **Next Bite**: The next callee to inspect for EEPROM persistence should be `Am_Object::operator=`. This is because the function calls `Am_Object::operator=` to handle the base class part of the assignment, and understanding how the base class manages state could provide insights into the overall persistence mechanism.

---

## 198. `UdcDrIsh10c.dll` — `Am_Part_Iterator` (`10001ef0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.5s)*

1. **Role**: The `Am_Part_Iterator` function is a constructor for the `Am_Part_Iterator` class. It initializes the object by copying another `Am_Part_Iterator` object, likely setting up internal state for iterating over partitions or managing data.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper or part of the object management system, possibly setting up iterators for handling data partitions without directly committing changes to EEPROM or flash.

3. **Key Constants / Opcodes / Calls**: 
   - No specific hex constants, offsets, error HRESULTs, or direct calls to known opcodes are observed in the provided code snippet.
   - The function calls `Am_Object::Am_Object` twice, which suggests it is part of a larger object-oriented framework.

4. **Next Bite**: To trace EEPROM persistence, inspect the callees of `Am_Object::Am_Object` or any other methods that might be involved in data handling or state management. Look for functions that interact with partitions or perform operations that could involve committing data to EEPROM or flash.

---

## 199. `UdcDrIsh10c.dll` — `~Am_Part_Iterator` (`10001f50`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.5s)*

1. **Role**: The `~Am_Part_Iterator` destructor function is responsible for cleaning up resources associated with an `Am_Part_Iterator` object. It calls destructors for both the `Am_Part_Iterator` and its base `Am_Object` class.

2. **EEPROM / Persistence Mechanism**: This function does not directly handle the mechanics of making state permanent on the radio. It appears to be a transport helper function that ensures proper cleanup of resources, which may indirectly contribute to state persistence by ensuring that all changes are properly finalized before the object is destroyed.

3. **Key Constants / Opcodes / Calls**: 
   - Calls to destructors: `Am_Object::~Am_Object((Am_Object *)(this + 4))` and `Am_Object::~Am_Object((Am_Object *)this)`.
   - Exception handling setup: `ExceptionList = &local_c` and `ExceptionList = local_c`.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are the destructors `Am_Object::~Am_Object((Am_Object *)(this + 4))` and `Am_Object::~Am_Object((Am_Object *)this)`. These destructors may contain the logic for committing changes to EEPROM or handling other persistence mechanisms.

---

## 200. `UdcDrIsh10c.dll` — `Am_Constraint` (`10001fb0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 9.7s)*

1. **Role**: The `Am_Constraint` function is a constructor for the `Am_Constraint` class. It initializes the object by setting its vtable pointer to `_vftable_`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with the EEPROM or handle state persistence mechanisms. It appears to be a setup function for the class.

3. **Key Constants / Opcodes / Calls**: 
   - `0x1fb0`: The memory address of the function.
   - `_vftable_`: The vtable pointer being set.

4. **Next Bite**: Since this function is a constructor and does not directly interact with EEPROM or persistence, the next step should be to inspect the vtable (`_vftable_`) to see which methods are called and how they might interact with the radio's state persistence mechanisms.

---

## 201. `UdcDrIsh10c.dll` — `Am_Constraint` (`10001fc0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 9.6s)*

1. **Role**: The `Am_Constraint` function is a copy constructor for the `Am_Constraint` class. It initializes the object by setting its vtable pointer to `_vftable_`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with EEPROM or handle state persistence mechanisms. It appears to be a class initialization routine.

3. **Key Constants / Opcodes / Calls**: 
   - `0x1fc0`: The memory address of the function.
   - `_vftable_`: The vtable pointer being set.

4. **Next Bite**: Since this function is a constructor and does not directly interact with EEPROM or state persistence, the next step should be to inspect the vtable (`_vftable_`) to see which methods are called and how they might interact with EEPROM or state persistence mechanisms.

---

## 202. `UdcDrIsh10c.dll` — `operator==` (`10001fd0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 9.0s)*

1. **Role**: This function checks if two `Am_Slot` objects are equal by comparing their integer values. It is likely used to determine if two slots are the same in some context within the application.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with EEPROM or handle state persistence. It appears to be a utility function for comparing objects.

3. **Key Constants / Opcodes / Calls**: 
   - No specific hex constants, offsets, error HRESULTs, or callees are observed in the provided code snippet.

4. **Next Bite**: Since this function is a simple equality check, there are no callees to inspect next for tracing EEPROM persistence. The next step would be to trace how `Am_Slot` objects are used in the context of state persistence operations.

---

## 203. `UdcDrIsh10c.dll` — `operator!=` (`10001ff0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.3s)*

1. **Role**: This function checks if two `Am_Slot` objects are not equal by comparing their integer representations. It returns a non-zero value if they are not equal, and zero if they are equal.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly affect the permanent state on the radio. It is likely used for internal comparisons within the application logic.

3. **Key Constants / Opcodes / Calls**: The function uses a simple integer comparison (`*(int *)this != *(int *)param_1`). There are no specific hex constants, offsets, error HRESULTs, or callees observed in the provided code snippet.

4. **Next Bite**: Since this function is a simple comparison and does not involve any direct interaction with the radio's EEPROM or state persistence mechanisms, there is no specific callee to inspect next for tracing EEPROM persistence. Further analysis should focus on other parts of the codebase that handle state persistence operations.

---

## 204. `UdcDrIsh10c.dll` — `operator=` (`10002010`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.2s)*

1. **Role**: This function is an assignment operator for the `Am_Slot` class. It copies the contents of one `Am_Slot` object to another, performing a shallow copy of the object's data members.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly affect the permanent state on the radio. It is a transport helper function that copies data between objects, which may be part of a larger process involving EEPROM persistence.

3. **Key Constants / Opcodes / Calls**: The function does not contain any specific hex constants, offsets, error HRESULTs, or callees that are directly related to EEPROM persistence. It simply copies the first four bytes of the source object to the destination object.

4. **Next Bite**: Since this function is a simple assignment operator, the next step should be to inspect the larger context in which it is used. Look for calls to other functions that might involve EEPROM operations, such as those related to committing changes, locking/unlocking, or flushing data to the radio's storage.

---

## 205. `UdcDrIsh10c.dll` — `Am_Object_Advanced` (`10002020`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.9s)*

1. **Role**: This function is a copy constructor for the `Am_Object_Advanced` class. It initializes a new instance of `Am_Object_Advanced` by copying the state from an existing instance.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function itself does not directly interact with EEPROM or manage state persistence. It appears to be a part of the object initialization process, which may be indirectly related to state management through higher-level operations.

3. **Key Constants / Opcodes / Calls**: 
   - The function calls `Am_Object::Am_Object`, which is a base class constructor. No specific hex constants, offsets, error HRESULTs, or other opcodes are directly observed in the provided code snippet.

4. **Next Bite**: To trace EEPROM persistence, the next callees to inspect should be those related to state management or object initialization within the `Am_Object` or `Am_Object_Advanced` classes. Look for functions that involve operations like `EnterMode`, `OP_LOCK`, `OP_UNLOCK`, or any other methods that might interact with the radio's state or EEPROM.

---

## 206. `UdcDrIsh10c.dll` — `operator=` (`10002040`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 8.9s)*

1. **Role**: This function is an assignment operator for the `Am_Object_Advanced` class. It assigns the contents of one `Am_Object_Advanced` object to another by calling the base class's assignment operator.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with EEPROM or handle state persistence. It appears to be a utility function for object assignment.

3. **Key Constants / Opcodes / Calls**: 
   - Calls the base class's assignment operator: `Am_Object::operator=`

4. **Next Bite**: The next callee to inspect for EEPROM persistence would be the base class's assignment operator (`Am_Object::operator=`). This is because the function delegates the assignment operation to the base class, and any EEPROM persistence logic would likely be implemented there.

---

## 207. `UdcDrIsh10c.dll` — `~Am_Object_Advanced` (`10002060`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.7s)*

1. **Role**: This function is the destructor for the `Am_Object_Advanced` class, which calls the destructor of its base class `Am_Object`. It is responsible for cleaning up resources associated with the object.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly handle EEPROM persistence. It is a transport helper function that ensures proper cleanup of resources, which may indirectly contribute to the overall state management of the radio.

3. **Key Constants / Opcodes / Calls**: 
   - No specific hex constants, offsets, error HRESULTs, or callees are directly observed in the provided code snippet. The function primarily calls the destructor of the base class `Am_Object`.

4. **Next Bite**: The next callee to inspect for EEPROM persistence should be the destructor of the base class `Am_Object` (`Am_Object::~Am_Object`). This is indicated by the call `Am_Object::~Am_Object((Am_Object *)this);` within the `Am_Object_Advanced` destructor.

---

## 208. `UdcDrIsh10c.dll` — `Am_Constraint_Context` (`10002070`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.2s)*

1. **Role**: The `Am_Constraint_Context` function is a constructor for the `Am_Constraint_Context` class. It initializes the object by setting its vtable pointer to `_vftable_`.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It is a transport helper function that sets up the object's virtual function table, which is likely used for method dispatching in subsequent operations.

3. **Key Constants / Opcodes / Calls**: The function sets the vtable pointer (`*(undefined ***)this = &_vftable_;`). There are no specific hex constants, opcodes, or error HRESULTs observed in the provided code snippet.

4. **Next Bite**: To trace EEPROM persistence, the next callees or methods associated with the `Am_Constraint_Context` class should be inspected, particularly those that interact with the radio's EEPROM or involve state management operations.

---

## 209. `UdcDrIsh10c.dll` — `Am_Constraint_Context` (`10002080`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.4s)*

1. **Role**: The function `Am_Constraint_Context::Am_Constraint_Context` is a copy constructor for the `Am_Constraint_Context` class. It initializes the object by setting its vtable pointer to `_vftable_`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with the radio's EEPROM or flash memory. It appears to be a class constructor and does not involve any operations related to committing state to persistent storage.

3. **Key Constants / Opcodes / Calls**: 
   - The function sets the vtable pointer (`*(undefined ***)this = &_vftable_;`), but no specific hex constants, opcodes, or other direct calls to EEPROM-related functions are observed.

4. **Next Bite**: Since this function does not involve direct EEPROM operations, the next step should be to inspect the vtable (`_vftable_`) and any other methods or functions that might be called on instances of `Am_Constraint_Context` to see if they interact with the radio's persistent storage.

---

## 210. `UdcDrIsh10c.dll` — `Am_Formula_Advanced` (`10002090`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.0s)*

1. **Role**: The `Am_Formula_Advanced` function is a constructor for the `Am_Formula_Advanced` class. It initializes the object by setting its virtual function table pointer (`vftable_`) to a predefined address.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with EEPROM or flash storage. It appears to be a setup function for the class, which may be involved in higher-level operations that affect state persistence.

3. **Key Constants / Opcodes / Calls**: 
   - `0x2090`: The memory address of the function.
   - `0x9`: The size of the function in bytes.
   - `undefined ***this`: The pointer to the object being constructed.
   - `_vftable_`: The virtual function table pointer being set.

4. **Next Bite**: Since this function is a constructor and does not directly interact with EEPROM, the next step would be to inspect the virtual functions pointed to by `_vftable_` to see if any of them involve EEPROM operations or state persistence mechanisms.

---

## 211. `UdcDrIsh10c.dll` — `Am_Formula_Advanced` (`100020a0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 9.6s)*

1. **Role**: The `Am_Formula_Advanced` function is a constructor for the `Am_Formula_Advanced` class. It initializes the object by setting its vtable pointer to `_vftable_`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with EEPROM or handle state persistence mechanisms. It appears to be a class initialization routine.

3. **Key Constants / Opcodes / Calls**: 
   - `0x20a0`: The memory address of the function.
   - `_vftable_`: The vtable pointer being set.

4. **Next Bite**: Since this function is a constructor and does not directly interact with EEPROM or state persistence, the next step should be to inspect the vtable (`_vftable_`) to find other functions that might be involved in handling EEPROM or state persistence.

---

## 212. `UdcDrIsh10c.dll` — `operator=` (`100020b0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 9.9s)*

1. **Role**: This function is an assignment operator for the `Am_Constraint_Iterator` class. It copies the contents of one `Am_Constraint_Iterator` object to another by copying the first four bytes of each object.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanism. It appears to be a utility function for copying iterator states.

3. **Key Constants / Opcodes / Calls**: 
   - No specific hex constants, offsets, error HRESULTs, or callees are observed in the provided code snippet.

4. **Next Bite**: Since this function is primarily a copy operation and does not involve direct interaction with EEPROM or persistence mechanisms, there is no immediate next callee to inspect for EEPROM persistence. Further analysis would involve tracing how this iterator is used in the context of other functions that might interact with EEPROM.

---

## 213. `UdcDrIsh10c.dll` — `Am_Formula` (`100020d0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 15.1s)*

1. **Role**: The `Am_Formula` function is a copy constructor for the `Am_Formula` class. It initializes a new instance of `Am_Formula` by copying the contents of an existing instance (`param_1`) to the new instance (`this`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanism. It appears to be a class constructor and does not involve any operations related to committing state to EEPROM or handling locks/unlocks.

3. **Key Constants / Opcodes / Calls**: 
   - `0x20d0`: The memory address of the function.
   - `&Am_Registered_Type::_vftable_`: A pointer to the virtual function table for the `Am_Registered_Type` class.
   - `param_1 + 4`: An offset to access a member of the `param_1` object.
   - `this + 4`: An offset to access a member of the `this` object.

4. **Next Bite**: Since the function is a constructor and does not involve any direct interaction with EEPROM or persistence mechanisms, there are no callees to inspect next for tracing EEPROM persistence. The next step would be to trace the class methods that are called after an instance of `Am_Formula` is created to see if they interact with EEPROM or persistence mechanisms.

---

## 214. `UdcDrIsh10c.dll` — `operator=` (`100020f0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.5s)*

1. **Role**: This function is an assignment operator for the `Am_Formula` class. It copies the value from one `Am_Formula` object to another by copying the value at offset 4 of the source object to the same offset in the destination object.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with EEPROM or any persistence mechanism. It appears to be a utility function for copying object states within the application.

3. **Key Constants / Opcodes / Calls**: The function involves copying a 4-byte value from one object to another. There are no specific hex constants, opcodes, or calls to other functions or COM methods observed in the provided code snippet.

4. **Next Bite**: Since this function does not directly interact with EEPROM or any persistence mechanism, there is no specific callee to inspect next for tracing EEPROM persistence. Further analysis would need to focus on other parts of the codebase that handle state persistence.

---

## 215. `UdcDrIsh10c.dll` — `Am_Map_CStr2Int` (`10002100`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.4s)*

1. **Role**: This function is a copy constructor for the `Am_Map_CStr2Int` class. It initializes a new instance of `Am_Map_CStr2Int` by copying the data from an existing instance (`param_1`) to the new instance (`this`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanisms. It appears to be a utility function for object management rather than state persistence.

3. **Key Constants / Opcodes / Calls**: 
   - No specific hex constants, offsets, error HRESULTs, or callees are observed in the provided code snippet.

4. **Next Bite**: Since this function is a copy constructor and does not involve any direct interaction with EEPROM or persistence mechanisms, there is no specific callee to inspect next for tracing EEPROM persistence. Further analysis should focus on other functions that handle state persistence or interact with the radio's storage.

---

## 216. `UdcDrIsh10c.dll` — ``default_constructor_closure'` (`10002130`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 9.8s)*

1. **Role**: This function serves as a default constructor closure for the `Am_Map_CStr2Int` class, initializing an instance with a specific parameter (`0x17`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function appears to be a constructor and does not directly interact with EEPROM or persistence mechanisms. It likely sets up internal state for the class instance.

3. **Key Constants / Opcodes / Calls**: 
   - Hex constant: `0x17`
   - Callee: `::Am_Map_CStr2Int::Am_Map_CStr2Int(this,0x17)`

4. **Next Bite**: The next callee to inspect is `::Am_Map_CStr2Int::Am_Map_CStr2Int(this,0x17)` to trace how the instance is initialized and if it involves any EEPROM or persistence operations.

---

## 217. `UdcDrIsh10c.dll` — `Am_MapIterator_CStr2Int` (`100021a0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.8s)*

1. **Role**: This function initializes an `Am_MapIterator_CStr2Int` object by calling its `Init` method with a pointer to an `Am_Map_CStr2Int` object. It serves as a constructor for the iterator class.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function itself does not directly interact with EEPROM or handle state persistence. It appears to be a helper function for initializing iterators, which may be used in higher-level operations that affect EEPROM persistence.

3. **Key Constants / Opcodes / Calls**: 
   - The function calls `::Am_MapIterator_CStr2Int::Init`, which is likely where the actual initialization logic resides.
   - No specific hex constants, offsets, error HRESULTs, or other direct EEPROM-related operations are observed in the provided code snippet.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence should be `::Am_MapIterator_CStr2Int::Init`. This method is responsible for the actual initialization of the iterator and may contain calls to other functions that handle EEPROM operations or state persistence.

---

## 218. `UdcDrIsh10c.dll` — `Key` (`100021c0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.4s)*

1. **Role**: The function `Key` is a member of the `Am_MapIterator_CStr2Int` class and returns a pointer to a constant character string. It appears to be used to retrieve a key associated with an iterator in a map-like data structure.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly affect the permanent state on the radio. It is likely a transport helper function used to manage data within the application, possibly in preparation for operations that could involve EEPROM persistence.

3. **Key Constants / Opcodes / Calls**: The function does not contain any specific hex constants, offsets, error HRESULTs, or direct calls to other functions. It simply returns a pointer to a character string stored at an offset within the object instance.

4. **Next Bite**: Since this function is a simple accessor, the next step should be to inspect the caller of this function to understand how the key is used in the context of EEPROM persistence operations. Look for calls to other functions that might involve writing to EEPROM or managing state persistence.

---

## 219. `UdcDrIsh10c.dll` — `operator=` (`100021d0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.4s)*

1. **Role**: This function is an assignment operator for the `Am_MapIterator_CStr2Int` class. It copies the contents of one `Am_MapIterator_CStr2Int` object to another by copying four 4-byte chunks of data.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with EEPROM or any other persistent storage mechanisms. It appears to be a utility function for copying iterator state, which is likely used in higher-level operations that may affect persistent state.

3. **Key Constants / Opcodes / Calls**: The function copies data at offsets 0, 4, 8, and 0xc from the source object to the destination object. There are no specific hex constants, opcodes, error HRESULTs, or callees (`FUN_*` / COM vtable offsets) observed in the provided code snippet.

4. **Next Bite**: Since this function is a simple assignment operator, the next step would be to inspect the higher-level functions that use this operator, particularly those that involve operations on the `Am_MapIterator_CStr2Int` object. Look for functions that might call this operator and then perform operations that could affect persistent state, such as writing to EEPROM or committing changes.

---

## 220. `UdcDrIsh10c.dll` — ``default_constructor_closure'` (`10002200`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.2s)*

1. **Role**: This function serves as the default constructor closure for the `Am_MapIterator_CStr2Int` class, initializing an instance of `Am_MapIterator_CStr2Int` by calling the `Init` method with a null pointer cast to `Am_Map_CStr2Int`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanisms. It appears to be a helper function for initializing an iterator, which is likely part of a larger system responsible for managing state.

3. **Key Constants / Opcodes / Calls**: 
   - `0x2200`: The offset of the function in the binary.
   - `::Am_MapIterator_CStr2Int::Init`: The method called within the function.
   - `(Am_Map_CStr2Int *)0x0`: A null pointer cast to `Am_Map_CStr2Int`, passed as an argument to the `Init` method.

4. **Next Bite**: The `Init` method should be inspected next to trace any potential interactions with EEPROM persistence or other state management mechanisms.

---

## 221. `UdcDrIsh10c.dll` — `KeyComp` (`10002210`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.8s)*

1. **Role**: The `KeyComp` function compares two strings (`param_1` and `param_2`) character by character. It returns 0 if the strings are identical, a positive value if `param_1` is greater, and a negative value if `param_1` is less. The comparison is case-sensitive and considers null terminators.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It is a string comparison utility and does not involve EEPROM commit, lock/unlock, reset, or any other persistence mechanisms.

3. **Key Constants / Opcodes / Calls**: None observed in the provided code snippet. The function does not use any specific hex constants, opcodes, error HRESULTs, or make any direct calls to other functions.

4. **Next Bite**: Since this function is a simple string comparison utility, there is no specific callee to inspect next for tracing EEPROM persistence. The next step would be to trace the function calls that use `KeyComp` to understand its role in the broader context of the application.

---

## 222. `UdcDrIsh10c.dll` — `Am_Symbol_Table` (`10002250`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.1s)*

1. **Role**: The `Am_Symbol_Table` constructor initializes an object by calling the constructor of its base class `Am_Map_CStr2Int` with an integer parameter. It then sets the vtable pointer of the object to `_vftable_`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with EEPROM or handle state persistence mechanisms. It appears to be a part of the object initialization process.

3. **Key Constants / Opcodes / Calls**: 
   - The function calls `Am_Map_CStr2Int::Am_Map_CStr2Int` with `param_1`.
   - The vtable pointer is set to `_vftable_`.

4. **Next Bite**: The next callee to inspect for EEPROM persistence would be `Am_Map_CStr2Int::Am_Map_CStr2Int`, as it is the base class constructor called within this function.

---

## 223. `UdcDrIsh10c.dll` — `Create` (`10002270`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 17.4s)*

1. **Role**: The `Create` function is a static method of the `Am_Symbol_Table` class that allocates memory for a new instance of `Am_Symbol_Table` and initializes it using the `Am_Map_CStr2Int` constructor. It returns a pointer to the newly created `Am_Symbol_Table` object.

2. **EEPROM / Persistence Mechanism**: This function does not directly interact with the EEPROM or handle state persistence on the radio. It appears to be a transport helper function responsible for creating and initializing an object, which may be used in higher-level operations that affect EEPROM persistence.

3. **Key Constants / Opcodes / Calls**: 
   - `0x10`: Size of memory allocated for the new instance.
   - `&LAB_10009b0b`: A reference to a label, possibly related to exception handling.
   - `ExceptionList`: A pointer to the current exception list, used for exception handling.
   - `operator_new(0x10)`: Allocates memory for the new instance.
   - `Am_Map_CStr2Int::Am_Map_CStr2Int(this,param_1)`: Calls the constructor for `Am_Map_CStr2Int`.
   - `*(undefined ***)this = &_vftable_`: Assigns the virtual function table pointer to the new instance.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence should be `Am_Map_CStr2Int::Am_Map_CStr2Int`, as it is called within the `Create` function and may handle more specific initialization or operations related to state persistence.

---

## 224. `UdcDrIsh10c.dll` — `Add_Item` (`100022d0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 9.3s)*

1. **Role**: The `Add_Item` function adds an item to the symbol table by setting a mapping from a string to an integer using the `SetAt` method of the `Am_Map_CStr2Int` class.

2. **EEPROM / Persistence Mechanism**: This function is a transport helper. It does not directly affect the permanent state on the radio (EEPROM/flash commit, host markers, lock/unlock, reset, state persistence). Instead, it manages in-memory data structures.

3. **Key Constants / Opcodes / Calls**: 
   - None observed in the provided code snippet.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `Am_Map_CStr2Int::SetAt`. This method is responsible for adding the item to the map and should be analyzed to understand how it interacts with the underlying storage mechanisms.

---

## 225. `UdcDrIsh10c.dll` — `Get_Value` (`100022f0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.9s)*

1. **Role**: The `Get_Value` function is a method of the `Am_Symbol_Table` class that retrieves an integer value associated with a given string key. It appears to be a utility function for accessing symbol table entries.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It is a transport helper function that retrieves values from a symbol table, which is likely used in the broader context of managing state and data within the system.

3. **Key Constants / Opcodes / Calls**: The function calls `Am_Map_CStr2Int::GetAt`, which is a method of the `Am_Map_CStr2Int` class. There are no specific hex constants, offsets, error HRESULTs, or opcodes directly observed in the provided code snippet.

4. **Next Bite**: To trace EEPROM persistence, the next callee to inspect should be `Am_Map_CStr2Int::GetAt`. This method is responsible for retrieving the integer value associated with the string key, and understanding its implementation may provide insights into how the system manages and persists state.

---

## 226. `UdcDrIsh10c.dll` — `operator[]` (`10002300`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 14.1s)*

1. **Role**: This function acts as an operator[] for the `Am_Symbol_Table` class, which appears to be a symbol table implementation. It takes a string parameter and returns a pointer to an integer, likely representing a symbol or identifier associated with that string.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly affect the permanent state on the radio. It is a transport helper function that delegates to another operator[] method (`Am_Map_CStr2Int::operator[]`) to retrieve an integer value based on the input string. It does not involve any direct interaction with EEPROM, flash, commit, lock/unlock, reset, or state persistence mechanisms.

3. **Key Constants / Opcodes / Calls**: 
   - The function calls `Am_Map_CStr2Int::operator[]`, which is a method of the `Am_Map_CStr2Int` class.
   - No specific hex constants, offsets, error HRESULTs, or other direct EEPROM/persistence-related calls are observed in the provided code snippet.

4. **Next Bite**: To trace EEPROM persistence, the next callee to inspect should be `Am_Map_CStr2Int::operator[]`. This method is responsible for the actual retrieval of the integer value based on the input string and may involve more complex operations related to symbol management or state persistence.

---

## 227. `UdcDrIsh10c.dll` — `Get_Key` (`10002310`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.7s)*

1. **Role**: The `Get_Key` function retrieves a key associated with a given index from an `Am_Symbol_Table` object. It appears to be a simple accessor method that uses the `operator[]` to fetch the key.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with EEPROM or any persistence mechanism. It is likely a helper function used in the context of data retrieval or transport.

3. **Key Constants / Opcodes / Calls**: The function calls `::Am_Symbol_Table::operator[]` with the `this` pointer and the provided index (`param_1`). There are no specific hex constants, offsets, error HRESULTs, or other opcodes observed in the provided code snippet.

4. **Next Bite**: The next callee to inspect for EEPROM persistence should be `::Am_Symbol_Table::operator[]`. This function is responsible for fetching the key from the symbol table and may involve more complex operations related to data storage or retrieval, which could be relevant to understanding how state is made permanent on the radio.

---

## 228. `UdcDrIsh10c.dll` — `Remove_Item` (`10002320`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 14.3s)*

1. **Role**: The `Remove_Item` function is part of the `Am_Symbol_Table` class and is responsible for removing an item identified by a string key from a symbol table. This operation likely involves deleting an entry from a map or dictionary structure.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly interact with the EEPROM or flash storage to make changes permanent. Instead, it appears to be a high-level operation that manipulates in-memory data structures. The actual persistence mechanism would likely occur elsewhere in the codebase, possibly during a commit operation or when the application is shut down.

3. **Key Constants / Opcodes / Calls**: 
   - The function calls `Am_Map_CStr2Int::DeleteKey`, which is a method of the `Am_Map_CStr2Int` class. This method is responsible for deleting a key from the map.
   - There are no specific hex constants, offsets, error HRESULTs, or other low-level operations directly visible in the provided code snippet.

4. **Next Bite**: To trace EEPROM persistence, the next step should be to inspect the `Am_Map_CStr2Int::DeleteKey` method. This method is likely responsible for removing the item from the in-memory map and may involve additional operations that eventually lead to the persistence of changes to the EEPROM or flash storage.

---

## 229. `UdcDrIsh10c.dll` — `Max_Size` (`10002330`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.8s)*

1. **Role**: The `Max_Size` function retrieves the maximum size of the symbol table associated with an instance of `Am_Symbol_Table`. It accesses an integer value stored at an offset of 4 bytes from the `this` pointer.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly affect the permanent state on the radio. It is likely a helper function used to manage memory or data structures within the application, possibly in support of operations that do affect persistence.

3. **Key Constants / Opcodes / Calls**: The function accesses an integer value at offset 4 from the `this` pointer. There are no specific hex constants, opcodes, or direct calls to other functions or COM methods visible in the provided code snippet.

4. **Next Bite**: Since this function is a simple accessor, the next step would be to inspect the callers of `Max_Size` to understand how it is used within the application. This might provide insights into operations that could affect EEPROM persistence.

---

## 230. `UdcDrIsh10c.dll` — `Am_Symbol_Table` (`10002340`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.8s)*

1. **Role**: This function is a copy constructor for the `Am_Symbol_Table` class. It initializes a new instance of `Am_Symbol_Table` by copying the data from an existing instance (`param_1`) to the new instance (`this`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function appears to be a standard class constructor and does not directly interact with EEPROM or any persistence mechanisms. It copies member variables but does not perform any operations related to committing changes to EEPROM or managing locks.

3. **Key Constants / Opcodes / Calls**: 
   - No specific hex constants, offsets, error HRESULTs, or direct calls to other functions are observed in the provided code snippet. The function simply copies member variables from one instance to another.

4. **Next Bite**: Since this function does not directly interact with EEPROM or persistence mechanisms, the next step should be to inspect the class methods that are called after this constructor, particularly those that might involve operations on the `Am_Symbol_Table` instance. Look for methods that could involve writing to EEPROM or managing locks.

---

## 231. `UdcDrIsh10c.dll` — `~Am_Symbol_Table` (`10002370`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.8s)*

1. **Role**: The `~Am_Symbol_Table` function is a destructor for the `Am_Symbol_Table` class. It calls the destructor of its base class `Am_Map_CStr2Int`, likely performing cleanup operations.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It appears to be a cleanup routine that may be part of a larger process involving state persistence, but the specific mechanism is not evident from this snippet alone.

3. **Key Constants / Opcodes / Calls**: 
   - The function calls `Am_Map_CStr2Int::~Am_Map_CStr2Int`, which is a destructor for a base class. No specific hex constants, offsets, error HRESULTs, or other opcodes are directly observable in the provided code snippet.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence should be `Am_Map_CStr2Int::~Am_Map_CStr2Int`. This function may contain more detailed operations related to state persistence or cleanup that could involve EEPROM or flash storage.

---

## 232. `UdcDrIsh10c.dll` — ``default_constructor_closure'` (`10002380`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.8s)*

1. **Role**: This function acts as a default constructor closure for the `Am_Symbol_Table` class, initializing an instance of `Am_Symbol_Table` with a specific constant value (`0x59`).

2. **EEPROM / Persistence Mechanism**: The function itself does not directly handle EEPROM persistence. It appears to be a transport helper or initialization routine that may be part of a larger process involving state persistence on the radio.

3. **Key Constants / Opcodes / Calls**: The key constant observed is `0x59`, which is passed to the `Am_Symbol_Table` constructor. There are no other hex constants, opcodes, or direct calls to persistence-related functions in the provided code snippet.

4. **Next Bite**: The next callee to inspect for EEPROM persistence should be the `Am_Symbol_Table` constructor (`Am_Symbol_Table(this,0x59)`). This constructor might contain the logic for initializing or interacting with the EEPROM or other persistent storage mechanisms on the radio.

---

## 233. `UdcDrIsh10c.dll` — `FUN_10002470` (`10002470`)
- **Keywords:** has-strings
- **Strings:** `FALSE`

*(qwen2.5-coder:14b, 9.8s)*

1. **Role**: The function `FUN_10002470` initializes a `CString` object with the string "FALSE" from the global data at `DAT_10011854`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function appears to be a string initialization routine and does not directly interact with EEPROM or persistence mechanisms.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"FALSE"` at `s_FALSE_10011424`.
   - Global data reference: `DAT_10011854`.

4. **Next Bite**: Since this function does not directly interact with EEPROM or persistence, the next step should be to trace the call stack to see where this function is called and what other functions it interacts with, particularly those that might involve EEPROM operations.

---

## 234. `UdcDrIsh10c.dll` — `FUN_100024b0` (`100024b0`)
- **Keywords:** has-strings
- **Strings:** `FALSE`

*(qwen2.5-coder:14b, 9.0s)*

1. **Role**: The function `FUN_100024b0` initializes a `CString` object with the string "FALSE" from a global data location.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function appears to be a string initialization routine and does not directly interact with EEPROM or persistence mechanisms.

3. **Key Constants / Opcodes / Calls**:
   - String: "FALSE" (referenced by `s_FALSE_10011424`)
   - Global data: `DAT_10011800`

4. **Next Bite**: Since this function does not directly interact with EEPROM or persistence, there is no specific callee to inspect next for tracing EEPROM persistence. Further analysis should focus on other functions that handle EEPROM operations or state persistence.

---

## 235. `UdcDrIsh10c.dll` — `FUN_10002530` (`10002530`)
- **Keywords:** has-strings
- **Strings:** `DISPLAY_LAST`

*(qwen2.5-coder:14b, 10.8s)*

1. **Role**: The function `FUN_10002530` initializes a `CString` object with the string "DISPLAY_LAST" from the global data at `DAT_10011830`.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper function that initializes a string for display purposes.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"DISPLAY_LAST"` at `s_DISPLAY_LAST_10011434`.
   - Global data reference: `DAT_10011830`.

4. **Next Bite**: Since this function is primarily a string initialization, the next step should be to inspect the caller of `FUN_10002530` to see how it integrates with other operations that might involve EEPROM persistence. Look for calls to functions that handle EEPROM operations or state management.

---

## 236. `UdcDrIsh10c.dll` — `FUN_10002570` (`10002570`)
- **Keywords:** has-strings
- **Strings:** `APPEND`

*(qwen2.5-coder:14b, 10.7s)*

1. **Role**: The function `FUN_10002570` initializes a `CString` object with the string "APPEND" from a predefined memory location.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper function used for string manipulation, possibly related to data transmission or logging.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"APPEND"` at offset `0x10011444`
   - `CString` constructor call

4. **Next Bite**: Since this function is primarily involved in string manipulation, the next step should be to inspect the callees or the context in which this function is used to understand its role in the broader process of state persistence. Specifically, look into how the `CString` object is used in subsequent operations, such as data transmission or logging, which might involve EEPROM or flash operations.

---

## 237. `UdcDrIsh10c.dll` — `FUN_10002730` (`10002730`)
- **Keywords:** has-strings
- **Strings:** `INVALID`

*(qwen2.5-coder:14b, 10.2s)*

1. **Role**: This function initializes a `CString` object with the string "INVALID" from a global data location (`DAT_10011870`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function appears to be setting an error message rather than directly affecting the EEPROM or flash persistence mechanisms.

3. **Key Constants / Opcodes / Calls**: 
   - String: "INVALID" (`s_INVALID_10011468`)
   - Global data: `DAT_10011870`

4. **Next Bite**: Since this function is primarily concerned with setting an error message, the next step should be to trace where this function is called and how it fits into the broader context of the application. Look for calls to `FUN_10002730` and analyze the surrounding code to understand its role in error handling or state management.

---

## 238. `UdcDrIsh10c.dll` — `CudcDrIshCmdLine` (`10002f20`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 14.3s)*

1. **Role**: The function `CudcDrIshCmdLine` is a constructor for the `CudcDrIshCmdLine` class. It initializes various member variables and strings, setting up the object for command line processing.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. It appears to be a transport helper function that sets up command line processing, which may be indirectly involved in state persistence through higher-level operations.

3. **Key Constants / Opcodes / Calls**:
   - `0xffffffff` is used to initialize a variable.
   - `&LAB_10009b3e` and `ExceptionList` are used for exception handling.
   - `CCommandLineInfo::CCommandLineInfo` and `CString::CString` are constructors for other classes.
   - `CString::operator=` is used to assign strings.
   - `&DAT_10011898` is a pointer to a string data.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `CCommandLineInfo::CCommandLineInfo` and `CString::CString`, as they are constructors that might involve setting up command line processing which could be related to state persistence operations.

---

## 239. `UdcDrIsh10c.dll` — `FreeItem` (`10002fb0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.9s)*

1. **Role**: The `FreeItem` function is a virtual method within the `Am_Map_CStr2Int` class. It appears to be responsible for freeing an item identified by an integer parameter. However, the function body is empty, indicating that it does not perform any operations.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanisms. It seems to be a placeholder or a transport helper function that might be involved in managing resources but does not affect the permanent state on the radio.

3. **Key Constants / Opcodes / Calls**: None. The function does not contain any specific hex constants, offsets, error HRESULTs, or calls to other functions. It is a simple return statement.

4. **Next Bite**: Since the function does not call any other functions or interact with any persistence mechanisms, there is no next callee to inspect. The focus should be on other functions within the same class or related classes that might handle EEPROM persistence.

---

## 240. `UdcDrIsh10c.dll` — `CudcDrIshCmdLine` (`10003030`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 14.8s)*

1. **Role**: The function `CudcDrIshCmdLine` is a constructor for the `CudcDrIshCmdLine` class. It initializes the object with parameters including an integer and two `CString` objects, setting up internal state and possibly preparing for command-line operations.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly interact with EEPROM or manage state persistence on the radio. It appears to be a transport helper or setup function, possibly preparing data or configurations that will be used in subsequent operations that affect EEPROM.

3. **Key Constants / Opcodes / Calls**: 
   - The function uses `CString` objects, which are part of the MFC library for string handling.
   - There are no specific opcodes or constants related to EEPROM operations in the provided code snippet.
   - The function calls constructors and destructors for `CString` objects, indicating string manipulation.

4. **Next Bite**: To trace EEPROM persistence, the next callees to inspect would be any methods or functions that interact with the radio's EEPROM, such as those handling `0x0100` (ReadIsh), `0x0101` (WriteIsh), or `0x0106` (EnterMode/Session). These would likely be involved in committing changes to the radio's permanent storage.

---

## 241. `UdcDrIsh10c.dll` — `~CudcDrIshCmdLine` (`100030d0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 17.2s)*

1. **Role**: This function is the destructor for the `CudcDrIshCmdLine` class. It performs cleanup operations, including destroying instances of `CString` and `CCommandLineInfo` associated with the object.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with the radio's EEPROM or flash memory. It appears to be focused on cleaning up resources rather than managing persistent state.

3. **Key Constants / Opcodes / Calls**: 
   - `this + 0x28` and `this + 0x24`: Offsets to `CString` instances being destroyed.
   - `ExceptionList`: Used for exception handling setup and teardown.
   - `&LAB_10009b93`: A reference to a label, possibly for exception handling.
   - `CudcDrIshCmdLine::~CudcDrIshCmdLine`: The destructor function itself.
   - `CString::~CString`: Destructor for `CString` objects.
   - `CCommandLineInfo::~CCommandLineInfo`: Destructor for `CCommandLineInfo` objects.

4. **Next Bite**: Since this function does not directly interact with EEPROM or flash memory, the next step should be to inspect the constructors and other methods of the `CudcDrIshCmdLine` class to see if they involve any calls to functions that manage persistent state on the radio. Additionally, tracing the calls to `CString` and `CCommandLineInfo` destructors might reveal more about how resources are managed and potentially how state is persisted.

---

## 242. `UdcDrIsh10c.dll` — `ParseParam` (`10003130`)
- **Keywords:** exported, has-strings, named
- **Strings:** `protocol, radioAtPort`

*(qwen2.5-coder:14b, 11.3s)*

1. **Role**: The `ParseParam` function processes command-line parameters, setting flags based on the parameter name and potentially storing values. It appears to handle specific parameters like "protocol" and "radioAtPort".

2. **EEPROM / Persistence Mechanism**: This function does not directly handle EEPROM persistence. It sets flags and possibly stores values, but does not involve direct operations like commit, lock/unlock, or reset. It seems to be a transport helper function.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x2c`, `0x2d`, `0x30`
   - Strings: `"protocol"`, `"radioAtPort"`
   - Functions: `_stricmp`, `atoi`, `CString::operator=`, `CCommandLineInfo::ParseParam`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `CString::operator=` and `CCommandLineInfo::ParseParam`, as they handle string operations and command-line parsing, respectively.

---

## 243. `UdcDrIsh10c.dll` — `GetPortName` (`100031f0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.4s)*

1. **Role**: The `GetPortName` function appears to be a member of the `CudcDrIshCmdLine` class, responsible for retrieving the port name associated with the object. It initializes a `CString` object using a pointer to the object itself plus an offset of 0x24.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It is likely a transport helper function used to manage communication parameters without directly interacting with EEPROM or flash storage.

3. **Key Constants / Opcodes / Calls**: 
   - Offset: `0x24` (used to access a member of the `CudcDrIshCmdLine` object)
   - `CString::CString` constructor is called with the pointer to the `CString` object and the offset pointer.

4. **Next Bite**: Since this function is primarily a transport helper, the next step should be to inspect the callees or the class methods that interact with the radio's EEPROM or flash storage to understand how state persistence is managed. Specifically, look into methods that use the port name to establish or manage communication channels, as these might involve setting up or tearing down state that affects EEPROM persistence.

---

## 244. `UdcDrIsh10c.dll` — `GetProtocolRead` (`10003210`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 16.2s)*

1. **Role**: The `GetProtocolRead` function appears to be responsible for retrieving a protocol-related string from an instance of the `CudcDrIshCmdLine` class. It initializes a `CString` object using a pointer to the current instance (`this`) and an offset of `0x28` bytes from the instance.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It seems to be a transport helper function that retrieves a protocol string, which might be used in subsequent operations that could affect EEPROM persistence, but the function itself does not perform any direct commit, lock, unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**: 
   - The function uses an offset of `0x28` bytes from the `this` pointer to access a member variable.
   - The function calls the `CString` constructor with the address of a local variable (`in_stack_00000004`) and a pointer to the `CString` member at offset `0x28` of the `CudcDrIshCmdLine` instance.

4. **Next Bite**: Since this function is primarily a transport helper, the next step should be to inspect the callees or the context in which this function is used. Specifically, look at the `CString` constructor and any other methods that might be called on the `CString` object to understand how the protocol string is used in the broader context of EEPROM persistence operations.

---

## 245. `UdcDrIsh10c.dll` — `GetPortIndex` (`10003230`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.8s)*

1. **Role**: The `GetPortIndex` function retrieves the port index from an instance of the `CudcDrIshCmdLine` class. It accesses an integer value stored at an offset of 0x30 from the `this` pointer, likely representing the port index used for communication.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly affect the permanent state on the radio. It is a transport helper function used to retrieve the port index, which is essential for communication but does not involve EEPROM commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**: 
   - Offset: 0x30 (used to access the port index)
   - No specific hex constants, opcodes, or HRESULTs are directly observed in the provided code snippet.

4. **Next Bite**: Since this function is a transport helper, the next step should be to inspect the callees or methods that use this port index for communication. Specifically, look into methods that handle the actual data transfer or command execution, such as those involving the opcodes mentioned earlier (e.g., `ReadIsh`, `WriteIsh`, `EnterMode`). These methods are more likely to involve operations that affect the permanent state on the radio.

---

## 246. `UdcDrIsh10c.dll` — `FUN_10003250` (`10003250`)
- **Keywords:** has-strings
- **Strings:** `FALSE`

*(qwen2.5-coder:14b, 9.2s)*

1. **Role**: The function `FUN_10003250` initializes a `CString` object with the string "FALSE" from a global data location.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper or utility function related to string handling.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"FALSE"` at `s_FALSE_10011424`
   - Global data reference: `DAT_10011904`

4. **Next Bite**: Since this function is primarily involved in string initialization, the next step should be to inspect the callees or functions that use this `CString` object to understand how it might indirectly influence the EEPROM persistence mechanism.

---

## 247. `UdcDrIsh10c.dll` — `FUN_10003290` (`10003290`)
- **Keywords:** has-strings
- **Strings:** `FALSE`

*(qwen2.5-coder:14b, 9.9s)*

1. **Role**: The function `FUN_10003290` initializes a `CString` object with the string "FALSE" from a global data location `DAT_100118b0`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function appears to be a string initialization routine and does not directly interact with EEPROM or any persistence mechanisms related to committing state to the radio.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"FALSE"` at `s_FALSE_10011424`.
   - Global data reference: `DAT_100118b0`.

4. **Next Bite**: Since this function does not directly relate to EEPROM persistence, there is no immediate next callee to inspect for EEPROM persistence. Further analysis should focus on other functions that interact with the radio's EEPROM or state management.

---

## 248. `UdcDrIsh10c.dll` — `FUN_10003310` (`10003310`)
- **Keywords:** has-strings
- **Strings:** `DISPLAY_LAST`

*(qwen2.5-coder:14b, 9.9s)*

1. **Role**: The function `FUN_10003310` initializes a `CString` object with the string "DISPLAY_LAST" from the global data at `DAT_100118e0`.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper function that initializes a string for display purposes.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"DISPLAY_LAST"` at `s_DISPLAY_LAST_10011434`.
   - Global data reference: `DAT_100118e0`.

4. **Next Bite**: Since this function is primarily a string initialization, the next step should be to inspect the callees or the context in which this function is used to understand how it might indirectly influence the EEPROM persistence mechanism.

---

## 249. `UdcDrIsh10c.dll` — `FUN_10003350` (`10003350`)
- **Keywords:** has-strings
- **Strings:** `APPEND`

*(qwen2.5-coder:14b, 10.6s)*

1. **Role**: The function `FUN_10003350` initializes a `CString` object with the string "APPEND" from a predefined memory location.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper function that initializes a string for further processing.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"APPEND"` at offset `0x10011444`.
   - `CString` constructor call: `CString::CString((CString *)&DAT_100118a0, s_APPEND_10011444);`

4. **Next Bite**: Since this function is primarily a string initialization, the next step should be to inspect the callees or the context in which this function is used to understand how the "APPEND" string is utilized in the broader context of EEPROM persistence.

---

## 250. `UdcDrIsh10c.dll` — `FUN_10003510` (`10003510`)
- **Keywords:** has-strings
- **Strings:** `INVALID`

*(qwen2.5-coder:14b, 9.3s)*

1. **Role**: This function initializes a `CString` object with the string "INVALID" from a global data location (`DAT_10011920`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function appears to be setting an error message rather than directly affecting the EEPROM or flash persistence mechanisms.

3. **Key Constants / Opcodes / Calls**: 
   - String: "INVALID" (`s_INVALID_10011468`)
   - Global data: `DAT_10011920`

4. **Next Bite**: Since this function is primarily concerned with setting an error message, the next step should be to trace where this function is called and how it fits into the broader context of the application. Look for any subsequent calls that might involve EEPROM operations or state persistence mechanisms.

---

## 251. `UdcDrIsh10c.dll` — `OkayToWriteImageToDevice` (`10003d00`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.2s)*

1. **Role**: The function `OkayToWriteImageToDevice` is a virtual method in the `CudcDrIshDoc` class that checks if it is permissible to write an image to the device. It returns `1`, indicating that the operation is allowed.

2. **EEPROM / Persistence Mechanism**: This function does not directly handle the mechanics of making state permanent on the radio. It appears to be a transport helper function that checks a condition before allowing an image write operation. It does not involve direct EEPROM/flash commit, lock/unlock, reset, or state persistence operations.

3. **Key Constants / Opcodes / Calls**: The function does not contain any specific hex constants, offsets, error HRESULTs, or callees. It simply returns a constant value (`1`).

4. **Next Bite**: Since this function does not directly interact with EEPROM persistence, the next step should be to inspect the caller of this function or any other functions that might be involved in the image writing process to understand how the actual persistence is managed.

---

## 252. `UdcDrIsh10c.dll` — `GetLastUsedPortName` (`10003d10`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.0s)*

1. **Role**: The function `GetLastUsedPortName` is responsible for retrieving the last used port name associated with the `CudcDrIshDoc` object. It initializes a `CString` object using a pointer to the `this` object plus an offset of `0x1f8`.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper function that retrieves configuration data, possibly used for communication settings, without directly interacting with EEPROM or flash storage.

3. **Key Constants / Opcodes / Calls**: 
   - Offset: `0x1f8` (used to access a member of the `CudcDrIshDoc` object)
   - Callee: `CString::CString` (constructor for the `CString` object)

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence would be the constructor of the `CString` object, specifically how it initializes the string with the data from the `CudcDrIshDoc` object at the offset `0x1f8`. This might involve further calls to other functions that handle the actual data retrieval or storage mechanisms.

---

## 253. `UdcDrIsh10c.dll` — `CreateObject` (`10003d40`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.2s)*

1. **Role**: The `CreateObject` function is responsible for creating and initializing a new instance of the `CudcDrIshDoc` class. It allocates memory for the object using `operator_new` and then calls the constructor `CudcDrIshDoc` to initialize the object.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly handle the mechanics of making state permanent on the radio. It is more of a transport helper function that sets up the object structure necessary for subsequent operations that might involve EEPROM persistence.

3. **Key Constants / Opcodes / Calls**: 
   - `0x1fc`: The size of memory allocated for the new object.
   - `ExceptionList`: Used for exception handling, though no specific exceptions are handled in this snippet.
   - `operator_new`: The function used to allocate memory for the new object.
   - `CudcDrIshDoc`: The constructor called to initialize the newly allocated object.

4. **Next Bite**: The next callee to inspect for EEPROM persistence would be the constructor `CudcDrIshDoc`, as it is responsible for initializing the object and might contain calls to other functions that handle EEPROM operations.

---

## 254. `UdcDrIsh10c.dll` — `GetRuntimeClass` (`10003dc0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.9s)*

1. **Role**: The `GetRuntimeClass` function returns a pointer to the runtime class information for the `CudcDrIshDoc` object. This is typically used in COM (Component Object Model) programming to identify the class of an object at runtime.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with the EEPROM or handle state persistence mechanisms. It appears to be a utility function related to object class identification rather than data storage or commit operations.

3. **Key Constants / Opcodes / Calls**: 
   - `classCudcDrIshDoc`: A pointer to the runtime class structure for `CudcDrIshDoc`.
   - No specific hex constants, opcodes, or error HRESULTs are directly observed in the provided code snippet.

4. **Next Bite**: Since this function is primarily related to COM class identification, the next step should be to inspect the callers of `GetRuntimeClass` to understand how it fits into the overall object model and identify any other functions that might be involved in EEPROM persistence operations.

---

## 255. `UdcDrIsh10c.dll` — `GetMessageMap` (`10003de0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.5s)*

1. **Role**: The `GetMessageMap` function returns a pointer to the message map associated with the `CudcDrIshDoc` class. This message map is used by the MFC framework to map messages to their corresponding handler functions.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly affect the permanent state on the radio. It is a transport helper function that is part of the MFC message handling mechanism and does not involve EEPROM commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**: 
   - `messageMap`: A pointer to the message map structure.
   - No specific hex constants, opcodes, or HRESULTs are observed in the provided code snippet.

4. **Next Bite**: Since this function is a transport helper and does not directly interact with EEPROM persistence, the next step should be to inspect the callees or functions that are directly involved in handling EEPROM operations, such as those related to `ReadIsh`, `WriteIsh`, `Prepare Write`, or `EnterMode/Session`. These functions are more likely to involve the actual mechanics of making state permanent on the radio.

---

## 256. `UdcDrIsh10c.dll` — `OnRdkReadDevice` (`10003df0`)
- **Keywords:** exported, has-strings, named
- **Strings:** `PORT_SELECTION, PORT_SELECTION`

*(qwen2.5-coder:14b, 13.1s)*

1. **Role**: The function `OnRdkReadDevice` appears to handle the reading of a device, possibly related to the radio configuration or state. It retrieves the current thread and, if valid, calls another method `OnRdkReadDevice` on an instance of `CudcDrIshMainFrm`.

2. **EEPROM / Persistence Mechanism**: This function does not directly handle the mechanics of making state permanent on the radio. It seems to be a transport helper or a higher-level function that delegates the actual reading operation to another method. The persistence mechanism is likely handled elsewhere in the code.

3. **Key Constants / Opcodes / Calls**: 
   - `AfxGetThread()`: Retrieves the current thread.
   - `0x7c`: An offset used to access a method pointer in the thread object.
   - `CudcDrIshMainFrm::OnRdkReadDevice`: The method called on the retrieved frame object.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `CudcDrIshMainFrm::OnRdkReadDevice`. This method is likely where the actual reading operation occurs and where the persistence mechanism might be implemented.

---

## 257. `UdcDrIsh10c.dll` — `OnRdkReadDeviceDirect` (`10003e10`)
- **Keywords:** exported, has-strings, named
- **Strings:** `PORT_SELECTION`

*(qwen2.5-coder:14b, 12.1s)*

1. **Role**: This function appears to handle the direct reading of a device, possibly related to the radio's configuration or state. It retrieves the current thread and then calls another function, `OnRdkReadDeviceDirect`, on a frame object.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly manipulate EEPROM or state persistence. It seems to be a transport helper function that delegates the actual reading operation to another method.

3. **Key Constants / Opcodes / Calls**: 
   - `AfxGetThread()`: Retrieves the current thread.
   - `0x7c`: An offset used to access a method pointer in the thread object.
   - `CudcDrIshMainFrm::OnRdkReadDeviceDirect(this_00)`: The actual method that performs the device reading.

4. **Next Bite**: The next function to inspect for EEPROM persistence is `CudcDrIshMainFrm::OnRdkReadDeviceDirect`. This function is likely where the actual reading operation occurs, and it may involve interactions with the radio's EEPROM or state persistence mechanisms.

---

## 258. `UdcDrIsh10c.dll` — `CudcDrIshDoc` (`10003e30`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 16.3s)*

1. **Role**: The function `CudcDrIshDoc::CudcDrIshDoc` is a constructor for the `CudcDrIshDoc` class. It initializes the object by calling the base class constructor and setting up various member variables and virtual function tables.

2. **EEPROM / Persistence Mechanism**: This function does not directly handle the mechanics of making state permanent on the radio. It appears to be a transport helper function that sets up the object for further operations but does not involve direct EEPROM/flash commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**: 
   - Virtual function table pointers: `_vftable__for__CudXchgDoc__`, `_vftable__for__CudcIshPkUp__`, `_vftable__for__CudcIshDbToImage__`
   - Member variable offset: `0x198`, `0x19c`, `0x1f8`
   - HRESULT: `0xffffffff` (indicating an error or failure state)

4. **Next Bite**: The next callees to inspect for EEPROM persistence would be the constructors and methods of the base class `CudcIshDoc` and any methods that interact with the radio's EEPROM or flash memory, such as `CudcIshDoc::CudcIshDoc` and any methods that might involve the opcodes or constants related to EEPROM operations.

---

## 259. `UdcDrIsh10c.dll` — `~CudcDrIshDoc` (`10003f20`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 14.2s)*

1. **Role**: The `~CudcDrIshDoc` function is the destructor for the `CudcDrIshDoc` class. It performs cleanup operations, including setting virtual function tables and calling destructors for member objects.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. It appears to be a transport helper function that ensures proper cleanup of resources and state within the application, which may indirectly affect state persistence by ensuring that all changes are properly committed or rolled back.

3. **Key Constants / Opcodes / Calls**: 
   - Virtual function table pointers (`_vftable__for__CudXchgDoc__`, `_vftable__for__CudcIshPkUp__`, `_vftable__for__CudcIshDbToImage__`).
   - Calls to destructors (`CString::~CString`, `CudcIshDoc::~CudcIshDoc`).

4. **Next Bite**: The next callees to inspect for EEPROM persistence are the destructors called within this function, specifically `CString::~CString` and `CudcIshDoc::~CudcIshDoc`, as they may contain the logic for committing or flushing changes to the radio's memory.

---

## 260. `UdcDrIsh10c.dll` — `InitPortInfo` (`10003f90`)
- **Keywords:** exported, has-strings, named
- **Strings:** `Settings, ReadPort`

*(qwen2.5-coder:14b, 13.7s)*

1. **Role**: The `InitPortInfo` function initializes port information by retrieving the port name and matching it with a list of available port names. It sets up the port index if a match is found.

2. **EEPROM / Persistence Mechanism**: This function does not directly handle EEPROM persistence. It appears to be a transport helper function that sets up port configurations, which may indirectly affect state persistence by ensuring the correct port is used for communication.

3. **Key Constants / Opcodes / Calls**:
   - `0x1f8`: Offset to the `CString` object for the port name.
   - `0x500`: Offset to store the port index.
   - `udcDrXAdkGetPortNamesFromMachine`: Function to retrieve port names from the machine.
   - `FUN_100040e0`: Function to get a port name from the array.
   - `_stricmp`: Function to compare strings case-insensitively.

4. **Next Bite**: The next function to inspect for EEPROM persistence is `udcDrXAdkGetPortNamesFromMachine`, as it retrieves the list of port names which is crucial for setting up the correct communication channel.

---

## 261. `UdcDrIsh10c.dll` — `Serialize` (`10004110`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.8s)*

1. **Role**: The `Serialize` function is a virtual method in the `CudcDrIshDoc` class, intended to serialize the object's state to or from an archive. However, the provided decompiled code does not contain any implementation, suggesting it might be a placeholder or an incomplete method.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not contain any code that directly manipulates EEPROM, flash, or any other persistent storage. It is likely involved in the serialization process, which could be part of a larger mechanism for ensuring state persistence, but without implementation details, its direct role in EEPROM persistence is unclear.

3. **Key Constants / Opcodes / Calls**: None. The function does not contain any specific hex constants, offsets, error HRESULTs, or calls to other functions. It is a simple return statement, indicating no direct interaction with EEPROM or other persistent storage mechanisms.

4. **Next Bite**: Since the `Serialize` function is empty, there are no callees to inspect. To trace EEPROM persistence, one should look at other functions in the `UdcDrIsh10c.dll` that are likely involved in the serialization or deserialization process, such as those that handle the transport layer or interact with the radio's persistent storage.

---

## 262. `UdcDrIsh10c.dll` — `AppGetDeviceCpgVersion` (`10004120`)
- **Keywords:** exported, has-strings, named
- **Strings:** `App must impement AppGetDeviceCpgVersion()`

*(qwen2.5-coder:14b, 11.3s)*

1. **Role**: This function is intended to retrieve the device's CPG (Configuration Programming Guide) version. However, the current implementation simply displays a message box stating "App must impement AppGetDeviceCpgVersion()" and returns 0, indicating that the functionality is not yet implemented.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with the radio's EEPROM or flash memory to make state permanent. It appears to be a placeholder or a stub function that needs to be implemented to provide the actual version information.

3. **Key Constants / Opcodes / Calls**: 
   - String: "App must impement AppGetDeviceCpgVersion()"
   - Function: `AfxMessageBox`

4. **Next Bite**: Since this function is a stub and does not interact with the radio's EEPROM or flash memory, there is no specific callee to inspect next for tracing EEPROM persistence. The implementation of this function should be reviewed to understand how it will interact with the radio's storage mechanisms in the future.

---

## 263. `UdcDrIsh10c.dll` — `AppGetReadWriteVoiceFilesFlag` (`10004140`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.5s)*

1. **Role**: This function, `AppGetReadWriteVoiceFilesFlag`, appears to be a method within the `CudcDrIshDoc` class that returns an integer value. Given its name, it likely checks or retrieves a flag related to the read/write permissions of voice files on the radio.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly interact with EEPROM or flash storage. It returns a constant value (`0`), which suggests it might be a helper function or a placeholder for future implementation. It does not affect permanent state on the radio directly.

3. **Key Constants / Opcodes / Calls**: 
   - The function returns `0`, which is a constant value.
   - No specific hex constants, offsets, error HRESULTs, or callees are observed in the provided code snippet.

4. **Next Bite**: Since the function does not interact with EEPROM or flash storage, there is no immediate next callee to inspect for EEPROM persistence. Further analysis would involve tracing other functions that might interact with the radio's storage or state management.

---

## 264. `UdcDrIsh10c.dll` — `AppGetSysRelVersionStr` (`10004150`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.4s)*

1. **Role**: This function appears to create and return a `CString` object containing the system release version string. It is likely used to provide version information about the system or application.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any other persistent storage mechanisms. It seems to be a utility function for retrieving version information.

3. **Key Constants / Opcodes / Calls**: 
   - `CString::CString(in_stack_00000004, &DAT_10011898)`: This line initializes a `CString` object. The address `&DAT_10011898` likely points to a string containing the version information.

4. **Next Bite**: Since this function does not directly interact with EEPROM or other persistent storage, there is no specific callee to inspect next for tracing EEPROM persistence. However, if the version string is used in other parts of the application to trigger state changes or updates, those areas should be investigated.

---

## 265. `UdcDrIsh10c.dll` — `OpenRadio` (`10004180`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 17.5s)*

1. **Role**: The `OpenRadio` function appears to initialize and configure a radio connection, likely setting up communication parameters and preparing the radio for further operations.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to prepare the radio for operations that may involve state changes, possibly through COM method calls that could indirectly affect EEPROM persistence. It does not explicitly commit changes to EEPROM or flash.

3. **Key Constants / Opcodes / Calls**:
   - COM method calls: `CoCreateInstance`, `GetUUIDList`, `CString::AllocSysString`, `SysFreeString`, `VariantInit`, `VariantClear`.
   - COM interface offsets: `0x154`, `0x124`, `0x15c`, `0x160`, `0x164`.
   - HRESULT check: `-1 < HVar3` to ensure COM method calls succeed.
   - GUID and CString handling: `param_2`, `param_1`.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is the method call at `0x164` (`(**(code **)(*(int *)this + 0x164))(aCStack_58);`). This method likely handles the final steps of opening the radio and could involve setting up state persistence mechanisms.

---

## 266. `UdcDrIsh10c.dll` — `GetUUIDList` (`10004430`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 16.9s)*

1. **Role**: The `GetUUIDList` function appears to retrieve a list of UUIDs associated with the device. It initializes a `CStringList` to store these UUIDs and then populates it by calling an internal method of the `CudcDrIshDoc` class. The function allocates memory for the UUIDs and copies them into the allocated space.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the EEPROM or flash memory to make state permanent. It seems to be a transport helper function that retrieves data from the device without altering its persistent state. The function does not involve any known opcodes for committing changes to EEPROM or locking/unlocking security.

3. **Key Constants / Opcodes / Calls**:
   - `0x11c`: Offset in the vtable for an internal method call.
   - `0xa030`: Error message ID for memory allocation failure.
   - `CoTaskMemAlloc`: Function used to allocate memory for the UUIDs.
   - `AfxMessageBox`: Function used to display an error message if memory allocation fails.

4. **Next Bite**: The next callee to inspect for EEPROM persistence would be the internal method called via the vtable offset `0x11c` (`**(code **)(*(int *)this + 0x11c)`). This method is responsible for populating the `CStringList` with UUIDs and should be analyzed to understand how it interacts with the device's internal state.

---

## 267. `UdcDrIsh10c.dll` — `ReadData` (`100045a0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.6s)*

1. **Role**: The `ReadData` function appears to handle reading data from a device, possibly a radio, based on the provided parameters. It checks if the data should be read from a port and processes the data accordingly.

2. **EEPROM / Persistence Mechanism**: The function does not directly handle EEPROM persistence or commit operations. It seems to be more of a transport helper function that might be involved in the process of reading data that could be used to update or read persistent state on the radio.

3. **Key Constants / Opcodes / Calls**:
   - GUID comparison loop with constants at `DAT_1000b9b0`.
   - COM vtable call at `**(code **)(*(int *)this + 0x140))` which likely involves reading data into a `CByteArray`.
   - No direct EEPROM/flash commit or lock/unlock opcodes are observed.

4. **Next Bite**: The next callee to inspect for EEPROM persistence would be the one at `**(code **)(*(int *)this + 0x140))`, which is responsible for reading data into a `CByteArray`. This function might interact with the underlying storage mechanism, including EEPROM or flash.

---

## 268. `UdcDrIsh10c.dll` — `ReadDataFromDevice` (`10004650`)
- **Keywords:** exported, has-strings, named
- **Strings:** `Invalid file type for reading from device!`

*(qwen2.5-coder:14b, 16.3s)*

1. **Role**: This function is responsible for reading data from a device, specifically handling the case where the file type is not supported by throwing an exception if the file type is not 4.

2. **EEPROM / Persistence Mechanism**: The function does not directly handle EEPROM persistence. It appears to be a transport helper function that opens a radio connection and reads data, but does not explicitly manage EEPROM commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**:
   - `0x10004650`: Function address.
   - `0x10009c92`: Exception handling label.
   - `0x1000b7bc`: Pointer to a label.
   - `0x1000bd28`: Pointer to a `ThrowInfo` structure.
   - `0x6fb5`: Status bar update code.
   - `OpenRadio`: Function call to open a radio connection.
   - `CAdkGenException::CAdkGenException`: Exception constructor call.
   - `CString::CString`: String constructor call.
   - `CString::~CString`: String destructor call.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `OpenRadio`, as it is responsible for establishing a connection to the radio, which is a critical step in any operation that involves reading or writing to the device's EEPROM.

---

## 269. `UdcDrIsh10c.dll` — `AppCanReadFromDevice` (`100047c0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.1s)*

1. **Role**: The function `AppCanReadFromDevice` is a virtual method in the `CudcDrIshDoc` class that checks if the application can read from the device. It returns `1`, indicating that reading is permitted.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It is likely a transport helper function that manages access permissions rather than performing any EEPROM commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**: The function does not contain any specific hex constants, offsets, error HRESULTs, or callees. It simply returns a constant value (`1`).

4. **Next Bite**: Since this function does not perform any EEPROM persistence operations, there are no callees to inspect next for tracing EEPROM persistence. Further analysis should focus on other functions that might interact with the device's EEPROM or state management.

---

## 270. `UdcDrIsh10c.dll` — `GetCodeplugFromDevice` (`100047d0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.8s)*

1. **Role**: This function retrieves the codeplug from a device, initializing and using COM VARIANTARG structures to interact with the device's data.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by interacting with the device's data through COM interfaces. It does not directly commit changes to EEPROM or flash; instead, it prepares data for retrieval or further processing.

3. **Key Constants / Opcodes / Calls**:
   - COM VARIANTARG initialization with `0x2011` type.
   - Calls to `operator_new` and `operator_delete` for memory management.
   - COM method calls through vtable offsets (`0x138` and `0x24`).
   - Potential HRESULT checks for COM method success.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `CopyDataToCpArray`, as it directly manipulates the data retrieved from the device and could involve copying it to a byte array, which might be relevant for understanding how the data is handled and persisted.

---

## 271. `UdcDrIsh10c.dll` — `CopyDataToCpArray` (`10004870`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 15.8s)*

1. **Role**: The `CopyDataToCpArray` function copies data from a `SAFEARRAY` to a `CByteArray`. It handles the conversion of data elements from a variant array to a byte array, ensuring the data is correctly sized and copied.

2. **EEPROM / Persistence Mechanism**: This function is a transport helper. It does not directly manage EEPROM persistence or state commitment on the radio. Instead, it prepares data for further processing, which may involve subsequent operations that handle EEPROM persistence.

3. **Key Constants / Opcodes / Calls**:
   - `SafeArrayAccessData` and `SafeArrayUnaccessData`: These functions are used to access and release the data in the `SAFEARRAY`.
   - `AfxMessageBox`: Used to display error messages if the data access or copying fails.
   - HRESULT `HVar1`: Used to check the success of `SafeArrayAccessData`.
   - `0xa02c` and `0xa02d`: Error message resource IDs.

4. **Next Bite**: The next callees to inspect for EEPROM persistence would be any functions that call `CopyDataToCpArray` and subsequently handle the data for EEPROM operations. Specifically, look for calls to functions related to writing to the EEPROM, such as `WriteIsh` (opcode `0x0101`), or any other functions that involve committing changes to the radio's state.

---

## 272. `UdcDrIsh10c.dll` — `AppGetIshHeaderList` (`10004930`)
- **Keywords:** exported, has-strings, named
- **Strings:** `App must implement AppGetIshHeaderList() on the document class.`

*(qwen2.5-coder:14b, 8.7s)*

1. **Role**: This function is intended to retrieve a list of ISH headers, but it currently displays a message box indicating that the implementation is missing and returns 0.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or manage state persistence. It seems to be a placeholder or a stub that needs implementation.

3. **Key Constants / Opcodes / Calls**: 
   - String: `"App must implement AppGetIshHeaderList() on the document class."`
   - Function: `AfxMessageBox`

4. **Next Bite**: Since this function is a stub, there is no direct next callee to inspect for EEPROM persistence. The implementation of this function should be traced to understand its role in managing state persistence.

---

## 273. `UdcDrIsh10c.dll` — `OnRdkWriteDevice` (`10004950`)
- **Keywords:** exported, has-strings, named
- **Strings:** `device, PORT_SELECTION, PORT_SELECTION`

*(qwen2.5-coder:14b, 14.8s)*

1. **Role**: The function `OnRdkWriteDevice` appears to handle the process of writing device settings to a radio, likely involving user input validation, option selection, and direct device communication.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to manage the state of the application and user interface, possibly preparing data for writing to the device. It does not explicitly show any direct commit or lock/unlock operations on the radio's EEPROM or flash.

3. **Key Constants / Opcodes / Calls**:
   - `s_PORT_SELECTION_1001162c`: A string related to port selection.
   - `DAT_10011898`: A data pointer used for comparison.
   - `udcDrXAdkGetPortFromUser`: A function call that likely retrieves the port from user input.
   - `OnRdkWriteDeviceDirect`: A function call that presumably handles the direct writing of device settings.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `OnRdkWriteDeviceDirect`, as it is the function that likely handles the actual communication with the device to write settings, which could involve EEPROM operations.

---

## 274. `UdcDrIsh10c.dll` — `OnRdkWriteDeviceDirect` (`10004bf0`)
- **Keywords:** exported, has-strings, named
- **Strings:** `device, PORT_SELECTION`

*(qwen2.5-coder:14b, 32.4s)*

1. **Role**: The function `OnRdkWriteDeviceDirect` appears to handle the direct writing of data to a device, likely a radio, by interacting with various components such as UI elements, device interfaces, and data structures. It manages the process of writing data to the device, including handling errors and updating UI status.

2. **EEPROM / Persistence Mechanism**: The function involves several operations that could affect the permanent state on the radio. It includes opening a connection to the device, writing data to partitions, and handling locks and unlocks. The function also calls `WriteToDevice` or `WritePartitionToDevice`, which are likely responsible for the actual data writing to the device's EEPROM or flash memory. Additionally, it manages the state of the device by setting and resetting various flags and calling methods to update the UI.

3. **Key Constants / Opcodes / Calls**:
   - **Hex Constants**: `0xe146`, `0xa02e`, `0x6fcc` (likely error messages or status codes).
   - **Offsets**: `0x128`, `0x158`, `0x198`, `0x19c`, `0x1e0`, `0x1e4`, `0x1e8`, `0x1ec`, `0x1f0`, `0x1f8`, `0x20` (member offsets in the `CudcDrIshDoc` structure).
   - **Error HRESULTs**: `0xffffffff` (indicating an error condition).
   - **Callees**: `FUN_100040e0`, `OpenRadio`, `WriteToDevice`, `WritePartitionToDevice`, `CudcIshDoc::DeleteCpLayout`, `CudcIshDoc::ResetRdkCallingAppInfo`, `CudXchgDoc::SaveModificationLogFile`.

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `WriteToDevice` and `WritePartitionToDevice`. These functions are directly responsible for writing data to the device, and understanding their implementation will provide insights into how the permanent state on the radio is managed.

---

## 275. `UdcDrIsh10c.dll` — `AppCanWriteToDevice` (`100051e0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.5s)*

1. **Role**: The function `AppCanWriteToDevice` appears to be a virtual method in the `CudcDrIshDoc` class that checks if the application can write to the device. It returns an integer value, likely indicating success or failure.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It seems to be a transport helper function that checks permissions or conditions before allowing a write operation. It does not involve direct EEPROM commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**: The function does not contain any specific hex constants, offsets, error HRESULTs, or callees. It simply returns `0`, which could indicate success or failure depending on the context.

4. **Next Bite**: Since this function does not directly interact with EEPROM persistence, the next step would be to inspect the callers of this function to understand how it fits into the overall process of writing to the device. Additionally, examining other functions in the `CudcDrIshDoc` class or related classes might provide more insight into the EEPROM persistence mechanism.

---

## 276. `UdcDrIsh10c.dll` — `GetProtocolsToUse` (`100051f0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.8s)*

1. **Role**: The function `GetProtocolsToUse` retrieves the last used protocol for either reading or writing operations and assigns it to the provided `CString` object. It checks the direction parameter to decide whether to fetch the last read or write protocol.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly handle the mechanics of making state permanent on the radio. It appears to be a transport helper function that fetches protocol information, which is likely used elsewhere in the system to manage state persistence.

3. **Key Constants / Opcodes / Calls**: 
   - `Direction` enum values: `1` for write, `2` for read.
   - Calls to `CudcDrIshMainFrm::GetLastProtocolWrite` and `CudcDrIshMainFrm::GetLastProtocolRead` based on the direction parameter.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `CudcDrIshMainFrm::GetLastProtocolWrite` and `CudcDrIshMainFrm::GetLastProtocolRead`. These functions likely interact with the underlying storage mechanisms to fetch the last used protocols, which could involve EEPROM or flash operations.

---

## 277. `UdcDrIsh10c.dll` — `OnOpenDocument` (`100052a0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.7s)*

1. **Role**: The `OnOpenDocument` function is responsible for handling the opening of a document in the context of the `CudcDrIshDoc` class. It appears to delegate the actual opening process to a base class method and possibly performs additional thread-related operations.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the EEPROM or handle state persistence. It seems to be a transport helper function that may indirectly influence state persistence through thread management or by calling other methods that handle EEPROM operations.

3. **Key Constants / Opcodes / Calls**: 
   - `0x7c` offset in the thread object (`pCVar1`) suggests a vtable call.
   - `CudcIshDoc::OnOpenDocument` is called, which might handle document-specific operations.
   - No specific opcodes or constants related to EEPROM persistence are directly observed in the provided code snippet.

4. **Next Bite**: The next callee to inspect for EEPROM persistence should be `CudcIshDoc::OnOpenDocument`, as it is directly called within the function and might contain the logic for handling document operations, including state persistence mechanisms.

---

## 278. `UdcDrIsh10c.dll` — `SetPathName` (`100052d0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.5s)*

1. **Role**: The `SetPathName` function sets the path name for a document, potentially handling file extensions and updating the port name if the file type is specific (type 4).

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It appears to be a transport helper that may indirectly affect state persistence through file handling and port configuration.

3. **Key Constants / Opcodes / Calls**: 
   - File type check: `FVar2 = CFhAdkFileHandler::GetFileType();` (specifically checks for type 4)
   - COM vtable offset: `0x58` (used to call a method on `this`)
   - COM vtable offset: `0x7c` (used to get the main frame pointer)
   - CString operations: `CString::CString`, `CString::Format`, `CString::~CString`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `CFhAdkFileHandler::GetFileType` and the method called via `this + 0x58`. These are the most likely candidates for handling file-specific operations that could involve EEPROM or flash storage.

---

## 279. `UdcDrIsh10c.dll` — `SetTitle` (`100053e0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.7s)*

1. **Role**: The `SetTitle` function sets the title of a document object, likely used for managing or identifying the document within the application. It appears to be a virtual method that overrides a base class method, possibly from a document handling framework.

2. **EEPROM / Persistence Mechanism**: This function does not directly interact with the radio's EEPROM or flash memory. It is more of a transport helper function that sets the title of a document object, which could be part of a larger process that eventually affects the radio's state. The function calls `CDocument::SetTitle`, which is likely responsible for setting the title in memory, but does not involve any direct EEPROM commit or lock/unlock operations.

3. **Key Constants / Opcodes / Calls**: 
   - The function calls `CudcIshDoc::GetRdkCallingAppInfo`, which retrieves information about the calling application.
   - It then calls `CDocument::SetTitle`, which is a base class method for setting the document title.

4. **Next Bite**: The next callee to inspect for EEPROM persistence would be `CDocument::SetTitle`, as it is responsible for setting the title of the document. This method might be part of a larger process that eventually involves committing changes to the radio's EEPROM or flash memory.

---

## 280. `UdcDrIsh10c.dll` — `OnRdkFileSendMail` (`10005410`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.5s)*

1. **Role**: This function checks a condition and, if met, displays a message box with an error code `0x6fca`. If the condition is not met, it calls the base class method `OnFileSendMail` to handle sending a file via email.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It appears to be a transport helper function that checks a condition and displays an error message if necessary.

3. **Key Constants / Opcodes / Calls**:
   - Error code: `0x6fca`
   - Offset: `0x24`
   - Offset: `-8`
   - Callee: `AfxMessageBox`
   - Callee: `CDocument::OnFileSendMail`

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `CDocument::OnFileSendMail`. This method is part of the base class and may contain logic related to file operations, which could indirectly affect the radio's state.

---

## 281. `UdcDrIsh10c.dll` — `DeleteContents` (`10005430`)
- **Keywords:** exported, has-strings, named
- **Strings:** `Settings, WritePort`

*(qwen2.5-coder:14b, 13.1s)*

1. **Role**: The `DeleteContents` function appears to handle the deletion of settings by writing a profile string to a configuration file. It then calls a base class method to perform additional cleanup.

2. **EEPROM / Persistence Mechanism**: This function does not directly interact with the radio's EEPROM or flash memory. Instead, it writes a setting to a profile file, which is likely used to manage state persistence on the host system. The actual EEPROM commit or lock/unlock operations are not performed here.

3. **Key Constants / Opcodes / Calls**:
   - `s_Settings_1001163c`: A string constant likely representing the section name in the profile file.
   - `s_WritePort_10011648`: A string constant likely representing the key name in the profile file.
   - `CWinApp::WriteProfileStringA`: A function call to write a string to the Windows registry or an INI file.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `CudcIshDoc::DeleteContents`, as it is called at the end of the function and may contain additional logic related to state management or persistence.

---

## 282. `UdcDrIsh10c.dll` — `WritePartitionToDevice` (`10005470`)
- **Keywords:** exported, has-strings, named
- **Strings:** `Waiting on Virtual Radio APIs from Earl...`

*(qwen2.5-coder:14b, 15.8s)*

1. **Role**: This function, `WritePartitionToDevice`, appears to handle the process of writing a partition to a device, likely a radio. It initializes a `VARIANTARG` structure, sets its type, and then calls another function through a vtable pointer. If the call fails, it displays a message box.

2. **EEPROM / Persistence Mechanism**: The function does not directly handle the mechanics of making state permanent on the radio. It seems to be a transport helper function that interacts with a virtual radio API, which is responsible for the actual persistence operations like committing to EEPROM or flash.

3. **Key Constants / Opcodes / Calls**: 
   - `0x14c`: Offset in the object's vtable where the function pointer is located.
   - `0x2010`: Variant type set in the `VARIANTARG` structure.
   - `0xa02a`: Error message box identifier if the operation fails.
   - `s_Waiting_on_Virtual_Radio_APIs_fr_10011654`: String identifier for a message box indicating a wait for virtual radio APIs.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is the function pointed to by the vtable offset `0x14c` in the `this` object. This function is responsible for the actual interaction with the virtual radio API and is likely where the persistence operations are handled.

---

## 283. `UdcDrIsh10c.dll` — `WriteToDevice` (`100054e0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 15.2s)*

1. **Role**: The `WriteToDevice` function appears to handle the process of writing data to a device, likely a radio, by interacting with various COM interfaces and managing memory for data transfer.

2. **EEPROM / Persistence Mechanism**: The function seems to involve preparing data for writing, possibly setting up a buffer, and then using COM interfaces to send this data to the device. It does not directly show explicit EEPROM commit or lock/unlock operations; instead, it relies on other functions or interfaces to manage the persistence of data on the radio.

3. **Key Constants / Opcodes / Calls**:
   - COM vtable offsets: `0x148`, `0x134`, `0x28`
   - HRESULTs: `0xa02f`, `0xa02a`
   - Memory management: `operator_new`, `operator_delete`
   - SafeArray operations: `SafeArrayCreateVectorEx`, `SafeArrayAccessData`, `SafeArrayUnaccessData`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are the functions pointed to by the COM vtable offsets `0x148`, `0x134`, and `0x28`. These are likely responsible for the actual data transfer and persistence operations on the device.

---

## 284. `UdcDrIsh10c.dll` — `GetDataToBeWritten` (`10005660`)
- **Keywords:** exported, has-strings, named
- **Strings:** `Write failed.`

*(qwen2.5-coder:14b, 16.9s)*

1. **Role**: The function `GetDataToBeWritten` appears to prepare data for writing to the radio, likely involving serialization and error handling. It interacts with various classes and methods to ensure data integrity and proper storage.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by preparing data for writing and potentially invoking methods that handle EEPROM/flash commit operations. It does not directly perform commit or reset operations but sets up the data and environment for such actions.

3. **Key Constants / Opcodes / Calls**:
   - `0xa02a`: String resource ID for error messages.
   - `0x10005a30` and `0x10005f30`: Function pointers or offsets related to array initialization.
   - `0x10006070`: Function pointer or offset related to array cleanup.
   - `CudcIshDoc::GetPbtInfoFromApp`: Method to retrieve information about the application.
   - `GetDataToBeWritten`: Recursive call to itself with different parameters.
   - `CFhAdkFileHandler::SaveImage`: Method to save the image to the file handler.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `CFhAdkFileHandler::SaveImage`, as it is directly involved in saving the image, which likely includes committing data to the radio's storage.

---

## 285. `UdcDrIsh10c.dll` — `GetDataToBeWritten` (`100058f0`)
- **Keywords:** exported, has-strings, named
- **Strings:** `Write failed.`

*(qwen2.5-coder:14b, 13.2s)*

1. **Role**: The function `GetDataToBeWritten` appears to be responsible for preparing data to be written to the radio. It likely handles the marshalling of data into a format suitable for transmission or storage.

2. **EEPROM / Persistence Mechanism**: This function is likely a transport helper. It does not directly handle the mechanics of making state permanent on the radio (e.g., EEPROM commit, lock/unlock, reset). Instead, it prepares data for subsequent operations that may involve these actions.

3. **Key Constants / Opcodes / Calls**: 
   - The function calls `FUN_100059cc()`, which is likely a critical function for further processing.
   - The vtable offset `*(int *)(this + 0x19c) + 4` suggests a method call on an object managed by the `this` pointer.
   - The string "Write failed." is referenced, indicating potential error handling related to data writing.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_100059cc()`. This function is likely responsible for further processing the data and potentially interacting with the radio's storage mechanisms.

---

## 286. `UdcDrIsh10c.dll` — `RetryOnWriteFailure` (`10005a00`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.2s)*

1. **Role**: The `RetryOnWriteFailure` function appears to be a virtual method in the `CudcDrIshDoc` class that handles write failures. It returns 0, indicating no action was taken or the operation was successful.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It seems to be a transport helper function that might be involved in retrying write operations but does not perform any EEPROM commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**: The function does not contain any specific hex constants, offsets, error HRESULTs, or callees. It simply returns 0.

4. **Next Bite**: Since this function does not perform any EEPROM persistence operations, there is no specific callee to inspect next for tracing EEPROM persistence. Further analysis should focus on other functions that might be involved in handling write operations and ensuring state persistence.

---

## 287. `UdcDrIsh10c.dll` — `AppEndOfReadFromDevice` (`10005a10`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 15.5s)*

1. **Role**: This function, `AppEndOfReadFromDevice`, is a virtual method in the `CudcDrIshDoc` class that appears to be called at the end of a read operation from a device. It currently does nothing (`return;`), suggesting it might be a placeholder or a method that is intended to be overridden in derived classes.

2. **EEPROM / Persistence Mechanism**: Since the function does not contain any code, it does not directly affect the permanent state on the radio. It is likely a transport helper function that is part of the communication protocol but does not handle EEPROM commit, lock/unlock, or other persistence mechanisms itself.

3. **Key Constants / Opcodes / Calls**: None observed in the provided code snippet. The function signature includes parameters like `int param_1`, `IVirtualRadio *param_2`, and `CByteArray *param_3`, but no specific constants, opcodes, or calls are present.

4. **Next Bite**: Since this function does not contain any calls or operations related to EEPROM persistence, there is no specific callee to inspect next. The next step would be to look at other functions in the `CudcDrIshDoc` class or related classes that might handle the actual persistence mechanisms, such as those involving opcodes like `0x0106` (EnterMode/Session) or `0x0107` (UnlockSecurity).

---

## 288. `UdcDrIsh10c.dll` — `AppGetBaudRate` (`10005a20`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.9s)*

1. **Role**: The `AppGetBaudRate` function appears to be a method within the `CudcDrIshDoc` class that returns a constant value of `1`. This suggests it might be a placeholder or a stub function, possibly returning a default baud rate or a success status code.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanisms. It seems to be a utility function that provides a constant value, likely used in a larger context to manage communication settings or status.

3. **Key Constants / Opcodes / Calls**: The function does not contain any specific hex constants, offsets, error HRESULTs, or callees. It simply returns `1`.

4. **Next Bite**: Since this function does not interact with EEPROM or persistence mechanisms, there is no immediate next callee to inspect for tracing EEPROM persistence. The focus should shift to other functions within the `UdcDrIsh10c.dll` that might involve communication or state management, particularly those that interact with the radio's EEPROM or flash memory.

---

## 289. `UdcDrIsh10c.dll` — `FUN_100062e0` (`100062e0`)
- **Keywords:** has-strings
- **Strings:** `FALSE`

*(qwen2.5-coder:14b, 13.1s)*

1. **Role**: The function `FUN_100062e0` initializes a `CString` object with the string "FALSE" from the global data at `DAT_100119b0`.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper function that initializes a string, which could be used in communication or logging but does not involve EEPROM commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"FALSE"` at `s_FALSE_10011424`.
   - Global data reference: `DAT_100119b0`.

4. **Next Bite**: Since this function is primarily a string initialization, the next step should be to inspect the callees or the context in which this function is used to understand how it might indirectly influence EEPROM persistence. Look for calls to other functions that handle communication or state management, such as those involving opcodes like `0x0106` (EnterMode/Session) or `0x0107` (UnlockSecurity).

---

## 290. `UdcDrIsh10c.dll` — `FUN_10006320` (`10006320`)
- **Keywords:** has-strings
- **Strings:** `FALSE`

*(qwen2.5-coder:14b, 9.6s)*

1. **Role**: This function initializes a `CString` object with the string "FALSE" from a global data location (`DAT_1001195c`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanism. It appears to be a helper function for string initialization.

3. **Key Constants / Opcodes / Calls**: 
   - String: "FALSE" (`s_FALSE_10011424`)
   - Global data: `DAT_1001195c`

4. **Next Bite**: Since this function is primarily a string initialization helper, there is no direct call to inspect for EEPROM persistence. The next step would be to trace the call stack to see where this function is used and what other functions it might interact with that could involve EEPROM operations.

---

## 291. `UdcDrIsh10c.dll` — `FUN_100063a0` (`100063a0`)
- **Keywords:** has-strings
- **Strings:** `DISPLAY_LAST`

*(qwen2.5-coder:14b, 12.7s)*

1. **Role**: The function `FUN_100063a0` initializes a `CString` object with the string "DISPLAY_LAST" from the global data at `DAT_1001198c`.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper function that sets up a display string, which is likely used in the user interface of the CPS/NextGen10/ByteData10 application.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"DISPLAY_LAST"` at `s_DISPLAY_LAST_10011434`.
   - Global data reference: `DAT_1001198c`.

4. **Next Bite**: Since this function is primarily a string initialization, the next step should be to inspect the caller of `FUN_100063a0` to understand how it is used in the context of the application. Additionally, tracing the lifecycle of the `CString` object and any subsequent operations on it might provide insights into how it interacts with the radio's state.

---

## 292. `UdcDrIsh10c.dll` — `FUN_100063e0` (`100063e0`)
- **Keywords:** has-strings
- **Strings:** `APPEND`

*(qwen2.5-coder:14b, 12.2s)*

1. **Role**: The function `FUN_100063e0` initializes a `CString` object with the string "APPEND" from a predefined location in memory (`s_APPEND_10011444`).

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a helper function for string manipulation and does not involve EEPROM commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `s_APPEND_10011444`
   - Data structure: `CString`
   - Initialization: `CString::CString((CString *)&DAT_1001194c, s_APPEND_10011444)`

4. **Next Bite**: Since this function is primarily involved in string initialization, the next step should be to inspect the callees or the context in which this function is used to understand how it might indirectly contribute to EEPROM persistence. Look for calls to functions that handle EEPROM operations or state management.

---

## 293. `UdcDrIsh10c.dll` — `FUN_100065a0` (`100065a0`)
- **Keywords:** has-strings
- **Strings:** `INVALID`

*(qwen2.5-coder:14b, 10.4s)*

1. **Role**: This function initializes a `CString` object with the string "INVALID" from a global data location (`DAT_100119cc`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanism. It appears to be a helper function for error handling or string initialization.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `s_INVALID_10011468`
   - Global data location: `DAT_100119cc`
   - Function call: `CString::CString`

4. **Next Bite**: Since this function is primarily involved in string initialization and does not directly interact with EEPROM or persistence, the next step should be to trace the call stack to see where this function is invoked and how it fits into the overall process. Look for higher-level functions that might involve EEPROM operations or state persistence.

---

## 294. `UdcDrIsh10c.dll` — `FUN_10006da0` (`10006da0`)
- **Keywords:** has-strings
- **Strings:** `FALSE`

*(qwen2.5-coder:14b, 9.7s)*

1. **Role**: This function initializes a `CString` object with the string "FALSE" from a global data location (`DAT_10011a5c`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanism. It appears to be a helper function for string manipulation.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"FALSE"` at `s_FALSE_10011424`.
   - Global data reference: `DAT_10011a5c`.

4. **Next Bite**: Since this function is primarily a string initialization helper, the next step should be to trace the call stack to see where this function is used and how it might indirectly affect EEPROM persistence. Look for calls to other functions that handle EEPROM operations or state management.

---

## 295. `UdcDrIsh10c.dll` — `FUN_10006de0` (`10006de0`)
- **Keywords:** has-strings
- **Strings:** `FALSE`

*(qwen2.5-coder:14b, 10.1s)*

1. **Role**: This function initializes a `CString` object with the string "FALSE" at a specific memory location (`DAT_10011a08`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It appears to be a helper function for setting a string value, possibly related to configuration or status reporting.

3. **Key Constants / Opcodes / Calls**: 
   - String: "FALSE" (`s_FALSE_10011424`)
   - Memory location: `DAT_10011a08`

4. **Next Bite**: Since this function is primarily a string initialization, the next step should be to trace where `DAT_10011a08` is used or referenced. This will likely lead to a more relevant function that interacts with EEPROM or handles state persistence.

---

## 296. `UdcDrIsh10c.dll` — `FUN_10006e60` (`10006e60`)
- **Keywords:** has-strings
- **Strings:** `DISPLAY_LAST`

*(qwen2.5-coder:14b, 11.4s)*

1. **Role**: The function `FUN_10006e60` initializes a `CString` object with the string "DISPLAY_LAST" from the global data at `DAT_10011a38`.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper function that sets up a display string, which is likely used in the user interface of the CPS/NextGen10/ByteData10 application.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"DISPLAY_LAST"` at `s_DISPLAY_LAST_10011434`.
   - Global data reference: `DAT_10011a38`.

4. **Next Bite**: Since this function is primarily involved in setting up a display string, the next step should be to inspect the callees or the context in which this function is called to understand how it interacts with other parts of the application that might affect EEPROM persistence.

---

## 297. `UdcDrIsh10c.dll` — `FUN_10006ea0` (`10006ea0`)
- **Keywords:** has-strings
- **Strings:** `APPEND`

*(qwen2.5-coder:14b, 9.5s)*

1. **Role**: The function `FUN_10006ea0` initializes a `CString` object with the string "APPEND" from a global data location.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper function that initializes a string for further processing.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"APPEND"` at offset `0x10011444`.
   - Global data reference: `DAT_100119f8`.

4. **Next Bite**: Since this function initializes a string, the next step should be to inspect the callees or functions that use this `CString` object, particularly those that might involve communication or data handling related to the radio's EEPROM or state persistence.

---

## 298. `UdcDrIsh10c.dll` — `FUN_10007060` (`10007060`)
- **Keywords:** has-strings
- **Strings:** `INVALID`

*(qwen2.5-coder:14b, 10.0s)*

1. **Role**: This function initializes a `CString` object with the string "INVALID" from a global data location (`DAT_10011a78`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with the radio's EEPROM or flash memory. It appears to be a helper function for error handling or string management.

3. **Key Constants / Opcodes / Calls**: 
   - String: "INVALID" (`s_INVALID_10011468`)
   - Global data: `DAT_10011a78`

4. **Next Bite**: Since this function is primarily concerned with string initialization, the next step should be to trace the call stack to see where this function is invoked and how it fits into the overall process. Look for any subsequent calls that might involve EEPROM operations or state persistence mechanisms.

---

## 299. `UdcDrIsh10c.dll` — `CreateObject` (`10007850`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.8s)*

1. **Role**: The `CreateObject` function is responsible for creating and initializing an instance of the `CudcDrIshMainFrm` class. It allocates memory for the object and calls the constructor to set it up.

2. **EEPROM / Persistence Mechanism**: This function does not directly interact with the EEPROM or handle state persistence on the radio. It appears to be a transport helper function that manages object creation rather than state commitment or locking mechanisms.

3. **Key Constants / Opcodes / Calls**: 
   - `0x4a8`: The size of memory allocated for the `CudcDrIshMainFrm` object.
   - `ExceptionList`: Used for exception handling, though no specific exceptions are handled in this snippet.
   - `operator_new`: The function used to allocate memory for the object.
   - `CudcDrIshMainFrm(this)`: The constructor call for the `CudcDrIshMainFrm` class.

4. **Next Bite**: The next callee to inspect for EEPROM persistence would be the constructor `CudcDrIshMainFrm(this)`, as it is responsible for initializing the object and may contain calls to other functions that handle state persistence or interaction with the radio's EEPROM.

---

## 300. `UdcDrIsh10c.dll` — `GetRuntimeClass` (`100078c0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.7s)*

1. **Role**: The `GetRuntimeClass` function returns a pointer to the runtime class information for the `CudcDrIshMainFrm` object. This is typically used in MFC (Microsoft Foundation Classes) applications to identify the class type at runtime.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with the EEPROM or handle state persistence mechanisms. It appears to be a utility function for class identification rather than managing permanent state on the radio.

3. **Key Constants / Opcodes / Calls**: 
   - `classCudcDrIshMainFrm`: A pointer to the runtime class structure for `CudcDrIshMainFrm`.
   - No specific hex constants, opcodes, or error HRESULTs are directly observed in the provided code snippet.

4. **Next Bite**: Since this function is primarily involved in class identification, the next step would be to inspect the callers of `GetRuntimeClass` to see if they interact with the radio's EEPROM or state persistence mechanisms. Additionally, examining other functions within the same class or related classes might provide more insight into how state persistence is managed.

---

## 301. `UdcDrIsh10c.dll` — `GetMessageMap` (`100078e0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.5s)*

1. **Role**: The `GetMessageMap` function returns a pointer to the message map associated with the `CudcDrIshMainFrm` class. This message map is used by the MFC framework to map Windows messages to member functions of the class.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function itself does not directly interact with the EEPROM or handle state persistence. It is a standard MFC function used for message handling and does not involve any specific operations related to committing changes to the radio's EEPROM or managing state persistence.

3. **Key Constants / Opcodes / Calls**: 
   - `AFX_MSGMAP *`: The return type indicates a pointer to an `AFX_MSGMAP` structure.
   - `messageMap`: A static member variable of the `CudcDrIshMainFrm` class that holds the message map.

4. **Next Bite**: Since this function is primarily involved in message handling and does not directly interact with EEPROM or state persistence, the next step would be to inspect the callees or other functions that are directly involved in handling messages related to EEPROM operations, such as those that might call `ReadIsh`, `WriteIsh`, or other opcodes related to state persistence.

---

## 302. `UdcDrIsh10c.dll` — `CudcDrIshMainFrm` (`100078f0`)
- **Keywords:** exported, has-strings, named
- **Strings:** `Settings, Settings, LastProtocolWrite, LastProtocolRead`

*(qwen2.5-coder:14b, 16.0s)*

1. **Role**: This function initializes a `CudcDrIshMainFrm` object, setting up various string members and retrieving settings from the Windows registry using `GetProfileStringA`.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. It appears to be a transport helper function that initializes settings and does not involve any direct commit or lock/unlock operations on the radio's persistent storage.

3. **Key Constants / Opcodes / Calls**:
   - `0x498`, `0x49c`, `0x4a0`: Offsets for CString members.
   - `s_Settings_1001163c`, `s_LastProtocolRead_100116a8`, `s_LastProtocolWrite_10011694`: Strings used for registry keys.
   - `CWinApp::GetProfileStringA`: Function call to retrieve settings from the Windows registry.
   - `CString::CString`, `CString::operator=`, `CString::~CString`: CString operations for string initialization and cleanup.

4. **Next Bite**: Since this function does not directly interact with the radio's persistent storage, the next step should be to inspect the callees that handle actual communication with the radio, such as functions related to `ReadIsh`, `WriteIsh`, or `EnterMode`, to trace how EEPROM persistence is managed.

---

## 303. `UdcDrIsh10c.dll` — `~CudcDrIshMainFrm` (`10007a60`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.6s)*

1. **Role**: This function is the destructor for the `CudcDrIshMainFrm` class. It is responsible for cleaning up resources associated with an instance of this class, including calling destructors for `CString` objects and the base class destructor.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. It appears to be a transport helper function that ensures proper cleanup of resources, which may indirectly contribute to state persistence by ensuring that all changes are properly finalized before the object is destroyed.

3. **Key Constants / Opcodes / Calls**:
   - Offsets: `0x4a0`, `0x49c`, `0x498`
   - Calls: `CString::~CString`, `CudcIshMainFrm::~CudcIshMainFrm`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `CString::~CString` and `CudcIshMainFrm::~CudcIshMainFrm`, as they may contain logic related to resource cleanup and state persistence.

---

## 304. `UdcDrIsh10c.dll` — `OnClose` (`10007ae0`)
- **Keywords:** exported, has-strings, named
- **Strings:** `Settings, Settings, Settings, LastProtocolWrite, LastProtocolRead, ReadPort`

*(qwen2.5-coder:14b, 15.3s)*

1. **Role**: The `OnClose` function writes settings related to the read port, last protocol read, and last protocol write to the Windows registry under the "Settings" section. It then calls the base class `OnClose` method to perform any additional cleanup or closing operations.

2. **EEPROM / Persistence Mechanism**: This function indirectly affects the permanent state on the radio by writing configuration settings to the Windows registry. It does not directly interact with the radio's EEPROM or flash memory. The settings written might be used to restore the state of the application upon the next launch, but it does not explicitly commit changes to the radio's hardware.

3. **Key Constants / Opcodes / Calls**:
   - Strings: "Settings", "ReadPort", "LastProtocolRead", "LastProtocolWrite"
   - Function: `CWinApp::WriteProfileStringA`
   - Offset: `0x498`, `0x49c`, `0x4a0`
   - Indirectly related to: `CUiMFrmWnd::OnClose`

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence would be `CWinApp::WriteProfileStringA`, as it is responsible for writing the settings to the Windows registry. Understanding how this function interacts with the Windows registry and any subsequent calls it makes could provide insights into how the application manages state persistence.

---

## 305. `UdcDrIsh10c.dll` — `OnRdkReadDeviceFromCmdLine` (`10007b70`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 26.8s)*

1. **Role**: This function appears to handle reading a device from the command line, setting up temporary file names, and performing file operations. It initializes and manipulates strings and files, but does not directly interact with the radio's EEPROM or flash memory.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly affect the permanent state on the radio. It seems to be more focused on file handling and command-line processing rather than interacting with the radio's EEPROM or flash memory.

3. **Key Constants / Opcodes / Calls**:
   - `0x4a4` and `0x494`: Offsets used to store values in the `this` pointer.
   - `0x1000`: Mode flag for file operations.
   - `0x104`: Buffer size for `GetTempPathA`.
   - `CudcDrIshCmdLine::GetPortIndex`, `CudcDrIshCmdLine::GetPortName`, `CudcDrIshCmdLine::GetProtocolRead`: Functions to retrieve command-line parameters.
   - `udcDrXAdkCreateTmpFileNameForReadingDevice`: Function to create a temporary file name.
   - `GetTempPathA`: Retrieves the path to the directory for temporary files.
   - `CString::CString`, `CString::Format`, `CString::operator=`, `CString::~CString`: CString class methods for string manipulation.
   - `CFile::CFile`, `CFile::Close`, `CFile::Remove`, `CFile::~CFile`: CFile class methods for file operations.
   - `AfxGetModuleState`: Retrieves the current module state.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are:
   - `CudcDrIshCmdLine::GetPortIndex`, `CudcDrIshCmdLine::GetPortName`, `CudcDrIshCmdLine::GetProtocolRead`: These functions might interact with the radio's configuration or settings, which could indirectly affect EEPROM persistence.
   - `udcDrXAdkCreateTmpFileNameForReadingDevice`: This function might be part of a larger process that involves reading from or writing to the radio, which could involve EEPROM operations.
   - `AfxGetModuleState`: This function might be used to retrieve the current state of the application, which could be related to EEPROM persistence.

---

## 306. `UdcDrIsh10c.dll` — `GetPortName` (`10007d20`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.2s)*

1. **Role**: The `GetPortName` function appears to be a member function of the `CudcDrIshMainFrm` class, responsible for retrieving the port name associated with the object. It initializes a `CString` object using a pointer to the current object (`this`) and an offset (`0x498`).

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It seems to be a transport helper function, possibly used to obtain the port name for communication purposes without altering the EEPROM or flash state.

3. **Key Constants / Opcodes / Calls**: 
   - Offset: `0x498`
   - Callee: `CString::CString`

4. **Next Bite**: Since this function is primarily a transport helper, the next step should be to inspect the `CString::CString` constructor or any other methods called by `GetPortName` to understand how the port name is used in the context of communication.

---

## 307. `UdcDrIsh10c.dll` — `GetLastProtocolRead` (`10007d50`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.7s)*

1. **Role**: The function `GetLastProtocolRead` appears to initialize a `CString` object using a pointer to a member of the `CudcDrIshMainFrm` class. It likely retrieves or constructs a string representation of the last protocol read operation.

2. **EEPROM / Persistence Mechanism**: This function does not directly interact with the EEPROM or flash memory to make state permanent. It seems to be a transport helper function that deals with string manipulation rather than storage operations.

3. **Key Constants / Opcodes / Calls**: 
   - The function uses the offset `0x49c` to access a member of the `CudcDrIshMainFrm` class.
   - The `CString::CString` constructor is called with the address of the `CString` object and a pointer to the member at offset `0x49c`.

4. **Next Bite**: Since this function is primarily involved in string manipulation, the next step should be to inspect the member at offset `0x49c` to understand what data it holds and how it relates to the protocol read operations. Additionally, tracing the constructor of `CString` and any other methods called within this function might provide more insight into how the string is constructed and used.

---

## 308. `UdcDrIsh10c.dll` — `GetLastProtocolWrite` (`10007d80`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 14.9s)*

1. **Role**: The function `GetLastProtocolWrite` appears to initialize a `CString` object using a pointer to a member of the `CudcDrIshMainFrm` class. It likely retrieves or constructs a string representation of the last protocol write operation.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that deals with string manipulation rather than state persistence mechanisms like commit, lock/unlock, or reset.

3. **Key Constants / Opcodes / Calls**: 
   - The function uses the offset `0x4a0` to access a member of the `CudcDrIshMainFrm` class.
   - The `CString::CString` constructor is called with a pointer to the `CString` object and a pointer to the member at offset `0x4a0`.

4. **Next Bite**: Since the function is primarily involved in string manipulation, the next step should be to inspect the member at offset `0x4a0` within the `CudcDrIshMainFrm` class to understand what data it holds and how it relates to the last protocol write operation. Additionally, tracing the call to `CString::CString` and any other member functions of `CString` might provide more insight into how the string is constructed and used.

---

## 309. `UdcDrIsh10c.dll` — `SetLastProtocolRead` (`10007db0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 9.7s)*

1. **Role**: The `SetLastProtocolRead` function sets the last protocol read value in the `CudcDrIshMainFrm` object by copying the provided `CString` parameter into a member variable at an offset of `0x49c`.

2. **EEPROM / Persistence Mechanism**: This function is a transport helper that indirectly affects the permanent state on the radio by updating internal state tracking. It does not directly involve EEPROM commit, lock/unlock, reset, or state persistence operations.

3. **Key Constants / Opcodes / Calls**: 
   - Offset: `0x49c`
   - Callee: `CString::operator=`

4. **Next Bite**: Since this function is a transport helper, the next step should be to inspect the callees of `CString::operator=` to trace how the state is ultimately persisted or committed to the radio.

---

## 310. `UdcDrIsh10c.dll` — `SetLastProtocolWrite` (`10007dd0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.3s)*

1. **Role**: The `SetLastProtocolWrite` function sets the last protocol write value in the `CudcDrIshMainFrm` object by copying the provided `CString` parameter into a member variable at an offset of `0x4a0`.

2. **EEPROM / Persistence Mechanism**: This function is likely a transport helper that indirectly affects the permanent state on the radio by updating internal state that may be used in subsequent operations to ensure data consistency and persistence. It does not directly interact with EEPROM or flash commit operations.

3. **Key Constants / Opcodes / Calls**: 
   - Offset: `0x4a0` (where the `CString` is copied)
   - No specific hex constants, opcodes, or HRESULTs observed in the provided code snippet.

4. **Next Bite**: Since this function is a transport helper, the next step should be to inspect the callees or methods that are invoked after `SetLastProtocolWrite` to understand how the updated state is used in the context of EEPROM persistence. Look for calls to functions that handle communication with the radio or manage the state of the device.

---

## 311. `UdcDrIsh10c.dll` — `GetLastUsedPortIndex` (`10007df0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 14.1s)*

1. **Role**: The function `GetLastUsedPortIndex` retrieves the index of the last used port from an internal data structure within the `CudcDrIshMainFrm` object. This index is likely used to manage or reference different communication ports or interfaces.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly affect the permanent state on the radio. It appears to be a helper function that retrieves configuration data, which could be used in other operations that involve state persistence. The actual persistence mechanism would be in other functions that use this index to perform operations like reading or writing to EEPROM or flash.

3. **Key Constants / Opcodes / Calls**: 
   - The function accesses an integer value at an offset of `0x494` from the `this` pointer. This offset likely points to a member variable that stores the last used port index.
   - No specific opcodes, HRESULTs, or other constants are directly observed in the provided code snippet.

4. **Next Bite**: To trace EEPROM persistence, the next callees to inspect would be functions that use the port index returned by `GetLastUsedPortIndex` to perform operations on the radio's EEPROM or flash. These could include functions related to reading, writing, or locking/unlocking EEPROM/flash segments.

---

## 312. `UdcDrIsh10c.dll` — `IsReadFromPort` (`10007e00`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.8s)*

1. **Role**: The function `IsReadFromPort` checks a boolean value stored at a specific offset (`0x4a4`) within the `CudcDrIshMainFrm` object to determine if a read operation is in progress from a port.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It is likely a transport helper function used to manage read operations, possibly in conjunction with other mechanisms to ensure data integrity and persistence.

3. **Key Constants / Opcodes / Calls**: 
   - Offset: `0x4a4`
   - No specific opcodes or HRESULTs are observed in the provided code snippet.

4. **Next Bite**: Since this function is a simple getter, the next step would be to inspect the class or methods that modify the boolean value at offset `0x4a4`. This could provide insights into how read operations are managed and potentially how they relate to EEPROM persistence mechanisms.

---

## 313. `UdcDrIsh10c.dll` — `OnRdkReadDeviceDirect` (`10007e10`)
- **Keywords:** exported, has-strings, named
- **Strings:** `PORT_SELECTION`

*(qwen2.5-coder:14b, 18.6s)*

1. **Role**: The function `OnRdkReadDeviceDirect` appears to handle the reading of device data directly, possibly from a configuration file or command line. It checks for a specific port selection, processes command line arguments, and initializes a command line object to read device data.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the EEPROM or flash storage to make state permanent. It seems to be more of a transport helper function, managing the flow of data and possibly setting up conditions for subsequent operations that might affect the radio's state.

3. **Key Constants / Opcodes / Calls**:
   - `s_PORT_SELECTION_1001162c`: A string related to port selection.
   - `DAT_10011898`: A data pointer used in a comparison loop.
   - `0xe146`: An error message or HRESULT value.
   - `FUN_100040e0`, `FUN_10008080`: Function pointers or callees.
   - `CudcDrIshCmdLine::CudcDrIshCmdLine`: Constructor for a command line object.
   - `OnRdkReadDevice`, `OnRdkReadDeviceFromCmdLine`: Other functions called within this function.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `OnRdkReadDevice` and `OnRdkReadDeviceFromCmdLine`. These functions are likely responsible for the actual reading of device data and could involve operations that affect the radio's permanent state.

---

## 314. `UdcDrIsh10c.dll` — `OnRdkReadDevice` (`100080a0`)
- **Keywords:** exported, has-strings, named
- **Strings:** `PORT_SELECTION, PORT_SELECTION`

*(qwen2.5-coder:14b, 17.1s)*

1. **Role**: This function appears to handle the reading of device information, likely from a radio device, and involves user interaction and configuration settings. It checks for file open permissions, retrieves user options, and processes command-line arguments.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. It seems to be more of a transport helper, managing communication and configuration settings without explicitly committing changes to permanent storage. It may indirectly affect persistence through configuration management and user interaction.

3. **Key Constants / Opcodes / Calls**:
   - `s_PORT_SELECTION_1001162c`: A string related to port selection.
   - `DAT_10011898`: A byte array used for comparison.
   - `uiCanFileOpen()`: Checks if a file can be opened.
   - `AfxMessageBox(0xe146,0x10,0xffffffff)`: Displays a message box.
   - `udcDrXAdkGetPortFromUser`: Gets port information from the user.
   - `OnRdkReadDeviceFromCmdLine`: Processes command-line arguments.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `OnRdkReadDeviceFromCmdLine`. This function likely handles the actual reading of device information and could involve interactions with the radio's storage or configuration.

---

## 315. `UdcDrIsh10c.dll` — `SetReadPortName` (`100083a0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.3s)*

1. **Role**: The `SetReadPortName` function sets the read port name for the `CudcDrIshMainFrm` object by copying the provided `CString` parameter into the object's internal `CString` member at offset `0x498`.

2. **EEPROM / Persistence Mechanism**: This function is a transport helper that sets the read port name but does not directly affect the permanent state on the radio. It is likely used in conjunction with other functions to manage communication settings.

3. **Key Constants / Opcodes / Calls**: 
   - No specific hex constants, offsets, error HRESULTs, or callees are observed in the provided code snippet.

4. **Next Bite**: Since this function is primarily a setter for the read port name, the next callees to inspect for EEPROM persistence should be those that interact with the radio's communication settings or directly manage the radio's state, such as functions related to `EnterMode`, `OP_LOCK`, `OP_UNLOCK`, or `UnlockSecurity`.

---

## 316. `UdcDrIsh10c.dll` — `IsThisDeveloperOptionSet` (`100083c0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.0s)*

1. **Role**: This function checks if a specific developer option is set by performing a bitwise AND operation between a member variable `m_uDeveloperOptions` and the input parameter `param_1`, which represents the developer option to check.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It is a helper function used to determine the state of developer options, which may influence other operations that do affect persistence.

3. **Key Constants / Opcodes / Calls**: The function uses the bitwise AND operator (`&`) and does not involve any specific hex constants, offsets, error HRESULTs, or direct calls to other functions related to EEPROM persistence.

4. **Next Bite**: Since this function is a simple bitwise check, the next step should be to inspect the callers of `IsThisDeveloperOptionSet` to understand how the developer options influence other operations that might affect EEPROM persistence.

---

## 317. `UdcDrIsh10c.dll` — `SetDeveloperOptions` (`100083d0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 15.8s)*

1. **Role**: The `SetDeveloperOptions` function updates the developer options by setting specific bits in the `m_uDeveloperOptions` variable based on the input parameter `param_1`. This function is likely used to enable or configure various developer-specific features or settings.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly interact with the EEPROM or flash storage to make changes permanent. It appears to be a configuration function that sets internal flags, which may influence other parts of the system that handle EEPROM persistence. The actual persistence mechanism would likely be handled elsewhere in the codebase, possibly involving opcodes like `0x0106` (EnterMode/Session) or `0x0107` (UnlockSecurity), but this function does not directly perform any EEPROM operations.

3. **Key Constants / Opcodes / Calls**: 
   - `m_uDeveloperOptions`: A variable that holds the current developer options.
   - `param_1`: An input parameter representing the developer option to be set.
   - No specific hex constants, offsets, error HRESULTs, or callees are directly observed in the provided code snippet.

4. **Next Bite**: Since the function does not directly interact with EEPROM, the next step would be to trace how `m_uDeveloperOptions` is used elsewhere in the code. Look for functions that read or process `m_uDeveloperOptions` and check if they involve any EEPROM operations or calls to other functions that might handle persistence.

---

## 318. `UdcDrIsh10c.dll` — `AppGetPortNames` (`100083f0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 11.3s)*

1. **Role**: The `AppGetPortNames` function is responsible for retrieving and setting the port names associated with the radio. It initializes a `CStringArray` and calls another function to populate it with port names.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It is a transport helper function that deals with communication port names, which are not directly related to EEPROM or flash commit operations.

3. **Key Constants / Opcodes / Calls**: 
   - The function calls `CStringArray::SetSize` with parameters `0` and `-1`.
   - It calls `udcDrXAdkGetPortNamesFromMachine`, which is likely responsible for fetching the port names.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `udcDrXAdkGetPortNamesFromMachine`. This function is likely responsible for interacting with the underlying hardware or system to retrieve the port names, and understanding its implementation may provide insights into how the radio's state is managed.

---

## 319. `UdcDrIsh10c.dll` — `InitPortInfo` (`10008410`)
- **Keywords:** exported, has-strings, named
- **Strings:** `Settings, ReadPort`

*(qwen2.5-coder:14b, 14.0s)*

1. **Role**: The `InitPortInfo` function initializes port information by reading settings from the profile and comparing them with available port names. It sets up the port index if a match is found.

2. **EEPROM / Persistence Mechanism**: This function is primarily a transport helper. It does not directly handle EEPROM persistence or commit operations. Instead, it prepares the environment by setting up the port index, which is crucial for subsequent operations that might involve EEPROM writes or reads.

3. **Key Constants / Opcodes / Calls**:
   - **Strings**: "Settings", "ReadPort"
   - **Function Calls**: `CWinApp::GetProfileStringA`, `udcDrXAdkGetPortNamesFromMachine`, `FUN_100040e0`
   - **Offset**: `0x498`, `0x494`
   - **HRESULT**: `0xffffffff` (used for error handling)

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `udcDrXAdkGetPortNamesFromMachine`. This function likely retrieves the list of available port names, which is a critical step in setting up the correct port for subsequent operations that might involve EEPROM writes or reads.

---

## 320. `UdcDrIsh10c.dll` — `AppGetOtapDifWriteRadio` (`10008560`)
- **Keywords:** exported, has-strings, named
- **Strings:** `OTAP_DIF_WRITE_RADIO`

**ERROR querying homelab AI:** `timed out`

---

## 321. `UdcDrIsh10c.dll` — `AppGetOtapSessInactTimer` (`10008670`)
- **Keywords:** exported, has-strings, named
- **Strings:** `TIMER_SESS_INACT`

*(qwen2.5-coder:14b, 13.1s)*

1. **Role**: This function retrieves the inactivity timer value for an OTAP (Over-The-Air Programming) session from the radio settings. It constructs a CString with the key "TIMER_SESS_INACT" and uses it to fetch the corresponding option value from the radio settings.

2. **EEPROM / Persistence Mechanism**: The function does not directly affect the permanent state on the radio. It appears to be a transport helper function that retrieves configuration settings without making any changes to the EEPROM or flash memory. It does not involve any locking, unlocking, committing, or resetting operations.

3. **Key Constants / Opcodes / Calls**:
   - String: `"TIMER_SESS_INACT"`
   - String: `"OTAP_SESS_INACT"`
   - Function: `CUiMFrmWnd::GetOptionValue`
   - Function: `atoi`

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `CUiMFrmWnd::GetOptionValue`. This function is likely responsible for interacting with the radio to fetch the option value, and understanding its implementation will provide more insight into how the radio's settings are retrieved and managed.

---

## 322. `UdcDrIsh10c.dll` — `AppGetOtapRadioIPAddress` (`10008750`)
- **Keywords:** exported, has-strings, named
- **Strings:** `OTAP_RADIO_IP_ADDR`

*(qwen2.5-coder:14b, 12.5s)*

1. **Role**: This function retrieves the OTAP (Over-The-Air Programming) radio IP address from the application's configuration settings and returns it as a `CString`.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. It appears to be a transport helper function that fetches configuration data from the application's settings, which may be used by other functions to interact with the radio.

3. **Key Constants / Opcodes / Calls**:
   - String reference: `"OTAP_RADIO_IP_ADDR"`
   - COM vtable offset: `0x7c`
   - Function call: `CUiMFrmWnd::GetOptionValue`
   - Data reference: `&DAT_10011898` and `&DAT_10011454`

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `CUiMFrmWnd::GetOptionValue`, as it is responsible for fetching the configuration value from the application's settings, which may be used by other functions to interact with the radio.

---

## 323. `UdcDrIsh10c.dll` — `FUN_10008860` (`10008860`)
- **Keywords:** has-strings
- **Strings:** `FALSE`

*(qwen2.5-coder:14b, 9.7s)*

1. **Role**: This function initializes a `CString` object with the string "FALSE" from a global data location (`DAT_10011b0c`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanism. It appears to be a helper function for string manipulation.

3. **Key Constants / Opcodes / Calls**: 
   - String: "FALSE" (`s_FALSE_10011424`)
   - Global data: `DAT_10011b0c`

4. **Next Bite**: Since this function is primarily a string initialization helper, the next step should be to trace the call stack to see where this function is used and how it might indirectly affect EEPROM persistence. Look for calls to other functions that might involve EEPROM operations or state management.

---

## 324. `UdcDrIsh10c.dll` — `FUN_100088a0` (`100088a0`)
- **Keywords:** has-strings
- **Strings:** `FALSE`

*(qwen2.5-coder:14b, 9.6s)*

1. **Role**: This function initializes a `CString` object with the string "FALSE" from a global data location (`DAT_10011ab8`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanism. It appears to be a utility function for string handling.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"FALSE"` at `s_FALSE_10011424`.
   - Global data reference: `DAT_10011ab8`.

4. **Next Bite**: Since this function is primarily a string initialization utility, the next step should be to trace the call stack to see where this function is invoked and how it fits into the overall process. Look for any subsequent calls that might involve EEPROM operations or state persistence mechanisms.

---

## 325. `UdcDrIsh10c.dll` — `FUN_10008920` (`10008920`)
- **Keywords:** has-strings
- **Strings:** `DISPLAY_LAST`

*(qwen2.5-coder:14b, 9.9s)*

1. **Role**: The function `FUN_10008920` initializes a `CString` object with the string "DISPLAY_LAST" from the global data at `DAT_10011ae8`.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper function that initializes a string for display purposes.

3. **Key Constants / Opcodes / Calls**: 
   - String: "DISPLAY_LAST" at `s_DISPLAY_LAST_10011434`
   - Global data: `DAT_10011ae8`

4. **Next Bite**: Since this function is primarily a string initialization, the next step should be to inspect the caller of `FUN_10008920` to see how it interacts with the radio's EEPROM or state persistence mechanisms.

---

## 326. `UdcDrIsh10c.dll` — `FUN_10008960` (`10008960`)
- **Keywords:** has-strings
- **Strings:** `APPEND`

*(qwen2.5-coder:14b, 9.2s)*

1. **Role**: This function initializes a `CString` object with the string "APPEND" from a predefined memory location (`s_APPEND_10011444`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function appears to be a string initialization routine and does not directly interact with EEPROM or state persistence mechanisms.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `s_APPEND_10011444`
   - Memory location: `DAT_10011aa8`

4. **Next Bite**: Since this function does not directly interact with EEPROM or state persistence, there is no immediate next callee to inspect for EEPROM persistence. Further analysis should focus on other functions that might handle state persistence or interact with the radio's storage mechanisms.

---

## 327. `UdcDrIsh10c.dll` — `FUN_10008b20` (`10008b20`)
- **Keywords:** has-strings
- **Strings:** `INVALID`

*(qwen2.5-coder:14b, 10.2s)*

1. **Role**: This function initializes a `CString` object with the string "INVALID" from a global data location (`DAT_10011b28`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with the radio's EEPROM or flash memory. It appears to be a utility function for error handling or logging.

3. **Key Constants / Opcodes / Calls**: 
   - String: "INVALID" (`s_INVALID_10011468`)
   - Global data: `DAT_10011b28`

4. **Next Bite**: Since this function is primarily concerned with string initialization and does not involve direct EEPROM operations, the next step should be to trace the call stack to see where this function is invoked and how it fits into the overall state management process. Look for higher-level functions that might handle EEPROM persistence or error handling.

---

## 328. `UdcDrIsh10c.dll` — `entry` (`100099b7`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 20.2s)*

1. **Role**: The function `entry` appears to be a main entry point or handler for different operations based on the `param_2` value. It manages initialization, execution of operations, and finalization, possibly involving external functions or callbacks.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to manage state transitions and possibly invokes other functions that handle EEPROM persistence. It checks conditions and calls other functions (`FUN_1000990c`, `FUN_10002420`, and a function pointed to by `PTR_FUN_10011420`) which might involve EEPROM operations.

3. **Key Constants / Opcodes / Calls**:
   - `param_2` values: 0, 1, 2, 3
   - `DAT_10011b58`: A data offset used when `param_2` is 0.
   - `PTR_FUN_10011420`: A pointer to a function that might handle specific operations.
   - `FUN_1000990c`: A function called multiple times for different `param_2` values.
   - `FUN_10002420`: Another function called when `param_2` is 1.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000990c` and `FUN_10002420`, as they are called multiple times and might handle the actual state persistence operations. Additionally, the function pointed to by `PTR_FUN_10011420` should be examined if it is not null, as it might be responsible for specific operations that involve EEPROM.

---

## 329. `udcDrXAdk10c.dll` — `FUN_10001010` (`10001010`)
- **Keywords:** has-strings
- **Strings:** `FALSE`

*(qwen2.5-coder:14b, 11.1s)*

1. **Role**: The function `FUN_10001010` initializes a `CString` object with the string "FALSE" from the global data at `DAT_10004500`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with EEPROM or any persistence mechanism. It appears to be a helper function for string manipulation.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"FALSE"` at `s_FALSE_10004064`.
   - Global data reference: `DAT_10004500`.

4. **Next Bite**: Since this function is primarily involved in string initialization, the next step should be to inspect the callers of `FUN_10001010` to see how it is used in the context of the application. Look for any functions that might call this and then interact with the radio's EEPROM or state persistence mechanisms.

---

## 330. `udcDrXAdk10c.dll` — `FUN_10001050` (`10001050`)
- **Keywords:** has-strings
- **Strings:** `FALSE`

*(qwen2.5-coder:14b, 10.4s)*

1. **Role**: The function `FUN_10001050` initializes a `CString` object with the string "FALSE" from the global data at `DAT_100044f4`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with the radio's EEPROM or flash memory. It appears to be a utility function for string handling.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"FALSE"` at `s_FALSE_10004064`.
   - Global data reference: `DAT_100044f4`.

4. **Next Bite**: Since this function is primarily involved in string initialization, the next step should be to inspect the callees or the context in which this function is used to understand how it might indirectly affect EEPROM persistence. Look for calls to other functions that handle EEPROM operations or state management.

---

## 331. `udcDrXAdk10c.dll` — `FUN_100010d0` (`100010d0`)
- **Keywords:** has-strings
- **Strings:** `DISPLAY_LAST`

*(qwen2.5-coder:14b, 9.4s)*

1. **Role**: The function `FUN_100010d0` initializes a `CString` object with the string "DISPLAY_LAST" from the global data at `DAT_100044f8`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function appears to be a string initialization routine and does not directly interact with EEPROM or other persistence mechanisms.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"DISPLAY_LAST"` at offset `10004074`.
   - Global data reference: `DAT_100044f8`.

4. **Next Bite**: Since this function does not directly interact with EEPROM or persistence, there is no specific callee to inspect next for EEPROM persistence. Further analysis should focus on other functions that might handle EEPROM operations.

---

## 332. `udcDrXAdk10c.dll` — `FUN_10001110` (`10001110`)
- **Keywords:** has-strings
- **Strings:** `APPEND`

*(qwen2.5-coder:14b, 12.4s)*

1. **Role**: The function `FUN_10001110` initializes a `CString` object with the string "APPEND" from the global data at `DAT_100044f0`.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper function that initializes a string for further processing, possibly related to data handling or logging.

3. **Key Constants / Opcodes / Calls**: 
   - String: "APPEND" at `s_APPEND_10004084`
   - Global data: `DAT_100044f0`

4. **Next Bite**: Since this function is primarily concerned with string initialization, the next step should be to inspect the callees or the context in which this function is used to understand how it might indirectly influence EEPROM persistence. Look for calls to functions that handle data transmission or state management, such as those involving opcodes like `0x0106` (EnterMode/Session) or `0x000C` (OP_UNLOCK).

---

## 333. `udcDrXAdk10c.dll` — `FUN_100011f0` (`100011f0`)
- **Keywords:** has-strings
- **Strings:** `Unknown Radio Component not registered, Radio.Motorola.Unknown`

*(qwen2.5-coder:14b, 17.9s)*

1. **Role**: This function initializes or terminates an extension module related to a Motorola radio component. It checks for the registration of the radio component and handles the creation and destruction of a `CDynLinkLibrary` object.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It appears to be more focused on module initialization and error handling.

3. **Key Constants / Opcodes / Calls**:
   - `param_2 == 1`: Indicates initialization.
   - `param_2 == 0`: Indicates termination.
   - `CLSIDFromProgID`: Used to get the class ID from a programmatic identifier.
   - `AfxInitExtensionModule`: Initializes an extension module.
   - `AfxTermExtensionModule`: Terminates an extension module.
   - `AfxMessageBox`: Displays a message box if the radio component is not registered.
   - `HRESULT HVar2`: Used to check the result of `CLSIDFromProgID`.
   - `DAT_10004520`: A reference to an `AFX_EXTENSION_MODULE` structure.
   - `DAT_10004510`: A reference to a `CLSID`.
   - `s_Unknown_Radio_Component_not_regi_10004094`: A string for the error message.

4. **Next Bite**: The next callee to inspect for EEPROM persistence would be `CDynLinkLibrary::CDynLinkLibrary`, as it is responsible for creating the `CDynLinkLibrary` object and might involve further initialization steps related to the radio's state management.

---

## 334. `udcDrXAdk10c.dll` — `FUN_10001290` (`10001290`)
- **Keywords:** has-strings
- **Strings:** `FALSE`

*(qwen2.5-coder:14b, 11.5s)*

1. **Role**: The function `FUN_10001290` initializes a `CString` object with the string "FALSE" from a global data location (`DAT_10004540`).

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper function that initializes a string, possibly for use in communication or error handling.

3. **Key Constants / Opcodes / Calls**: 
   - String: `"FALSE"` (referenced at `s_FALSE_10004064`)
   - Global data: `DAT_10004540`

4. **Next Bite**: Since this function is primarily a string initializer, the next step should be to inspect the callees or the context in which this function is used to understand its role in the overall process of state persistence. Specifically, look at where `FUN_10001290` is called and how the initialized string is used.

---

## 335. `udcDrXAdk10c.dll` — `FUN_100012d0` (`100012d0`)
- **Keywords:** has-strings
- **Strings:** `FALSE`

*(qwen2.5-coder:14b, 10.4s)*

1. **Role**: The function `FUN_100012d0` initializes a `CString` object with the string "FALSE" from a global data location (`DAT_10004538`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function appears to be a string initialization routine and does not directly interact with EEPROM or persistence mechanisms.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"FALSE"` at `s_FALSE_10004064`.
   - Global data reference: `DAT_10004538`.

4. **Next Bite**: Since this function does not directly interact with EEPROM or persistence, the next step should be to trace the call graph to identify where this string is used or if it is part of a larger operation that involves EEPROM persistence. Look for calls to other functions that might handle EEPROM operations or state persistence.

---

## 336. `udcDrXAdk10c.dll` — `FUN_10001350` (`10001350`)
- **Keywords:** has-strings
- **Strings:** `DISPLAY_LAST`

*(qwen2.5-coder:14b, 9.8s)*

1. **Role**: The function `FUN_10001350` initializes a `CString` object with the string "DISPLAY_LAST" from the global data at `DAT_1000453c`.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper function that initializes a string for display purposes.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"DISPLAY_LAST"` at `s_DISPLAY_LAST_10004074`
   - Global data reference: `DAT_1000453c`

4. **Next Bite**: Since this function is primarily a string initialization, the next step should be to inspect the callees or the context in which this function is used to understand how it might indirectly influence EEPROM persistence.

---

## 337. `udcDrXAdk10c.dll` — `FUN_10001390` (`10001390`)
- **Keywords:** has-strings
- **Strings:** `APPEND`

*(qwen2.5-coder:14b, 11.3s)*

1. **Role**: The function `FUN_10001390` initializes a `CString` object with the string "APPEND" from the data at offset `0x10004084`.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a transport helper function that initializes a string for further processing, possibly related to data handling or logging.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"APPEND"` at offset `0x10004084`.
   - No specific hex constants, opcodes, or HRESULTs observed in the provided code snippet.

4. **Next Bite**: Since this function is primarily a string initialization, the next step should be to inspect the callees or the context in which this function is used to understand how it might indirectly influence EEPROM persistence. Specifically, look at the constructor of `CString` and any subsequent operations that might involve data transmission or storage.

---

## 338. `udcDrXAdk10c.dll` — `udcDrXAdkGetPortFromUser` (`10001770`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.3s)*

1. **Role**: The function `udcDrXAdkGetPortFromUser` appears to be a helper function that manages the retrieval of a port from user input. It initializes a `CStringArray`, calls another function with parameters including this array, and then cleans up the array.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly interact with the EEPROM or handle state persistence. It seems to be a transport helper function that prepares data structures for other operations that might affect the radio's state.

3. **Key Constants / Opcodes / Calls**: The function does not contain any specific hex constants, opcodes, or direct calls to EEPROM-related functions. It initializes a `CStringArray` and calls `udcDrXAdkGetPortFromUser` with additional parameters, but the actual implementation details are not visible in the provided snippet.

4. **Next Bite**: The next callee to inspect for EEPROM persistence would be `udcDrXAdkGetPortFromUser` (the one with four parameters), as it is the primary function being called within this function and might handle the actual interaction with the radio's state.

---

## 339. `udcDrXAdk10c.dll` — `udcDrXAdkGetPortFromUser` (`100017f0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 14.0s)*

1. **Role**: This function appears to handle user interaction for selecting a port, likely in a dialog context. It retrieves port names from the machine, displays a dialog for user selection, and processes the selected port.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It is more of a transport helper that manages user input and port selection, which could indirectly affect state persistence if the selected port is used for subsequent operations that involve EEPROM manipulation.

3. **Key Constants / Opcodes / Calls**: 
   - `udcDrXAdkGetPortNamesFromMachine`: A function call to retrieve port names.
   - `CUiPortDlg::CUiPortDlg`: Constructor for a dialog class.
   - `CDialog::DoModal`: Displays the dialog modally.
   - `CUiPortDlg::GetSelectedPort`: Retrieves the selected port from the dialog.
   - `FUN_10001740`: A function pointer or vtable offset that processes the selected port.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_10001740`, as it processes the selected port and could involve operations that affect the radio's permanent state.

---

## 340. `udcDrXAdk10c.dll` — `udcDrXAdkGetUUIDFromDevice` (`100018f0`)
- **Keywords:** exported, has-strings, named
- **Strings:** `Protocol Not Supported->`

*(qwen2.5-coder:14b, 12.1s)*

1. **Role**: This function appears to retrieve the UUID from a device, likely a radio, and involves obtaining a port from the user and then calling another function to get the UUID from the device.

2. **EEPROM / Persistence Mechanism**: The function does not directly handle EEPROM persistence or state commitment. It seems to be a transport helper function that sets up communication and then delegates the actual UUID retrieval to another function.

3. **Key Constants / Opcodes / Calls**: 
   - `udcDrXAdkGetPortFromUser`: A function call to obtain a port from the user.
   - `udcDrXAdkGetUUIDFromDevice`: A recursive call to another function to get the UUID from the device.
   - `"Protocol Not Supported->"`: A string that might be used for error handling or logging.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `udcDrXAdkGetUUIDFromDevice`, which is called recursively within the same function. This function should be analyzed to understand how it interacts with the device and whether it involves any EEPROM persistence operations.

---

## 341. `udcDrXAdk10c.dll` — `udcDrXAdkGetUUIDFromDevice` (`10001930`)
- **Keywords:** exported, has-strings, named
- **Strings:** `Protocol Not Supported->`

*(qwen2.5-coder:14b, 11.9s)*

1. **Role**: This function appears to retrieve the UUID from a device, likely a radio, and involves obtaining a port from the user and then fetching the UUID using that port.

2. **EEPROM / Persistence Mechanism**: The function does not directly handle EEPROM persistence or state commitment. It seems to be a transport helper function that sets up communication and then delegates the actual UUID retrieval to another function.

3. **Key Constants / Opcodes / Calls**: 
   - `udcDrXAdkGetPortFromUser`: This function is called to get a port from the user.
   - `udcDrXAdkGetUUIDFromDevice`: This function is called to fetch the UUID using the obtained port.
   - No specific opcodes or constants are directly visible in the provided code snippet.

4. **Next Bite**: The next function to inspect for EEPROM persistence is `udcDrXAdkGetUUIDFromDevice`, which is called after obtaining the port. This function is likely responsible for the actual communication with the device to retrieve the UUID and may involve operations related to EEPROM persistence.

---

## 342. `udcDrXAdk10c.dll` — `udcDrXAdkGetUUIDFromDevice` (`10001980`)
- **Keywords:** exported, has-strings, named
- **Strings:** `Protocol Not Supported->`

*(qwen2.5-coder:14b, 16.2s)*

1. **Role**: This function appears to retrieve the UUID from a device, likely a radio, and handles various error conditions and COM interactions to achieve this.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. It seems to be more of a transport helper function that interacts with the device to retrieve data, possibly involving some form of locking or unlocking mechanism to ensure data integrity.

3. **Key Constants / Opcodes / Calls**:
   - COM class object retrieval: `CoGetClassObject` with GUIDs `DAT_10004510` and `DAT_10003198`.
   - Error messages: `0x6fde` and `0x6fdd`.
   - HRESULT checks: `HVar3 < 0` for error handling.
   - COM method calls: `(**(code **)(*(int *)local_20 + 0x1c))` and `(**(code **)(*local_1c + 0x10))`.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10001570` and `FUN_10001400`, as they are involved in handling the protocol and data retrieval process, which might include interactions with the device's storage.

---

## 343. `udcDrXAdk10c.dll` — `udcDrXAdkCreateTmpFileNameForReadingDevice` (`10001bf0`)
- **Keywords:** exported, has-strings, named
- **Strings:** `%s_%d%d%d.%s, rdkDevice`

*(qwen2.5-coder:14b, 15.8s)*

1. **Role**: This function generates a temporary file name for reading a device, incorporating the current system time and a device-specific identifier. It appears to be part of a larger process for handling device data.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly interact with the radio's EEPROM or flash memory. It is more of a helper function for file naming, which is likely used in a broader context to manage temporary files during device operations. It does not involve direct EEPROM commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**:
   - `s_rdkDevice_10004118`: A string constant related to the device identifier.
   - `CFhAdkFileHandler::GetFileExtension`: A method call to get the file extension based on the file type.
   - `GetSystemTime`: A system call to retrieve the current system time.
   - `CString::Format`: A method to format a string using the current minute and other parameters.

4. **Next Bite**: The next callees to inspect for EEPROM persistence would be any functions related to file handling, such as `CFhAdkFileHandler::GetFileExtension`, or any other methods that might involve writing to or reading from the device's storage. Additionally, tracing the use of the generated temporary file name in subsequent operations could provide insights into how the device's state is managed.

---

## 344. `udcDrXAdk10c.dll` — `udcDrXAdkInsertProtFirstPos` (`10001cf0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 17.4s)*

1. **Role**: The function `udcDrXAdkInsertProtFirstPos` appears to manipulate a string (`CString`) by inserting a protection marker at the beginning. It involves COM object interactions and string operations, likely related to licensing or security settings.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that modifies internal state or prepares data for further processing, which could indirectly affect persistent state through subsequent operations.

3. **Key Constants / Opcodes / Calls**:
   - COM class object retrieval: `CoGetClassObject` with specific GUIDs (`DAT_10004510` and `DAT_100031a8`).
   - COM method calls: `0x1c` and `0x8` offsets in the vtable.
   - HRESULT check: `-1 < HVar1` and `-1 < iVar2`.
   - String manipulation: `CString::Find`, `CString::Delete`, `CString::Insert`.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are the methods called on the COM object retrieved via `CoGetClassObject`, specifically the methods at offsets `0x1c` and `0x8` in the vtable (`**(code **)(*local_20 + 0x1c)` and `**(code **)(*piVar5 + 8)`). These methods might involve actual interactions with the radio's storage or state management.

---

## 345. `udcDrXAdk10c.dll` — `FUN_10001eb0` (`10001eb0`)
- **Keywords:** has-strings
- **Strings:** `FALSE`

*(qwen2.5-coder:14b, 10.0s)*

1. **Role**: The function `FUN_10001eb0` initializes a `CString` object with the string "FALSE" from the global data at `DAT_10004558`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function appears to be a simple string initialization and does not directly interact with EEPROM or any persistence mechanisms related to the radio's state.

3. **Key Constants / Opcodes / Calls**: 
   - String: "FALSE" at `s_FALSE_10004064`
   - Global data: `DAT_10004558`

4. **Next Bite**: Since this function does not involve any EEPROM or persistence operations, there is no specific callee to inspect next for tracing EEPROM persistence. Further analysis should focus on other functions that interact with the radio's state or persistence mechanisms.

---

## 346. `udcDrXAdk10c.dll` — `FUN_10001ef0` (`10001ef0`)
- **Keywords:** has-strings
- **Strings:** `FALSE`

*(qwen2.5-coder:14b, 10.0s)*

1. **Role**: The function `FUN_10001ef0` initializes a `CString` object with the string "FALSE" from a global data location (`DAT_10004550`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with EEPROM or any persistence mechanism. It appears to be a helper function for string manipulation.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"FALSE"` at `s_FALSE_10004064`.
   - Global data reference: `DAT_10004550`.

4. **Next Bite**: Since this function is primarily a string initialization helper, the next step should be to trace the call graph to see where this `CString` object is used. Look for any subsequent function calls that might involve EEPROM operations or state persistence mechanisms.

---

## 347. `udcDrXAdk10c.dll` — `FUN_10001f70` (`10001f70`)
- **Keywords:** has-strings
- **Strings:** `DISPLAY_LAST`

*(qwen2.5-coder:14b, 9.9s)*

1. **Role**: This function initializes a `CString` object with the string "DISPLAY_LAST" from a global data location (`DAT_10004554`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function appears to be a string initialization routine and does not directly interact with EEPROM or other persistence mechanisms.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `"DISPLAY_LAST"` at offset `10004074`.
   - Global data reference: `DAT_10004554`.

4. **Next Bite**: Since this function does not directly interact with EEPROM or persistence, the next step should be to trace the call stack and inspect other functions that might be involved in handling EEPROM operations, such as those related to `OP_LOCK`, `OP_UNLOCK`, or `EnterMode/Session` opcodes.

---

## 348. `udcDrXAdk10c.dll` — `FUN_10001fb0` (`10001fb0`)
- **Keywords:** has-strings
- **Strings:** `APPEND`

*(qwen2.5-coder:14b, 10.8s)*

1. **Role**: The function `FUN_10001fb0` initializes a `CString` object with the string "APPEND" from a predefined location in memory (`s_APPEND_10004084`).

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a helper function for string manipulation and does not involve any EEPROM commit, lock/unlock, reset, or state persistence operations.

3. **Key Constants / Opcodes / Calls**: 
   - String reference: `s_APPEND_10004084`
   - `CString::CString` constructor call

4. **Next Bite**: Since this function is primarily involved in string initialization, the next step should be to inspect the callees or the context in which this function is used to understand how it might indirectly contribute to EEPROM persistence. Look for any subsequent calls that involve operations on the radio's state or memory.

---

## 349. `udcDrXAdk10c.dll` — `entry` (`100021db`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 17.2s)*

1. **Role**: The function `entry` appears to be an exported entry point in the DLL, handling different operations based on the `param_2` value. It seems to manage initialization, execution, and cleanup of operations, possibly related to device communication or state management.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it appears to manage the flow of operations, possibly invoking other functions that handle EEPROM persistence. It checks conditions and calls other functions (`FUN_10002130`, `FUN_100011f0`) that might be responsible for actual EEPROM operations.

3. **Key Constants / Opcodes / Calls**:
   - `param_2` values: 0, 1, 2, 3
   - `DAT_1000456c`: A data reference
   - `PTR_FUN_10004060`: A pointer to a function, possibly used for specific operations
   - `FUN_10002130`: A function called multiple times, possibly for initialization or cleanup
   - `FUN_100011f0`: Another function called, possibly for error handling or finalization

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10002130` and `FUN_100011f0`. These functions are called multiple times and might contain the logic for actual EEPROM operations or state management.

---
