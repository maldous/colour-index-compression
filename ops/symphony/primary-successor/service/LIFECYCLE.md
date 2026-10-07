Successor owner handoff — PREPARED, NOT PROVISIONED OR ACTIVE.

Matthew's actual redacted 7 October14:53:58UTC read proves LINEAR_API_KEY accesses
viewerba297b04, CIX team5b9076d9 and exact Managed service project852dfec6/slug1cad16b1273d
with CIX244 visible. Write capability remains NOT_TESTED. This is an attributed owner
receipt, not an agent key read or a CIX_LINEAR_API_KEY comparison. Selection is explicit.

After focused Quinn review and ordinary private integration, the one owner command is:

    bash /home/user/src/cix-approved-migration/successor-preparation/service/owner-launch.sh LINEAR_API_KEY

Run only in the owner's already configured authorized foo shell. The selected existing
variable is passed through builtin printf/stdin, never a secret in argv, log, chat or Git.
Only its nonsecret name is an argument. No profile sourcing, new key, proxy or agent
acquisition/provision is authorized. The old presented /run launcher remains unchanged;
use the reviewed successor command as the new handoff, not both commands.

The provisioner rejects an active primary, different installed unit, existing credential,
or prior ephemeral source. It pins successor config and the public runtime, creates only
root-owned0700 /etc/cix-symphony-primary and0400 linear-api-key, installs/enables/starts
ONE existing SYSTEM cix-symphony-primary.service in the existing aggregate. Any uncertain
failure requires exact target readback before a retry. Key source persists after a
failed start; no automatic deletion or silent replacement. Agent never executes it.

Access/persistence: root-restricted PLAINTEXT on persistent /etc, including possible
backups/disk snapshots. Root can read it; systemd gives the service a scoped copy and
the native provider receives its environment. Same UID/root access is not a new
cryptographic boundary. Existing provider filtering is unchanged source evidence,
not newly demonstrated live worker secrecy. No credential values are retained in Git
or cloud. Owner determines appropriate backup access/retention and provider scope.

Ordinary restart AND reboot retain the /etc source. The public runtime's 16 affected
ELFs now use exact retained musl bytes from stable runtime-cix243-v2/libexec/ld-musl.so,
with needed libraries/rpaths unchanged and all accepted BEAMs unchanged. All24 ELF
interpreters were inventoried; none uses /tmp. One initial missing-entry probe failed
before startup, corrected by copying the unchanged official entry. Affected official
argv/effective configuration checks passed without app/tracker/API startup. No old
loader/file was removed. Public-only runtime construction is not an actual reboot test.

Revocation: owner runs `sudo systemctl disable --now cix-symphony-primary.service`, then
`sudo systemctl show cix-symphony-primary.service -p MainPID -p ControlGroup -p ActiveState`.
Require MainPID0/ControlGroupempty/confirmed stop before removing exact persistent source:
`sudo rm -- /etc/cix-symphony-primary/linear-api-key`. Coordinate Linear revocation and
backup retention. Deleting the source alone is not a fence; uncertain stop remains held.
The stopped systemd credential copy is released by systemd; restricted empty directory
may remain. No automatic per-stop deletion that breaks supervisor recovery.

Actual boot/service startup, live read/write persistence, worker roles/Quinn/serialized
merge/retention and one-hour fenced cloud failover remain unqualified. Existing4GBhold,
239 unresolved,240241Canceled denials, public holds and ordinary workspace security stay.
