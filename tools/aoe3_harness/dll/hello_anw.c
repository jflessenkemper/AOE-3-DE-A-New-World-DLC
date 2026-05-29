#include <windows.h>
#include <stdio.h>

static FILE *g_log = NULL;

static void open_log(void) {
    if (g_log) return;
    /* Try Z:\tmp (host /tmp), fall back to AppData\Local\Temp if sandboxed */
    g_log = fopen("Z:\\tmp\\anw_dll.log", "a");
    if (!g_log) g_log = fopen("C:\\users\\steamuser\\AppData\\Local\\Temp\\anw_dll.log", "a");
    if (g_log) {
        SYSTEMTIME st;
        GetLocalTime(&st);
        fprintf(g_log, "[%04d-%02d-%02d %02d:%02d:%02d] DLL loaded into PID %lu\n",
                st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond,
                GetCurrentProcessId());
        fflush(g_log);
    }
}

BOOL WINAPI DllMain(HINSTANCE hinst, DWORD reason, LPVOID reserved) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hinst);
        open_log();
    }
    return TRUE;
}
