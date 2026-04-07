from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lizard_languages import get_reader_for


@dataclass(frozen=True)
class ParsedLizardCsv:
    functions_total: int
    unique_files: set[str]
    nloc_total: int
    ccn_total: int
    length_total: int
    max_ccn: int
    max_length: int
    technology_metrics: dict[str, dict[str, Any]]
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
            technology_rows=[],
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
    technology_metrics: dict[str, dict[str, Any]] = {}
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

        _merge_technology_metrics(technology_metrics, parsed.technology_metrics)

    technology_rows = _build_technology_rows(technology_metrics)
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
        technology_rows=technology_rows,
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
    technology_metrics: dict[str, dict[str, Any]] = {}
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
                    technology_metrics={},
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

                technology = _detect_technology(file_value)
                if technology not in technology_metrics:
                    technology_metrics[technology] = {
                        'files': set(),
                        'functions': 0,
                        'nloc_total': 0,
                        'ccn_total': 0,
                        'length_total': 0,
                        'max_ccn': 0,
                        'max_length': 0,
                    }

                technology_entry = technology_metrics[technology]
                if file_value:
                    technology_entry['files'].add(file_value)
                technology_entry['functions'] += 1
                technology_entry['nloc_total'] += nloc_value
                technology_entry['ccn_total'] += ccn_value
                technology_entry['length_total'] += length_value
                technology_entry['max_ccn'] = max(technology_entry['max_ccn'], ccn_value)
                technology_entry['max_length'] = max(technology_entry['max_length'], length_value)
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
        technology_metrics=technology_metrics,
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


def _detect_technology(file_path_value: str) -> str:
    if not file_path_value:
        return 'Other'

    reader = get_reader_for(file_path_value)
    if reader is None:
        return 'Other'

    language_names = getattr(reader, 'language_names', [])
    if not language_names:
        return 'Other'

    return _format_language_name(str(language_names[0]))


def _format_language_name(language_name: str) -> str:
    normalized = language_name.strip().lower()

    aliases = {
        'cpp': 'C/C++',
        'c': 'C/C++',
        'csharp': 'C#',
        'javascript': 'JavaScript',
        'js': 'JavaScript',
        'typescript': 'TypeScript',
        'objectivec': 'Objective-C',
        'objective-c': 'Objective-C',
        'objc': 'Objective-C',
        'gdscript': 'GDScript',
        'go': 'Go',
        'java': 'Java',
        'kotlin': 'Kotlin',
        'python': 'Python',
        'php': 'PHP',
        'ruby': 'Ruby',
        'swift': 'Swift',
        'scala': 'Scala',
        'rust': 'Rust',
        'lua': 'Lua',
        'fortran': 'Fortran',
        'tnsdl': 'TNSDL',
        'ttcn': 'TTCN',
        'ttcn3': 'TTCN',
    }

    if normalized in aliases:
        return aliases[normalized]

    return language_name.strip() or 'Other'


def _merge_technology_metrics(
    aggregate: dict[str, dict[str, Any]],
    parsed: dict[str, dict[str, Any]],
) -> None:
    for technology, values in parsed.items():
        if technology not in aggregate:
            aggregate[technology] = {
                'files': set(),
                'functions': 0,
                'nloc_total': 0,
                'ccn_total': 0,
                'length_total': 0,
                'max_ccn': 0,
                'max_length': 0,
            }

        target = aggregate[technology]
        target['files'].update(values.get('files', set()))
        target['functions'] += int(values.get('functions', 0))
        target['nloc_total'] += int(values.get('nloc_total', 0))
        target['ccn_total'] += int(values.get('ccn_total', 0))
        target['length_total'] += int(values.get('length_total', 0))
        target['max_ccn'] = max(int(target['max_ccn']), int(values.get('max_ccn', 0)))
        target['max_length'] = max(int(target['max_length']), int(values.get('max_length', 0)))


def _build_technology_rows(technology_metrics: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for technology, values in technology_metrics.items():
        functions_count = int(values.get('functions', 0))
        nloc_total = int(values.get('nloc_total', 0))
        ccn_total = int(values.get('ccn_total', 0))
        length_total = int(values.get('length_total', 0))
        max_ccn = int(values.get('max_ccn', 0))
        max_length = int(values.get('max_length', 0))
        files_count = len(values.get('files', set()))

        rows.append(
            {
                'technology': technology,
                'filesFormatted': _format_int(files_count),
                'functionsFormatted': _format_int(functions_count),
                'nlocFormatted': _format_int(nloc_total),
                'averageCcn': _format_average(ccn_total, functions_count),
                'maxCcnFormatted': _format_int(max_ccn),
                'averageLength': _format_average(length_total, functions_count),
                'maxLengthFormatted': _format_int(max_length),
                'nlocRaw': nloc_total,
            }
        )

    rows.sort(key=lambda row: (-int(row['nlocRaw']), str(row['technology']).lower()))
    return rows


def _create_summary_payload(
    csv_files: list[Path],
    functions_total: int,
    unique_files: set[str],
    nloc_total: int,
    ccn_total: int,
    length_total: int,
    max_ccn: int,
    max_length: int,
    technology_rows: list[dict[str, Any]],
    has_data_quality_issues: bool,
) -> dict[str, Any]:
    average_ccn = _format_average(ccn_total, functions_total)
    average_length = _format_average(length_total, functions_total)
    status = _resolve_status(csv_count=len(csv_files), has_data_quality_issues=has_data_quality_issues)

    metadata = {
        'metadata.files.unique': len(unique_files),
        'metadata.functions.total': functions_total,
        'metadata.nloc.total': nloc_total,
        'metadata.ccn.average': average_ccn,
        'metadata.ccn.max': max_ccn,
        'metadata.length.average': average_length,
        'metadata.length.max': max_length,
    }

    markdown_lines = [
        '## Lizard',
        '',
        (
            f'- NLOC: {_format_int(nloc_total)} / '
            f'Unique files: {_format_int(len(unique_files))} / '
            f'Functions: {_format_int(functions_total)}'
        ),
        (
            f'- Average CCN: {average_ccn} / '
            f'Max CCN: {_format_int(max_ccn)} / '
            f'Average length: {average_length} / '
            f'Max length: {_format_int(max_length)}'
        ),
        '',
        '### Metrics by Technology',
        '',
        '| Technology | Files | Functions | Total NLOC | Avg CCN | Max CCN | Avg Length | Max Length |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |',
    ]

    if not technology_rows:
        markdown_lines.append('| _none_ | 0 | 0 | 0 | 0 | 0 | 0 | 0 |')
    else:
        for row in technology_rows:
            markdown_lines.append(
                f"| {row.get('technology', 'Other')} | {row.get('filesFormatted', '0')} | {row.get('functionsFormatted', '0')} | "
                f"{row.get('nlocFormatted', '0')} | {row.get('averageCcn', '0')} | {row.get('maxCcnFormatted', '0')} | "
                f"{row.get('averageLength', '0')} | {row.get('maxLengthFormatted', '0')} |"
            )

    template_model = {
        'metrics': {
            'uniqueFilesFormatted': _format_int(len(unique_files)),
            'functionsTotalFormatted': _format_int(functions_total),
            'nlocTotalFormatted': _format_int(nloc_total),
            'averageCcn': average_ccn,
            'maxCcnFormatted': _format_int(max_ccn),
            'averageLength': average_length,
            'maxLengthFormatted': _format_int(max_length),
        },
        'technologyRows': technology_rows,
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
