# Research: Open-Source Requirements Gathering Tools

**Date:** 2026-02-12 (Broad Search Update)
**Scope:** Comprehensive search across GitHub, GitLab, Codeberg, SourceForge, Product Hunt, HackerNews, awesome-lists, EU research projects, open-source directories (AlternativeTo, OpenAlternative), and requirements management communities.

**Prior Research:** Initial survey (same date) covered 30+ tools across AI spec tools, conversational builders, AI workflow engines, chat UI libraries, story mapping tools, PM platforms, and story generators.

---

## Executive Summary

After two rounds of exhaustive research covering 50+ tools across every platform and directory we could find:

1. **No single open-source tool exists** that combines: conversational/wizard-based requirements gathering, hierarchical work item output (Epics > Features > Stories > Tasks), existing backlog import/refinement, and Plane integration. This is a genuine, validated gap in the market.

2. **The open-source requirements management landscape is bifurcated:** Traditional RM tools (StrictDoc, Doorstop, rmToo, OSRMT) are document-centric with outdated UIs and no AI. Modern PM tools (Plane, Taiga, OpenProject, Huly) handle backlogs but have no requirements discovery/gathering workflow. Feedback tools (Fider, ClearFlask, Astuto) collect user input but do not decompose it into work items. AI tools (MetaGPT, StoryMachine) generate from scratch but cannot import or refine existing backlogs.

3. **Two viable build paths exist:** (a) Fork Eververse (MIT, Next.js/React/Supabase) and extend with conversational AI + Plane integration, or (b) Build purpose-built using assistant-ui/CopilotKit components + FastAPI backend + Plane Python SDK. Both are medium-effort with high differentiation potential.

---

## Consolidated Tool Inventory (All Sources)

### TIER 1: Closest to Requirements (Serious Candidates for Fork/Adapt)

---

#### 1. Eververse
- **URL:** https://github.com/haydenbleasel/eververse
- **Platform:** GitHub
- **Stars:** 346 | **License:** MIT
- **Tech Stack:** Next.js (React), TypeScript, Supabase (PostgreSQL), shadcn/ui, TipTap editor, Excalidraw canvas, Stripe
- **Last Active:** January 2026 (v1.6.8)
- **What It Does:** Open-source product management platform. Explore problems, ideate solutions, prioritize features (RICE scoring), plan roadmaps (Gantt/calendar), AI-powered feedback summarization and sentiment analysis.
- **Backlog Import:** Integrations for push/pull with Jira, GitHub, Linear. No CSV/Markdown import.
- **Hierarchy:** Features and roadmap items. Does NOT explicitly support Epic > Feature > Story > Task as distinct entity types.
- **Fit Score:** 40% -- Best existing foundation. Missing: conversational requirements gathering, hierarchical decomposition, Plane integration, wizard/guided workflow, backlog import from CSV/Markdown.
- **Fork Viability:** HIGH. MIT license. Modern stack matches our needs. Would need: (1) conversational/wizard-based elicitation flow, (2) hierarchical work item decomposition, (3) Plane API integration via plane-sdk, (4) backlog import from CSV/Markdown/Plane, (5) AI-powered story splitting/refinement.

---

#### 2. StrictDoc
- **URL:** https://github.com/strictdoc-project/strictdoc
- **Platform:** GitHub
- **Stars:** 248 | **License:** Apache 2.0
- **Tech Stack:** Python (79%), Jinja templates, JavaScript, CSS, Rust components
- **Last Active:** February 2026 (87 releases, actively maintained)
- **What It Does:** Technical requirements specifications. Hierarchical requirement documents with traceability links. Built-in web server (`strictdoc server`) for viewing/editing.
- **Backlog Import:** YES -- ReqIF import/export (bidirectional with Doors, Polarion, etc.), Excel export, CSV capability. Tool-specific ReqIF profiles.
- **Web UI:** YES -- built-in web server for viewing and editing requirements. Changes write back to .sdoc files.
- **Hierarchy:** YES -- hierarchical tree of requirement documents with parent-child traceability.
- **Fit Score:** 35% -- Strongest import/export and traceability. Missing: modern React UI (uses Jinja templates), agile work item format, Plane integration, AI assistance, conversational flow.
- **Fork Viability:** MEDIUM. Apache 2.0 license. Python backend compatible with our stack. But the Jinja-based UI would need replacement with React, and the document-centric model needs adaptation for agile workflows.

---

#### 3. MetaGPT
- **URL:** https://github.com/FoundationAgents/MetaGPT
- **Platform:** GitHub
- **Stars:** 64,100 | **License:** MIT
- **Tech Stack:** Python (97.5%), requires Node.js/pnpm
- **Last Active:** Active (2026)
- **What It Does:** Multi-agent framework simulating a software company. Takes one-line requirement, outputs PRDs with user stories, competitive analysis, requirements, data structures, APIs, docs. Product Manager agent generates PRD with goals, user stories, competitive analysis.
- **Web UI:** Commercial MGX (mgx.dev). Open-source HuggingFace Space demo.
- **Backlog Import:** NO -- greenfield generation only from one-line prompts.
- **Hierarchy:** Generates PRDs with product goals > user stories > competitive analysis > requirements.
- **Fit Score:** 30% -- Excellent AI engine for requirements generation. Missing: iterative refinement of existing backlogs, Plane integration, non-technical-user-friendly UI, guided wizard UX.
- **Fork Viability:** LOW for full fork (massive codebase). MEDIUM for extracting the PRD/user-story generation pipeline and wrapping it.

---

#### 4. assistant-ui (Component Library)
- **URL:** https://github.com/assistant-ui/assistant-ui
- **Platform:** GitHub
- **Stars:** 8,500 | **License:** MIT
- **Tech Stack:** TypeScript (76%), React, shadcn/ui-inspired composable primitives
- **Last Active:** November 2025
- **What It Does:** Production-grade AI chat interface components. Streaming, auto-scrolling, accessibility. Tool call rendering and human approval workflows. Markdown rendering, code highlighting, voice input.
- **Fit Score:** N/A (component library, not application) -- EXCELLENT as building blocks for a custom requirements gathering tool. Tool call rendering and human approval map perfectly to interactive requirements decomposition.
- **Fork Viability:** EXCELLENT as a dependency. MIT license. React + shadcn/ui pattern matches our stack perfectly.

---

#### 5. CopilotKit (Framework)
- **URL:** https://github.com/CopilotKit/CopilotKit
- **Platform:** GitHub
- **Stars:** 28,700 | **License:** MIT
- **Tech Stack:** TypeScript, React, Next.js
- **Last Active:** January 2026
- **What It Does:** In-app AI copilot framework. Chat UI with message streaming and tool calls. Generative UI (agents generate UI components dynamically). Human-in-the-loop workflows. Shared state between agent and application.
- **Fit Score:** N/A (framework) -- VERY GOOD for building requirements gathering. Generative UI concept is uniquely powerful: AI could dynamically generate form fields, priority pickers, story templates during conversation.
- **Fork Viability:** HIGH as a dependency. MIT license. React/TypeScript stack matches.

---

#### 6. Typebot (Pattern/Inspiration)
- **URL:** https://github.com/baptisteArno/typebot.io
- **Platform:** GitHub
- **Stars:** 9,700 | **License:** Functional Source License (NOT fully open -- Fair Source)
- **Tech Stack:** TypeScript (68%), Next.js, TailwindCSS, Prisma
- **Last Active:** January 2026 (v3.15.2)
- **What It Does:** Visual drag-and-drop chatbot builder. 45+ building blocks. Conditional branching, scripting, A/B testing. Conversational form paradigm. Non-technical user friendly.
- **Fit Score:** 15% as-is (wrong domain), but the UX PATTERN is exactly right for requirements gathering. The conversational flow builder concept is what we need.
- **Fork Viability:** LOW (license is Fair Source, restricts commercial use). USE AS INSPIRATION ONLY.

---

#### 7. CreateMVP
- **URL:** https://github.com/rohitg00/CreateMVP
- **Platform:** GitHub
- **Stars:** 634 | **License:** Apache 2.0
- **Tech Stack:** React + Vite + Tailwind (frontend), Express.js + Node.js (backend), SQLite + Drizzle ORM, multi-LLM
- **Last Active:** 2025
- **What It Does:** AI-powered MVP plan generation. Takes requirements brief or PDF upload. Outputs technical spec, architecture, user-flow diagrams, task breakdown, PRD. Multi-model chat console.
- **Backlog Import:** PDF upload of existing requirements.
- **Fit Score:** 30% -- Right idea (natural language to structured output). Missing: iterative refinement, hierarchical decomposition to Plane format, existing backlog import beyond PDF.
- **Fork Viability:** MODERATE. Apache 2.0. React/Vite/Tailwind close to our stack. Express backend needs replacement with FastAPI.

---

### TIER 2: Relevant but Significant Gaps

---

#### 8. Taiga
- **URL:** https://github.com/kaleidos-ventures/taiga
- **Platform:** GitHub
- **Stars:** ~4,000+ | **License:** AGPL-3.0
- **Tech Stack:** AngularJS + CoffeeScript (frontend), Django + Python (backend), Docker
- **Last Active:** Active
- **Backlog Import:** YES -- from Trello, Asana, GitHub, Jira.
- **Hierarchy:** Epics > User Stories > Tasks, Sprint/Kanban views.
- **Fit Score:** 30% -- Strong backlog management with import. Missing: requirements gathering/discovery workflow, AI, Plane integration. Legacy frontend (AngularJS/CoffeeScript).
- **Fork Viability:** LOW. AGPL license. Legacy tech stack. Heavy adaptation needed.

---

#### 9. OpenProject
- **URL:** https://github.com/opf/openproject
- **Platform:** GitHub
- **Stars:** ~10,000+ | **License:** GPL-3.0
- **Tech Stack:** Ruby on Rails (backend), Angular (frontend), PostgreSQL
- **Last Active:** Active
- **Backlog Import:** YES -- work package import/export.
- **Hierarchy:** Configurable work package types with relationships.
- **Fit Score:** 25% -- Enterprise PM. Requirements tracing through work packages. Missing: requirements discovery workflow, AI, Plane integration. Very heavy (8GB+ RAM recommended).
- **Fork Viability:** LOW. GPL. Ruby/Angular stack. Enterprise-weight.

---

#### 10. Tuleap
- **URL:** https://github.com/Enalean/tuleap
- **Platform:** GitHub
- **Stars:** ~1,000+ | **License:** GPL-2.0
- **Tech Stack:** PHP, Git integration, Docker deployment
- **Last Active:** Active
- **What It Does:** Full ALM suite: requirements management, release planning, task assignment, progress monitoring, test management, traceability.
- **Fit Score:** 20% -- Enterprise ALM. Has requirements management but the entire tool is monolithic PHP. Not suitable for lightweight forking.
- **Fork Viability:** VERY LOW. PHP. Monolithic. GPL-2.0.

---

#### 11. Worklenz
- **URL:** https://github.com/Worklenz/worklenz
- **Platform:** GitHub
- **Stars:** 2,900 | **License:** AGPL-3.0
- **Tech Stack:** React + Ant Design (frontend), TypeScript/Express.js (backend), PostgreSQL, MinIO
- **Last Active:** Active
- **Backlog Import:** Not documented.
- **Hierarchy:** Tasks with subtasks. No formal epic/story hierarchy documented.
- **Fit Score:** 20% -- Modern general PM tool. Not requirements focused. AGPL.

---

#### 12. Fider
- **URL:** https://github.com/getfider/fider
- **Platform:** GitHub
- **Stars:** 4,100 | **License:** AGPL-3.0
- **Tech Stack:** Go (64%), TypeScript (29%), PostgreSQL
- **What It Does:** Collect and prioritize user feedback. Vote on feature requests.
- **Backlog Import:** No.
- **Fit Score:** 15% -- Different purpose. User-facing feedback, not PM-facing requirements decomposition.

---

#### 13. ClearFlask
- **URL:** https://clearflask.com/ | https://github.com/clearflask/clearflask
- **Platform:** GitHub
- **Stars:** ~500 | **License:** AGPL-3.0
- **Tech Stack:** Java (backend), React (frontend), Docker
- **What It Does:** Product feedback, public roadmap, changelog. Community voting.
- **Fit Score:** 15% -- Feedback collection, not requirements gathering.

---

#### 14. Astuto
- **URL:** https://github.com/astuto/astuto
- **Platform:** GitHub
- **Stars:** ~2,000+ | **License:** GPL-3.0
- **Tech Stack:** Ruby on Rails, PostgreSQL
- **What It Does:** Self-hosted customer feedback tool. Feature requests, voting, webhooks.
- **Fit Score:** 10% -- Simple feedback tool. Rails stack.

---

#### 15. LogChimp
- **URL:** https://github.com/logchimp/logchimp
- **Platform:** GitHub
- **License:** Open source
- **Tech Stack:** Node.js + Vue + PostgreSQL
- **What It Does:** Feature request tracking. Feedback collection, roadmaps, voting.
- **Fit Score:** 10% -- Feedback/roadmap tool. Vue stack does not match.

---

#### 16. Huly
- **URL:** https://github.com/hcengineering/platform
- **Platform:** GitHub
- **Stars:** 24,400 | **License:** EPL-2.0
- **Tech Stack:** TypeScript, JavaScript, Svelte, MongoDB, Elasticsearch
- **What It Does:** All-in-one PM (issues, chat, docs, virtual office). GitHub two-way sync.
- **Fit Score:** 15% -- Full PM suite. Too heavy, wrong tech stack, EPL license.

---

#### 17. Re:Backlogs
- **URL:** https://github.com/kaishuu0123/rebacklogs
- **Platform:** GitHub
- **Stars:** 181 | **License:** MIT
- **Tech Stack:** Ruby (42%), Vue (26%), Docker
- **What It Does:** Simple backlog management. Stories and tasks within sprints. Kanban board.
- **Backlog Import:** Not documented.
- **Fit Score:** 20% -- Right concept (backlog tool) but too simple, Ruby/Vue stack, no AI.

---

### TIER 3: Traditional Requirements Management (Document-Centric)

---

#### 18. Doorstop
- **URL:** https://github.com/doorstop-dev/doorstop
- **Platform:** GitHub
- **Stars:** 581 | **License:** LGPL-3.0
- **Tech Stack:** Python (96%)
- **Web UI:** NO (CLI only; Doorhole is separate graphical editor; Doorframe is commercial SaaS)
- **What It Does:** Requirements as YAML files in git. Hierarchical document tree. Traceability validation. Multi-format publishing.
- **Fit Score:** 10% -- CLI tool. No web UI. Good for traceability but wrong paradigm.

---

#### 19. rmToo
- **URL:** https://github.com/florath/rmtoo
- **Platform:** GitHub
- **License:** GPL-3.0
- **Tech Stack:** Python, CLI
- **Web UI:** NO
- **What It Does:** Text-file requirements processed into HTML, LaTeX/PDF, dependency graphs.
- **Fit Score:** 5% -- CLI requirements tool for developers. No web UI.

---

#### 20. OSRMT
- **URL:** https://github.com/osrmt/osrmt | https://sourceforge.net/projects/osrmt/
- **Platform:** GitHub + SourceForge
- **License:** GPL
- **Tech Stack:** Java, Swing/web client
- **Web UI:** YES (Java web app)
- **Last Updated:** 2019
- **Fit Score:** 10% -- Ancient Java tool. Full SDLC traceability but completely outdated.

---

#### 21. FRET (NASA)
- **URL:** https://github.com/NASA-SW-VnV/fret
- **Platform:** GitHub
- **Stars:** 401 | **License:** Apache 2.0
- **Tech Stack:** JavaScript (83%), Electron desktop app
- **Web UI:** NO (Electron desktop only)
- **What It Does:** Formal requirements in restricted English. Natural language to formal logic. Test generation. Consistency checking.
- **Fit Score:** 5% -- Safety-critical formal requirements. Wrong domain entirely.

---

#### 22. Ephemeris
- **URL:** https://github.com/shuart/ephemeris
- **Platform:** GitHub
- **Stars:** 75 | **License:** MIT
- **Tech Stack:** JavaScript (96%), CSS, HTML
- **Web UI:** YES (web demo at ephemeris.cloud/demo)
- **Last Updated:** April 2020 (stale)
- **Backlog Import:** YES -- Archimate files and CSV import via custom scripts.
- **Hierarchy:** Stakeholders > Requirements > Functions > Products with linking.
- **Fit Score:** 20% -- Interesting concept with stakeholder-requirement-function-product hierarchy and import. But stale (2020), tiny community, no AI. MIT license is good.

---

#### 23. Requirement Heap
- **URL:** https://sourceforge.net/projects/reqheap/
- **Platform:** SourceForge
- **Tech Stack:** Java web application
- **Last Updated:** Very old (0.8.0 beta)
- **What It Does:** Web-based requirement management with rich text, versioning, use cases, interviews, test cases, releases.
- **Fit Score:** 5% -- Abandoned Java web app.

---

#### 24. Capella (Eclipse MBSE)
- **URL:** https://github.com/eclipse-capella/capella | https://mbse-capella.org/
- **Platform:** GitHub (Eclipse Foundation)
- **License:** EPL-2.0
- **Tech Stack:** Java, Eclipse RCP desktop application
- **Web UI:** NO (Eclipse desktop only; Team for Capella adds collaboration)
- **What It Does:** Model-based systems engineering. Graphical system/hardware/software architecture modeling. Requirements via OSLC integration with Doors/Polarion.
- **Fit Score:** 0% -- Enterprise MBSE tool. Desktop only. Wrong domain.

---

#### 25. OpenReq (EU H2020 Project)
- **URL:** https://openreq.eu/ | https://github.com/OpenReqEU
- **Platform:** GitHub
- **License:** Various open source
- **Tech Stack:** Microservices architecture, various languages
- **What It Does:** EU research project for intelligent requirements recommendation. AI/ML for requirements prioritization. Plugins for Eclipse, Jira, GitHub Issues. OpenReq Live platform.
- **Fit Score:** 15% -- Interesting AI/ML components for requirements. But research-grade code, EU project funding ended, not production-ready.

---

### TIER 4: AI Tools for Story/PRD Generation

---

#### 26. StoryMachine
- **URL:** https://github.com/nilenso/storymachine
- **Platform:** GitHub
- **Stars:** 47 | **License:** Not specified
- **Tech Stack:** Python 3.13+, OpenAI API, pydantic-settings
- **Web UI:** NO (CLI only)
- **What It Does:** Generates user stories from PRD + tech spec documents. AI-powered context enrichment. Structured output with acceptance criteria.
- **Backlog Import:** NO -- generates from PRD documents, not existing backlogs.
- **Fit Score:** 20% -- Right output format (stories with AC). Wrong UX (CLI). No import.

---

#### 27. StoryCraft
- **URL:** https://github.com/kapadias/story-craft
- **Platform:** GitHub
- **Stars:** 15 | **License:** MIT
- **Tech Stack:** Python, Streamlit, OpenAI GPT-4
- **Web UI:** YES (Streamlit)
- **What It Does:** Generate user stories from persona + scope prompts. Interactive chat-based format.
- **Hierarchy:** NO -- individual stories only, no hierarchical generation.
- **Fit Score:** 15% -- Right concept, wrong scale. No hierarchy, no import, Streamlit UI.

---

#### 28. Agentic PRD Generation
- **URL:** https://github.com/SeeknnDestroy/agentic-prd-generation
- **Platform:** GitHub
- **Stars:** 10 | **License:** MIT
- **Tech Stack:** Python, FastAPI backend, Streamlit frontend, OpenAI, CrewAI, LangGraph
- **What It Does:** Multi-step agentic workflow: outline > draft > critique > revision. Compares vanilla LLM vs agent frameworks. SSE streaming.
- **Fit Score:** 20% -- FastAPI backend matches our stack. Agentic workflow pattern (outline/draft/critique/revision) maps to requirements gathering. But Streamlit UI and alpha quality.

---

#### 29. GTPlanner
- **URL:** https://github.com/OpenSQZ/GTPlanner
- **Platform:** GitHub
- **Stars:** 141 | **License:** MIT
- **Tech Stack:** Python 3.10+, FastAPI, PocketFlow, Langfuse
- **What It Does:** Natural language to structured technical documentation. FastAPI web UI. MCP support.
- **Fit Score:** 15% -- FastAPI match. But focused on AI coding assistant PRDs, not general requirements.

---

### TIER 5: Infrastructure/Framework Tools (Not Applications)

---

#### 30. Dify
- **URL:** https://github.com/langgenius/dify
- **Platform:** GitHub
- **Stars:** 129,000 | **License:** Dify Open Source License (Apache 2.0 based + additional conditions)
- **Tech Stack:** Python/Flask (backend), TypeScript/React/Next.js (frontend), Docker
- **What It Does:** Visual AI workflow builder. 100+ LLM integrations. RAG pipeline. Agent capabilities. Chat interface.
- **Fit Score:** N/A (platform, not application) -- Could be used to BUILD a requirements gathering workflow. Most powerful option but adds infrastructure.

---

#### 31. Flowise
- **URL:** https://github.com/FlowiseAI/Flowise
- **Platform:** GitHub
- **Stars:** ~49,000 | **License:** Apache 2.0
- **Tech Stack:** TypeScript, Node.js, LangChain
- **What It Does:** Visual AI agent workflow builder with drag-and-drop.
- **Fit Score:** N/A (platform) -- Could build requirements workflows. Lighter than Dify.

---

#### 32. Langflow
- **URL:** https://github.com/langflow-ai/langflow
- **Platform:** GitHub
- **Stars:** 145,000 | **License:** MIT
- **Tech Stack:** Python (55%), TypeScript (25%), React Flow
- **What It Does:** Visual workflow builder for AI applications.
- **Fit Score:** N/A (platform) -- General-purpose AI workflow platform.

---

#### 33. Plane Python SDK
- **URL:** https://pypi.org/project/plane-sdk/
- **Platform:** PyPI + GitHub
- **Tech Stack:** Python 3.10+, Pydantic models
- **What It Does:** Full CRUD SDK for Plane API. Resources: work_items, cycles, modules, labels, states, work_item_types, epics, initiatives, pages, customers, teamspaces.
- **Fit Score:** N/A -- This is the OUTPUT mechanism. Any tool we build should use this.

---

## Plane Ecosystem Analysis

### Plane's Built-in AI ("Plane AI")
- Turns conversations into structured work items with auto-filled descriptions, labels, structure
- Context-aware sidecar (knows what you are viewing)
- AI-assist for docs/wikis
- MCP Server for external AI agent interaction
- Agents handle work when mentioned/assigned
- **NO dedicated requirements gathering/discovery workflow**
- **NO conversational wizard for non-technical users**
- **NO backlog refinement/decomposition assistant**

### Plane Marketplace (Feb 2026)
- **Importers:** Jira, Jira Server, Asana, ClickUp, Notion, Confluence, Linear
- **Integrations:** GitHub, GitHub Enterprise, GitLab, GitLab Enterprise, Slack, Sentry, Draw.io, Raycast
- **AI Agents:** Claude, VS Code MCP
- **NO requirements gathering extensions**
- **NO product discovery tools**
- **NO backlog refinement assistants**

### Plane API Capabilities
- 180+ endpoints
- Full CRUD: projects, work items, cycles, modules, labels, states, sub-work-items
- Work item types and custom properties
- Epics and initiatives
- Webhooks for real-time events
- OAuth 2.0 for custom app registration
- Official Python SDK (plane-sdk v0.2.0) with Pydantic models

### Plane MCP Server
- Official: https://github.com/makeplane/plane-mcp-server
- Enables AI agents to interact with Plane via MCP
- Supports OAuth and PAT authentication
- Could power AI-driven requirements gathering that outputs to Plane

---

## Gap Analysis: What Does Not Exist

| Requirement | Status | Closest Tool |
|---|---|---|
| Graphical web UI for non-technical users | Partial | Eververse, Taiga, Worklenz |
| Conversational/wizard-based requirements gathering | DOES NOT EXIST | Typebot pattern (not requirements-specific) |
| Hierarchical output: Epic > Feature > Story > Task | Partial | Taiga (Epic > Story > Task), OpenProject |
| Import existing backlogs (Plane, Jira, CSV, Markdown) | Partial | Taiga (Jira/Trello), StrictDoc (ReqIF/CSV) |
| Refine/split/reorganize existing work items | DOES NOT EXIST | No tool does this |
| AI-powered requirements decomposition | DOES NOT EXIST | MetaGPT (greenfield only), StoryMachine (CLI) |
| AI-powered iterative refinement of existing items | DOES NOT EXIST | None |
| Push to MQ Planning via API | DOES NOT EXIST | MQ DevEngine is the only known MQ Planning integration builder |
| Permissive license (MIT/Apache) | Available | Eververse (MIT), StrictDoc (Apache 2.0), CopilotKit (MIT) |
| Modern tech stack (React/Next.js + Python) | Available | Eververse, CopilotKit, assistant-ui |

**Key finding: The combination of "conversational AI gathering + existing backlog import + hierarchical decomposition + Plane output" does not exist anywhere in the open-source world.**

---

## Recommended Build Approaches (Ranked)

### APPROACH A: assistant-ui + Custom FastAPI Backend (RECOMMENDED for MVP)
**Effort:** Medium (3-5 day sprint for MVP)

Build a custom requirements gathering application using assistant-ui React components + FastAPI backend + Plane Python SDK.

```
User <-> assistant-ui Chat UI <-> FastAPI /api/requirements/* <-> Claude/OpenAI API
                                         |
                                         v
                                  Structured JSON output
                                         |
                                   +-----+-----+
                                   |           |
                                   v           v
                            plane-sdk     CSV/Markdown
                          (push to Plane)   (export)
```

**Why:** Stack alignment (React + TypeScript + shadcn/ui + FastAPI). MIT license. Component library gives full control. Leverages existing Plane sync infrastructure.

---

### APPROACH B: Fork Eververse + Extend (RECOMMENDED for full product)
**Effort:** Medium-High (multi-sprint)

Fork Eververse and add: conversational wizard, backlog import, AI decomposition, Plane SDK integration.

**Why:** MIT license. Next.js/React/shadcn/ui/Supabase. Already has AI integrations, feedback management, roadmapping. Active (Jan 2026).

**Concerns:** Supabase/Vercel dependencies. Smaller community (346 stars).

---

### APPROACH C: CopilotKit + Custom Application
**Effort:** Medium-High (4-6 day sprint)

Use CopilotKit framework for in-app AI copilot with generative UI (AI dynamically generates form fields, story templates, priority pickers during conversation).

**Why:** MIT license. Generative UI is uniquely powerful. Human-in-the-loop built-in. 28.7k stars.

**Concerns:** Heavier framework. May require Next.js.

---

### APPROACH D: Plane Marketplace App
**Effort:** Medium

Build as a Plane Marketplace extension. OAuth app registration, standalone web UI, reads existing Plane backlog via API, conversational AI refines/decomposes, pushes back to Plane.

**Why:** Native Plane integration. Could be published to Plane Marketplace. Clear value proposition.

**Concerns:** Tightly coupled to Plane. Marketplace app constraints unknown.

---

### APPROACH E: StrictDoc Backend + React Frontend
**Effort:** Medium

Use StrictDoc's Python backend for requirements management (import/export, traceability, hierarchy) with a new React frontend and AI layer.

**Why:** Apache 2.0. Mature requirements management. Python backend compatible with our stack. ReqIF/CSV import.

**Concerns:** Document-centric model needs major adaptation for agile. Jinja UI deeply embedded.

---

## Final Recommendation

**For fastest MVP: APPROACH A** (assistant-ui + FastAPI + Plane SDK). Build a standalone tool with:
1. Conversational AI chat interface (assistant-ui components)
2. FastAPI backend with Claude/OpenAI for AI-powered conversation
3. Backlog import from Plane (via plane-sdk), CSV, and Markdown
4. AI decomposes requirements into Epic > Feature > Story > Task hierarchy
5. Refinement workflow: split stories, add acceptance criteria, estimate complexity
6. One-click push to Plane via plane-sdk

**For full product vision: APPROACH B** (Fork Eververse). Gets us a complete product management platform with MIT license and modern stack, that we extend with our unique conversational requirements gathering + Plane integration.

**The tool fills a genuine market gap.** No existing open-source tool combines conversational AI requirements gathering with existing backlog refinement and structured Plane output. This is differentiated and buildable.

---

## Tool Comparison Matrix

| Tool | Stars | License | Stack Match | Web UI | Conversational | Hierarchy | Import | Plane | Fit |
|------|-------|---------|-------------|--------|---------------|-----------|--------|-------|-----|
| Eververse | 346 | MIT | Excellent | Yes | No | Partial | Partial | No | 40% |
| StrictDoc | 248 | Apache 2.0 | Good (Python) | Yes | No | Yes | Yes (ReqIF/CSV) | No | 35% |
| MetaGPT | 64.1k | MIT | Low | CLI/Commercial | CLI | Partial | No | No | 30% |
| CreateMVP | 634 | Apache 2.0 | Good | Yes | Partial | No | PDF only | No | 30% |
| Taiga | ~4k | AGPL | Low | Yes | No | Yes | Yes (Jira etc) | No | 30% |
| assistant-ui | 8.5k | MIT | Excellent | Components | Yes | Via tools | N/A | N/A | N/A |
| CopilotKit | 28.7k | MIT | Good | Framework | Yes | Via gen UI | N/A | N/A | N/A |
| Typebot | 9.7k | Fair Source | Good | Yes | Yes | No | No | No | 15% |
| OpenProject | ~10k | GPL | Low | Yes | No | Yes | Yes | No | 25% |
| Worklenz | 2.9k | AGPL | Good | Yes | No | Partial | No | No | 20% |
| Fider | 4.1k | AGPL | Low (Go) | Yes | No | No | No | No | 15% |
| Ephemeris | 75 | MIT | Low | Yes | No | Yes | Yes (CSV) | No | 20% |
| StoryMachine | 47 | Unspecified | Good (Python) | No | No | No | No | No | 20% |

---

## Sources

### Tools Evaluated
- [Eververse](https://github.com/haydenbleasel/eververse)
- [StrictDoc](https://github.com/strictdoc-project/strictdoc)
- [Featmap](https://github.com/amborle/featmap) (archived)
- [MetaGPT](https://github.com/FoundationAgents/MetaGPT)
- [Typebot](https://github.com/baptisteArno/typebot.io)
- [Taiga](https://github.com/kaleidos-ventures/taiga)
- [OpenProject](https://github.com/opf/openproject)
- [Fider](https://github.com/getfider/fider)
- [ClearFlask](https://clearflask.com/)
- [Worklenz](https://github.com/Worklenz/worklenz)
- [Re:Backlogs](https://github.com/kaishuu0123/rebacklogs)
- [Doorstop](https://github.com/doorstop-dev/doorstop)
- [rmToo](https://github.com/florath/rmtoo)
- [OSRMT](https://github.com/osrmt/osrmt)
- [FRET (NASA)](https://github.com/NASA-SW-VnV/fret)
- [Ephemeris](https://github.com/shuart/ephemeris)
- [OpenReq](https://openreq.eu/)
- [Requirement Heap](https://sourceforge.net/projects/reqheap/)
- [StoryMachine](https://github.com/nilenso/storymachine)
- [StoryCraft](https://github.com/kapadias/story-craft)
- [CreateMVP](https://github.com/rohitg00/CreateMVP)
- [GTPlanner](https://github.com/OpenSQZ/GTPlanner)
- [Agentic PRD Generation](https://github.com/SeeknnDestroy/agentic-prd-generation)
- [assistant-ui](https://github.com/assistant-ui/assistant-ui)
- [CopilotKit](https://github.com/CopilotKit/CopilotKit)
- [Dify](https://github.com/langgenius/dify)
- [Flowise](https://github.com/FlowiseAI/Flowise)
- [Langflow](https://github.com/langflow-ai/langflow)
- [Exothermic](https://github.com/StevenWeathers/exothermic-story-mapping) (archived)
- [Tuleap](https://github.com/Enalean/tuleap)
- [Astuto](https://github.com/astuto/astuto)
- [LogChimp](https://github.com/logchimp/logchimp)
- [Huly](https://github.com/hcengineering/platform)
- [ZenTao](https://www.zentao.pm/)
- [Capella](https://mbse-capella.org/)
- [Botpress](https://github.com/botpress/botpress)
- [HeyForm](https://github.com/heyform/heyform)
- [Formbricks](https://github.com/formbricks/formbricks)

### Plane Ecosystem
- [Plane](https://github.com/makeplane/plane)
- [Plane AI](https://plane.so/ai)
- [Plane Marketplace](https://plane.so/marketplace)
- [Plane MCP Server](https://github.com/makeplane/plane-mcp-server)
- [Plane Python SDK](https://pypi.org/project/plane-sdk/)
- [Plane API Docs](https://developers.plane.so/api-reference/introduction)
- [Plane Developer Docs](https://developers.plane.so)

### Research Directories
- [Open source requirements tools (curated gist)](https://gist.github.com/stanislaw/aa40eb7de9f522ad482e5d239c435ff8)
- [requirementsmanagementtools.com](https://www.requirementsmanagementtools.com/opensource.php)
- [OpenAlternative - ProductBoard alternatives](https://openalternative.co/alternatives/productboard)
- [awesome-product-management](https://github.com/dend/awesome-product-management)
- [GitHub requirements-management topic](https://github.com/topics/requirements-management)
- [Digital Project Manager - Best OS Requirements Tools 2026](https://thedigitalprojectmanager.com/tools/best-open-source-requirements-management-tools/)
- [HN: Open source project management tools](https://news.ycombinator.com/item?id=25217835)
- [HN: Worklenz discussion](https://news.ycombinator.com/item?id=40397743)
- [IBM: MetaGPT PRD automation tutorial](https://www.ibm.com/think/tutorials/multi-agent-prd-ai-automation-metagpt-ollama-deepseek)
- [SourceForge OSRMT](https://sourceforge.net/projects/osrmt/)
- [Product Hunt - Open Source topic](https://www.producthunt.com/topics/open-source)
- [Codeberg.org](https://codeberg.org/)
