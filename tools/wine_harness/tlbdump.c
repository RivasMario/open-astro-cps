#define _WIN32_WINNT 0x0501
#include <windows.h>
#include <oleauto.h>
#include <stdio.h>
#include <wchar.h>

static const char* vt_name(VARTYPE vt) {
    switch (vt & VT_TYPEMASK) {
        case VT_EMPTY: return "VT_EMPTY";
        case VT_NULL: return "VT_NULL";
        case VT_I2: return "VT_I2";
        case VT_I4: return "VT_I4";
        case VT_R4: return "VT_R4";
        case VT_R8: return "VT_R8";
        case VT_CY: return "VT_CY";
        case VT_DATE: return "VT_DATE";
        case VT_BSTR: return "VT_BSTR";
        case VT_DISPATCH: return "VT_DISPATCH";
        case VT_ERROR: return "VT_ERROR";
        case VT_BOOL: return "VT_BOOL";
        case VT_VARIANT: return "VT_VARIANT";
        case VT_UNKNOWN: return "VT_UNKNOWN";
        case VT_I1: return "VT_I1";
        case VT_UI1: return "VT_UI1";
        case VT_UI2: return "VT_UI2";
        case VT_UI4: return "VT_UI4";
        case VT_I8: return "VT_I8";
        case VT_UI8: return "VT_UI8";
        case VT_INT: return "VT_INT";
        case VT_UINT: return "VT_UINT";
        case VT_VOID: return "VT_VOID";
        case VT_HRESULT: return "VT_HRESULT";
        case VT_PTR: return "VT_PTR";
        case VT_SAFEARRAY: return "VT_SAFEARRAY";
        case VT_CARRAY: return "VT_CARRAY";
        case VT_USERDEFINED: return "VT_USERDEFINED";
        case VT_LPSTR: return "VT_LPSTR";
        case VT_LPWSTR: return "VT_LPWSTR";
        default: return "VT_?";
    }
}

static void print_tdesc(TYPEDESC *td, char *buf, size_t bufsz) {
    if ((td->vt & VT_TYPEMASK) == VT_PTR) {
        char inner[64];
        print_tdesc(td->lptdesc, inner, sizeof(inner));
        snprintf(buf, bufsz, "PTR(%s)", inner);
    } else {
        snprintf(buf, bufsz, "%s%s", vt_name(td->vt), (td->vt & VT_BYREF) ? "|BYREF" : "");
    }
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: tlbdump <dllpath>\n"); return 1; }

    wchar_t wpath[1024];
    MultiByteToWideChar(CP_ACP, 0, argv[1], -1, wpath, 1024);

    HRESULT hr = CoInitialize(NULL);
    printf("CoInitialize: 0x%08lx\n", (long)hr);

    ITypeLib *pTypeLib = NULL;
    hr = LoadTypeLib(wpath, &pTypeLib);
    printf("LoadTypeLib: 0x%08lx\n", (long)hr);
    if (FAILED(hr)) return 1;

    UINT count = pTypeLib->lpVtbl->GetTypeInfoCount(pTypeLib);
    printf("TypeInfoCount: %u\n", count);

    for (UINT i = 0; i < count; i++) {
        BSTR name = NULL;
        pTypeLib->lpVtbl->GetDocumentation(pTypeLib, i, &name, NULL, NULL, NULL);
        wprintf(L"\n=== TypeInfo[%u]: %ls ===\n", i, name ? name : L"(null)");

        ITypeInfo *pTI = NULL;
        hr = pTypeLib->lpVtbl->GetTypeInfo(pTypeLib, i, &pTI);
        if (FAILED(hr)) continue;

        TYPEATTR *pAttr = NULL;
        hr = pTI->lpVtbl->GetTypeAttr(pTI, &pAttr);
        if (SUCCEEDED(hr)) {
            printf("  typekind=%d cFuncs=%d cVars=%d cImplTypes=%d\n",
                   pAttr->typekind, pAttr->cFuncs, pAttr->cVars, pAttr->cImplTypes);
            printf("  guid={%08lx-%04x-%04x-%02x%02x-%02x%02x%02x%02x%02x%02x}\n",
                   pAttr->guid.Data1, pAttr->guid.Data2, pAttr->guid.Data3,
                   pAttr->guid.Data4[0], pAttr->guid.Data4[1], pAttr->guid.Data4[2],
                   pAttr->guid.Data4[3], pAttr->guid.Data4[4], pAttr->guid.Data4[5],
                   pAttr->guid.Data4[6], pAttr->guid.Data4[7]);

            for (short f = 0; f < pAttr->cFuncs; f++) {
                FUNCDESC *pFD = NULL;
                hr = pTI->lpVtbl->GetFuncDesc(pTI, f, &pFD);
                if (FAILED(hr)) continue;

                BSTR names[16];
                UINT cNames = 0;
                pTI->lpVtbl->GetNames(pTI, pFD->memid, names, 16, &cNames);

                wprintf(L"  [%d] memid=0x%lx invkind=%d callconv=%d params=%d optional=%d vtbloff=%d funckind=%d  %ls(",
                        f, pFD->memid, pFD->invkind, pFD->callconv,
                        pFD->cParams, pFD->cParamsOpt, pFD->oVft, pFD->funckind,
                        cNames > 0 ? names[0] : L"?");

                for (short p = 0; p < pFD->cParams; p++) {
                    char tdbuf[64];
                    print_tdesc(&pFD->lprgelemdescParam[p].tdesc, tdbuf, sizeof(tdbuf));
                    USHORT pf = pFD->lprgelemdescParam[p].paramdesc.wParamFlags;
                    wprintf(L"%ls:%hs%s%s%s, ",
                            (p+1 < (short)cNames) ? names[p+1] : L"?",
                            tdbuf,
                            (pf & PARAMFLAG_FIN) ? " IN" : "",
                            (pf & PARAMFLAG_FOUT) ? " OUT" : "",
                            (pf & PARAMFLAG_FRETVAL) ? " RETVAL" : "");
                }
                char rettd[64];
                print_tdesc(&pFD->elemdescFunc.tdesc, rettd, sizeof(rettd));
                wprintf(L") -> %hs\n", rettd);

                pTI->lpVtbl->ReleaseFuncDesc(pTI, pFD);
            }
            pTI->lpVtbl->ReleaseTypeAttr(pTI, pAttr);
        }
        pTI->lpVtbl->Release(pTI);
    }

    pTypeLib->lpVtbl->Release(pTypeLib);
    CoUninitialize();
    return 0;
}
