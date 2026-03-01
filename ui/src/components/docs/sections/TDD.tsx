/**
 * TDD Documentation Section
 *
 * Explains the Red/Green/Refactor TDD integration in MQ DevEngine.
 * Covers: operating modes, workflow, PM guide for testable features.
 */

interface TDDProps {
  onNavigate?: (sectionId: string) => void
}

export function TDD({ onNavigate: _onNavigate }: TDDProps) {
  return (
    <div className="space-y-8 max-w-4xl">
      {/* Overview */}
      <section id="tdd-overview" className="space-y-3">
        <h1 className="text-3xl font-bold border-b-4 border-black pb-2">
          Test-Driven Development
        </h1>
        <p className="text-base leading-relaxed">
          MQ DevEngine supports opt-in TDD mode where coding agents follow the
          Red/Green/Refactor cycle. Instead of verifying features visually through
          browser automation, agents write automated tests that prove the code works.
        </p>
        <p className="text-sm text-neutral-600">
          Based on Simon Willison&apos;s agentic TDD patterns and Matt Pocock&apos;s TDD skill.
        </p>
      </section>

      {/* Operating Modes */}
      <section id="tdd-modes" className="space-y-4">
        <h2 className="text-2xl font-bold">Four Operating Modes</h2>
        <p className="text-sm">
          TDD and browser testing are independent toggles. The combination creates four modes:
        </p>
        <div className="overflow-x-auto">
          <table className="w-full border-4 border-black text-sm">
            <thead>
              <tr className="bg-black text-white">
                <th className="p-2 text-left">TDD</th>
                <th className="p-2 text-left">YOLO</th>
                <th className="p-2 text-left">Mode</th>
                <th className="p-2 text-left">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b-2 border-black">
                <td className="p-2">Off</td>
                <td className="p-2">Off</td>
                <td className="p-2 font-bold">Standard</td>
                <td className="p-2">Current behavior: browser verification</td>
              </tr>
              <tr className="border-b-2 border-black bg-cyan-50">
                <td className="p-2">On</td>
                <td className="p-2">Off</td>
                <td className="p-2 font-bold">TDD + Browser</td>
                <td className="p-2">Maximum quality, highest token cost</td>
              </tr>
              <tr className="border-b-2 border-black bg-yellow-50">
                <td className="p-2">Off</td>
                <td className="p-2">On</td>
                <td className="p-2 font-bold">YOLO</td>
                <td className="p-2">Only lint/typecheck (rapid prototyping)</td>
              </tr>
              <tr className="bg-green-50">
                <td className="p-2">On</td>
                <td className="p-2">On</td>
                <td className="p-2 font-bold">TDD Mode</td>
                <td className="p-2">Tests = verification, no browser needed</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="text-sm italic">
          The TDD + YOLO combination is the recommended mode for most projects:
          fast feedback through automated tests without browser overhead.
        </p>
      </section>

      {/* Workflow */}
      <section id="tdd-workflow" className="space-y-4">
        <h2 className="text-2xl font-bold">The Red/Green/Refactor Cycle</h2>
        <div className="border-4 border-black p-4 bg-neutral-50 font-mono text-sm space-y-2">
          <div className="flex items-center gap-2">
            <span className="inline-block w-4 h-4 bg-red-500 border-2 border-black" />
            <span><strong>RED:</strong> Write ONE failing test &rarr; Run it &rarr; Confirm it FAILS</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block w-4 h-4 bg-green-500 border-2 border-black" />
            <span><strong>GREEN:</strong> Write MINIMAL code to pass &rarr; Run it &rarr; Confirm it PASSES</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block w-4 h-4 bg-blue-500 border-2 border-black" />
            <span><strong>REFACTOR:</strong> Clean up &rarr; Run tests &rarr; Confirm STILL green</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block w-4 h-4 bg-yellow-400 border-2 border-black" />
            <span><strong>REPEAT</strong> for the next behaviour</span>
          </div>
        </div>
        <div className="border-4 border-red-700 bg-red-50 p-3 text-sm">
          <strong>Critical rule:</strong> ONE test at a time. Never write multiple tests before making them pass.
          This prevents the LLM from batch-writing 20 shallow tests (horizontal slicing).
        </div>
      </section>

      {/* Agent Roles */}
      <section id="tdd-agents" className="space-y-4">
        <h2 className="text-2xl font-bold">Agent Roles in TDD</h2>
        <div className="grid gap-3">
          <div className="border-4 border-black p-3">
            <h3 className="font-bold">Architect Agent</h3>
            <p className="text-sm">
              Decides the test framework (Vitest, Jest, pytest) and stores the decision
              in session memory. Coding agents recall this via <code>memory_recall</code>.
            </p>
          </div>
          <div className="border-4 border-black p-3">
            <h3 className="font-bold">Initializer Agent</h3>
            <p className="text-sm">
              Creates an additional infrastructure feature: &quot;Test framework configured and passing&quot;.
              This ensures the test runner is set up before any TDD features begin.
            </p>
          </div>
          <div className="border-4 border-black p-3">
            <h3 className="font-bold">Coding Agent</h3>
            <p className="text-sm">
              Follows the Red/Green/Refactor cycle for each feature.
              Plans the interface, lists testable behaviours, then implements one test at a time.
              Records test info via <code>feature_record_test</code>.
            </p>
          </div>
          <div className="border-4 border-black p-3">
            <h3 className="font-bold">Testing Agent</h3>
            <p className="text-sm">
              Runs the automated test suite BEFORE browser verification.
              If tests fail, investigates and fixes the regression.
            </p>
          </div>
          <div className="border-4 border-black p-3">
            <h3 className="font-bold">Review Agent</h3>
            <p className="text-sm">
              Checks that tests exist and verify behaviour (not implementation details).
              Catches tests that are too tightly coupled to internals.
            </p>
          </div>
        </div>
      </section>

      {/* PM Guide */}
      <section id="tdd-pm-guide" className="space-y-4">
        <h2 className="text-2xl font-bold">Writing TDD-Friendly Features</h2>

        <div className="grid md:grid-cols-2 gap-4">
          <div className="border-4 border-red-700 p-3">
            <h3 className="font-bold text-red-700 mb-2">Before (Visual Checks)</h3>
            <p className="text-sm italic">
              &quot;User can create a todo: Navigate to /todos, click &apos;New&apos;, fill in
              title, click save, verify todo appears in list&quot;
            </p>
          </div>
          <div className="border-4 border-green-700 p-3">
            <h3 className="font-bold text-green-700 mb-2">After (Testable Behaviours)</h3>
            <p className="text-sm italic">
              &quot;User can create a todo: POST /api/todos with &#123;title: string&#125; returns 201
              with &#123;id, title, completed: false&#125;. Todo appears in GET /api/todos response.
              Missing title returns 400 with validation error.&quot;
            </p>
          </div>
        </div>

        <h3 className="font-bold text-lg mt-4">When to Skip TDD</h3>
        <ul className="list-disc list-inside text-sm space-y-1">
          <li>Pure visual features (layout, colors, animations)</li>
          <li>Accessibility testing (requires axe-core or screen reader)</li>
          <li>Performance benchmarks</li>
          <li>Features that are 100% CSS/HTML with no logic</li>
        </ul>

        <h3 className="font-bold text-lg mt-4">Token Cost Impact</h3>
        <p className="text-sm">
          TDD increases token usage by approximately 30-80% per feature (due to writing tests,
          running them, seeing failures, implementing, and re-running). However, regression rates
          drop significantly, and the testing agent becomes faster (running <code>npm test</code> instead
          of browser automation). Budget 2 features per batch instead of 3 when TDD is enabled.
        </p>
      </section>
    </div>
  )
}
