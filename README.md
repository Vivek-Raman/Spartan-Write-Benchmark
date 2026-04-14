# benchmark

Benchmark tooling and dataset runner for the Spartan-Write project.

## CLI

### `benchmark`

- **Help**: `uv run benchmark --help`
- **Options**
  - **`--dir <DIRECTORY>`**: Benchmark working directory (defaults to current working directory).
- **Commands**
  - **`run`**: Run benchmarks.
    - **Flags**
      - **`--model <NAME>`** (required): Model id used for `/chat` and for the results folder `<dir>/<model>/data/`.
      - **`--session-id <ID>`** (required): Session id sent to the server for this run (use a unique value per run).
  - **`dashboard`**: Serve the Streamlit dashboard. Point **`--dir` at the parent workdir** (the same path you pass to `run`) so the dashboard can load every `<dir>/<model>/data/` tree.

Examples:

```bash
uv run benchmark --dir /path/to/benchmark run --model gpt-4o --session-id my-run-001
uv run benchmark --dir /path/to/benchmark dashboard
uv run dashboard --dir /path/to/benchmark
```

### `dashboard`

The package also exposes a standalone dashboard entrypoint:

```bash
uv run dashboard --dir /path/to/benchmark
```
