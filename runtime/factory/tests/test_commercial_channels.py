import unittest

from lib.commercial_channels import (
    ChannelDirection,
    CommercialChannel,
    CommercialChannelEvent,
)


class CommercialChannelTests(unittest.TestCase):
    def test_inbound_channel_event_is_observation_not_authority(self):
        event = CommercialChannelEvent(
            event_ref="email:reply:1",
            direction=ChannelDirection.INBOUND,
            channel=CommercialChannel.EMAIL,
            counterparty_ref="customer:acme",
            provider_ref="mail-provider",
            payload_digest="a" * 64,
        )

        self.assertTrue(event.is_observation_only)
        self.assertFalse(event.grants_authority)

    def test_outbound_event_still_does_not_grant_authority(self):
        event = CommercialChannelEvent(
            event_ref="sms:send:1",
            direction=ChannelDirection.OUTBOUND,
            channel=CommercialChannel.SMS,
            counterparty_ref="prospect:1",
            provider_ref="sms-provider",
            payload_digest="b" * 64,
            endpoint_ref="provider:endpoint",
        )

        self.assertFalse(event.is_observation_only)
        self.assertFalse(event.grants_authority)


if __name__ == "__main__":
    unittest.main()
