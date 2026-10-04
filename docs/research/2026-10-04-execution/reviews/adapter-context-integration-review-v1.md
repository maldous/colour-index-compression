# Adapter context integration review v1

Date: 2026-10-05
Scope: read-only review of the new six-TU Cppcheck projection integration in `tools/sonar-cxx/repair.py` and `translation_context.py`. No scan, build, test, or tool edit was performed for this review.

## Correction and completed integration evidence

The earlier assertion in this review that the prepared source was the native-subdirectory root was incorrect. `prepared-v6/plan.json` records the repository root as its `source`, and `cppcheck-adapter-context-v1/run.py` calls `repair.cppcheck(ROOT, ...)`. The historical readers-v3 paths therefore resolve correctly.

The completed `cppcheck-adapter-context-v1/receipt.json` records `pass_scoped_analysis`, six projected translation units, unchanged source and tool hashes, and an empty `fatal_configuration` object. Its projection receipts include the three historical userspace input bindings and label the kernel inputs `NEW_ANALYSIS_INPUT_FREEZE_NOT_HISTORICAL_BUILD_PROOF`. This establishes the bounded six-TU Cppcheck experiment; it does not establish full CXX qualification.

## Correct parts of the boundary

The projected compiler invocation has a read-only root and network namespace, with only the budgeted projection directory rebound writable. It pre-creates the destination, reserves the maximum external payload, applies the file-size limit, rejects unexpected stdout, and verifies the explicit bound inputs again before retaining the analyzer copy. The kernel fallback labels its hashes `NEW_ANALYSIS_INPUT_FREEZE_NOT_HISTORICAL_BUILD_PROOF`, which correctly avoids representing current kernel headers or stage copies as historical build evidence.

The context validator keeps the recorded source operand spelling while comparing resolved paths. This handles the retained double-slash SquashFS command without rewriting the invocation. It removes the recorded `-Wp,-MMD,<old-depfile>` output when converting the command to `-E`, and records that removal in the projection receipt.

The completed `sonar-tool-tests-v12` receipt records passing tool suites and unchanged frozen tool inputs. The separate adapter-context-v1 result adds the real six-TU integration evidence.

## Resolved dependency-output mapping concern

The v1 projection record retained the old kernel `-Wp,-MMD,.../.cix_profile_portable.o.d` option in its generated Cppcheck database even though preprocessing removed it. `cppcheck-adapter-context-v2` resolves that mismatch: its receipt records `old_dependency_outputs_absent_from_analyzer_database: true`, and its six-row `compile_commands.cppcheck.json` contains no `-Wp,-MMD` argument. It also retains an empty `fatal_configuration` object and unchanged source/tool hashes. The projected analyzer database now matches the suppressed old dependency-output policy.

## Future hardening

`preprocess_command` removes the one known `-Wp,-MMD,...` side effect but otherwise accepts the full recorded argv. The read-only root contains ordinary accidental output paths, but the parser should fail closed on other known write-producing compiler options (`-MD`, `-MMD`, `-MF`, `-save-temps`, `-ftime-trace`, and compiler/plugin pass-through output forms) unless an explicitly reviewed transform removes them. This prevents a later capture from turning an unfamiliar output option into a confusing preprocessing failure or a claim that the only writable destination was the projection directory.

Similarly, source operand validation counts operands resolving to the selected source but does not reject a second positional source or other non-option input. Reject an extra recognized source operand before preprocessing. The existing canonical replacement is correct for the selected source, but accepting an additional translation unit would make the projection and its one-source receipt ambiguous.

## Disposition

The six-TU integration completed with bounded read-only preprocessing, correctly labelled kernel input provenance, and a sanitized projected analyzer database. The experiment does not resolve the existing analysis gaps.
