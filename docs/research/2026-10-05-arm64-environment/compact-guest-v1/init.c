/* CIX ARM64 environment probe: minimal PID 1 for a generated validation guest. */
#include <stdio.h>
#include <stdlib.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <unistd.h>
#include <string.h>

int main(void) {
  setvbuf(stdout, NULL, _IONBF, 0);
  struct utsname system;
  int okay = mount("proc", "/proc", "proc", 0, NULL) == 0;
  okay = okay && uname(&system) == 0 && strcmp(system.machine, "aarch64") == 0;
  if (okay) printf("CIX_GUEST_KERNEL %s %s\n", system.release, system.machine);
  pid_t child = fork();
  if (child == 0) {
    execl("/probe-cpp", "/probe-cpp", (char *)NULL);
    _exit(127);
  }
  int status = 0;
  okay = okay && child > 0 && waitpid(child, &status, 0) == child;
  okay = okay && WIFEXITED(status) && WEXITSTATUS(status) == 0;
  puts(okay ? "CIX_ARM64_COMPACT_GUEST_PASS" : "CIX_ARM64_COMPACT_GUEST_FAIL");
  sync();
  reboot(RB_POWER_OFF);
  for (;;) pause();
}
