# CIX message source catalogs

Only English source text is required today. Actual translations are a separate
deliverable. `en.json` and `en/*.json` are the editable source; generated Rust
metadata is embedded into the native runtime, so it never invokes Python.

```json
{
  "schema": "cix-messages-v1",
  "locale": "en",
  "messages": {
    "service.example.failed": {
      "context": "Complete explanation of a failed operation; operation is an invariant ID.",
      "parameters": {"operation": "code"},
      "forms": {"other": "Operation {operation} failed"}
    }
  }
}
```

Use meaningful stable IDs, complete sentences, translator context and named
arguments. Parameter kinds are `text`, `code`, `path`, `number` and `message`.
For plurals supply `plural: "count"` naming a numeric argument and both English
`one` and `other` forms. Every form must use exactly the declared argument set.
Repeated/reordered arguments are allowed. Escape literal braces as `{{`/`}}`.
Do not translate code/option/route/status identifiers or mutate actual paths.

From the research repository root, run `python3 tools/i18n/catalog.py`; add
`--check` for schema/generated-drift validation. Never hand-edit
`src/i18n_catalog.rs`. Generation must precede the root-owned validation lease.
New service/SDK teams should own their own `en/<surface>.json` fragment and
coordinate regeneration of the single generated file.

The runtime `Catalog` interface accepts immutable host-owned translations,
plural rules, number formatting and text direction. The CLI currently selects
English. A callable interface and catalog source do not prove that every
application interaction has been migrated. See the repository's
`docs/INTERNATIONALIZATION.md` and dated coverage register for the remaining
requirements and the installed-source tooling contract.
