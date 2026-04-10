/**
 * usePostChecks.ts — React hook for consuming post_check_update WebSocket events.
 *
 * Maintains step state for a specific feature and exposes it to PostCheckStepper.
 *
 * Integration point: call handlePostCheckMessage() from the existing
 * useWebSocket hook when message.type === "post_check_update".
 */

import { useCallback, useMemo, useRef, useSyncExternalStore } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type CheckStatus = "pending" | "running" | "passed" | "failed" | "skipped";

export interface CheckStep {
  name: string;
  status: CheckStatus;
  detail: string;
}

export interface PostCheckState {
  steps: CheckStep[];
  attempt: number;
  maxAttempts: number;
  visible: boolean;
}

/** Shape of the WebSocket message from retry_controller.py */
export interface PostCheckMessage {
  type: "post_check_update";
  feature_id: number;
  event: "check_start" | "check_done" | "retry" | "complete";
  check_name: string | null;
  passed: boolean | null;
  attempt: number;
  max_attempts: number;
  detail: string;
}

// ---------------------------------------------------------------------------
// Default steps (matches checks.yaml order)
// ---------------------------------------------------------------------------

const DEFAULT_STEPS: CheckStep[] = [
  { name: "lint", status: "pending", detail: "" },
  { name: "mock_detection", status: "pending", detail: "" },
  { name: "tests", status: "pending", detail: "" },
  { name: "coverage", status: "pending", detail: "" },
];

function resetSteps(): CheckStep[] {
  return DEFAULT_STEPS.map((s) => ({ ...s, status: "pending", detail: "" }));
}

// ---------------------------------------------------------------------------
// Store — one per feature, manages state outside React render cycle
// ---------------------------------------------------------------------------

type Listener = () => void;

class PostCheckStore {
  private states = new Map<number, PostCheckState>();
  private listeners = new Set<Listener>();

  getState(featureId: number): PostCheckState {
    return (
      this.states.get(featureId) ?? {
        steps: resetSteps(),
        attempt: 0,
        maxAttempts: 3,
        visible: false,
      }
    );
  }

  handleMessage(msg: PostCheckMessage): void {
    const { feature_id, event, check_name, passed, attempt, max_attempts, detail } = msg;

    const current = this.getState(feature_id);
    let steps = [...current.steps.map((s) => ({ ...s }))];
    let visible = true;

    switch (event) {
      case "check_start":
        // New attempt — reset all steps, mark first as running
        steps = resetSteps();
        if (steps.length > 0) {
          steps[0].status = "running";
        }
        break;

      case "check_done": {
        if (!check_name) break;
        const idx = steps.findIndex((s) => s.name === check_name);
        if (idx === -1) break;

        steps[idx].status = passed ? "passed" : "failed";
        steps[idx].detail = detail;

        // If passed and there's a next step, mark it running
        if (passed && idx + 1 < steps.length) {
          steps[idx + 1].status = "running";
        }
        break;
      }

      case "retry":
        // Keep failed state visible briefly — check_start will reset
        break;

      case "complete":
        // Final state — keep steps as-is, stop pulsing
        steps = steps.map((s) =>
          s.status === "running" ? { ...s, status: "pending" } : s
        );
        break;
    }

    this.states.set(feature_id, {
      steps,
      attempt,
      maxAttempts: max_attempts,
      visible,
    });

    this.notify();
  }

  /** Call to hide the stepper (e.g., when feature moves to next state). */
  dismiss(featureId: number): void {
    this.states.delete(featureId);
    this.notify();
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify(): void {
    for (const listener of this.listeners) {
      listener();
    }
  }
}

// Singleton store — shared across all PostCheckStepper instances
const store = new PostCheckStore();

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Call this from your WebSocket message handler:
 *
 *   if (msg.type === "post_check_update") {
 *     handlePostCheckMessage(msg);
 *   }
 */
export function handlePostCheckMessage(msg: PostCheckMessage): void {
  store.handleMessage(msg);
}

/**
 * Dismiss the stepper for a feature (e.g., after it transitions to passing).
 */
export function dismissPostChecks(featureId: number): void {
  store.dismiss(featureId);
}

/**
 * React hook — returns current post-check state for a feature.
 */
export function usePostChecks(featureId: number): PostCheckState {
  const subscribe = useCallback(
    (onStoreChange: () => void) => store.subscribe(onStoreChange),
    []
  );
  const getSnapshot = useCallback(() => store.getState(featureId), [featureId]);

  // useSyncExternalStore ensures consistent reads during concurrent rendering
  const state = useSyncExternalStore(subscribe, getSnapshot);

  return state;
}
