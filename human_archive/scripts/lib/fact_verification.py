# -*- coding: utf-8 -*-
"""Fact verification and sentence segment evidence binding logic."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def verify_script(
    script_data: dict[str, Any],
    claim_inventory: dict[str, Any],
    source_snapshots: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if source_snapshots is None:
        source_snapshots = {}

    sentences = script_data.get("sentences", [])
    claims_by_id = {c["claim_id"]: c for c in claim_inventory.get("claims", [])}

    spans_by_id = {}
    for s in source_snapshots.get("sources", []):
        for sp in s.get("evidence_spans", []):
            if "span_id" in sp:
                spans_by_id[sp["span_id"]] = sp

    segment_evals = []
    sentence_evals = []
    unsupported_count = 0
    forbidden_count = 0
    review_req_count = 0

    if not sentences:
        return {
            "schema_version": 2,
            "verified_at_utc": datetime.now(timezone.utc).isoformat(),
            "overall_status": "FAIL",
            "total_sentences": 0,
            "total_segments": 0,
            "fail_count": 1,
            "unsupported_count": 1,
            "forbidden_wording_count": 0,
            "unresolved_conflict_count": 0,
            "review_required_count": 0,
            "segment_evaluations": [],
            "sentence_evaluations": [],
            "warnings": ["Empty sentences"],
        }

    for s in sentences:
        sid = s.get("sentence_id", "")
        segments = s.get("segments", [])
        if not segments:
            # Fallback for v1 sentence format
            cid_list = s.get("claim_ids") or []
            st_type = s.get("statement_type", "verified_fact")
            kind = "insight" if st_type == "editorial" else "fact"
            cid = cid_list[0] if cid_list else None
            segments = [{"kind": kind, "text": s.get("display_text", ""), "claim_id": cid}]

        sentence_status = "PASS"

        for idx, seg in enumerate(segments):
            kind = seg.get("kind", "fact")
            txt = seg.get("text", "")
            cid = seg.get("claim_id")
            span_ids = seg.get("evidence_span_ids", [])
            issues = []
            status = "PASS"

            if kind in ["fact", "direct_quote"]:
                if not cid:
                    issues.append("Missing claim_id for factual segment")
                    status = "FAIL"
                    unsupported_count += 1
                elif cid not in claims_by_id:
                    issues.append(f"Claim ID '{cid}' not found in inventory")
                    status = "FAIL"
                    unsupported_count += 1
                else:
                    claim = claims_by_id[cid]
                    # Check forbidden wording
                    for fb in claim.get("forbidden_wording", []):
                        if fb in txt:
                            issues.append(f"Contains forbidden wording '{fb}'")
                            status = "FAIL"
                            forbidden_count += 1

                    # Check evidence span references if spans exist in snapshot
                    if spans_by_id and span_ids:
                        for sp_id in span_ids:
                            if sp_id not in spans_by_id:
                                issues.append(f"Referenced evidence span '{sp_id}' not found in source snapshots")
                                status = "FAIL"
                                unsupported_count += 1
                            elif claim.get("evidence_refs") and sp_id not in claim["evidence_refs"]:
                                issues.append(f"Evidence span '{sp_id}' is not associated with Claim '{cid}'")
                                if status != "FAIL":
                                    status = "REVIEW_REQUIRED"

                    # Direct quote check
                    if kind == "direct_quote":
                        if not span_ids:
                            issues.append("Direct quote segment requires evidence_span_ids")
                            status = "FAIL"
                            unsupported_count += 1
                        elif spans_by_id:
                            matched_any = False
                            for sp_id in span_ids:
                                sp_obj = spans_by_id.get(sp_id, {})
                                excerpt = sp_obj.get("excerpt", "")
                                transl = sp_obj.get("translation", "")
                                if (excerpt and (excerpt in txt or txt in excerpt)) or (transl and (transl in txt or txt in transl)):
                                    matched_any = True
                                    break
                            if not matched_any:
                                issues.append("Direct quote text does not match referenced evidence span excerpt or translation")
                                if status != "FAIL":
                                    status = "REVIEW_REQUIRED"

                    # Check approved paraphrases if present
                    approved_para = claim.get("approved_paraphrases", [])
                    if approved_para and not any(p in txt or txt in p for p in approved_para):
                        issues.append("Segment phrasing differs from approved paraphrase")
                        if status != "FAIL":
                            status = "REVIEW_REQUIRED"

            elif kind in ["analogy", "insight", "transition"]:
                if status != "FAIL":
                    status = "PASS"

            if status == "FAIL":
                sentence_status = "FAIL"
            elif status == "REVIEW_REQUIRED" and sentence_status != "FAIL":
                sentence_status = "REVIEW_REQUIRED"
                review_req_count += 1

            segment_evals.append({
                "sentence_id": sid,
                "segment_index": idx,
                "kind": kind,
                "claim_id": cid,
                "evidence_span_ids": span_ids,
                "status": status,
                "issues": issues,
            })

        sentence_evals.append({
            "sentence_id": sid,
            "status": sentence_status if sentence_status != "REVIEW_REQUIRED" else "QUALIFIED",
        })

    fail_count = unsupported_count + forbidden_count
    overall_status = "FAIL" if fail_count > 0 else ("REVIEW_REQUIRED" if review_req_count > 0 else "PASS")

    return {
        "schema_version": 2,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall_status,
        "total_sentences": len(sentences),
        "total_segments": len(segment_evals),
        "fail_count": fail_count,
        "unsupported_count": unsupported_count,
        "forbidden_wording_count": forbidden_count,
        "unresolved_conflict_count": 0,
        "review_required_count": review_req_count,
        "segment_evaluations": segment_evals,
        "sentence_evaluations": sentence_evals,
        "warnings": [iss for se in segment_evals for iss in se["issues"]],
    }
