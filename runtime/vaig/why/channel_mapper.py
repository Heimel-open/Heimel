"""
Channel Mapper — Maps distrust levels to applicable explanation channels.

Determines which CAN/SHOULD/WHY channels apply to a given distrust level.
This is pure logic, no external dependencies.
"""

from why.explanation_engine import ExplanationChannel
from typing import Set


class ChannelMapper:
    """
    Map L0-L4 distrust levels to explanation channels.

    Rules:
      - L0-L1 (CLEAR, WATCH): CAN only
      - L2-L3 (FRICTION, COUNCIL): CAN + SHOULD
      - L4 (LOCK): CAN + SHOULD + WHY
      - UNKNOWN: CAN (conservative fallback)
    """

    def channels_for(self, level: int) -> Set[ExplanationChannel]:
        """
        Return which explanation channels apply to a given distrust level.

        Args:
            level: Distrust level (0-4) or -1 for UNKNOWN

        Returns:
            Set of applicable ExplanationChannel values
        """
        if level < 0:
            # UNKNOWN: conservative fallback — only CAN
            return {ExplanationChannel.can}

        if level <= 1:
            # CLEAR (L0), WATCH (L1): CAN only
            return {ExplanationChannel.can}

        if level <= 3:
            # FRICTION (L2), COUNCIL (L3): CAN + SHOULD
            return {ExplanationChannel.can, ExplanationChannel.should}

        if level >= 4:
            # LOCK (L4): all three channels
            return {
                ExplanationChannel.can,
                ExplanationChannel.should,
                ExplanationChannel.why,
            }

        # Fallback (should not reach here)
        return {ExplanationChannel.can}

    def applies(self, level: int, channel: ExplanationChannel) -> bool:
        """Check if a specific channel applies to a given level."""
        return channel in self.channels_for(level)
