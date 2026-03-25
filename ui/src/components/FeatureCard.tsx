import { useState } from 'react'
import { CheckCircle2, Circle, Loader2, MessageCircle, ScrollText, ListChecks, AlertTriangle, ListTodo } from 'lucide-react'
import type { Feature, ActiveAgent, FeatureTask } from '../lib/types'
import { DependencyBadge } from './DependencyBadge'
import { AgentAvatar } from './AgentAvatar'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { useBreakdown } from '../hooks/useProjects'

interface FeatureCardProps {
  feature: Feature
  onClick: () => void
  isInProgress?: boolean
  allFeatures?: Feature[]
  activeAgent?: ActiveAgent
  hasDialogueLogs?: boolean
  onShowDialogue?: (featureId: number) => void
  subItemCount?: number
  subItemsDone?: number
  projectName?: string
}

// Generate consistent color for category
function getCategoryColor(category: string): string {
  const colors = [
    'bg-pink-500',
    'bg-cyan-500',
    'bg-green-500',
    'bg-yellow-500',
    'bg-orange-500',
    'bg-purple-500',
    'bg-blue-500',
  ]

  let hash = 0
  for (let i = 0; i < category.length; i++) {
    hash = category.charCodeAt(i) + ((hash << 5) - hash)
  }

  return colors[Math.abs(hash) % colors.length]
}

function TasksPopup({ feature }: { feature: Feature }) {
  const tasks = feature.tasks ?? []
  if (tasks.length === 0) return null

  const doneCount = tasks.filter(t => t.done).length
  const allDone = doneCount === tasks.length

  return (
    <DialogContent className="max-w-md" onClick={e => e.stopPropagation()}>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <ListChecks size={18} />
          Taken — #{feature.id} {feature.name.slice(0, 40)}{feature.name.length > 40 ? '…' : ''}
        </DialogTitle>
      </DialogHeader>

      {/* Progress bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>{doneCount} / {tasks.length} voltooid</span>
          {allDone && <span className="text-primary font-medium">✓ Alle taken klaar</span>}
        </div>
        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full bg-primary rounded-full transition-all"
            style={{ width: `${tasks.length > 0 ? (doneCount / tasks.length) * 100 : 0}%` }}
          />
        </div>
      </div>

      {/* Task list */}
      {tasks.length > 0 && (
        <ul className="space-y-2 mt-1">
          {tasks.map((task: FeatureTask) => (
            <li key={task.id} className={`flex items-start gap-2.5 p-2 rounded-md text-sm ${task.done ? 'bg-primary/5' : 'bg-muted/40'}`}>
              {task.done
                ? <CheckCircle2 size={15} className="text-primary shrink-0 mt-0.5" />
                : <Circle size={15} className="text-muted-foreground shrink-0 mt-0.5" />
              }
              <div className="flex-1 min-w-0">
                <span className={task.done ? 'text-foreground' : 'text-muted-foreground'}>
                  {task.name}
                </span>
                {task.done && task.test_count > 0 && (
                  <span className="ml-2 text-xs text-primary/70 font-mono">
                    [{task.test_count} test{task.test_count !== 1 ? 's' : ''}]
                  </span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* AC labels (set by architect agent) */}
      {feature.steps && feature.steps.length > 0 && (
        <div className="mt-3 space-y-1.5">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Acceptatiecriteria</p>
          <ul className="space-y-1">
            {feature.steps.map((step, i) => {
              const label = feature.ac_labels?.[i]
              const labelStyle =
                label === 'human-only' ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400' :
                label === 'needs-fixture' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
                label === 'auto-testable' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                'bg-muted text-muted-foreground'
              return (
                <li key={i} className="flex items-start gap-2 text-xs">
                  {label && (
                    <span className={`shrink-0 mt-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium ${labelStyle}`}>
                      {label === 'human-only' ? '👤 human' : label === 'needs-fixture' ? '🔧 fixture' : '✓ auto'}
                    </span>
                  )}
                  <span className="text-muted-foreground line-clamp-2">{step}</span>
                </li>
              )
            })}
          </ul>
        </div>
      )}

      {/* Escalation reason */}
      {feature.escalation_reason && (
        <div className="mt-3 p-2.5 rounded-md bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 flex items-start gap-2">
          <AlertTriangle size={14} className="text-orange-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-semibold text-orange-700 dark:text-orange-400">Escalatie — vereist jouw oordeel</p>
            <p className="text-xs text-orange-600 dark:text-orange-300 mt-0.5">{feature.escalation_reason}</p>
          </div>
        </div>
      )}
    </DialogContent>
  )
}

export function FeatureCard({ feature, onClick, isInProgress, allFeatures = [], activeAgent, hasDialogueLogs, onShowDialogue, subItemCount, subItemsDone, projectName }: FeatureCardProps) {
  const [tasksOpen, setTasksOpen] = useState(false)
  const breakdown = useBreakdown(projectName ?? '')
  const categoryColor = getCategoryColor(feature.category)
  const isBlocked = feature.blocked || (feature.blocking_dependencies && feature.blocking_dependencies.length > 0)
  // Don't show agent overlay on completed features (agent may linger in activeAgents after finishing)
  const hasActiveAgent = !!activeAgent && !feature.passes

  const tasks = feature.tasks ?? []
  const tasksDone = tasks.filter(t => t.done).length
  const isEscalated = feature.review_status === 'needs_human_review'
  const humanOnlyCount = (feature.ac_labels ?? []).filter(l => l === 'human-only').length

  return (
    <>
    <Dialog open={tasksOpen} onOpenChange={setTasksOpen}>
      <TasksPopup feature={feature} />
    </Dialog>
    <Card
      onClick={onClick}
      className={`
        cursor-pointer transition-all hover:border-primary py-3
        ${feature.passes ? 'border-primary/50' : ''}
        ${isBlocked && !feature.passes ? 'border-destructive/50 opacity-80' : ''}
        ${hasActiveAgent ? 'ring-2 ring-primary ring-offset-2' : ''}
      `}
    >
      <CardContent className="p-4 space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge className={`${categoryColor} text-white`}>
              {feature.category}
            </Badge>
            <DependencyBadge feature={feature} allFeatures={allFeatures} compact />
            {subItemCount !== undefined && subItemCount > 0 && (
              <Badge variant="outline" className="text-orange-600 border-orange-400 text-[10px] px-1.5 py-0">
                {subItemCount} sub
              </Badge>
            )}
          </div>
          <span className="font-mono text-sm text-muted-foreground shrink-0">
            #{feature.id}
          </span>
        </div>

        {/* Escalation banner */}
        {isEscalated && (
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-orange-100 dark:bg-orange-900/30 border border-orange-300 dark:border-orange-700">
            <AlertTriangle size={12} className="text-orange-600 dark:text-orange-400 shrink-0" />
            <span className="text-xs font-medium text-orange-700 dark:text-orange-400">Vereist jouw oordeel</span>
          </div>
        )}

        {/* Human-only AC hint (pre-coding, no escalation yet) */}
        {!isEscalated && humanOnlyCount > 0 && (
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700">
            <AlertTriangle size={12} className="text-yellow-600 dark:text-yellow-400 shrink-0" />
            <span className="text-xs text-yellow-700 dark:text-yellow-400">{humanOnlyCount} AC{humanOnlyCount !== 1 ? "'s" : ''} vereist menselijk oordeel</span>
          </div>
        )}

        {/* Name */}
        <h3 className="font-semibold line-clamp-2">
          {feature.name}
        </h3>

        {/* Description */}
        <p className="text-sm text-muted-foreground line-clamp-2">
          {feature.description}
        </p>

        {/* Agent working on this feature (hide for completed features) */}
        {activeAgent && !feature.passes && (
          <div className="flex items-center gap-2 py-2 px-2 rounded-md bg-primary/10 border border-primary/30">
            <AgentAvatar name={activeAgent.agentName} state={activeAgent.state} size="sm" />
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-primary">
                {activeAgent.agentName} is working on this!
              </div>
              {activeAgent.thought && (
                <div className="flex items-center gap-1 mt-0.5">
                  <MessageCircle size={10} className="text-muted-foreground shrink-0" />
                  <p className="text-[10px] text-muted-foreground truncate italic">
                    {activeAgent.thought}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Sub-feature progress bar (for parent features with Feature DB sub-records) */}
        {subItemCount !== undefined && subItemCount > 0 && (
          <div className="space-y-0.5">
            <div className="flex justify-between text-[10px] text-muted-foreground">
              <span>Sub-features</span>
              <span className="font-mono">{subItemsDone ?? 0}/{subItemCount}</span>
            </div>
            <div className="h-1 bg-muted rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${(subItemsDone ?? 0) === subItemCount ? 'bg-primary' : 'bg-primary/60'}`}
                style={{ width: `${((subItemsDone ?? 0) / subItemCount) * 100}%` }}
              />
            </div>
          </div>
        )}

        {/* Inline task progress bar — only when no Feature DB sub-records (avoids duplication) */}
        {tasks.length > 0 && !(subItemCount !== undefined && subItemCount > 0) && (
          <div className="space-y-0.5">
            <div className="flex justify-between text-[10px] text-muted-foreground">
              <span>Taken</span>
              <span className="font-mono">{tasksDone}/{tasks.length}</span>
            </div>
            <div className="h-1 bg-muted rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${tasksDone === tasks.length ? 'bg-primary' : 'bg-primary/60'}`}
                style={{ width: `${(tasksDone / tasks.length) * 100}%` }}
              />
            </div>
          </div>
        )}

        {/* Status */}
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            {isInProgress ? (
              <>
                <Loader2 size={16} className="animate-spin text-primary" />
                <span className="text-primary font-medium">Processing...</span>
              </>
            ) : feature.passes ? (
              <>
                <CheckCircle2 size={16} className="text-primary" />
                <span className="text-primary font-medium">Complete</span>
              </>
            ) : isBlocked ? (
              <>
                <Circle size={16} className="text-destructive" />
                <span className="text-destructive">Blocked</span>
              </>
            ) : (
              <>
                <Circle size={16} className="text-muted-foreground" />
                <span className="text-muted-foreground">Pending</span>
              </>
            )}
          </div>
          <div className="flex items-center gap-1">
            {/* Breakdown knop: pending features zonder tasks, als projectName bekend is */}
            {!feature.passes && !feature.in_progress && tasks.length === 0 && projectName && (
              <button
                onClick={(e) => { e.stopPropagation(); breakdown.mutate(feature.id) }}
                disabled={breakdown.isPending}
                title="Breakdown in taken"
                className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
              >
                {breakdown.isPending
                  ? <Loader2 size={14} className="animate-spin" />
                  : <ListTodo size={14} />
                }
              </button>
            )}
            {/* Only show tasks button when no Feature DB sub-records exist (avoids duplication) */}
            {tasks.length > 0 && !(subItemCount !== undefined && subItemCount > 0) && (
              <button
                onClick={(e) => { e.stopPropagation(); setTasksOpen(true) }}
                className="flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-muted transition-colors"
                title={`Taken: ${tasksDone}/${tasks.length}`}
              >
                <ListChecks size={14} className="text-muted-foreground" />
                <span className="text-xs font-mono text-muted-foreground">{tasksDone}/{tasks.length}</span>
              </button>
            )}
            {hasDialogueLogs && onShowDialogue && (
              <button
                onClick={(e) => { e.stopPropagation(); onShowDialogue(feature.id) }}
                className="p-1 rounded hover:bg-muted transition-colors"
                title="View agent dialogue"
              >
                <ScrollText size={14} className="text-muted-foreground hover:text-foreground" />
              </button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
    </>
  )
}
