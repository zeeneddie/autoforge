import { FeatureCard } from './FeatureCard'
import { Plus, Sparkles, Wand2, Layers } from 'lucide-react'
import type { Feature, ActiveAgent } from '../lib/types'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

function parseNumericPrefix(name: string): number[] {
  const match = name.match(/^(?:Story\s+)?(\d+(?:\.\d+)*)/)
  if (!match) return []
  return match[1].split('.').map(Number)
}

// ── Story group header ────────────────────────────────────────────────────────

interface StoryGroupHeaderProps {
  parentName: string
  totalCount: number
  doneCount: number
  onClick: () => void
}

function StoryGroupHeader({ parentName, totalCount, doneCount, onClick }: StoryGroupHeaderProps) {
  const pct = totalCount > 0 ? (doneCount / totalCount) * 100 : 0
  const allDone = doneCount === totalCount && totalCount > 0

  return (
    <button
      onClick={onClick}
      className="w-full text-left px-3 py-2 rounded-lg bg-muted/40 hover:bg-muted/60 transition-colors border border-border/50"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <Layers size={13} className={allDone ? 'text-primary shrink-0' : 'text-muted-foreground shrink-0'} />
          <span className="text-xs font-semibold truncate text-foreground">{parentName}</span>
        </div>
        <Badge variant="outline" className={`text-[10px] px-1.5 py-0 shrink-0 font-mono ${allDone ? 'border-primary text-primary' : ''}`}>
          {doneCount}/{totalCount}
        </Badge>
      </div>
      <div className="mt-1.5 h-1 bg-muted rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${allDone ? 'bg-primary' : 'bg-primary/60'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </button>
  )
}

// ── Types ─────────────────────────────────────────────────────────────────────

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
  projectName?: string
}

type RenderItem =
  | { type: 'storyGroup'; parentKey: string; parentName: string }
  | { type: 'subItem'; feature: Feature; parentKey: string }
  | { type: 'card'; feature: Feature }

const colorMap = {
  pending: 'border-t-4 border-t-muted',
  progress: 'border-t-4 border-t-primary',
  done: 'border-t-4 border-t-primary',
}

// ── Component ─────────────────────────────────────────────────────────────────

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
  projectName,
}: KanbanColumnProps) {
  // Agent lookup map
  const agentByFeatureId = new Map<number, ActiveAgent>()
  for (const agent of activeAgents) {
    const ids = agent.featureIds || [agent.featureId]
    for (const fid of ids) agentByFeatureId.set(fid, agent)
  }

  // Global sub-item counts across ALL columns (from allFeatures)
  const subItemCounts = new Map<string, number>()
  const subItemDoneCounts = new Map<string, number>()
  for (const f of allFeatures) {
    const p = parseNumericPrefix(f.name)
    if (p.length >= 3) {
      const parentKey = p.slice(0, 2).join('.')
      subItemCounts.set(parentKey, (subItemCounts.get(parentKey) ?? 0) + 1)
      if (f.passes) subItemDoneCounts.set(parentKey, (subItemDoneCounts.get(parentKey) ?? 0) + 1)
    }
  }

  // Cache: parentKey → parent Feature (from allFeatures)
  const parentFeatureByKey = new Map<string, Feature>()
  for (const f of allFeatures) {
    const p = parseNumericPrefix(f.name)
    if (p.length === 2) parentFeatureByKey.set(p.join('.'), f)
  }

  // Build render list — one pass through sorted features
  const renderedGroupKeys = new Set<string>()
  const renderItems: RenderItem[] = []

  for (const f of features) {
    const p = parseNumericPrefix(f.name)
    const depth = p.length

    if (depth === 2 && (subItemCounts.get(p.join('.')) ?? 0) > 0) {
      // Container feature with DB sub-records → story group header, not a card
      const key = p.join('.')
      if (!renderedGroupKeys.has(key)) {
        renderedGroupKeys.add(key)
        renderItems.push({ type: 'storyGroup', parentKey: key, parentName: f.name })
      }
    } else if (depth >= 3 && (subItemCounts.get(p.slice(0, 2).join('.')) ?? 0) > 0) {
      // Sub-feature with a known container
      const parentKey = p.slice(0, 2).join('.')
      if (!renderedGroupKeys.has(parentKey)) {
        // Container lives in a different column — insert the header before the first sub-item here
        renderedGroupKeys.add(parentKey)
        const parent = parentFeatureByKey.get(parentKey)
        renderItems.push({ type: 'storyGroup', parentKey, parentName: parent?.name ?? parentKey })
      }
      renderItems.push({ type: 'subItem', feature: f, parentKey })
    } else {
      renderItems.push({ type: 'card', feature: f })
    }
  }

  // Drop story group headers that have no sub-items in this column
  // (container might be IN_PROG while all children are in Pending — header would float alone)
  const keysWithSubItems = new Set(
    renderItems.filter(i => i.type === 'subItem').map(i => (i as Extract<RenderItem, { type: 'subItem' }>).parentKey)
  )
  const visibleItems = renderItems.filter(
    i => i.type !== 'storyGroup' || keysWithSubItems.has((i as Extract<RenderItem, { type: 'storyGroup' }>).parentKey)
  )

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
              visibleItems.map((item, index) => {
                // ── Story group header ────────────────────────────────────
                if (item.type === 'storyGroup') {
                  const totalCount = subItemCounts.get(item.parentKey) ?? 0
                  const doneCount = subItemDoneCounts.get(item.parentKey) ?? 0
                  const parentFeature = parentFeatureByKey.get(item.parentKey)
                  return (
                    <div key={`group-${item.parentKey}`} className="pt-1 first:pt-0">
                      <StoryGroupHeader
                        parentName={item.parentName}
                        totalCount={totalCount}
                        doneCount={doneCount}
                        onClick={() => parentFeature && onFeatureClick(parentFeature)}
                      />
                    </div>
                  )
                }

                // ── Sub-item or regular card ───────────────────────────────
                const feature = item.feature
                const isSubItem = item.type === 'subItem'
                const p = parseNumericPrefix(feature.name)
                const featureTasks = feature.tasks ?? []

                // For depth-2 card items only (containers without dbSubs, or plain features)
                const isDepth2 = p.length === 2
                const dbSubCountForThis = isDepth2 ? (subItemCounts.get(p.join('.')) ?? 0) : 0
                const hasDbSubs = dbSubCountForThis > 0
                // isParent = depth-2 card that has JSON tasks (no DB subs — those become storyGroup)
                const isParent = isDepth2 && !hasDbSubs && featureTasks.length > 0
                const subCount = isParent ? featureTasks.length : 0
                const subDoneCount = isParent ? featureTasks.filter(t => t.done).length : 0

                return (
                  <div
                    key={feature.id}
                    className={`animate-slide-in ${isSubItem ? 'ml-3 border-l-2 border-orange-300 pl-2' : ''}`}
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <FeatureCard
                      feature={feature}
                      onClick={() => onFeatureClick(feature)}
                      isInProgress={color === 'progress'}
                      allFeatures={allFeatures}
                      activeAgent={agentByFeatureId.get(feature.id)}
                      hasDialogueLogs={featureHasLogs?.(feature.id) ?? false}
                      onShowDialogue={onShowDialogue}
                      subItemCount={subCount > 0 ? subCount : undefined}
                      subItemsDone={subCount > 0 ? subDoneCount : undefined}
                      isContainer={isParent}
                      projectName={projectName}
                    />
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
