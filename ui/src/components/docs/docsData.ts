/**
 * Documentation sections registry.
 *
 * Each section maps to a React component in sections/.
 * Used by DocsPage for sidebar navigation and search.
 */

export interface DocSubsection {
  id: string
  title: string
}

export interface DocSection {
  id: string
  title: string
  subsections: DocSubsection[]
  searchKeywords: string[]
}

/**
 * Registered documentation sections.
 * Add new sections here and create a matching component in sections/.
 */
export const DOCS_SECTIONS: DocSection[] = [
  {
    id: "tdd",
    title: "Test-Driven Development",
    subsections: [
      { id: "tdd-overview", title: "Overview" },
      { id: "tdd-modes", title: "Operating Modes" },
      { id: "tdd-workflow", title: "Red/Green/Refactor Cycle" },
      { id: "tdd-agents", title: "Agent Roles" },
      { id: "tdd-pm-guide", title: "PM Guide" },
    ],
    searchKeywords: [
      "test",
      "tdd",
      "testing",
      "red",
      "green",
      "refactor",
      "vitest",
      "jest",
      "pytest",
      "yolo",
    ],
  },
]
