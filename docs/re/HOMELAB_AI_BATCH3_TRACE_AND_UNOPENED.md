# Homelab AI Function-by-Function Analysis: ASTRO 25 EEPROM & State Persistence

- **Model:** `qwen2.5-coder:14b` (`num_ctx=8192` on TrueNAS RTX 3080)
- **Scope:** Undocumented functions in `NextGen10.dll` and `ByteData10.dll` related to EEPROM, host markers, commit/lock, and state persistence.
- **Total functions analyzed:** 56

---

## 1. `NextGen10.dll` — `FUN_100067c5` (`100067c5`)
- **Keywords:** callee-follow-up

*(qwen2.5-coder:14b, 10.5s)*

1. **Role**: This function retrieves a value from a specific offset within the memory pointed to by `param_1`. It appears to be a simple data access function.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function itself does not directly interact with EEPROM or handle state persistence. It seems to be a utility function that accesses data structures.

3. **Key Constants / Opcodes / Calls**: The function accesses data at offset `0x110` from the pointer `param_1`. There are no specific hex constants, opcodes, error HRESULTs, or callees directly visible in the provided code snippet.

4. **Next Bite**: Since the function is a simple data access function, the next step should be to trace where `param_1` comes from and how it is used in the broader context. Look for calls to this function and inspect the values passed to `param_1` to understand its role in the EEPROM persistence mechanism.

---

## 2. `NextGen10.dll` — `FUN_1000c01f` (`1000c01f`)
- **Keywords:** callee-follow-up
- **Strings:** `Radio is Not Responding, Radio is Busy, The Radio is Not an OTAP Enabled Radio, Could not communicate with the Radio, CRcmpBundler::Open`

*(qwen2.5-coder:14b, 20.8s)*

1. **Role**: This function appears to handle communication with the radio, possibly managing different states or operations based on the input parameters. It checks for various error conditions and handles them accordingly, including communication failures and state transitions.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to manage state transitions and communication, which could indirectly affect EEPROM persistence through higher-level operations like committing changes or handling locks. It does not explicitly call any functions related to EEPROM commit or reset.

3. **Key Constants / Opcodes / Calls**:
   - **Hex Constants**: `0xd`, `0xc`, `0x1f43`, `0x1c`, `0xf4`, `0xf0`, `0x2011`, `0x11`, `0x410`.
   - **Offsets**: `0x20`, `0x92`, `0x91`, `0x29`.
   - **Error HRESULTs**: `-0x13fffff1`, `-0x13fffff8`, `-0x13fffff3`.
   - **Callees**: `FUN_1000b2ad`, `FUN_1000d523`, `FUN_1000b3bb`, `FUN_1000b5b0`, `FUN_1000b500`.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000b5b0` and `FUN_1000b2ad`, as they are called under conditions that might involve state changes or communication with the radio, which could affect EEPROM persistence.

---

## 3. `NextGen10.dll` — `FUN_1000fe49` (`1000fe49`)
- **Keywords:** callee-follow-up

*(qwen2.5-coder:14b, 11.3s)*

1. **Role**: This function appears to be a constructor or initialization method for an object, setting up internal state and possibly managing a module state. It assigns a parameter to an object field and updates a pointer.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be more related to object initialization and state management within the application.

3. **Key Constants / Opcodes / Calls**:
   - `0x2c`: Offset where `param_1` is stored in the object.
   - `FUN_1002120d`: A function call to retrieve a module state.
   - `AFX_MAINTAIN_STATE2::AFX_MAINTAIN_STATE2`: A constructor call for managing module state.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_1002120d`, as it retrieves a module state which might be involved in managing the radio's persistent state.

---

## 4. `NextGen10.dll` — `FUN_100129ab` (`100129ab`)
- **Keywords:** callee-follow-up

*(qwen2.5-coder:14b, 16.8s)*

1. **Role**: This function initializes a `VARIANTARG` structure, creates a `SAFEARRAY`, and performs operations related to accessing and manipulating data within this array. It checks a condition based on a byte value and returns a boolean result.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. It appears to be a helper function that may be involved in preparing data for storage or processing, but does not explicitly commit changes to permanent storage.

3. **Key Constants / Opcodes / Calls**:
   - `0x11`: Used in `SafeArrayCreateVector` to specify the type of the array elements.
   - `0x370`: The size of the `SAFEARRAY` created.
   - `0x1e`: A threshold used to check the number of elements in the `SAFEARRAY`.
   - `0x1f`: An offset used to access a specific byte in the array data.
   - `FUN_1000b2ad`: A function called to perform an operation, possibly related to initialization or error handling.
   - `FUN_1000b5b0`: A function called to perform another operation, possibly related to data retrieval or processing.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_1000b2ad` and `FUN_1000b5b0`. These functions may contain the logic for committing changes to permanent storage or handling critical operations related to state persistence.

---

## 5. `NextGen10.dll` — `FUN_10016889` (`10016889`)
- **Keywords:** callee-follow-up
- **Strings:** `CRcmpBundler::Del OTAP Full ISHItems Failed, OTAP - Del Full - Overal RC:[%d] , CRcmpBundler::DeleteOTAPCodePlugISHItems`

*(qwen2.5-coder:14b, 23.3s)*

1. **Role**: This function appears to handle the deletion of OTAP (Over-The-Air Programming) items from the radio's codeplug, preparing the radio for new firmware or configuration updates.

2. **EEPROM / Persistence Mechanism**: The function interacts with the radio's EEPROM by preparing and sending commands to delete items from the codeplug partition (0x80). It uses opcodes like `0x0103` (DelIshTypes) to remove items and ensures the changes are made permanent by committing the session with opcode `0x0106` (EnterMode/Session: 01=commit). It also locks and unlocks security with opcodes `0x000C` (OP_UNLOCK) and `0x000D` (OP_LOCK with 16-byte UUID).

3. **Key Constants / Opcodes / Calls**:
   - Opcodes: `0x0103` (DelIshTypes), `0x0106` (EnterMode/Session), `0x000C` (OP_UNLOCK), `0x000D` (OP_LOCK)
   - HRESULTs: `0x80070057` (E_INVALIDARG), `0x80070005` (E_ACCESSDENIED)
   - Callees: `FUN_10016b00`, `FUN_1000b2ad`, `FUN_1000ba53`, `FUN_1001773c`, `FUN_1000b500`

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_10016b00`, which is called multiple times with different opcodes and parameters. This function likely handles the actual communication with the radio to execute the commands that modify the EEPROM.

---

## 6. `NextGen10.dll` — `FUN_10016c17` (`10016c17`)
- **Keywords:** callee-follow-up
- **Strings:** `CRcmpBundler::Del OTAP Partial ISHItems Failed, OTAP, Del Partial - Overal RC:[%d] , CRcmpBundler::DelPartialCodeplug`

*(qwen2.5-coder:14b, 31.9s)*

1. **Role**: This function appears to handle the deletion of partial codeplug items in the radio's memory, likely as part of an Over-The-Air Programming (OTAP) process. It manages data arrays, sends messages, and performs operations related to the deletion process.

2. **EEPROM / Persistence Mechanism**: The function interacts with the radio's memory by sending commands to delete items, which could involve marking certain areas as deleted or invalid. It does not directly commit changes to EEPROM or flash; instead, it prepares the data for deletion and handles the state transition. The actual persistence mechanism (committing changes to EEPROM) is likely handled by other functions or processes not shown in this decompiled code.

3. **Key Constants / Opcodes / Calls**:
   - **Hex Constants**: `0x80`, `0x81`, `0x102`, `0x405`, `0x3c0`, `0x11`, `0x2011`.
   - **Offsets**: `0x2c`, `0x98`, `0x10`, `0xc`.
   - **Error HRESULTs**: `-0x13fffffa`.
   - **Callees**: `FUN_10021490`, `FUN_1002120d`, `FUN_10006984`, `SafeArrayAccessData`, `SafeArrayGetLBound`, `SafeArrayGetUBound`, `SafeArrayCreateVectorEx`, `SendMessageA`, `FUN_1000bd6f`, `FUN_10016b00`, `FUN_1000ba53`.

4. **Next Bite**: The next callee to inspect for tracing EEPROM persistence is `FUN_10016b00`, which is called with opcode `0x102` and appears to handle the actual data manipulation or communication with the radio. This function is likely where the deletion commands are sent to the radio, and further analysis could reveal how these commands affect the radio's permanent state.

---

## 7. `NextGen10.dll` — `FUN_10017c71` (`10017c71`)
- **Keywords:** callee-follow-up

*(qwen2.5-coder:14b, 19.6s)*

1. **Role**: This function appears to handle the opening and configuration of a communication port, likely for interacting with a radio device. It manages various states and operations based on the input parameter `iVar6`.

2. **EEPROM / Persistence Mechanism**: The function indirectly affects the permanent state on the radio by managing the state of communication channels and possibly invoking operations that commit changes to EEPROM or flash memory. It does not directly perform EEPROM operations but sets up conditions that could lead to such operations.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x2011`, `0x24`, `0x28`, `0x18`
   - Offsets: `0xc`, `0xd`, `0x7`, `0x5`, `0x6`, `0x8`, `0x4`
   - HRESULTs: `-0x7fffbfff`
   - Callees: `FUN_10021490`, `FUN_1002120d`, `CString::CString`, `CString::operator=`, `CString::~CString`, `VariantInit`, `SetOtapAbortFlag`, `(**(code **)(*(int *)piVar1[4] + 0x20))`, `(**(code **)(iVar5 + 0x18))`

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `(**(code **)(piVar1 + 0x24))` and `(**(code **)(iVar5 + 0x18))`, as they are invoked based on the conditions and could potentially handle the actual commit or lock/unlock operations on the radio's EEPROM or flash memory.

---

## 8. `NextGen10.dll` — `FUN_1001edd1` (`1001edd1`)
- **Keywords:** callee-follow-up
- **Strings:** `CVirtualRadio::GetCodeplugVersion`

*(qwen2.5-coder:14b, 15.0s)*

1. **Role**: This function appears to handle the retrieval of the codeplug version from a virtual radio device. It initializes COM objects, creates safe arrays, and processes data received from the device.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. It seems to be a transport helper function that handles data retrieval and error handling, possibly indirectly contributing to state persistence by ensuring data integrity and error reporting.

3. **Key Constants / Opcodes / Calls**:
   - COM vtable offsets: `0x48` and `0x30`
   - SafeArray creation: `SafeArrayCreateVector`
   - Data access: `SafeArrayAccessData` and `SafeArrayUnaccessData`
   - Error handling: `HRESULT` checks
   - String operations: `CString::CString`, `CString::AllocSysString`, `SysFreeString`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10021490`, `FUN_1002120d`, and the functions referenced by the COM vtable offsets `0x48` and `0x30`. These functions might contain more direct interactions with the radio's storage mechanisms.

---

## 9. `ConnWinSock10.dll` — `FUN_13001000` (`13001000`)
- **Keywords:** has-strings
- **Strings:** `WSAStartup failed with error %d
`

*(qwen2.5-coder:14b, 16.9s)*

1. **Role**: This function initializes the Windows Sockets API (Winsock) for network communication. It checks if the initialization parameter is `1`, and if so, calls `WSAStartup` to initialize the Winsock library. If `WSAStartup` fails, it logs the error and cleans up by calling `WSACleanup`.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function is primarily responsible for setting up the network transport layer and does not directly handle EEPROM persistence or state management on the radio.

3. **Key Constants / Opcodes / Calls**:
   - `0x202`: Passed to `WSAStartup` as the version requested.
   - `WSAGetLastError()`: Called to retrieve the error code if `WSAStartup` fails.
   - `FUN_13001e8c`: A function that logs the error message.
   - `FUN_13001560`: A function that handles the error logging process.
   - `WSACleanup()`: Cleans up the Winsock library if initialization fails.
   - `s_WSAStartup_failed_with_error__d_1300a034`: The error message string.

4. **Next Bite**: Since this function is a transport helper, the next callees to inspect for EEPROM persistence should be those related to network communication and data handling, such as functions that send or receive data over the network. Look for functions that interact with the radio's partitions or use the known opcodes to manage state.

---

## 10. `ConnWinSock10.dll` — `OpenSock` (`13001090`)
- **Keywords:** exported, has-strings, named
- **Strings:** `connect() failed: %d
, setsockopt() failed: %d
`

*(qwen2.5-coder:14b, 17.6s)*

1. **Role**: The `OpenSock` function establishes a TCP connection to a specified IP address and port. It handles error checking for socket creation and connection, returning appropriate error codes if any step fails.

2. **EEPROM / Persistence Mechanism**: This function is primarily a transport helper. It does not directly handle EEPROM persistence mechanisms such as commit, lock/unlock, or reset. Its role is to set up the communication channel required for subsequent operations that may involve state persistence.

3. **Key Constants / Opcodes / Calls**:
   - **Error Codes**: `6` (if `param_1` or `param_3` is `NULL`), `0x32` (if the IP address comparison fails), and various error codes returned by `WSAGetLastError` for socket operations.
   - **Socket Operations**: `socket(2,1,0)` creates a TCP socket, `setsockopt` sets socket options, and `connect` establishes a connection.
   - **Error Handling**: Calls `FUN_13001e8c` and `FUN_13001560` to handle error messages and cleanup.

4. **Next Bite**: The next callees to inspect for EEPROM persistence would be any functions that send opcodes or handle data transactions over the established socket. Specifically, look into functions that use the socket (`DAT_1300d18c`) to send commands like `0x0106` (EnterMode/Session) or `0x0107` (UnlockSecurity), as these might involve state persistence operations.

---

## 11. `ConnWinSock10.dll` — `CloseSock` (`130011f0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 15.3s)*

1. **Role**: The `CloseSock` function closes a socket and performs a cleanup of the Winsock library. It checks if the socket closure was successful and returns an error code if it was not.

2. **EEPROM / Persistence Mechanism**: This function is primarily a transport helper. It does not directly affect the permanent state on the radio (EEPROM/flash commit, host markers, lock/unlock, reset, etc.). Its role is to ensure that the socket is properly closed and resources are cleaned up, which is essential for maintaining the integrity of the communication channel but does not involve direct manipulation of the radio's persistent storage.

3. **Key Constants / Opcodes / Calls**: 
   - `closesocket(DAT_1300d18c)`: This function call attempts to close the socket identified by `DAT_1300d18c`.
   - `WSACleanup()`: This function call cleans up the Winsock library.
   - `WSAGetLastError()`: This function call retrieves the last error code if the socket closure fails.

4. **Next Bite**: Since this function is a transport helper and does not directly interact with the radio's persistent storage, there is no specific callee to inspect next for tracing EEPROM persistence. The next step would be to trace the functions that handle the actual communication and data manipulation, such as those involving the opcodes and partitions mentioned in the initial documentation.

---

## 12. `ConnWinSock10.dll` — `OpenPPP` (`13001220`)
- **Keywords:** exported, has-strings, named
- **Strings:** `Cannot get server ip address`

*(qwen2.5-coder:14b, 16.4s)*

1. **Role**: The `OpenPPP` function appears to establish a PPP connection and retrieve server IP address information. It handles errors related to connection setup and copies data from local buffers to provided output buffers.

2. **EEPROM / Persistence Mechanism**: This function is primarily a transport helper. It does not directly handle EEPROM persistence or state commitment. Its role is to facilitate communication setup, which is essential for subsequent operations that might involve state persistence.

3. **Key Constants / Opcodes / Calls**:
   - `RASP_PppIp` (0x00000001): Indicates the type of projection information requested.
   - `FUN_13001590`, `FUN_130017f0`, `FUN_13001560`: These are function calls within the same DLL, possibly for error handling and connection setup.
   - `s_Cannot_get_server_ip_address_1300a094`: A string constant used for error messages.
   - `RasGetProjectionInfoA`: A Windows API function to get projection information from a RAS connection.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_13001590` and `FUN_13001560`, as they are involved in error handling and might contain logic related to connection setup that could indirectly affect state persistence.

---

## 13. `ConnWinSock10.dll` — `SetSockOption` (`13001320`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.9s)*

1. **Role**: The `SetSockOption` function sets a socket option for a given socket identified by `param_1` using the option value provided in `param_2`. It returns an error code if `param_2` is null or the result of the `setsockopt` call.

2. **EEPROM / Persistence Mechanism**: This function is a transport helper that sets socket options, which may indirectly affect the state persistence on the radio by configuring how data is transmitted or received. It does not directly handle EEPROM commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**: 
   - `param_1`: The socket option level.
   - `param_2`: The option value.
   - `DAT_1300d18c`: The socket descriptor.
   - `setsockopt`: The system call to set socket options.
   - Return value `6`: Indicates an error if `param_2` is null.

4. **Next Bite**: The next callee to inspect for EEPROM persistence would be the `setsockopt` system call, as it is responsible for applying the socket options that could influence the state persistence on the radio.

---

## 14. `ConnWinSock10.dll` — `ReadData` (`13001350`)
- **Keywords:** exported, has-strings, named
- **Strings:** `recv() failed: error %d
`

*(qwen2.5-coder:14b, 15.2s)*

1. **Role**: The `ReadData` function is responsible for receiving data from a socket connection. It uses the `recv` function to read data into a buffer and handles errors by retrieving the last Windows Sockets error and logging it.

2. **EEPROM / Persistence Mechanism**: This function is a transport helper. It does not directly affect the permanent state on the radio (EEPROM/flash commit, host markers, lock/unlock, reset, state persistence). Its primary role is to facilitate data transfer over the network.

3. **Key Constants / Opcodes / Calls**:
   - `recv` function call with parameters: `DAT_1300d18c` (socket), `param_1` (buffer), `param_2` (length), and `0` (flags).
   - `WSAGetLastError` function call to retrieve the last error code if `recv` fails.
   - `FUN_13001e8c` and `FUN_13001560` are called to log the error message.

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_13001e8c` and `FUN_13001560`, as they handle error logging and might provide more context on how errors are managed and logged, which could indirectly relate to state persistence mechanisms.

---

## 15. `ConnWinSock10.dll` — `BroadcastData` (`130013a0`)
- **Keywords:** exported, has-strings, named
- **Strings:** `send() failed: error %d
`

*(qwen2.5-coder:14b, 15.0s)*

1. **Role**: The `BroadcastData` function is responsible for sending data over a network connection. It uses the `send` function to transmit data and handles errors by logging them and cleaning up the Winsock environment.

2. **EEPROM / Persistence Mechanism**: This function is a transport helper. It does not directly affect the permanent state on the radio (EEPROM/flash commit, host markers, lock/unlock, reset, state persistence). Its primary role is to facilitate data transmission.

3. **Key Constants / Opcodes / Calls**:
   - `DAT_1300d18c`: A global variable likely representing the socket used for sending data.
   - `s_send___failed__error__d_1300a0d0`: A string used for error logging.
   - `FUN_13001e8c`: A function that logs the error message.
   - `FUN_13001560`: A function that processes the logged error.
   - `WSACleanup()`: A function to clean up the Winsock environment.

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_13001e8c` and `FUN_13001560`, as they handle error logging and processing, which might involve interactions with the radio's state management.

---

## 16. `ConnWinSock10.dll` — `RequestData` (`130013f0`)
- **Keywords:** exported, has-strings, named
- **Strings:** `recv() failed: error %d
, recv() failed: error %d
, Read took %d attempt(s).  Timeout passed in : %d  Packet Length = %d
, Additional Read : %d bytes.  Packet Length = %d
, RequestData setsockopt() failed: %d
`

*(qwen2.5-coder:14b, 17.2s)*

1. **Role**: The `RequestData` function is responsible for sending data to the radio and receiving a response. It handles setting socket options, broadcasting data, and reading data with retries and error handling.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. It appears to be a transport helper function that ensures reliable data transmission and reception, which is crucial for maintaining the state of the radio. It does not explicitly perform any EEPROM commit, lock, unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**:
   - `setsockopt` with option `0x1006` (likely `SO_RCVTIMEO` for receive timeout)
   - `BroadcastData` and `ReadData` are called for data transmission and reception
   - Error handling strings: `"recv() failed: error %d\r\n"`, `"Read took %d attempt(s).  Timeout passed in : %d  Packet Length = %d\r\n"`, `"Additional Read : %d bytes.  Packet Length = %d\r\n"`, `"RequestData setsockopt() failed: %d\r\n"`
   - `FUN_13001e8c` and `FUN_13001560` are used for error logging and message display

4. **Next Bite**: The `BroadcastData` and `ReadData` functions should be inspected next to trace how data is actually sent and received, as these are the primary operations that could involve state persistence on the radio.

---

## 17. `ConnWinSock10.dll` — `FUN_13001590` (`13001590`)
- **Keywords:** has-strings
- **Strings:** `Cannot create connection 
, USB25, USB25, USB50, USB50, ConnMotXTS, ConnMotXTS`

*(qwen2.5-coder:14b, 27.1s)*

1. **Role**: This function appears to handle connection setup and error reporting for a radio communication protocol, possibly involving USB or network interfaces. It processes parameters, initializes data structures, and attempts to establish a connection, returning an error code if unsuccessful.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. It seems to be more of a transport helper, managing connection setup and error handling. It does not explicitly show any direct interaction with EEPROM commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**:
   - **Hex Constants**: `0x1000`, `0x2000`, `0x3000`, `0x4000`, `0x5000`, `0x6000`, `0x7000`, `0x80000`, `0x100000`, `0x200000`, `0x10000000`
   - **Offsets**: `0x1300a1fc`, `0x1300a1ec`, `0x1300a1e4`, `0x1300a1dc`, `0x1300a1d4`, `0x1300a1cc`, `0x1300a1c4`, `0x1300a1c0`, `0x1300a1ac`
   - **Error HRESULTs**: `0x704`
   - **Callees**: `FUN_13001880`, `FUN_13001560`, `RasDialA`, `RasGetErrorStringA`, `FUN_130017f0`

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_13001880`, as it is called with parameters that might involve actual communication or state management with the radio.

---

## 18. `ConnWinSock10.dll` — `FUN_130017f0` (`130017f0`)
- **Keywords:** has-strings
- **Strings:** `Sleep(100)
`

*(qwen2.5-coder:14b, 15.8s)*

1. **Role**: This function handles the disconnection process for a PPP connection established with the radio. It attempts to hang up the connection and waits for the connection status to indicate that the disconnection is complete.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. It is a transport helper function that ensures the PPP connection is properly closed, which is an indirect step towards ensuring that any changes made during the session are committed and persisted.

3. **Key Constants / Opcodes / Calls**:
   - `RasHangUpA`: Function to hang up the PPP connection.
   - `RasGetConnectStatusA`: Function to get the status of the PPP connection.
   - `DAT_1300d2ac`: Global variable holding the PPP connection handle.
   - `0x120`: Size of the `tagRASCONNSTATUSA` structure.
   - `6`: Error HRESULT indicating the connection is disconnected.
   - `FUN_13001560`: Another function called with the string `"Sleep(100)\n"`.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_13001560`, as it is called within a loop that waits for the connection to be fully disconnected. This function might contain additional logic related to ensuring state persistence or handling connection-related tasks.

---

## 19. `ConnWinSock10.dll` — `FUN_13001880` (`13001880`)
- **Keywords:** has-strings
- **Strings:** `Unable to create the phonebook entry '%s'.  Error %ld, Unable to set the connection information.  Error %ld , Addresses, Cannot create registry key, Cannot create registry key, RemoteAccess, RemoteAccess\Addresses, 550001`

*(qwen2.5-coder:14b, 23.2s)*

1. **Role**: This function appears to validate and enumerate RAS (Remote Access Service) devices, check for existing entries, and potentially read default entry properties. It handles errors by logging messages and returning error codes.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage on the radio. It seems to be more of a transport helper, managing RAS device enumeration and entry validation, which could indirectly affect state persistence through RAS configuration.

3. **Key Constants / Opcodes / Calls**:
   - **Strings**: "Motorola XTS ", "Entry '%s' already exists", "Unable to read default entry properties.  Error %ld"
   - **Error Codes**: 0xb7 (ENTRY_ALREADY_EXISTS), 0x80070057 (ERROR_INVALID_PARAMETER)
   - **Function Calls**: `RasValidateEntryNameA`, `RasEnumDevicesA`, `RasGetEntryPropertiesA`
   - **Constants**: `0x98` (size of `tagRASDEVINFOA`), `0x2d1` (loop count), `0xb44`, `0x104`

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `RasGetEntryPropertiesA`, which retrieves properties of a RAS entry. This function might interact with the radio's configuration, which could involve EEPROM operations.

---

## 20. `ConnWinSock10.dll` — `entry` (`13002068`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 14.6s)*

1. **Role**: This function appears to handle different operations based on the `param_2` value, potentially involving state management or communication with the radio. It checks conditions and calls other functions to perform specific tasks.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to manage state through calls to other functions, possibly involving commit operations or state persistence mechanisms. It does not explicitly show markers, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**:
   - `param_2` values: 0, 1, 2, 3
   - Offsets: `DAT_1300d2b4`, `DAT_1300e9bc`
   - Functions: `FUN_13001f8f`, `FUN_13001000`
   - Conditional checks and calls to other functions based on `param_2` value.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_13001f8f` and `FUN_13001000`. These functions are called multiple times within the code and may contain the logic for state persistence or commit operations.

---

## 21. `ConnWinSock10.dll` — `FUN_13002250` (`13002250`)
- **Keywords:** has-strings
- **Strings:** `null), null), null)`

*(qwen2.5-coder:14b, 36.2s)*

1. **Role**: The function `FUN_13002250` appears to parse and process a command or configuration string, likely related to radio settings or operations. It handles various cases based on the input characters and possibly invokes other functions to perform specific actions.

2. **EEPROM / Persistence Mechanism**: The function does not directly handle EEPROM commit or lock/unlock operations. It seems to be more of a transport helper or configuration parser that may indirectly influence state persistence through the invocation of other functions (`FUN_13002991`, `FUN_13002a2f`, etc.). It processes input data and possibly sets up conditions for state persistence, but the actual commit or lock operations are likely handled elsewhere.

3. **Key Constants / Opcodes / Calls**:
   - Hex constants: `0x20`, `0x23`, `0x2a`, `0x2b`, `0x2d`, `0x30`, `0x49`, `0x68`, `0x6c`, `0x77`, `0x67`, `0x58`, `0x43`, `0x45`, `0x47`, `0x53`, `0x5a`, `0x69`, `0x36`, `0x34`
   - Offsets: `DAT_13008a14`, `DAT_13008a34`, `PTR_DAT_1300a738`, `PTR_DAT_1300a3d4`
   - Error HRESULTs: Not explicitly shown in the provided code snippet.
   - Callees: `FUN_13002991`, `FUN_13002a2f`, `FUN_13002a4c`, `FUN_13003d3b`, `FUN_13002a3c`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_13002991`, `FUN_13002a2f`, `FUN_13002a4c`, `FUN_13003d3b`, and `FUN_13002a3c`. These functions are likely responsible for handling specific operations that could involve EEPROM commit, lock/unlock, or other state persistence mechanisms.

---

## 22. `ConnWinSock10.dll` — `FUN_1300344b` (`1300344b`)
- **Keywords:** has-strings
- **Strings:** `__GLOBAL_HEAP_SELECTED, __MSVCRT_HEAP_SELECT`

*(qwen2.5-coder:14b, 15.7s)*

1. **Role**: This function appears to check the operating system version and environment variables related to heap selection. It then processes a string from the environment variable or the module file name, possibly to determine heap settings or configuration.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with the radio's EEPROM or flash memory. It seems to be more related to configuration and environment setup rather than state persistence on the radio.

3. **Key Constants / Opcodes / Calls**:
   - OS version check: `GetVersionExA`
   - Environment variable retrieval: `GetEnvironmentVariableA`
   - String manipulation: `_strncmp`, character conversion (uppercase conversion)
   - Module file name retrieval: `GetModuleFileNameA`
   - Heap-related functions: `FUN_13001f60`, `FUN_13001ee0`, `FUN_13002a70`
   - Error handling: `FUN_1300341e`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_13001ee0` and `FUN_13002a70`, as they process the environment variable or module file name string, which might be related to configuration settings that affect the radio's state persistence.

---

## 23. `ConnWinSock10.dll` — `FUN_130036d1` (`130036d1`)
- **Keywords:** has-strings
- **Strings:** `R6009
- not enough space for environment
, R6009
- not enough space for environment
, R6009
- not enough space for environment
, Microsoft Visual C++ Runtime Library, Runtime Error!

Program: , <program name unknown>`

*(qwen2.5-coder:14b, 16.6s)*

1. **Role**: This function appears to handle error reporting and logging, specifically for runtime errors related to insufficient space for the environment. It writes error messages to the standard error handle and constructs detailed error messages using various string manipulation functions.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with the radio's EEPROM or flash memory. Instead, it focuses on error handling and reporting, which is indirectly related to the transport layer but does not involve making state permanent on the radio.

3. **Key Constants / Opcodes / Calls**:
   - Error message strings: "R6009\r\n- not enough space for environment\r\n", "Microsoft Visual C++ Runtime Library", "Runtime Error!\n\nProgram: ", "<program name unknown>".
   - Error handling: `GetStdHandle(0xfffffff4)` to get the standard error handle.
   - String manipulation: `_strlen`, `_strncpy`.
   - Error reporting: `FUN_13004350`, `FUN_13004360`, `FUN_13005c4d`.

4. **Next Bite**: The callees `FUN_13004350`, `FUN_13004360`, and `FUN_13005c4d` should be inspected next to trace further details on error reporting and potentially any indirect interactions with the transport or state persistence mechanisms.

---

## 24. `ConnWinSock10.dll` — `FUN_13005c4d` (`13005c4d`)
- **Keywords:** has-strings
- **Strings:** `GetLastActivePopup, GetActiveWindow, MessageBoxA, user32.dll`

*(qwen2.5-coder:14b, 12.9s)*

1. **Role**: This function appears to load the `user32.dll` library and retrieves the addresses of `MessageBoxA`, `GetActiveWindow`, and `GetLastActivePopup` functions. It then calls these functions to display a message box based on the active window and the last active popup.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanisms on the radio. It is more likely a helper function for displaying messages or managing user interface elements.

3. **Key Constants / Opcodes / Calls**:
   - `user32.dll` is loaded.
   - `MessageBoxA`, `GetActiveWindow`, and `GetLastActivePopup` are retrieved via `GetProcAddress`.
   - The function calls these retrieved functions with parameters passed to it.

4. **Next Bite**: Since the function does not directly interact with EEPROM or persistence mechanisms, the next step would be to inspect the callers of `FUN_13005c4d` to see how it is used in the context of the application. Look for any calls to this function that might be part of a larger sequence involving EEPROM operations.

---

## 25. `NewProto10.dll` — `FUN_12001575` (`12001575`)
- **Keywords:** has-strings
- **Strings:** `REGISTRY, Module`

*(qwen2.5-coder:14b, 19.2s)*

1. **Role**: This function appears to handle the registration or configuration of a module, possibly related to the radio's operation. It retrieves the module's file path, converts it to a wide character string, and then processes it further, likely involving some form of registry or configuration update.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. Instead, it seems to be involved in setting up or updating configuration settings, which could indirectly affect the radio's state persistence by ensuring that necessary configurations are correctly applied. It does not explicitly perform any commit, lock, unlock, or reset operations on the EEPROM or flash.

3. **Key Constants / Opcodes / Calls**:
   - **Strings**: "REGISTRY", "Module"
   - **Error HRESULT**: `0x8007000e` (ERROR_INSUFFICIENT_BUFFER)
   - **Function Calls**: `FUN_12001732`, `GetModuleFileNameA`, `GetShortPathNameA`, `MultiByteToWideChar`, `lstrlenW`, `FUN_12001701`, `FUN_1200174e`, `FUN_120019dc`, `FUN_12001823`, `FUN_12004037`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_120019dc` and `FUN_1200185c`, as they are conditionally called based on the value of `param_3` and could potentially involve more direct interactions with the radio's configuration or state.

---

## 26. `NewProto10.dll` — `FUN_12001ec4` (`12001ec4`)
- **Keywords:** has-strings
- **Strings:** `TYPELIB, TYPELIB, TYPELIB, TYPELIB, CLSID, CLSID, Delete, NoRemove`

*(qwen2.5-coder:14b, 25.0s)*

1. **Role**: This function appears to manage registry operations, including deleting, removing, and modifying keys and values. It handles operations like `Delete`, `ForceRemove`, and `NoRemove`, and interacts with the Windows Registry API to perform these actions.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. Instead, it seems to manage registry keys and values, which could be used to configure or manage the radio's state. The function does not explicitly perform any EEPROM commit, lock/unlock, or reset operations. It relies on the underlying system to handle these aspects.

3. **Key Constants / Opcodes / Calls**:
   - **Strings**: `"Delete"`, `"ForceRemove"`, `"NoRemove"`, `"CLSID"`, `"TYPELIB"`
   - **Error Codes**: `-0x7ffdfff7` (indicating an error)
   - **Registry API Calls**: `RegCloseKey`, `RegDeleteValueA`, `RegDeleteKeyA`, `RegCreateKeyExA`
   - **Function Calls**: `FUN_12001b90`, `FUN_120023af`, `FUN_120024d1`, `FUN_120027f4`, `FUN_12002748`, `FUN_1200277d`, `FUN_12004120`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_120027f4`, `FUN_120024d1`, and `FUN_12001ec4`. These functions might contain the actual logic for interacting with the radio's EEPROM or managing its state.

---

## 27. `NewProto10.dll` — `FUN_12002ce4` (`12002ce4`)
- **Keywords:** has-strings
- **Strings:** `UnRegisterTypeLib, oleaut32.dll`

*(qwen2.5-coder:14b, 18.6s)*

1. **Role**: This function appears to unregister a type library associated with a given library attribute. It loads the `oleaut32.dll` library, retrieves the `UnRegisterTypeLib` function, and calls it with the library attributes to unregister the type library.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It is more likely a helper function for managing COM type libraries, which may indirectly affect state persistence through COM object management.

3. **Key Constants / Opcodes / Calls**:
   - `HRESULT HVar1`, `HRESULT HVar2`: Used to store the result of function calls.
   - `s_oleaut32_dll_1200b220`: String constant for "oleaut32.dll".
   - `s_UnRegisterTypeLib_1200b20c`: String constant for "UnRegisterTypeLib".
   - `FUN_12002d85`: Another function called with parameters to get library attributes.
   - `local_8->lpVtbl->GetLibAttr`: COM method to get library attributes.
   - `local_8->lpVtbl->ReleaseTLibAttr`: COM method to release library attributes.
   - `local_8->lpVtbl->Release`: COM method to release the type library object.
   - `SysFreeString(local_c)`: Frees a BSTR string.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_12002d85`, as it is called with parameters to get library attributes and may involve more direct interactions with the radio's state or storage.

---

## 28. `NewProto10.dll` — `FUN_120034c3` (`120034c3`)
- **Keywords:** has-strings
- **Strings:** `PROTOCS_TCPUSB, PROTOCS_TCPRS232, PROTOTCPUSB, PROTOUSB, PROTOSB_EPRCMP, PROTOSB_EPRS232, PROTOTCPRS232, PROTORS232`

*(qwen2.5-coder:14b, 19.1s)*

1. **Role**: This function appears to determine the transport protocol being used by comparing the input parameter `param_2` against a series of predefined transport protocol strings. It then calls a function pointer to handle the identified protocol.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly handle EEPROM persistence. It seems to be a transport helper function that identifies the protocol and delegates further processing to another function. The persistence mechanism would likely be handled by the function called through the function pointer.

3. **Key Constants / Opcodes / Calls**:
   - Transport protocol strings: "PROTOCS_TCPUSB", "PROTOCS_TCPRS232", "PROTOTCPUSB", "PROTOUSB", "PROTOSB_EPRCMP", "PROTOSB_EPRS232", "PROTOTCPRS232", "PROTORS232", "ESBEP", "SBEP".
   - Function pointer call: `(**(code **)(**(int **)(param_1 + 8) + 0x18))(*(int **)(param_1 + 8),uVar2,param_5,in_stack_00000024);`
   - Error HRESULT: `0x80004003` if the condition `*(int *)(param_1 + 8) == 0` is met.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_120046cc`, which is called multiple times with different transport protocol strings. This function likely handles the actual comparison and might be involved in setting up the transport layer, which could include persistence mechanisms.

---

## 29. `NewProto10.dll` — `FUN_120035ec` (`120035ec`)
- **Keywords:** has-strings
- **Strings:** `CNewProtocol::BroadcastData HexStreamToByteArray failed 
, CNewProtocol::BroadcastData  There should be an even number of wide characters in the data
`

*(qwen2.5-coder:14b, 14.2s)*

1. **Role**: This function appears to handle broadcasting data from a BSTR (wide string) parameter to an underlying protocol interface. It checks the length of the input string, converts it to a byte array, and then delegates the actual data transmission to another function.

2. **EEPROM / Persistence Mechanism**: The function does not directly handle EEPROM persistence or state commitment. It seems to be a transport helper function that prepares and sends data, which could be part of a larger process involving EEPROM operations. The actual persistence mechanism would likely be handled by other functions or methods invoked elsewhere in the code.

3. **Key Constants / Opcodes / Calls**:
   - Error HRESULTs: `0x80004003`, `0x80004005`, `0x80070057`
   - COM vtable offset: `0xc`
   - Callees: `FUN_120037b8`, `FUN_120037b3`

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_120037b8`, as it is responsible for converting the wide string to a byte array. This function might interact with lower-level operations that could involve EEPROM persistence.

---

## 30. `NewProto10.dll` — `FUN_12003675` (`12003675`)
- **Keywords:** has-strings
- **Strings:** `CNewProtocol::RequestData HexStreamToByteArray failed 
, CNewProtocol::RequestData  There should be an even number of wide characters in the data
`

*(qwen2.5-coder:14b, 15.8s)*

1. **Role**: This function appears to handle data requests, converting a BSTR input to a byte array and processing it through a series of checks and operations. It seems to involve communication with a device or service, possibly related to configuration or data management.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to be a transport helper function that processes data and interacts with a protocol handler. It may indirectly contribute to state persistence by ensuring data integrity and proper communication, but it does not explicitly commit changes to EEPROM or flash.

3. **Key Constants / Opcodes / Calls**:
   - `0x7fffbffd` and `0x7fffbffb` are error HRESULTs.
   - `0x7ff8ffa9` is another error HRESULT.
   - `FUN_12004120`, `FUN_120037b8`, `FUN_120037b3`, `FUN_1200395d` are function calls within the code.
   - `0x14` is an offset used to access a function pointer in a vtable.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_120037b8`, as it processes the input data and could be involved in preparing or validating the data before further processing or communication.

---

## 31. `NewProto10.dll` — `FUN_1200386f` (`1200386f`)
- **Keywords:** has-strings
- **Strings:** `CNewProtocol::HexStringToInt failed: input string is not hexadecimal.`

*(qwen2.5-coder:14b, 12.3s)*

1. **Role**: This function appears to convert a hexadecimal string to an integer. It iterates through the string from the end to the beginning, converting each character to its corresponding integer value and accumulating the result.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function is primarily involved in string-to-integer conversion and does not directly interact with EEPROM or state persistence mechanisms.

3. **Key Constants / Opcodes / Calls**:
   - Hexadecimal conversion logic: `0x30` (for '0'-'9') and `0x37` (for 'A'-'F').
   - Error handling: Calls `FUN_120037b3()` if the input string is not hexadecimal.
   - String length calculation: Uses `_strlen(param_1)`.

4. **Next Bite**: The callees `FUN_12004836`, `FUN_12004864`, and `FUN_1200480e` should be inspected next to trace any potential interactions with EEPROM or state persistence mechanisms.

---

## 32. `NewProto10.dll` — `operator_new` (`12004029`)
- **Keywords:** named

*(qwen2.5-coder:14b, 9.5s)*

1. **Role**: This function is an overloaded `operator new` that allocates memory for objects. It calls `__nh_malloc` to perform the actual memory allocation.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function is a standard memory allocation routine and does not directly interact with the radio's EEPROM or state persistence mechanisms.

3. **Key Constants / Opcodes / Calls**: 
   - `__nh_malloc` is the function called to allocate memory.
   - No specific hex constants, offsets, error HRESULTs, or other opcodes are observed in the provided code snippet.

4. **Next Bite**: Since this function is a standard memory allocator, the next step should be to inspect the callees of `__nh_malloc` or any other functions that might be involved in memory management or state persistence within the `NewProto10.dll` library.

---

## 33. `NewProto10.dll` — `entry` (`12004af4`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 17.0s)*

1. **Role**: This function appears to be an entry point or handler for different operations based on the `param_2` value. It manages the flow of operations, possibly involving initialization, processing, and cleanup.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. It seems to be a transport helper that manages the flow of operations and possibly delegates EEPROM persistence tasks to other functions. It does not explicitly show markers, commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**:
   - `param_2` values: 0, 1, 2, 3
   - `DAT_1200e140`: A global variable used when `param_2` is 0.
   - `DAT_1200e848`: A pointer to a function that is called if `param_2` is 1 or 2 and returns 0.
   - `FUN_12004a1b`: A function called multiple times with different parameters.
   - `FUN_12001015`: A function called when `param_2` is 1 and the previous function returns non-zero.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_12004a1b` and `FUN_12001015`. These functions are called multiple times and might contain the actual logic for handling EEPROM persistence.

---

## 34. `NewProto10.dll` — `FUN_12004d2f` (`12004d2f`)
- **Keywords:** has-strings
- **Strings:** `__GLOBAL_HEAP_SELECTED, __MSVCRT_HEAP_SELECT`

*(qwen2.5-coder:14b, 14.7s)*

1. **Role**: This function checks the operating system version and environment variables related to heap selection. It then processes a string from the environment variable to determine if it matches the module file name, and if so, it calls another function (`FUN_120073a8`) with specific parameters.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the radio's EEPROM or flash memory. It appears to be a transport helper function that processes environment variables and module file names, possibly to configure or verify the environment before proceeding with operations that might affect the radio's state.

3. **Key Constants / Opcodes / Calls**:
   - OS version check: `GetVersionExA`
   - Environment variable retrieval: `GetEnvironmentVariableA`
   - String manipulation: `_strncmp`, `_strstr`, `_strchr`
   - Function call: `FUN_120073a8`
   - Error handling: Returns `1`, `2`, `3`, or `3 - (uint)(bVar8 < 6)`

4. **Next Bite**: The next function to inspect for EEPROM persistence is `FUN_120073a8`, as it is called with parameters that might involve direct interaction with the radio's state or configuration.

---

## 35. `NewProto10.dll` — `FUN_12007076` (`12007076`)
- **Keywords:** has-strings
- **Strings:** `R6009
- not enough space for environment
, R6009
- not enough space for environment
, R6009
- not enough space for environment
, Microsoft Visual C++ Runtime Library, Runtime Error!

Program: , <program name unknown>`

*(qwen2.5-coder:14b, 17.8s)*

1. **Role**: This function appears to handle error reporting and logging, specifically for runtime errors related to insufficient space for the environment or other critical issues. It writes error messages to the standard error handle or constructs a detailed error message if a runtime error occurs.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with the radio's EEPROM or flash memory. It seems to be more focused on error handling and reporting rather than managing the radio's persistent state.

3. **Key Constants / Opcodes / Calls**:
   - Error message strings: "R6009\r\n- not enough space for environment\r\n", "Microsoft Visual C++ Runtime Library", "Runtime Error!\n\nProgram: ", "<program name unknown>".
   - Function calls: `GetStdHandle`, `WriteFile`, `GetModuleFileNameA`, `FUN_12007c60`, `FUN_12007c70`, `FUN_12008281`.
   - Constants: `0xfffffff4` (standard error handle), `0x104` (buffer size for module file name), `0x3c` (buffer size threshold), `0x12010` (error dialog flags).

4. **Next Bite**: The callees `FUN_12007c60`, `FUN_12007c70`, and `FUN_12008281` should be inspected next to trace any further interactions with the radio's persistent state or error handling mechanisms.

---

## 36. `NewProto10.dll` — `FUN_12008281` (`12008281`)
- **Keywords:** has-strings
- **Strings:** `GetLastActivePopup, GetActiveWindow, MessageBoxA, user32.dll`

*(qwen2.5-coder:14b, 18.3s)*

1. **Role**: This function appears to load the `user32.dll` library and retrieves addresses for `MessageBoxA`, `GetActiveWindow`, and `GetLastActivePopup` functions. It then calls these functions to display a message box associated with the active window.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It seems to be a utility function for displaying messages, which is indirectly related to the transport layer by potentially handling errors or status updates.

3. **Key Constants / Opcodes / Calls**: 
   - `DAT_1200e3b0`, `DAT_1200e3b4`, `DAT_1200e3b8`: Addresses for `MessageBoxA`, `GetActiveWindow`, and `GetLastActivePopup` respectively.
   - `LoadLibraryA("user32.dll")`: Loads the user32.dll library.
   - `GetProcAddress`: Retrieves the address of the specified function from the loaded DLL.
   - `MessageBoxA`, `GetActiveWindow`, `GetLastActivePopup`: Functions called to display a message box and get window handles.

4. **Next Bite**: The next callees to inspect for EEPROM persistence would be any functions that interact with the transport layer or handle data storage, such as `FUN_*` functions that use the known opcodes like `0x0100` (ReadIsh), `0x0101` (WriteIsh), or `0x0106` (EnterMode/Session). These functions are more likely to involve direct interactions with the radio's storage mechanisms.

---

## 37. `PortManager10.dll` — `CPortManager` (`10001040`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.0s)*

1. **Role**: This function is the constructor for the `CPortManager` class. It allocates memory for two objects of size 0x104 bytes and assigns their pointers to the `this` object at offsets 0x104 and 0x108.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or handle state persistence. It appears to be a memory management function for the `CPortManager` object.

3. **Key Constants / Opcodes / Calls**: 
   - Memory allocation sizes: 0x104 bytes
   - Offsets: 0x104, 0x108
   - Calls: `operator_new` (twice)

4. **Next Bite**: Since this function is primarily concerned with memory allocation, the next callees to inspect for EEPROM persistence should be those related to communication or state management, such as functions that handle opcodes or interact with the radio's EEPROM. Look for functions that use the allocated memory or call other functions that might involve EEPROM operations.

---

## 38. `PortManager10.dll` — `~CPortManager` (`10001070`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.6s)*

1. **Role**: The `~CPortManager` destructor function is responsible for cleaning up resources associated with the `CPortManager` object. It calls two other functions (`FUN_1000199e`) with pointers to objects stored at offsets `0x104` and `0x108` within the `CPortManager` instance.

2. **EEPROM / Persistence Mechanism**: The function does not directly handle EEPROM persistence or state commitment. It appears to be a transport helper function that cleans up resources, possibly related to communication channels or memory management, without affecting the permanent state of the radio's EEPROM or flash memory.

3. **Key Constants / Opcodes / Calls**: 
   - Offsets: `0x104`, `0x108`
   - Callee: `FUN_1000199e`

4. **Next Bite**: To trace EEPROM persistence, the next callees to inspect are `FUN_1000199e`. Analyzing these functions will provide more insight into how resources are managed and whether they interact with the radio's EEPROM or flash memory.

---

## 39. `PortManager10.dll` — `ListDevices` (`10001090`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 12.6s)*

1. **Role**: The `ListDevices` function appears to enumerate and list devices, likely including communication ports and possibly radio devices. It checks the operating system version and conditionally calls different functions based on the provided parameters.

2. **EEPROM / Persistence Mechanism**: The function does not directly handle EEPROM persistence or state commitment. It seems to be a transport helper function that may indirectly influence state persistence through device enumeration and configuration.

3. **Key Constants / Opcodes / Calls**:
   - OS version check: `GetVersionExA`
   - Error code: `0x57` (ERROR_INVALID_PARAMETER)
   - Function calls: `GetNTCommPort`, `GetRadioInfo`, `GetDeviceInfo`
   - GUID construction: Uses constants from `DAT_10008130`, `DAT_10008138`, `DAT_1000813c`, `DAT_10008134`

4. **Next Bite**: The `GetDeviceInfo` function should be inspected next to trace any potential interactions with EEPROM persistence or state commitment.

---

## 40. `PortManager10.dll` — `GetDeviceInfo` (`100011c0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 17.2s)*

1. **Role**: The `GetDeviceInfo` function appears to enumerate devices and retrieve information related to a specific device identified by a GUID. It initializes a `CSetupMgr` object, calls `FUN_10001630` to set up the device, and then uses `EnumerateDevices` to populate a `DeviceList` structure with device information. Finally, it cleans up resources by calling `FUN_10001680`.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. It seems to be a transport helper function that sets up and retrieves device information without explicitly committing changes to permanent storage. The persistence mechanism is likely handled by other functions that are not shown in this snippet.

3. **Key Constants / Opcodes / Calls**:
   - `FUN_10001630`: Called to initialize the `CSetupMgr` object with the provided GUID and device name.
   - `EnumerateDevices`: This function is called with the `CPortManager` instance, a `DeviceList` reference, the initialized `CSetupMgr` object, and additional parameters. It returns an `HRESULT` indicating success or failure.
   - `FUN_10001680`: Called to clean up resources associated with the `CSetupMgr` object.

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `EnumerateDevices`. This function likely interacts with the device to retrieve information and may involve operations that affect the device's state, including potential interactions with EEPROM or flash storage.

---

## 41. `PortManager10.dll` — `GetNTCommPort` (`10001280`)
- **Keywords:** exported, has-strings, named
- **Strings:** `Communications Port, Communications Port, HARDWARE\DEVICEMAP\SERIALCOMM, HARDWARE\DEVICEMAP\SERIALCOMM`

*(qwen2.5-coder:14b, 20.6s)*

1. **Role**: The `GetNTCommPort` function appears to enumerate and retrieve information about communication ports, specifically serial ports, from the Windows registry. It queries the registry key `HARDWARE\DEVICEMAP\SERIALCOMM` to list available serial ports and their corresponding device names.

2. **EEPROM / Persistence Mechanism**: This function does not directly interact with the radio's EEPROM or flash memory. It is primarily a helper function for managing communication ports and does not involve any direct operations related to making state permanent on the radio. It is more focused on transport and communication setup rather than EEPROM persistence.

3. **Key Constants / Opcodes / Calls**:
   - Registry key: `HARDWARE\DEVICEMAP\SERIALCOMM`
   - Error HRESULTs: `0xe` (ERROR_OUTOFMEMORY)
   - Registry access flags: `0x20019` (KEY_READ | KEY_WOW64_64KEY)
   - String constants: `"Communications Port"`
   - Callees: `RegOpenKeyExA`, `RegQueryInfoKeyA`, `RegEnumValueA`, `FUN_1000199e` (likely for memory deallocation)

4. **Next Bite**: Since this function is primarily about port management and does not directly interact with EEPROM persistence, the next step should be to inspect the callees that handle actual communication with the radio, such as `FUN_1000199e` or any other functions that might be involved in sending commands to the radio (e.g., those handling opcodes like `0x0100` to `0x0107`). These functions are more likely to involve operations that affect the radio's permanent state.

---

## 42. `PortManager10.dll` — `GetRadioInfo` (`10001480`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 10.7s)*

1. **Role**: The `GetRadioInfo` function appears to be a simple method within the `CPortManager` class that returns a constant value (`0x32`) without performing any significant operations on the input parameters or the device list.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or any persistence mechanisms. It seems to be a utility function that provides information about the radio, possibly for higher-level operations.

3. **Key Constants / Opcodes / Calls**: The function returns the constant `0x32`. There are no specific hex constants, offsets, error HRESULTs, or callees observed in the provided code snippet.

4. **Next Bite**: Since the function does not directly interact with EEPROM or persistence mechanisms, there is no specific callee to inspect next for tracing EEPROM persistence. Further analysis would involve tracing higher-level functions that might call `GetRadioInfo` and interact with the radio's state.

---

## 43. `PortManager10.dll` — `EnumerateDevices` (`10001490`)
- **Keywords:** exported, has-strings, named
- **Strings:** `Failed to get device name in PortManager. Error code:%d
, Failed to get Comm Port in PortManager. Error code:%d
`

*(qwen2.5-coder:14b, 18.6s)*

1. **Role**: The `EnumerateDevices` function in `PortManager10.dll` is responsible for enumerating devices, likely by interacting with a setup manager to retrieve device names and communication ports. It handles errors related to device enumeration and updates a device list.

2. **EEPROM / Persistence Mechanism**: The function does not directly handle EEPROM persistence or state commitment. It appears to be a transport helper function that manages device communication and error handling, but does not explicitly involve committing changes to EEPROM or handling locks/unlocks.

3. **Key Constants / Opcodes / Calls**:
   - Error strings: `"Failed to get device name in PortManager. Error code:%d\r\n"`, `"Failed to get Comm Port in PortManager. Error code:%d\r\n"`
   - HRESULTs: `0x103` (specific error code)
   - Function calls: `FUN_100016d0`, `FUN_10001720`, `FUN_10001850`, `FUN_10001dd0`, `FUN_10001d7e`, `FUN_10001010`
   - Offsets: `0x104`, `0x108`, `0x6800`

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10001720`, `FUN_10001850`, and `FUN_10001dd0`, as they interact with device and communication settings which might involve underlying EEPROM operations.

---

## 44. `PortManager10.dll` — `operator=` (`100015f0`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.6s)*

1. **Role**: This function is an assignment operator for the `DeviceList` class, copying data from one `DeviceList` object to another by iterating through memory blocks of size 4 bytes each, up to a total of 0x1a01 (6145) iterations.

2. **EEPROM / Persistence Mechanism**: This function itself does not directly handle EEPROM persistence. It is a transport helper function that copies data between `DeviceList` objects, which may be part of a larger process involving state persistence on the radio.

3. **Key Constants / Opcodes / Calls**: 
   - The loop runs for 0x1a01 iterations.
   - No specific opcodes, error HRESULTs, or direct calls to EEPROM functions are observed in the provided code snippet.

4. **Next Bite**: Since this function is primarily a data copy operation, the next step should be to inspect the callers of this function to understand the context in which it is used. Look for functions that involve state management, such as those that might call `EnterMode` (opcode 0x0106) or `OP_LOCK` (opcode 0x000D), which are known to affect the state persistence on the radio.

---

## 45. `PortManager10.dll` — `operator=` (`10001610`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 13.9s)*

1. **Role**: This function is an assignment operator for the `CPortManager` class. It copies the contents of one `CPortManager` object to another by iterating through and copying 4-byte chunks of data from the source object to the destination object.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly handle EEPROM persistence or state commitment. It appears to be a transport helper function that copies the state of one `CPortManager` object to another, which could be part of a larger process involving state management and persistence.

3. **Key Constants / Opcodes / Calls**: The function uses a loop that iterates 67 times (0x43 iterations), copying 4 bytes at a time. There are no specific hex constants, opcodes, or direct calls to functions related to EEPROM or state persistence in the provided code snippet.

4. **Next Bite**: Since the function is primarily focused on copying object state, the next step would be to inspect the constructors, destructors, or other methods of the `CPortManager` class to see if they involve any calls to functions that handle EEPROM persistence or state commitment. Additionally, tracing the flow of data through the application to see where this assignment operator is used in the context of state management could provide more insight.

---

## 46. `PortManager10.dll` — `FUN_10001630` (`10001630`)
- **Keywords:** has-strings
- **Strings:** `Device Enumeration failed with Error%d
`

*(qwen2.5-coder:14b, 13.5s)*

1. **Role**: This function initializes a device enumeration process for a specified class and path, storing the result in the object's state. It handles errors by logging them and cleaning up.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function is primarily concerned with device enumeration and error handling, not directly with making state permanent on the radio. It does not involve EEPROM commit, lock/unlock, or other persistence mechanisms.

3. **Key Constants / Opcodes / Calls**:
   - `GUID` and `PCSTR` parameters for device class and path.
   - `SetupDiGetClassDevsA` call for device enumeration.
   - `GetLastError` to retrieve error codes.
   - `FUN_10001d7e` for logging errors.
   - `FUN_10001010` for cleanup.
   - Error message string: "Device Enumeration failed with Error%d\r\n".

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_10001d7e` and `FUN_10001010`, as they might involve more detailed error handling or cleanup processes that could be related to state persistence.

---

## 47. `PortManager10.dll` — `FUN_10001680` (`10001680`)
- **Keywords:** has-strings
- **Strings:** `DestroyDevice failed with Error%d
`

*(qwen2.5-coder:14b, 15.8s)*

1. **Role**: This function is responsible for destroying a device information list associated with a device handle. It checks if the handle is valid, attempts to destroy the list, and if it fails, logs an error message and performs additional cleanup.

2. **EEPROM / Persistence Mechanism**: This function does not directly affect the permanent state on the radio. It is a transport helper function that manages device handles and error logging, which are indirectly related to the overall operation of the system but do not involve direct EEPROM commit, lock/unlock, or reset operations.

3. **Key Constants / Opcodes / Calls**:
   - `SetupDiDestroyDeviceInfoList`: A Windows API function to destroy a device information list.
   - `GetLastError`: Retrieves the last error code set by a system service or function.
   - `FUN_10001d7e`: A function that formats and logs an error message.
   - `FUN_10001010`: A function that performs additional cleanup or logging.
   - `s_DestroyDevice_failed_with_Error__1000a11c`: A string used in the error message.

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_10001d7e` and `FUN_10001010`, as they may contain more detailed operations related to error handling and cleanup that could be indirectly involved in maintaining the state of the radio.

---

## 48. `PortManager10.dll` — `FUN_10001720` (`10001720`)
- **Keywords:** has-strings
- **Strings:** `GetDeviceRegistryProperty() failed to get registry property; Error code %d
, GetDeviceRegistryProperty unable to allocate memory. Error code: %d
, Length is 0. Error Code %d 
`

*(qwen2.5-coder:14b, 18.2s)*

1. **Role**: This function retrieves a device registry property and copies it into a buffer provided by the caller. It handles errors related to memory allocation and registry property retrieval, logging appropriate error messages.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with the radio's EEPROM or flash memory. It appears to be a utility function for retrieving device properties, which may be used in a broader context to manage state persistence.

3. **Key Constants / Opcodes / Calls**:
   - `SetupDiGetDeviceRegistryPropertyA`: Windows API call to retrieve a device registry property.
   - `GetLastError`: Retrieves the last error code set by a system call.
   - `FUN_10001d7e`: Likely a function for logging error messages.
   - `FUN_10001010`: Another function, possibly for additional error handling or cleanup.
   - `FUN_10001ed1`: Frees the allocated memory for the property buffer.
   - Error messages: "GetDeviceRegistryProperty() failed to get registry property; Error code %d\r\n", "GetDeviceRegistryProperty unable to allocate memory. Error code: %d\r\n", "Length is 0. Error Code %d \r\n".

4. **Next Bite**: The next callees to inspect for tracing EEPROM persistence are `FUN_10001d7e` and `FUN_10001010`, as they may contain additional logic related to error handling or state management that could be relevant to understanding how the radio's permanent state is managed.

---

## 49. `PortManager10.dll` — `FUN_10001850` (`10001850`)
- **Keywords:** has-strings
- **Strings:** `AttachedTo, AttachedTo, PortName, PortName`

*(qwen2.5-coder:14b, 18.5s)*

1. **Role**: This function appears to query a registry key for a value associated with a device, copying the value into a provided buffer if successful. It handles different scenarios based on the `param_3` flag, either using a hardcoded string or a dynamic string derived from the OS version.

2. **EEPROM / Persistence Mechanism**: The function interacts with the Windows registry to read a value, which could be related to the state or configuration of the radio. It does not directly manipulate EEPROM or flash storage; instead, it retrieves data that might be used to manage the radio's state. The function does not explicitly commit, lock, or unlock EEPROM/flash; it is more of a transport helper for retrieving configuration data.

3. **Key Constants / Opcodes / Calls**:
   - **Strings**: `"AttachedTo"`, `"PortName"`
   - **Registry Key Type**: `KeyType` is set to 1 or 2 based on the OS version.
   - **Registry Functions**: `SetupDiOpenDevRegKey`, `RegQueryValueExA`, `RegCloseKey`.
   - **Error Codes**: `0x57` (ERROR_INVALID_PARAMETER), `6` (ERROR_BAD_ENVIRONMENT).

4. **Next Bite**: The next callees to inspect for EEPROM persistence would be `SetupDiOpenDevRegKey` and `RegQueryValueExA`, as they directly interact with the registry, which could be storing data related to the radio's state. Additionally, examining the callers of `FUN_10001850` might provide more context on how this function fits into the overall state management process.

---

## 50. `PortManager10.dll` — `operator_new` (`10001990`)
- **Keywords:** named

*(qwen2.5-coder:14b, 9.6s)*

1. **Role**: This function is an overloaded `operator new` that allocates memory for objects. It calls `__nh_malloc` to perform the actual memory allocation.

2. **EEPROM / Persistence Mechanism**: None / transport helper. This function is a standard memory allocation routine and does not directly interact with the radio's EEPROM or handle state persistence mechanisms.

3. **Key Constants / Opcodes / Calls**: 
   - `__nh_malloc` is the function called to allocate memory.
   - No specific hex constants, offsets, error HRESULTs, or opcodes are observed in the provided code snippet.

4. **Next Bite**: Since this function is a standard memory allocator, the next step should be to inspect the callees of `__nh_malloc` or any other functions that might be involved in memory management or state persistence within the `PortManager10.dll`.

---

## 51. `PortManager10.dll` — `entry` (`100021cd`)
- **Keywords:** exported, named

*(qwen2.5-coder:14b, 18.6s)*

1. **Role**: This function appears to manage operations related to different modes or states of the radio, possibly handling initialization, processing, and finalization of operations based on the `param_2` value. It seems to delegate tasks to other functions based on the mode specified.

2. **EEPROM / Persistence Mechanism**: The function does not directly manipulate EEPROM or flash storage. Instead, it seems to manage the flow of operations that might involve committing changes to persistent storage. It calls other functions (`FUN_100020f4`, `FUN_10001000`) which could be responsible for actual persistence operations. The presence of `DAT_1000e5e8` as a function pointer suggests it might be involved in handling specific operations that could include persistence.

3. **Key Constants / Opcodes / Calls**:
   - `param_2` values: 0, 1, 2, 3
   - `DAT_1000cecc`: A data pointer used when `param_2` is 0.
   - `DAT_1000e5e8`: A function pointer that might be used for specific operations.
   - `FUN_100020f4`: A function called multiple times with different parameters.
   - `FUN_10001000`: Another function called when `param_2` is 1.

4. **Next Bite**: The next callees to inspect for EEPROM persistence are `FUN_100020f4` and `FUN_10001000`. These functions are called multiple times and could be responsible for the actual persistence operations.

---

## 52. `PortManager10.dll` — `FUN_10002e67` (`10002e67`)
- **Keywords:** has-strings
- **Strings:** `null), null), null)`

**ERROR querying homelab AI:** `timed out`

---

## 53. `PortManager10.dll` — `FUN_10003874` (`10003874`)
- **Keywords:** has-strings
- **Strings:** `__GLOBAL_HEAP_SELECTED, __MSVCRT_HEAP_SELECT`

*(qwen2.5-coder:14b, 14.0s)*

1. **Role**: This function appears to check the environment and module file name, process certain environment variables, and potentially handle heap selection. It seems to be a helper function that may be involved in setting up or verifying the environment for subsequent operations.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with the EEPROM or flash storage. It seems to be more of a transport helper, possibly ensuring the environment is correctly set up before any EEPROM operations are performed.

3. **Key Constants / Opcodes / Calls**:
   - Environment variable names: `__MSVCRT_HEAP_SELECT`, `__GLOBAL_HEAP_SELECTED`
   - String processing: Converts characters to uppercase if they fall within a specific range.
   - Calls: `GetVersionExA`, `GetEnvironmentVariableA`, `_strncmp`, `_strstr`, `_strchr`, `FUN_100068cc`, `FUN_10003847`

4. **Next Bite**: The next callee to inspect for EEPROM persistence is `FUN_100068cc`, as it is called with parameters that might indicate a more direct interaction with the radio's storage.

---

## 54. `PortManager10.dll` — `FUN_100051d2` (`100051d2`)
- **Keywords:** has-strings
- **Strings:** `R6009
- not enough space for environment
, R6009
- not enough space for environment
, R6009
- not enough space for environment
, Microsoft Visual C++ Runtime Library, Runtime Error!

Program: , <program name unknown>`

*(qwen2.5-coder:14b, 18.3s)*

1. **Role**: This function appears to handle error reporting and possibly logging, checking conditions related to a parameter (`param_1`) and writing error messages to standard error or a file if certain conditions are met.

2. **EEPROM / Persistence Mechanism**: The function does not directly interact with EEPROM or flash storage. It seems to be more of a transport helper or error handling mechanism, possibly related to logging or reporting errors that could affect the state persistence of the radio.

3. **Key Constants / Opcodes / Calls**:
   - `0x1000c460`: Base address for a data structure or array.
   - `0x1000c464`: Base address for another data structure or array.
   - `0x1000ced8` and `0x1000cedc`: Flags or states that determine the execution path.
   - `0xfc`: A specific value that skips certain error handling.
   - `0x100052f6`: An address used in error reporting.
   - `FUN_10006180`, `FUN_10006190`, `FUN_10007063`: Callees involved in string manipulation and error reporting.

4. **Next Bite**: The callees `FUN_10006180`, `FUN_10006190`, and `FUN_10007063` should be inspected next to trace any further interactions with EEPROM persistence or error handling that might be indirectly related to state management.

---

## 55. `PortManager10.dll` — `FUN_10007063` (`10007063`)
- **Keywords:** has-strings
- **Strings:** `GetLastActivePopup, GetActiveWindow, MessageBoxA, user32.dll`

*(qwen2.5-coder:14b, 16.1s)*

1. **Role**: This function appears to load the `user32.dll` library and retrieves addresses for `MessageBoxA`, `GetActiveWindow`, and `GetLastActivePopup` functions. It then calls these functions to display a message box based on the active window and last active popup.

2. **EEPROM / Persistence Mechanism**: None / transport helper. The function does not directly interact with EEPROM or flash storage. It is more likely involved in user interface operations rather than state persistence mechanisms.

3. **Key Constants / Opcodes / Calls**:
   - `MessageBoxA`, `GetActiveWindow`, `GetLastActivePopup` from `user32.dll`.
   - `DAT_1000d13c`, `DAT_1000d140`, `DAT_1000d144` as pointers to the respective functions.
   - No specific opcodes or constants related to EEPROM or flash operations are observed.

4. **Next Bite**: Since this function is primarily focused on user interface operations, the next callees to inspect for EEPROM persistence should be those related to communication with the radio, such as functions that use the known opcodes like `0x0100` (ReadIsh), `0x0101` (WriteIsh), or `0x0106` (EnterMode/Session). These functions are more likely to handle the actual state persistence on the radio.

---

## 56. `PortManager10.dll` — `Unwind@10007bf0` (`10007bf0`)
- **Keywords:** named

*(qwen2.5-coder:14b, 13.9s)*

1. **Role**: The function `Unwind_10007bf0` appears to be a cleanup or finalization routine, as it calls another function `FUN_10001680` with a pointer to a structure located at `unaff_EBP - 0x134`.

2. **EEPROM / Persistence Mechanism**: The function itself does not directly interact with EEPROM or flash storage. It seems to be a transport helper or a part of a larger process that manages state persistence, possibly by cleaning up resources or ensuring that all necessary operations have been completed before the program exits or transitions to another state.

3. **Key Constants / Opcodes / Calls**: 
   - The function calls `FUN_10001680` with a pointer to a structure at `unaff_EBP - 0x134`.
   - No specific hex constants, opcodes, or error HRESULTs are directly visible in the provided code snippet.

4. **Next Bite**: To trace EEPROM persistence, the next callee to inspect is `FUN_10001680`. This function likely contains the actual logic for committing changes to EEPROM or handling state persistence, as it is called by `Unwind_10007bf0`.

---
