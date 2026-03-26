from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ParsedLizardCsv:
    functions_total: int
    unique_files: set[str]
    nloc_total: int
    ccn_total: int
    length_total: int
    max_ccn: int
    max_length: int
    top_functions: list[dict[str, Any]]
    had_parse_failure: bool
    invalid_rows: int


def extract_lizard_summary(results_directory: str | Path) -> dict[str, Any]:
    target = Path(results_directory)

    try:
        entries = list(target.iterdir())
    except Exception:
        return _create_summary_payload(
            csv_files=[],
            functions_total=0,
            unique_files=set(),
            nloc_total=0,
            ccn_total=0,
            length_total=0,
            max_ccn=0,
            max_length=0,
            top_functions=[],
            has_data_quality_issues=True,
        )

    csv_files = sorted(
        [
            entry
            for entry in entries
            if entry.is_file() and entry.suffix.lower() == '.csv' and entry.name != 'summary.csv'
        ],
        key=lambda value: value.name,
    )

    functions_total = 0
    unique_files: set[str] = set()
    nloc_total = 0
    ccn_total = 0
    length_total = 0
    max_ccn = 0
    max_length = 0
    top_functions: list[dict[str, Any]] = []
    had_parse_failures = False
    invalid_rows_total = 0

    for csv_file in csv_files:
        parsed = _parse_lizard_csv(csv_file)
        functions_total += parsed.functions_total
        unique_files.update(parsed.unique_files)
        nloc_total += parsed.nloc_total
        ccn_total += parsed.ccn_total
        length_total += parsed.length_total
        max_ccn = max(max_ccn, parsed.max_ccn)
        max_length = max(max_length, parsed.max_length)
        invalid_rows_total += parsed.invalid_rows
        had_parse_failures = had_parse_failures or parsed.had_parse_failure

        top_functions.extend(parsed.top_functions)

    top_functions = _pick_top_functions(top_functions, limit=10)
    has_data_quality_issues = had_parse_failures or invalid_rows_total > 0 or functions_total == 0

    return _create_summary_payload(
        csv_files=csv_files,
        functions_total=functions_total,
        unique_files=unique_files,
        nloc_total=nloc_total,
        ccn_total=ccn_total,
        length_total=length_total,
        max_ccn=max_ccn,
        max_length=max_length,
        top_functions=top_functions,
        has_data_quality_issues=has_data_quality_issues,
    )


def _parse_lizard_csv(file_path: Path) -> ParsedLizardCsv:
    functions_total = 0
    unique_files: set[str] = set()
    nloc_total = 0
    ccn_total = 0
    length_total = 0
    max_ccn = 0
    max_length = 0
    top_functions: list[dict[str, Any]] = []
    had_parse_failure = False
    invalid_rows = 0

    try:
        with file_path.open('r', encoding='utf-8', errors='replace', newline='') as handle:
            reader = csv.reader(handle)
            header = next(reader, None)
            column_indexes = _resolve_column_indexes(header)
            if column_indexes is None:
                return ParsedLizardCsv(
                    functions_total=0,
                    unique_files=set(),
                    nloc_total=0,
                    ccn_total=0,
                    length_total=0,
                    max_ccn=0,
                    max_length=0,
                    top_functions=[],
                    had_parse_failure=True,
                    invalid_rows=0,
                )

            for row in reader:
                if len(row) <= column_indexes['length']:
                    invalid_rows += 1
                    continue

                try:
                    nloc_value = int(row[column_indexes['nloc']])
                    ccn_value = int(row[column_indexes['ccn']])
                    length_value = int(row[column_indexes['length']])
                except (TypeError, ValueError):
                    invalid_rows += 1
                    continue

                file_value = row[column_indexes['file']].strip()
                function_name = row[column_indexes['function']].strip()
                location_value = row[column_indexes['location']].strip()

                functions_total += 1
                nloc_total += nloc_value
                ccn_total += ccn_value
                length_total += length_value
                max_ccn = max(max_ccn, ccn_value)
                max_length = max(max_length, length_value)

                if file_value:
                    unique_files.add(file_value)

                top_functions.append(
                    {
                        'function': function_name or 'unknown',
                        'file': file_value or 'unknown',
                        'location': location_value or 'unknown',
                        'ccn': ccn_value,
                        'nloc': nloc_value,
                        'length': length_value,
                    }
                )
    except Exception:
        had_parse_failure = True

    return ParsedLizardCsv(
        functions_total=functions_total,
        unique_files=unique_files,
        nloc_total=nloc_total,
        ccn_total=ccn_total,
        length_total=length_total,
        max_ccn=max_ccn,
        max_length=max_length,
        top_functions=_pick_top_functions(top_functions, limit=10),
        had_parse_failure=had_parse_failure,
        invalid_rows=invalid_rows,
    )


def _resolve_column_indexes(header: list[str] | None) -> dict[str, int] | None:
    if not header:
        return None

    normalized = [value.strip().lower() for value in header]
    required = {
        'nloc': 'nloc',
        'ccn': 'ccn',
        'length': 'length',
        'location': 'location',
        'file': 'file',
        'function': 'function',
    }

    indexes: dict[str, int] = {}
    for key, column_name in required.items():
        if column_name not in normalized:
            return None
        indexes[key] = normalized.index(column_name)

    return indexes


def _pick_top_functions(candidates: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    ordered = sorted(
        candidates,
        key=lambda item: (
            -int(item.get('ccn', 0)),
            -int(item.get('nloc', 0)),
            -int(item.get('length', 0)),
            str(item.get('function', '')),
        ),
    )
    return ordered[:limit]


def _create_summary_payload(
    csv_files: list[Path],
    functions_total: int,
    unique_files: set[str],
    nloc_total: int,
    ccn_total: int,
    length_total: int,
    max_ccn: int,
    max_length: int,
    top_functions: list[dict[str, Any]],
    has_data_quality_issues: bool,
) -> dict[str, Any]:
    generated_at = _iso_now()
    average_ccn = _format_average(ccn_total, functions_total)
    average_length = _format_average(length_total, functions_total)
    status = _resolve_status(csv_count=len(csv_files), has_data_quality_issues=has_data_quality_issues)

    metadata = {
        'metadata.csv.files': len(csv_files),
        'metadata.files.unique': len(unique_files),
        'metadata.functions.total': functions_total,
        'metadata.nloc.total': nloc_total,
        'metadata.ccn.average': average_ccn,
        'metadata.ccn.max': max_ccn,
        'metadata.length.average': average_length,
        'metadata.length.max': max_length,
        'metadata.generated.at': generated_at,
    }

    markdown_lines = [
        '## Lizard',
        '',
        f'- CSV files: {_format_int(len(csv_files))}',
        f'- Unique files analyzed: {_format_int(len(unique_files))}',
        f'- Functions analyzed: {_format_int(functions_total)}',
        f'- Total NLOC: {_format_int(nloc_total)}',
        f'- Average CCN: {average_ccn}',
        f'- Max CCN: {_format_int(max_ccn)}',
        f'- Average length: {average_length}',
        f'- Max length: {_format_int(max_length)}',
        '',
        '### Top Complex Functions',
        '',
        '| Function | File | CCN | NLOC | Length |',
        '| --- | --- | ---: | ---: | ---: |',
    ]

    if not top_functions:
        markdown_lines.append('| _none_ | _none_ | 0 | 0 | 0 |')
    else:
        for row in top_functions:
            markdown_lines.append(
                f"| {row.get('function', 'unknown')} | {row.get('file', 'unknown')} | {_format_int(int(row.get('ccn', 0)))} | "
                f"{_format_int(int(row.get('nloc', 0)))} | {_format_int(int(row.get('length', 0)))} |"
            )

    template_model = {
        'generatedAt': generated_at,
        'metrics': {
            'csvFilesFormatted': _format_int(len(csv_files)),
            'uniqueFilesFormatted': _format_int(len(unique_files)),
            'functionsTotalFormatted': _format_int(functions_total),
            'nlocTotalFormatted': _format_int(nloc_total),
            'averageCcn': average_ccn,
            'maxCcnFormatted': _format_int(max_ccn),
            'averageLength': average_length,
            'maxLengthFormatted': _format_int(max_length),
        },
        'topFunctions': [
            {
                **row,
                'ccnFormatted': _format_int(int(row.get('ccn', 0))),
                'nlocFormatted': _format_int(int(row.get('nloc', 0))),
                'lengthFormatted': _format_int(int(row.get('length', 0))),
            }
            for row in top_functions
        ],
    }

    return {
        'tool': 'lizard',
        'status': status,
        'metadata': metadata,
        'markdown': '\n'.join(markdown_lines),
        'templateModel': template_model,
    }


def _format_average(total: int, count: int) -> str:
    if count <= 0:
        return '0'

    average = float(total) / float(count)
    if average.is_integer():
        return _format_int(int(average))
    return f'{average:,.2f}'.rstrip('0').rstrip('.')


def _format_int(value: int) -> str:
    return f'{value:,}'


def _resolve_status(csv_count: int, has_data_quality_issues: bool) -> str:
    if csv_count == 0:
        return 'failed'
    if has_data_quality_issues:
        return 'partial'
    return 'success'


def _iso_now() -> str:
    local_now = datetime.now().astimezone()
    return f"{local_now.strftime('%Y-%m-%d %H:%M:%S')} {_format_gmt_offset(local_now.strftime('%z'))}"


def _format_gmt_offset(offset: str) -> str:
    if len(offset) != 5:
        return 'GMT+0'

    sign = offset[0]
    hours = int(offset[1:3])
    minutes = int(offset[3:5])

    if minutes == 0:
        return f'GMT{sign}{hours}'

    return f'GMT{sign}{hours}:{minutes:02d}'
