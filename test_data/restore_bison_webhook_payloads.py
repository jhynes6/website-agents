"""
Restore nested Email Bison webhook payloads from flattened records.

Input files in this repo's `test_data/` are JSON arrays of "flattened" records with keys like:
  - event_type, event_name, workspace_id, workspace_name, instance_url
  - reply_id, reply_uuid, reply_text_body, ...
  - lead_id, lead_email, ...
  - campaign_id, campaign_name
  - campaign_event_id, campaign_event_type, ...
  - scheduled_email_id, ...
  - sender_email_id, ...

This script converts each record to a nested payload matching the canonical webhook structure:

{
  "event": {...},
  "data": {
    "reply": {...},
    "campaign_event": {...},
    "lead": {...},
    "campaign": {...},
    "scheduled_email": {...},
    "sender_email": {...}
  }
}

It writes `*_nested.json` files next to each input file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


TEST_DATA_DIR = Path(__file__).resolve().parent


def _get(rec: Dict[str, Any], key: str) -> Any:
    return rec.get(key, None)


def _obj_from_pairs(rec: Dict[str, Any], pairs: Iterable[Tuple[str, str]]) -> Dict[str, Any]:
    """
    Build an object from (source_key, dest_key) pairs, only including keys
    that exist in the record (even if value is None).
    """
    out: Dict[str, Any] = {}
    for src, dst in pairs:
        if src in rec:
            out[dst] = rec.get(src)
    return out


def restore_record_to_payload(rec: Dict[str, Any]) -> Dict[str, Any]:
    # Event
    event = _obj_from_pairs(
        rec,
        [
            ("event_type", "type"),
            ("event_name", "name"),
            ("instance_url", "instance_url"),
            ("workspace_id", "workspace_id"),
            ("workspace_name", "workspace_name"),
        ],
    )

    # Reply
    reply = _obj_from_pairs(
        rec,
        [
            ("reply_id", "id"),
            ("reply_uuid", "uuid"),
            ("reply_email_subject", "email_subject"),
            ("reply_interested", "interested"),
            ("reply_automated_reply", "automated_reply"),
            ("reply_text_body", "text_body"),
            ("reply_date_received", "date_received"),
            ("reply_type", "type"),
            ("reply_folder", "folder"),
            ("reply_from_name", "from_name"),
            ("reply_from_email_address", "from_email_address"),
            ("reply_primary_to_email_address", "primary_to_email_address"),
            ("reply_raw_message_id", "raw_message_id"),
            ("reply_parent_id", "parent_id"),
            ("reply_to", "to"),
            ("reply_cc", "cc"),
            ("reply_bcc", "bcc"),
            ("reply_created_at", "created_at"),
            ("reply_updated_at", "updated_at"),
            ("reply_attachments", "attachments"),
        ],
    )

    # Campaign event
    campaign_event = _obj_from_pairs(
        rec,
        [
            ("campaign_event_id", "id"),
            ("campaign_event_type", "type"),
            ("campaign_event_created_at_local", "created_at_local"),
            ("campaign_event_local_timezone", "local_timezone"),
            ("campaign_event_created_at", "created_at"),
        ],
    )

    # Lead
    lead = _obj_from_pairs(
        rec,
        [
            ("lead_id", "id"),
            ("lead_email", "email"),
            ("lead_first_name", "first_name"),
            ("lead_last_name", "last_name"),
            ("lead_status", "status"),
            ("lead_title", "title"),
            ("lead_company", "company"),
            ("lead_custom_variables", "custom_variables"),
            ("lead_emails_sent", "emails_sent"),
            ("lead_opens", "opens"),
            ("lead_unique_opens", "unique_opens"),
            ("lead_replies", "replies"),
            ("lead_unique_replies", "unique_replies"),
            ("lead_bounces", "bounces"),
        ],
    )

    # Campaign
    campaign = _obj_from_pairs(
        rec,
        [
            ("campaign_id", "id"),
            ("campaign_name", "name"),
        ],
    )

    # Scheduled email
    scheduled_email = _obj_from_pairs(
        rec,
        [
            ("scheduled_email_id", "id"),
            ("scheduled_email_sequence_step_id", "sequence_step_id"),
            ("scheduled_email_sequence_step_order", "sequence_step_order"),
            ("scheduled_email_status", "status"),
            ("scheduled_email_scheduled_date_est", "scheduled_date_est"),
            ("scheduled_email_scheduled_date_local", "scheduled_date_local"),
            ("scheduled_email_local_timezone", "local_timezone"),
            ("scheduled_email_sent_at", "sent_at"),
            ("scheduled_email_opens", "opens"),
            ("scheduled_email_replies", "replies"),
            ("scheduled_email_unique_opens", "unique_opens"),
            ("scheduled_email_unique_replies", "unique_replies"),
            ("scheduled_email_interested", "interested"),
            ("scheduled_email_raw_message_id", "raw_message_id"),
        ],
    )

    # Sender email
    sender_email = _obj_from_pairs(
        rec,
        [
            ("sender_email_id", "id"),
            ("sender_email_name", "name"),
            ("sender_email_email", "email"),
            ("sender_email_status", "status"),
            ("sender_email_type", "type"),
            ("sender_email_daily_limit", "daily_limit"),
            ("sender_email_emails_sent", "emails_sent"),
            ("sender_email_replied", "replied"),
            ("sender_email_opened", "opened"),
            ("sender_email_unsubscribed", "unsubscribed"),
            ("sender_email_bounced", "bounced"),
            ("sender_email_unique_replies", "unique_replies"),
            ("sender_email_unique_opens", "unique_opens"),
            ("sender_email_total_leads_contacted", "total_leads_contacted"),
            ("sender_email_interested", "interested"),
            ("sender_email_created_at", "created_at"),
            ("sender_email_updated_at", "updated_at"),
        ],
    )

    payload: Dict[str, Any] = {
        "event": event,
        "data": {
            "reply": reply,
            "campaign_event": campaign_event,
            "lead": lead,
            "campaign": campaign,
            "scheduled_email": scheduled_email,
            "sender_email": sender_email,
        },
    }

    return payload


def restore_file(in_path: Path) -> Path:
    arr = json.loads(in_path.read_text())
    if not isinstance(arr, list):
        raise ValueError(f"Expected list root in {in_path}, got {type(arr).__name__}")

    restored = []
    for i, rec in enumerate(arr):
        if not isinstance(rec, dict):
            raise ValueError(f"Expected dict record at index {i} in {in_path}, got {type(rec).__name__}")
        restored.append(restore_record_to_payload(rec))

    out_path = in_path.with_name(in_path.stem + "_nested.json")
    out_path.write_text(json.dumps(restored, indent=2, ensure_ascii=False))
    return out_path


def main() -> None:
    inputs = sorted(TEST_DATA_DIR.glob("bison_webhook_*.json"))
    if not inputs:
        raise SystemExit(f"No inputs found under {TEST_DATA_DIR}")

    # Avoid re-processing already-generated outputs
    inputs = [p for p in inputs if not p.name.endswith("_nested.json")]

    wrote: List[Path] = []
    for p in inputs:
        wrote.append(restore_file(p))

    print("Wrote:")
    for p in wrote:
        print(f"- {p}")


if __name__ == "__main__":
    main()


