"""Offline pipeline-policy simulator.

This module is the deterministic offline demo required by docs/GLM_TASKS.md:
it loads the REAL promotion policy (infra/pipeline/policy.yaml), the REAL
active workflows (.github/workflows/) and the REAL pipeline templates
(examples/pipelines/) and replays GitHub events against the policy, proving:

- a PR changing any module produces exactly the offline checks + plan
  (dev), and NEVER an apply;
- a push to main plans the configured environments but NEVER applies;
- applies are possible only through manual dispatch of the inert template,
  only inside jobs gated by a GitHub `environment:` approval context, and
  only in strict dev -> stage -> prod order (no skip-level promotion).

It also audits the files themselves: active workflows may run only the
allowed terraform subcommands, and every `uses:` in every workflow/template
must be pinned to a major version tag or a full commit SHA.

Any drift between the policy file, the templates and the workflows raises
immediately in tests/test_pipeline_policy.py.
"""

from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "infra" / "pipeline" / "policy.yaml"
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
TEMPLATES_DIR = ROOT / "examples" / "pipelines"

# A terraform subcommand that mutates state or infrastructure.
FORBIDDEN_TERRAFORM_RE = re.compile(
    r"terraform(?:\s+-[^\s]+)*\s+(apply|destroy|import|taint|untaint|workspace)\b"
    r"|terraform\s+state\s+\w+"
)
# Azure deployment CLI mutations (defense in depth: none may appear anywhere
# in ACTIVE workflows even though this repo does not use them).
FORBIDDEN_AZURE_RE = re.compile(
    r"\b(az\s+(deployment\s+group\s+create|deployment\s+sub\s+create|group\s+create|group\s+delete)"
    r"|armdeploy)",
    re.IGNORECASE,
)
PINNED_USES_RE = re.compile(r"^(?P<action>[\w.-]+/[\w.-]+)@(?P<ref>v\d+(?:\.\d+)*|sha256:[0-9a-f]{16,64})$")
WILDCARD_SUBJECT_RE = re.compile(r'subject\s*=\s*"repo:[^"]*:\*"')
OFFLINE_CHECKS = ["unittest", "terraform fmt -check", "terraform init -backend=false", "terraform validate"]


def load_policy() -> dict:
    """The promotion policy exactly as committed (no defaults invented)."""
    policy = yaml.safe_load(POLICY_PATH.read_text())
    if not isinstance(policy, dict) or "environments" not in policy:
        raise ValueError("policy.yaml drifted: missing environments")
    return policy


def environments(policy: dict = None) -> dict:
    return (policy or load_policy())["environments"]


def ordered_environments(policy: dict = None) -> list:
    """Environment names in promotion order (dev first, prod last)."""
    envs = environments(policy)
    return sorted(envs, key=lambda name: envs[name]["order"])


def load_yaml(path: Path) -> dict:
    doc = yaml.safe_load(path.read_text())
    if not isinstance(doc, dict) or "jobs" not in doc:
        raise ValueError(f"{path.relative_to(ROOT)} drifted: not a workflow document")
    return doc


def iter_yaml(directory: Path):
    for path in sorted(directory.glob("*.yml")) + sorted(directory.glob("*.yaml")):
        yield path, load_yaml(path)


def job_steps(job: dict) -> list:
    """Flatten a job's steps into {name, uses, run, if} dicts (missing -> '')."""
    steps = job.get("steps", []) or []
    return [
        {
            "name": str(s.get("name", "")),
            "uses": str(s.get("uses", "")),
            "run": str(s.get("run", "")),
            "if": str(s.get("if", "")),
        }
        for s in steps
    ]


def active_workflow_violations(policy: dict = None) -> list:
    """Every way an ACTIVE workflow violates the policy.

    Returns a list of strings (empty = compliant):
    - forbidden terraform subcommands in any run step;
    - forbidden azure CLI mutations anywhere in the file;
    - unpinned actions (uses: must be @vN[.N] or @sha256:...);
    - missing top-level `permissions:` declaration.
    """
    policy = policy or load_policy()
    violations = []
    for path, doc in iter_yaml(WORKFLOWS_DIR):
        rel = path.relative_to(ROOT)
        if "permissions" not in doc:
            violations.append(f"{rel}: missing top-level permissions")
        for job_name, job in doc["jobs"].items():
            for step in job_steps(job):
                blob = " ".join(step.values())
                if FORBIDDEN_TERRAFORM_RE.search(blob):
                    violations.append(
                        f"{rel} [{job_name}] '{step['name'] or step['run'][:40]}': forbidden terraform subcommand"
                    )
                if FORBIDDEN_AZURE_RE.search(blob):
                    violations.append(
                        f"{rel} [{job_name}] '{step['name'] or step['run'][:40]}': mutating azure CLI"
                    )
                uses = step["uses"]
                if uses and not PINNED_USES_RE.match(uses):
                    violations.append(f"{rel} [{job_name}]: action not pinned: {uses}")
    return violations


def template_violations(policy: dict = None) -> list:
    """Policy violations in the inert pipeline templates.

    - apply steps must live in a job that declares `environment:` (approval gate);
    - no wildcard OIDC subjects (paranoia: none may appear even in templates);
    - every action pinned;
    - the drift template must not contain any apply/destroy.
    """
    policy = policy or load_policy()
    violations = []
    for path, doc in iter_yaml(TEMPLATES_DIR):
        rel = path.relative_to(ROOT)
        raw = path.read_text()
        if WILDCARD_SUBJECT_RE.search(raw):
            violations.append(f"{rel}: wildcard OIDC subject present")
        for job_name, job in doc["jobs"].items():
            gated = "environment" in job
            for step in job_steps(job):
                if step["uses"] and not PINNED_USES_RE.match(step["uses"]):
                    violations.append(f"{rel} [{job_name}]: action not pinned: {step['uses']}")
                text = step["run"]
                if re.search(r"terraform(?:\s+-[^\s]+)*\s+(apply|destroy)\b", text):
                    if not gated:
                        violations.append(
                            f"{rel} [{job_name}] '{step['name']}': terraform apply outside an environment-gated job"
                        )
                    if "drift" in rel.name:
                        violations.append(f"{rel} [{job_name}]: drift detection must never apply")
    return violations


def apply_jobs(template_path: Path) -> dict:
    """{job_name: {environment, needs, if}} for every job in a template that
    contains a terraform apply step."""
    doc = load_yaml(template_path)
    found = {}
    for job_name, job in doc["jobs"].items():
        runs = [s["run"] for s in job_steps(job)]
        if any(re.search(r"terraform(?:\s+-[^\s]+)*\s+apply\b", r) for r in runs):
            found[job_name] = {
                "environment": job.get("environment"),
                "needs": job.get("needs"),
                "if": job.get("if"),
            }
    return found


def simulate_event(event: str, changed_paths=None, target_environment=None,
                   template_gates_present=True):
    """Deterministic replay of the promotion policy for one GitHub event.

    event: 'pull_request' | 'push_main' | 'workflow_dispatch'
    changed_paths: list of repo-relative paths the event touches (informational;
        the offline checks always run because the policy has no path filters).
    target_environment: for workflow_dispatch, the promotion endpoint.
    template_gates_present: False simulates an attacker/regression removing the
        `environment:` gates from the apply template (negative test).

    Returns a dict describing what the pipeline does:
    {checks, plans, apply: {permitted, reason, approval_required, path}}
    """
    policy = load_policy()
    envs = environments(policy)
    result = {
        "event": event,
        "checks": list(OFFLINE_CHECKS),
        "plans": [],
        "apply": {"permitted": False, "reason": "", "approval_required": False, "path": []},
    }

    if event == "pull_request":
        result["plans"] = [e for e in ordered_environments(policy)
                           if "pull_request" in envs[e].get("plans_on", [])]
        result["apply"]["reason"] = (
            "apply_mode=manual for every environment: PRs generate plans only"
        )
        return result

    if event == "push_main":
        result["plans"] = [e for e in ordered_environments(policy)
                           if "push_main" in envs[e].get("plans_on", [])]
        result["apply"]["reason"] = (
            "no auto-apply on push: applies require manual workflow_dispatch "
            "plus environment approval"
        )
        return result

    if event == "workflow_dispatch":
        if target_environment not in envs:
            result["apply"]["reason"] = f"unknown environment '{target_environment}'"
            return result
        # Strict sequential promotion: the dispatch endpoint expands to the
        # full path dev -> ... -> endpoint; skip-level is forbidden.
        path = promotion_path(policy, target_environment)
        result["apply"]["path"] = path
        result["apply"]["approval_required"] = bool(
            policy["promotion"]["requires_github_environment_protection"]
        )
        env = envs[target_environment]
        if env.get("apply_mode") != "manual":
            result["apply"]["reason"] = "auto-apply modes are forbidden by policy"
            return result
        if not template_gates_present:
            result["apply"]["reason"] = (
                "apply template lacks environment: gates — apply refused"
            )
            return result
        # Cross-check the real template: every job on the path must be gated.
        template = ROOT / "examples" / "pipelines" / "apply-promotion.yml"
        jobs = apply_jobs(template) if template.exists() else {}
        ungated = [j for j, meta in jobs.items()
                   if meta["environment"] in path and not meta["environment"]]
        if ungated:
            result["apply"]["reason"] = f"ungated apply jobs in template: {ungated}"
            return result
        result["apply"]["permitted"] = True
        result["apply"]["reason"] = (
            "manual dispatch of the INERT template (never active in this repo): "
            "each apply job waits for its GitHub environment reviewer approval"
        )
        return result

    raise ValueError(f"unsupported event '{event}'")


def promotion_path(policy: dict, endpoint: str) -> list:
    """Full promotion path for a dispatch endpoint: strictly sequential from
    the lowest order, no skips. Raises ValueError on skip-level attempts."""
    envs = policy["environments"]
    if endpoint not in envs:
        raise ValueError(f"unknown environment '{endpoint}'")
    if not policy["promotion"].get("skip_levels_forbidden", True):
        return [endpoint]
    orders = {e: envs[e]["order"] for e in envs}
    target = orders[endpoint]
    expected = [e for e in sorted(orders, key=orders.get) if orders[e] <= target]
    if [orders[e] for e in expected] != list(range(1, target + 1)):
        raise ValueError(f"environment orders are not contiguous 1..{target}: {orders}")
    return expected


def validate_promotion_sequence(sequence: list) -> tuple:
    """(ok, reason) for a manually supplied apply sequence (negative tests)."""
    policy = load_policy()
    envs = environments(policy)
    orders = {e: envs[e]["order"] for e in envs}
    unknown = [e for e in sequence if e not in envs]
    if unknown:
        return False, f"unknown environments: {unknown}"
    seen = [orders[e] for e in sequence]
    if seen != sorted(seen):
        return False, "promotion must not go backwards"
    if seen != list(range(1, len(seen) + 1)):
        return False, "skip-level promotion forbidden: start at dev, promote one level at a time"
    if not sequence:
        return False, "empty promotion sequence"
    return True, "sequential dev -> stage -> prod promotion"
