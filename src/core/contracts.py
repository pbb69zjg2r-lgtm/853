"""
Contracts loader for V2 literature evidence extraction.

Loads contracts/*.yaml and provides a unified API for downstream validation.
All functions return plain dict/list types — no custom classes.
"""

import os
import yaml

_CONTRACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "contracts")
_CACHE = {}


def _abs(path):
    return os.path.normpath(os.path.join(_CONTRACTS_DIR, path))


def _load_yaml(relpath):
    if relpath not in _CACHE:
        with open(_abs(relpath), "r", encoding="utf-8") as f:
            _CACHE[relpath] = yaml.safe_load(f)
    return _CACHE[relpath]


def reload_contracts():
    """Force reload all contracts on next access."""
    _CACHE.clear()


# ---------------------------------------------------------------------------
# Dictionaries (enums)
# ---------------------------------------------------------------------------

def get_dictionary(name):
    """Return list of valid values for a dictionary (enum).

    >>> get_dictionary('evidence_type')
    ['disease_association', 'detection_method', 'thermogenesis_modulation', ...]
    """
    d = _load_yaml("dictionaries.yaml")
    if name in d:
        return list(d[name])
    raise KeyError(f"Dictionary '{name}' not found. Available: {list(d.keys())}")


def get_enum_values(name):
    """Alias for get_dictionary."""
    return get_dictionary(name)


def list_dictionaries():
    """Return all dictionary names."""
    d = _load_yaml("dictionaries.yaml")
    return [k for k in d if not k.startswith("schema_")]


# ---------------------------------------------------------------------------
# Field schemas
# ---------------------------------------------------------------------------

def _parse_fields(raw, prefix=""):
    """Recursively flatten field definitions into {name: spec} dict."""
    out = {}
    for key, val in raw.items():
        if key in ("schema_version", "contract_version", "description"):
            continue
        if key == "common":
            continue
        if isinstance(val, dict) and "type" in val:
            out[f"{prefix}{key}"] = val
        elif isinstance(val, dict) and "fields" in val:
            out[f"{prefix}{key}"] = val  # nested object
            nested = _parse_fields(val["fields"], f"{prefix}{key}.")
            out.update(nested)
        elif isinstance(val, dict) and "item_schema" in val:
            out[f"{prefix}{key}"] = val
            nested = _parse_fields(val["item_schema"], f"{prefix}{key}.")
            out.update(nested)
        elif isinstance(val, dict):
            nested = _parse_fields(val, f"{prefix}{key}.")
            out.update(nested)
    return out


def get_field_schema(schema_name):
    """Return all field definitions for a named schema block.

    >>> schema = get_field_schema('evidence_unit')
    >>> schema['evidence_id']
    {'type': 'string', 'required': True}
    """
    raw = _load_yaml("fields.yaml")
    if schema_name not in raw:
        raise KeyError(f"Schema '{schema_name}' not found in fields.yaml. Available: {list(raw.keys())}")
    return _parse_fields(raw[schema_name])


def get_required_fields(schema_name):
    """Return list of required top-level field names for a schema.

    >>> get_required_fields('evidence_unit')
    ['evidence_id', 'paper_id', 'evidence_type', 'claim', ...]
    """
    schema = get_field_schema(schema_name)
    return sorted(k for k, v in schema.items() if v.get("required") and "." not in k)


def is_field_required(schema_name, field_name):
    return field_name in get_required_fields(schema_name)


def get_field_type(schema_name, field_name):
    schema = get_field_schema(schema_name)
    if field_name not in schema:
        raise KeyError(f"Field '{field_name}' not in schema '{schema_name}'")
    return schema[field_name].get("type")


def get_enum_field_values(schema_name, field_name):
    """If a field is an enum with inline 'values', return them. Else return None."""
    schema = get_field_schema(schema_name)
    if field_name not in schema:
        raise KeyError(f"Field '{field_name}' not in schema '{schema_name}'")
    spec = schema[field_name]
    if spec.get("type") == "enum" and "values" in spec:
        return list(spec["values"])
    return None


def get_enum_field_dictionary(schema_name, field_name):
    """If a field references a dictionary, return the dictionary name."""
    schema = get_field_schema(schema_name)
    if field_name not in schema:
        raise KeyError(f"Field '{field_name}' not in schema '{schema_name}'")
    return schema[field_name].get("dictionary")


# ---------------------------------------------------------------------------
# Stage contracts
# ---------------------------------------------------------------------------

def get_stage(stage_name):
    """Return full stage definition dict."""
    sc = _load_yaml("stage_contracts.yaml")
    stages = sc.get("stages", {})
    if stage_name not in stages:
        raise KeyError(f"Stage '{stage_name}' not found. Available: {list(stages.keys())}")
    return stages[stage_name]


def get_stage_inputs(stage_name):
    """Return list of input file patterns for a stage (relative to paper run dir)."""
    return get_stage(stage_name).get("inputs", [])


def get_stage_outputs(stage_name):
    """Return list of output file patterns for a stage (relative to paper run dir)."""
    return get_stage(stage_name).get("outputs", [])


def stage_input_paths(stage_name, run_dir):
    """Return {basename: absolute_path} for all non-glob stage inputs."""
    result = {}
    for p in get_stage_inputs(stage_name):
        if "*" not in p:
            result[os.path.basename(p)] = os.path.join(run_dir, p)
    return result


def stage_output_paths(stage_name, run_dir):
    """Return {basename: absolute_path} for all non-glob stage outputs."""
    result = {}
    for p in get_stage_outputs(stage_name):
        if "*" not in p:
            result[os.path.basename(p)] = os.path.join(run_dir, p)
    return result


def get_all_stages():
    """Return list of all stage names in order."""
    sc = _load_yaml("stage_contracts.yaml")
    return list(sc.get("stages", {}).keys())


def get_producer(stage_name):
    """Return producer module path for a stage."""
    return get_stage(stage_name).get("producer")


def is_trusted_stage(stage_name):
    """Whether a stage produces trusted output."""
    return get_stage(stage_name).get("trusted_output", False)


# ---------------------------------------------------------------------------
# Output contracts
# ---------------------------------------------------------------------------

def _get_output_contracts():
    return _load_yaml("output_contracts.yaml")


def get_trusted_outputs():
    """Return dict of trusted output definitions."""
    return _get_output_contracts().get("trusted_outputs", {})


def get_candidate_outputs():
    """Return dict of candidate output definitions."""
    return _get_output_contracts().get("candidate_outputs", {})


def is_output_trusted(output_name):
    """Check if a named output is in the trusted outputs list."""
    return output_name in get_trusted_outputs()


def get_output_required_fields(output_name):
    """Return required top-level fields for a named output."""
    oc = _get_output_contracts()
    for group in ["trusted_outputs", "candidate_outputs", "internal_outputs", "source_outputs"]:
        items = oc.get(group, {})
        if output_name in items:
            return items[output_name].get("required_fields", items[output_name].get("required_top_level_fields", []))
    return []


def get_output_forbidden_fields(output_name):
    """Return forbidden fields for a named output (empty list if none)."""
    oc = _get_output_contracts()
    for group in ["trusted_outputs", "candidate_outputs"]:
        items = oc.get(group, {})
        if output_name in items:
            return items[output_name].get("forbidden_fields", [])
    return []


def get_output_info(output_name):
    """Return full output definition dict for a named output."""
    oc = _get_output_contracts()
    for group in ["trusted_outputs", "candidate_outputs", "internal_outputs", "source_outputs"]:
        items = oc.get(group, {})
        if output_name in items:
            return items[output_name]
    raise KeyError(f"Output '{output_name}' not found in output_contracts.yaml")


def list_outputs():
    """Return list of all named outputs."""
    oc = _get_output_contracts()
    names = []
    for group in ["trusted_outputs", "candidate_outputs", "internal_outputs", "source_outputs"]:
        names.extend(oc.get(group, {}).keys())
    return names


# ---------------------------------------------------------------------------
# Prompt formatting — inject dictionary values into prompt templates
# ---------------------------------------------------------------------------

def format_prompt(template):
    """Replace {{DICT_NAME}} placeholders with pipe-joined dictionary values.

    >>> format_prompt('types: {{EVIDENCE_TYPE}}')
    'types: disease_association | detection_method | ...'
    """
    import re

    def _replacer(match):
        dict_name = match.group(1).lower()
        try:
            values = get_dictionary(dict_name)
            return " | ".join(values)
        except KeyError:
            return match.group(0)  # leave unknown placeholders as-is

    return re.sub(r"\{\{(\w+)\}\}", _replacer, template)


# ---------------------------------------------------------------------------
# Convenience: load everything at once
# ---------------------------------------------------------------------------

def load_contracts():
    """Load and return all contracts as a dict.

    >>> c = load_contracts()
    >>> c['dictionaries']['evidence_type']
    ['disease_association', ...]
    >>> c['stages']['evidence_units']['outputs']
    ['03_evidence/evidence_units.jsonl']
    """
    return {
        "dictionaries": _load_yaml("dictionaries.yaml"),
        "fields": _load_yaml("fields.yaml"),
        "stages": _load_yaml("stage_contracts.yaml"),
        "outputs": _load_yaml("output_contracts.yaml"),
    }
