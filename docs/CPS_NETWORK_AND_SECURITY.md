# CPS Network Programming & Security Subsystems

The "interesting but previously unopened" DLLs, now gone through. These are
**separate from the local-USB codeplug path** (`NextGen10`→`ByteData10`→
`RadioCustStack10`): they are the **network/OTAP programming** variant and the
**CPS feature-licensing** layer.

## 1. Network Radio Programmer (.NET Remoting) — the "program over a network" path

`NetworkRadioProg_DLLs/` is a **.NET Remoting** client/server that mirrors the
RCMP codeplug operations over a network channel (this is the real mechanism
behind the `CRemotePcIntranet` / proxy ports 8000/8003 seen in `ByteData10`).

* **`NetVRClientLib.dll`** (.NET) — `INetVRClient` / `INetVRLib` with the op set
  mirroring RCMP: `NetOpen`, `NetClose`, `NetReadBytesFromRadio`, `NetReadIshList`,
  `NetReadIshIDSet`, `NetDelCodeplug`, `NetDelIshItem`, `NetDelIshTypes`,
  `NetGetRadioUUID`, **`NetGetRadioPassword`**, `NetGetFlashCode`, `NetGetVersion`,
  `NetCbiRadio`. Uses `BinaryServerFormatterSinkProvider` + a custom encryption
  sink. **Note:** `NetGetRadioPassword` — the radio exposes a *password* in
  addition to the UUID; worth remembering for the auth model.
* **`INetVR.dll`** (.NET) — the remoting interface definitions.
* **`Interop.NEXTGENLib.dll`** (.NET) — COM interop wrapper around `NextGen10.dll`
  (the native RCMP engine), i.e. the .NET side calls the same native
  `CRcmpBundler` under the hood.
* **`EncryptionSink.dll`** (.NET) — encrypts the remoting channel:
  `EncryptionClientSink`/`EncryptionServerSink`, `CreateEncryptor`/`CreateDecryptor`,
  `CryptoStream`, `GetEncryptionAlgorithm`/`GetEncryptionKey`, `_encryptionKey`/
  `_encryptionIV`. Algorithm literal present: **`DES`**. So the channel is
  DES-encrypted (weak — transport obfuscation, not real security). Key/IV come
  from `GetEncryptionKey`/`_encryptionIV` (not a plain literal in strings; derived
  or resource-held — would need the .NET IL to extract exactly).

Takeaway: the network path is the **same codeplug protocol** wrapped in .NET
remoting + DES channel crypto. For OpenAstro's purposes the local USB/TCP path we
fully mapped is simpler and sufficient; this documents the alternative.

## 2. `authAES.dll` (native) — AES auth/encrypt helper

Exports `_encrypt_function@12`, `_decrypt_function@12`,
`_shuming_encrypt_validation@0` (plus internal `auth_key_encrypt`). "shuming" is
a developer name left in a validation symbol. `encrypt_function` (`0x10001C50`)
is a thin 3-arg wrapper that packs mode params (`0x300030`, `0x100010`,
`0x300000`) and calls the real AES core at `0x10001a20`. A standalone native AES
encrypt/decrypt + validation utility used for an internal auth step (not the
voice/codeplug crypto). Exact key/mode would need tracing `0x10001a20`; not
pursued (marginal).

## 3. Feature licensing — `SECURITYLIB.dll` / `Security.exe` / `CPSFeatures.enc`

The CPS **entitlement / feature-level gate** (what the logged-in user is allowed
to do in CPS — not radio crypto):

* **`SECURITYLIB.dll`** — `CSecurityObj` with `IsFeatureAccessible`,
  `IsFeatureFullyAccessible`, `IsFeaturePartof`, `IsSecurityEnabled`,
  `GetFeaturesFilePath`, `CPSFeatures`. Uses Windows CryptoAPI
  (`CryptCreateHash`/`CryptHashData`) — it hashes a feature password/secret and
  checks it against the features file. Also sets registry/file ACLs
  (`SetSecurityDescriptorDacl`, `RegSetKeySecurity`) to lock the entitlement.
* **`Security.exe`** — the admin tool for it (imports `SECURITYLIB.dll` +
  `NETAPI32`).
* **`FeatureLevelPassword/CPSFeatures.enc`** — the encrypted features/entitlement
  file `GetFeaturesFilePath` points at.

Relevance: this is the "unlock all CPS features" surface. It gates the *CPS app*,
not the radio — irrelevant to OpenAstro's own tooling (we don't run CPS), but
documented since it was flagged.

## 4. Others

* **`EncatenComponent.dll`** (native, self-reg COM; imports ole32/advapi32) —
  "Encaten" = concatenate; a COM component for assembling/concatenating the
  codeplug image (ProgID `IBENCATENCOMPONENTL…`, registers under HKEY). Codeplug
  image build helper. Not deep-dissected.
* **`OtapRWCDTimer.dll` / `OtapRWCDTimerExe.exe`** — OTAP (Over-The-Air
  Programming) read/write/config-data timing. Minor; relevant only to the network
  path above.

## Net effect on OpenAstro

None of this changes the core local path we reimplement (USB→AT→PPP→TCP:8002→
RCMP). It documents: (a) a network/.NET-remoting programming variant exists
(DES-wrapped, same ops), (b) the radio has a *password* as well as a UUID, (c)
CPS has its own feature-licensing (not our concern), (d) `authAES` is an internal
AES auth helper. The `NetGetRadioPassword` fact is the one worth carrying into the
auth model when we test writes.
