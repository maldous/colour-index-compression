"""Inactive native initialization candidate; no per-issue admission database."""
import argparse
import re
import subprocess
from pathlib import Path


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["init", "verify"])
    parser.add_argument("source_mirror")
    parser.add_argument("base_commit")
    parser.add_argument("base_tree")
    parser.add_argument("--fixture-root", help="Explicit private test root; never actual dispatch")
    args = parser.parse_args()
    cwd = Path.cwd()
    root = Path("/home/user/src/cix-approved-migration/disposable-issues")
    if args.fixture_root:
        root = Path(args.fixture_root)
        assert root.resolve() == Path(__file__).resolve().parent / "init-resume-fixture"
    assert re.fullmatch(r"CIX-[0-9]+", cwd.name)
    assert cwd.resolve().parent == root.resolve() and not cwd.is_symlink()
    mirror = Path(args.source_mirror)
    assert mirror.is_absolute() and mirror.exists() and not mirror.is_symlink()
    assert re.fullmatch(r"[0-9a-f]{40}", args.base_commit)
    assert git("-C", str(mirror), "rev-parse", args.base_commit + "^{tree}") == args.base_tree
    repo = cwd / "repo"
    if args.mode == "init":
        assert not list(cwd.iterdir()), "refuse overwrite of preserved workspace"
        subprocess.run(["git", "clone", "--no-hardlinks", "--no-checkout", "--", str(mirror), str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "sparse-checkout", "init", "--no-cone"], check=True)
        subprocess.run(["git", "-C", str(repo), "sparse-checkout", "set", "--no-cone", "--", "/*", "!/docs/"], check=True)
        subprocess.run(["git", "-C", str(repo), "checkout", "--detach", args.base_commit], check=True)
        assert git("-C", str(repo), "rev-parse", "HEAD^{tree}") == args.base_tree
    else:
        assert repo.is_dir() and not repo.is_symlink()
        # Native issue/attempt/branch remain authoritative; never reset resumed work.
        git("-C", str(repo), "rev-parse", "--git-dir")
    print("workspace initialized" if args.mode == "init" else "workspace resume preserved")


if __name__ == "__main__":
    main()
