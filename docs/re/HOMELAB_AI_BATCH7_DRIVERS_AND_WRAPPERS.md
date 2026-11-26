# Homelab AI Function-by-Function Analysis: ASTRO 25 EEPROM & State Persistence

- **Model:** `qwen2.5-coder:14b` (`num_ctx=8192` on TrueNAS RTX 3080)
- **Scope:** Undocumented functions in `NextGen10.dll` and `ByteData10.dll` related to EEPROM, host markers, commit/lock, and state persistence.
- **Total functions analyzed:** 89

---

## 1. `PSTWrapper.dll` — `USBGetDeviceList` (`10001280`)
- **Keywords:** exported-or-named
- **Strings:** `Motorola_Flash`

*(qwen2.5-coder:14b, 10.3s)*

1. **Role**: The `USBGetDeviceList` function initializes a list of USB devices, likely filtering or preparing a list of connected Motorola devices based on the referenced string "Motorola_Flash".

2. **EEPROM / Persistence Mechanism**: This function does not directly handle EEPROM persistence or state commitment. It appears to be a transport helper function that prepares the environment for device interaction, possibly setting up or resetting internal states before device enumeration.

3. **Key Constants / Opcodes / Calls**:
   - Referenced string: "Motorola_Flash"
   - Function call: `iDEN_PSTGetDeviceList()`

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `iDEN_PSTGetDeviceList()`, as it is the primary function called within `USBGetDeviceList` and may handle device-specific initialization or state management.

---

## 2. `PSTWrapper.dll` — `USBReadData` (`100013a0`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 15.0s)*

1. **Role**: The `USBReadData` function appears to handle USB data reading operations. It looks up a pointer in a map using the provided parameter and then calls another function, `iDEN_PSTReadData`, to perform the actual read operation.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly handle EEPROM persistence. It seems to be a transport helper function that delegates the read operation to another function. The persistence mechanism would likely be handled by `iDEN_PSTReadData` or other related functions.

3. **Key Constants / Opcodes / Calls**: 
   - `CMapPtrToPtr::Lookup` is called with a map pointer (`DAT_10003100`) and the first parameter (`param_1`).
   - The function returns `5` if the lookup fails.
   - The function calls `iDEN_PSTReadData` with the looked-up pointer (`local_4`), the original parameters (`param_1`, `param_2`, `param_3`, `param_4`), and a constant `2`.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `iDEN_PSTReadData`. This function is likely responsible for the actual read operation and may involve interactions with the EEPROM or other persistent storage mechanisms.

---

## 3. `PSTWrapper.dll` — `USBWriteData` (`100013f0`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 14.9s)*

1. **Role**: The `USBWriteData` function appears to handle USB data writing operations. It looks up a pointer in a map using the provided parameter and then calls another function, `iDEN_PSTWriteData`, to perform the actual write operation.

2. **EEPROM / Persistence Mechanism**: The function is likely involved in the process of writing data to the radio's EEPROM or flash memory, as indicated by the call to `iDEN_PSTWriteData`. However, the specific mechanism of how it makes the state permanent (e.g., commit, lock/unlock, reset) is not directly evident from this function alone.

3. **Key Constants / Opcodes / Calls**: 
   - The function uses a map lookup with the address `DAT_10003100`.
   - It calls `iDEN_PSTWriteData` with parameters including `param_1`, `param_2`, `param_3`, and `param_4`.
   - The return value `5` could indicate an error or a specific status code.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `iDEN_PSTWriteData`. This function is likely where the actual write operation to the radio's memory occurs, and understanding its implementation will provide more insight into how the state is made permanent.

---

## 4. `PortMgrWrapper.dll` — `operator=` (`10001000`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 12.1s)*

1. **Role**: This function is an assignment operator for the `PortMgrWrapper` class. It appears to perform a shallow copy of the `PortMgrWrapper` object pointed to by `param_1` to the object pointed to by `this`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any other persistent storage mechanisms. It seems to be a utility function for managing object state within the application.

3. **Key Constants / Opcodes / Calls**: None. The function does not contain any specific hex constants, offsets, error HRESULTs, or calls to other functions that are relevant to EEPROM persistence.

4. **Next Bite**: Since this function does not directly interact with EEPROM or any other persistent storage mechanisms, there is no specific callee to inspect next for tracing EEPROM persistence. Further analysis should focus on other functions or classes that are known to handle EEPROM operations, such as those involving the `0x0106` opcode for entering modes or the `0x0107` opcode for unlocking security.

---

## 5. `PortMgrWrapper.dll` — `PortMgrWrapper` (`10001020`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 9.1s)*

1. **Role**: This function is a constructor for the `PortMgrWrapper` class. It initializes the object by returning the `this` pointer, indicating that it does not perform any additional initialization or operations.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function itself does not directly interact with EEPROM or manage state persistence. It appears to be a basic constructor that sets up the object for further operations.

3. **Key Constants / Opcodes / Calls**: 
   - None observed in the provided code snippet.

4. **Next Bite**: Since this function does not contain any calls to other functions or operations related to EEPROM persistence, there is no specific callee to inspect next. Further analysis should focus on other functions within the `PortMgrWrapper.dll` or related modules that might handle EEPROM operations.

---

## 6. `PortMgrWrapper.dll` — `GetListOfDevices` (`10001030`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 13.1s)*

1. **Role**: The `GetListOfDevices` function initializes a `CPortManager` object, lists devices, and copies device names into the provided buffer. It returns the number of devices found or an error code.

2. **EEPROM / Persistence Mechanism**: This function does not directly manipulate EEPROM or flash storage. It appears to be a transport helper function that interacts with devices but does not handle state persistence mechanisms like commit, lock/unlock, or reset.

3. **Key Constants / Opcodes / Calls**:
   - `0x1a01`: Loop counter for initializing `DeviceList` array.
   - `0xd0`: Offset for copying device names into the buffer.
   - `CPortManager::CPortManager`: Constructor for `CPortManager`.
   - `CPortManager::ListDevices`: Method to list devices.
   - `CPortManager::~CPortManager`: Destructor for `CPortManager`.

4. **Next Bite**: The `CPortManager::ListDevices` method should be inspected next to trace any interactions with the radio's EEPROM or flash storage.

---

## 7. `PortMgrWrapper.dll` — `CreatePortMgrWrapperClass` (`10001120`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 11.3s)*

1. **Role**: The function `CreatePortMgrWrapperClass` allocates memory for an object using the `operator_new` function, likely to initialize an instance of a class related to port management.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with EEPROM or handle state persistence. It appears to be a helper function for creating an object, which may be involved in higher-level operations that affect EEPROM persistence.

3. **Key Constants / Opcodes / Calls**: 
   - `operator_new(1)`: Allocates memory for an object.
   - No specific hex constants, offsets, error HRESULTs, or callees (`FUN_*` / COM vtable offsets) are observed in the provided code snippet.

4. **Next Bite**: Since the function does not directly interact with EEPROM or persistence, the next step should be to inspect the class methods or other functions that this object might call, particularly those related to port management or communication, to trace how EEPROM persistence is handled.

---

## 8. `PortMgrWrapper.dll` — `TranslatorGuardHandler` (`100012f6`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 15.9s)*

1. **Role**: The `TranslatorGuardHandler` function appears to be an exception handler within the `PortMgrWrapper.dll` library. It processes exceptions by calling internal C++ frame handlers and possibly unwinding nested frames, depending on the exception record and registration node provided.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be more of a transport helper, managing exception handling and possibly state transitions within the application, which could indirectly affect state persistence through controlled execution paths.

3. **Key Constants / Opcodes / Calls**:
   - `DAT_10009040`: A data pointer or constant used for comparison.
   - `0x66`: A bitmask used in the exception record check.
   - `0x8`: A bitmask used to modify the exception record.
   - `___InternalCxxFrameHandler`: A function call for internal C++ exception handling.
   - `_UnwindNestedFrames`: A function call to unwind nested exception frames.
   - `_CallSETranslator`: A function call to handle structured exception translators.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `___InternalCxxFrameHandler` and `_CallSETranslator`, as they are directly involved in handling exceptions and could potentially manage state transitions or interactions with the underlying storage mechanisms.

---

## 9. `PortMgrWrapper.dll` — `IsExceptionObjectToBeDestroyed` (`1000144a`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 11.1s)*

1. **Role**: This function checks if a given exception object is to be destroyed by traversing the exception chain linked list managed by the thread data structure (`_ptiddata`).

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function does not directly interact with EEPROM or manage state persistence on the radio. It is a utility function related to exception handling.

3. **Key Constants / Opcodes / Calls**: 
   - `__getptd()`: Retrieves the thread data structure.
   - `_curexception`: Pointer to the current exception in the thread data structure.
   - `piVar2[1]`: Moves to the next exception in the chain.

4. **Next Bite**: Since this function is related to exception handling and does not directly manage EEPROM persistence, there is no specific callee to inspect next for EEPROM persistence. Further analysis should focus on other functions that interact with the radio's state management, such as those handling opcodes or managing partitions.

---

## 10. `PortMgrWrapper.dll` — `report_failure` (`10001510`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 10.6s)*

1. **Role**: The `report_failure` function is responsible for handling a security error by invoking a security error handler and then terminating the process with an exit code of 3.

2. **EEPROM / Persistence Mechanism**: This function does not directly interact with the EEPROM or handle state persistence on the radio. It appears to be a transport helper function that deals with error handling and process termination.

3. **Key Constants / Opcodes / Calls**: 
   - The function calls `___security_error_handler(1)`, where `1` is likely an error code or flag.
   - The function then calls `ExitProcess(3)`, where `3` is the exit code indicating an error.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence would be `___security_error_handler`, as it is directly called by `report_failure` and might contain more detailed logic related to error handling and state management.

---

## 11. `PortMgrWrapper.dll` — `operator_new` (`1000167e`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 10.9s)*

1. **Role**: This function is an overloaded operator `new` that allocates memory for an object of a specified size. It calls `__nh_malloc` to perform the actual memory allocation.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function is primarily responsible for memory management and does not directly interact with the radio's EEPROM or state persistence mechanisms.

3. **Key Constants / Opcodes / Calls**: 
   - `__nh_malloc` is the function called to allocate memory.
   - No specific hex constants, offsets, error HRESULTs, or opcodes are observed in the provided code snippet.

4. **Next Bite**: Since this function is a memory allocator and does not directly interact with the radio's EEPROM or state persistence, the next step should be to inspect the callees of functions that are known to interact with the radio's EEPROM or state persistence mechanisms, such as `ReadIsh`, `WriteIsh`, or `EnterMode`.

---

## 12. `PortMgrWrapper.dll` — `TypeMatch` (`10001929`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 12.7s)*

1. **Role**: The `TypeMatch` function appears to compare two types, likely in the context of exception handling or type checking within the application. It checks if the types match based on certain criteria, such as name and attributes.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or handle state persistence. It seems to be a utility function for type comparison, which is part of the application's internal logic rather than managing the radio's permanent state.

3. **Key Constants / Opcodes / Calls**: 
   - `_strcmp` is called for string comparison.
   - The function checks specific bits in the `adjectives` field of the `_s_HandlerType` structure.
   - No specific hex constants, opcodes, or error HRESULTs are directly observed in the provided code snippet.

4. **Next Bite**: Since this function is primarily involved in type comparison and does not directly interact with EEPROM or state persistence, there is no immediate next callee to inspect for EEPROM persistence. The focus should shift to other functions that handle communication with the radio or manage its state.

---

## 13. `PortMgrWrapper.dll` — `AdjustPointer` (`10001aa9`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 9.9s)*

1. **Role**: The `AdjustPointer` function adjusts a pointer based on the input parameters, potentially involving some form of pointer arithmetic and conditional offset addition.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function appears to be a general-purpose pointer adjustment utility and does not directly interact with EEPROM or state persistence mechanisms.

3. **Key Constants / Opcodes / Calls**: 
   - No specific hex constants, opcodes, or error HRESULTs are directly observed in the provided code snippet.
   - The function involves pointer arithmetic and conditional logic based on input parameters.

4. **Next Bite**: Since this function does not directly interact with EEPROM or state persistence, the next step would be to trace the call stack to identify higher-level functions that might involve EEPROM operations. Look for callees that interact with the transport layer or handle specific opcodes related to EEPROM operations.

---

## 14. `PortMgrWrapper.dll` — `CallCatchBlock` (`10001ac8`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 14.3s)*

1. **Role**: The `CallCatchBlock` function is a part of the exception handling mechanism in the `PortMgrWrapper.dll`. It appears to manage the execution flow when an exception occurs, potentially invoking custom exception handlers or translators.

2. **EEPROM / Persistence Mechanism**: This function does not directly interact with the EEPROM or flash storage of the radio. It is more likely a transport helper function that manages the exception handling process, which could be indirectly related to ensuring state persistence by maintaining the integrity of the communication channel.

3. **Key Constants / Opcodes / Calls**: 
   - `FUN_10001c1d`: A function call within the function.
   - `__SEH_prolog` and `__SEH_epilog`: Replaced with custom injection functions, possibly for handling structured exception handling.
   - `_CallCatchBlock2`: A function call that processes the exception handling logic.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `_CallCatchBlock2` at address `10001c1d`. This function likely contains more detailed logic related to handling exceptions and could provide insights into how the system ensures state persistence through exception management.

---

## 15. `PortMgrWrapper.dll` — `BuildCatchObject` (`10001c8c`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 13.7s)*

1. **Role**: The `BuildCatchObject` function appears to handle exception catching and object construction in a C++ environment, likely related to error handling and resource management.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that manages memory and object states, possibly indirectly affecting persistence through memory validation and object copying.

3. **Key Constants / Opcodes / Calls**:
   - `_ValidateRead` and `_ValidateWrite` are called to ensure memory access is valid.
   - `AdjustPointer` is used to adjust pointers.
   - `_memmove` is used to copy memory.
   - `FID_conflict__CallMemberFunction1` is called to invoke member functions.
   - `in_ECX` and `in_EDX` are used as pointers to data structures.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `_ValidateRead`, `_ValidateWrite`, and `FID_conflict__CallMemberFunction1`, as they involve memory operations that could be related to state persistence mechanisms.

---

## 16. `PortMgrWrapper.dll` — `FindHandlerForForeignException` (`10001e6f`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 14.1s)*

1. **Role**: The function `FindHandlerForForeignException` is responsible for handling foreign exceptions in a structured exception handling (SEH) context. It searches for an appropriate exception handler based on the exception record and the current stack context.

2. **EEPROM / Persistence Mechanism**: This function does not directly interact with the radio's EEPROM or flash memory. It is a transport helper function that aids in exception handling, which may indirectly affect state persistence by ensuring that the system can recover from exceptions without losing critical data.

3. **Key Constants / Opcodes / Calls**:
   - `0x7ffffffd`: A constant used to check the exception code.
   - `_CallSETranslator`: A function call that attempts to translate the exception.
   - `_GetRangeOfTrysToCheck`: A function call to determine the range of try blocks to check for exception handling.
   - `CatchIt`: A function call to handle the caught exception.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence should be `_CallSETranslator` and `_GetRangeOfTrysToCheck`, as they are involved in the exception handling process and might interact with system-level operations that could affect state persistence.

---

## 17. `PortMgrWrapper.dll` — `FindHandler` (`10001f2d`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 14.4s)*

1. **Role**: The `FindHandler` function is part of the exception handling mechanism in the `PortMgrWrapper.dll`. It processes exceptions by finding appropriate handlers based on the exception record and function information.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It is more of a transport helper that manages exception handling, which could indirectly influence state persistence through error handling and recovery mechanisms.

3. **Key Constants / Opcodes / Calls**:
   - Exception HRESULT: `-0x1f928c9d`
   - Specific offsets: `0x10`, `0x14`, `0x1c`
   - Function calls: `_inconsistency()`, `_ValidateRead()`, `___DestructExceptionObject()`, `CatchIt()`, `FindHandlerForForeignException()`, `terminate()`

4. **Next Bite**: The `CatchIt` function should be inspected next to trace EEPROM persistence, as it is responsible for executing the catch block associated with the exception, which could involve state management or recovery actions.

---

## 18. `PortMgrWrapper.dll` — `terminate` (`100024e2`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 10.0s)*

1. **Role**: The `terminate` function is responsible for terminating the program. It calls `__getptd` to retrieve thread-specific data and then invokes a cleanup routine if available. Finally, it calls `_abort` to terminate the process.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It is a transport helper function that ensures proper cleanup before terminating the program.

3. **Key Constants / Opcodes / Calls**: 
   - `__getptd`: Retrieves thread-specific data.
   - `ptlocinfo`: Pointer to thread local information.
   - `_abort`: Aborts the program.

4. **Next Bite**: Since this function does not directly interact with EEPROM or persistence mechanisms, there is no specific callee to inspect next for tracing EEPROM persistence. The focus should remain on other functions that handle EEPROM operations.

---

## 19. `PortMgrWrapper.dll` — `doexit` (`10002a8f`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 19.9s)*

1. **Role**: The `doexit` function is responsible for handling the termination of a process. It checks a condition (`DAT_1000998c == 1`) to decide whether to terminate the current process using `TerminateProcess`. It also manages cleanup tasks such as calling initialization terminators and a custom function (`FUN_10002b3e`).

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It appears to be a transport helper function that manages process termination and cleanup, which may indirectly affect state persistence by ensuring all resources are properly released before the process exits.

3. **Key Constants / Opcodes / Calls**:
   - `DAT_1000998c`: A global variable checked to determine if the process should be terminated.
   - `DAT_10009988`: Set to 1, possibly indicating a state change or flag.
   - `DAT_10009984`: Set to the value of `param_3`, which could be a flag or status code.
   - `DAT_1000a168` and `DAT_1000a164`: Pointers used in a loop to call functions stored in an array.
   - `__initterm`: A function used to call initialization terminators.
   - `FUN_10002b3e`: A custom function called during cleanup.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_10002b3e`, as it is called during the cleanup process and may contain logic related to state persistence or resource management.

---

## 20. `PortMgrWrapper.dll` — `parse_cmdline` (`10002f3e`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 16.6s)*

1. **Role**: The `parse_cmdline` function appears to parse command-line arguments, handling quotes and backslashes, and possibly storing the parsed arguments in a buffer. It also counts the number of arguments and updates a parameter with this count.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or handle state persistence on the radio. It seems to be a transport helper function that processes command-line input, which could be part of a larger process that eventually affects the radio's state.

3. **Key Constants / Opcodes / Calls**: 
   - Hex constants: `0x22` (double quote), `0x20` (space), `0x09` (tab), `0x5c` (backslash).
   - Offsets: `DAT_10009e20` (used in bitwise operations).
   - No specific opcodes or HRESULTs are directly observed in the code snippet.

4. **Next Bite**: Since this function is primarily focused on parsing command-line arguments, the next step would be to inspect any callees or functions that this function might call, especially those that could be involved in communication or state management with the radio. Look for functions that handle data transmission, state updates, or interactions with the radio's memory.

---

## 21. `PortMgrWrapper.dll` — `setSBCS` (`10003f1c`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 16.6s)*

1. **Role**: The `setSBCS` function initializes or resets a series of global variables and memory locations to zero. It appears to be a setup or initialization routine for some internal state management within the application.

2. **EEPROM / Persistence Mechanism**: This function does not directly interact with the EEPROM or flash storage to make state permanent. It is more likely a transport helper or internal state reset function that prepares the system for subsequent operations, possibly involving EEPROM writes or commits.

3. **Key Constants / Opcodes / Calls**: 
   - Memory addresses: `DAT_10009e20`, `DAT_10009f24`, `DAT_10009e04`, `DAT_10009dfc`, `DAT_10009f30`, `DAT_10009f34`, `DAT_10009f38`
   - Loop count: `0x40` (64 iterations)
   - No specific opcodes or HRESULTs are observed in the provided code snippet.

4. **Next Bite**: Since this function does not directly interact with EEPROM, the next step would be to inspect any callees or functions that are called after `setSBCS` to see if they involve EEPROM operations or state persistence mechanisms. Look for functions that might handle write operations, commit transactions, or lock/unlock mechanisms.

---

## 22. `PortMgrWrapper.dll` — `setSBUpLow` (`10003f45`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 15.8s)*

1. **Role**: The function `setSBUpLow` appears to initialize or configure character case conversion tables, possibly for use in string processing or formatting within the application.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be a utility function for setting up internal data structures for character handling, which may be indirectly related to data transmission or processing before any EEPROM operations.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x20`, `0x41`, `0x5a`, `0x60`, `0x7b`
   - Offsets: `&DAT_10009e20`, `&DAT_10009f40`
   - Callees: `GetCPInfo`, `___crtGetStringTypeA`, `___crtLCMapStringA`

4. **Next Bite**: The callees `___crtGetStringTypeA` and `___crtLCMapStringA` should be inspected next to trace any potential interactions with string processing or character encoding that might be indirectly related to EEPROM persistence.

---

## 23. `PortMgrWrapper.dll` — `siglookup` (`1000641c`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 15.3s)*

1. **Role**: The `siglookup` function iterates through a list of entries, comparing a value at an offset of 4 bytes from each entry with a given value (`unaff_ESI`). It returns when a match is found or when it exhausts the list.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It appears to be a helper function for searching through a list of entries, possibly related to configuration or state management but not directly involved in EEPROM commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**: 
   - `0xc`: The offset used to move to the next entry in the list.
   - `DAT_1000911c`: A constant used to determine the number of entries in the list.
   - No specific opcodes or HRESULTs are observed in the provided code snippet.

4. **Next Bite**: Since this function is a search helper, the next step should be to inspect the caller of `siglookup` to understand its context and how it interacts with EEPROM persistence mechanisms. Look for calls to functions that involve opcodes like `0x0106` (EnterMode/Session), `0x0107` (UnlockSecurity), or any other functions that might involve direct EEPROM operations.

---

## 24. `RemoteRadioProg.exe` — `.ctor` (`004032e0`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 10.1s)*

1. **Role**: This function appears to be a constructor (`_ctor`) that modifies a parameter and checks a condition to potentially call another function via a software interrupt (`swi(4)`).

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that modifies parameters and checks conditions, possibly related to communication or state management.

3. **Key Constants / Opcodes / Calls**: 
   - `swi(4)`: Software interrupt call with argument `4`.
   - `SCARRY1(cVar1, cVar3)`: Condition check involving two variables.

4. **Next Bite**: The next function to inspect should be the one pointed to by `pcVar2`, which is the result of the `swi(4)` call. This function might be responsible for actual EEPROM persistence operations.

---

## 25. `Security.exe` — `FUN_00401170` (`00401170`)
- **Keywords:** has-strings
- **Strings:** `Unsupported Operating System, This application has to be launched from the CPS, Help file not found:
, {8B4196F6-822D-49b1-A5EC-7AB26041BC38}, {40A5A5E9-77A3-47b3-924C-158BF7EFE3B4}`

*(qwen2.5-coder:14b, 25.1s)*

1. **Role**: This function appears to be the entry point for the `Security.exe` application. It checks the operating system version, parses command-line arguments, and initializes the application's main dialog. It also handles specific command-line options related to application behavior and displays error messages if certain conditions are not met.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. It seems to be more of a transport helper, ensuring the application is launched correctly and handling command-line options. It does not perform any explicit operations related to committing state to the radio's permanent storage.

3. **Key Constants / Opcodes / Calls**:
   - **Strings**: "Unsupported Operating System", "This application has to be launched from the CPS", "Help file not found:\r\n", "{8B4196F6-822D-49b1-A5EC-7AB26041BC38}", "{40A5A5E9-77A3-47b3-924C-158BF7EFE3B4}"
   - **Function Calls**: `GetVersionExA`, `FUN_004047a0`, `CWinApp::ParseCommandLine`, `_mbscmp`, `CString::MakeLower`, `CString::Right`, `CString::Left`, `CFile::GetStatus`, `AfxMessageBox`, `FUN_00401a00`, `CDialog::DoModal`, `FUN_00401bb0`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_004047a0`, `FUN_00401a00`, and `FUN_00401bb0`. These functions might contain more detailed logic related to the application's behavior and interactions with the radio's storage.

---

## 26. `Security.exe` — `FUN_00401450` (`00401450`)
- **Keywords:** has-strings
- **Strings:** `KeyHelp.KeyPopup`

*(qwen2.5-coder:14b, 19.5s)*

1. **Role**: This function initializes COM components, creates an instance of a COM object identified by the ProgID "KeyHelp.KeyPopup", and invokes a method on this object with parameters passed to the function. It handles memory allocation, error checking, and COM uninitialization.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It appears to be a transport helper that sets up a COM-based communication channel, possibly for higher-level operations that could involve EEPROM persistence. The actual persistence mechanism is likely handled by the COM object methods invoked.

3. **Key Constants / Opcodes / Calls**:
   - ProgID: "KeyHelp.KeyPopup"
   - COM CLSID: `local_30`
   - COM IID: `DAT_0040a160`
   - HRESULTs: `0x8007000e` (E_OUTOFMEMORY)
   - COM method invocation: `(**(code **)(*local_18 + 0x28))(local_18, param_1, uVar7, param_2, param_3)`
   - COM release: `(**(code **)(*local_18 + 8))(local_18)`

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_00405a8e`, which is called to create a BSTR object. This function might be responsible for preparing data that could be written to EEPROM or involved in the persistence mechanism.

---

## 27. `Security.exe` — `FUN_004016b0` (`004016b0`)
- **Keywords:** has-strings
- **Strings:** `KeyHelp.KeyProcWindow`

*(qwen2.5-coder:14b, 18.3s)*

1. **Role**: This function initializes COM components related to a key processing window, possibly for handling security operations on the radio. It manages COM initialization, object creation, and error handling.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. It appears to be a transport helper that sets up the environment for security operations, which may indirectly affect state persistence through COM interactions.

3. **Key Constants / Opcodes / Calls**:
   - COM CLSID: `0x0040a1a8` (KeyHelp.KeyProcWindow)
   - COM IID: `0x0040a198`
   - HRESULTs: `0x8007000e` (E_OUTOFMEMORY)
   - COM method calls: `CLSIDFromProgID`, `CoCreateInstance`, `CoUninitialize`
   - Internal function calls: `FUN_00405a8e`, `FUN_00405a42`, `FUN_00401680`

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_00405a8e`, which is called with the local string `local_28`. This function likely handles the actual interaction with the radio's security features, so it should be analyzed to understand how it affects state persistence.

---

## 28. `Security.exe` — `FUN_00401a00` (`00401a00`)
- **Keywords:** has-strings
- **Strings:** `Element, Name`

*(qwen2.5-coder:14b, 20.7s)*

1. **Role**: This function initializes a dialog window and sets up various UI elements, including strings and icons. It also creates an instance of `CSecurityObj` and sets its family.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It appears to be a transport helper function that sets up the UI and initializes objects, but does not handle the actual persistence of state on the radio.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x65`, `0x6b`, `0xe`
   - Offsets: `0x60`, `0x80`, `0x88`, `0x8c`, `0x90`, `0x94`, `0x98`, `0xb4`, `0xb8`, `0xf8`, `0x138`, `0x13c`, `0x140`, `0x144`, `0x148`
   - Strings: `"Element"`, `"Name"`
   - Calls: `FUN_00404940`, `CString::CString`, `CStringList::CStringList`, `CWnd::CWnd`, `AfxFindResourceHandle`, `LoadIconA`, `SysAllocString`, `operator_new`, `CSecurityObj::CSecurityObj`, `CString::CString`, `CSecurityObj::SetFamily`

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_00404940`, as it is called early in the function and may handle initialization or setup related to security or state management.

---

## 29. `Security.exe` — `FUN_00401d00` (`00401d00`)
- **Keywords:** has-strings
- **Strings:** `You don't have sufficient permissions to run this program. Please contact your system administrator.
 For more information on this feature, please type 'Feature Access Setup' from the index of the CPS's
 online help system., Administrators, {5F854CEA-4E57-4b6e-9EA6-8F0476B349E3}, Fatal Error.  The application will quit,  - ASTRO 25 CPS,  - ASTRO CPS, Feature Access setup, &About Security...`

*(qwen2.5-coder:14b, 25.6s)*

1. **Role**: This function initializes a dialog window for security settings in the CPS application. It checks user permissions, loads configuration files, and sets up the UI based on the user's administrative status.

2. **EEPROM / Persistence Mechanism**: The function does not directly handle EEPROM persistence. It appears to be a transport helper function that sets up the environment and checks permissions, which are prerequisites for operations that might affect the radio's permanent state.

3. **Key Constants / Opcodes / Calls**:
   - Strings: "You don't have sufficient permissions to run this program.", "Administrators", "{5F854CEA-4E57-4b6e-9EA6-8F0476B349E3}", "Fatal Error. The application will quit", " - ASTRO 25 CPS", " - ASTRO CPS", "Feature Access setup", "&About Security..."
   - Function Calls: `CSecurityObj::GetFeaturesFilePath`, `CFile::GetStatus`, `NetGetDCName`, `NetUserEnum`, `NetUserGetLocalGroups`, `NetApiBufferFree`
   - COM Calls: `SendMessageA`, `AppendMenuA`, `SetWindowTextA`, `Create`, `CenterWindow`, `ShowWindow`, `AllocSysString`, `SysAllocString`, `SysFreeString`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_00404f70`, `FUN_00404ca0`, and `FUN_004029d0`, as they are involved in setting up and managing security features that might interact with the radio's permanent state.

---

## 30. `Security.exe` — `FUN_00402210` (`00402210`)
- **Keywords:** has-strings
- **Strings:** `Column`

*(qwen2.5-coder:14b, 17.2s)*

1. **Role**: This function appears to recursively insert items into a tree control, likely populating a user interface with data from some source. It processes a list of items, compares strings, and inserts matching items into the tree.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper or UI update function, possibly indirectly affecting persistence through UI state management.

3. **Key Constants / Opcodes / Calls**:
   - `s_Column_0040a3b4`: A string reference.
   - `0x34` and `0x58` offsets in the `param_2` structure, likely pointing to function pointers in a vtable.
   - `FUN_00404c20`, `FUN_00402390`, `FUN_00405840`, `FUN_00402210`: Specific function calls within the code.
   - `0xffff0002`: A constant used in the `InsertItem` call.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_00404c20` and `FUN_00402390`, as they are directly involved in processing and comparing items, which could be related to state management or persistence mechanisms.

---

## 31. `Security.exe` — `FUN_00402390` (`00402390`)
- **Keywords:** has-strings
- **Strings:** `TRUE`

*(qwen2.5-coder:14b, 16.2s)*

1. **Role**: This function compares a string from `param_1` with the string "TRUE". If they match, it allocates a BSTR from `local_30` and assigns it to `*param_2`. It returns `true` if the strings match, otherwise `false`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It appears to be a helper function for string comparison and BSTR allocation, which may be part of a larger process involving EEPROM persistence.

3. **Key Constants / Opcodes / Calls**:
   - String "TRUE" at `u_TRUE_0040a3c4`.
   - Calls to `FUN_00404b20` with offsets `0x80` and `0x88` from `this`.
   - `SysAllocString` for BSTR allocation.
   - `wcscmp` for string comparison.

4. **Next Bite**: Inspect `FUN_00404b20` next to understand how it processes the input parameters and what it does with the offsets `0x80` and `0x88` from `this`. This function might be involved in preparing or reading data that could be related to EEPROM persistence.

---

## 32. `Security.exe` — `FUN_004027c0` (`004027c0`)
- **Keywords:** has-strings
- **Strings:** `PROFILES`

*(qwen2.5-coder:14b, 20.6s)*

1. **Role**: This function appears to update user settings and manage a tree control in a GUI application, possibly related to security settings. It handles operations like setting check states in a tree view and updating user settings through a `CSecurityObj` object.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by updating user settings through the `CSecurityObj::UpdateUserSettings` method. It does not directly interact with EEPROM or flash operations but relies on the underlying `CSecurityObj` methods to ensure settings are persisted.

3. **Key Constants / Opcodes / Calls**:
   - `0x110a`: A message sent to a window, possibly to retrieve a tree item.
   - `FUN_00402c50`, `FUN_00402cc0`, `FUN_00403140`, `FUN_00403b90`: Various function calls within the code.
   - `CSecurityObj::UpdateUserSettings`, `CSecurityObj::GetSettingsForUser`, `CSecurityObj::GetDomainName`: Methods called on a `CSecurityObj` object.
   - `s_PROFILES_0040a3d4`, `DAT_0040a3d0`: Strings used in the function.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `CSecurityObj::UpdateUserSettings` and `CSecurityObj::GetSettingsForUser`. These methods are likely responsible for the actual interaction with the radio's EEPROM or flash memory to ensure settings are committed and persisted.

---

## 33. `Security.exe` — `FUN_00403040` (`00403040`)
- **Keywords:** has-strings
- **Strings:** `Saving settings for element "`

*(qwen2.5-coder:14b, 15.0s)*

1. **Role**: This function appears to handle the saving of settings for a specific element, likely within a security context. It initializes and manipulates strings, calls a method to save settings, and performs cleanup operations.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by calling `CSecurityObj::SaveSettingsElement`, which likely involves writing to EEPROM or flash memory. It also includes calls to `FUN_004010a0` three times, which might be related to committing changes or ensuring persistence.

3. **Key Constants / Opcodes / Calls**:
   - `CSecurityObj::SaveSettingsElement` is called with an offset of `0xb4` from `param_1`.
   - `FUN_00403110` is called with parameters related to a tree control and an integer.
   - `FUN_004010a0` is called three times, possibly for committing changes or ensuring persistence.
   - `CString` operations are performed with specific offsets and parameters.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `CSecurityObj::SaveSettingsElement`, as it is directly responsible for saving settings and likely involves the actual writing to EEPROM or flash memory.

---

## 34. `Security.exe` — `FUN_004033c0` (`004033c0`)
- **Keywords:** has-strings
- **Strings:** `PROFILES, At least one tree element neeeds to be unchecked before saving a profile., Saved settings for , No user or profile selected`

*(qwen2.5-coder:14b, 15.7s)*

1. **Role**: This function appears to handle the saving of settings for a selected user or profile in a security context. It checks if a user or profile is selected and if the necessary conditions are met (e.g., at least one tree element unchecked), then proceeds to save the settings.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by invoking another function (`FUN_00403ad0`) which likely handles the actual commit of settings to EEPROM or flash. It does not directly perform commit, lock, unlock, or reset operations itself.

3. **Key Constants / Opcodes / Calls**:
   - Strings: "PROFILES", "At least one tree element neeeds to be unchecked before saving a profile.", "Saved settings for ", "No user or profile selected"
   - Offsets: `0xf8`, `0x138`, `0xb4`, `0xd8`, `0xb8`
   - Function call: `FUN_00403ad0`

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_00403ad0`, as it is directly called with parameters that likely include the settings to be saved.

---

## 35. `Security.exe` — `FUN_00403770` (`00403770`)
- **Keywords:** has-strings
- **Strings:** `At least one tree element neeeds to be unchecked before saving a profile., Overwrite the existing profile?, PROFILES*`

*(qwen2.5-coder:14b, 16.8s)*

1. **Role**: This function appears to manage profile operations in a security context. It handles user interactions for saving and overwriting profiles, and it checks the state of tree elements before saving.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by managing profile lists and user interactions. It does not directly interact with EEPROM or flash storage; instead, it prepares data for persistence through user confirmation and dialog management.

3. **Key Constants / Opcodes / Calls**:
   - Strings: "At least one tree element neeeds to be unchecked before saving a profile.", "Overwrite the existing profile?", "PROFILES*"
   - Calls: `FUN_00404480`, `FUN_00404690`, `FUN_00403ad0`
   - COM vtable offsets: `SendMessageA_exref`
   - HRESULTs: None explicitly observed

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_00404690` and `FUN_00403ad0`, as they handle profile population and saving, respectively. These functions are likely to interact more directly with the underlying storage mechanisms.

---

## 36. `Security.exe` — `FUN_00403c10` (`00403c10`)
- **Keywords:** has-strings
- **Strings:** `Only one instance of this aplication can be run at a time`

*(qwen2.5-coder:14b, 11.9s)*

1. **Role**: This function is responsible for displaying a message box indicating that only one instance of the application can be run at a time. It ensures that the application window is brought to the foreground and displayed.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with the radio's EEPROM or flash memory. It is more of a user interface management function.

3. **Key Constants / Opcodes / Calls**:
   - String: "Only one instance of this aplication can be run at a time" (address: `0040a4ac`)
   - Calls: `CWnd::ShowWindow`, `BringWindowToTop`, `SetForegroundWindow`, `AfxMessageBox`

4. **Next Bite**: Since this function does not directly interact with the radio's EEPROM or flash memory, there is no specific callee to inspect next for tracing EEPROM persistence. The focus should be on other functions that handle communication with the radio, such as those involving the transport layer or specific opcodes related to EEPROM operations.

---

## 37. `Security.exe` — `FUN_00403c40` (`00403c40`)
- **Keywords:** has-strings
- **Strings:** `PROFILES*, Delete profile '%s'?`

*(qwen2.5-coder:14b, 13.6s)*

1. **Role**: This function appears to handle the deletion of a profile. It prompts the user for confirmation, then clears user settings and updates them if the user confirms.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by calling `CSecurityObj::ClearUserSettings` and `CSecurityObj::UpdateUserSettings`. These methods likely involve writing to EEPROM or flash memory to make changes permanent.

3. **Key Constants / Opcodes / Calls**:
   - `0x147` and `0x144` are likely Windows message identifiers used in `SendMessageA` calls.
   - `s_PROFILES__0040a4a0` is a string constant related to profile handling.
   - `CSecurityObj::ClearUserSettings` and `CSecurityObj::UpdateUserSettings` are key methods for managing user settings persistence.

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `CSecurityObj::ClearUserSettings` and `CSecurityObj::UpdateUserSettings`. These methods are likely where the actual EEPROM/flash operations occur.

---

## 38. `Security.exe` — `FUN_00403f10` (`00403f10`)
- **Keywords:** has-strings
- **Strings:** `m_nIDContextHelp = 0`

*(qwen2.5-coder:14b, 17.1s)*

1. **Role**: This function checks if a context help ID is set in the provided window (`param_1`). If not, it displays a message box using `AfxMessageBox`. If set, it retrieves a dialog item based on the context help ID, gets its context help ID, and calls another function (`FUN_00401450`) with some parameters derived from the window. Finally, it resets the context help ID to 0.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It appears to be a UI-related function that handles context help IDs and does not involve any direct state persistence mechanisms.

3. **Key Constants / Opcodes / Calls**:
   - `s_m_nIDContextHelp___0_0040a500`: A string used in `AfxMessageBox`.
   - `0x140`, `0x144`, `0x148`: Offsets used to access fields in the `param_1` structure.
   - `FUN_00401450`: A function called with parameters derived from the window structure.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_00401450`. This function might contain the actual logic for handling context help IDs or interacting with the radio's state, so it should be analyzed further.

---

## 39. `Security.exe` — `FUN_00404220` (`00404220`)
- **Keywords:** has-strings
- **Strings:** `m_nIDContextHelp = 0`

*(qwen2.5-coder:14b, 16.9s)*

1. **Role**: This function checks if a context help ID is set in the provided `CWnd` object. If not, it displays a message box and returns. If set, it retrieves a dialog item based on the context help ID, gets its context help ID, and calls another function (`FUN_00401450`) with this ID and additional parameters. Finally, it resets the context help ID to 0.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It appears to be a helper function for UI operations, possibly related to displaying help messages.

3. **Key Constants / Opcodes / Calls**:
   - String: `"m_nIDContextHelp = 0"`
   - Offset: `param_1 + 100` (checked and reset)
   - Offset: `param_1 + 0x68` and `param_1 + 0x6c` (used in the call to `FUN_00401450`)
   - Function: `FUN_00401450` (called with context help ID and additional parameters)

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_00401450`. This function likely contains the logic for handling the context help ID and could potentially interact with the radio's EEPROM or flash storage.

---

## 40. `Security.exe` — `FUN_00404630` (`00404630`)
- **Keywords:** has-strings
- **Strings:** `Invalid profile name, * /'()%$#@!^~\|`+-."`

*(qwen2.5-coder:14b, 13.2s)*

1. **Role**: This function checks if the profile name contains any invalid characters. If valid, it proceeds to close the dialog; otherwise, it displays an error message and sends a message to the window.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It appears to be a validation step before proceeding with other operations that might affect persistent state.

3. **Key Constants / Opcodes / Calls**:
   - String: `"Invalid profile name"`
   - String: `"* /'()%$#@!^~\\|`+-.\""`
   - Function: `CWnd::UpdateData`
   - Function: `CString::FindOneOf`
   - Function: `CDialog::OnOK`
   - Function: `AfxMessageBox`
   - Function: `SendMessageA`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `CWnd::UpdateData`, `CString::FindOneOf`, `CDialog::OnOK`, and `SendMessageA`. These functions might indirectly influence the state persistence mechanism by handling user input or triggering other operations.

---

## 41. `Security.exe` — `FUN_00404720` (`00404720`)
- **Keywords:** has-strings
- **Strings:** `SecurityDlgClass`

*(qwen2.5-coder:14b, 13.4s)*

1. **Role**: This function initializes a `CString` object with the class name "SecurityDlgClass" and sets the first parameter to 0. It appears to be part of a larger process related to setting up a security dialog or class.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be involved in setting up a dialog or class, which may be part of a larger process that affects state persistence.

3. **Key Constants / Opcodes / Calls**:
   - `s_SecurityDlgClass_0040a548`: A string constant with the value "SecurityDlgClass".
   - `CString::CString`: A constructor for the `CString` class.
   - `CString::operator=`: An assignment operator for the `CString` class.

4. **Next Bite**: The next callees to inspect for EEPROM persistence would be any functions that interact with the transport layer or directly with storage, such as `FUN_00404720`'s callees or any functions that handle `CString` operations related to security settings.

---

## 42. `Security.exe` — `FUN_00404830` (`00404830`)
- **Keywords:** has-strings
- **Strings:** `hhctrl.ocx`

*(qwen2.5-coder:14b, 21.1s)*

1. **Role**: This function appears to load a DLL (Dynamic Link Library) named "hhctrl.ocx" or a dynamically determined library name, and then calls a function from this DLL with the provided parameters. It checks if the library and function pointers are already loaded and initialized, and if not, it attempts to load them.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly interact with the radio's EEPROM or flash memory. It is more of a transport helper function that loads and calls a specific function from a DLL, which might be responsible for EEPROM operations. The actual persistence mechanism would be in the called function from the DLL.

3. **Key Constants / Opcodes / Calls**:
   - `DAT_0040a72c`: A global variable that holds the handle to the loaded DLL.
   - `DAT_0040a734`: A global variable that indicates whether the DLL loading failed.
   - `DAT_0040a73c`: A global variable that holds the function pointer from the DLL.
   - `FUN_004048c9`: A function that fills the `local_108` buffer with a potential DLL name.
   - `LoadLibraryA`: Used to load the DLL.
   - `GetProcAddress`: Used to get the address of a function in the loaded DLL.
   - `hhctrl.ocx`: The name of the DLL that might be loaded if the dynamic name fails.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is the function pointed to by `DAT_0040a73c`, which is obtained via `GetProcAddress`. This function is likely responsible for the actual EEPROM operations and should be analyzed to understand how state is made permanent on the radio.

---

## 43. `Security.exe` — `FUN_004048c9` (`004048c9`)
- **Keywords:** has-strings
- **Strings:** `CLSID\{ADB880A6-D8FF-11CF-9377-00AA003B7A11}\InprocServer32`

*(qwen2.5-coder:14b, 15.7s)*

1. **Role**: This function attempts to open a specific registry key and read a value from it. It is likely used to retrieve configuration or security settings stored in the Windows registry.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. It is a transport helper function that retrieves data from the registry, which may be used by other parts of the system to manage state persistence on the radio.

3. **Key Constants / Opcodes / Calls**:
   - Registry key: `"CLSID\\{ADB880A6-D8FF-11CF-9377-00AA003B7A11}\\InprocServer32"`
   - Registry access rights: `0x20019` (KEY_READ | KEY_WOW64_64KEY)
   - Buffer size: `0x104` (260 bytes)
   - Error check: `LVar1 == 0` to determine if the registry operation was successful

4. **Next Bite**: Since this function is a registry read operation, the next step should be to inspect how the retrieved data is used within the application. Look for calls to other functions that might handle EEPROM operations or state persistence, such as those involving `FUN_*` or COM vtable offsets related to security or configuration management.

---

## 44. `Security.exe` — `FUN_00405300` (`00405300`)
- **Keywords:** has-strings
- **Strings:** `Copyright (c) %s Motorola, Inc. All rights reserved.`

*(qwen2.5-coder:14b, 16.2s)*

1. **Role**: This function generates a timestamp and formats a copyright string with the current year, which is then stored in a global variable.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any other persistent storage mechanism. It appears to be a utility function for generating a copyright notice.

3. **Key Constants / Opcodes / Calls**:
   - `DAT_0040a604`: Format string for `strftime`.
   - `s_Copyright__c___s_Motorola__Inc__A_0040a5cc`: Format string for `sprintf`.
   - `time(&local_c)`: Gets the current time.
   - `localtime(&local_c)`: Converts the time to local time.
   - `strftime((char *)((int)&local_c + 4),5,&DAT_0040a604,_Tm)`: Formats the time into a string.
   - `sprintf(&DAT_0040a744,s_Copyright__c___s_Motorola__Inc__A_0040a5cc,(char *)((int)&local_c + 4))`: Formats the copyright string with the year.

4. **Next Bite**: None. This function does not call any other functions that directly interact with EEPROM or persistent storage. Further analysis should focus on other functions that might handle EEPROM operations.

---

## 45. `fudally.sys` — `FUN_00011008` (`00011008`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 24.2s)*

1. **Role**: This function initializes a series of function pointers within a structure pointed to by `param_1`. It sets up various callbacks and handlers for different operations, likely related to the radio's functionality.

2. **EEPROM / Persistence Mechanism**: The function does not directly handle EEPROM persistence. Instead, it sets up function pointers that are likely to be invoked during operations that could affect the radio's state, such as committing changes or handling security. The actual persistence mechanism would be handled by the functions these pointers point to.

3. **Key Constants / Opcodes / Calls**:
   - Offsets: `0xe0`, `0x120`, `0x148`, `0x70`, `0x80`, `0x100`, `0x90`, `0x88`, `0x68`, `0x30`
   - Function pointers: `FUN_0001337c`, `FUN_0001276c`, `FUN_00011298`, `FUN_000131e0`, `FUN_00013308`, `FUN_000123d0`, `FUN_00013928`, `FUN_000110a0`
   - Data pointer: `&DAT_00011094`

4. **Next Bite**: The callees `FUN_0001337c`, `FUN_0001276c`, `FUN_00011298`, `FUN_000131e0`, `FUN_00013308`, `FUN_000123d0`, `FUN_00013928`, and `FUN_000110a0` should be inspected next to trace EEPROM persistence. These functions are likely responsible for handling specific operations that could affect the radio's state, including committing changes to EEPROM.

---

## 46. `fudally.sys` — `FUN_000110a0` (`000110a0`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 17.7s)*

1. **Role**: This function appears to create and initialize a device object in the Windows Driver Model (WDM) environment, setting up various device properties and interfaces. It also checks for available WDM versions and sets power states.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be more of a transport helper, setting up device interfaces and handling device stack attachment. It does not explicitly show mechanisms for committing state to EEPROM or handling locks/unlocks directly.

3. **Key Constants / Opcodes / Calls**:
   - `IoCreateDevice` with device type `0x80` and size `0x238`.
   - `IoAttachDeviceToDeviceStack`.
   - `IoRegisterDeviceInterface` with GUID `DAT_00015150`.
   - `IoIsWdmVersionAvailable` checks for WDM versions 1.0, 1.5, 1.10, and 1.20.
   - `PoSetPowerState` to set the device power state.
   - Error HRESULT `0xc000000e` if device attachment fails.

4. **Next Bite**: The next callees to inspect for EEPROM persistence would be `IoRegisterDeviceInterface` and any other functions that interact with device interfaces or power states, as these might indirectly affect how the device handles data persistence.

---

## 47. `fudally.sys` — `FUN_00011298` (`00011298`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 26.1s)*

1. **Role**: This function appears to handle various operations based on a parameter (`cVar1`), potentially involving state management and communication with a device. It checks conditions, acquires locks, and calls other functions to perform specific tasks.

2. **EEPROM / Persistence Mechanism**: The function involves acquiring and releasing spinlocks, setting state flags, and calling other functions that likely handle EEPROM operations. It also increments counters and adjusts pointers, suggesting it manages state persistence indirectly through these operations.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x88`, `0x90`, `0xa0`, `0x8c`, `0x100`, `0x40`, `0xb8`, `0x30`, `0x38`, `0x43`
   - Error HRESULT: `0xc0000056`
   - Callees: `FUN_000125f4`, `FUN_000137b8`, `FUN_000114b8`, `FUN_0001266c`, `FUN_00011f88`, `FUN_00011d64`, `FUN_00011c20`, `FUN_00011b1c`, `FUN_00011e68`, `FUN_0001211c`

4. **Next Bite**: The callees `FUN_000114b8`, `FUN_00011f88`, `FUN_00011d64`, `FUN_00011c20`, `FUN_00011b1c`, `FUN_00011e68`, and `FUN_0001211c` should be inspected next to trace EEPROM persistence, as they are conditionally called based on the value of `cVar1`.

---

## 48. `fudally.sys` — `FUN_000114b8` (`000114b8`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 26.1s)*

1. **Role**: This function appears to handle a complex operation involving device initialization, event handling, and state management. It initializes an event, copies data, sets device interface state, and manages spinlocks and timers.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by setting device interface states, managing spinlocks, and potentially triggering a timer that could lead to further state persistence operations. It does not directly perform EEPROM commit or reset operations but sets up conditions that could result in such actions.

3. **Key Constants / Opcodes / Calls**:
   - `0x103`: An HRESULT indicating a pending operation.
   - `FUN_000125d0`: A function pointer set in the device structure.
   - `FUN_0001166c`: A function called to manage device state.
   - `FUN_00013040`: A function called if a specific condition is met.
   - `FUN_0001225c`: A function called to finalize device operations.
   - Offsets like `0x40`, `0x68`, `0x70`, `0x78`, `0x80`, `0x88`, `0x8c`, `0x90`, `0xa0`, `0x140`, `0x148`, `0x14c`, `0x150`, `0x158`, `0x198`, `0x230`, `0x100`, `0x104`, and `0x114` are used to access various fields in the device structure.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_0001166c`, `FUN_00013040`, and `FUN_0001225c`. These functions likely contain the logic for managing device state, committing changes, or handling timers that could lead to EEPROM persistence operations.

---

## 49. `fudally.sys` — `FUN_0001166c` (`0001166c`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 19.2s)*

1. **Role**: This function appears to allocate memory, initialize a structure, and call other functions to perform operations related to the radio's state, likely involving EEPROM or flash memory management.

2. **EEPROM / Persistence Mechanism**: The function allocates memory for a structure, initializes it, and then calls other functions (`FUN_00011a40` and `FUN_0001175c`) which are likely responsible for writing to or managing the radio's EEPROM or flash memory. It also updates a pointer to a memory block (`*(longlong *)(lVar1 + 0x68)`) and frees allocated memory, suggesting it manages state persistence indirectly through these calls.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x88`, `0x12`
   - Offsets: `0x40`, `0x18`, `0x42`, `0x1c`, `0x12`, `0x14`, `0x83`, `0x41`, `0x68`
   - Error HRESULT: `-0x3fffff66`
   - Callees: `ExAllocatePool`, `ExFreePool`, `FUN_00011a40`, `FUN_0001175c`

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_00011a40` and `FUN_0001175c`, as they are directly involved in the operations that manage the radio's state.

---

## 50. `fudally.sys` — `FUN_0001175c` (`0001175c`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 16.6s)*

1. **Role**: This function appears to allocate memory, prepare a data structure, and call another function (`FUN_00011a40`) to perform an operation on the radio. It then processes the result and possibly updates internal state.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by allocating memory, preparing a data structure, and calling another function (`FUN_00011a40`). It does not directly commit to EEPROM or flash; instead, it relies on the called function to handle the persistence mechanism.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x88`, `0xb`, `0x40`, `0x70`, `0x150`, `0x83`, `0x41`, `0x12`, `0x14`
   - Error HRESULT: `-0x3fffff66`
   - Callees: `ExAllocatePool`, `ExFreePool`, `FUN_00011a40`, `FUN_000118b8`

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_00011a40`, as it is directly involved in the operation on the radio and likely handles the actual persistence mechanism.

---

## 51. `fudally.sys` — `FUN_000118b8` (`000118b8`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 13.4s)*

1. **Role**: This function appears to parse USB configuration descriptors and allocate memory for USB configuration requests. It also handles memory allocation and copying for USB descriptors and endpoints.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that sets up USB configurations, which may be indirectly related to state persistence through USB communication.

3. **Key Constants / Opcodes / Calls**:
   - `ExAllocatePool`: Allocates memory.
   - `USBD_ParseConfigurationDescriptorEx`: Parses USB configuration descriptors.
   - `USBD_CreateConfigurationRequestEx`: Creates a USB configuration request.
   - `memcpy`: Copies memory.
   - Error code `-0x3fffff66` (likely `STATUS_INSUFFICIENT_RESOURCES`).

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_00011a40`, which is called after parsing and creating the USB configuration request. This function might handle more specific USB operations or interactions with the radio's storage.

---

## 52. `fudally.sys` — `FUN_00011a40` (`00011a40`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 20.4s)*

1. **Role**: This function appears to initiate a device I/O control request to interact with a device, possibly a radio, using a specific control code (`0x220003`). It sets up an event, builds an I/O request packet, and calls a driver to execute the request. If the request fails with a specific error code (`0x103`), it waits for the event to be signaled and retrieves the result.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to be a transport helper function that sends a control request to the device driver. The actual persistence mechanism, such as committing changes to EEPROM or handling locks/unlocks, is likely handled by the device driver or other functions called within the driver.

3. **Key Constants / Opcodes / Calls**:
   - Control code: `0x220003`
   - Event initialization: `KeInitializeEvent`
   - I/O request building: `IoBuildDeviceIoControlRequest`
   - Error code: `-0x3fffff66` (if `IoBuildDeviceIoControlRequest` fails)
   - Driver call: `IofCallDriver`
   - Event wait: `KeWaitForSingleObject`
   - Result retrieval: `local_38[0]`
   - Callee functions: `FUN_000125f4`, `FUN_0001266c`

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_000125f4` and `FUN_0001266c`. These functions might contain the actual logic for handling device-specific operations, including EEPROM persistence mechanisms.

---

## 53. `fudally.sys` — `FUN_00011b1c` (`00011b1c`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 16.9s)*

1. **Role**: This function appears to handle a specific operation on a device, possibly related to state management or communication, based on the parameters and internal logic.

2. **EEPROM / Persistence Mechanism**: The function involves setting up an event, copying data, modifying flags, and potentially calling another function (`FUN_0001225c`) to finalize the operation. It seems to involve locking mechanisms and possibly committing changes to EEPROM or flash, but the exact mechanism is not fully clear from the provided code snippet.

3. **Key Constants / Opcodes / Calls**:
   - `0x103` (HRESULT): Indicates a specific condition that triggers a wait operation.
   - `0x40`, `0x88`, `0x8c`, `0x90`, `0xa0`: Offsets used to access various fields in the structures pointed to by `param_1`.
   - `FUN_000125d0`: A function pointer set in the structure at an offset.
   - `FUN_0001225c`: A function called at the end to finalize the operation.

4. **Next Bite**: The next function to inspect for tracing EEPROM persistence is `FUN_0001225c`, as it is called at the end of the function and likely contains the final steps to commit changes to EEPROM or flash.

---

## 54. `fudally.sys` — `FUN_00011c20` (`00011c20`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 22.9s)*

1. **Role**: This function appears to manage state transitions and synchronization for a device, possibly a radio, by handling timers, locks, and invoking other functions to perform operations.

2. **EEPROM / Persistence Mechanism**: The function involves acquiring and releasing a spin lock, which suggests it manages concurrent access to shared resources. It also calls `FUN_000126fc` and `FUN_00011a40`, which likely handle specific operations related to state persistence, possibly involving EEPROM or flash writes. The function updates various fields in the `param_2` structure, indicating it may be involved in tracking the state or progress of these operations.

3. **Key Constants / Opcodes / Calls**:
   - `KeCancelTimer`, `KeWaitForSingleObject`, `KeAcquireSpinLockRaiseToDpc`, `KeReleaseSpinLock`, `ExAllocatePool`, `ExFreePool`, `IofCallDriver`
   - Offsets: `0x40`, `0x230`, `0x100`, `0x158`, `0x1d8`, `0x120`, `0x90`, `0x88`, `0x8c`, `0x38`, `0x43`, `0x30`, `0xb8`
   - HRESULT: `-0x3fffff66` (indicating an error condition)
   - Callees: `FUN_000130b0`, `FUN_000126fc`, `FUN_00011a40`

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_000126fc` and `FUN_00011a40`, as they are directly involved in the operations that likely handle the actual state persistence mechanisms.

---

## 55. `fudally.sys` — `FUN_00011d64` (`00011d64`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 16.1s)*

1. **Role**: This function appears to handle a specific operation on a device, possibly related to state management or communication, based on the initialization of an event, copying data, and making a driver call.

2. **EEPROM / Persistence Mechanism**: The function seems to involve setting up a driver call with specific parameters and handling the response. It includes operations that might affect the device's state, such as setting a marker (`0xe0`), but the direct impact on EEPROM persistence is unclear without further context.

3. **Key Constants / Opcodes / Calls**:
   - `0x103`: An HRESULT indicating a pending operation.
   - `0x40`, `0x88`, `0x8c`, `0x90`, `0xa0`: Offsets used to access various fields in the structures pointed to by `param_1`.
   - `FUN_000125d0`: A function pointer set in the structure at an offset.
   - `FUN_0001225c`: Another function called at the end of the operation.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_0001225c`, as it is called after the main operations and might contain the final steps or checks related to state persistence.

---

## 56. `fudally.sys` — `FUN_00011e68` (`00011e68`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 24.1s)*

1. **Role**: This function appears to manage the state of a device, possibly a radio, by handling various operations such as canceling timers, acquiring and releasing spinlocks, and setting device interface states. It also prepares and sends a request to a driver.

2. **EEPROM / Persistence Mechanism**: The function involves setting and modifying internal states that could affect the persistence of data on the radio. It sets a marker (`*(undefined4 *)(lVar2 + 0x8c) = uVar1`) and changes the state (`*(undefined4 *)(lVar2 + 0x88) = 5`). It also calls `FUN_0001225c` and `FUN_00012504`, which might involve further operations related to state persistence or device management.

3. **Key Constants / Opcodes / Calls**:
   - Offsets: `0x40`, `0x150`, `0x230`, `0x100`, `0x158`, `0x1d8`, `0x120`, `0x90`, `0x88`, `0x8c`, `0xa0`, `0x18`, `0x30`, `0x38`, `0x43`, `0xb8`
   - Calls: `FUN_000130b0`, `KeCancelTimer`, `KeWaitForSingleObject`, `KeAcquireSpinLockRaiseToDpc`, `KeReleaseSpinLock`, `FUN_0001225c`, `IoSetDeviceInterfaceState`, `FUN_00012504`, `IofCallDriver`

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_0001225c` and `FUN_00012504`, as they are directly involved in operations that could affect the device's state and persistence.

---

## 57. `fudally.sys` — `FUN_00011f88` (`00011f88`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 28.5s)*

1. **Role**: This function appears to handle the finalization and cleanup of a device interface, transitioning its state and ensuring proper resource release. It involves setting device states, canceling timers, and detaching/deleting the device.

2. **EEPROM / Persistence Mechanism**: The function sets a state marker (`*(undefined4 *)(lVar1 + 0x88) = 6`) and calls `FUN_0001266c` twice, which likely involves committing changes to EEPROM or flash. It also increments a counter (`*(char *)(param_2 + 0x43) = *(char *)(param_2 + 0x43) + '\x01'`) and adjusts a pointer (`*(longlong *)(param_2 + 0xb8) = *(longlong *)(param_2 + 0xb8) + 0x48`). These actions suggest a mechanism for tracking and ensuring state persistence.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x40`, `0x88`, `0x90`, `0xa0`, `0x150`, `0x230`, `0x100`, `0x158`, `0x1d8`, `0x120`, `0x18`, `0x8c`, `0x88`, `0xc0`, `0x30`, `0x38`, `0x43`, `0xb8`
   - Callees: `KeAcquireSpinLockRaiseToDpc`, `KeReleaseSpinLock`, `FUN_000130b0`, `KeCancelTimer`, `KeWaitForSingleObject`, `FUN_0001225c`, `IoSetDeviceInterfaceState`, `FUN_00012504`, `FUN_0001266c`, `FUN_000126fc`, `IofCallDriver`, `IoDetachDevice`, `IoDeleteDevice`

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_0001266c` and `IofCallDriver`. These functions are directly involved in setting the device state and making driver calls, respectively, which are critical for ensuring state persistence.

---

## 58. `fudally.sys` — `FUN_0001211c` (`0001211c`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 17.7s)*

1. **Role**: This function appears to handle a specific operation on a device, possibly related to configuration or state management. It initializes an event, copies data, and calls another driver function to perform the operation.

2. **EEPROM / Persistence Mechanism**: The function sets a flag in the `_Src` structure to indicate a change (0x200), initializes an event, and copies data. It then calls another driver function (`FUN_000125d0`) to perform the operation. If the operation is successful, it updates the device's state and ensures certain conditions are met before returning. The function does not directly commit to EEPROM or flash; instead, it relies on the driver function to handle the persistence.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: 0x40, 0x200, 0x30, 0x138, 0xe0
   - Offsets: 0x40, 0xb8, 0x30, 0x138
   - Error HRESULT: 0x103
   - Callee: `FUN_000125d0`

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_000125d0`. This function is likely responsible for the actual operation on the device, including any necessary EEPROM or flash commits.

---

## 59. `fudally.sys` — `FUN_0001225c` (`0001225c`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 18.9s)*

1. **Role**: This function appears to manage a linked list of operations or tasks, likely related to device communication or state management. It handles acquiring and releasing a spinlock, iterating through a list of tasks, and completing or requeuing tasks based on certain conditions.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to manage tasks that may involve communication with the device, possibly including operations that could lead to state persistence. It checks for conditions that might trigger further actions related to device state, such as error handling or task completion.

3. **Key Constants / Opcodes / Calls**:
   - `0xb8`: Offset for acquiring and releasing a spinlock.
   - `0xa8`: Offset for accessing a list of tasks.
   - `0xa0`: Offset for checking a state value.
   - `0xc0000056`: HRESULT for an error condition.
   - `0xc0000120`: Another HRESULT for a different error condition.
   - `FUN_000125f4` and `FUN_0001266c`: Callees that might handle specific task processing or completion.

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_000125f4` and `FUN_0001266c`. These functions likely contain more detailed logic for handling specific tasks, which could include operations related to device communication or state persistence.

---

## 60. `fudally.sys` — `FUN_000123d0` (`000123d0`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 17.1s)*

1. **Role**: This function appears to manage a linked list of structures, possibly related to pending operations or tasks, and handles their completion and cleanup. It involves acquiring and releasing a spinlock, modifying pointers within the structures, and completing I/O requests.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that manages the state of operations, possibly preparing them for execution or marking them as completed. It does not explicitly handle commit, lock/unlock, or reset operations on the radio's EEPROM/flash.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0xc0000120` (HRESULT indicating an error)
   - Offsets: `0x40`, `0xb8`, `0x30`, `0x38`
   - Callees: `FUN_000125f4`, `FUN_0001266c`, `KeAcquireSpinLockRaiseToDpc`, `KeReleaseSpinLock`, `IofCompleteRequest`

4. **Next Bite**: The callees `FUN_000125f4` and `FUN_0001266c` should be inspected next to trace any potential interactions with EEPROM persistence or other critical operations.

---

## 61. `fudally.sys` — `FUN_00012504` (`00012504`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 15.1s)*

1. **Role**: This function iterates over a list of entries, allocating memory for each, and processes them using another function (`FUN_00011a40`). It checks for null-terminated strings and modifies them upon successful processing.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by processing entries that likely involve EEPROM operations. It allocates memory, processes entries, and potentially modifies strings, which could be markers or indicators of state changes. However, direct EEPROM commit or lock/unlock operations are not explicitly shown.

3. **Key Constants / Opcodes / Calls**:
   - `0x28`: Memory allocation size.
   - `0xc000009a`: Error HRESULT for memory allocation failure.
   - `0x10`, `0x20`, `0x78`, `0x80`: Offsets used to access data structures.
   - `FUN_00011a40`: Callee function used to process each entry.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_00011a40`, as it directly processes the entries and could contain the logic for committing changes to EEPROM or handling lock/unlock operations.

---

## 62. `fudally.sys` — `FUN_000125f4` (`000125f4`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 14.7s)*

1. **Role**: This function increments a counter stored at an offset within the provided parameter structure. It also manages a spin lock to ensure thread safety during the increment operation and clears an event if the counter reaches a specific value (2 in this case).

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It appears to be a helper function for managing state transitions or synchronization, possibly related to the commit process or state persistence mechanisms, but it does not perform any direct EEPROM operations.

3. **Key Constants / Opcodes / Calls**:
   - `0xf8`: Offset for acquiring and releasing a spin lock.
   - `0xf0`: Offset for the counter variable.
   - `0xd8`: Offset for an event that is cleared when the counter reaches 2.
   - `KeAcquireSpinLockRaiseToDpc`, `KeClearEvent`, `KeReleaseSpinLock`: Kernel-mode functions for lock management and event handling.

4. **Next Bite**: Since the function does not directly interact with EEPROM, the next step should be to inspect the callers of `FUN_000125f4` to understand its role in the broader context of state persistence. Look for functions that call this one and check if they involve EEPROM operations or state commit processes.

---

## 63. `fudally.sys` — `FUN_0001266c` (`0001266c`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 14.1s)*

1. **Role**: This function appears to manage a reference count and set events based on the count reaching zero or one. It involves acquiring and releasing a spinlock, decrementing a reference count, and signaling events when the count reaches specific values.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that manages synchronization and event signaling, which could be part of a larger mechanism for ensuring state persistence on the radio.

3. **Key Constants / Opcodes / Calls**:
   - `KeAcquireSpinLockRaiseToDpc` and `KeReleaseSpinLock` are used for spinlock management.
   - `LOCK()` and `UNLOCK()` are macros or inline functions for locking and unlocking.
   - `KeSetEvent` is called with offsets `0xd8` and `0xc0` to set events when the reference count reaches 1 or 0, respectively.

4. **Next Bite**: Since the function does not directly interact with EEPROM, the next step should be to inspect the callees or the context in which this function is used, particularly focusing on any functions that might involve direct interaction with EEPROM or flash storage.

---

## 64. `fudally.sys` — `FUN_000126fc` (`000126fc`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 12.8s)*

1. **Role**: This function appears to be responsible for cleaning up allocated memory by calling `ExFreePool` on several pointers stored in a structure referenced by `param_1`. It sets these pointers to zero after freeing them.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the EEPROM or flash storage. It is more likely a transport helper function that ensures memory is properly cleaned up, which could be part of a larger process that affects state persistence.

3. **Key Constants / Opcodes / Calls**: 
   - Offsets: `0x40`, `0x68`, `0x70`, `0x78`, `0x80`
   - Function Call: `ExFreePool`

4. **Next Bite**: Since this function is primarily concerned with memory management, the next step would be to trace the calls to this function to understand its context within the larger system. Look for where `FUN_000126fc` is called and what operations precede and follow it, especially those related to EEPROM or state persistence.

---

## 65. `fudally.sys` — `FUN_0001276c` (`0001276c`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 28.9s)*

1. **Role**: This function appears to handle different states and operations related to device power management and possibly data processing, based on the conditions and calls within it.

2. **EEPROM / Persistence Mechanism**: The function manipulates certain flags and structures that could be related to state persistence, such as setting bits in a byte array and copying data. It also calls other functions (`FUN_000125f4`, `FUN_0001266c`, `FUN_00012c84`, `FUN_0001296c`, `FUN_00012a3c`) which likely handle specific operations related to EEPROM persistence or state management.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x88`, `0x40`, `0xb8`, `0x38`, `0x43`, `0x10`, `0xe0`, `0x103`, `0xc0000056`
   - Offsets: `param_1 + 0x40`, `param_2 + 0xb8`, `param_2 + 0x38`, `param_2 + 0x30`, `lVar4 + 1`, `lVar4 + 0x10`
   - Error HRESULTs: `0xc0000056`
   - Callees: `PoStartNextPowerIrp`, `IofCompleteRequest`, `PoCallDriver`, `FUN_000125f4`, `FUN_0001266c`, `FUN_00013114`, `FUN_00012afc`, `FUN_00012c84`, `FUN_0001296c`, `FUN_00012a3c`

4. **Next Bite**: The callees `FUN_00012c84`, `FUN_0001296c`, and `FUN_00012a3c` should be inspected next to trace EEPROM persistence, as they are conditionally called based on the state of the device and the data being processed.

---

## 66. `fudally.sys` — `FUN_0001296c` (`0001296c`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 17.8s)*

1. **Role**: This function appears to handle a request to write data to a device, possibly a radio, by copying data from one buffer to another, setting up a completion routine, and calling a driver function to process the request.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it sets up a completion routine (`FUN_00012afc`) and calls a driver function (`PoCallDriver`) to handle the actual data processing. The function also checks conditions related to the device's state and handles errors by completing the request with an error code.

3. **Key Constants / Opcodes / Calls**:
   - `0x103`: Return value indicating success.
   - `0xc0000184`: Error HRESULT indicating an invalid parameter.
   - `FUN_00013040`: A function called if certain conditions are met.
   - `FUN_00012afc`: A function pointer set in the completion routine.
   - `PoCallDriver`: A function to call the driver.
   - `PoStartNextPowerIrp`: A function to start the next power IRP.
   - `IofCompleteRequest`: A function to complete the request.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_00012afc`, as it is set as the completion routine and may handle the actual data processing and persistence operations.

---

## 67. `fudally.sys` — `FUN_00012a3c` (`00012a3c`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 15.8s)*

1. **Role**: This function appears to handle power management and state transitions for a device, possibly a radio. It checks conditions, calls another function to perform operations, and manages power IRPs (Interrupt Request Packets).

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by managing power transitions and possibly invoking operations that could lead to EEPROM commits or state persistence. It does not directly perform EEPROM operations but is likely involved in the process.

3. **Key Constants / Opcodes / Calls**:
   - `0x103`: An error code returned by `FUN_00012ed4`.
   - `0xc0000184`: An HRESULT indicating an error condition.
   - `PoStartNextPowerIrp`: A function call to start the next power IRP.
   - `PoCallDriver`: A function call to call the driver.
   - `IofCompleteRequest`: A function call to complete the I/O request.
   - `FUN_0001266c`: A function call at the end of the function.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_00012ed4`, as it is called with parameters that could involve EEPROM operations and returns a value that affects the function's outcome.

---

## 68. `fudally.sys` — `FUN_00012afc` (`00012afc`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 14.7s)*

1. **Role**: This function appears to handle power state transitions and possibly state persistence on the radio. It checks a condition related to power state and either starts a power IRP or processes some data based on a specific condition.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. It seems to be more of a transport helper, possibly managing power states or session transitions that could indirectly affect state persistence.

3. **Key Constants / Opcodes / Calls**:
   - `PoStartNextPowerIrp`: A function call related to power management.
   - `FUN_0001266c`: A function call, possibly related to handling power state changes.
   - `FUN_00012b50`: A function call, possibly related to processing data or state transitions.
   - `0xc0000016`: An error HRESULT, possibly indicating a failure or specific condition.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_0001266c` and `FUN_00012b50`. These functions might contain more detailed logic related to state persistence or power management that could affect the radio's permanent state.

---

## 69. `fudally.sys` — `FUN_00012b50` (`00012b50`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 19.2s)*

1. **Role**: This function appears to handle power management and state persistence for a device, possibly a radio. It allocates a pool, requests a power IRP, and manages the completion of the request.

2. **EEPROM / Persistence Mechanism**: The function indirectly supports state persistence by managing power IRPs, which are crucial for ensuring that any changes made to the device's state are properly committed before the device enters a low-power state. This is essential for maintaining the integrity of the device's EEPROM or flash memory.

3. **Key Constants / Opcodes / Calls**:
   - `0x38` and `0x40` are offsets used to access specific fields in the structures pointed to by `param_1` and `param_2`.
   - `ExAllocatePool` and `ExFreePool` are used for memory management.
   - `PoRequestPowerIrp` is called with a specific power state and a completion routine (`FUN_00012c1c`).
   - `PoStartNextPowerIrp` and `IofCompleteRequest` are used to manage the power IRP queue and request completion.
   - `FUN_0001266c` is called at the end, possibly for cleanup or further processing.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_00012c1c`, which is the completion routine passed to `PoRequestPowerIrp`. This function likely handles the actual completion of the power IRP and may contain further details on how the device's state is committed or locked.

---

## 70. `fudally.sys` — `FUN_00012c1c` (`00012c1c`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 16.5s)*

1. **Role**: This function appears to handle the completion of a power-related IRP (I/O Request Packet) and possibly updates some internal state or markers related to the radio's operation.

2. **EEPROM / Persistence Mechanism**: The function sets a marker at `lVar1 + 0x30` and then calls `PoStartNextPowerIrp` and `IofCompleteRequest`, which suggests it might be involved in managing power states or ensuring that certain operations are completed before the system transitions to a new power state. It also calls `FUN_0001266c` and `ExFreePool`, which could be related to freeing resources or committing changes to persistent storage like EEPROM or flash.

3. **Key Constants / Opcodes / Calls**: 
   - `PoStartNextPowerIrp` and `IofCompleteRequest` are called, indicating power management and IRP handling.
   - `FUN_0001266c` is called with `lVar2` as an argument, which might be related to further processing or committing changes.
   - `ExFreePool` is called, which is used for freeing memory allocated from non-paged pool.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_0001266c`, as it is called with a parameter that might be related to committing changes or managing persistent storage.

---

## 71. `fudally.sys` — `FUN_00012c84` (`00012c84`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 22.6s)*

1. **Role**: This function appears to handle the copying and processing of data from a source buffer to a destination buffer, with conditional logic based on the size of the data and the current state of the device. It also sets up a callback function and initiates a driver call.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to prepare data for processing and sets up a callback to handle further operations, which could include committing changes to persistent storage. The function involves locking mechanisms and conditional logic that might be related to ensuring data integrity before committing to EEPROM.

3. **Key Constants / Opcodes / Calls**:
   - **Hex Constants**: `0x40`, `0xb8`, `0x18`, `0x9c`, `0x90`, `0xa0`, `-0x48`, `0x38`, `-0x10`, `-8`, `-0x45`
   - **Error HRESULTs**: `0x103` (likely a success code)
   - **Callees**: `memcpy`, `FUN_00012da0`, `FUN_00012ed4`, `PoStartNextPowerIrp`, `IofCompleteRequest`, `FUN_0001266c`, `KeAcquireSpinLockRaiseToDpc`, `KeReleaseSpinLock`, `FUN_0001225c`, `PoCallDriver`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_00012ed4` and `FUN_00012da0`, as they are conditionally called based on the size of the data and the current state of the device. These functions might contain the actual logic for committing changes to EEPROM or handling the persistence of state.

---

## 72. `fudally.sys` — `FUN_00012da0` (`00012da0`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 17.9s)*

1. **Role**: This function appears to handle power state transitions for a device, possibly a radio. It checks the current power state, updates it, and manages spinlocks and power IRPs. It also calls other functions to complete requests and manage power states.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to manage power states, which could indirectly affect state persistence by ensuring the device is in the correct state for operations that might involve EEPROM writes. There is no explicit call to commit or flush EEPROM data.

3. **Key Constants / Opcodes / Calls**:
   - `0xc0000016`: An error HRESULT.
   - `PoStartNextPowerIrp`: A function call related to power IRPs.
   - `PoSetPowerState`: A function call to set the power state.
   - `KeAcquireSpinLockRaiseToDpc` and `KeReleaseSpinLock`: Functions for managing spinlocks.
   - `FUN_0001225c` and `FUN_0001266c`: Other function calls within the code.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_0001225c` and `FUN_0001266c`. These functions might contain the logic for committing or flushing EEPROM data, or they could be involved in managing the device's state in a way that affects persistence.

---

## 73. `fudally.sys` — `FUN_00012e74` (`00012e74`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 13.3s)*

1. **Role**: This function appears to handle power state transitions and possibly updates to the radio's state. It checks conditions related to the power state and a specific byte in memory, then sets a power state and starts the next power IRP.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the radio's state by setting a power state, which could trigger EEPROM/flash commit or other persistence mechanisms. It does not directly manipulate EEPROM or flash but is likely part of the broader process that ensures state persistence.

3. **Key Constants / Opcodes / Calls**:
   - `PoSetPowerState(param_1, 1)`: Sets the power state.
   - `PoStartNextPowerIrp(param_2)`: Starts the next power IRP.
   - `FUN_0001266c(param_3)`: Calls another function, possibly related to further processing.

4. **Next Bite**: The next function to inspect for tracing EEPROM persistence is `FUN_0001266c`, as it is called after setting the power state and starting the next power IRP, and it may contain further details on how the state is made permanent.

---

## 74. `fudally.sys` — `FUN_00012ed4` (`00012ed4`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 14.2s)*

1. **Role**: This function appears to allocate resources and queue a work item for execution, likely to perform some operation on the radio's state or data.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the radio's permanent state by allocating a work item and setting a flag in the radio's memory. It does not directly commit to EEPROM or flash; instead, it prepares the environment for a subsequent operation that may involve state persistence.

3. **Key Constants / Opcodes / Calls**:
   - `0x103`: Return value indicating success.
   - `0xc000009a`: Return value indicating failure.
   - `ExAllocatePool`: Allocates memory pool.
   - `IoAllocateWorkItem`: Allocates a work item.
   - `IoQueueWorkItem`: Queues a work item for execution.
   - `FUN_00012f74`: The function called by the work item.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_00012f74`, as it is responsible for executing the queued work item and likely contains the logic for the actual operation that affects the radio's permanent state.

---

## 75. `fudally.sys` — `FUN_00012f74` (`00012f74`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 16.0s)*

1. **Role**: This function appears to handle some form of state management or operation on a device, possibly related to communication or configuration. It involves waiting for an object, copying data, and making a driver call.

2. **EEPROM / Persistence Mechanism**: The function does not directly show explicit EEPROM commit or lock/unlock operations. It seems to be more of a transport helper function, possibly preparing data for a driver call that could involve EEPROM operations.

3. **Key Constants / Opcodes / Calls**:
   - `FUN_0001266c`: Called twice, possibly for initialization or cleanup.
   - `KeWaitForSingleObject`: Waits for an object with a timeout.
   - `FUN_000125f4`: Called twice, possibly for setting up or tearing down some state.
   - `memcpy`: Copies data from one location to another.
   - `PoCallDriver`: Makes a call to a driver, which could involve EEPROM operations.
   - `IoFreeWorkItem`: Frees a work item.
   - `ExFreePool`: Frees a memory pool.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `PoCallDriver`, as it is the function that directly interacts with the driver, which could involve committing changes to EEPROM or handling other persistent state operations.

---

## 76. `fudally.sys` — `FUN_00013040` (`00013040`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 18.1s)*

1. **Role**: This function appears to manage a state transition or power request for a device, possibly related to committing changes to EEPROM or ensuring state persistence. It locks a resource, checks a condition, and either requests a power IRP or sets an error code.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects permanent state on the radio by potentially requesting a power IRP, which could trigger a commit operation to EEPROM or flash. It also uses locking mechanisms to ensure thread safety during state changes.

3. **Key Constants / Opcodes / Calls**:
   - `0x14c`: Offset where the state is checked and modified.
   - `0x148`: Offset where a flag is set to `0`.
   - `0x10`: Offset for a device handle or context.
   - `0x54`: Offset for a power state or type.
   - `0x80000011`: Error HRESULT returned if the initial condition (`iVar1`) is not `0`.
   - `PoRequestPowerIrp`: Function called to request a power IRP.
   - `FUN_00013170`: Callback function passed to `PoRequestPowerIrp`.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `PoRequestPowerIrp` and its callback `FUN_00013170`. These functions are likely responsible for handling the power request and any subsequent operations that might involve committing changes to EEPROM or flash.

---

## 77. `fudally.sys` — `FUN_000130b0` (`000130b0`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 16.7s)*

1. **Role**: This function appears to handle the cancellation of an I/O request and possibly updates the state of a power management IRP. It checks if a specific I/O request is pending, cancels it, and then conditionally starts the next power IRP if a certain condition is met.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be more of a transport helper function that manages I/O request states and power IRPs, which could be indirectly related to ensuring state persistence by managing when operations are completed or canceled.

3. **Key Constants / Opcodes / Calls**:
   - `0x140` and `0x148`: Offsets used to access fields in the `param_1` structure.
   - `0xc0000120`: An HRESULT value, possibly indicating an error or status code.
   - `IoCancelIrp`: Function to cancel an I/O request.
   - `PoStartNextPowerIrp`: Function to start the next power IRP.
   - `IofCompleteRequest`: Function to complete an I/O request.

4. **Next Bite**: The next callees to inspect for EEPROM persistence would be `IoCancelIrp`, `PoStartNextPowerIrp`, and `IofCompleteRequest`, as they are directly involved in managing I/O and power states, which could be related to ensuring state persistence on the radio.

---

## 78. `fudally.sys` — `FUN_00013114` (`00013114`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 16.1s)*

1. **Role**: This function appears to manage a state transition or operation on a device, possibly related to power management or initialization, based on the presence of a marker and the handling of a lock mechanism.

2. **EEPROM / Persistence Mechanism**: The function modifies a marker in memory (`*pbVar1 = *pbVar1 | 1;`) and interacts with a lock mechanism (`LOCK()` and `UNLOCK()`). It also checks and sets a state flag (`*(int *)(param_3 + 0x148) = 1;`) and calls `PoStartNextPowerIrp(param_2);`, which suggests it might be involved in power state transitions that could affect persistent storage.

3. **Key Constants / Opcodes / Calls**:
   - `0x41` and `0xb8` offsets in `param_2`.
   - `0x140` and `0x148` offsets in `param_3`.
   - `0xc0000016` and `0xc0000120` HRESULTs.
   - `PoStartNextPowerIrp` function call.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `PoStartNextPowerIrp(param_2);`, as it is likely involved in power state transitions that could affect how data is committed to persistent storage.

---

## 79. `fudally.sys` — `FUN_00013170` (`00013170`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 16.2s)*

1. **Role**: This function appears to manage a state transition or power request for a device, possibly related to committing changes to EEPROM or ensuring device stability before proceeding with operations.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by potentially committing changes to EEPROM or ensuring the device is in a stable state before proceeding. It involves locking and unlocking mechanisms, which are crucial for ensuring data integrity during state transitions.

3. **Key Constants / Opcodes / Calls**:
   - `LOCK()` and `UNLOCK()`: These functions are called to manage a critical section, ensuring that the operations within are thread-safe.
   - `PoRequestPowerIrp`: This function is called to request a power IRP, which could be related to putting the device into a low-power state or ensuring it is fully awake before proceeding.
   - `FUN_000125f4`: This function is called to perform some operation related to the device's state or configuration.
   - `FUN_00013040`: This function is called if a specific condition is met, possibly to handle an error or perform a recovery operation.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_000125f4`, as it is called before the power request and might contain operations related to committing changes to EEPROM or ensuring device stability.

---

## 80. `fudally.sys` — `FUN_000131e0` (`000131e0`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 24.2s)*

1. **Role**: This function appears to handle some form of state management or operation on a device, possibly related to EEPROM or flash memory, based on the presence of locking mechanisms and state counters.

2. **EEPROM / Persistence Mechanism**: The function involves locking and unlocking operations, incrementing a state counter, and potentially writing to EEPROM or flash memory. It checks conditions and updates markers or pointers related to the device's state, which could indicate a commit or persistence operation.

3. **Key Constants / Opcodes / Calls**:
   - `0xc000000d`: An HRESULT indicating an error or failure.
   - `0xc0000184`: Another HRESULT indicating a different error or failure.
   - `0x154`: An offset where a state counter is incremented.
   - `0x100`: An offset checked for a non-zero value to determine if a function (`FUN_000137b8`) should be called.
   - `0x80`: An offset used in pointer arithmetic.
   - `0x58`: An offset used to check a condition.
   - `0x30`: An offset used to access a pointer.
   - `0xb8`: An offset used to access a pointer.
   - `0x40`: An offset used to access a pointer.
   - `0x78`: An offset used to access a pointer.
   - `0x10`: An offset used to access a value in a loop.
   - `FUN_000137b8`: A function called if a specific condition is met.
   - `FUN_0001385c`: A function called to get a pointer or value.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_000137b8`, as it is conditionally called when a specific state is met, potentially indicating a critical operation related to state persistence or commit.

---

## 81. `fudally.sys` — `FUN_00013308` (`00013308`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 17.6s)*

1. **Role**: This function appears to handle the completion of a request, potentially related to a device operation, and updates internal state counters. It also locks and unlocks a resource, likely to ensure thread safety during the operation.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a transport helper function that manages request completion and resource locking. It does not explicitly commit changes to EEPROM or flash; however, it might be part of a larger sequence that ensures state persistence.

3. **Key Constants / Opcodes / Calls**:
   - `0x40` and `0xb8` are offsets used to access specific fields in the input parameters.
   - `0x18` and `0x58` are offsets used to access fields in a structure pointed to by `lVar3`.
   - `FUN_0001385c` is a function called with parameters `param_1` and a pointer to a `ushort` array.
   - `IofCompleteRequest` is a function call to complete a request.
   - `LOCK()` and `UNLOCK()` are macros or functions used to manage resource locking.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_0001385c`, as it is called with parameters that might be related to the operation's data or context. Understanding what this function does could provide insights into how the device's state is managed and persisted.

---

## 82. `fudally.sys` — `FUN_0001337c` (`0001337c`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 22.2s)*

1. **Role**: This function appears to handle different operations based on the opcode provided, potentially involving data transfer, state management, and error handling for a device interaction.

2. **EEPROM / Persistence Mechanism**: The function interacts with the device's EEPROM or flash memory by copying data to or from a destination buffer. It also manages locks and unlocks, and handles specific opcodes that might involve committing changes to the device's permanent state.

3. **Key Constants / Opcodes / Calls**:
   - Opcodes: `0x220000`, `0x220004`, `0x220008`, `0x22000c`, `0x220010`, `0x220014`
   - Error HRESULTs: `0xc0000184`, `-0x3fffffdd`, `-0x3ffffff3`, `-0x3ffffff0`, `-0x3fffffff`
   - Callees: `FUN_000125f4`, `FUN_00013644`, `FUN_000135c0`, `FUN_00011a40`, `FUN_0001266c`, `FUN_00013cd0`

4. **Next Bite**: The callees `FUN_00013644`, `FUN_000135c0`, and `FUN_00011a40` should be inspected next to trace EEPROM persistence, as they are directly involved in handling specific operations that might affect the device's permanent state.

---

## 83. `fudally.sys` — `FUN_000135c0` (`000135c0`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 13.4s)*

1. **Role**: This function allocates a memory buffer, initializes it with specific values, and then calls another function (`FUN_00011a40`) with the buffer and a parameter. It checks the result of the called function and returns 0 if successful, or an error code otherwise.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by allocating and initializing a buffer that is passed to another function. The actual mechanism of how this affects EEPROM persistence is unclear from this function alone and requires further analysis of the called function.

3. **Key Constants / Opcodes / Calls**:
   - Memory allocation size: `0x28` bytes
   - Buffer initialization values: `0x28`, `0x1e`
   - Error HRESULT: `-0x3fffff66`
   - Callee function: `FUN_00011a40`

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_00011a40`, as it is directly involved in the process of making state permanent on the radio.

---

## 84. `fudally.sys` — `FUN_00013644` (`00013644`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 17.4s)*

1. **Role**: This function appears to handle device I/O control requests, specifically for operations related to device state management and possibly committing changes to persistent storage.

2. **EEPROM / Persistence Mechanism**: The function involves building and sending device I/O control requests with specific opcodes (0x220013 and 0x220007). It initializes events, calls drivers, and waits for responses. The presence of `KeWaitForSingleObject` suggests it waits for asynchronous operations to complete, which could be related to committing changes to EEPROM or flash. The function checks flags in `local_res8` to determine the success of operations and whether to proceed with further actions.

3. **Key Constants / Opcodes / Calls**:
   - **Opcodes**: 0x220013, 0x220007
   - **Offsets**: 0x40, 0xb8
   - **Error HRESULTs**: 0xc000009a (STATUS_NOT_SUPPORTED)
   - **Callees**: `IoBuildDeviceIoControlRequest`, `IofCallDriver`, `KeInitializeEvent`, `KeWaitForSingleObject`

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `IoBuildDeviceIoControlRequest` and `IofCallDriver`, as they are responsible for building and sending the I/O control requests that likely interact with the device's persistent storage.

---

## 85. `fudally.sys` — `FUN_000137b8` (`000137b8`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 17.8s)*

1. **Role**: This function appears to handle the cancellation of an I/O request and the management of a counter associated with that request. It also checks certain conditions and sets an event if the counter reaches zero.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the EEPROM or flash storage. It seems to be a transport helper function that manages I/O request cancellation and resource cleanup, which could be part of a larger process that ensures state persistence.

3. **Key Constants / Opcodes / Calls**:
   - `KeAcquireSpinLockRaiseToDpc` and `KeReleaseSpinLock` are used for synchronization.
   - `IoCancelIrp` is called to cancel an I/O request.
   - `IoFreeIrp` is called to free the I/O request packet.
   - `KeSetEvent` is used to signal an event.
   - Offsets used: `0x118`, `0x154`, `0xf0`, `0x108`, `0x114`, `0x120`.

4. **Next Bite**: The next callees to inspect for EEPROM persistence would be `IoCancelIrp` and `IoFreeIrp`, as they are directly involved in I/O request management. Additionally, any functions that interact with the spinlock or event handling (`KeAcquireSpinLockRaiseToDpc`, `KeReleaseSpinLock`, `KeSetEvent`) should be examined to understand their role in the overall state management process.

---

## 86. `fudally.sys` — `FUN_0001385c` (`0001385c`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 15.5s)*

1. **Role**: This function appears to parse a string input to extract a numeric value, possibly related to a configuration or state identifier. It then uses this value to calculate an offset and checks if the result is within a valid range (0-5).

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be a helper function that processes input data and calculates an offset, which could be used by other functions to manage state persistence. It does not perform any direct commit, lock, unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x2f`, `0x3a`, `0x30`, `0x39`
   - Offsets: `param_2 + 4`, `param_1 + 0x40`, `0x80`
   - Error HRESULTs: None observed
   - Callees: None directly called within the function

4. **Next Bite**: The next step should be to inspect the callees or functions that use this function, particularly those that might interact with EEPROM or manage state persistence. Look for functions that use the calculated offset (`lVar6`) to read from or write to memory, or that call other functions related to EEPROM operations.

---

## 87. `fudally.sys` — `FUN_00013928` (`00013928`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 33.1s)*

1. **Role**: This function appears to handle data transfer operations, possibly involving memory allocation, buffer management, and driver interaction, likely for communication with a radio device.

2. **EEPROM / Persistence Mechanism**: The function indirectly supports EEPROM persistence by managing memory descriptors (`IoAllocateMdl`), preparing data buffers, and interacting with a driver (`IofCallDriver`). It sets up structures that are likely used by the driver to perform operations on the radio's EEPROM, though it does not directly commit or flush the EEPROM.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x801`, `0x400`, `0x220003`, `0xf`, `0xe0`, `0x80`, `0x103`, `0xc0000184`, `0xc0000008`, `0xc000009a`, `0xc000000d`.
   - Offsets: `0xb8`, `0x40`, `0x30`, `0x88`, `0x100`, `0x120`, `0x28`, `0x2c`, `0x20`, `0x18`, `0x8`, `0x14`, `0x1c`, `0x12`, `0x10`, `0x14`, `0x38`, `0x30`.
   - Error HRESULTs: `0xc0000184`, `0xc0000008`, `0xc000009a`, `0xc000000d`.
   - Callees: `ExAllocatePool`, `IoAllocateMdl`, `IoBuildPartialMdl`, `ExFreePool`, `IoFreeMdl`, `FUN_00013bb4`, `FUN_000125f4`, `IofCallDriver`, `FUN_000135c0`, `FUN_00013644`, `IofCompleteRequest`.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_00013bb4`, as it is set as a callback function (`*(code **)(lVar11 + -0x10) = FUN_00013bb4;`) and may handle the actual interaction with the radio's EEPROM.

---

## 88. `fudally.sys` — `FUN_00013bb4` (`00013bb4`)
- **Keywords:** non-trivial

*(qwen2.5-coder:14b, 17.1s)*

1. **Role**: This function appears to handle data processing and possibly I/O operations, including building partial MDLs (Memory Descriptor Lists) and calling another driver function. It manages memory allocation and deallocation, and seems to interact with a device driver context.

2. **EEPROM / Persistence Mechanism**: The function indirectly supports EEPROM persistence by managing data transfer and possibly signaling a driver to perform a commit operation. It sets up a partial MDL and calls another function (`FUN_00013bb4`) with a modified context, which likely involves writing data to the device. The function also handles cleanup and error management.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x400`, `0xf`, `0x220003`, `0xe0`, `-0x3fffffea`
   - Offsets: `0x30`, `0x8`, `0xb8`, `0x14`, `0x24`
   - Callees: `IoBuildPartialMdl`, `IofCallDriver`, `FUN_0001266c`, `ExFreePool`, `IoFreeMdl`

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_00013bb4`, as it is called with a modified context that likely involves the actual data transfer and commit operation.

---

## 89. `fudally.sys` — `memcpy` (`00013d30`)
- **Keywords:** exported-or-named

*(qwen2.5-coder:14b, 18.8s)*

1. **Role**: The function `memcpy` is a standard library function used to copy a block of memory from a source location to a destination location. It handles different memory alignment and sizes efficiently.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly handle EEPROM persistence or state commitment on the radio. It is a transport helper function used to move data around in memory, which could be part of a larger process that involves EEPROM operations.

3. **Key Constants / Opcodes / Calls**: 
   - The function does not contain any specific opcodes or constants related to EEPROM operations.
   - It includes calls to `LOCK()` and `UNLOCK()`, which might be related to synchronization or critical section management but are not directly tied to EEPROM persistence.

4. **Next Bite**: Since `memcpy` is a standard library function, the next step should be to trace the calls to this function within the context of the larger application. Look for higher-level functions or modules that use `memcpy` to transfer data to or from EEPROM partitions (0x80, 0x81, 0x82). Focus on functions that handle operations like `ReadIsh`, `WriteIsh`, or `Prepare Write`, as these are more likely to involve direct EEPROM access.

---
