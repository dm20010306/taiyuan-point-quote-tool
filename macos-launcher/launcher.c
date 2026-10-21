#include <fcntl.h>
#include <errno.h>
#include <limits.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

static const char *SOURCE_DIR =
    "/Volumes/工作文件/Gopro/毛棋玉/态元智控知识库Vault/11_工具/"
    "智能图纸点位与报价工具";

static volatile sig_atomic_t runner_pid = -1;

static void forward_signal(int signal_number) {
    if (runner_pid > 0) {
        kill((pid_t)runner_pid, signal_number);
    }
}

static int copy_runner(const char *source, const char *destination) {
    char temporary[PATH_MAX];
    snprintf(temporary, sizeof(temporary), "%s.tmp", destination);
    int input = open(source, O_RDONLY);
    if (input < 0) {
        return -1;
    }
    int output = open(temporary, O_WRONLY | O_CREAT | O_TRUNC, 0700);
    if (output < 0) {
        close(input);
        return -1;
    }

    char buffer[16384];
    ssize_t count;
    int result = 0;
    while ((count = read(input, buffer, sizeof(buffer))) > 0) {
        ssize_t offset = 0;
        while (offset < count) {
            ssize_t written = write(output, buffer + offset, (size_t)(count - offset));
            if (written < 0) {
                result = -1;
                break;
            }
            offset += written;
        }
        if (result < 0) {
            break;
        }
    }
    if (count < 0) {
        result = -1;
    }
    close(input);
    if (close(output) < 0) {
        result = -1;
    }
    if (result == 0 && rename(temporary, destination) < 0) {
        result = -1;
    }
    if (result < 0) {
        unlink(temporary);
    }
    return result;
}

int main(void) {
    char shared_runner[PATH_MAX];
    snprintf(shared_runner, sizeof(shared_runner), "%s/macos-launcher/run-macos.zsh.txt", SOURCE_DIR);
    if (access(shared_runner, R_OK) != 0) {
        execl("/usr/bin/osascript", "osascript", "-e",
              "display alert \"找不到项目\" message \"请先连接工作文件服务器，再重新打开启动器。\" as critical",
              (char *)NULL);
        return 1;
    }

    const char *home = getenv("HOME");
    char local_runner[PATH_MAX];
    if (home != NULL) {
        char log_dir[PATH_MAX];
        char log_path[PATH_MAX];
        char cache_dir[PATH_MAX];
        snprintf(log_dir, sizeof(log_dir), "%s/Library/Logs/TaiyuanPointQuote", home);
        mkdir(log_dir, 0755);
        snprintf(log_path, sizeof(log_path), "%s/launcher.log", log_dir);
        int log_fd = open(log_path, O_WRONLY | O_CREAT | O_APPEND, 0644);
        if (log_fd >= 0) {
            dup2(log_fd, STDOUT_FILENO);
            dup2(log_fd, STDERR_FILENO);
            close(log_fd);
        }
        snprintf(cache_dir, sizeof(cache_dir), "%s/Library/Caches/TaiyuanPointQuote", home);
        mkdir(cache_dir, 0755);
        snprintf(local_runner, sizeof(local_runner), "%s/run-macos.command", cache_dir);
        if (copy_runner(shared_runner, local_runner) < 0) {
            dprintf(STDERR_FILENO, "无法同步本机启动脚本：%s\n", strerror(errno));
            return 1;
        }
    } else {
        return 1;
    }

    setenv("POINT_QUOTE_SOURCE_DIR", SOURCE_DIR, 1);

    /* Keep the Mach-O app process alive. Replacing it with zsh causes
       LaunchServices to lose ownership and may terminate the runner later. */
    pid_t child = fork();
    if (child < 0) {
        return 1;
    }
    if (child == 0) {
        execl("/bin/zsh", "zsh", local_runner, (char *)NULL);
        _exit(1);
    }

    runner_pid = child;
    struct sigaction action = {0};
    action.sa_handler = forward_signal;
    sigemptyset(&action.sa_mask);
    sigaction(SIGTERM, &action, NULL);
    sigaction(SIGINT, &action, NULL);
    sigaction(SIGHUP, &action, NULL);

    int status = 0;
    while (waitpid(child, &status, 0) < 0) {
        if (errno != EINTR) {
            return 1;
        }
    }
    runner_pid = -1;
    return WIFEXITED(status) ? WEXITSTATUS(status) : 1;
}
