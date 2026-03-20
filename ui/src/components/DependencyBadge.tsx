import { AlertTriangle, GitBranch, Check } from 'lucide-react'
import * as Popover from '@radix-ui/react-popover'
import type { Feature } from '../lib/types'
import { Badge } from '@/components/ui/badge'

interface DependencyBadgeProps {
  feature: Feature
  allFeatures?: Feature[]
  compact?: boolean
}

/**
 * Badge component showing dependency status for a feature.
 * Compact mode: clickable badge that opens a popover with full dependency list.
 */
export function DependencyBadge({ feature, allFeatures = [], compact = false }: DependencyBadgeProps) {
  const dependencies = feature.dependencies || []

  if (dependencies.length === 0) {
    return null
  }

  const isBlocked = feature.blocked ??
    (feature.blocking_dependencies && feature.blocking_dependencies.length > 0) ??
    false

  const blockingIds = feature.blocking_dependencies ?? []
  const blockingCount = blockingIds.length

  const passingIds = new Set(allFeatures.filter(f => f.passes).map(f => f.id))
  const satisfiedCount = dependencies.filter(d => passingIds.has(d)).length

  if (compact) {
    return (
      <Popover.Root>
        <Popover.Trigger asChild>
          <button
            onClick={e => e.stopPropagation()}
            className="focus:outline-none"
          >
            <Badge
              variant="outline"
              className={`gap-1 font-mono text-xs cursor-pointer hover:opacity-80 ${
                isBlocked
                  ? 'bg-destructive/10 text-destructive border-destructive/30'
                  : 'bg-muted text-muted-foreground'
              }`}
            >
              {isBlocked ? (
                <>
                  <AlertTriangle size={12} />
                  <span>{blockingIds.map(id => `#${id}`).join(' ')}</span>
                </>
              ) : (
                <>
                  <GitBranch size={12} />
                  <span>{satisfiedCount}/{dependencies.length}</span>
                </>
              )}
            </Badge>
          </button>
        </Popover.Trigger>

        <Popover.Portal>
          <Popover.Content
            side="bottom"
            align="start"
            sideOffset={4}
            className="z-50 w-56 rounded-md border bg-popover p-3 shadow-md text-sm"
            onClick={e => e.stopPropagation()}
          >
            <p className="font-semibold mb-2 text-foreground">
              Afhankelijkheden ({dependencies.length})
            </p>
            <ul className="space-y-1">
              {dependencies.map(depId => {
                const depFeature = allFeatures.find(f => f.id === depId)
                const isDone = passingIds.has(depId)
                const isBlocking = blockingIds.includes(depId)
                return (
                  <li key={depId} className="flex items-center gap-2">
                    {isDone ? (
                      <Check size={12} className="text-primary shrink-0" />
                    ) : (
                      <AlertTriangle size={12} className="text-destructive shrink-0" />
                    )}
                    <span className={`font-mono ${isBlocking ? 'text-destructive' : 'text-muted-foreground'}`}>
                      #{depId}
                    </span>
                    {depFeature && (
                      <span className="truncate text-xs text-muted-foreground">
                        {depFeature.name}
                      </span>
                    )}
                  </li>
                )
              })}
            </ul>
            {isBlocked && (
              <p className="mt-2 text-xs text-destructive">
                Geblokkeerd door {blockingCount} {blockingCount === 1 ? 'feature' : 'features'}
              </p>
            )}
            <Popover.Arrow className="fill-border" />
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>
    )
  }

  // Full view with more details
  return (
    <div className="flex items-center gap-2">
      {isBlocked ? (
        <div className="flex items-center gap-1.5 text-sm text-destructive">
          <AlertTriangle size={14} />
          <span className="font-medium">
            Geblokkeerd door {blockingCount} {blockingCount === 1 ? 'feature' : 'features'}:
            {' '}{blockingIds.map(id => `#${id}`).join(', ')}
          </span>
        </div>
      ) : (
        <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <Check size={14} className="text-primary" />
          <span>
            Alle {dependencies.length} {dependencies.length === 1 ? 'dependency' : 'dependencies'} voldaan
          </span>
        </div>
      )}
    </div>
  )
}

/**
 * Small inline indicator for dependency status
 */
export function DependencyIndicator({ feature }: { feature: Feature }) {
  const dependencies = feature.dependencies || []
  const isBlocked = feature.blocked || (feature.blocking_dependencies && feature.blocking_dependencies.length > 0)

  if (dependencies.length === 0) {
    return null
  }

  if (isBlocked) {
    return (
      <span
        className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-destructive/10 text-destructive"
        title={`Geblokkeerd door ${feature.blocking_dependencies?.length || 0} features`}
      >
        <AlertTriangle size={12} />
      </span>
    )
  }

  return (
    <span
      className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-muted text-muted-foreground"
      title={`${dependencies.length} dependencies (allemaal voldaan)`}
    >
      <GitBranch size={12} />
    </span>
  )
}


