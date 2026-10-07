root = __DIR__
runtime = "/home/user/src/cix-approved-migration/runtime-cix243-v2"
Code.prepend_paths(Path.wildcard(runtime <> "/lib/*/ebin"))
Code.compiler_options(ignore_module_conflict: true)
for file <- ["config/schema.ex", "linear/agent_tool.ex", "failure_isolation.ex", "codex/app_server.ex"] do
  path = root <> "/lib/symphony_elixir/" <> file
  File.write!(path, IO.iodata_to_binary(Code.format_string!(File.read!(path))) <> "\n")
  Code.compile_file(path)
end
IO.puts("CIX245_CHANGED_SOURCE_COMPILE_PASS")

defmodule SymphonyElixir.Config do
  def local_workspace_root, do: Process.get(:focused_root)
  def settings!, do: %{codex: %{command: Process.get(:focused_peer), read_timeout_ms: 5_000}}
  def codex_runtime_settings(_workspace, _opts \\ []), do: {:ok, Process.get(:focused_policy)}
end

defmodule SymphonyElixir.Codex.DynamicTool do
  def bind do
    specs = SymphonyElixir.Linear.AgentTool.tool_specs()
    specs = if Process.get(:obsolete_specs), do: Enum.map(specs, &Map.delete(&1, "type")), else: specs
    %{tool_specs: specs, secret_environment_names: []}
  end
end

alias SymphonyElixir.{Config.Schema, Codex.AppServer, FailureIsolation}
{:ok, settings} = Schema.parse(%{})
%{"granular" => categories} = settings.codex.approval_policy
5 = map_size(categories)
true = Enum.all?(categories, fn {_category, allowed} -> allowed == false end)
"workspace-write" = settings.codex.thread_sandbox
fixture = root <> "/fixture/issue"
File.mkdir_p!(fixture)
Process.put(:focused_root, root <> "/fixture")
Process.put(:focused_peer, "python3 " <> root <> "/fake-peer.py")
policy = %{approval_policy: settings.codex.approval_policy, thread_sandbox: settings.codex.thread_sandbox, turn_sandbox_policy: %{}}
Process.put(:focused_policy, %{policy | approval_policy: %{"reject" => %{"sandbox_approval" => true, "rules" => true, "mcp_elicitations" => true}}})
Process.put(:obsolete_specs, true)
{:error, {:startup_stage, :thread_start, {:response_error, %{"code" => -32602}}} = reason} = AppServer.start_session(fixture)
{:ok, initial} = FailureIsolation.from_comments([])
{:ok, scoped} = FailureIsolation.scope(initial, "offline-only", "compatibility-focused")
{:ok, inflight} = FailureIsolation.begin_attempt(scoped)
blocked = FailureIsolation.finish(inflight, reason)
"blocked" = blocked["status"]
0 = blocked["count"]
%{"stage" => "thread_start", "tag" => "response_error", "code" => -32602} = blocked["observation"]
false = String.contains?(FailureIsolation.body(blocked), "synthetic-private-error")
{:ok, ^blocked} = FailureIsolation.from_comments([%{"body" => FailureIsolation.body(inflight)}, %{"body" => FailureIsolation.body(blocked)}])
IO.puts("CIX245_ACTUAL_APPSERVER_OLD_REQUEST_REJECTED_SAFE_RECORD_PASS")

Process.put(:focused_policy, policy)
Process.put(:obsolete_specs, false)
{:ok, session} = AppServer.start_session(fixture)
"offline-focused-thread" = session.thread_id
false = session.auto_approve_requests
:ok = AppServer.stop_session(session)
IO.puts("CIX245_ACTUAL_APPSERVER_CORRECTED_REQUEST_ACCEPTED_NO_TURN_PASS")

# Existing denial and counted failure semantics remain unchanged by stage wrapping.
denied = FailureIsolation.finish(inflight, {:startup_stage, :initialize, %File.Error{reason: :eacces, path: "private", action: "read"}})
"blocked" = denied["status"]
1 = denied["count"]
counted = FailureIsolation.finish(inflight, {:startup_stage, :initialize, {:port_exit, 7}})
1 = counted["count"]
%{"stage" => "initialize", "tag" => "port_exit", "code" => 7} = counted["observation"]
false = String.contains?(FailureIsolation.body(denied), "private")
bad = Map.put(blocked, "observation", %{"stage" => "unknown", "tag" => "unclassified", "code" => nil, "message" => "private"})
{:error, :invalid_failure_record} = FailureIsolation.read(bad)
IO.puts("CIX245_OBSERVATION_DENIAL_PRIVACY_AND_CHAIN_PASS")
