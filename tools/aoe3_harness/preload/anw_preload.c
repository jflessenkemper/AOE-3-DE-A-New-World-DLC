/*
 * anw_preload.c — Linux LD_PRELOAD shared library for ANW harness input injection.
 *
 * Purpose: Bypass the Proton DLL injection blockade by injecting at the Linux
 * process level rather than the Windows DLL level.  This .so is loaded via
 * LD_PRELOAD into the Wine/Proton launch wrapper BEFORE pressure-vessel, so it
 * runs on the host Linux side and can call host tools (xdotool, spectacle).
 *
 * Architecture:
 *   1. Constructor function starts a background thread.
 *   2. Thread creates a Unix domain socket at the standard anwhook socket path
 *      (same path computation as dll_client.py so Python code is unchanged).
 *   3. Thread listens for line-protocol commands (same protocol as anw_hook.dll).
 *   4. Commands dispatched:
 *      PING          → PONG
 *      KEY <vk_hex>  → DISPLAY=:1 xdotool key --window <wid> <keysym>
 *      KEYTYPE <str> → DISPLAY=:1 xdotool type --window <wid> <str>
 *      CLICK <x> <y> → DISPLAY=:1 xdotool mousemove <x> <y> click 1
 *      MOVE <x> <y>  → DISPLAY=:1 xdotool mousemove <x> <y>
 *      SCREENSHOT <path> → spectacle --background --nonotify --fullscreen -o <path>
 *      STATE         → ALIVE pid=<PID> tick=0
 *      QUIT          → close pipe, exit thread
 *
 * Socket path: same as dll_client.py::get_pipe_socket_path() —
 *   /tmp/.wine-<uid>/server-<dev_minor_hex>-<inode_hex>/pipe/anwhook
 *
 * Note on gamescope window ID: the gamescope window on DISPLAY=:1 is
 * enumerated at startup and cached. Fallback WID: 0x1e00001 (confirmed by
 * calibration agent).
 *
 * Compilation (host GCC):
 *   gcc -shared -fPIC -O2 -o anw_preload.so anw_preload.c -lpthread
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <errno.h>
#include <signal.h>
#include <stdarg.h>

/* ---------------------------------------------------------------------------
 * Configuration
 * ---------------------------------------------------------------------------*/

/* Fallback gamescope window ID on DISPLAY=:1 (calibration session confirmed) */
#define GAMESCOPE_WID_FALLBACK "0x1e00001"

/* Socket path: /tmp/.wine-<uid>/server-<dev_minor>-<inode>/pipe/anwhook */
#define SOCKET_DIR_FMT  "/tmp/.wine-%d"
#define PIPE_SUBPATH    "/pipe/anwhook"

/* Buffer sizes */
#define CMD_BUF 4096
#define RESP_BUF 512

/* ---------------------------------------------------------------------------
 * Socket path computation (mirrors dll_client.py::get_pipe_socket_path)
 * ---------------------------------------------------------------------------*/

static char g_socket_path[512] = {0};
static volatile int g_quit = 0;

/* Find the wineserver directory: /tmp/.wine-<uid>/server-<dev>-<ino>
 * Matches the first server-* subdirectory. */
static int find_socket_path(const char *pfx_path) {
    char wine_dir[256];
    int uid = (int)getuid();
    snprintf(wine_dir, sizeof(wine_dir), SOCKET_DIR_FMT, uid);

    struct stat st;
    if (stat(pfx_path, &st) != 0) {
        fprintf(stderr, "[anw_preload] Cannot stat pfx: %s: %s\n", pfx_path, strerror(errno));
        return -1;
    }

    unsigned int dev_minor = (unsigned int)(st.st_dev & 0xffffff);  /* lower 24 bits */
    unsigned long inode = (unsigned long)st.st_ino;

    snprintf(g_socket_path, sizeof(g_socket_path),
             "%s/server-%x-%lx%s",
             wine_dir, dev_minor, inode, PIPE_SUBPATH);

    fprintf(stderr, "[anw_preload] Socket path: %s\n", g_socket_path);
    return 0;
}

/* ---------------------------------------------------------------------------
 * Command helpers
 * ---------------------------------------------------------------------------*/

static char g_wid[32] = GAMESCOPE_WID_FALLBACK;

/* Run a shell command and return exit code */
static int run_cmd(const char *fmt, ...) {
    char cmd[2048];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(cmd, sizeof(cmd), fmt, ap);
    va_end(ap);
    fprintf(stderr, "[anw_preload] exec: %s\n", cmd);
    int rc = system(cmd);
    return rc;
}

/* Map Windows virtual key codes to X11 keysyms for xdotool */
static const char *vk_to_keysym(unsigned int vk) {
    switch (vk) {
    case 0x08: return "BackSpace";
    case 0x09: return "Tab";
    case 0x0D: return "Return";
    case 0x1B: return "Escape";
    case 0x20: return "space";
    case 0x25: return "Left";
    case 0x26: return "Up";
    case 0x27: return "Right";
    case 0x28: return "Down";
    case 0x2E: return "Delete";
    case 0x30: return "0";
    case 0x31: return "1";
    case 0x32: return "2";
    case 0x33: return "3";
    case 0x34: return "4";
    case 0x35: return "5";
    case 0x36: return "6";
    case 0x37: return "7";
    case 0x38: return "8";
    case 0x39: return "9";
    case 0x41: return "a";
    case 0x42: return "b";
    case 0x43: return "c";
    case 0x44: return "d";
    case 0x45: return "e";
    case 0x46: return "f";
    case 0x47: return "g";
    case 0x48: return "h";
    case 0x49: return "i";
    case 0x4A: return "j";
    case 0x4B: return "k";
    case 0x4C: return "l";
    case 0x4D: return "m";
    case 0x4E: return "n";
    case 0x4F: return "o";
    case 0x50: return "p";
    case 0x51: return "q";
    case 0x52: return "r";
    case 0x53: return "s";
    case 0x54: return "t";
    case 0x55: return "u";
    case 0x56: return "v";
    case 0x57: return "w";
    case 0x58: return "x";
    case 0x59: return "y";
    case 0x5A: return "z";
    case 0x70: return "F1";
    case 0x71: return "F2";
    case 0x72: return "F3";
    case 0x73: return "F4";
    case 0x74: return "F5";
    case 0x75: return "F6";
    case 0x76: return "F7";
    case 0x77: return "F8";
    case 0x78: return "F9";
    case 0x79: return "F10";
    case 0x7A: return "F11";
    case 0x7B: return "F12";
    default:   return NULL;
    }
}

/* Parse unsigned hex or decimal integer */
static int parse_uint(const char *s, unsigned int *out) {
    if (s[0] == '0' && (s[1] == 'x' || s[1] == 'X')) {
        return sscanf(s + 2, "%x", out) == 1;
    }
    return sscanf(s, "%u", out) == 1;
}

/* ---------------------------------------------------------------------------
 * Command dispatcher
 * ---------------------------------------------------------------------------*/

/* Returns 1 if QUIT received, 0 otherwise */
static int dispatch_command(int fd, const char *cmd) {
    char resp[RESP_BUF];

    if (strcmp(cmd, "PING") == 0) {
        snprintf(resp, sizeof(resp), "PONG\r\n");
        write(fd, resp, strlen(resp));
        return 0;
    }

    if (strcmp(cmd, "STATE") == 0) {
        snprintf(resp, sizeof(resp), "ALIVE pid=%d tick=0\r\n", (int)getpid());
        write(fd, resp, strlen(resp));
        return 0;
    }

    if (strcmp(cmd, "QUIT") == 0) {
        snprintf(resp, sizeof(resp), "OK\r\n");
        write(fd, resp, strlen(resp));
        return 1;
    }

    /* KEY <vk_hex> */
    if (strncmp(cmd, "KEY_DOWN ", 9) == 0 || strncmp(cmd, "KEY_UP ", 7) == 0) {
        /* For simplicity, treat KEY_DOWN and KEY_UP same as KEY */
        const char *vk_str = strchr(cmd, ' ') + 1;
        unsigned int vk = 0;
        if (!parse_uint(vk_str, &vk)) {
            snprintf(resp, sizeof(resp), "ERR invalid vk\r\n");
            write(fd, resp, strlen(resp));
            return 0;
        }
        const char *ksym = vk_to_keysym(vk);
        if (ksym) {
            run_cmd("DISPLAY=:1 xdotool key --window %s %s", g_wid, ksym);
        } else {
            run_cmd("DISPLAY=:1 xdotool key --window %s 0x%02x", g_wid, vk);
        }
        snprintf(resp, sizeof(resp), "OK\r\n");
        write(fd, resp, strlen(resp));
        return 0;
    }

    if (strncmp(cmd, "KEY ", 4) == 0) {
        unsigned int vk = 0;
        if (!parse_uint(cmd + 4, &vk)) {
            snprintf(resp, sizeof(resp), "ERR invalid vk\r\n");
            write(fd, resp, strlen(resp));
            return 0;
        }
        const char *ksym = vk_to_keysym(vk);
        if (ksym) {
            run_cmd("DISPLAY=:1 xdotool key --window %s %s", g_wid, ksym);
        } else {
            run_cmd("DISPLAY=:1 xdotool key --window %s 0x%02x", g_wid, vk);
        }
        snprintf(resp, sizeof(resp), "OK\r\n");
        write(fd, resp, strlen(resp));
        return 0;
    }

    /* KEYTYPE <string> */
    if (strncmp(cmd, "KEYTYPE ", 8) == 0) {
        const char *text = cmd + 8;
        /* Safety: reject if text contains shell metacharacters */
        int safe = 1;
        for (const char *p = text; *p; p++) {
            if (*p == '\'' || *p == '\\' || *p == '$' || *p == '`' || *p == '"') {
                safe = 0;
                break;
            }
        }
        if (!safe) {
            snprintf(resp, sizeof(resp), "ERR unsafe string\r\n");
            write(fd, resp, strlen(resp));
            return 0;
        }
        run_cmd("DISPLAY=:1 xdotool type --window %s '%s'", g_wid, text);
        snprintf(resp, sizeof(resp), "OK\r\n");
        write(fd, resp, strlen(resp));
        return 0;
    }

    /* CLICK <x> <y> */
    if (strncmp(cmd, "CLICK ", 6) == 0) {
        int x = 0, y = 0;
        if (sscanf(cmd + 6, "%d %d", &x, &y) != 2) {
            snprintf(resp, sizeof(resp), "ERR expected CLICK <x> <y>\r\n");
            write(fd, resp, strlen(resp));
            return 0;
        }
        run_cmd("DISPLAY=:1 xdotool mousemove --window %s %d %d click 1", g_wid, x, y);
        snprintf(resp, sizeof(resp), "OK\r\n");
        write(fd, resp, strlen(resp));
        return 0;
    }

    /* MOVE <x> <y> */
    if (strncmp(cmd, "MOVE ", 5) == 0) {
        int x = 0, y = 0;
        if (sscanf(cmd + 5, "%d %d", &x, &y) != 2) {
            snprintf(resp, sizeof(resp), "ERR expected MOVE <x> <y>\r\n");
            write(fd, resp, strlen(resp));
            return 0;
        }
        run_cmd("DISPLAY=:1 xdotool mousemove --window %s %d %d", g_wid, x, y);
        snprintf(resp, sizeof(resp), "OK\r\n");
        write(fd, resp, strlen(resp));
        return 0;
    }

    /* SCREENSHOT <path> */
    if (strncmp(cmd, "SCREENSHOT ", 11) == 0) {
        const char *path = cmd + 11;
        /* Convert Z:\path to /path or use as-is if already Unix */
        char unix_path[512];
        if (path[0] == 'Z' && path[1] == ':') {
            /* Z:\foo\bar → /foo/bar */
            snprintf(unix_path, sizeof(unix_path), "%s", path + 2);
            /* Replace backslashes */
            for (char *p = unix_path; *p; p++) {
                if (*p == '\\') *p = '/';
            }
        } else {
            snprintf(unix_path, sizeof(unix_path), "%s", path);
        }
        /* Use spectacle for full-screen capture (confirmed working) */
        run_cmd("spectacle --background --nonotify --fullscreen --output '%s'", unix_path);
        snprintf(resp, sizeof(resp), "OK %s\r\n", unix_path);
        write(fd, resp, strlen(resp));
        return 0;
    }

    snprintf(resp, sizeof(resp), "ERR unknown command: %.200s\r\n", cmd);
    write(fd, resp, strlen(resp));
    return 0;
}

/* ---------------------------------------------------------------------------
 * Server thread
 * ---------------------------------------------------------------------------*/

static void *server_thread(void *arg) {
    (void)arg;

    /* Ensure socket directory exists */
    char dir[256];
    {
        char tmp[512];
        strncpy(tmp, g_socket_path, sizeof(tmp) - 1);
        tmp[sizeof(tmp) - 1] = '\0';
        /* Strip last component to get directory */
        char *last_slash = strrchr(tmp, '/');
        if (last_slash) {
            *last_slash = '\0';
            snprintf(dir, sizeof(dir), "%s", tmp);
            /* mkdir -p the directory */
            run_cmd("mkdir -p '%s'", dir);
        }
    }

    /* Remove stale socket */
    unlink(g_socket_path);

    int server_fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (server_fd < 0) {
        fprintf(stderr, "[anw_preload] socket() failed: %s\n", strerror(errno));
        return NULL;
    }

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, g_socket_path, sizeof(addr.sun_path) - 1);

    if (bind(server_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        fprintf(stderr, "[anw_preload] bind(%s) failed: %s\n", g_socket_path, strerror(errno));
        close(server_fd);
        return NULL;
    }

    if (listen(server_fd, 4) < 0) {
        fprintf(stderr, "[anw_preload] listen() failed: %s\n", strerror(errno));
        close(server_fd);
        return NULL;
    }

    /* Enumerate gamescope window */
    {
        char wid_out[64] = {0};
        FILE *fp = popen("DISPLAY=:1 xdotool search --class steam_app_933110 2>/dev/null | head -1", "r");
        if (fp) {
            if (fgets(wid_out, sizeof(wid_out), fp)) {
                wid_out[strcspn(wid_out, "\r\n")] = '\0';
                if (strlen(wid_out) > 2) {
                    snprintf(g_wid, sizeof(g_wid), "%s", wid_out);
                    fprintf(stderr, "[anw_preload] gamescope WID: %s\n", g_wid);
                }
            }
            pclose(fp);
        }
    }

    fprintf(stderr, "[anw_preload] Listening on %s (WID=%s)\n", g_socket_path, g_wid);

    /* Accept + serve loop */
    while (!g_quit) {
        int client_fd = accept(server_fd, NULL, NULL);
        if (client_fd < 0) {
            if (!g_quit) {
                fprintf(stderr, "[anw_preload] accept() failed: %s\n", strerror(errno));
            }
            break;
        }

        fprintf(stderr, "[anw_preload] Client connected\n");

        char buf[CMD_BUF];
        int pos = 0;
        char c;
        ssize_t n;

        while ((n = read(client_fd, &c, 1)) > 0) {
            if (c == '\r') continue;
            if (c == '\n') {
                buf[pos] = '\0';
                if (pos > 0) {
                    int done = dispatch_command(client_fd, buf);
                    if (done) {
                        g_quit = 1;
                        break;
                    }
                }
                pos = 0;
            } else if (pos < CMD_BUF - 1) {
                buf[pos++] = c;
            }
        }

        close(client_fd);
        fprintf(stderr, "[anw_preload] Client disconnected\n");
    }

    close(server_fd);
    unlink(g_socket_path);
    fprintf(stderr, "[anw_preload] Server thread exiting\n");
    return NULL;
}

/* ---------------------------------------------------------------------------
 * Constructor — runs when the .so is loaded
 * ---------------------------------------------------------------------------*/

__attribute__((constructor))
static void anw_preload_init(void) {
    /* Only activate for processes with GAMEID=933110 AND when we can acquire
     * the socket (only ONE process should be the server).  We bind eagerly —
     * if bind() fails because the socket already exists and is active, skip.
     * This naturally selects the first process that starts (umu-run itself). */
    const char *gameid = getenv("GAMEID");
    if (!gameid || strcmp(gameid, "933110") != 0) {
        return;
    }

    /* Only start ONE server. Use a persistent fd lock held for the lifetime of
     * the server process (flock on a file).  Child processes inherit the fd but
     * flock is per (file, process) pair so they get independent lock attempts. */
    const char *lock_path = "/tmp/anw_preload.lock";
    int lock_fd = open(lock_path, O_CREAT | O_WRONLY, 0600);
    if (lock_fd < 0) return;
    /* Non-blocking exclusive flock: only the first process wins */
    struct flock fl;
    fl.l_type   = F_WRLCK;
    fl.l_whence = SEEK_SET;
    fl.l_start  = 0;
    fl.l_len    = 1;
    if (fcntl(lock_fd, F_SETLK, &fl) < 0) {
        close(lock_fd);
        return;  /* Another process holds the lock */
    }
    /* Keep lock_fd open — lock held until this process exits */
    (void)lock_fd;

    fprintf(stderr, "[anw_preload] Activating for GAMEID=933110 (PID=%d)\n", (int)getpid());

    /* Compute socket path from WINEPREFIX */
    const char *pfx = getenv("WINEPREFIX");
    if (!pfx) {
        /* Default Proton prefix */
        static char default_pfx[512];
        const char *home = getenv("HOME");
        if (!home) home = "/home/jflessenkemper";
        snprintf(default_pfx, sizeof(default_pfx),
                 "%s/.local/share/Steam/steamapps/compatdata/933110/pfx", home);
        pfx = default_pfx;
    }

    if (find_socket_path(pfx) != 0) {
        fprintf(stderr, "[anw_preload] Failed to compute socket path — not starting server\n");
        return;
    }

    /* Spawn server thread */
    pthread_t tid;
    if (pthread_create(&tid, NULL, server_thread, NULL) != 0) {
        fprintf(stderr, "[anw_preload] pthread_create failed: %s\n", strerror(errno));
        return;
    }
    pthread_detach(tid);

    fprintf(stderr, "[anw_preload] Server thread spawned\n");
}

/* No destructor needed: lock is released automatically when the process exits
 * (kernel releases all advisory locks on fd close or process exit). */
