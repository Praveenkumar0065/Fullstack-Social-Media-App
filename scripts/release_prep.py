from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare release artifacts: update VERSION and scaffold release notes file."
    )
    parser.add_argument(
        "version",
        nargs="?",
        help="Semantic version without prefix, e.g. 1.2.0",
    )
    bump = parser.add_mutually_exclusive_group()
    bump.add_argument("--major", action="store_true", help="Bump major version from VERSION file")
    bump.add_argument("--minor", action="store_true", help="Bump minor version from VERSION file")
    bump.add_argument("--patch", action="store_true", help="Bump patch version from VERSION file")
    parser.add_argument(
        "--notes-only",
        action="store_true",
        help="Create release-notes file only; do not update VERSION.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite release notes file if it already exists.",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Stage and commit release prep files after generation.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open generated release-notes file after creation.",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow running with an uncommitted working tree.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview planned changes without writing files, opening editor, or committing.",
    )
    return parser.parse_args()


def ensure_semver(version: str) -> None:
    if not SEMVER_RE.fullmatch(version):
        raise ValueError(f"Invalid version '{version}'. Use semantic version X.Y.Z")


def load_template(repo_root: Path) -> str:
    template_path = repo_root / "release-notes" / "TEMPLATE.md"
    if not template_path.exists():
        raise FileNotFoundError(f"Missing template: {template_path}")
    return template_path.read_text(encoding="utf-8")


def read_version(repo_root: Path) -> str:
    version_path = repo_root / "VERSION"
    if not version_path.exists():
        raise FileNotFoundError(f"Missing VERSION file: {version_path}")
    version = version_path.read_text(encoding="utf-8").strip()
    ensure_semver(version)
    return version


def bump_version(current: str, bump_type: str) -> str:
    major, minor, patch = [int(x) for x in current.split(".")]
    if bump_type == "major":
        return f"{major + 1}.0.0"
    if bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def run_git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )


def ensure_working_tree_clean(repo_root: Path) -> None:
    result = run_git(repo_root, ["status", "--porcelain"])
    if result.returncode != 0:
        raise RuntimeError(f"git status failed: {result.stderr.strip()}")
    if result.stdout.strip():
        raise RuntimeError(
            "Working tree has uncommitted changes. Commit/stash them or pass --allow-dirty."
        )


def ensure_tag_not_exists(repo_root: Path, version: str) -> None:
    tag_name = f"v{version}"
    result = run_git(repo_root, ["tag", "--list", tag_name])
    if result.returncode != 0:
        raise RuntimeError(f"git tag lookup failed: {result.stderr.strip()}")
    if tag_name in result.stdout.split():
        raise RuntimeError(f"Tag already exists: {tag_name}")


def write_version(repo_root: Path, version: str) -> None:
    version_path = repo_root / "VERSION"
    version_path.write_text(f"{version}\n", encoding="utf-8")


def write_release_notes(repo_root: Path, version: str, template: str, force: bool) -> Path:
    notes_dir = repo_root / "release-notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    notes_path = notes_dir / f"v{version}.md"

    if notes_path.exists() and not force:
        raise FileExistsError(
            f"Release notes already exist: {notes_path}. Use --force to overwrite."
        )

    notes_path.write_text(template, encoding="utf-8")
    return notes_path


def maybe_open_file(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
        return
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.run([opener, str(path)], check=False)


def maybe_commit(repo_root: Path, version: str, notes_path: Path, notes_only: bool) -> None:
    files_to_add = [str(notes_path)]
    if not notes_only:
        files_to_add.insert(0, "VERSION")

    add_result = run_git(repo_root, ["add", *files_to_add])
    if add_result.returncode != 0:
        raise RuntimeError(f"git add failed: {add_result.stderr.strip()}")

    message = f"chore(release): prepare v{version}"
    commit_result = run_git(repo_root, ["commit", "-m", message])
    if commit_result.returncode != 0:
        stderr = commit_result.stderr.strip()
        stdout = commit_result.stdout.strip()
        combined = stderr or stdout
        if "nothing to commit" in combined.lower():
            print("No changes to commit")
            return
        raise RuntimeError(f"git commit failed: {combined}")


def main() -> int:
    args = parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    has_git = (repo_root / ".git").exists()

    bump_flags = [args.major, args.minor, args.patch]
    if args.version and any(bump_flags):
        raise ValueError("Provide either <version> or one bump flag (--major/--minor/--patch), not both")
    if not args.version and not any(bump_flags):
        raise ValueError("Provide <version> or one bump flag (--major/--minor/--patch)")

    if args.version:
        version = args.version
        ensure_semver(version)
    else:
        current = read_version(repo_root)
        bump_type = "major" if args.major else "minor" if args.minor else "patch"
        version = bump_version(current, bump_type)

    if has_git and not args.allow_dirty:
        ensure_working_tree_clean(repo_root)
    if has_git:
        ensure_tag_not_exists(repo_root, version)

    template = load_template(repo_root)
    notes_path = repo_root / "release-notes" / f"v{version}.md"
    if notes_path.exists() and not args.force:
        raise FileExistsError(
            f"Release notes already exist: {notes_path}. Use --force to overwrite."
        )

    if args.dry_run:
        print("Dry run: no files were modified")
        if args.notes_only:
            print("Would keep VERSION unchanged (--notes-only set)")
        else:
            print(f"Would update VERSION to {version}")
        print(f"Would create release notes: {notes_path}")
        if args.commit:
            print("Would stage and commit release prep files")
        if args.open:
            print("Would open generated release notes file")
        return 0

    if not args.notes_only:
        write_version(repo_root, version)

    notes_path = write_release_notes(
        repo_root=repo_root,
        version=version,
        template=template,
        force=args.force,
    )

    if args.commit:
        if not has_git:
            raise RuntimeError("--commit requested but .git directory was not found")
        maybe_commit(repo_root, version, notes_path, args.notes_only)

    if args.open:
        maybe_open_file(notes_path)

    print(f"Prepared release notes: {notes_path}")
    if args.notes_only:
        print("VERSION unchanged (--notes-only set)")
    else:
        print(f"Updated VERSION to {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
