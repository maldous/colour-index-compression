# POSIX PAQ worker ownership

The same-CIX worker starts in a private process group. The supervisor observes
an exited direct child with `waitid(...WNOWAIT)`, terminates the group while
that PID is still reserved, then reaps the direct child. Cancellation, deadlines
and error cleanup use the same ownership boundary. Fallible cleanup retains
the child handle and attempts direct-child termination if group signaling fails.

Unix diagnostic pipes are nonblocking. A cleanup guard signals their readers
on every exit path; readers drain available bytes for at most 100 ms after
observing that signal and mark a forced cutoff as truncated. A descendant
that deliberately leaves the process group therefore cannot hold the pipe join
indefinitely. Process groups do not contain such escaped descendants; the test
fixture explicitly terminates its own escaped writer. An OS blocking wait for
an uninterruptible child is not given a strict wall-clock guarantee.

The frozen source in `jobs/paq-supervisor-freeze-v1` passed formatting,
all-target Clippy with warnings denied, and eight worker tests. Nine supervisor
tests passed in the first attempt; the opt-in provider fixture refused its
incomplete environment because the runner had not yet built the current CIX
executable. The original failure remains in `jobs/paq-supervisor-groups-v1`.

V2 continued the identical source and cache, built CIX first, and supplied all
three required provider variables together. All ten supervisor tests and the
real installed-provider archive fixture passed. Source and retained provider
identities stayed unchanged. This is Linux-local development-profile evidence;
it is not a final optimized build, broader platform support, a throughput
measurement, or RC51 acceptance.
