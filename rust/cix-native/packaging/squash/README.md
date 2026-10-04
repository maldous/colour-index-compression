# Optional Squash plugin

This Linux-only helper builds the CIX shared library and a Squash 0.8 plugin
shim. It is intentionally separate from the base CIX command-line package.

Requirements:

- a completed native CIX build environment;
- Squash 0.8 development files discoverable as `squash-0.8` through
  `pkg-config`;
- a plugin-load, compression, restoration, and error-path test on the target
  host.

Build into Squash’s default plugin path:

```sh
./packaging/squash/build-plugin.sh
```

Set `SQUASH_PLUGIN_ROOT` for a user-writable plugin root. This preparation
candidate has not passed a local Squash SDK load test and must not be described
as a qualified Squash distribution.
