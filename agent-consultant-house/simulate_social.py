from __future__ import annotations

import argparse
import hashlib
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path


PLATFORMS = {
    "Agentbook": ["text", "image", "audit"],
    "AgentTok": ["short_video", "simulation"],
    "AgentGram": ["image", "simulation"],
    "AgentTube": ["long_video", "audit", "simulation"],
}


@dataclass
class AgentProfile:
    agent_id: str
    display_name: str
    owner_id: str
    domain: str
    operated_by: str
    human_made: bool
    verification_tier: str
    allowed_content_types: list[str]
    reputation: float
    balance: float = 0.0


@dataclass
class PostIntent:
    post_id: int
    platform: str
    content_type: str
    risk: float
    quality: float
    human_face_detected: bool


@dataclass
class ContentReceipt:
    post_id: int
    agent_id: str
    platform: str
    content_type: str
    decision: str
    human_face_detected: bool
    verified_multiplier: float
    reach: int
    revenue: float
    audit_hash: str


def stable_hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def create_profiles() -> list[AgentProfile]:
    return [
        AgentProfile(
            agent_id="valo-builder-01",
            display_name="VALO Builder",
            owner_id="human:njal",
            domain="code",
            operated_by="agent",
            human_made=True,
            verification_tier="VALO_VERIFIED",
            allowed_content_types=["text", "image", "short_video", "long_video", "simulation", "audit"],
            reputation=0.72,
        ),
        AgentProfile(
            agent_id="audit-oracle-01",
            display_name="Audit Oracle",
            owner_id="human:triin",
            domain="governance",
            operated_by="agent",
            human_made=True,
            verification_tier="VALO_PREMIUM",
            allowed_content_types=["text", "long_video", "simulation", "audit"],
            reputation=0.81,
        ),
        AgentProfile(
            agent_id="sales-synth-01",
            display_name="Sales Synth",
            owner_id="human:investor-a",
            domain="sales",
            operated_by="agent",
            human_made=True,
            verification_tier="UNVERIFIED",
            allowed_content_types=["text", "image", "short_video"],
            reputation=0.46,
        ),
        AgentProfile(
            agent_id="research-loop-01",
            display_name="Research Loop",
            owner_id="human:investor-a",
            domain="research",
            operated_by="agent",
            human_made=True,
            verification_tier="VALO_VERIFIED",
            allowed_content_types=["text", "long_video", "simulation", "audit"],
            reputation=0.68,
        ),
    ]


def generate_intent(post_id: int) -> PostIntent:
    platform = random.choice(list(PLATFORMS))
    content_type = random.choice(PLATFORMS[platform])
    return PostIntent(
        post_id=post_id,
        platform=platform,
        content_type=content_type,
        risk=random.random(),
        quality=random.uniform(0.35, 0.98),
        human_face_detected=random.random() < 0.08,
    )


def verified_multiplier(profile: AgentProfile) -> float:
    if profile.verification_tier == "VALO_PREMIUM":
        return 2.2
    if profile.verification_tier == "VALO_VERIFIED":
        return 1.6
    return 0.65


def valo_social_gate(profile: AgentProfile, intent: PostIntent) -> str:
    if profile.operated_by != "agent":
        return "HALT"
    if intent.human_face_detected:
        return "HALT"
    if intent.content_type not in profile.allowed_content_types:
        return "DENY"
    if profile.verification_tier == "UNVERIFIED" and intent.risk > 0.55:
        return "DENY"
    if intent.risk > 0.82:
        return "STEP_UP"
    if intent.quality < 0.42:
        return "DENY"
    return "PUBLISH"


def settle(profile: AgentProfile, intent: PostIntent, decision: str) -> ContentReceipt:
    multiplier = verified_multiplier(profile)

    if decision in {"DENY", "HALT"}:
        reach = 0
        revenue = 0.0
        if decision == "DENY":
            profile.reputation = round(max(0.0, profile.reputation - 0.015), 3)
    elif decision == "STEP_UP":
        reach = int(500 * intent.quality * multiplier)
        revenue = round(reach * 0.018, 2)
        profile.balance = round(profile.balance + revenue, 2)
        profile.reputation = round(min(1.0, profile.reputation + 0.01), 3)
    else:
        reach = int(1000 * intent.quality * multiplier * (0.7 + profile.reputation))
        revenue = round(reach * 0.022, 2)
        profile.balance = round(profile.balance + revenue, 2)
        profile.reputation = round(min(1.0, profile.reputation + 0.018), 3)

    payload = {
        "post_id": intent.post_id,
        "agent_id": profile.agent_id,
        "platform": intent.platform,
        "decision": decision,
        "reach": reach,
        "revenue": revenue,
    }
    return ContentReceipt(
        post_id=intent.post_id,
        agent_id=profile.agent_id,
        platform=intent.platform,
        content_type=intent.content_type,
        decision=decision,
        human_face_detected=intent.human_face_detected,
        verified_multiplier=multiplier,
        reach=reach,
        revenue=revenue,
        audit_hash=stable_hash(payload),
    )


def baro_social_signal(receipts: list[ContentReceipt]) -> dict:
    counts: dict[str, int] = {}
    platform_reach: dict[str, int] = {}
    face_blocks = 0
    total_revenue = 0.0

    for receipt in receipts:
        counts[receipt.decision] = counts.get(receipt.decision, 0) + 1
        platform_reach[receipt.platform] = platform_reach.get(receipt.platform, 0) + receipt.reach
        if receipt.human_face_detected:
            face_blocks += 1
        total_revenue += receipt.revenue

    total = max(len(receipts), 1)
    halt_rate = counts.get("HALT", 0) / total
    deny_rate = counts.get("DENY", 0) / total

    if halt_rate > 0.08:
        status = "face-risk"
    elif deny_rate > 0.25:
        status = "restricted"
    else:
        status = "operational"

    return {
        "schema_version": "baro.agent_social_signal.v1",
        "status": status,
        "decision_counts": counts,
        "platform_reach": platform_reach,
        "face_blocks": face_blocks,
        "total_revenue": round(total_revenue, 2),
    }


def simulate(rounds: int, seed: int) -> dict:
    random.seed(seed)
    profiles = create_profiles()
    receipts: list[ContentReceipt] = []

    for post_id in range(1, rounds + 1):
        profile = random.choice(profiles)
        intent = generate_intent(post_id)
        decision = valo_social_gate(profile, intent)
        receipts.append(settle(profile, intent, decision))

    return {
        "schema_version": "valo.agent_social_network.simulation.v1",
        "rounds": rounds,
        "seed": seed,
        "profiles": [asdict(profile) for profile in profiles],
        "receipts": [asdict(receipt) for receipt in receipts],
        "baro_signal": baro_social_signal(receipts),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=80)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    result = simulate(rounds=args.rounds, seed=args.seed)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
