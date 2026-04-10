/**
 * PostCheckStepper.tsx — Mini-stepper for AgentCard showing post-check progress.
 *
 * Displays: lint → mock → tests → coverage as a horizontal step indicator.
 * Each step shows: pending (gray), running (blue pulse), passed (green), failed (red).
 *
 * Consumes WebSocket messages of type "post_check_update" via the usePostChecks hook.
 *
 * Usage in AgentCard:
 *   <PostCheckStepper featureId={feature.id} />
 */

import { useMemo } from "react";
import { usePostChecks, type CheckStep, type CheckStatus } from "./usePostChecks";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PostCheckStepperProps {
  featureId: number;
  className?: string;
}

// ---------------------------------------------------------------------------
// Step icon component
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

const STEP_LABELS: Record<string, string> = {
  lint: "Lint",
  mock_detection: "Mock",
  tests: "Tests",
  coverage: "Cov",
};

function StepIcon({ step }: { step: CheckStep }) {
  const label = STEP_LABELS[step.name] ?? step.name;

  return (
    <div className="flex flex-col items-center gap-0.5">
      <div
        className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-mono ${STATUS_STYLES[step.status]}`}
        title={`${label}: ${step.status}${step.detail ? ` — ${step.detail}` : ""}`}
      >
        {STATUS_ICONS[step.status]}
      </div>
      <span className="text-[10px] text-zinc-500 leading-none">{label}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Connector line between steps
// ---------------------------------------------------------------------------

function Connector({ left, right }: { left: CheckStatus; right: CheckStatus }) {
  const active = left === "passed" || left === "skipped";
  const failed = left === "failed";

  let color = "bg-zinc-700";
  if (active) color = "bg-emerald-700";
  if (failed) color = "bg-red-700";

  return <div className={`h-0.5 w-4 mt-3 ${color}`} />;
}

// ---------------------------------------------------------------------------
// Attempt counter
// ---------------------------------------------------------------------------

function AttemptBadge({ attempt, maxAttempts }: { attempt: number; maxAttempts: number }) {
  if (maxAttempts <= 1) return null;

  return (
    <span className="text-[10px] text-zinc-500 ml-2 mt-3">
      {attempt}/{maxAttempts}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function PostCheckStepper({ featureId, className = "" }: PostCheckStepperProps) {
  const { steps, attempt, maxAttempts, visible } = usePostChecks(featureId);

  if (!visible) return null;

  return (
    <div className={`flex items-start gap-0 ${className}`}>
      {steps.map((step, i) => (
        <div key={step.name} className="flex items-start">
          {i > 0 && <Connector left={steps[i - 1].status} right={step.status} />}
          <StepIcon step={step} />
        </div>
      ))}
      <AttemptBadge attempt={attempt} maxAttempts={maxAttempts} />
    </div>
  );
}

export default PostCheckStepper;
