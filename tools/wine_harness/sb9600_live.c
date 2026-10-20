#define _WIN32_WINNT 0x0501
#include <windows.h>
#include <oleauto.h>
#include <stdio.h>

#define CHECK(label, hr) printf("%-28s hr=0x%08lx\n", label, (long)(hr))

static HRESULT invoke(IDispatch *pDisp, DISPID id, VARIANTARG *args, UINT nargs, VARIANT *result) {
    DISPPARAMS dp = {0};
    dp.rgvarg = args;
    dp.cArgs = nargs;
    // VB/automation convention: args passed in REVERSE order in rgvarg
    VARIANT rev[8];
    for (UINT i = 0; i < nargs; i++) rev[i] = args[nargs - 1 - i];
    dp.rgvarg = rev;

    EXCEPINFO ei; memset(&ei, 0, sizeof(ei));
    UINT argErr = 0;
    VariantInit(result);
    HRESULT hr = pDisp->lpVtbl->Invoke(pDisp, id, &IID_NULL, LOCALE_SYSTEM_DEFAULT,
                                  DISPATCH_METHOD, &dp, result, &ei, &argErr);
    if (hr == DISP_E_EXCEPTION) {
        wprintf(L"  EXCEPINFO: code=%hu source=%ls desc=%ls scode=0x%08lx\n",
                ei.wCode, ei.bstrSource ? ei.bstrSource : L"(null)",
                ei.bstrDescription ? ei.bstrDescription : L"(null)", (long)ei.scode);
    } else if (hr == DISP_E_PARAMNOTFOUND || hr == DISP_E_TYPEMISMATCH) {
        printf("  argErr index: %u\n", argErr);
    }
    return hr;
}

static void print_variant_summary(const char *label, VARIANT *v) {
    printf("%s: vt=%u", label, v->vt);
    if (v->vt == VT_BSTR && v->bstrVal) {
        wprintf(L" bstr=\"%ls\"", v->bstrVal);
    } else if (v->vt == (VT_ARRAY | VT_UI1) && v->parray) {
        printf(" byte-array bytes=%lu: ", (unsigned long)v->parray->rgsabound[0].cElements);
        BYTE *p = (BYTE*)v->parray->pvData;
        for (unsigned i = 0; i < v->parray->rgsabound[0].cElements && i < 64; i++) printf("%02X ", p[i]);
    } else if (v->vt == VT_I4) {
        printf(" i4=%ld", (long)v->lVal);
    }
    printf("\n");
}

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: sb9600_live <device_com_port> <phase>\n  phase: open | portnames | epreq | close\n"); return 1; }
    char *comport = argv[1];
    char *phase = argv[2];

    CHECK("CoInitialize", CoInitialize(NULL));

    // Register the embedded typelib so standard-marshaled IDispatch::Invoke
    // calls can resolve parameter info. argv[3] (if given) is the dll path.
    if (argc >= 4) {
        wchar_t wdllpath[1024];
        MultiByteToWideChar(CP_ACP, 0, argv[3], -1, wdllpath, 1024);
        ITypeLib *pTL = NULL;
        HRESULT hrtl = LoadTypeLib(wdllpath, &pTL);
        CHECK("LoadTypeLib", hrtl);
        if (SUCCEEDED(hrtl)) {
            HRESULT hrreg = RegisterTypeLib(pTL, wdllpath, NULL);
            CHECK("RegisterTypeLib", hrreg);
            pTL->lpVtbl->Release(pTL);
        }
    }

    CLSID clsid;
    CHECK("CLSIDFromString", CLSIDFromString(L"{BB885C92-9093-11D3-A0A4-00108302D33D}", &clsid));

    IDispatch *pDisp = NULL;
    HRESULT hr = CoCreateInstance(&clsid, NULL, CLSCTX_INPROC_SERVER, &IID_IDispatch, (void**)&pDisp);
    CHECK("CoCreateInstance", hr);
    if (FAILED(hr) || !pDisp) return 1;

    if (strcmp(phase, "open") == 0) {
        wchar_t wport[64];
        MultiByteToWideChar(CP_ACP, 0, comport, -1, wport, 64);
        VARIANTARG args[2];
        VariantInit(&args[0]); args[0].vt = VT_BSTR; args[0].bstrVal = SysAllocString(wport);
        VariantInit(&args[1]); args[1].vt = VT_I4;   args[1].lVal = 0;
        VARIANT result;
        hr = invoke(pDisp, 0x7, args, 2, &result); // Open
        CHECK("Open()", hr);
    }
    else if (strcmp(phase, "portnames") == 0) {
        VARIANT result;
        hr = invoke(pDisp, 0x1, NULL, 0, &result); // GetPortNames, zero args
        CHECK("GetPortNames()", hr);
        if (SUCCEEDED(hr)) print_variant_summary("  result", &result);
    }
    else if (strcmp(phase, "epreq") == 0) {
        wchar_t wport[64];
        MultiByteToWideChar(CP_ACP, 0, comport, -1, wport, 64);
        VARIANTARG oargs[2];
        VariantInit(&oargs[0]); oargs[0].vt = VT_BSTR; oargs[0].bstrVal = SysAllocString(wport);
        VariantInit(&oargs[1]); oargs[1].vt = VT_I4;   oargs[1].lVal = 0;
        VARIANT oresult;
        hr = invoke(pDisp, 0x7, oargs, 2, &oresult); // Open
        CHECK("Open()", hr);
        if (FAILED(hr)) goto done;

        wchar_t wop[32] = L"EPREQ";
        VARIANTARG sargs[6];
        VariantInit(&sargs[0]); sargs[0].vt = VT_BSTR; sargs[0].bstrVal = SysAllocString(wop);
        VariantInit(&sargs[1]); sargs[1].vt = VT_EMPTY;              // tPacket - empty payload
        VariantInit(&sargs[2]); sargs[2].vt = VT_I4; sargs[2].lVal = 0; // lAddress
        VariantInit(&sargs[3]); sargs[3].vt = VT_I4; sargs[3].lVal = 0; // lDeviceMajor
        VariantInit(&sargs[4]); sargs[4].vt = VT_I4; sargs[4].lVal = 0; // lDeviceMinor
        VariantInit(&sargs[5]); sargs[5].vt = VT_I4; sargs[5].lVal = 0; // lGroup
        VARIANT sresult;
        printf("[*] Calling Send(\"EPREQ\", <empty>, 0,0,0,0) now...\n");
        fflush(stdout);
        hr = invoke(pDisp, 0xd, sargs, 6, &sresult); // Send
        CHECK("Send(EPREQ)", hr);

        VARIANT cresult;
        hr = invoke(pDisp, 0x6, NULL, 0, &cresult); // Close
        CHECK("Close()", hr);
    }
    else if (strcmp(phase, "close") == 0) {
        VARIANT result;
        hr = invoke(pDisp, 0x6, NULL, 0, &result); // Close
        CHECK("Close()", hr);
    }

done:
    pDisp->lpVtbl->Release(pDisp);
    CoUninitialize();
    return 0;
}
