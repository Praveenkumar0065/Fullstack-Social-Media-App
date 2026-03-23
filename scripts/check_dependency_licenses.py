from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Iterable

UNKNOWN_MARKERS = {"", "unknown", "none", "n/a", "no license"}


@dataclass
class LicenseRecord:
    ecosystem: str
    package: str
    version: str
    license_name: str


RISK_HIGH_TOKENS = {
    "gpl",
    "gpl-2-0",
    "gpl-3-0",
    "agpl",
    "agpl-3-0",
    "proprietary",
    "commercial",
    "source-available",
}

RISK_MEDIUM_TOKENS = {
    "lgpl",
    "lgpl-2-1",
    "lgpl-3-0",
    "mpl",
    "mpl-2-0",
    "epl",
    "epl-2-0",
    "cddl",
}


def normalize_license_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_requirements(path: Path) -> list[str]:
    packages: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.split(";", 1)[0].strip()
        line = line.split("==", 1)[0].strip()
        line = line.split("[", 1)[0].strip()
        if line:
            packages.append(line)
    return packages


def frontend_records(repo_root: Path) -> list[LicenseRecord]:
    package_json = read_json(repo_root / "frontend_react" / "package.json")
    names = []
    names.extend((package_json.get("dependencies") or {}).keys())
    names.extend((package_json.get("devDependencies") or {}).keys())

    records: list[LicenseRecord] = []
    missing: list[str] = []
    for name in sorted(set(names), key=str.lower):
        pkg_path = repo_root / "frontend_react" / "node_modules" / name / "package.json"
        if not pkg_path.exists():
            missing.append(name)
            continue
        pkg = read_json(pkg_path)
        version = str(pkg.get("version", "UNKNOWN")).strip()
        license_value = pkg.get("license", "")
        if isinstance(license_value, dict):
            license_name = str(license_value.get("type", "")).strip()
        elif isinstance(license_value, list):
            license_name = ", ".join(str(x) for x in license_value)
        else:
            license_name = str(license_value).strip()

        records.append(
            LicenseRecord(
                ecosystem="frontend",
                package=name,
                version=version or "UNKNOWN",
                license_name=license_name or "UNKNOWN",
            )
        )

    if missing:
        raise RuntimeError(
            "Missing frontend package metadata for: " + ", ".join(sorted(missing)) + ". Run npm ci in frontend_react."
        )

    return records


def build_distribution_index() -> dict[str, metadata.Distribution]:
    index: dict[str, metadata.Distribution] = {}
    for dist in metadata.distributions():
        name = dist.metadata.get("Name") or ""
        if not name:
            continue
        index[normalize_name(name)] = dist
    return index


def extract_license(dist: metadata.Distribution) -> str:
    classifiers = dist.metadata.get_all("Classifier") or []
    classifier_license = ""
    for classifier in classifiers:
        if "License ::" in classifier:
            classifier_license = classifier.split("License ::", 1)[1].strip()
            break

    direct = (dist.metadata.get("License") or "").strip()
    if direct and normalize_name(direct) not in UNKNOWN_MARKERS:
        # Some distributions include full license text in the License field.
        # Prefer concise classifier license when available.
        if len(direct) > 120 and classifier_license:
            return classifier_license
        first_line = direct.splitlines()[0].strip()
        return first_line or direct

    if classifier_license:
        return classifier_license

    return "UNKNOWN"


def backend_records(repo_root: Path) -> list[LicenseRecord]:
    reqs = parse_requirements(repo_root / "backend_code" / "requirements.txt")
    dist_index = build_distribution_index()
    records: list[LicenseRecord] = []
    missing: list[str] = []

    for req in reqs:
        key = normalize_name(req)
        dist = dist_index.get(key)
        if dist is None:
            missing.append(req)
            continue

        version = str(dist.version or "UNKNOWN").strip()
        license_name = extract_license(dist)
        records.append(
            LicenseRecord(
                ecosystem="backend",
                package=req,
                version=version or "UNKNOWN",
                license_name=license_name or "UNKNOWN",
            )
        )

    if missing:
        raise RuntimeError(
            "Missing backend distributions for: " + ", ".join(sorted(missing)) + ". Run pip install -r backend_code/requirements.txt."
        )

    return records


def has_unknown_licenses(records: Iterable[LicenseRecord]) -> list[LicenseRecord]:
    unknown: list[LicenseRecord] = []
    for rec in records:
        value = rec.license_name.strip().lower()
        if value in UNKNOWN_MARKERS:
            unknown.append(rec)
    return unknown


def infer_license_aliases(raw_license: str) -> set[str]:
    text = raw_license.strip().lower()
    aliases: set[str] = set()

    if "mit" in text:
        aliases.add("mit")
    if "apache" in text and "2" in text:
        aliases.add("apache-2-0")
    if "apache software license" in text:
        aliases.add("apache-2-0")
    if "bsd-3" in text or "3-clause" in text:
        aliases.add("bsd-3-clause")
    if "bsd-2" in text or "2-clause" in text:
        aliases.add("bsd-2-clause")
    if "bsd" in text:
        aliases.add("bsd")
    if "unlicense" in text:
        aliases.add("unlicense")
    if "isc" in text:
        aliases.add("isc")
    if "mpl" in text:
        aliases.add("mpl")

    if not aliases and text:
        aliases.add(normalize_license_token(text))

    return aliases


def parse_allowed_licenses(raw_values: list[str]) -> set[str]:
    allowed: set[str] = set()
    for raw in raw_values:
        for piece in raw.split(","):
            token = normalize_license_token(piece)
            if token:
                allowed.add(token)
    return allowed


def find_disallowed_licenses(records: Iterable[LicenseRecord], allowed_tokens: set[str]) -> list[tuple[LicenseRecord, set[str]]]:
    blocked: list[tuple[LicenseRecord, set[str]]] = []
    for rec in records:
        aliases = infer_license_aliases(rec.license_name)
        if not aliases.intersection(allowed_tokens):
            blocked.append((rec, aliases))
    return blocked


def classify_risk(record: LicenseRecord, aliases: set[str]) -> str:
    raw = normalize_license_token(record.license_name)
    all_tokens = set(aliases)
    if raw:
        all_tokens.add(raw)

    if normalize_name(record.license_name) in UNKNOWN_MARKERS or "unknown" in all_tokens:
        return "high"

    for token in all_tokens:
        if token in RISK_HIGH_TOKENS or token.startswith("gpl") or token.startswith("agpl"):
            return "high"

    for token in all_tokens:
        if token in RISK_MEDIUM_TOKENS or token.startswith("lgpl") or token.startswith("mpl") or token.startswith("epl"):
            return "medium"

    return "low"


def records_with_risk(records: Iterable[LicenseRecord]) -> list[tuple[LicenseRecord, set[str], str]]:
    analyzed: list[tuple[LicenseRecord, set[str], str]] = []
    for rec in records:
        aliases = infer_license_aliases(rec.license_name)
        risk = classify_risk(rec, aliases)
        analyzed.append((rec, aliases, risk))
    return analyzed


def should_fail_for_risk(risk: str, threshold: str) -> bool:
    if threshold == "none":
        return False
    if threshold == "high":
        return risk == "high"
    if threshold == "medium":
        return risk in {"medium", "high"}
    return False


def write_json_report(path: Path, analyzed: list[tuple[LicenseRecord, set[str], str]], allowed_tokens: set[str]) -> None:
    summary = {
        "total": len(analyzed),
        "risk": {
            "low": sum(1 for _, _, risk in analyzed if risk == "low"),
            "medium": sum(1 for _, _, risk in analyzed if risk == "medium"),
            "high": sum(1 for _, _, risk in analyzed if risk == "high"),
        },
        "allowed_license_tokens": sorted(allowed_tokens),
    }

    payload = {
        "summary": summary,
        "dependencies": [
            {
                "ecosystem": rec.ecosystem,
                "package": rec.package,
                "version": rec.version,
                "license": rec.license_name,
                "aliases": sorted(aliases),
                "risk": risk,
            }
            for rec, aliases, risk in analyzed
        ],
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def ensure_notices_exists(repo_root: Path) -> None:
    notices = repo_root / "THIRD_PARTY_NOTICES.md"
    if not notices.exists() or not notices.read_text(encoding="utf-8").strip():
        raise RuntimeError("THIRD_PARTY_NOTICES.md is missing or empty")


def print_table(records: list[LicenseRecord]) -> None:
    print("ecosystem|package|version|license")
    for rec in records:
        print(f"{rec.ecosystem}|{rec.package}|{rec.version}|{rec.license_name}")


def print_risk_table(analyzed: list[tuple[LicenseRecord, set[str], str]]) -> None:
    print("\nrisk|ecosystem|package|version|license|aliases")
    for rec, aliases, risk in analyzed:
        alias_text = ",".join(sorted(aliases)) if aliases else ""
        print(f"{risk}|{rec.ecosystem}|{rec.package}|{rec.version}|{rec.license_name}|{alias_text}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate dependency license metadata for frontend and backend packages.")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--verify-notices", action="store_true", help="Fail if THIRD_PARTY_NOTICES.md is missing or empty")
    parser.add_argument("--strict", action="store_true", help="Fail if any dependency license is unknown")
    parser.add_argument(
        "--allowed-license",
        action="append",
        default=[],
        help="Allowed license token(s). Can be repeated or comma-separated (example: --allowed-license MIT --allowed-license Apache-2.0,BSD-3-Clause)",
    )
    parser.add_argument(
        "--fail-on-risk",
        choices=["none", "medium", "high"],
        default="none",
        help="Fail if dependencies meet or exceed this license risk threshold.",
    )
    parser.add_argument(
        "--report-json",
        default="",
        help="Optional output path for a JSON compliance report.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()

    if args.verify_notices:
        ensure_notices_exists(repo_root)

    frontend = frontend_records(repo_root)
    backend = backend_records(repo_root)
    combined = sorted(frontend + backend, key=lambda r: (r.ecosystem, r.package.lower()))

    print_table(combined)

    analyzed = records_with_risk(combined)
    print_risk_table(analyzed)

    if args.strict:
        unknown = has_unknown_licenses(combined)
        if unknown:
            print("\nFound dependencies with unknown/missing license metadata:", file=sys.stderr)
            for rec in unknown:
                print(f"- {rec.ecosystem}:{rec.package} ({rec.version})", file=sys.stderr)
            return 1

    allowed_tokens = parse_allowed_licenses(args.allowed_license)
    if allowed_tokens:
        disallowed = find_disallowed_licenses((rec for rec, _, _ in analyzed), allowed_tokens)
        if disallowed:
            print("\nFound dependencies outside allowed license policy:", file=sys.stderr)
            print("Allowed tokens: " + ", ".join(sorted(allowed_tokens)), file=sys.stderr)
            for rec, aliases in disallowed:
                alias_text = ", ".join(sorted(aliases)) if aliases else "none"
                print(
                    f"- {rec.ecosystem}:{rec.package} ({rec.version}) license='{rec.license_name}' aliases=[{alias_text}]",
                    file=sys.stderr,
                )
            return 1

    if args.fail_on_risk != "none":
        risky = [(rec, aliases, risk) for rec, aliases, risk in analyzed if should_fail_for_risk(risk, args.fail_on_risk)]
        if risky:
            print("\nFound dependencies violating risk threshold:", file=sys.stderr)
            print("Threshold: " + args.fail_on_risk, file=sys.stderr)
            for rec, aliases, risk in risky:
                alias_text = ", ".join(sorted(aliases)) if aliases else "none"
                print(
                    f"- {rec.ecosystem}:{rec.package} ({rec.version}) risk={risk} license='{rec.license_name}' aliases=[{alias_text}]",
                    file=sys.stderr,
                )
            return 1

    if args.report_json:
        write_json_report(Path(args.report_json), analyzed, allowed_tokens)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
