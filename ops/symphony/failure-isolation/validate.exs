runtime = System.fetch_env!("CIX243_RUNTIME")
Code.prepend_paths(Path.wildcard(runtime <> "/lib/*/ebin"))
Code.compiler_options(ignore_module_conflict: true)
files = ["config/schema.ex", "tracker/issue.ex", "failure_isolation.ex", "tracker.ex", "linear/client.ex", "linear/adapter.ex", "agent_runner.ex", "orchestrator.ex"]
Enum.each(files ++ ["../test/symphony_elixir/failure_isolation_test.exs"], fn file ->
  path = if String.starts_with?(file, "../"), do: String.replace_prefix(file, "../", ""), else: "lib/symphony_elixir/" <> file
  File.write!(path, IO.iodata_to_binary(Code.format_string!(File.read!(path))) <> "\n")
end)
Enum.each(files, fn file -> Code.compile_file("lib/symphony_elixir/" <> file) end)
IO.puts("CIX243_SOURCE_COMPILE_PASS")
Code.require_file(".cix243/direct-check.exs")
