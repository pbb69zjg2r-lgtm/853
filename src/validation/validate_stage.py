"""
Contracts-driven validator for V2 pipeline stage outputs.

Validates JSON/JSONL files against contracts/fields.yaml and
contracts/output_contracts.yaml. Uses src.core.contracts for all lookups.

Usage:
    python validate_stage.py <run_dir> <stage_name>
    python validate_stage.py <run_dir> --all
    python validate_stage.py <file.jsonl> <schema_name>
"""

import json
import os
import sys

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.contracts import (  # noqa: E402
    get_field_schema,
    get_required_fields,
    get_enum_field_values,
    get_enum_field_dictionary,
    get_dictionary,
    get_stage_outputs,
    get_stage_inputs,
    get_all_stages,
    get_output_required_fields,
    get_output_forbidden_fields,
)


# ---------------------------------------------------------------------------
# Core validation logic
# ---------------------------------------------------------------------------

def _check_type(value, expected_type):
    """Return error message or None."""
    if expected_type == "string":
        return None if isinstance(value, str) else f"expected string, got {type(value).__name__}"
    if expected_type == "integer":
        return None if isinstance(value, int) and not isinstance(value, bool) else f"expected integer, got {type(value).__name__}"
    if expected_type == "number":
        return None if isinstance(value, (int, float)) and not isinstance(value, bool) else f"expected number, got {type(value).__name__}"
    if expected_type == "array":
        return None if isinstance(value, list) else f"expected array, got {type(value).__name__}"
    if expected_type == "object":
        return None if isinstance(value, dict) else f"expected object, got {type(value).__name__}"
    if expected_type == "enum":
        return None  # value check handled separately
    return None


def _check_enum(value, spec):
    """Return error message or None. Checks inline values or dictionary reference."""
    valid = None
    if "values" in spec:
        valid = spec["values"]
    elif "dictionary" in spec:
        try:
            valid = get_dictionary(spec["dictionary"])
        except KeyError:
            return f"unknown dictionary: {spec['dictionary']}"
    else:
        return None  # no enum constraint

    if value not in valid:
        return f"invalid value '{value}', allowed: {valid}"
    return None


def validate_record(record, schema_name):
    """Validate a single dict against a named schema.

    Returns (errors: list[str], warnings: list[str]).
    """
    errors = []
    warnings = []

    if not isinstance(record, dict):
        errors.append(f"record is not a dict: {type(record).__name__}")
        return errors, warnings

    schema = get_field_schema(schema_name)

    # Required fields
    required = get_required_fields(schema_name)
    for field in required:
        if field not in record or record[field] is None:
            errors.append(f"missing required field: {field}")

    # Check each field
    for key, value in record.items():
        if value is None:
            continue

        # Find field spec — try exact match, then dotted path
        spec = schema.get(key)
        if spec is None:
            warnings.append(f"unknown field '{key}' not in schema '{schema_name}'")
            continue

        expected_type = spec.get("type", "string")
        type_err = _check_type(value, expected_type)
        if type_err:
            errors.append(f"field '{key}': {type_err}")
            continue

        # Enum check
        if expected_type == "enum":
            enum_err = _check_enum(value, spec)
            if enum_err:
                errors.append(f"field '{key}': {enum_err}")

        # Recurse into nested objects
        if expected_type == "object" and isinstance(value, dict):
            _validate_nested(value, spec, key, errors)

        # Recurse into arrays
        if expected_type == "array" and isinstance(value, list):
            _validate_array(value, spec, key, errors)

    return errors, warnings


def _validate_nested(obj, spec, path, errors):
    """Validate a nested object against its fields spec."""
    fields = spec.get("fields", {})
    if not fields:
        return

    for fname, fspec in fields.items():
        if fname not in obj:
            if fspec.get("required"):
                errors.append(f"field '{path}.{fname}': missing required field")
            continue
        val = obj[fname]
        if val is None:
            continue

        ftype = fspec.get("type", "string")
        type_err = _check_type(val, ftype)
        if type_err:
            errors.append(f"field '{path}.{fname}': {type_err}")
            continue
        if ftype == "enum":
            enum_err = _check_enum(val, fspec)
            if enum_err:
                errors.append(f"field '{path}.{fname}': {enum_err}")
        if ftype == "object" and isinstance(val, dict):
            _validate_nested(val, fspec, f"{path}.{fname}", errors)
        if ftype == "array" and isinstance(val, list):
            _validate_array(val, fspec, f"{path}.{fname}", errors)


def _validate_array(arr, spec, path, errors):
    """Validate an array against its item_schema."""
    item_schema = spec.get("item_schema", {})
    if not item_schema:
        return

    for idx, item in enumerate(arr):
        if not isinstance(item, dict):
            continue
        for fname, fspec in item_schema.items():
            if fname not in item:
                if fspec.get("required"):
                    errors.append(f"field '{path}[{idx}].{fname}': missing required field")
                continue
            val = item[fname]
            if val is None:
                continue

            ftype = fspec.get("type", "string")
            type_err = _check_type(val, ftype)
            if type_err:
                errors.append(f"field '{path}[{idx}].{fname}': {type_err}")
            if ftype == "enum":
                enum_err = _check_enum(val, fspec)
                if enum_err:
                    errors.append(f"field '{path}[{idx}].{fname}': {enum_err}")


def validate_forbidden(record, output_name):
    """Check for forbidden fields in a trusted output. Returns error list."""
    errors = []
    forbidden = get_output_forbidden_fields(output_name)
    for field in forbidden:
        if field in record:
            errors.append(f"forbidden field '{field}' in trusted output '{output_name}'")
    return errors


# ---------------------------------------------------------------------------
# File-level validation
# ---------------------------------------------------------------------------

def validate_jsonl(filepath, schema_name):
    """Validate a JSONL file against a schema. Returns (all_errors, all_warnings)."""
    all_errors = []
    all_warnings = []
    record_count = 0

    with open(filepath, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                all_errors.append(f"line {line_no}: invalid JSON: {e}")
                continue

            record_count += 1
            errs, warns = validate_record(record, schema_name)
            for e in errs:
                all_errors.append(f"line {line_no} (record #{record_count}): {e}")
            for w in warns:
                all_warnings.append(f"line {line_no} (record #{record_count}): {w}")

    return all_errors, all_warnings, record_count


def validate_json(filepath, schema_name):
    """Validate a JSON file (single object or array) against a schema."""
    all_errors = []
    all_warnings = []
    record_count = 0

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data if isinstance(data, list) else [data]
    for idx, record in enumerate(records):
        record_count += 1
        errs, warns = validate_record(record, schema_name)
        for e in errs:
            all_errors.append(f"record #{idx}: {e}")
        for w in warns:
            all_warnings.append(f"record #{idx}: {w}")

    return all_errors, all_warnings, record_count


def validate_file(filepath, schema_name):
    """Auto-detect JSON vs JSONL and validate."""
    if not os.path.exists(filepath):
        return [f"file not found: {filepath}"], [], 0

    if filepath.endswith(".jsonl"):
        return validate_jsonl(filepath, schema_name)
    else:
        return validate_json(filepath, schema_name)


# ---------------------------------------------------------------------------
# Stage-level validation
# ---------------------------------------------------------------------------

SCHEMA_FOR_OUTPUT = {
    "source_blocks.jsonl": "source_block",
    "document_structure.json": "source_block",
    "evidence_units.jsonl": "evidence_unit",
    "context_packs.jsonl": "context_pack",
    "draft_entries.jsonl": "draft_entry",
    "verifier_report.json": "verifier_report",
    "review_export.json": "review_export",
}


def _guess_schema(filename):
    for key, schema in SCHEMA_FOR_OUTPUT.items():
        if filename.endswith(key) or filename == key:
            return schema
    return None


def validate_stage(run_dir, stage_name):
    """Validate all output files of a stage.

    Returns dict: {filename: (errors, warnings, record_count)}
    """
    results = {}
    outputs = get_stage_outputs(stage_name)

    for output_rel in outputs:
        # Skip patterns like "contracts/*" and "input/*"
        if "*" in output_rel:
            continue

        filepath = os.path.join(run_dir, output_rel)
        schema_name = _guess_schema(output_rel)

        if schema_name is None:
            results[output_rel] = ([f"no schema mapping for {output_rel}"], [], 0)
            continue

        if not os.path.exists(filepath):
            results[output_rel] = ([f"file not found: {filepath}"], [], 0)
            continue

        errors, warnings, count = validate_file(filepath, schema_name)
        results[output_rel] = (errors, warnings, count)

    return results


def validate_all_stages(run_dir):
    """Validate all stage outputs found in a run directory."""
    all_results = {}
    for stage_name in get_all_stages():
        outputs = get_stage_outputs(stage_name)
        has_files = any(
            os.path.exists(os.path.join(run_dir, o)) and "*" not in o
            for o in outputs
        )
        if has_files:
            all_results[stage_name] = validate_stage(run_dir, stage_name)
    return all_results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_results(results, verbose=False):
    """Print validation results as readable text."""
    total_errors = 0
    total_warnings = 0
    total_records = 0

    if isinstance(results, dict) and all(isinstance(v, tuple) and len(v) == 3 for v in results.values()):
        # Single stage result: {filename: (errors, warnings, count)}
        for filename, (errors, warnings, count) in results.items():
            total_errors += len(errors)
            total_warnings += len(warnings)
            total_records += count
            status = "PASS" if not errors else "FAIL"
            print(f"\n  [{status}] {filename}  ({count} records)")
            for e in errors:
                print(f"    ERROR: {e}")
            if verbose:
                for w in warnings:
                    print(f"    WARN:  {w}")

    elif isinstance(results, dict):
        # Multi-stage result: {stage: {filename: (errors, warnings, count)}}
        for stage_name, stage_results in results.items():
            stage_errors = sum(len(r[0]) for r in stage_results.values())
            stage_warnings = sum(len(r[1]) for r in stage_results.values())
            stage_records = sum(r[2] for r in stage_results.values())
            total_errors += stage_errors
            total_warnings += stage_warnings
            total_records += stage_records

            status = "PASS" if stage_errors == 0 else "FAIL"
            print(f"\n{'='*60}")
            print(f"[{status}] Stage: {stage_name}  ({stage_records} records)")
            print(f"{'='*60}")

            for filename, (errors, warnings, count) in stage_results.items():
                fstatus = "PASS" if not errors else "FAIL"
                print(f"  [{fstatus}] {filename}  ({count} records)")
                for e in errors:
                    print(f"    ERROR: {e}")
                if verbose:
                    for w in warnings:
                        print(f"    WARN:  {w}")

    else:
        # Direct file result tuple
        errors, warnings, count = results
        total_errors = len(errors)
        total_warnings = len(warnings)
        total_records = count
        for e in errors:
            print(f"  ERROR: {e}")
        if verbose:
            for w in warnings:
                print(f"  WARN:  {w}")

    print(f"\n{'='*60}")
    print(f"Total: {total_errors} error(s), {total_warnings} warning(s), {total_records} record(s)")
    status = "PASS" if total_errors == 0 else "FAIL"
    print(f"Result: {status}")
    return total_errors == 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if len(sys.argv) == 2 and sys.argv[1] == "--all":
        # Validate all stages in current directory
        run_dir = os.getcwd()
        results = validate_all_stages(run_dir)
        ok = print_results(results)
        sys.exit(0 if ok else 1)

    if len(sys.argv) == 3 and sys.argv[1] == "--all":
        # Validate all stages in specified directory
        run_dir = sys.argv[2]
        results = validate_all_stages(run_dir)
        ok = print_results(results)
        sys.exit(0 if ok else 1)

    if len(sys.argv) == 3:
        arg1, arg2 = sys.argv[1], sys.argv[2]

        # Check if arg1 looks like a run directory (contains stage dirs)
        if os.path.isdir(arg1) and any(
            d.startswith("0") and d[1].isdigit() for d in os.listdir(arg1)
        ):
            # arg1 = run_dir, arg2 = stage_name
            run_dir, stage = arg1, arg2
            if stage not in get_all_stages():
                print(f"Unknown stage: {stage}")
                print(f"Available: {get_all_stages()}")
                sys.exit(1)
            results = validate_stage(run_dir, stage)
            ok = print_results(results)
            sys.exit(0 if ok else 1)
        else:
            # arg1 = filepath, arg2 = schema_name
            filepath, schema = arg1, arg2
            errors, warnings, count = validate_file(filepath, schema)
            ok = print_results((errors, warnings, count))
            sys.exit(0 if ok else 1)

    print(__doc__)
    sys.exit(1)


if __name__ == "__main__":
    main()
