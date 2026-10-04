# Direct Cppcheck kernel diagnostic v1

This prerequisite runs after v18 and projection-v3. It invokes the same private
Cppcheck 2.13 runtime, config files, host-header mirror, compiler projection,
and evidence bound used by the adapter probe, but selects only the retained
decompressor compiler record. It starts no Sonar server. It requires compiler
normalization to report at least one GNU `typeof` spelling conversion and then
requires zero `unknownMacro` diagnostics in Cppcheck XML.
