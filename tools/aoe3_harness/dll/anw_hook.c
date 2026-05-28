/*
 * anw_hook.c — DllMain, worker thread, and named pipe server.
 *
 * Implements §1 (DllMain + worker thread) and §4 (named pipe protocol) of
 * artifacts/harness_design/phase2_dll_architecture.md.
 *
 * DLL lifecycle:
 *   DLL_PROCESS_ATTACH → DisableThreadLibraryCalls, EAC guard, spawn worker
 *   DLL_PROCESS_DETACH → MH_DisableHook, MH_Uninitialize, close pipe
 *
 * Worker thread:
 *   1. Open log to Z:\tmp\anw_hook.log
 *   2. MH_Initialize()
 *   3. dxgi_hook_init() — installs Present hook (or stub if not compiled in)
 *   4. CreateNamedPipeW(\\.\pipe\anwhook, ...)
 *   5. Loop: ConnectNamedPipe → dispatch_command() → DisconnectNamedPipe
 *   6. On QUIT command: exit loop, close pipe
 *
 * Named pipe protocol (§4):
 *   Commands are \r\n-terminated lines. Responses are \r\n-terminated lines.
 *   One connection per command session; the pipe is recreated after disconnect.
 *   Pipe handle is kept open across commands within a session until EOF or QUIT.
 *
 * Anti-cheat guard (§10.1):
 *   DllMain returns FALSE if EasyAntiCheat.dll is loaded, preventing the DLL
 *   from attaching in multiplayer sessions where EAC is active.
 */

#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

#include "minhook/include/MinHook.h"
#include "anw_input.h"
#include "anw_dxgi_hook.h"

/* -------------------------------------------------------------------------
 * Constants
 * -------------------------------------------------------------------------*/

#define PIPE_NAME       L"\\\\.\\pipe\\anwhook"
#define LOG_PATH        "Z:\\tmp\\anw_hook.log"
#define PIPE_BUF_SIZE   4096
#define CMD_BUF_SIZE    1024
#define RESP_BUF_SIZE   512

/* KEY press gap in milliseconds (between KEY_DOWN and KEY_UP for KEY command) */
#define KEY_PRESS_DELAY_MS  50

/* -------------------------------------------------------------------------
 * Module globals
 * -------------------------------------------------------------------------*/

static HANDLE g_pipe_handle  = INVALID_HANDLE_VALUE;
static HANDLE g_worker_thread = NULL;
static volatile LONG g_quit  = 0;  /* set to 1 by QUIT command */

/* -------------------------------------------------------------------------
 * Logging helpers
 * -------------------------------------------------------------------------*/

static void log_write(const char *fmt, ...) {
    FILE *fp = fopen(LOG_PATH, "a");
    if (!fp) return;

    /* Timestamp */
    SYSTEMTIME st;
    GetLocalTime(&st);
    fprintf(fp, "[%04d-%02d-%02d %02d:%02d:%02d] ",
            st.wYear, st.wMonth, st.wDay,
            st.wHour, st.wMinute, st.wSecond);

    va_list ap;
    va_start(ap, fmt);
    vfprintf(fp, fmt, ap);
    va_end(ap);

    fprintf(fp, "\n");
    fclose(fp);
}

/* -------------------------------------------------------------------------
 * Pipe I/O helpers
 * -------------------------------------------------------------------------*/

/*
 * pipe_readline() — Read a \r\n-terminated line from the pipe into buf.
 * Returns number of bytes read (excluding \r\n), or -1 on error/EOF.
 * buf is always null-terminated on success.
 */
static int pipe_readline(HANDLE pipe, char *buf, int buf_size) {
    int pos = 0;
    char c;
    DWORD n;

    while (pos < buf_size - 1) {
        if (!ReadFile(pipe, &c, 1, &n, NULL) || n == 0) {
            return -1;
        }
        if (c == '\r') {
            /* Consume \n */
            ReadFile(pipe, &c, 1, &n, NULL);
            buf[pos] = '\0';
            return pos;
        }
        if (c == '\n') {
            buf[pos] = '\0';
            return pos;
        }
        buf[pos++] = c;
    }
    buf[pos] = '\0';
    return pos;
}

/*
 * pipe_writeline() — Write a \r\n-terminated response to the pipe.
 * Returns non-zero on success.
 */
static int pipe_writeline(HANDLE pipe, const char *resp) {
    char buf[RESP_BUF_SIZE];
    int len = (int)snprintf(buf, sizeof(buf) - 2, "%s", resp);
    buf[len]     = '\r';
    buf[len + 1] = '\n';

    DWORD written;
    return WriteFile(pipe, buf, (DWORD)(len + 2), &written, NULL) && written == (DWORD)(len + 2);
}

/* -------------------------------------------------------------------------
 * Command parsing helpers
 * -------------------------------------------------------------------------*/

/* Parse a hex integer like "0x57" or "57" into *out.  Returns 1 on success. */
static int parse_hex(const char *s, unsigned int *out) {
    if (s[0] == '0' && (s[1] == 'x' || s[1] == 'X')) {
        return sscanf(s + 2, "%x", out) == 1;
    }
    return sscanf(s, "%x", out) == 1;
}

/* -------------------------------------------------------------------------
 * Command dispatcher
 * -------------------------------------------------------------------------*/

/*
 * dispatch_command() — Parse and execute one pipe command line.
 *
 * cmd:  null-terminated command string (the \r\n has already been stripped).
 * pipe: open pipe handle for writing the response.
 *
 * Returns:
 *   0  — command handled; loop should continue
 *   1  — QUIT received; loop should exit
 */
static int dispatch_command(HANDLE pipe, const char *cmd) {
    log_write("[pipe] cmd: %s", cmd);

    /* ---- STATE --------------------------------------------------------- */
    if (strcmp(cmd, "STATE") == 0) {
        char resp[RESP_BUF_SIZE];
        snprintf(resp, sizeof(resp), "ALIVE pid=%lu tick=0", (unsigned long)GetCurrentProcessId());
        pipe_writeline(pipe, resp);
        return 0;
    }

    /* ---- QUIT ---------------------------------------------------------- */
    if (strcmp(cmd, "QUIT") == 0) {
        pipe_writeline(pipe, "OK");
        log_write("[pipe] QUIT received — worker exiting");
        return 1;
    }

    /* ---- KEY_DOWN <vk_hex> --------------------------------------------- */
    if (strncmp(cmd, "KEY_DOWN ", 9) == 0) {
        unsigned int vk = 0;
        if (!parse_hex(cmd + 9, &vk) || vk == 0 || vk > 0xFF) {
            pipe_writeline(pipe, "ERR invalid vk");
            return 0;
        }
        inject_key((WORD)vk, TRUE);
        pipe_writeline(pipe, "OK");
        return 0;
    }

    /* ---- KEY_UP <vk_hex> ----------------------------------------------- */
    if (strncmp(cmd, "KEY_UP ", 7) == 0) {
        unsigned int vk = 0;
        if (!parse_hex(cmd + 7, &vk) || vk == 0 || vk > 0xFF) {
            pipe_writeline(pipe, "ERR invalid vk");
            return 0;
        }
        inject_key((WORD)vk, FALSE);
        pipe_writeline(pipe, "OK");
        return 0;
    }

    /* ---- KEY <vk_hex> -------------------------------------------------- */
    if (strncmp(cmd, "KEY ", 4) == 0) {
        unsigned int vk = 0;
        if (!parse_hex(cmd + 4, &vk) || vk == 0 || vk > 0xFF) {
            pipe_writeline(pipe, "ERR invalid vk");
            return 0;
        }
        inject_key((WORD)vk, TRUE);
        Sleep(KEY_PRESS_DELAY_MS);
        inject_key((WORD)vk, FALSE);
        pipe_writeline(pipe, "OK");
        return 0;
    }

    /* ---- CLICK <x> <y> ------------------------------------------------- */
    if (strncmp(cmd, "CLICK ", 6) == 0) {
        int x = 0, y = 0;
        if (sscanf(cmd + 6, "%d %d", &x, &y) != 2) {
            pipe_writeline(pipe, "ERR expected CLICK <x> <y>");
            return 0;
        }
        inject_click(x, y);
        pipe_writeline(pipe, "OK");
        return 0;
    }

    /* ---- MOVE <x> <y> -------------------------------------------------- */
    if (strncmp(cmd, "MOVE ", 5) == 0) {
        int x = 0, y = 0;
        if (sscanf(cmd + 5, "%d %d", &x, &y) != 2) {
            pipe_writeline(pipe, "ERR expected MOVE <x> <y>");
            return 0;
        }
        inject_move(x, y);
        pipe_writeline(pipe, "OK");
        return 0;
    }

    /* ---- SCREENSHOT <path> --------------------------------------------- */
    if (strncmp(cmd, "SCREENSHOT ", 11) == 0) {
        const char *path = cmd + 11;
        int rc = dxgi_request_screenshot(path);
        if (rc == -1) {
            pipe_writeline(pipe, "ERR DXGI_NOT_IMPLEMENTED");
        } else if (rc == -2) {
            pipe_writeline(pipe, "ERR path too long");
        } else {
            /* Use CMD_BUF_SIZE (1024) to accommodate long paths without truncation */
            char resp[CMD_BUF_SIZE];
            /* Block until screenshot is done (Present hook clears the flag) */
            int waited = 0;
            while (dxgi_screenshot_pending() && waited < 5000) {
                Sleep(10);
                waited += 10;
            }
            if (dxgi_screenshot_pending()) {
                pipe_writeline(pipe, "ERR SCREENSHOT timeout");
            } else {
                snprintf(resp, sizeof(resp), "OK %s", path);
                pipe_writeline(pipe, resp);
            }
        }
        return 0;
    }

    /* ---- Unknown command ----------------------------------------------- */
    char resp[RESP_BUF_SIZE];
    snprintf(resp, sizeof(resp), "ERR unknown command: %.200s", cmd);
    pipe_writeline(pipe, resp);
    return 0;
}

/* -------------------------------------------------------------------------
 * Worker thread
 * -------------------------------------------------------------------------*/

static DWORD WINAPI worker_thread(LPVOID param) {
    (void)param;

    log_write("anw_hook.dll loaded into PID %lu — worker thread started",
              (unsigned long)GetCurrentProcessId());

    /* Initialize MinHook */
    MH_STATUS mh = MH_Initialize();
    if (mh != MH_OK) {
        log_write("[worker] MH_Initialize failed: %d", (int)mh);
        /* Non-fatal for SendInput functionality — continue without hooks */
    } else {
        log_write("[worker] MinHook initialized");
    }

    /* Install DXGI Present hook (or log stub message) */
    int dxgi_rc = dxgi_hook_init();
    if (dxgi_rc != 0) {
        log_write("[worker] dxgi_hook_init returned %d — screenshots unavailable", dxgi_rc);
    }

    /* Named pipe server loop */
    log_write("[worker] Creating named pipe: " "\\\\.\\pipe\\anwhook");

    while (!InterlockedCompareExchange(&g_quit, 0, 0)) {
        /* Create the pipe (recreated each connection cycle) */
        HANDLE pipe = CreateNamedPipeW(
            PIPE_NAME,
            PIPE_ACCESS_DUPLEX,
            PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
            1,                /* max instances */
            PIPE_BUF_SIZE,    /* out buffer */
            PIPE_BUF_SIZE,    /* in buffer */
            0,                /* default timeout */
            NULL              /* default security */
        );

        if (pipe == INVALID_HANDLE_VALUE) {
            DWORD err = GetLastError();
            log_write("[worker] CreateNamedPipeW failed: error %lu", (unsigned long)err);
            Sleep(1000);
            continue;
        }

        g_pipe_handle = pipe;
        log_write("[worker] Pipe created, waiting for client...");

        /* Block until a client connects */
        BOOL connected = ConnectNamedPipe(pipe, NULL);
        if (!connected && GetLastError() != ERROR_PIPE_CONNECTED) {
            log_write("[worker] ConnectNamedPipe failed: error %lu",
                      (unsigned long)GetLastError());
            CloseHandle(pipe);
            g_pipe_handle = INVALID_HANDLE_VALUE;
            continue;
        }

        log_write("[worker] Client connected");

        /* Serve commands until the client disconnects or sends QUIT */
        char cmd_buf[CMD_BUF_SIZE];
        while (1) {
            int n = pipe_readline(pipe, cmd_buf, sizeof(cmd_buf));
            if (n < 0) {
                log_write("[worker] Client disconnected");
                break;
            }
            if (n == 0) continue;  /* empty line */

            int done = dispatch_command(pipe, cmd_buf);
            if (done) {
                InterlockedExchange(&g_quit, 1);
                break;
            }
        }

        DisconnectNamedPipe(pipe);
        CloseHandle(pipe);
        g_pipe_handle = INVALID_HANDLE_VALUE;
    }

    log_write("[worker] Worker thread exiting");

    /* Cleanup */
    dxgi_hook_cleanup();
    MH_DisableHook(MH_ALL_HOOKS);
    MH_Uninitialize();

    return 0;
}

/* -------------------------------------------------------------------------
 * DllMain
 * -------------------------------------------------------------------------*/

BOOL WINAPI DllMain(HINSTANCE hinst, DWORD reason, LPVOID reserved) {
    switch (reason) {
    case DLL_PROCESS_ATTACH:
        /* EAC guard: refuse to load in multiplayer sessions (§10.1) */
        if (GetModuleHandleW(L"EasyAntiCheat.dll") != NULL) {
            /* Silently decline — do NOT hook in multiplayer */
            return FALSE;
        }

        DisableThreadLibraryCalls(hinst);

        /* Spawn worker thread — DllMain must NOT block */
        g_worker_thread = CreateThread(NULL, 0, worker_thread, NULL, 0, NULL);
        if (g_worker_thread == NULL) {
            /* Failed to spawn; DLL can still load but won't serve pipe commands */
            return TRUE;
        }
        break;

    case DLL_PROCESS_DETACH:
        /* Signal worker to stop */
        InterlockedExchange(&g_quit, 1);

        /* Close any open pipe so ConnectNamedPipe unblocks */
        if (g_pipe_handle != INVALID_HANDLE_VALUE) {
            CancelIoEx(g_pipe_handle, NULL);
        }

        /* Brief wait for worker to clean up (avoid dangling MH hooks) */
        if (g_worker_thread) {
            WaitForSingleObject(g_worker_thread, 2000);
            CloseHandle(g_worker_thread);
            g_worker_thread = NULL;
        }
        break;

    default:
        break;
    }

    return TRUE;
}
