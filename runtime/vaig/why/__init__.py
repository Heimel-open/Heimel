"""
WHY Gate — Post-hoc attribution layer for VALO.

This module explains decisions. It does not make them.
It does not influence L1. It does not replace UI_SEMANTICS.

Status: PR #8 skeleton — not wired into production.
"""

from why.explanation_engine import WhyGate, ExplanationChannel
from why.purple_detector import PurpleDetector
from why.channel_mapper import ChannelMapper

__all__ = ["WhyGate", "ExplanationChannel", "PurpleDetector", "ChannelMapper"]
