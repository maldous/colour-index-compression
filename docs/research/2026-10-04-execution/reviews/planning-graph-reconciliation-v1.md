# Planning graph reconciliation v1

This note reconciles the execution crosswalk with the coordinator's
2026-10-05 review. It changes no ledger status, acceptance criterion, feature
scope, or benchmark gate.

## Edge types

`planning_prerequisite_edges` are construction inputs. They must be acyclic
after a coordinated construction cohort is treated as one node.
`acceptance_backedges` are final evidence relationships and must never be read
as start-order dependencies. RC51 remains the terminal acceptance gate with
its original 50 source requirements and `RC42-owned`, `RC54-sdk-runners`, and
`RC54-identities`.

The former RC02-to-RC19 and RC19-to-RC02 pair is now a S1 coordinated
construction cohort: RC02 starts after RC01, while RC19's clean-runtime audit
is retained as RC02 acceptance evidence. The former RC24/RC43/RC45 triangle is
now a construction chain into a coordinated acceptance cohort: RC24 prepares
installable SDK artifacts, RC43 prepares actual-platform qualification using
those artifacts and real runners, and RC45 prepares provenance/package scope.
Their final cross-checks remain required but do not form an execution cycle.
S4 no longer treats RC45 as a construction entry edge; its adapter evidence
returns to the RC43/RC45 acceptance cohort.

## Owned external obligations

The local crosswalk now gives the three ledger obligations explicit nodes,
owners, dependent IDs, promises and evidence targets. Their wording and
dependent IDs are copied from `requirements.json`; the owner split follows the
controlling direction: root supplies implementation/evidence and the
coordinator accepts against the ledger. `RC42-upstream` and
`RC54-registry-stock` remain conditional external claim gates. They are not
substitutes for current-RC owned work.

## Draft consistency check

No script was run for this note. A future read-only validator can parse
`dependency-blockers.json`, form a directed graph from stage entry edges plus
`planning_prerequisite_edges` and
`owned_external_obligation_nodes[].construction_prerequisite_edges`, then:

1. Collapse entries with `execution_mode=coordinated_construction_cohort`.
2. Reject any remaining cycle or edge to an unknown construction node.
3. Verify that `acceptance_backedges` are absent from that graph.
4. Verify RC51 still lists the 50 required source rows and exactly the three
   mandatory owned external obligations from `requirements.json`.

This validator would check planning consistency only. It cannot accept a
requirement, convert a missing SDK/runner into a waiver, or authorize a
benchmark.
