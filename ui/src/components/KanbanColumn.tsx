import { FeatureCard } from './FeatureCard'
import { Plus, Sparkles, Wand2, ChevronDown, ChevronRight, Circle, Loader2, CheckCircle2 } from 'lucide-react'
import type { Feature, ActiveAgent } from '../lib/types'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

function parseNumericPrefix(name: string): number[] {
  const match = name.match(/^(\d+(?:\.\d+)*)/)
  if (!match) return []
  return match[1].split('.').map(Number)
}

interface KanbanColumnProps {
  title: string
  count: number
  features: Feature[]
  allFeatures?: Feature[]
  activeAgents?: ActiveAgent[]
  color: 'pending' | 'progress' | 'done'
  onFeatureClick: (feature: Feature) => void
  onAddFeature?: () => void
  onExpandProject?: () => void
  showExpandButton?: boolean
  onCreateSpec?: () => void
  showCreateSpec?: boolean
  onShowDialogue?: (featureId: number) => void
  featureHasLogs?: (featureId: number) => boolean
  accordionMode?: boolean
  expandedParent?: string | null
  onToggleParent?: (prefix: string | null) => void
  projectName?: string
}

const colorMap = {
  pending: 'border-t-4 border-t-muted',
  progress: 'border-t-4 border-t-primary',
  done: 'border-t-4 border-t-primary',
}

export function KanbanColumn({
  title,
  count,
  features,
  allFeatures = [],
  activeAgents = [],
  color,
  onFeatureClick,
  onAddFeature,
  onExpandProject,
  showExpandButton,
  onCreateSpec,
  showCreateSpec,
  onShowDialogue,
  featureHasLogs,
  accordionMode = false,
  expandedParent = null,
  onToggleParent,
  projectName,
}: KanbanColumnProps) {
  // Create a map of feature ID to active agent for quick lookup
  const agentByFeatureId = new Map<number, ActiveAgent>()
  for (const agent of activeAgents) {
    const ids = agent.featureIds || [agent.featureId]
    for (const fid of ids) {
      agentByFeatureId.set(fid, agent)
    }
  }

  // Accordion logic: compute sub-item counts from allFeatures (cross-column aware)
  const subItemCounts = new Map<string, number>()
  const subItemDoneCounts = new Map<string, number>()
  if (accordionMode) {
    for (const f of allFeatures) {
      const p = parseNumericPrefix(f.name)
      if (p.length >= 3) {
        const parentKey = p.slice(0, 2).join('.')
        subItemCounts.set(parentKey, (subItemCounts.get(parentKey) ?? 0) + 1)
        if (f.passes) {
          subItemDoneCounts.set(parentKey, (subItemDoneCounts.get(parentKey) ?? 0) + 1)
        }
      }
    }
  }

  // Keys of parents that exist in THIS column (for accordion grouping)
  const parentKeysInThisColumn = new Set<string>()
  if (accordionMode) {
    for (const f of features) {
      const p = parseNumericPrefix(f.name)
      if (p.length === 2) parentKeysInThisColumn.add(p.join('.'))
    }
  }

  const visibleFeatures = accordionMode
    ? features.filter(f => {
        const p = parseNumericPrefix(f.name)
        if (p.length < 3) return true  // top-level always visible
        const parentKey = p.slice(0, 2).join('.')
        // If parent is in this column: only show when expanded
        if (parentKeysInThisColumn.has(parentKey)) return parentKey === expandedParent
        // Parent is in a different column: show at top level (not hidden)
        return true
      })
    : features

  return (
    <Card className={`overflow-hidden ${colorMap[color]} py-0`}>
      {/* Header */}
      <CardHeader className="px-4 py-3 border-b flex-row items-center justify-between space-y-0">
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          {title}
          <Badge variant="secondary">{count}</Badge>
        </CardTitle>
        {(onAddFeature || onExpandProject) && (
          <div className="flex items-center gap-2">
            {onAddFeature && (
              <Button
                onClick={onAddFeature}
                size="icon-sm"
                title="Add new feature (N)"
              >
                <Plus size={16} />
              </Button>
            )}
            {onExpandProject && showExpandButton && (
              <Button
                onClick={onExpandProject}
                size="icon-sm"
                variant="secondary"
                title="Expand project with AI (E)"
              >
                <Sparkles size={16} />
              </Button>
            )}
          </div>
        )}
      </CardHeader>

      {/* Cards */}
      <CardContent className="p-0">
        <div className="h-[600px] overflow-y-auto">
          <div className="p-4 space-y-3">
            {features.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                {showCreateSpec && onCreateSpec ? (
                  <div className="space-y-4">
                    <p>No spec created yet</p>
                    <Button onClick={onCreateSpec}>
                      <Wand2 size={18} />
                      Create Spec with AI
                    </Button>
                  </div>
                ) : (
                  'No features'
                )}
              </div>
            ) : (
              visibleFeatures.map((feature, index) => {
                const prefix = parseNumericPrefix(feature.name)
                const isSubItem = accordionMode && prefix.length >= 3 && parentKeysInThisColumn.has(prefix.slice(0, 2).join('.'))
                const featureTasks = feature.tasks ?? []
                const dbSubCount = subItemCounts.get(prefix.join('.')) ?? 0
                // If Feature DB sub-records exist, JSON tasks are superseded — don't double-count
                const hasDbSubs = dbSubCount > 0
                const isParent = accordionMode && prefix.length === 2 &&
                  (dbSubCount > 0 || featureTasks.length > 0)
                const parentKey = prefix.length === 2 ? prefix.join('.') : null
                const isExpanded = parentKey !== null && expandedParent === parentKey
                const subCount = isParent
                  ? dbSubCount + (hasDbSubs ? 0 : featureTasks.length)
                  : 0
                const subDoneCount = isParent
                  ? (subItemDoneCounts.get(prefix.join('.')) ?? 0) + (hasDbSubs ? 0 : featureTasks.filter(t => t.done).length)
                  : 0

                // Cross-column sub-items: children of this parent that live in other columns
                const crossColumnSubItems = isParent && isExpanded
                  ? allFeatures
                      .filter(f => {
                        const fp = parseNumericPrefix(f.name)
                        return fp.length >= 3 && fp.slice(0, 2).join('.') === parentKey && !features.includes(f)
                      })
                      .sort((a, b) => {
                        const pa = parseNumericPrefix(a.name)
                        const pb = parseNumericPrefix(b.name)
                        const len = Math.max(pa.length, pb.length)
                        for (let i = 0; i < len; i++) {
                          const va = pa[i] ?? -1, vb = pb[i] ?? -1
                          if (va !== vb) return va - vb
                        }
                        return 0
                      })
                  : []

                return (
                  <div
                    key={feature.id}
                    className={`animate-slide-in ${isSubItem ? 'ml-3 border-r-4 border-orange-400 rounded-r-md' : ''}`}
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    {isParent && (
                      <button
                        className="w-full flex items-center justify-end gap-1 pb-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                        onClick={() => onToggleParent?.(isExpanded ? null : parentKey)}
                      >
                        {isExpanded
                          ? <><ChevronDown size={13} /><span>{subCount} sub-items</span></>
                          : <><ChevronRight size={13} /><span>{subCount} sub-items</span></>
                        }
                      </button>
                    )}
                    <FeatureCard
                      feature={feature}
                      onClick={() => {
                        if (isParent && onToggleParent) {
                          onToggleParent(isExpanded ? null : parentKey!)
                        } else {
                          onFeatureClick(feature)
                        }
                      }}
                      isInProgress={color === 'progress'}
                      allFeatures={allFeatures}
                      activeAgent={agentByFeatureId.get(feature.id)}
                      hasDialogueLogs={featureHasLogs?.(feature.id) ?? false}
                      onShowDialogue={onShowDialogue}
                      subItemCount={subCount > 0 ? subCount : undefined}
                      subItemsDone={subCount > 0 ? subDoneCount : undefined}
                      projectName={projectName}
                    />
                    {/* Cross-column sub-items: Feature DB children in other columns */}
                    {crossColumnSubItems.length > 0 && (
                      <div className="ml-3 mt-1 space-y-1 border-l-2 border-orange-300 pl-2">
                        {crossColumnSubItems.map(sub => {
                          const isDone = sub.passes
                          const isInProg = sub.in_progress
                          return (
                            <button
                              key={sub.id}
                              onClick={() => onFeatureClick(sub)}
                              className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-left hover:bg-muted/60 transition-colors group"
                            >
                              {isDone
                                ? <CheckCircle2 size={13} className="text-primary shrink-0" />
                                : isInProg
                                  ? <Loader2 size={13} className="animate-spin text-primary shrink-0" />
                                  : <Circle size={13} className="text-muted-foreground shrink-0" />
                              }
                              <span className="text-xs text-muted-foreground group-hover:text-foreground truncate flex-1">
                                {sub.name}
                              </span>
                            </button>
                          )
                        })}
                      </div>
                    )}
                    {/* Task sub-items from feature.tasks — only when no Feature DB sub-records exist */}
                    {isParent && isExpanded && featureTasks.length > 0 && !hasDbSubs && (
                      <div className="ml-3 mt-1 space-y-1 border-l-2 border-orange-300 pl-2">
                        {featureTasks.map((task, taskIdx) => {
                          const taskNum = `${prefix.slice(0, 2).join('.')}.${taskIdx + 1}`
                          return (
                            <div
                              key={task.id}
                              className="flex items-center gap-2 px-2 py-1.5 rounded bg-muted/20"
                            >
                              {task.done
                                ? <CheckCircle2 size={13} className="text-primary shrink-0" />
                                : <Circle size={13} className="text-muted-foreground shrink-0" />
                              }
                              <span className="text-xs font-mono text-muted-foreground shrink-0">{taskNum}</span>
                              <span className="text-xs text-muted-foreground truncate flex-1">{task.name}</span>
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )
              })
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
