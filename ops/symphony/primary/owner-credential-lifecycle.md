Prepared owner handoff only; the agent has not acquired, provisioned or sent a key.

After the same CIX244 review and current-tree integration, the single nonsecret owner
command in their already configured authorized server shell is:

    bash /home/user/src/cix-approved-migration/config/owner-launch.sh

The command consumes the owner's existing LINEAR_API_KEY environment through stdin
to sudo, never a key value in argv/chat/Git/cloud. It does not inspect auth profiles.
It pins the reviewed host config, rejects an existing source or different primary unit,
creates root-owned directory0700 and file0400 at /run/cix-symphony-primary/linear-api-key,
installs the single SYSTEM unit and active workflow, then enables/starts the service.
It is owner-only code, not an instruction for the agent to run it. An uncertain or failed
command requires exact target readback before any repeat; do not silently replace a key.

This is a plaintext root-restricted source on /run, with a systemd service-scoped copy.
Root can read it; the native provider receives it in its environment. Existing native
tracker-secret filtering removes provider variables from spawned app-server environments;
live behavior is not yet qualified. The service runs as user and can read its delivered
credential. Same-UID/root access must not be described as a new cryptographic boundary.
No extra proxy, permanent home/profile credential or cloud auth copy is created.

Ordinary service stop/restart and supervisor retries preserve the /run source. No
ExecStop/Post deletes it. Revocation is an explicit owner action: first
`sudo systemctl disable --now cix-symphony-primary.service`, then verify MainPID=0 and
ControlGroup empty using `sudo systemctl show cix-symphony-primary.service -p MainPID
-p ControlGroup -p ActiveState`; only after confirmed stop remove the exact source with
`sudo rm -- /run/cix-symphony-primary/linear-api-key`. Reconcile any uncertain stop;
file removal alone is not a worker fence. The restricted empty directory may remain.

Host reboot clears /run. The enabled unit then lacks its source and cannot authenticate;
this handoff does NOT establish unattended host-reboot recovery. Owner secure reprovision
(or a separately approved supported persistent secure store) is required. No key is
saved elsewhere to hide that limitation. Revocation/expiry at Linear also requires
owner coordination and service stop. First actual outage and meaningful failure/stop
receipts belong in the existing Linear/native supervisor process, not a new daemon.

The one-hour cloud failover still requires real primary fencing/exclusive routing and
lower measured cloud capacity. This command and ephemeral key do not prove failover,
API persistence, issue-role/review/merge acceptance or full BAU.
