# Real OTP stop boundary in this disposable focused VM, with no product worker.
stub_source = File.read!(".cix243/orchestrator_check.exs") |> String.split("defmodule CIX243.NativeOrchestratorTest") |> hd()
Code.compile_string(stub_source)
defmodule SymphonyElixir.AgentRunner do
  def run(_issue, _recipient, _opts) do
    worker = self()
    Agent.update(CIX243.Store, &Map.merge(&1, %{starts: &1.starts + 1, worker: worker}))
    receive do :finish -> :ok end
  end
end

defmodule CIX243.StallCheckpoint do
  def await(fun, remaining \\ 200)
  def await(_, 0), do: raise("stall checkpoint not reached")
  def await(fun, remaining) do
    if fun.(), do: :ok, else: (Process.sleep(5); await(fun, remaining - 1))
  end
end

{:ok, store} = Agent.start_link(fn -> %{comments: [], starts: 0, worker: nil} end, name: CIX243.Store)
{:ok, supervisor} = Task.Supervisor.start_link()
Application.put_env(:symphony_elixir, :linear_client_module, CIX243.FakeClient)
{:ok, parent} = SymphonyElixir.Orchestrator.start_link(name: nil, task_supervisor: supervisor)
CIX243.StallCheckpoint.await(fn -> Agent.get(store, & &1.starts) == 1 end)
worker = Agent.get(store, & &1.worker)
true = Process.alive?(worker)
:sys.replace_state(parent, fn state ->
  entry = state.running["native-test"]
  %{state | running: Map.put(state.running, "native-test", %{entry | started_at: DateTime.add(DateTime.utc_now(), -120, :second)})}
end)
:sys.suspend(supervisor)
send(parent, :run_poll_cycle)
CIX243.StallCheckpoint.await(fn ->
  case Process.info(parent, :current_stacktrace) do
    {:current_stacktrace, frames} -> Enum.any?(frames, fn {module, function, _, _} ->
      module == SymphonyElixir.Orchestrator and function in [:confirm_stalled_worker_stop, :terminate_task]
    end)
    _ -> false
  end
end)
{:ok, inflight} = CIX243.FakeClient.fetch_failure_record(nil, [])
"inflight" = inflight["status"]
0 = inflight["count"]
true = Process.alive?(worker)
Process.unlink(parent)
parent_monitor = Process.monitor(parent)
Process.exit(parent, :kill)
receive do {:DOWN, ^parent_monitor, :process, ^parent, :killed} -> :ok after 1_000 -> raise("parent not stopped") end
{:ok, restarted} = SymphonyElixir.Orchestrator.start_link(name: nil, task_supervisor: supervisor)
CIX243.StallCheckpoint.await(fn -> Map.has_key?(:sys.get_state(restarted).blocked, "native-test") end)
1 = Agent.get(store, & &1.starts)
{:ok, ^inflight} = CIX243.FakeClient.fetch_failure_record(nil, [])
true = Process.alive?(worker)
IO.puts("CIX243_STALL_INTERRUPTED_STOP_RESTART_HOLD_BEFORE_SECOND_WORKER_PASS")
:sys.resume(supervisor)
CIX243.StallCheckpoint.await(fn -> not Process.alive?(worker) end)
GenServer.stop(restarted)
Supervisor.stop(supervisor)
Agent.stop(store)
Application.delete_env(:symphony_elixir, :linear_client_module)
IO.puts("CIX243_STALL_CHECK_REAL_OTP_CLEANUP_PASS")
