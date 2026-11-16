# Architecture

GitHub PR validate and plan -> protected OIDC apply to dev -> human-approved production; remote state in Azure Storage with blob lease locking.

**Acceptance goal:** Generate safe plans, secure PR checks and reviewable infrastructure changes.

Separate internet edge, workload identity, CI credentials, control plane and data plane. Private services require a reachable private runner or network path. Verify DNS, routing, firewall, quotas and regional availability. This is an offline scaffold, NOT deployed production architecture.
