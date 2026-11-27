# Homelab AI Function-by-Function Analysis: ASTRO 25 EEPROM & State Persistence

- **Model:** `qwen2.5-coder:14b` (`num_ctx=8192` on TrueNAS RTX 3080)
- **Scope:** Undocumented functions in `NextGen10.dll` and `ByteData10.dll` related to EEPROM, host markers, commit/lock, and state persistence.
- **Total functions analyzed:** 20

---

## 1. `NextGen10.dll` — `FUN_10009c7e` (`10009c7e`)
- **Keywords:** bundle, rcmp
- **Strings:** `CRcmpBundler::DelCodeplug`

*(qwen2.5-coder:14b, 17.1s)*

1. **Role**: This function appears to handle the deletion of a codeplug on the radio, likely involving communication with the radio via the RCMP protocol and managing the state of the operation.

2. **EEPROM / Persistence Mechanism**: The function seems to manage the state of the operation by sending messages to a window handle (HWND) and calling various functions that could involve committing changes to the radio's EEPROM or flash memory. It also checks and sets certain flags that might indicate the success or failure of the operation, which could be related to the persistence of state.

3. **Key Constants / Opcodes / Calls**:
   - `0x405`: A message identifier used in `SendMessageA` calls.
   - `FUN_1000b5b0`: A function called multiple times, possibly related to committing changes or handling the state of the operation.
   - `FUN_1000b2ad`: A function called when the initial operation fails, possibly to handle an error or retry the operation.
   - `s_CRcmpBundler__DelCodeplug_1002c624`: A string related to the operation of deleting a codeplug.

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_1000b5b0` and `FUN_1000b2ad`, as they are called multiple times and could be directly involved in committing changes or handling errors related to the operation.

---

## 2. `NextGen10.dll` — `FUN_10009e3f` (`10009e3f`)
- **Keywords:** delish, bundle, rcmp
- **Strings:** `CRcmpBundler::DelIshItem`

*(qwen2.5-coder:14b, 15.6s)*

1. **Role**: This function appears to handle the deletion of an item (`DelIshItem`) in the context of a radio communication protocol, possibly involving state management and error handling.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by potentially invoking operations that could lead to state persistence, such as committing changes or unlocking security. It does not directly perform EEPROM/flash commit or reset operations but may involve calls that do.

3. **Key Constants / Opcodes / Calls**:
   - `s_CRcmpBundler__DelIshItem_1002c640`: Referenced string indicating the operation being performed.
   - `FUN_1000b5b0` and `FUN_1000b2ad`: Potential callees that could handle the actual deletion or state management.
   - `*(char *)(iVar1 + 0x20) == '\x01'`: Condition that checks a specific byte in the object being processed.
   - `HRESULT HVar3`: Used to capture the result of operations, indicating success or failure.

4. **Next Bite**: The callees `FUN_1000b5b0` and `FUN_1000b2ad` should be inspected next to trace EEPROM persistence, as they are likely responsible for the actual deletion or state management operations.

---

## 3. `NextGen10.dll` — `FUN_10009f15` (`10009f15`)
- **Keywords:** delish, bundle, rcmp
- **Strings:** `CRcmpBundler::DelIshTypes`

*(qwen2.5-coder:14b, 18.1s)*

1. **Role**: This function appears to handle the deletion of types associated with a specific bundle in the context of the RCMP transport protocol. It initializes a string with the label "CRcmpBundler::DelIshTypes" and checks a condition based on the value at an offset in the input parameter. Depending on the condition, it calls different functions and manages strings.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that manages state within the application layer, possibly preparing data for transport or handling acknowledgments. It does not explicitly commit changes to EEPROM or perform any direct persistence operations.

3. **Key Constants / Opcodes / Calls**:
   - String: "CRcmpBundler::DelIshTypes"
   - Offset checks: `*(char *)(iVar1 + 0x20) == '\x01'`
   - Function calls: `FUN_10021490()`, `FUN_1002120d()`, `FUN_1000b5b0()`, `FUN_1000b2ad()`, `FUN_1000b500()`
   - HRESULT checks: `-1 < HVar3`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000b5b0()` and `FUN_1000b2ad()`, as they are conditionally called based on the state of the input parameter and could potentially handle the actual transport or persistence logic.

---

## 4. `NextGen10.dll` — `FUN_10009fe9` (`10009fe9`)
- **Keywords:** bundle, rcmp
- **Strings:** `CRcmpBundler::GetRadioUUID`

*(qwen2.5-coder:14b, 21.2s)*

1. **Role**: This function appears to handle the retrieval of the radio's UUID and manages error handling and state transitions related to the radio's operational mode and security status.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by checking and setting operational modes and handling security locks. It does not directly perform EEPROM commits or flushes but is involved in the process of ensuring the radio's state is correctly managed and persisted.

3. **Key Constants / Opcodes / Calls**:
   - **Hex Constants**: `0x80004003`, `0x80004005`
   - **Offsets**: `0x20`, `0x80`, `0x30`, `0x98`
   - **Error HRESULTs**: `0x80004003`, `0x80004005`
   - **Callees**: `FUN_1000b2ad`, `FUN_10021744`, `FUN_1000b8b5`, `FUN_1000a201`, `FUN_1000a268`, `FUN_1000a3a9`, `FUN_1000b500`

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_1000b2ad`, `FUN_10021744`, `FUN_1000b8b5`, and `FUN_1000a3a9`, as they are involved in error handling, operational mode setting, and security management, which are critical for ensuring the radio's state is correctly persisted.

---

## 5. `NextGen10.dll` — `FUN_1000ab20` (`1000ab20`)
- **Keywords:** writeish, bundle, rcmp
- **Strings:** `CRcmpBundler::WriteIshList`

*(qwen2.5-coder:14b, 19.4s)*

1. **Role**: This function appears to handle a list of "ish" items for writing to the radio, possibly using a bundler mechanism. It manages the state of the operation, including error handling and cleanup.

2. **EEPROM / Persistence Mechanism**: The function interacts with the radio's EEPROM by writing a list of items. It uses a bundler to manage the write process, which likely involves locking, writing, and unlocking the EEPROM to ensure data integrity and persistence. The function also handles error conditions and ensures that resources are properly released.

3. **Key Constants / Opcodes / Calls**:
   - `0x405` (SendMessageA parameter): Likely a custom message for the radio.
   - `0x0100` (ReadIsh opcode): Indicated by the `WriteIshList` string.
   - `FUN_10006984`: Possibly initializes or prepares the data for writing.
   - `FUN_1000bd6f` and `FUN_1000beb6`: These functions are likely involved in the actual data writing process.
   - `SafeArrayAccessData`, `SafeArrayGetLBound`, `SafeArrayGetUBound`, `SafeArrayUnaccessData`: These functions manage the SAFEARRAY used to store the data to be written.

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_1000bd6f` and `FUN_1000beb6`, as they are directly involved in the data writing process. These functions likely contain the core logic for committing data to the radio's EEPROM.

---

## 6. `NextGen10.dll` — `FUN_1000b8b5` (`1000b8b5`)
- **Keywords:** bundle, rcmp
- **Strings:** `CRcmpBundler::SendCommand`

*(qwen2.5-coder:14b, 17.0s)*

1. **Role**: This function appears to prepare and send a command to an RCMP (likely a radio control protocol) interface, possibly for configuration or data manipulation. It constructs a SAFEARRAY with command data and sends it using a bundler method.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by preparing and sending commands that could involve writing to EEPROM or committing changes. It does not directly handle commit, lock/unlock, or reset operations but is part of the process that likely leads to these actions.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x11`, `0x2011`
   - Offsets: `-0x1c`, `-0x2c`, `-0x24`, `-0x18`, `-0x10`, `-0x20`
   - Error HRESULTs: `-1` (indicating failure)
   - Callees: `FUN_10021490`, `FUN_1002120d`, `FUN_1000ba53`, `BstrFromVector`

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_1000ba53`, as it is called after the command data is prepared and before the final cleanup, suggesting it might handle the actual sending or processing of the command.

---

## 7. `NextGen10.dll` — `FUN_1000ba53` (`1000ba53`)
- **Keywords:** bundle, rcmp
- **Strings:** `CRcmpBundler::SendCommand`

*(qwen2.5-coder:14b, 22.9s)*

1. **Role**: This function appears to handle sending commands to a radio device via a bundler mechanism, possibly managing the state or data transfer process.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by sending commands that could involve committing changes to EEPROM or flash memory. It checks conditions and calls other functions that likely handle the actual commit or lock/unlock operations.

3. **Key Constants / Opcodes / Calls**:
   - `0x0100` (ReadIsh), `0x0101` (WriteIsh), `0x0102` (Prepare Write), `0x0103` (DelIshTypes), `0x0106` (EnterMode/Session), `0x0107` (UnlockSecurity LFSR), `0x000C` (OP_UNLOCK), `0x000D` (OP_LOCK with 16-byte UUID), `0x0012` (GetRadioUUID).
   - HRESULT `0x80070057` (E_INVALIDARG), `0x80070005` (E_ACCESSDENIED), `0x80070002` (E_NOTFOUND).
   - Calls: `FUN_10021490`, `FUN_1002120d`, `SafeArrayAccessData`, `SafeArrayUnaccessData`, `SetOtapAbortFlag`, `GetOtapAbortFlag`.

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_10021490`, `FUN_1002120d`, and the functions pointed to by the COM vtable offsets `0x1c`, `0x30`, and `0x2c` in the `extraout_ECX` structure. These functions are likely responsible for the actual command execution and state management on the radio.

---

## 8. `NextGen10.dll` — `FUN_1000beb6` (`1000beb6`)
- **Keywords:** writeish, bundle, rcmp
- **Strings:** `CRcmpBundler::ReadWriteIshLetToRadio`

*(qwen2.5-coder:14b, 15.6s)*

1. **Role**: This function appears to handle the reading and writing of data to a radio device, possibly through a bundler mechanism, and manages error handling and state transitions.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by managing data transfer and potentially setting markers or flags that indicate the state of the operation. It does not directly perform EEPROM commit or reset operations but is involved in the process of ensuring data integrity and persistence.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x22`, `0x23`, `-0x7fffbffb`
   - Offsets: `0x10`, `0x28`, `0x98`
   - Error HRESULTs: `-0x7fffbffb`
   - Callees: `FUN_10021490`, `FUN_1002120d`, `FUN_1000b5b0`, `SafeArrayAccessData`, `SafeArrayUnaccessData`, `FUN_1000b500`

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_1000b5b0`, as it is called multiple times and may handle the actual data transfer or state commit operations.

---

## 9. `NextGen10.dll` — `FUN_1000c01f` (`1000c01f`)
- **Keywords:** bundle, rcmp, otap
- **Strings:** `Radio is Not Responding, Radio is Busy, The Radio is Not an OTAP Enabled Radio, Could not communicate with the Radio, CRcmpBundler::Open`

*(qwen2.5-coder:14b, 24.1s)*

1. **Role**: This function appears to handle the opening and communication with a radio device, possibly setting up a connection and preparing for operations like reading or writing data. It checks the state of the radio and handles different error conditions, including communication failures and unsupported operations.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to manage the state of the connection and prepare the radio for operations that might involve writing to EEPROM. It uses opcodes like `0x0106` (EnterMode/Session) and `0x000C` (OP_UNLOCK) to manage the radio's state, which could be part of the process of making changes permanent.

3. **Key Constants / Opcodes / Calls**:
   - Opcodes: `0x0106`, `0x000C`, `0x000D`
   - Constants: `0x1f43`, `0x2011`
   - HRESULTs: `-0x13fffff1`, `-0x13fffff8`, `-0x13fffff3`
   - Callees: `FUN_1000b2ad`, `FUN_1000d523`, `FUN_1000b5b0`, `FUN_1000b500`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000b5b0` and `FUN_1000b2ad`, as they are called after preparing the radio and could involve actual data operations that might affect EEPROM. Additionally, examining the COM vtable calls (e.g., `(**(code **)(*piVar2 + 0xf4))`) could provide insights into how the radio's state is managed and committed.

---

## 10. `NextGen10.dll` — `FUN_1000ca08` (`1000ca08`)
- **Keywords:** bundle, rcmp
- **Strings:** `CRcmpBundler::Close`

*(qwen2.5-coder:14b, 19.2s)*

1. **Role**: This function appears to handle the closing of an `RCmpBundler` object, performing various cleanup and state management operations, including error handling and finalizing the bundling process.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by ensuring that all pending operations are finalized and any necessary locks are released. It does not directly perform EEPROM writes or commits but ensures that the bundling process is properly closed, which likely includes committing any changes to the radio's EEPROM or flash memory.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x80`, `0x30`, `0x20`, `0x29`, `0x8`, `0x24`, `0x20`, `0x98`
   - HRESULTs: `-0x7fffbffb`
   - Callees: `FUN_10021490`, `FUN_1002120d`, `FUN_1000b5b0`, `FUN_1000b3bb`, `FUN_1000b500`
   - COM vtable offsets: `0x38`, `0x24`, `0x8`, `0x20`, `0x8`

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_1000b5b0` and `FUN_1000b3bb`, as they are directly invoked within the function and may handle critical operations related to committing changes or managing locks.

---

## 11. `NextGen10.dll` — `FUN_1000d794` (`1000d794`)
- **Keywords:** bundle, rcmp
- **Strings:** `CRcmpBundler::EnterBootMode
`

*(qwen2.5-coder:14b, 24.6s)*

1. **Role**: This function appears to handle the entry into boot mode for a radio device, likely involving communication with the radio over a transport layer and managing state transitions.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by preparing and sending commands to enter boot mode. It involves setting up a SAFEARRAY, initializing a VARIANTARG, and making COM calls that likely involve sending commands to the radio. The function does not directly perform EEPROM commit or reset operations but is part of the process that ensures the radio's state is correctly managed and persisted.

3. **Key Constants / Opcodes / Calls**:
   - `0x2011` and `0x200` are used in setting up the SAFEARRAY.
   - `0x76`, `0x77`, and `0x78` are error codes set in different branches of the function.
   - `0x80004005` is a HRESULT indicating an error.
   - COM calls and vtable offsets like `0x1c`, `0x30`, and `0x2c` are used to invoke methods on COM objects.
   - `FUN_10021490`, `FUN_1002120d`, `FUN_10021744`, and `FUN_1000b2ad` are other functions called within this function.

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_1000b2ad`, `FUN_10021490`, `FUN_1002120d`, and `FUN_10021744`, as they are invoked at critical points in the function and may contain the logic for sending commands to the radio or handling errors. Additionally, examining the COM methods invoked through the vtable offsets (`0x1c`, `0x30`, and `0x2c`) could provide insights into the actual communication with the radio.

---

## 12. `NextGen10.dll` — `FUN_10011a98` (`10011a98`)
- **Keywords:** enterprogram, bundle, rcmp
- **Strings:** `CRcmpBundler::EnterProgramMode
`

*(qwen2.5-coder:14b, 16.1s)*

1. **Role**: This function, `FUN_10011a98`, appears to handle entering program mode for an RcmpBundler object. It checks certain conditions and calls other functions to either enter program mode or handle errors.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by potentially setting markers or flags that indicate the state of the program mode. It does not directly perform EEPROM commit, lock/unlock, or reset operations. Instead, it relies on other functions to manage these aspects.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x29`, `0x20`, `0x98`
   - HRESULTs: `0`, `-1`
   - Callees: `FUN_10021490`, `FUN_1002120d`, `FUN_1000b5b0`, `FUN_1000b2ad`, `FUN_1000b500`
   - Strings: `"CRcmpBundler::EnterProgramMode"`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000b5b0` and `FUN_1000b2ad`, as they are conditionally called based on the state of the object and may handle the actual persistence mechanisms.

---

## 13. `NextGen10.dll` — `FUN_100135cd` (`100135cd`)
- **Keywords:** bundle, rcmp
- **Strings:** `CRcmpBundler::ResetRequest
`

*(qwen2.5-coder:14b, 20.1s)*

1. **Role**: This function appears to handle a reset request for the CRcmpBundler, likely preparing and sending a command to the radio to reset its state.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the radio's permanent state by preparing a reset request and sending it over the transport layer. It does not directly commit to EEPROM or flash; instead, it relies on the transport mechanism to ensure the reset command is processed by the radio.

3. **Key Constants / Opcodes / Calls**:
   - `0x2011`: A constant used in the `VariantInit` call, possibly related to the type of data being sent.
   - `0x9b` and `0x9c`: Error codes set in the function if certain operations fail.
   - `FUN_1000b2ad`: A function called to handle errors.
   - `FUN_10021744`: Another error handling function.
   - `SafeArrayCreateVector`, `SafeArrayAccessData`, `SafeArrayUnaccessData`, `SafeArrayDestroy`: Functions related to handling arrays.
   - `CString::CString`, `CString::~CString`: String handling functions.

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_1000b2ad` and `FUN_10021744`, as they handle errors and might provide more insight into the transport and persistence mechanisms. Additionally, examining the vtable calls at `**(code **)(**(int **)(iVar1 + 0x18) + 0x1c)` and `**(code **)(**(int **)(iVar1 + 8) + 0x30)` could reveal more about the actual communication with the radio.

---

## 14. `NextGen10.dll` — `FUN_100171b5` (`100171b5`)
- **Keywords:** bundle, rcmp, otap
- **Strings:** `Radio is Busy, The Radio is Not an OTAP Enabled Radio, CheckSum Error, CRcmpBundler::Write OTAP ISHItems Failed, Overal Result Code [%d], CRcmpBundler::WriteOTAPIshList`

*(qwen2.5-coder:14b, 30.2s)*

1. **Role**: This function appears to handle the bundling and writing of OTAP (Over-The-Air Programming) ISH (Item Specific Header) items to a radio, likely through a communication protocol over TCP.

2. **EEPROM / Persistence Mechanism**: The function interacts with the radio's EEPROM by preparing and sending data packets. It uses specific opcodes to manage the state, including locking and unlocking security, and possibly committing changes to ensure persistence. The function also handles error conditions and updates the radio's state accordingly.

3. **Key Constants / Opcodes / Calls**:
   - **Opcodes**: `0x0100` (ReadIsh), `0x0101` (WriteIsh), `0x0102` (Prepare Write), `0x0103` (DelIshTypes), `0x0106` (EnterMode/Session), `0x0107` (UnlockSecurity).
   - **Constants**: `0x80` (codeplug ReadWrite), `0x81` (security/EEPROM ReadWriteLocked), `0x82` (tuning ReadOnly).
   - **Error HRESULTs**: `SafeArrayAccessData`, `SafeArrayGetLBound`, `SafeArrayGetUBound`, `SafeArrayCreateVectorEx`, `SafeArrayUnaccessData`, `SafeArrayDestroy`.
   - **Callees**: `FUN_10006984`, `FUN_1000bd6f`, `FUN_10017093`, `FUN_1001773c`, `FUN_1000ba53`.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_10017093`, as it is directly involved in writing data to the radio and likely handles the actual data transfer and commit process.

---

## 15. `NextGen10.dll` — `FUN_1001773c` (`1001773c`)
- **Keywords:** bundle, rcmp
- **Strings:** `CRcmpBundler::Send ReOrg`

*(qwen2.5-coder:14b, 19.2s)*

1. **Role**: This function appears to prepare and send a command related to reorganizing or reordering data, likely using the RCMP protocol over TCP. It initializes a string, sets up a buffer, and sends it via a bundler.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by preparing a command that could involve reorganizing data, which might include committing changes to EEPROM or flash memory. It does not directly perform a commit or reset but sets up the data for such operations.

3. **Key Constants / Opcodes / Calls**:
   - String: `"CRcmpBundler::Send ReOrg"`
   - Buffer setup: `*(undefined1 *)(unaff_EBP + -0x18) = 1; *(undefined1 *)(unaff_EBP + -0x17) = 7; *(undefined1 *)(unaff_EBP + -0x16) = 0x80; *(undefined1 *)(unaff_EBP + -0x15) = 0;`
   - Function calls: `FUN_10021490()`, `FUN_1002120d()`, `AFX_MAINTAIN_STATE2::AFX_MAINTAIN_STATE2()`, `CString::CString()`, `CString::~CString()`, `FUN_100177e1()`, `FUN_1000b5b0()`

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_100177e1`, as it directly manipulates the buffer that could be related to sending commands to the radio for data reorganization or state persistence.

---

## 16. `NextGen10.dll` — `FUN_1001a32d` (`1001a32d`)
- **Keywords:** 1001a3

*(qwen2.5-coder:14b, 19.1s)*

1. **Role**: This function appears to manage the visibility and enabled state of various UI elements within a dialog window. It toggles the visibility and enablement of different controls based on certain conditions, likely related to the application's state or user permissions.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the EEPROM or flash storage of the radio. It is more of a UI management function that controls the visibility and enablement of UI elements, which could indirectly affect user interactions that might trigger EEPROM operations elsewhere in the application.

3. **Key Constants / Opcodes / Calls**: 
   - Hex constants for control IDs: `0x101`, `0xf0`, `0xfb`, `0xf8`, `0xfd`, `0xf9`, `0xfe`, `0xfa`, `0xfc`, `0xf7`, `0xf5`, `0xf3`, `0xf6`, `0xf4`, `0xff`, `0x100`.
   - Offsets: `0xa4`, `0xa0` (used to determine enablement state of certain controls).
   - Calls: `CWnd::GetDlgItem`, `CWnd::ShowWindow`, `CWnd::EnableWindow`.

4. **Next Bite**: Since this function does not directly interact with EEPROM, the next step would be to trace the callees that manage the actual state persistence, such as those related to committing changes or handling security operations. Look for functions that involve opcodes like `0x0106` (EnterMode/Session) or `0x0107` (UnlockSecurity), or any other functions that might handle EEPROM operations.

---

## 17. `NextGen10.dll` — `FUN_1001a577` (`1001a577`)
- **Keywords:** 1001a5

*(qwen2.5-coder:14b, 15.4s)*

1. **Role**: This function appears to manage the visibility and enabled state of various UI elements within a dialog window. It shows certain controls and hides/enables others, likely in response to user interaction or program state changes.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be a UI management function that may indirectly affect persistence through user actions that trigger other functions.

3. **Key Constants / Opcodes / Calls**: 
   - Hex constants: `0x101`, `0xf0`, `0xfb`, `0xf8`, `0xfd`, `0xf9`, `0xfe`, `0xfa`, `0xfc`, `0xf7`, `0xf5`, `0xf3`, `0xf6`, `0xf4`, `0xff`, `0x100`
   - Calls: `CWnd::GetDlgItem`, `CWnd::ShowWindow`, `CWnd::EnableWindow`

4. **Next Bite**: Since this function does not directly interact with EEPROM, the next step would be to trace the callees that manage UI interactions, such as button clicks or other user actions, to see if they trigger any EEPROM-related operations. Focus on functions that handle user input or state changes that could lead to EEPROM commits or locks.

---

## 18. `NextGen10.dll` — `FUN_1001c92d` (`1001c92d`)
- **Keywords:** writecodeplug
- **Strings:** `CVirtualRadio::WriteCodeplug`

*(qwen2.5-coder:14b, 41.4s)*

1. **Role**: This function appears to handle the process of writing a codeplug to a virtual radio, including error handling, state management, and communication with the radio.

2. **EEPROM / Persistence Mechanism**: The function involves several operations that could affect the permanent state on the radio, such as accessing and modifying data arrays, checking and setting flags, and potentially sending commands to the radio to commit changes. It also includes error handling and cleanup operations.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x80004003`, `0x80004005`, `0x405`
   - Offsets: `0x18`, `0x20`, `0x91`, `0x91`
   - Error HRESULTs: `0x80004003`, `0x80004005`
   - Callees: `FUN_1001d137`, `FUN_1001f273`, `FUN_1000d4b4`, `FUN_10021744`, `FUN_1001e4df`, `FUN_1001ddc8`, `FUN_1001d472`, `FUN_1001df9a`, `FUN_10006778`, `FUN_100069ff`, `FUN_100088bd`, `FUN_10017a4d`, `FUN_10017a2f`, `FUN_1001ff23`, `_mbscmp`, `_mbscmp_exref`

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_1001d137`, `FUN_1001f273`, `FUN_1000d4b4`, `FUN_10021744`, `FUN_1001e4df`, `FUN_1001ddc8`, `FUN_1001d472`, `FUN_1001df9a`, `FUN_10006778`, `FUN_100069ff`, `FUN_100088bd`, `FUN_10017a4d`, `FUN_10017a2f`, `FUN_1001ff23`. These functions are involved in various stages of the codeplug writing process and may contain the specific logic for committing changes to the radio's EEPROM.

---

## 19. `ByteData10.dll` — `FUN_1100421d` (`1100421d`)
- **Keywords:** state, rcmp
- **Strings:** `CRawBytes::Open SetCommState failed 
, CRawBytes::Open GetCommState failed 
, Connecting to Monitoring tool for TCP/IP-PPP, Connecting to Monitoring tool, TCP/IP, %d.%d.%d.%d, Failed, Failed`

*(qwen2.5-coder:14b, 35.9s)*

1. **Role**: This function appears to handle the initialization and configuration of a communication channel with a radio device, likely setting up a connection over TCP/IP or PPP/USNET. It also manages various states and configurations related to the radio's operation.

2. **EEPROM / Persistence Mechanism**: The function sets up communication parameters and handles different states, but it does not directly commit changes to EEPROM or flash. It seems to manage the transport layer and possibly locks/unlocks the radio's state, but the actual persistence mechanism (like committing changes to EEPROM) is not explicitly shown in this function. It may rely on other functions or mechanisms not present in the provided code snippet.

3. **Key Constants / Opcodes / Calls**:
   - **Constants**: `0x80004005`, `0x80004001`, `0xcad`, `0x1000`, `0x1f43`.
   - **Opcodes**: None directly visible in the provided code snippet.
   - **Error HRESULTs**: `0xecec0003`, `0x80004005`, `0x80004001`.
   - **Callees**: `FUN_11004edc`, `FUN_11004ecf`, `FUN_11007170`, `FUN_11007180`, `CreateFileA`, `SetCommTimeouts`, `GetCommState`, `SetCommState`, `SetupComm`, `SetCommMask`, `FUN_110054f0`, `FUN_110032cf`, `operator_new`, `FUN_11005601`, `FUN_110056f3`, `FUN_110057de`, `FUN_11005824`, `FUN_11006a73`.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_11004c07`, `FUN_11004c4b`, and `FUN_11005601`. These functions seem to handle specific operations that might involve committing changes to the radio's state, and further analysis of these functions could provide insights into the EEPROM persistence mechanism.

---

## 20. `ByteData10.dll` — `FUN_11005601` (`11005601`)
- **Keywords:** nwrite, nread
- **Strings:** `fudally_usb.dll, fudallyUSB_getDevDescriptor, fudallyUSB_write, fudallyUSB_read, fudallyUSB_close, fudallyUSB_openWrite, fudallyUSB_openRead`

*(qwen2.5-coder:14b, 22.3s)*

1. **Role**: This function initializes a structure with various function pointers from the `fudally_usb.dll` library, setting up USB read and write operations. It also stores some parameters and initializes several fields in the structure to default values.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly handle EEPROM persistence. It sets up the environment for USB operations, which could be used in subsequent operations to write to or read from the radio's EEPROM. The actual persistence mechanism would involve calls to the USB write functions, which might then interact with the radio's EEPROM.

3. **Key Constants / Opcodes / Calls**:
   - `0x2c`, `0x2e`: Offsets where `param_2` and `param_3` are stored.
   - `0xffffffff`: Default values set for several fields in the structure.
   - `LoadLibraryA("fudally_usb.dll")`: Loads the USB library.
   - `GetProcAddress`: Retrieves addresses of functions from the USB library.
   - `s_fudallyUSB_openRead_11017a14`, `s_fudallyUSB_openWrite_110179fc`, `s_fudallyUSB_close_110179e8`, `s_fudallyUSB_read_110179d8`, `s_fudallyUSB_write_110179c4`, `s_fudallyUSB_getDevDescriptor_110179a8`: Strings representing function names in the USB library.

4. **Next Bite**: The next callees to inspect for EEPROM persistence would be the functions pointed to by the function pointers stored in the structure, specifically `s_fudallyUSB_write_110179c4` and `s_fudallyUSB_read_110179d8`. These are the functions that would handle actual data transfer to and from the radio, which could involve writing to or reading from the EEPROM.

---
