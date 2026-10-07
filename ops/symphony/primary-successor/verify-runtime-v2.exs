# Prepared entry only. The technical owner separately binds actual activation.
root = "/home/user/src/cix-approved-migration/runtime-cix243-v2"
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
{:ok, workflow} = SymphonyElixir.Workflow.load("/home/user/src/cix-approved-migration/config/WORKFLOW.draft.md")
{:ok, settings} = SymphonyElixir.Config.Schema.parse(workflow.config)
true = settings.agent.failure_isolation_enabled
"CIX243:511039ec3e8258437d2d3ccda2e697cf5f90ca698da855532a3ddacd1dce65ec" = settings.agent.failure_isolation_context
8 = settings.agent.max_concurrent_agents
30000 = settings.polling.interval_ms
"1cad16b1273d" = settings.tracker.provider["project_slug"]
true = "cix-migration-primary" in settings.tracker.required_labels
false = "Blocked" in settings.tracker.active_states
policy = SymphonyElixir.Config.Schema.resolve_turn_sandbox_policy(settings, "/home/user/src/cix-approved-migration/disposable-issues/CIX-0")
IO.inspect(policy, label: "ordinary_workspace_policy")
false = List.keymember?(Application.started_applications(), :symphony_elixir, 0)
IO.puts("CIX244_EFFECTIVE_OVERLAY_CONFIGURATION_PASS_NO_START_NO_TRACKER")
