#!/usr/bin/env python3
"""Extract and summarize sensor data from a .tar.gz or .tgz archive.

The script uses only the Python standard library and is suitable for Python 3.8+.
"""

from __future__ import annotations

import argparse
import csv
import locale
import math
import re
import shutil
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence


SCRIPT_VERSION = "2026-07-30-docker-v6-start-delay"


@dataclass(frozen=True)
class PowerRow:
    timestamp: float
    power: float
    scope: str
    csv_row: int


RESULT_FIELDS = [
    "report_file",
    "scope",
    "experiment_start_seconds",
    "experiment_stop_seconds",
    "experiment_start_ms",
    "experiment_stop_ms",
    "START",
    "STOP",
    "PRESTART",
    "PRESTOP",
    "selected_start_timestamp_ms",
    "selected_stop_timestamp_ms",
    "weighted_average_power",
]


def format_number(value: float) -> str:
    """Match PowerShell's invariant ``0.################`` formatting."""
    if not math.isfinite(value):
        raise ValueError(f"Non-finite numeric value encountered: {value!r}")

    text = format(value, ".16f").rstrip("0").rstrip(".")
    return "0" if text in {"-0", ""} else text


def parse_number(value: object, description: str) -> float:
    """Parse invariant numbers first, then try the operating-system locale."""
    text = str(value).strip()
    try:
        number = float(text)
    except ValueError:
        try:
            number = locale.atof(text)
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"Cannot parse {text!r} as a number for {description}."
            ) from exc

    if not math.isfinite(number):
        raise ValueError(f"Non-finite value {text!r} found for {description}.")
    return number


def detect_delimiter(path: Path) -> str:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        header = handle.readline()
    if not header:
        raise ValueError(f"CSV file is empty: {path}")

    counts = {",": header.count(","), ";": header.count(";"), "\t": header.count("\t")}
    delimiter = max(counts, key=counts.get)
    if counts[delimiter] == 0:
        raise ValueError(f"Could not determine CSV delimiter from the header in: {path}")
    return delimiter


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    delimiter = detect_delimiter(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError(f"CSV file has no header: {path}")
        return list(reader)


def require_column(fieldnames: Sequence[str], required_name: str, path: Path) -> str:
    for name in fieldnames:
        if name.strip().lower() == required_name.lower():
            return name
    available = ", ".join(fieldnames)
    raise ValueError(
        f"Column {required_name!r} was not found in {path}. "
        f"Available columns: {available}"
    )


def find_exactly_one(paths: Iterable[Path], description: str) -> Path:
    unique = sorted({path.resolve() for path in paths}, key=lambda item: str(item).lower())
    if len(unique) != 1:
        raise ValueError(f"Expected exactly one {description}, but found {len(unique)}.")
    return unique[0]


def recursive_directories(root: Path) -> Iterable[Path]:
    return (path for path in root.rglob("*") if path.is_dir())


def recursive_files(root: Path, filename: str) -> Iterable[Path]:
    target = filename.lower()
    return (path for path in root.rglob("*") if path.is_file() and path.name.lower() == target)


def get_container_id(container_ids_path: Path, name: str) -> str:
    content = container_ids_path.read_text(encoding="utf-8-sig", errors="strict")
    pattern = re.compile(rf"^\s*{re.escape(name)}\s*=\s*([0-9a-f]+)\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(content)
    if match is None:
        raise ValueError(f"Could not find {name}=<hex id> in {container_ids_path}.")
    return match.group(1).lower()


def find_container_power_report(sensor_directories: Sequence[Path], container_id: str, container_name: str) -> Path:
    docker_pattern = re.compile(rf"^docker-{re.escape(container_id)}(?:\.scope)?$", re.IGNORECASE)
    matches: List[Path] = []

    for sensor_directory in sensor_directories:
        system_slices = [
            directory
            for directory in recursive_directories(sensor_directory)
            if directory.name.lower() == "system.slice"
        ]
        for system_slice in system_slices:
            docker_directories = [
                directory
                for directory in recursive_directories(system_slice)
                if docker_pattern.fullmatch(directory.name)
            ]
            for docker_directory in docker_directories:
                matches.extend(recursive_files(docker_directory, "PowerReport.csv"))

    return find_exactly_one(
        matches,
        f"PowerReport.csv for {container_name} container ID {container_id}",
    )


def normalize_power_report(
    source_path: Path,
    destination_path: Path,
    included_scopes: Optional[Sequence[str]] = None,
) -> List[PowerRow]:
    allowed_scopes = (
        None
        if included_scopes is None
        else {scope.strip().lower() for scope in included_scopes}
    )

    rows = read_csv_rows(source_path)
    if not rows:
        raise ValueError(f"Power report contains no data rows: {source_path}")

    fieldnames = list(rows[0].keys())
    timestamp_column = require_column(fieldnames, "timestamp", source_path)
    power_column = require_column(fieldnames, "power", source_path)
    scope_column = require_column(fieldnames, "scope", source_path)

    normalized_values = []
    for row in rows:
        scope = str(row.get(scope_column, "")).strip().lower()
        if not scope:
            raise ValueError(f"A blank scope value was found in {source_path}.")
        if allowed_scopes is not None and scope not in allowed_scopes:
            continue
        normalized_values.append(
            (
                parse_number(row.get(timestamp_column, ""), f"timestamp in {source_path}"),
                parse_number(row.get(power_column, ""), f"power in {source_path}"),
                scope,
            )
        )

    if not normalized_values:
        requested = (
            "all scopes"
            if allowed_scopes is None
            else ", ".join(sorted(allowed_scopes))
        )
        raise ValueError(
            f"Power report contains no rows for {requested}: {source_path}"
        )

    normalized_values.sort(key=lambda item: (item[2], item[0]))
    indexed_rows = [
        PowerRow(timestamp=timestamp, power=power, scope=scope, csv_row=index + 2)
        for index, (timestamp, power, scope) in enumerate(normalized_values)
    ]

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with destination_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp", "power", "scope"])
        writer.writeheader()
        for row in indexed_rows:
            writer.writerow(
                {
                    "timestamp": format_number(row.timestamp),
                    "power": format_number(row.power),
                    "scope": row.scope,
                }
            )

    return indexed_rows


def calculate_interval_result(
    rows: Sequence[PowerRow],
    report_name: str,
    scope: str,
    experiment_start_ms: Optional[float],
    experiment_stop_ms: Optional[float],
    experiment_start_seconds: Optional[float],
    experiment_stop_seconds: Optional[float],
    use_all_values: bool = False,
    start_delay_minutes: float = 0.0,
) -> Dict[str, object]:
    if not math.isfinite(start_delay_minutes) or start_delay_minutes < 0:
        raise ValueError("start_delay_minutes must be a finite, non-negative number.")

    scope_rows = sorted(
        (row for row in rows if row.scope.lower() == scope.lower()),
        key=lambda row: row.timestamp,
    )
    if not scope_rows:
        raise ValueError(f"Report {report_name!r} has no {scope!r} rows.")

    if use_all_values:
        # The first measurement supplies the preceding timestamp for the first
        # weighted interval. All complete intervals after it are considered.
        if len(scope_rows) < 2:
            raise ValueError(
                f"Report {report_name!r} must contain at least two {scope!r} "
                "samples to calculate a weighted average over all values."
            )
        start_index = 1
        stop_index = len(scope_rows) - 1
    else:
        if (
            experiment_start_ms is None
            or experiment_stop_ms is None
            or experiment_start_seconds is None
            or experiment_stop_seconds is None
        ):
            raise ValueError(
                "Experiment timestamps are required unless --all-values is used."
            )

        start_index = next(
            (
                index
                for index, row in enumerate(scope_rows)
                if row.timestamp >= experiment_start_ms
            ),
            -1,
        )
        stop_index = next(
            (
                index
                for index in range(len(scope_rows) - 1, -1, -1)
                if scope_rows[index].timestamp <= experiment_stop_ms
            ),
            -1,
        )

        if start_index < 0 or stop_index < 0 or stop_index < start_index:
            raise ValueError(
                f"No {scope!r} samples in {report_name!r} fall inside the experiment "
                f"interval {experiment_start_ms}..{experiment_stop_ms} ms."
            )

        # The formula needs the timestamp immediately preceding START.
        if start_index == 0:
            if len(scope_rows) < 2 or stop_index < 1:
                raise ValueError(
                    f"Report {report_name!r} does not contain at least two {scope!r} "
                    "samples inside or before the experiment interval, so a weighted "
                    "average cannot be calculated."
                )
            start_index = 1

    initial_start_index = start_index
    if start_delay_minutes > 0:
        delayed_start_timestamp_ms = (
            scope_rows[initial_start_index].timestamp
            + start_delay_minutes * 60_000.0
        )
        start_index = next(
            (
                index
                for index in range(initial_start_index, stop_index + 1)
                if scope_rows[index].timestamp >= delayed_start_timestamp_ms
            ),
            -1,
        )
        if start_index < 0:
            available_minutes = (
                scope_rows[stop_index].timestamp
                - scope_rows[initial_start_index].timestamp
            ) / 60_000.0
            raise ValueError(
                f"The requested start delay of {format_number(start_delay_minutes)} "
                f"minutes leaves no usable {scope!r} samples in {report_name!r}. "
                f"Only {format_number(max(0.0, available_minutes))} minutes are "
                "available from the initially selected START through STOP."
            )

    if stop_index < start_index:
        raise ValueError(
            f"No usable {scope!r} samples remain in {report_name!r} after "
            "reserving the first measurement as PRESTART or applying the start delay."
        )

    numerator = 0.0
    denominator = 0.0
    for index in range(start_index, stop_index + 1):
        delta_ms = scope_rows[index].timestamp - scope_rows[index - 1].timestamp
        if delta_ms < 0:
            raise ValueError(
                f"Timestamps are not ordered in {report_name!r} for scope {scope!r}."
            )
        numerator += scope_rows[index].power * delta_ms
        denominator += delta_ms

    if denominator == 0:
        raise ValueError(
            f"The weighted-average denominator is zero in {report_name!r} "
            f"for scope {scope!r}."
        )

    return {
        "report_file": report_name,
        "scope": scope,
        "experiment_start_seconds": (
            "" if use_all_values else format_number(experiment_start_seconds)
        ),
        "experiment_stop_seconds": (
            "" if use_all_values else format_number(experiment_stop_seconds)
        ),
        "experiment_start_ms": (
            "" if use_all_values else format_number(experiment_start_ms)
        ),
        "experiment_stop_ms": (
            "" if use_all_values else format_number(experiment_stop_ms)
        ),
        "START": scope_rows[start_index].csv_row,
        "STOP": scope_rows[stop_index].csv_row,
        "PRESTART": scope_rows[start_index - 1].csv_row,
        "PRESTOP": scope_rows[stop_index - 1].csv_row,
        "selected_start_timestamp_ms": format_number(scope_rows[start_index].timestamp),
        "selected_stop_timestamp_ms": format_number(scope_rows[stop_index].timestamp),
        "weighted_average_power": format_number(numerator / denominator),
    }


def process_sensor_output(
    sensor_output_directory: Path,
    use_all_values: bool = False,
    include_dram: bool = True,
    source_archive_name: str = "source_archive",
    start_delay_minutes: float = 0.0,
) -> Path:
    print(f"Processing: {sensor_output_directory}")
    summary_directory = sensor_output_directory / "summary"
    summary_directory.mkdir(parents=True, exist_ok=True)

    swatts_directory = find_exactly_one(
        (
            directory
            for directory in recursive_directories(sensor_output_directory)
            if directory.name.lower() == "swatts"
        ),
        f"swatts directory under {sensor_output_directory}",
    )
    container_ids_file = find_exactly_one(
        recursive_files(sensor_output_directory, "container_ids.txt"),
        f"container_ids.txt under {sensor_output_directory}",
    )

    rapl_source = find_exactly_one(
        (
            path
            for path in recursive_files(swatts_directory, "PowerReport.csv")
            if path.parent.name.lower() == "sensor-rapl"
        ),
        "sensor-rapl PowerReport.csv",
    )
    global_source = find_exactly_one(
        (
            path
            for path in recursive_files(swatts_directory, "PowerReport.csv")
            if path.parent.name.lower() == "sensor-global"
        ),
        "sensor-global PowerReport.csv",
    )

    sensor_directories = [
        directory
        for directory in recursive_directories(swatts_directory)
        if directory.name.lower().startswith("sensor-")
        and directory.name.lower() not in {"sensor-rapl", "sensor-global"}
    ]
    if not sensor_directories:
        raise ValueError(
            f"No container-specific sensor-* directory was found under {swatts_directory}."
        )

    anvil_id = get_container_id(container_ids_file, "anvil")
    alto_id = get_container_id(container_ids_file, "alto")
    anvil_source = find_container_power_report(sensor_directories, anvil_id, "anvil")
    alto_source = find_container_power_report(sensor_directories, alto_id, "alto")

    experiment_start_seconds: Optional[float] = None
    experiment_stop_seconds: Optional[float] = None
    experiment_start_ms: Optional[float] = None
    experiment_stop_ms: Optional[float] = None

    # In all-values mode, confirmed_blocks.csv is neither located nor opened.
    if not use_all_values:
        confirmed_blocks_file = find_exactly_one(
            recursive_files(sensor_output_directory, "confirmed_blocks.csv"),
            f"confirmed_blocks.csv under {sensor_output_directory}",
        )
        confirmed_rows = read_csv_rows(confirmed_blocks_file)
        if not confirmed_rows:
            raise ValueError(
                f"confirmed_blocks.csv contains no data rows: {confirmed_blocks_file}. "
                "Use --all-values to process the complete PowerReport series without "
                "reading confirmed_blocks.csv."
            )

        confirmed_fieldnames = list(confirmed_rows[0].keys())
        timestamp_column = require_column(
            confirmed_fieldnames, "timestamp", confirmed_blocks_file
        )
        experiment_start_seconds = parse_number(
            confirmed_rows[0].get(timestamp_column, ""),
            "first confirmed_blocks timestamp",
        )
        experiment_stop_seconds = parse_number(
            confirmed_rows[-1].get(timestamp_column, ""),
            "last confirmed_blocks timestamp",
        )
        experiment_start_ms = experiment_start_seconds * 1000.0
        experiment_stop_ms = experiment_stop_seconds * 1000.0
        if experiment_stop_ms < experiment_start_ms:
            raise ValueError(
                "The last confirmed_blocks timestamp is earlier than the first timestamp."
            )

    reports = [
        (rapl_source, "PowerReport-RAPL.csv"),
        (global_source, "PowerReport-SWGlobal.csv"),
        (anvil_source, "PowerReport-SWAnvil.csv"),
        (alto_source, "PowerReport-SWAlto.csv"),
    ]

    scopes = ("cpu", "dram") if include_dram else ("cpu",)

    results: List[Dict[str, object]] = []
    for source, output_name in reports:
        destination = summary_directory / output_name
        normalized_rows = normalize_power_report(
            source, destination, included_scopes=scopes
        )
        for scope in scopes:
            results.append(
                calculate_interval_result(
                    rows=normalized_rows,
                    report_name=output_name,
                    scope=scope,
                    experiment_start_ms=experiment_start_ms,
                    experiment_stop_ms=experiment_stop_ms,
                    experiment_start_seconds=experiment_start_seconds,
                    experiment_stop_seconds=experiment_stop_seconds,
                    use_all_values=use_all_values,
                    start_delay_minutes=start_delay_minutes,
                )
            )

    result_path = summary_directory / f"PowerSummaryResults_{source_archive_name}.csv"
    with result_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(results)

    print(f"Created: {result_path}")
    return result_path


def extraction_folder_for(archive_path: Path) -> Path:
    lower_name = archive_path.name.lower()
    if lower_name.endswith(".tar.gz"):
        folder_name = archive_path.name[:-7]
    elif lower_name.endswith(".tgz"):
        folder_name = archive_path.name[:-4]
    else:
        raise ValueError(f"Input file must have a .tar.gz or .tgz extension: {archive_path}")
    if not folder_name.strip():
        raise ValueError(f"Cannot determine an extraction-folder name from: {archive_path}")
    return archive_path.parent / folder_name


def safe_extract_tar(archive_path: Path, destination: Path) -> None:
    """Extract a tar archive while rejecting path traversal and link escapes."""
    destination_resolved = destination.resolve()
    with tarfile.open(archive_path, mode="r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            member_path = (destination / member.name).resolve()
            try:
                member_path.relative_to(destination_resolved)
            except ValueError as exc:
                raise ValueError(f"Unsafe archive member path: {member.name}") from exc

            if member.issym() or member.islnk():
                link_target = (member_path.parent / member.linkname).resolve()
                try:
                    link_target.relative_to(destination_resolved)
                except ValueError as exc:
                    raise ValueError(
                        f"Unsafe archive link target in {member.name}: {member.linkname}"
                    ) from exc

        try:
            # Python 3.12+ supports an explicit extraction filter. Paths and
            # links have already been validated above.
            archive.extractall(destination, members=members, filter="fully_trusted")
        except TypeError:
            # Compatibility with Python 3.8-3.11.
            archive.extractall(destination, members=members)


def find_sensor_output_directories(extract_root: Path) -> List[Path]:
    directories: List[Path] = []
    if extract_root.name.lower() == "sensor_output":
        directories.append(extract_root.resolve())
    directories.extend(
        path.resolve()
        for path in recursive_directories(extract_root)
        if path.name.lower() == "sensor_output"
    )
    return sorted(set(directories), key=lambda item: str(item).lower())


def nonnegative_finite_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Expected a numeric number of minutes, got {value!r}."
        ) from exc

    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError(
            "The number of minutes must be finite and greater than or equal to zero."
        )
    return number


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract a sensor .tar.gz/.tgz archive, normalize four PowerReport.csv "
            "files, and calculate weighted-average power for CPU and, unless --nodram is used, DRAM."
        )
    )
    parser.add_argument("archive_file", type=Path, help="Path to the .tar.gz or .tgz archive")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace the extraction folder if it already exists",
    )
    parser.add_argument(
        "--all-values",
        "--all_values",
        action="store_true",
        help=(
            "Ignore the confirmed-block START/STOP interval and calculate each "
            "weighted average for each requested scope over the complete available series"
        ),
    )
    parser.add_argument(
        "--nodram",
        action="store_true",
        help=(
            "Process CPU data only: exclude DRAM rows from normalized reports "
            "and from the archive-specific PowerSummaryResults_<archive>.csv file"
        ),
    )
    parser.add_argument(
        "--start-delay-minutes",
        "--start-delay",
        type=nonnegative_finite_float,
        default=0.0,
        metavar="MINUTES",
        help=(
            "Begin the weighted-average calculation at the first sample at or "
            "after MINUTES have elapsed from the initially selected START. "
            "STOP is unchanged; fractional minutes are accepted."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    print(f"PowerReportSummary version: {SCRIPT_VERSION}")

    try:
        locale.setlocale(locale.LC_NUMERIC, "")
    except locale.Error:
        # Invariant parsing still works if the operating-system locale is unavailable.
        pass

    args = parse_args(argv)
    print(
        "Processing mode: "
        + (
            "all PowerReport values; confirmed_blocks.csv is ignored"
            if args.all_values
            else "confirmed-block interval"
        )
    )
    print("Power scopes: " + ("CPU only" if args.nodram else "CPU and DRAM"))
    print(
        "Weighted-average start delay: "
        f"{format_number(args.start_delay_minutes)} minute(s)"
    )
    archive_path = args.archive_file.expanduser().resolve()
    if not archive_path.is_file():
        raise FileNotFoundError(f"Archive file does not exist: {archive_path}")

    extract_root = extraction_folder_for(archive_path)
    if extract_root.exists():
        if not args.force:
            raise FileExistsError(
                f"Extraction folder already exists: {extract_root}. Re-run with --force to replace it."
            )
        if extract_root.is_dir():
            shutil.rmtree(extract_root)
        else:
            extract_root.unlink()

    extract_root.mkdir(parents=True)
    try:
        safe_extract_tar(archive_path, extract_root)
        sensor_output_directories = find_sensor_output_directories(extract_root)
        if not sensor_output_directories:
            raise ValueError(f"No sensor_output directory was found after extracting {archive_path}.")

        for sensor_output_directory in sensor_output_directories:
            process_sensor_output(
                sensor_output_directory,
                use_all_values=args.all_values,
                include_dram=not args.nodram,
                source_archive_name=extract_root.name,
                start_delay_minutes=args.start_delay_minutes,
            )
    except Exception:
        # Keep the extracted folder for inspection, matching the PowerShell script's behavior.
        raise

    print(f"Done. Extracted folder: {extract_root}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
