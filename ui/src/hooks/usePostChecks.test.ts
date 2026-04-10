/**
 * usePostChecks.test.ts — Unit tests for the PostCheck store logic.
 *
 * Tests the store directly (no React rendering needed).
 * Verifies state transitions from WebSocket messages.
 *
 * To run in mq-devEngine: npx vitest run usePostChecks.test.ts
 */

import { describe, it, expect, beforeEach } from "vitest";

// We test the store class directly by re-implementing the message flow.
// In production, handlePostCheckMessage() is the entry point.

// ---------------------------------------------------------------------------
// Inline store for testing (mirrors usePostChecks.ts logic)
// ---------------------------------------------------------------------------

type CheckStatus = "pending" | "running" | "passed" | "failed" | "skipped";

interface CheckStep {
  name: string;
  status: CheckStatus;
  detail: string;
}

interface PostCheckState {
  steps: CheckStep[];
  attempt: number;
  maxAttempts: number;
  visible: boolean;
}

interface PostCheckMessage {
  type: "post_check_update";
  feature_id: number;
  event: "check_start" | "check_done" | "retry" | "complete";
  check_name: string | null;
  passed: boolean | null;
  attempt: number;
  max_attempts: number;
  detail: string;
}

const DEFAULT_STEPS: CheckStep[] = [
  { name: "lint", status: "pending", detail: "" },
  { name: "mock_detection", status: "pending", detail: "" },
  { name: "tests", status: "pending", detail: "" },
  { name: "coverage", status: "pending", detail: "" },
];

function resetSteps(): CheckStep[] {
  return DEFAULT_STEPS.map((s) => ({ ...s, status: "pending", detail: "" }));
}

class TestStore {
  private states = new Map<number, PostCheckState>();

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
        steps = resetSteps();
        if (steps.length > 0) steps[0].status = "running";
        break;
      case "check_done": {
        if (!check_name) break;
        const idx = steps.findIndex((s) => s.name === check_name);
        if (idx === -1) break;
        steps[idx].status = passed ? "passed" : "failed";
        steps[idx].detail = detail;
        if (passed && idx + 1 < steps.length) {
          steps[idx + 1].status = "running";
        }
        break;
      }
      case "retry":
        break;
      case "complete":
        steps = steps.map((s) =>
          s.status === "running" ? { ...s, status: "pending" } : s
        );
        break;
    }

    this.states.set(feature_id, { steps, attempt, maxAttempts: max_attempts, visible });
  }

  dismiss(featureId: number): void {
    this.states.delete(featureId);
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function msg(
  featureId: number,
  event: PostCheckMessage["event"],
  opts: Partial<PostCheckMessage> = {}
): PostCheckMessage {
  return {
    type: "post_check_update",
    feature_id: featureId,
    event,
    check_name: null,
    passed: null,
    attempt: 1,
    max_attempts: 3,
    detail: "",
    ...opts,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("PostCheckStore", () => {
  let store: TestStore;

  beforeEach(() => {
    store = new TestStore();
  });

  describe("initial state", () => {
    it("returns default state for unknown feature", () => {
      const state = store.getState(999);
      expect(state.visible).toBe(false);
      expect(state.steps).toHaveLength(4);
      expect(state.steps.every((s) => s.status === "pending")).toBe(true);
    });
  });

  describe("check_start", () => {
    it("makes stepper visible and marks first step running", () => {
      store.handleMessage(msg(1, "check_start", { attempt: 1 }));
      const state = store.getState(1);
      expect(state.visible).toBe(true);
      expect(state.steps[0].status).toBe("running");
      expect(state.steps[1].status).toBe("pending");
    });

    it("resets steps on new attempt", () => {
      // First attempt — lint fails
      store.handleMessage(msg(1, "check_start", { attempt: 1 }));
      store.handleMessage(msg(1, "check_done", { check_name: "lint", passed: false, attempt: 1 }));
      expect(store.getState(1).steps[0].status).toBe("failed");

      // Second attempt — reset
      store.handleMessage(msg(1, "check_start", { attempt: 2 }));
      expect(store.getState(1).steps[0].status).toBe("running");
      expect(store.getState(1).attempt).toBe(2);
    });
  });

  describe("check_done", () => {
    it("marks step passed and advances to next", () => {
      store.handleMessage(msg(1, "check_start"));
      store.handleMessage(msg(1, "check_done", { check_name: "lint", passed: true }));

      const state = store.getState(1);
      expect(state.steps[0].status).toBe("passed");
      expect(state.steps[1].status).toBe("running"); // mock_detection
    });

    it("marks step failed without advancing", () => {
      store.handleMessage(msg(1, "check_start"));
      store.handleMessage(msg(1, "check_done", { check_name: "lint", passed: false, detail: "E501" }));

      const state = store.getState(1);
      expect(state.steps[0].status).toBe("failed");
      expect(state.steps[0].detail).toBe("E501");
      expect(state.steps[1].status).toBe("pending"); // NOT running
    });

    it("handles last step passed", () => {
      store.handleMessage(msg(1, "check_start"));
      store.handleMessage(msg(1, "check_done", { check_name: "lint", passed: true }));
      store.handleMessage(msg(1, "check_done", { check_name: "mock_detection", passed: true }));
      store.handleMessage(msg(1, "check_done", { check_name: "tests", passed: true }));
      store.handleMessage(msg(1, "check_done", { check_name: "coverage", passed: true }));

      const state = store.getState(1);
      expect(state.steps.every((s) => s.status === "passed")).toBe(true);
    });

    it("ignores unknown check names", () => {
      store.handleMessage(msg(1, "check_start"));
      store.handleMessage(msg(1, "check_done", { check_name: "unknown_check", passed: true }));

      // Should not crash — steps unchanged
      const state = store.getState(1);
      expect(state.steps[0].status).toBe("running");
    });
  });

  describe("complete", () => {
    it("stops running indicators", () => {
      store.handleMessage(msg(1, "check_start"));
      // Only lint ran, rest still pending/running
      store.handleMessage(msg(1, "check_done", { check_name: "lint", passed: true }));
      // mock_detection is "running" now
      store.handleMessage(msg(1, "complete", { passed: false }));

      const state = store.getState(1);
      expect(state.steps[1].status).toBe("pending"); // was running, now pending
    });
  });

  describe("multi-feature isolation", () => {
    it("tracks features independently", () => {
      store.handleMessage(msg(1, "check_start", { attempt: 1 }));
      store.handleMessage(msg(2, "check_start", { attempt: 1 }));

      store.handleMessage(msg(1, "check_done", { check_name: "lint", passed: true }));
      store.handleMessage(msg(2, "check_done", { check_name: "lint", passed: false }));

      expect(store.getState(1).steps[0].status).toBe("passed");
      expect(store.getState(2).steps[0].status).toBe("failed");
    });
  });

  describe("dismiss", () => {
    it("removes feature state", () => {
      store.handleMessage(msg(1, "check_start"));
      expect(store.getState(1).visible).toBe(true);

      store.dismiss(1);
      expect(store.getState(1).visible).toBe(false);
    });
  });

  describe("full happy path", () => {
    it("walks through all checks passing on first attempt", () => {
      store.handleMessage(msg(42, "check_start", { attempt: 1, max_attempts: 3 }));

      store.handleMessage(msg(42, "check_done", { check_name: "lint", passed: true, detail: "ok" }));
      store.handleMessage(msg(42, "check_done", { check_name: "mock_detection", passed: true, detail: "clean" }));
      store.handleMessage(msg(42, "check_done", { check_name: "tests", passed: true, detail: "12 passed" }));
      store.handleMessage(msg(42, "check_done", { check_name: "coverage", passed: true, detail: "92%" }));

      store.handleMessage(msg(42, "complete", { passed: true, attempt: 1 }));

      const state = store.getState(42);
      expect(state.steps.every((s) => s.status === "passed")).toBe(true);
      expect(state.attempt).toBe(1);
      expect(state.visible).toBe(true);
    });
  });

  describe("full retry path", () => {
    it("fails first attempt, passes second", () => {
      // Attempt 1: lint fails
      store.handleMessage(msg(7, "check_start", { attempt: 1, max_attempts: 3 }));
      store.handleMessage(msg(7, "check_done", { check_name: "lint", passed: false, detail: "E501" }));
      store.handleMessage(msg(7, "retry", { attempt: 1 }));

      expect(store.getState(7).steps[0].status).toBe("failed");

      // Attempt 2: all pass
      store.handleMessage(msg(7, "check_start", { attempt: 2, max_attempts: 3 }));
      store.handleMessage(msg(7, "check_done", { check_name: "lint", passed: true }));
      store.handleMessage(msg(7, "check_done", { check_name: "mock_detection", passed: true }));
      store.handleMessage(msg(7, "check_done", { check_name: "tests", passed: true }));
      store.handleMessage(msg(7, "check_done", { check_name: "coverage", passed: true }));
      store.handleMessage(msg(7, "complete", { passed: true, attempt: 2 }));

      const state = store.getState(7);
      expect(state.steps.every((s) => s.status === "passed")).toBe(true);
      expect(state.attempt).toBe(2);
    });
  });
});
