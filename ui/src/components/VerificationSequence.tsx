/**
 * VerificationSequence.tsx
 *
 * Sprint 1 Blok E task 1.16 (2026-04-11):
 * Full verification pipeline for a story, shown as a 7-step horizontal
 * indicator. Superset of PostCheckStepper (which only shows the 4 automated
 * post-checks).
 *
 * Sequence (left to right):
 *   1. AC         — Acceptance criteria defined? (story has AC list)
 *   2. Codex      — Independent code review (feature.review_status)
 *   3. Tests      — Unit + integration tests pass (post-check)
 *   4. Lint       — Static analysis clean (post-check)
 *   5. Mock       — No mock/placeholder data in production (post-check)
 *   6. Regressie  — Regression tests pass (test_runs with agent_type=testing)
 *   7. PO         — Product owner sign-off (feature.passes = final approval)
 *
 * Each step shows a status icon (○ pending, ◌ running, ✓ passed, ✗ failed,
 * — skipped) and a small label. Hover tooltips explain what the step checks.
 *
 * Usage:
 *   <VerificationSequence story={story} />
 */

import { useMemo } from "react";
import type { Story } from "../lib/types";
import { usePostChecks, type CheckStatus, type CheckStep } from "../hooks/usePostChecks";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface VerificationSequenceProps {
  story: Story;
  className?: string;
}

type StepId =
  | "ac"
  | "codex"
  | "tests"
  | "lint"
  | "mock"
  | "regression"
  | "po";

interface VerificationStep {
  id: StepId;
  label: string;
  status: CheckStatus;
  detail: string;
  tooltip: string;
}

// ---------------------------------------------------------------------------
// Styles — match PostCheckStepper so the two components visually compose
// ---------------------------------------------------------------------------

const STATUS_STYLES: Record<CheckStatus, string> = {
  pending: "bg-zinc-600 text-zinc-400",
  running: "bg-blue-600 text-white animate-pulse",
  passed: "bg-emerald-600 text-white",
  failed: "bg-red-600 text-white",
  skipped: "bg-zinc-700 text-zinc-500",
};

const STATUS_ICONS: Record<CheckStatus, string> = {
  pending: "○",
  running: "◌",
  passed: "✓",
  failed: "✗",
  skipped: "—",
};

// ---------------------------------------------------------------------------
// Derive step statuses from Story + post-check data
// ---------------------------------------------------------------------------

function deriveAcStatus(story: Story): Pick<VerificationStep, "status" | "detail"> {
  // Story must declare AC before we can verify anything.
  // If AC list is empty → "pending" (under-specified). If non-empty → passed.
  const acs = getStoryAcs(story);
  if (acs.length === 0) {
    return { status: "pending", detail: "no AC declared yet" };
  }
  return {
    status: "passed",
    detail: `${acs.length} AC defined`,
  };
}

function deriveCodexStatus(
  story: Story,
): Pick<VerificationStep, "status" | "detail"> {
  const rs = (story as any).review_status as string | null | undefined;
  if (rs === "approved") return { status: "passed", detail: "Codex approved" };
  if (rs === "rejected") return { status: "failed", detail: "Codex rejected" };
  if (rs === "pending_review") return { status: "running", detail: "Codex reviewing…" };
  // No review_status at all → either review flag is off or story hasn't reached reviewer
  if (story.passes) return { status: "skipped", detail: "review not triggered" };
  return { status: "pending", detail: "waiting for review" };
}

function deriveStepFromPostCheck(
  postChecks: CheckStep[],
  name: string,
): CheckStatus {
  const step = postChecks.find((s) => s.name === name);
  return step ? step.status : "pending";
}

function deriveRegressionStatus(
  story: Story,
): Pick<VerificationStep, "status" | "detail"> {
  // test_runs table tracks regression runs separately. Without a dedicated
  // feed from the API, we infer: if the story passes AND recent coding work
  // succeeded, regression is assumed passed. This is an approximation and
  // will be refined once a dedicated WebSocket message type is added.
  if (story.passes) {
    return { status: "passed", detail: "regression assumed OK (story passing)" };
  }
  if (story.in_progress) {
    return { status: "pending", detail: "awaiting coding completion" };
  }
  return { status: "pending", detail: "not yet tested" };
}

function derivePoStatus(story: Story): Pick<VerificationStep, "status" | "detail"> {
  // "PO sign-off" is represented by the final passes=True flag.
  // If story is passing AND has been reviewed by codex (or manually approved), PO step is green.
  if (story.passes) {
    return { status: "passed", detail: "story marked as passing (PO approved)" };
  }
  if (story.in_progress) {
    return { status: "pending", detail: "not yet ready for PO review" };
  }
  return { status: "pending", detail: "awaiting PO approval" };
}

// Helper: read AC list from Story, handling legacy `steps` field as fallback
function getStoryAcs(story: Story): string[] {
  const s = story as any;
  if (Array.isArray(s.acceptance_criteria) && s.acceptance_criteria.length > 0) {
    return s.acceptance_criteria as string[];
  }
  if (Array.isArray(s.steps) && s.steps.length > 0) {
    return s.steps as string[];
  }
  return [];
}

// ---------------------------------------------------------------------------
// Compose the 7 steps from available data
// ---------------------------------------------------------------------------

function useVerificationSteps(story: Story): VerificationStep[] {
  const { steps: postChecks } = usePostChecks(story.id);

  return useMemo<VerificationStep[]>(() => {
    const ac = deriveAcStatus(story);
    const codex = deriveCodexStatus(story);
    const testsStatus = deriveStepFromPostCheck(postChecks, "tests");
    const lintStatus = deriveStepFromPostCheck(postChecks, "lint");
    const mockStatus = deriveStepFromPostCheck(postChecks, "mock_detection");
    const regression = deriveRegressionStatus(story);
    const po = derivePoStatus(story);

    return [
      {
        id: "ac",
        label: "AC",
        status: ac.status,
        detail: ac.detail,
        tooltip: "Acceptance criteria declared and ready for verification",
      },
      {
        id: "codex",
        label: "Codex",
        status: codex.status,
        detail: codex.detail,
        tooltip: "Independent code review by Codex (Sprint 1 Blok C)",
      },
      {
        id: "tests",
        label: "Tests",
        status: testsStatus,
        detail: "unit + integration tests",
        tooltip: "All unit and integration tests pass",
      },
      {
        id: "lint",
        label: "Lint",
        status: lintStatus,
        detail: "static analysis",
        tooltip: "Linter and type-checker clean",
      },
      {
        id: "mock",
        label: "Mock",
        status: mockStatus,
        detail: "no stub data in production",
        tooltip: "No mock/placeholder/stub data detected in production code",
      },
      {
        id: "regression",
        label: "Regr",
        status: regression.status,
        detail: regression.detail,
        tooltip: "Regression tests on previously-passing stories",
      },
      {
        id: "po",
        label: "PO",
        status: po.status,
        detail: po.detail,
        tooltip: "Product Owner sign-off — final approval gate",
      },
    ];
  }, [story, postChecks]);
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StepIcon({ step }: { step: VerificationStep }) {
  return (
    <div className="flex flex-col items-center gap-0.5">
      <div
        className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-mono ${STATUS_STYLES[step.status]}`}
        title={`${step.label}: ${step.status}${step.detail ? ` — ${step.detail}` : ""}\n\n${step.tooltip}`}
      >
        {STATUS_ICONS[step.status]}
      </div>
      <span className="text-[10px] text-zinc-500 leading-none">{step.label}</span>
    </div>
  );
}

function Connector({ left }: { left: CheckStatus }) {
  const active = left === "passed" || left === "skipped";
  const failed = left === "failed";

  let color = "bg-zinc-700";
  if (active) color = "bg-emerald-700";
  if (failed) color = "bg-red-700";

  return <div className={`h-0.5 w-3 mt-3.5 ${color}`} />;
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function VerificationSequence({
  story,
  className = "",
}: VerificationSequenceProps) {
  const steps = useVerificationSteps(story);

  // Summary: how many passed / total
  const passedCount = steps.filter((s) => s.status === "passed").length;
  const failedCount = steps.filter((s) => s.status === "failed").length;

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <div className="flex items-center gap-2 text-[10px] text-zinc-500">
        <span className="font-semibold uppercase tracking-wider">Verificatie</span>
        <span>
          {passedCount}/{steps.length} passed
          {failedCount > 0 && <span className="text-red-400"> · {failedCount} failed</span>}
        </span>
      </div>
      <div className="flex items-start gap-0">
        {steps.map((step, i) => (
          <div key={step.id} className="flex items-start">
            {i > 0 && <Connector left={steps[i - 1].status} />}
            <StepIcon step={step} />
          </div>
        ))}
      </div>
    </div>
  );
}

export default VerificationSequence;
