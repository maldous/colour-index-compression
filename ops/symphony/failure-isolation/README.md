# CIX243 native failure isolation

This source patch applies to official Symphony revision 1c0fb6c8e8ef9031a2c861e62af5f9e66cee39cb. It extends the existing native orchestration/Linear adapter boundary; no separate scheduler, dispatcher, daemon or ledger is introduced. The implementation defaults off. Enabling requires a nonsecret source/workflow context and supported Linear comment read/create access. It appends compact identified failure events, verifies readback and reconciles before dispatch. Unknown writes, malformed/forked history and orphaned in-flight attempts hold dispatch. Three confirmed same failures block; permission denial blocks immediately. Normal continuation does not erase the failure streak. Human descriptions are never overwritten.

Apply the patch to the pinned source, then check source-manifest.json before compiling. The private delivery preserves patch and focused validation provenance; it does not activate the runtime. The old official binary alone does not include this change. Actual effective runtime must bind these changed modules and the source context before primary launch.

Focused checks used the retained official runtime in a bounded helper inside the existing system cix-bau139.slice. Current source compilation, direct state/API assertions and real Orchestrator GenServer/Task.Supervisor restart isolation passed using a fake provider. Standard ExUnit was unavailable and remains UNRUN. Live Linear/authentication, package activation and production service acceptance remain UNRUN. focused-receipt.json preserves prior failed attempts and actual stopped successful helper metrics. Retained detailed logs remain outside disposable workspaces on the managed host.

Authoritative issue comments are trusted work records, not protection against privileged deletion/forgery or competing native parents. One native mutation owner and normal technical custody remain required. An operator resolution uses a new explicit progress reference and exact current chain; ordinary reopen does not bypass a hold.

Tracking: https://linear.app/maldous/issue/CIX-243/eliquinn-persist-native-symphony-failure-isolation-across-restart
