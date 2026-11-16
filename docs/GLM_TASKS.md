# GLM implementation instructions — Terraform CI/CD Pipeline

**Architecture:** GitHub PR validate and plan -> protected OIDC apply to dev -> human-approved production; remote state in Azure Storage with blob lease locking.

**Goal:** Generate safe plans, secure PR checks and reviewable infrastructure changes.

## Offline implementation backlog
- [ ] Audit existing files, Azure documentation and actual available tools.
- [ ] Implement realistic modular IaC for all named services; leave deploy_enabled=false as default.
- [ ] Implement deterministic offline demo covering generate safe plans, secure pr checks and reviewable infrastructure changes.
- [ ] Create behavior, failure and negative-security tests.
- [ ] Add static security scanners, dependency review and minimal CI permissions; pin tested action versions.
- [ ] Refine topology diagram, network/identity trust boundaries and disaster recovery paths.
- [ ] Run unittest, terraform fmt, init -backend=false, validate and document real output.

## Cost gate
- [ ] Estimate fixed and variable regional Azure costs; verify licenses and quotas.
- [ ] Require explicit approval for exact deployment scope, maximum budget and teardown.
- [ ] Only after approval may live testing, performance measurements and cost validation occur.

Don't stop at proposals. Start implementing an offline slice now and submit evidence.
