import { useState } from 'react'
import { KanbanColumn } from './KanbanColumn'
import type { Feature, FeatureListResponse, ActiveAgent } from '../lib/types'
import { Card, CardContent } from '@/components/ui/card'

/**
 * Extract the leading numeric prefix from a feature name.
 * "2.1.1 Google OAuth..." → [2, 1, 1]
 * "Story 3.2: Foo"       → [3, 2]
 * "Some feature"         → []
 */
function parseNumericPrefix(name: string): number[] {
  const match = name.match(/^(\d+(?:\.\d+)*)/)
  if (!match) return []
  return match[1].split('.').map(Number)
}

/**
 * Compare two numeric prefix arrays lexicographically.
 * [2, 1] < [2, 1, 1] < [2, 1, 2] < [2, 2] < [3]
 */
function comparePrefix(a: number[], b: number[]): number {
  const len = Math.max(a.length, b.length)
  for (let i = 0; i < len; i++) {
    const va = a[i] ?? -1   // parent sorts before children (shorter prefix wins)
    const vb = b[i] ?? -1
    if (va !== vb) return va - vb
  }
  return 0
}

/**
 * Sort features into hierarchical order:
 * parent first, then its children in numeric order, then next parent, etc.
 * Features without a numeric prefix are sorted by priority at the end.
 */
function sortHierarchical(features: Feature[]): Feature[] {
  return [...features].sort((a, b) => {
    const pa = parseNumericPrefix(a.name)
    const pb = parseNumericPrefix(b.name)
    if (pa.length === 0 && pb.length === 0) return a.priority - b.priority
    if (pa.length === 0) return 1
    if (pb.length === 0) return -1
    const cmp = comparePrefix(pa, pb)
    if (cmp !== 0) return cmp
    return a.priority - b.priority
  })
}

interface KanbanBoardProps {
  features: FeatureListResponse | undefined
  onFeatureClick: (feature: Feature) => void
  onAddFeature?: () => void
  onExpandProject?: () => void
  activeAgents?: ActiveAgent[]
  onCreateSpec?: () => void
  hasSpec?: boolean
  onShowDialogue?: (featureId: number) => void
  featureHasLogs?: (featureId: number) => boolean
  projectName?: string
}

export function KanbanBoard({ features, onFeatureClick, onAddFeature, onExpandProject, activeAgents = [], onCreateSpec, hasSpec = true, onShowDialogue, featureHasLogs, projectName }: KanbanBoardProps) {
  const [expandedPending, setExpandedPending] = useState<string | null>(null)
  const [expandedDone, setExpandedDone] = useState<string | null>(null)

  const hasFeatures = features && (features.pending.length + features.in_progress.length + features.done.length) > 0

  // Combine all features for dependency status calculation
  const allFeatures = features
    ? [...features.pending, ...features.in_progress, ...features.done]
    : []

  if (!features) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {['Pending', 'In Progress', 'Done'].map(title => (
          <Card key={title} className="py-4">
            <CardContent className="p-4">
              <div className="h-8 bg-muted animate-pulse rounded mb-4" />
              <div className="space-y-3">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-24 bg-muted animate-pulse rounded" />
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <KanbanColumn
        title="Pending"
        count={features.pending.length}
        features={sortHierarchical(features.pending)}
        allFeatures={allFeatures}
        activeAgents={activeAgents}
        color="pending"
        onFeatureClick={onFeatureClick}
        onAddFeature={onAddFeature}
        onExpandProject={onExpandProject}
        showExpandButton={hasFeatures}
        onCreateSpec={onCreateSpec}
        showCreateSpec={!hasSpec && !hasFeatures}
        onShowDialogue={onShowDialogue}
        featureHasLogs={featureHasLogs}
        accordionMode={true}
        expandedParent={expandedPending}
        onToggleParent={setExpandedPending}
        projectName={projectName}
      />
      <KanbanColumn
        title="In Progress"
        count={features.in_progress.length}
        features={features.in_progress}
        allFeatures={allFeatures}
        activeAgents={activeAgents}
        color="progress"
        onFeatureClick={onFeatureClick}
        onShowDialogue={onShowDialogue}
        featureHasLogs={featureHasLogs}
      />
      <KanbanColumn
        title="Done"
        count={features.done.length}
        features={sortHierarchical(features.done)}
        allFeatures={allFeatures}
        activeAgents={activeAgents}
        color="done"
        onFeatureClick={onFeatureClick}
        onShowDialogue={onShowDialogue}
        featureHasLogs={featureHasLogs}
        accordionMode={true}
        expandedParent={expandedDone}
        onToggleParent={setExpandedDone}
      />
    </div>
  )
}
