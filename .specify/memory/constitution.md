<!--
Sync Impact Report
- Version change: unspecified → 0.1.0
- Modified principles:
	- [PRINCIPLE_1_NAME] -> I. Library-First
	- [PRINCIPLE_2_NAME] -> II. CLI Interface (Text I/O First)
	- [PRINCIPLE_3_NAME] -> III. Test-First (NON-NEGOTIABLE)
	- [PRINCIPLE_4_NAME] -> IV. Integration Testing
	- [PRINCIPLE_5_NAME] -> V. Observability, Versioning & Simplicity
- Added sections: Constraints & Security Requirements; Development Workflow & Quality Gates
- Removed sections: none
- Templates checked:
	- .specify/templates/plan-template.md ✅ aligned (Constitution Check present)
	- .specify/templates/spec-template.md ✅ aligned
	- .specify/templates/tasks-template.md ✅ aligned
	- .specify/templates/checklist-template.md ✅ aligned
	- .specify/templates/constitution-template.md ✅ source template
	- .specify/templates/agent-file-template.md ✅ aligned
	- .specify/templates/commands/*.md ⚠ missing (no commands folder present)
- Follow-up TODOs:
	- None deferred. All placeholders replaced.
-->

# gonggang Constitution

## Core Principles

### I. Library-First
Every feature MUST begin as a standalone, well-scoped library or package. Libraries
MUST be self-contained, independently testable, and documented. A library MUST
have a clear public surface and a stated purpose; organizational-only libraries
that do not provide testable, discoverable value are NOT permitted.

### II. CLI Interface (Text I/O First)
All libraries and tools SHOULD expose an explicit text-based interface (CLI or
well-documented stdin/args → stdout protocol). Implementations MUST route
errors to `stderr`. Output formats MUST include a machine-readable option
(JSON) and a concise human-readable option unless explicitly justified.

### III. Test-First (NON-NEGOTIABLE)
Tests MUST be authored before implementation (or alongside design artifacts) and
demonstrate failing expectations prior to code changes (Red → Green → Refactor).
Every change set merged to main MUST include tests that validate the behavior and
regressions the change addresses.

### IV. Integration Testing
Integration tests are REQUIRED for:
- New or changed library contracts
- Inter-service or inter-process communication paths
- Shared schemas and data contracts
Contract changes MUST include migration plans and integration tests that assert
backwards compatibility or document and justify breaking changes.

### V. Observability, Versioning & Simplicity
- Observability: Production-capable services and libraries MUST emit structured
	logs, expose meaningful metrics where applicable, and include context for
	troubleshooting.
- Versioning: The project MUST follow semantic versioning (MAJOR.MINOR.PATCH).
	Breaking changes require a MAJOR version bump and an associated migration
	plan; compatible additions use MINOR; bug fixes use PATCH.
- Simplicity: Prefer the smallest change that satisfies the requirement. Avoid
	premature optimization and needless abstraction; YAGNI applies.

## Constraints & Security Requirements
- Supported runtimes and language versions MUST be documented in feature
	plans and the `agent-file` guidance.
- Secrets MUST NOT be checked into source control; use approved secret stores.
- Dependencies MUST be scanned for known vulnerabilities before production
	deployment (automated tooling preferred).
- Data retention and privacy constraints (if applicable) MUST be declared in
	the relevant feature spec and enforced by tasks and CI checks.

## Security & Privacy (detailed)

Purpose: protect submitters' timetable data and minimize retention and exposure
while allowing the service to compute and share common availability.

Retention & Deletion
- Default retention (MVP): all uploaded artifacts (original images, submitted
	links, and derived availability grids) are retained for **72 hours (3 days)**
	from upload, after which they are automatically deleted.
- Users may be offered options (TODO to implement): `24h`, `72h`, `7 days`,
	or `Immediate delete` at upload time; selection affects stored copy lifetime.

Upload & Storage Policy
- MVP behavior: original uploaded images and raw link text are stored
	temporarily (max 72 hours) and then auto-deleted.
- Derived data: the normalized/parsed availability grid necessary for computing
	and presenting common free times MAY be stored for the retention period.
	This is expected to contain less identifiable information than raw images.
- Optional mode (TODO): a “stateless/transform-only” mode where originals are
	not persisted beyond in-memory processing and only the derived availability
	result is emitted and stored (or even not stored at all if user selects
	`Immediate delete`).

Access Control & Tokens
- Authentication: MVP operates without mandatory login. Access to group
	management (group leader actions) is controlled by a generated admin token
	embedded in the organizer link. Keep admin tokens secret and treat them as
	bearer tokens.
- Sharing: result pages are read-only and may be reachable via public share
	links. Do not include personal identifiers (email, student ID) in public
	views.
- Dev/ops access: operational access to raw data is restricted by least
	privilege and must be recorded in audit logs.

External Links & Crawling
- MVP: when users submit an external link (e.g., an Everytime link), the
	service stores only the submitted link text (for up to 72 hours). The
	service does **not** automatically crawl, scrape, or fetch content from
	external pages in MVP.
- Any future automatic collection requires an explicit consent/permission
	flow and legal review (TODO: policy & consent UX).

Transport & Storage Security
- Transport: TLS (HTTPS) required for all client-server communication.
- At-rest: apply storage-level encryption (platform default) for stored
	artifacts. Where feasible, encourage full at-rest encryption for originals;
	at minimum, metadata and any tokens MUST be encrypted or hashed.
- Logging: redact or mask sensitive values (links, tokens, image URLs) in
	logs; avoid logging full raw submissions.

Key Management
- MVP: rely on platform-managed keys where available; plan for KMS-based key
	management for production (TODO: KMS integration and rotation policy).

Compliance & Legal
- Principle: minimize collection and retention of personal data (data
	minimization). Provide a concise Privacy Notice describing: no-login model,
	short retention (72 hours default), auto-deletion, and how to request data
	deletion earlier.
- External services / SSO: MVP excludes school SSO and automatic external
	scraping to reduce regulatory footprint. Future expansions require formal
	legal review.

Operational Security
- Secrets: do not store API keys/secrets in repo; use secret managers.
- Vulnerability scanning: run dependency scans in CI and remediate high-risk
	findings before production release.
- Incident response: document a basic incident response procedure and contact
	list (TODO: populate contacts).

User Controls & Transparency
- Provide UI affordances to let uploaders: view their uploaded items, trigger
	immediate deletion, and select retention preferences from allowed options
	(TODO: retention UI and explicit consent copy).

## Development Workflow & Quality Gates

## Development Workflow & Quality Gates
- Pull requests MUST include: a link to the plan/spec, tests, and changelog
	entry when behavior changes.
- All PRs MUST pass CI, including linting, unit tests, and any required
	integration tests before merge.
- Code review: at least one approving review from a code owner or core
	maintainer is REQUIRED for changes to critical paths.
- Definition of Done for a feature: implemented tests pass, docs updated,
	security scan completed, and a versioning decision recorded if API changes
	occurred.

## Governance
Amendments to this constitution MUST follow the procedure below:

1. A written amendment proposal (PR) MUST be filed describing the change,
	 rationale, and migration steps.
2. The proposal MUST be reviewed by core maintainers and receive a majority
	 approval from designated code owners or maintainers defined in repository
	 settings.
3. If the amendment affects backward compatibility or core principles, the
	 proposal MUST include a clear migration plan and an appropriate version bump
	 per the Versioning rules above.

Compliance and reviews:
- An annual compliance review SHOULD be scheduled to validate adherence to the
	constitution; ad-hoc reviews can be triggered by major incidents or proposed
	governance changes.

**Version**: 0.1.0 | **Ratified**: 2026-02-11 | **Last Amended**: 2026-02-11
