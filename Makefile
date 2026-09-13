#!/usr/bin/make -s
# VALO Factory install — copies control plane to local runtime and wires hooks.
VALO_HOME ?= $(HOME)/.valo
BIN := $(VALO_HOME)/bin
LIB := $(VALO_HOME)/lib
CONF := $(VALO_HOME)/config
LINK := $(HOME)/.local/bin

install:
	mkdir -p $(BIN) $(LIB) $(CONF)
	cp bin/* $(BIN)/
	cp lib/*.py $(LIB)/
	cp config/tokenomics-policy.json $(CONF)/tokenomics-policy.json
	cp config/graft_policy.json $(CONF)/graft_policy.json
	chmod 711 $(BIN)/*
	chmod 644 $(LIB)/*.py $(CONF)/tokenomics-policy.json $(CONF)/graft_policy.json
	@for f in $(BIN)/*; do ln -sf $$f $(LINK)/$$(basename $$f); done
	@echo "Installed control plane to $(BIN) with runtime libraries in $(LIB)."
	@echo "Wire primary-repo guard manually:"
	@echo "  cp hooks/00-agent-primary-guard ~/valo-platform/.git/hooks/pre-commit.d/"

verify:
	@for c in valoctl valo-git valo-run valo-claim valo-orchestrator valo-agent-provider valo-qc valo-classify valo-merge valo-watchdog valo-report valo-deliver valo-graft; do \
		command -v $$c >/dev/null || echo "MISSING: $$c"; done
	@test -r $(LIB)/provider_agent_adapters.py || echo "MISSING: $(LIB)/provider_agent_adapters.py"
	@test -r $(CONF)/tokenomics-policy.json || echo "MISSING: $(CONF)/tokenomics-policy.json"
	@test -r $(CONF)/graft_policy.json || echo "MISSING: $(CONF)/graft_policy.json"
	@valo-agent-provider providers >/dev/null
	@valoctl check

# Install systemd units for 24/7 operation. Copies the unit files into
# /etc/systemd/system but does NOT enable/start them — that requires a human
# operator decision (and, for Class C control-plane changes, the human
# authority gate). Enable only after a real end-to-end dispatcher tick is green.
install-systemd:
	install -d /etc/systemd/system
	install -m 0644 deploy/valo-factory-tick.service /etc/systemd/system/
	install -m 0644 deploy/valo-factory-tick.timer /etc/systemd/system/
	install -m 0644 deploy/valo-factory-health.service /etc/systemd/system/
	install -m 0644 deploy/valo-factory-health.timer /etc/systemd/system/
	@echo "Installed systemd units. Enable manually after E2E verification."
	@echo "Configure VALO_FACTORY_WORKER_PROVIDER and VALO_DELIVER_CHANNELS first."
