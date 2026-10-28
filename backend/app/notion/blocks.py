import json


def _clean_str(val) -> str:
    """Safely handle strings, lists, and dicts."""
    if val is None:
        return ""
    if isinstance(val, (dict, list)):
        try:
            return json.dumps(val, ensure_ascii=False)
        except Exception:
            return str(val)
    return str(val)


def _format_dict_item(item: dict) -> str:
    """Format structured dictionary items into human-readable text."""
    item_id = item.get("id") or item.get("issue_id")
    desc = item.get("description") or item.get("summary")

    if item_id and desc:
        return f"{item_id} — {desc}"

    if "name" in item and "role" in item:
        needs = item.get("needs")
        needs_str = f" (Needs: {', '.join(needs)})" if isinstance(needs, list) else ""
        return f"{item['name']} ({item['role']}){needs_str}"

    parts = []
    for k, v in item.items():
        if isinstance(v, list):
            v_str = ", ".join(str(x) for x in v)
            parts.append(f"{k.replace('_', ' ').title()}: {v_str}")
        else:
            parts.append(f"{k.replace('_', ' ').title()}: {v}")
    return " | ".join(parts)


def text_block(text) -> dict:
    content = _clean_str(text)
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": content[:2000]
                    }
                }
            ]
        }
    }


def heading_block(text, level: int = 2) -> dict:
    content = _clean_str(text)
    block_type = f"heading_{max(1, min(level, 3))}"

    return {
        "object": "block",
        "type": block_type,
        block_type: {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": content[:2000]
                    }
                }
            ]
        }
    }


def bullet_block(text) -> dict:
    content = _clean_str(text)
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": content[:2000]
                    }
                }
            ]
        }
    }


def divider_block() -> dict:
    return {
        "object": "block",
        "type": "divider",
        "divider": {}
    }


def code_block(data) -> dict:
    if isinstance(data, str):
        content = data
    else:
        try:
            content = json.dumps(data, indent=2, ensure_ascii=False)
        except Exception:
            content = str(data)

    return {
        "object": "block",
        "type": "code",
        "code": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": content[:2000]
                    }
                }
            ],
            "language": "json"
        }
    }


def document_to_blocks(title: str, document) -> list:
    blocks = [
        heading_block(title, level=1),
        divider_block()
    ]

    if isinstance(document, dict):
        for key, value in document.items():
            formatted_key = _clean_str(key).replace("_", " ").title()

            # Skip rendering empty fields or empty lists
            if value is None or value == [] or value == {}:
                continue

            blocks.append(heading_block(formatted_key, level=2))

            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        # Format dict items like OBJ-001, BR-001, Stakeholders cleanly
                        clean_line = _format_dict_item(item)
                        blocks.append(bullet_block(clean_line))
                    else:
                        blocks.append(bullet_block(_clean_str(item)))

            elif isinstance(value, dict):
                blocks.append(code_block(value))

            else:
                blocks.append(text_block(_clean_str(value)))

    else:
        blocks.append(text_block(_clean_str(document)))

    return blocks