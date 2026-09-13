import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from task_router import (  # noqa: E402
    AUTHORITY_EFFECT,
    CommandResult,
    RouterRegistry,
    RouterValidationError,
    RoutingCandidate,
    RoutingReceipt,
    RoutingRequest,
    RuVectorRouterAdapter,
)


def request():
    return RoutingRequest(
        task_id="task-1",
        query_embedding=(1.0, 0.0, 0.0),
        candidates=(
            RoutingCandidate(
                route_id="code",
                handler="openai_codex",
                embedding=(1.0, 0.0, 0.0),
                metadata={"kind": "agent"},
            ),
            RoutingCandidate(
                route_id="research",
                handler="research_factory",
                embedding=(0.0, 1.0, 0.0),
                metadata={"kind": "agent"},
            ),
        ),
        k=1,
        threshold=0.7,
    )


class RuVectorAdapterTests(unittest.TestCase):
    def adapter_with_output(self, payload, returncode=0, stderr=""):
        calls = []

        def runner(argv, **kwargs):
            calls.append((argv, kwargs))
            return CommandResult(
                returncode=returncode,
                stdout=json.dumps(payload) if not isinstance(payload, str) else payload,
                stderr=stderr,
            )

        return RuVectorRouterAdapter(
            connector_path="/tmp/router.cjs",
            runner=runner,
        ), calls

    def test_precomputed_embedding_payload_and_receipt(self):
        adapter, calls = self.adapter_with_output({
            "router_id": "ruvector",
            "router_version": "0.1.30",
            "authority_effect": "none",
            "results": [{
                "route_id": "code",
                "handler": "openai_codex",
                "score": 0.99,
                "metadata": {"kind": "agent"},
            }],
        })
        receipt = adapter.route(request())
        self.assertIsInstance(receipt, RoutingReceipt)
        self.assertEqual(receipt.authority_effect, AUTHORITY_EFFECT)
        self.assertEqual(receipt.suggestions[0].handler, "openai_codex")
        self.assertTrue(receipt.request_digest.startswith("sha256:"))

        argv, kwargs = calls[0]
        self.assertEqual(argv[0], "node")
        sent = json.loads(kwargs["input_text"])
        self.assertEqual(sent["query_embedding"], [1.0, 0.0, 0.0])
        self.assertNotIn("query", sent)
        self.assertNotIn("prompt", sent)
        self.assertEqual(sent["candidates"][0]["embedding"], [1.0, 0.0, 0.0])

    def test_authority_bearing_output_fails_closed(self):
        adapter, _ = self.adapter_with_output({
            "router_id": "ruvector",
            "router_version": "0.1.30",
            "authority_effect": "allow",
            "results": [],
        })
        with self.assertRaises(RouterValidationError):
            adapter.route(request())

    def test_unknown_route_fails_closed(self):
        adapter, _ = self.adapter_with_output({
            "router_id": "ruvector",
            "router_version": "0.1.30",
            "authority_effect": "none",
            "results": [{
                "route_id": "unknown",
                "handler": "shell",
                "score": 0.9,
                "metadata": {},
            }],
        })
        with self.assertRaises(RouterValidationError):
            adapter.route(request())

    def test_changed_handler_fails_closed(self):
        adapter, _ = self.adapter_with_output({
            "router_id": "ruvector",
            "router_version": "0.1.30",
            "authority_effect": "none",
            "results": [{
                "route_id": "code",
                "handler": "shell",
                "score": 0.9,
                "metadata": {},
            }],
        })
        with self.assertRaises(RouterValidationError):
            adapter.route(request())

    def test_changed_metadata_fails_closed(self):
        adapter, _ = self.adapter_with_output({
            "router_id": "ruvector",
            "router_version": "0.1.30",
            "authority_effect": "none",
            "results": [{
                "route_id": "code",
                "handler": "openai_codex",
                "score": 0.9,
                "metadata": {"kind": "tool"},
            }],
        })
        with self.assertRaises(RouterValidationError):
            adapter.route(request())

    def test_wrong_router_version_fails_closed(self):
        adapter, _ = self.adapter_with_output({
            "router_id": "ruvector",
            "router_version": "0.1.31",
            "authority_effect": "none",
            "results": [],
        })
        with self.assertRaises(RouterValidationError):
            adapter.route(request())

    def test_extra_execution_field_fails_closed(self):
        adapter, _ = self.adapter_with_output({
            "router_id": "ruvector",
            "router_version": "0.1.30",
            "authority_effect": "none",
            "execute": True,
            "results": [],
        })
        with self.assertRaises(RouterValidationError):
            adapter.route(request())

    def test_invalid_json_fails_closed(self):
        adapter, _ = self.adapter_with_output("not-json")
        with self.assertRaises(RouterValidationError):
            adapter.route(request())

    def test_dimension_mismatch_fails_before_connector(self):
        bad = RoutingRequest(
            task_id="task-1",
            query_embedding=(1.0, 0.0),
            candidates=(
                RoutingCandidate("code", "openai_codex", (1.0, 0.0, 0.0)),
            ),
        )
        called = False

        def runner(*_args, **_kwargs):
            nonlocal called
            called = True
            return CommandResult(0, "{}")

        adapter = RuVectorRouterAdapter(
            connector_path="/tmp/router.cjs", runner=runner
        )
        with self.assertRaises(RouterValidationError):
            adapter.route(bad)
        self.assertFalse(called)

    def test_registry_is_replaceable(self):
        class FakeRouter:
            router_id = "fake"

            def route(self, req):
                return RoutingReceipt(
                    task_id=req.task_id,
                    request_digest="sha256:test",
                    router_id="fake",
                    router_version="1",
                    suggestions=(),
                )

        registry = RouterRegistry()
        registry.register(FakeRouter())
        receipt = registry.route("fake", request())
        self.assertEqual(receipt.router_id, "fake")
        self.assertEqual(receipt.authority_effect, "none")

    def test_connector_dependency_is_exactly_pinned(self):
        package = json.loads(
            (ROOT / "connectors" / "ruvector" / "package.json").read_text()
        )
        self.assertEqual(package["dependencies"]["@ruvector/router"], "0.1.30")

    def test_connector_uses_embedding_surface_only(self):
        source = (ROOT / "connectors" / "ruvector" / "router.cjs").read_text()
        self.assertIn("routeWithEmbedding", source)
        self.assertNotIn(".setEmbedder(", source)
        self.assertNotIn("router.route(", source)
        self.assertIn('authority_effect: AUTHORITY_EFFECT', source)


if __name__ == "__main__":
    unittest.main()
