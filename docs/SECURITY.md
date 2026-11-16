# Threat model

Threats: supply-chain compromise, privileged CI job, state exposure, accidental public endpoints, lateral workload movement, log data leaks and incomplete teardown.

Mitigations: minimum GitHub permissions, reviewable changes, state protection, scoped OIDC, no public admin access, cloud policy guardrails and negative tests.

Do not configure cloud admin roles or enable paid production resources automatically.
