# Node declaration typecheck recipe

A retained TypeScript 5.8.3 compiler and Node declarations are available at
`/usr/local/lib/node_modules/netlify-cli/node_modules`. The root-dispatched
runner pins their identities and does not install dependencies. To run manually
from `rust/cix-native/bindings/node`:

```text
tsc --noEmit -p test/typed-consumer/tsconfig.json
```

The check covers the package name, `Buffer`-only input surface, numeric options
and capacities, stream progress, disposal/reset/cancellation, and the exposed
Decoder `flush` method. It does not load or build `cix_node.node`.
