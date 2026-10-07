# Artifact derivation only: no Application.ensure_all_started/CLI/tracker calls.
[root, plan_path] = System.argv()
Code.prepend_paths(Path.wildcard(Path.join(root, "lib/*/ebin")))
plan = Jason.decode!(File.read!(plan_path))
if System.version() != "1.19.5" or to_string(:erlang.system_info(:version)) != "16.4",
  do: raise("installed compiler/runtime identity differs from bound plan")
Code.compiler_options(ignore_module_conflict: true)
overlay = Path.join(root, "overlay/ebin")
File.mkdir_p!(overlay)
units = Enum.map(plan["source_files"], fn source ->
  bytes = File.read!(source["path"])
  hash = :crypto.hash(:sha256, bytes) |> Base.encode16(case: :lower)
  if hash != source["sha256"], do: raise("reviewed source pin changed")
  modules = Enum.map(Code.compile_file(source["path"]), fn {module, beam} ->
    name = Atom.to_string(module)
    if not String.starts_with?(name, "Elixir.SymphonyElixir."), do: raise("unexpected compiled module namespace")
    filename = name <> ".beam"
    target = Path.join(overlay, filename)
    if File.exists?(target), do: raise("duplicate compiled module")
    File.write!(target, beam)
    %{"module" => name, "path" => "overlay/ebin/" <> filename,
      "sha256" => :crypto.hash(:sha256, beam) |> Base.encode16(case: :lower)}
  end)
  %{"source" => source["relative_path"], "source_sha256" => hash, "modules" => modules}
end)
manifest = %{"status" => "DERIVED_NOT_ACTIVATED", "reviewed_patch_sha256" => plan["reviewed_patch_sha256"],
  "native_base" => plan["reviewed_native_base"], "elixir" => System.version(),
  "erts" => to_string(:erlang.system_info(:version)), "otp" => System.otp_release(),
  "units" => units, "tests_replayed" => false, "live_tracker" => false,
  "entry" => "official extracted bin/symphony eval -> verified overlay -> existing CLI.main"}
File.write!(Path.join(root, "overlay/beam-manifest.json"), Jason.encode!(manifest, pretty: true) <> "\n")
IO.puts("CIX243_BEAM_ARTIFACT_DERIVED_NOT_ACTIVATED")
