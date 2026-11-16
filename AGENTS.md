# GLM / ZCode engineering handoff: Terraform CI/CD Pipeline

1. Read README.md and all docs before modifying files.
2. Keep this GitHub repository **PRIVATE**, preserve unrelated work and do not leak secrets, tenant details or Terraform state.
3. Use GLM subagents for independent tasks when available, but integrate code centrally and run actual tests.
4. Implement offline-testable real work: Terraform modules, architecture diagrams, app/code examples and negative security tests. Confirm Microsoft/Azure SKU and current APIs before making choices.
5. **No terraform apply/destroy, paid Azure provisioning, automatic deployment, IAM mutations or paid tests without separate explicit cost and action approval.**
6. OIDC and least privilege; no persistent cloud keys. Verify GitHub branch protection and environment constraints before assuming they exist.
7. Log real commands and outcomes in docs/VALIDATION.md; mark Azure untested until truly validated.
8. Continue docs/GLM_TASKS.md from first unchecked milestone; commit reviewed changes and report next steps.
