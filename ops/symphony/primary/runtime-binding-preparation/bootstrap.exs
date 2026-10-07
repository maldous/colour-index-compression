# Prepared entry only. The technical owner separately binds actual activation.
root = __DIR__
Code.prepend_paths(Path.wildcard(Path.join(root, "lib/*/ebin")))
if List.keymember?(Application.started_applications(), :symphony_elixir, 0),
  do: raise("Symphony started before overlay binding")
manifest = Jason.decode!(File.read!(Path.join(root, "overlay/beam-manifest.json")))
if manifest["elixir"] != System.version() or manifest["erts"] != to_string(:erlang.system_info(:version)),
  do: raise("bound artifact/runtime identity mismatch")
overlay = Path.join(root, "overlay/ebin")
Code.prepend_path(overlay)
Enum.each(manifest["units"], fn unit ->
  Enum.each(unit["modules"], fn artifact ->
    path = Path.join(root, artifact["path"])
    if Path.dirname(path) != overlay or not String.starts_with?(artifact["module"], "Elixir.SymphonyElixir."),
      do: raise("invalid overlay artifact path")
    beam = File.read!(path)
    hash = :crypto.hash(:sha256, beam) |> Base.encode16(case: :lower)
    if hash != artifact["sha256"], do: raise("overlay artifact pin mismatch")
    module = String.to_atom(artifact["module"])
    {:module, ^module} = :code.load_binary(module, String.to_charlist(path), beam)
    if :code.which(module) != String.to_charlist(path), do: raise("effective module path mismatch")
  end)
end)
# Preserve the official CLI's workflow parsing and guardrails acknowledgment.
SymphonyElixir.CLI.main(System.argv())
