# Audit Report Template

<!-- WHAT: This reference defines the Phase 2 output contract, not audit findings.
HOW: Read it when rendering the audit; replace every {{field}} with collected evidence.
WHY: Lessons 2–3 place a substantial output schema in N3 references, keeping the skill entry point short. -->

## Rendering rules

<!-- WHAT: Separate evidence collection from presentation and publication.
HOW: Render the completed report in the conversation, then stop at its approval question.
WHY: A polished report must not imply permission to write files or refactor; the challenge explicitly requires a human gate. -->

- Fill the template below from the current target and the anti-pattern catalog.
  Treat `{{...}}` as intentional template fields, not literal report content.
- During Phases 1–2, display the report only. Do not create the report directory,
  save a draft, install dependencies, seed data, or start a writing application.
- Resolve a user-specified report path against its stated root. Otherwise propose
  `reports/architecture-audit.md` inside the target project before asking for approval.
  A path in a parent repository is appropriate when the user explicitly specifies it.
- After explicit approval, save the report exactly as reviewed before editing
  application code. Keep this pre-refactoring audit separate from validation results.
- Use project-relative source paths and inclusive line ranges from the audited
  snapshot. Make links relative to the eventual report location when practical.

<!-- WHAT: Make the report independently traceable to the bytes actually inspected.
HOW: Derive the commit and worktree state at execution; record uncommitted deviations explicitly.
WHY: A commit alone cannot identify dirty or untracked source, and line numbers change during refactoring. -->

- Record the actual audited commit, target directory, and source scope. If the user
  provided a historical commit, verify that the inspected source matches it; do not
  label current worktree code with that hash merely because it appears in a plan.
- For a dirty worktree, distinguish the base commit from tracked modifications and
  untracked application files. Record paths and content hashes, or an equivalent
  reproducible description, without saving a new snapshot before approval.
- Separate static observations, inferences, and previously executed runtime evidence.
  Reused baseline results retain their commit, environment, time, and known limitations.
  State “not executed in this phase” for checks that were not run.
- Count each distinct finding once; repeat its location list when one issue spans
  files. Reconcile severity totals with the finding list. Do not inflate counts to
  satisfy a minimum, or treat every textual match as a confirmed vulnerability.
- Mask secrets, passwords, hashes, tokens, and payment data in excerpts and output.
  Preserve field names and locations so the issue remains reviewable.

## After approval: separate validation record

<!-- WHAT: Preserve the original evidence while reporting the actual outcome.
HOW: Use a separate validation artifact or conversation output, referring back to the saved finding IDs.
WHY: Overwriting the audit would discard the exact legacy locations needed to review what changed. -->

Record changed files, finding disposition, actual boot and endpoint results,
database checks, intentional contract differences, and failures or unverified
items. Report the number of routes exercised separately from line coverage.
Do not mark remaining failures as resolved or claim “zero anti-patterns” from boot alone.

## Report to render

<!-- WHAT: The following sections are the report itself.
HOW: Copy the structure, repeat the finding block for real issues, and remove empty optional rows.
WHY: Stable fields make audits comparable across stacks without prescribing project-specific filenames or schemas. -->

# Architecture Audit Report — {{project_name}}

## Audited state

- **Target:** `{{target_directory}}`.
- **Repository root:** `{{repository_root_or_not_applicable}}`.
- **Audited commit:** `{{verified_full_commit_or_no_git_repository}}`.
- **Worktree state:** {{clean_or_explicit_tracked_and_untracked_source_differences}}.
- **Snapshot qualification:** {{commit_matches_source_or_uncommitted_source_identifiers}}.
- **Audit time:** {{timestamp_with_timezone}}.
- **Tool/model:** {{available_tool_and_model_identifiers_or_unknown}}.
- **Proposed report destination:** `{{reviewed_report_path}}`.

## Project analysis

| Field | Observed value | Evidence |
|---|---|---|
| Language and runtime | {{language_and_verified_or_unknown_runtime}} | {{manifest_or_existing_runtime_evidence}} |
| Framework | {{framework_and_version_status}} | {{declaration_lockfile_or_resolved_metadata}} |
| Database | {{engine_storage_and_initialization_behavior}} | {{source_location}} |
| Domain | {{implemented_business_domain}} | {{routes_entities_and_workflows}} |
| Architecture | {{current_responsibilities_and_dependencies}} | {{source_locations}} |
| Inventory | {{source_file_count_and_source_line_count}} | {{scope_and_counting_definition}} |
| Exclusions | {{excluded_dependencies_generated_files_and_nonapplication_content}} | {{reason}} |

## Severity summary

| CRITICAL | HIGH | MEDIUM | LOW | Total |
|---|---|---|---|---|
| {{critical_count}} | {{high_count}} | {{medium_count}} | {{low_count}} | {{total_count}} |

## Findings

<!-- WHAT: Each finding connects a reproducible observation to a justified change.
HOW: Sort CRITICAL → HIGH → MEDIUM → LOW; use stable F-IDs and catalog AP-IDs.
WHY: Exact evidence and explicit inference prevent generic “bad code” claims and make manual comparison possible. -->

### {{F_ID}} — [{{severity}}] {{finding_title}}

- **Catalog:** {{AP_ID_and_category}}.
- **Location:** `{{project_relative_file}}:{{start_line}}–{{end_line}}`.
- **Additional locations:** {{exact_ranges_or_none}}.
- **Evidence type:** {{static_observation_runtime_observation_or_inference}}.
- **Observation:** {{specific_behavior_or_responsibility_violation}}.
- **Evidence:** {{short_sanitized_excerpt_or_linked_baseline_case}}.
- **Severity rationale:** {{why_the_impact_meets_this_severity}}.
- **Impact:** {{concrete_security_architecture_quality_or_performance_consequence}}.
- **Context and false-positive check:** {{input_origin_reachability_and_relevant_limits}}.
- **Recommendation:** {{targeted_transformation_and_playbook_AP_ID}}.
- **Compatibility:** {{valid_contracts_to_preserve_and_intentional_changes_to_review}}.
- **Verification:** {{specific_endpoint_or_invariant_and_expected_database_effect}}.

Repeat this block for each confirmed finding; do not leave an empty finding.

## Deprecated API assessment

| API and exact source range | Applicable version | Official evidence | Replacement and compatibility |
|---|---|---|---|
| {{confirmed_API_or_none_confirmed}} | {{verified_version_or_unresolved}} | {{direct_official_reference_and_status}} | {{replacement_preserving_return_and_error_semantics}} |

An unresolved version or missing authoritative source is a verification item,
not a confirmed deprecation finding. State when no applicable deprecated API was found.

## Comparison with the manual analysis

| Manual reference and ID | Matching finding ID | Match and reason |
|---|---|---|
| {{manual_document_and_ID_or_not_available}} | {{finding_ID_or_none}} | {{confirmed_not_reproduced_or_unverified}} |

- **Manual problems confirmed:** {{count_of_distinct_matches}}.
- **Challenge checks:** {{at_least_five_findings_and_one_CRITICAL_or_HIGH_status}}.
- **Required manual overlap:** {{at_least_five_matches_when_required_or_missing_evidence}}.

If the manual analysis or required matches are missing, state the gap. Do not
claim an assisted finding was manually documented or invent matches to pass.

## Proposed MVC refactoring

1. {{proposed_models_routes_views_controllers_and_optional_services}}.
2. {{configuration_error_handling_and_composition_changes}}.
3. {{incremental_transformation_order_mapped_to_finding_IDs}}.
4. {{data_migration_and_existing_data_preservation_strategy_or_not_needed}}.

| Existing contract | Preserve or intentionally change | Reason and planned verification |
|---|---|---|
| {{method_route_payload_status_or_response_field}} | {{approved_change_or_unchanged_valid_behavior}} | {{finding_ID_and_test_scenario}} |

## Validation plan and existing baseline

- **Existing evidence:** {{baseline_paths_commit_environment_time_or_not_available}}.
- **Evidence compatibility:** {{whether_the_baseline_matches_the_audited_source_and_runtime}}.
- **Checks executed during this audit:** {{none_or_existing_read_only_evidence_only}}.
- **Post-approval boot command:** `{{target_specific_command}}`.
- **Data isolation:** {{disposable_database_seed_effects_and_local_data_preservation}}.

| Method and route | Input | Observed baseline status | Relevant response fields | Database effect | Preserve or correct |
|---|---|---|---|---|---|
| {{route_or_link_to_complete_matrix}} | {{sanitized_payload_query_or_none}} | {{observed_or_not_executed}} | {{fields_or_unverified}} | {{observed_effect_or_unverified}} | {{desired_contract_or_fix}} |

Cover every original method/route and the affected success, invalid-input, and
authorization scenarios. Distinguish observed table counts from field updates
confirmed by SQL. A planned test is not a passing test.

## Approval required

<!-- WHAT: End Phase 2 here, after the user has seen both findings and planned effects.
HOW: Ask once and wait; silence, automatic test success, or the original skill invocation is not this approval.
WHY: The challenge requires approval after review, before even the audit report is written to disk. -->

May I save this reviewed audit to `{{reviewed_report_path}}` and begin Phase 3
for `{{target_directory}}`, including the contract and data changes listed above?

**Awaiting an explicit answer. No files have been changed by Phases 1–2.**
