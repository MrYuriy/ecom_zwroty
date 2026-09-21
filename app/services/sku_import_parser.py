"""Reads the SKU/EAN export: {"supplier_sku_id": EAN, "sku_id": reference, "description": name, "ecommerce": Y|N}.

Accepts a proper JSON document ({"items": [...]} or [...]) as well as the bare fragment the warehouse
export produces (`,"items": [ {...}\n,{...}\n ]}`), in UTF-8 or Windows-1250.
"""

import json
from dataclasses import dataclass, field

_MAX_REFERENCE = 64
_MAX_EAN = 32
_MAX_NAME = 500
_FLAGS = {"Y": True, "N": False}


class SkuFileError(ValueError):
    pass


@dataclass
class ParsedSkuFile:
    # reference -> [product name, is_parametrized or None when the file says nothing]
    skus: dict[str, list] = field(default_factory=dict)
    # code -> reference; a code listed under several references belongs to the last one in the file
    eans: dict[str, str] = field(default_factory=dict)
    rows_read: int = 0
    rows_skipped: int = 0


def decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1250")


def _records_line_by_line(text: str):
    # The export puts one record per line; parsing them one by one keeps 600k rows out of one huge object.
    for line in text.splitlines():
        chunk = line.strip().strip(",")
        if chunk.startswith("{") and chunk.endswith("}"):
            try:
                record = json.loads(chunk)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict) and "sku_id" in record:
                yield record


def _records_whole_document(text: str) -> list:
    body = text.strip()
    for candidate in (body, "{" + body.lstrip(",")):
        try:
            document = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(document, list):
            return document
        if isinstance(document, dict):
            items = document.get("items")
            if isinstance(items, list):
                return items
            lists = [value for value in document.values() if isinstance(value, list)]
            if lists:
                return lists[0]
    raise SkuFileError("Unrecognized file: expected records with supplier_sku_id, sku_id and description")


def parse_sku_file(raw: bytes) -> ParsedSkuFile:
    text = decode(raw)
    records = list(_records_line_by_line(text)) or _records_whole_document(text)
    parsed = ParsedSkuFile()

    for record in records:
        parsed.rows_read += 1
        reference = str(record.get("sku_id") or "").strip()
        code = str(record.get("supplier_sku_id") or "").strip()
        name = str(record.get("description") or "").strip()[:_MAX_NAME]
        if not reference or len(reference) > _MAX_REFERENCE or len(code) > _MAX_EAN:
            parsed.rows_skipped += 1
            continue

        entry = parsed.skus.setdefault(reference, [reference, None])
        if name:
            entry[0] = name
        flag = _FLAGS.get(str(record.get("ecommerce") or "").strip().upper())
        if flag is not None:
            entry[1] = flag
        if code:
            parsed.eans[code] = reference

    if not parsed.skus:
        raise SkuFileError("The file has no SKU records")
    return parsed
