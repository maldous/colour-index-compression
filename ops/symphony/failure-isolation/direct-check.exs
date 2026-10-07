alias SymphonyElixir.{FailureIsolation, Linear.Client, Tracker.Issue}
{:ok, initial} = FailureIsolation.from_comments([])
{:ok, scoped} = FailureIsolation.scope(initial, "proof-issue", "proof-source")
{:error, :invalid_failure_context} = FailureIsolation.scope(initial, "id", String.duplicate("x", 129))
{:ok, a} = FailureIsolation.begin_attempt(scoped)
b = FailureIsolation.finish(a, {:workspace_hook_failed, "before_run", 7, "secret-output"})
1 = b["count"]
{:ok, c} = FailureIsolation.begin_attempt(b)
d = FailureIsolation.finish(c, {:workspace_hook_failed, "before_run", 7, "new-output"})
2 = d["count"]
{:ok, e} = FailureIsolation.begin_attempt(d)
f = FailureIsolation.finish(e, {:workspace_hook_failed, "before_run", 7, "third-output"})
3 = f["count"]
"blocked" = f["status"]
comment = fn record -> %{"body" => FailureIsolation.body(record)} end
{:ok, ^f} = FailureIsolation.from_comments(Enum.map([f,e,d,c,b,a], comment))
{:error, :durable_failure_hold} = FailureIsolation.begin_attempt(f)
{:error, :durable_failure_hold} = FailureIsolation.finish(f, :setup_failed)
{:error, :durable_failure_hold} = FailureIsolation.continue(f)
{:error, :failure_context_changed} = FailureIsolation.scope(f, "proof-issue", "new-source")
{:ok, ^a} = FailureIsolation.from_comments([comment.(a), comment.(a)])
{:ok, other} = FailureIsolation.begin_attempt(scoped)
{:error, :ambiguous_failure_history} = FailureIsolation.from_comments([comment.(a), comment.(other)])
{:error, :ambiguous_failure_history} = FailureIsolation.from_comments([comment.(b)])
{:error, :durable_failure_hold} = FailureIsolation.begin_attempt(a)
continued = FailureIsolation.continue(c)
1 = continued["count"]
{:ok, g} = FailureIsolation.begin_attempt(continued)
different = FailureIsolation.finish(g, {:workspace_hook_failed, "before_run", 8, ""})
1 = different["count"]
true = different["failure"] != b["failure"]
permission = FailureIsolation.finish(a, %File.Error{reason: :eacces, path: "secret", action: "read"})
"blocked" = permission["status"]
1 = permission["count"]
http_denied = FailureIsolation.finish(a, {:turn_failed, %{"error" => %{"code" => 403}}})
"blocked" = http_denied["status"]
opaque = FailureIsolation.finish(a, %RuntimeError{message: "secret"})
"blocked" = opaque["status"]
0 = opaque["count"]
false = String.contains?(FailureIsolation.body(f), "secret")
{:ok, resumed} = FailureIsolation.resume(f, "verified-resolution")
0 = resumed["count"]
"idle" = resumed["status"]
{:error, :new_progress_reference_required} = FailureIsolation.resume(resumed, "verified-resolution")
IO.puts("CIX243_FOCUSED_STATE_ASSERTIONS_PASS")

{:ok, store} = Agent.start_link(fn -> %{comments: [], writes: 0} end)
request = fn payload, _headers ->
  if String.contains?(payload["query"], "mutation SymphonyFailureRecord") do
    body = payload["variables"]["input"]["body"]
    Agent.update(store, fn s -> %{s | comments: s.comments ++ [%{"body" => body}], writes: s.writes + 1} end)
    {:error, :simulated_timeout}
  else
    comments = Agent.get(store, & &1.comments)
    {:ok, %{status: 200, body: %{"data" => %{"issue" => %{"comments" => %{"nodes" => comments, "pageInfo" => %{"hasNextPage" => false}}}}}}}
  end
end
opts = [tracker_settings: %{api_key: "test-only", endpoint: "https://unused.invalid"}, request_fun: request]
issue = %Issue{id: "proof-issue", description: "human text"}
{:ok, ^a} = Client.persist_failure_record(issue, a, opts)
{:ok, ^a} = Client.persist_failure_record(issue, a, opts)
1 = Agent.get(store, & &1.writes)
"human text" = issue.description
Agent.stop(store)
pages = Keyword.put(opts, :request_fun, fn payload, _ ->
  {nodes, page} = if payload["variables"]["after"] == nil,
    do: {[comment.(b)], %{"hasNextPage" => true, "endCursor" => "next"}},
    else: {[comment.(a)], %{"hasNextPage" => false}}
  {:ok, %{status: 200, body: %{"data" => %{"issue" => %{"comments" => %{"nodes" => nodes, "pageInfo" => page}}}}}}
end)
{:ok, ^b} = Client.fetch_failure_record(issue, pages)
unknown = Keyword.put(opts, :request_fun, fn _, _ -> {:error, :simulated_timeout} end)
{:error, :failure_record_unconfirmed} = Client.fetch_failure_record(issue, unknown)
IO.puts("CIX243_FOCUSED_ADAPTER_READBACK_ASSERTIONS_PASS")

stub_source = File.read!(".cix243/orchestrator_check.exs") |> String.split("defmodule CIX243.NativeOrchestratorTest") |> hd()
Code.compile_string(stub_source)
defmodule CIX243.Checkpoint do
  def await(pid, predicate, remaining \\ 100)
  def await(_, _, 0), do: raise("native checkpoint not reached")
  def await(pid, predicate, remaining) do
    state = :sys.get_state(pid)
    if predicate.(state), do: state, else: (Process.sleep(10); await(pid, predicate, remaining-1))
  end
end
{:ok, store} = Agent.start_link(fn -> %{comments: [], starts: 0} end, name: CIX243.Store)
{:ok, supervisor} = Task.Supervisor.start_link()
Application.put_env(:symphony_elixir, :linear_client_module, CIX243.FakeClient)
{:ok, parent} = SymphonyElixir.Orchestrator.start_link(name: nil, task_supervisor: supervisor)
state = CIX243.Checkpoint.await(parent, &Map.has_key?(&1.retry_attempts, "native-test"))
retry = state.retry_attempts["native-test"]
send(parent, {:retry_issue, "native-test", retry.retry_token})
state = CIX243.Checkpoint.await(parent, fn s -> Agent.get(store, & &1.starts) == 2 and Map.has_key?(s.retry_attempts, "native-test") end)
retry = state.retry_attempts["native-test"]
send(parent, {:retry_issue, "native-test", retry.retry_token})
CIX243.Checkpoint.await(parent, &Map.has_key?(&1.blocked, "native-test"))
3 = Agent.get(store, & &1.starts)
{:ok, record} = CIX243.FakeClient.fetch_failure_record(nil, [])
3 = record["count"]
"blocked" = record["status"]
"native-test" = record["issue_id"]
"focused-source-v1" = record["context"]
GenServer.stop(parent)
{:ok, restarted} = SymphonyElixir.Orchestrator.start_link(name: nil, task_supervisor: supervisor)
CIX243.Checkpoint.await(restarted, &Map.has_key?(&1.blocked, "native-test"))
3 = Agent.get(store, & &1.starts)
GenServer.stop(restarted)
Supervisor.stop(supervisor)
Agent.stop(store)
Application.delete_env(:symphony_elixir, :linear_client_module)
IO.puts("CIX243_REAL_GEN_SERVER_THREE_SETUP_FAILURES_AND_RESTART_HOLD_PASS")
IO.puts("STANDARD_EXUNIT_SUITE_UNRUN: ExUnit omitted from retained release; no live Linear/network/service activation")
