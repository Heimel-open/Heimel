from __future__ import annotations

from unittest import mock

import pytest

from valo_operator.adapters.commercial_channels import (
    commercial_channel_configured,
    notification_external_config,
    payment_external_config,
)


def test_email_sms_voice_are_config_only_notification_edges() -> None:
    for channel in ("email", "sms", "voice"):
        prefix = channel.upper()
        with mock.patch.dict(
            "os.environ",
            {
                f"{prefix}_BASE_URL": f"https://{channel}.example",
                f"{prefix}_AUTH": "Bearer secret",
                f"{prefix}_FROM": "valo",
            },
            clear=True,
        ):
            config = notification_external_config(channel)
            body = config.body_builder(
                {
                    "parameters": {
                        "notification": {
                            "recipient": "customer@example.test",
                            "message": "POC ready",
                            "subject": "Your POC",
                        }
                    }
                }
            )
            assert config.name == f"commercial-{channel}"
            assert config.base_url == f"https://{channel}.example"
            assert config.effect_key == "delivered"
            assert body["to"] == "customer@example.test"
            assert body["message"] == "POC ready"
            assert body["channel"] == channel
            assert commercial_channel_configured(channel) is True


def test_email_subject_is_data_mapping_only() -> None:
    with mock.patch.dict(
        "os.environ",
        {
            "EMAIL_BASE_URL": "https://email.example",
            "EMAIL_AUTH": "Bearer secret",
            "EMAIL_FROM": "sales@example.test",
        },
        clear=True,
    ):
        config = notification_external_config("email")
        body = config.body_builder(
            {
                "parameters": {
                    "notification": {
                        "recipient": "cto@example.test",
                        "subject": "Custom POC",
                        "message": "Built for your use case",
                    }
                }
            }
        )
        assert body == {
            "channel": "email",
            "from": "sales@example.test",
            "to": "cto@example.test",
            "message": "Built for your use case",
            "subject": "Custom POC",
        }


def test_payment_config_is_provider_neutral_and_observable() -> None:
    with mock.patch.dict(
        "os.environ",
        {
            "PAY_BASE_URL": "https://payments.example",
            "PAY_AUTH": "Bearer secret",
            "PAY_SUCCESS_STATE": "settled",
        },
        clear=True,
    ):
        config = payment_external_config()
        body = config.body_builder(
            {
                "parameters": {
                    "payment": {
                        "customer_ref": "customer:acme",
                        "amount": "7500.00",
                        "currency": "EUR",
                        "payment_method_ref": "customer-selected-method",
                        "description": "Approved POC",
                    }
                }
            }
        )
        assert config.name == "commercial-payment"
        assert config.effect_key == "payment_observed"
        assert config.success_state == "settled"
        assert body["amount"] == "7500.00"
        assert body["payment_method_ref"] == "customer-selected-method"
        assert commercial_channel_configured("payment") is True


def test_unknown_notification_channel_fails_closed() -> None:
    with pytest.raises(ValueError, match="unsupported notification channel"):
        notification_external_config("carrier-pigeon")


def test_configuration_presence_never_requires_or_implies_authority() -> None:
    with mock.patch.dict("os.environ", {}, clear=True):
        assert commercial_channel_configured("email") is False
        assert commercial_channel_configured("payment") is False
