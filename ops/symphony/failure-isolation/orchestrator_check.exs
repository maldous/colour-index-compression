# Only the focused validation VM loads these test doubles; no service is started.
defmodule SymphonyElixir.Config do
  def settings!, do: %{tracker: %{kind: "linear", endpoint: "https://unused.invalid", api_key: "test-only", project_slug: "test", assignee: nil, required_labels: [], active_states: ["Todo"], terminal_states: ["Done"]}, polling: %{interval_ms: 3_600_000}, agent: %{max_concurrent_agents: 1, max_retry_backoff_ms: 3_600_000, failure_isolation_enabled: true, failure_isolation_context: "focused-source-v1"}, worker: %{ssh_hosts: [], max_concurrent_agents_per_host: 1}, codex: %{stall_timeout_ms: 60_000}}
  def settings, do: {:ok, settings!()}
  def validate!, do: :ok
  def max_concurrent_agents_for_state(_), do: 1
end

defmodule CIX243.FakeClient do
  alias SymphonyElixir.{FailureIsolation, Tracker.Issue}
  def fetch_issues_by_states(states) do
    if "Todo" in states, do: {:ok, [%Issue{id: "native-test", identifier: "NATIVE-1", title: "safe setup failure", state: "Todo", dispatchable: true}]}, else: {:ok, []}
  end
  def fetch_issues_by_ids(_), do: fetch_issues_by_states(["Todo"])
  def fetch_failure_record(_, _), do: Agent.get(CIX243.Store, fn s -> FailureIsolation.from_comments(s.comments) end)
  def persist_failure_record(_, record, opts) do
    Agent.get_and_update(CIX243.Store, fn s ->
      {:ok, current} = FailureIsolation.from_comments(s.comments)
      if current == Keyword.fetch!(opts, :expected_failure_record),
        do: {{:ok, record}, %{s | comments: s.comments ++ [%{"body" => FailureIsolation.body(record)}]}},
        else: {{:error, :conflict}, s}
    end)
  end
end

defmodule SymphonyElixir.AgentRunner do
  def run(_issue, _recipient, _opts) do
    Agent.update(CIX243.Store, &%{&1 | starts: &1.starts + 1})
    exit(:setup_failed)
  end
end

defmodule SymphonyElixir.StatusDashboard do
  def notify_update, do: :ok
end

defmodule CIX243.NativeOrchestratorTest do
  use ExUnit.Case, async: false
  alias SymphonyElixir.Orchestrator

  defp await_state(pid, predicate, attempts \\ 100)
  defp await_state(_, _, 0), do: flunk("native state checkpoint not reached")
  defp await_state(pid, predicate, attempts) do
    state = :sys.get_state(pid)
    if predicate.(state), do: state, else: (Process.sleep(10); await_state(pid, predicate, attempts - 1))
  end

  test "real parent dispatches three confirmed setup failures then restart holds before spawning" do
    {:ok, store} = Agent.start_link(fn -> %{comments: [], starts: 0} end, name: CIX243.Store)
    {:ok, supervisor} = Task.Supervisor.start_link()
    Application.put_env(:symphony_elixir, :linear_client_module, CIX243.FakeClient)
    on_exit(fn ->
      Application.delete_env(:symphony_elixir, :linear_client_module)
      if Process.alive?(store), do: Agent.stop(store)
      if Process.alive?(supervisor), do: Supervisor.stop(supervisor)
    end)
    {:ok, parent} = Orchestrator.start_link(name: nil, task_supervisor: supervisor)
    state = await_state(parent, &Map.has_key?(&1.retry_attempts, "native-test"))
    retry = state.retry_attempts["native-test"]
    send(parent, {:retry_issue, "native-test", retry.retry_token})
    state = await_state(parent, fn s -> Agent.get(store, & &1.starts) == 2 and Map.has_key?(s.retry_attempts, "native-test") end)
    retry = state.retry_attempts["native-test"]
    send(parent, {:retry_issue, "native-test", retry.retry_token})
    await_state(parent, &Map.has_key?(&1.blocked, "native-test"))
    assert Agent.get(store, & &1.starts) == 3
    {:ok, record} = CIX243.FakeClient.fetch_failure_record(nil, [])
    assert record["count"] == 3
    assert record["status"] == "blocked"
    assert record["issue_id"] == "native-test"
    assert record["context"] == "focused-source-v1"
    GenServer.stop(parent)
    {:ok, restarted} = Orchestrator.start_link(name: nil, task_supervisor: supervisor)
    await_state(restarted, &Map.has_key?(&1.blocked, "native-test"))
    assert Agent.get(store, & &1.starts) == 3
    GenServer.stop(restarted)
  end
end
