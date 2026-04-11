/**
 * GoalsView.tsx
 *
 * Sprint 1 Blok E task 1.15 (2026-04-11):
 * Goals view for mq-devEngine. Shows stories organised around their
 * acceptance criteria and provides drill-down into the agent tool calls
 * (from the agent_logs table).
 *
 * Layout (one column per story group — pending / in-progress / done):
 *   - Story header (id, name, status indicator)
 *   - Description
 *   - Verification sequence (7 steps — reuses VerificationSequence)
 *   - AC list with individual status per AC (pending / passed visually)
 *   - Expandable "tool calls" section → fetches agent logs on demand
 *
 * This is the primary "what did the agents do?" view, complementing:
 *   - Kanban: board-style state transitions
 *   - Graph: dependency visualization
 *   - Analytics: aggregate metrics
 *   - Goals (this): AC-level traceability and per-story drilldown
 */

import { useState, useMemo } from 'react'
import { ChevronRight, CheckCircle2, Circle, Loader2, Target, ScrollText, Filter } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { fetchFeatureLogs } from '../lib/api'
import type { Feature, FeatureListResponse } from '../lib/types'
import { VerificationSequence } from './VerificationSequence'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface GoalsViewProps {
  features: FeatureListResponse | undefined
  projectName: string
  onFeatureClick?: (feature: Feature) => void
}

type FilterMode = 'all' | 'in_progress' | 'pending' | 'done'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getFeatureAcs(feature: Feature): string[] {
  const f = feature as any
  if (Array.isArray(f.acceptance_criteria) && f.acceptance_criteria.length > 0) {
    return f.acceptance_criteria as string[]
  }
  if (Array.isArray(f.steps) && f.steps.length > 0) {
    return f.steps as string[]
  }
  return []
}

function getStatusLabel(feature: Feature): string {
  if (feature.passes) return 'DONE'
  if (feature.in_progress) return 'IN PROGRESS'
  if ((feature as any).blocked) return 'BLOCKED'
  return 'PENDING'
}

function getStatusColor(feature: Feature): string {
  if (feature.passes) return 'text-emerald-500'
  if (feature.in_progress) return 'text-blue-500'
  if ((feature as any).blocked) return 'text-orange-500'
  return 'text-zinc-500'
}

// ---------------------------------------------------------------------------
// Tool call drill-down (agent logs)
// ---------------------------------------------------------------------------

interface ToolCallDrilldownProps {
  feature: Feature
  projectName: string
}

function ToolCallDrilldown({ feature, projectName }: ToolCallDrilldownProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['agent-logs', projectName, feature.id],
    queryFn: () => fetchFeatureLogs(projectName, feature.id),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  })

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-3 text-xs text-muted-foreground">
        <Loader2 size={14} className="animate-spin" />
        Loading tool calls…
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-3 text-xs text-red-500">
        Failed to load agent logs: {String(error)}
      </div>
    )
  }

  if (!data || data.logs.length === 0) {
    return (
      <div className="p-3 text-xs text-muted-foreground italic">
        No agent logs yet — this story hasn't been worked on by an agent.
      </div>
    )
  }

  // Filter to just tool-call-like entries: lines that mention a tool name, or
  // that are of log_type "state_change" / "output" with structured content.
  // Without a dedicated tool_call log_type, we heuristically highlight lines
  // that look like agent actions (starts with Use or Call or has _ in a word).
  const toolCallLines = data.logs
    .filter((log) => {
      const line = log.line || ''
      return (
        /^use the \w+_\w+ tool/i.test(line) ||
        /^call(ing)? \w+_\w+/i.test(line) ||
        /^\w+_\w+\(/.test(line) ||
        log.log_type === 'state_change'
      )
    })
    .slice(0, 20) // cap for display

  return (
    <div className="p-3 bg-muted/50 rounded border border-border">
      <div className="text-xs font-semibold text-muted-foreground mb-2 flex items-center gap-2">
        <ScrollText size={12} />
        Tool calls ({toolCallLines.length} of {data.total} log entries)
      </div>
      {toolCallLines.length === 0 ? (
        <div className="text-xs text-muted-foreground italic">
          No tool calls detected in {data.total} log entries. The agent may have
          worked without structured tool invocations.
        </div>
      ) : (
        <div className="space-y-1 font-mono text-[11px] max-h-48 overflow-y-auto">
          {toolCallLines.map((log) => (
            <div key={log.id} className="flex gap-2 items-start">
              <span className="text-muted-foreground/70 shrink-0">
                {log.agent_type || '?'}
              </span>
              <span className="text-foreground truncate">{log.line}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Individual goal card
// ---------------------------------------------------------------------------

interface GoalCardProps {
  feature: Feature
  projectName: string
  onClick?: () => void
}

function GoalCard({ feature, projectName, onClick }: GoalCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [showToolCalls, setShowToolCalls] = useState(false)
  const acs = getFeatureAcs(feature)
  const statusColor = getStatusColor(feature)

  return (
    <div className="border border-border rounded-lg bg-card p-4 hover:border-primary/50 transition-colors">
      {/* Header */}
      <div className="flex items-start gap-3 mb-3">
        <button
          onClick={() => setExpanded((e) => !e)}
          className="mt-1 text-muted-foreground hover:text-foreground transition-colors"
          aria-label={expanded ? 'Collapse' : 'Expand'}
        >
          <ChevronRight
            size={16}
            className={`transition-transform ${expanded ? 'rotate-90' : ''}`}
          />
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-muted-foreground font-mono">
              #{feature.id}
            </span>
            <span className={`text-xs font-semibold uppercase tracking-wide ${statusColor}`}>
              {getStatusLabel(feature)}
            </span>
            {feature.category && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                {feature.category}
              </span>
            )}
          </div>
          <h3
            className={`font-semibold text-base leading-tight ${onClick ? 'cursor-pointer hover:text-primary' : ''}`}
            onClick={onClick}
          >
            {feature.name}
          </h3>
          {feature.description && (
            <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
              {feature.description}
            </p>
          )}
        </div>
        <div className="shrink-0">
          {feature.passes ? (
            <CheckCircle2 size={20} className="text-emerald-500" />
          ) : feature.in_progress ? (
            <Loader2 size={20} className="text-blue-500 animate-spin" />
          ) : (
            <Circle size={20} className="text-muted-foreground" />
          )}
        </div>
      </div>

      {/* Verification sequence (always visible) */}
      <div className="pl-7 mb-3">
        <VerificationSequence story={feature} />
      </div>

      {/* Expanded: AC list + tool calls */}
      {expanded && (
        <div className="pl-7 space-y-3 mt-3 border-t border-border pt-3">
          {/* AC list */}
          <div>
            <div className="text-xs font-semibold text-muted-foreground mb-2 flex items-center gap-2 uppercase tracking-wide">
              <Target size={12} />
              Acceptance Criteria ({acs.length})
            </div>
            {acs.length === 0 ? (
              <div className="text-xs text-muted-foreground italic">
                No acceptance criteria defined. This story is under-specified.
              </div>
            ) : (
              <ul className="space-y-1.5">
                {acs.map((ac, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm">
                    {feature.passes ? (
                      <CheckCircle2 size={14} className="text-emerald-500 mt-0.5 shrink-0" />
                    ) : (
                      <Circle size={14} className="text-muted-foreground mt-0.5 shrink-0" />
                    )}
                    <span className={feature.passes ? 'text-muted-foreground' : 'text-foreground'}>
                      {ac}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Dependencies */}
          {feature.dependencies && feature.dependencies.length > 0 && (
            <div className="text-xs text-muted-foreground">
              <span className="font-semibold">Depends on: </span>
              {feature.dependencies.map((id, idx) => (
                <span key={id}>
                  {idx > 0 && ', '}
                  <span className="font-mono">#{id}</span>
                </span>
              ))}
            </div>
          )}

          {/* Tool call drill-down (lazy-loaded) */}
          <div>
            <button
              onClick={() => setShowToolCalls((s) => !s)}
              className="text-xs font-semibold text-muted-foreground hover:text-foreground flex items-center gap-2 uppercase tracking-wide"
            >
              <ChevronRight
                size={12}
                className={`transition-transform ${showToolCalls ? 'rotate-90' : ''}`}
              />
              <ScrollText size={12} />
              Tool calls drill-down
            </button>
            {showToolCalls && (
              <div className="mt-2">
                <ToolCallDrilldown feature={feature} projectName={projectName} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Goals view
// ---------------------------------------------------------------------------

export function GoalsView({ features, projectName, onFeatureClick }: GoalsViewProps) {
  const [filter, setFilter] = useState<FilterMode>('all')
  const [search, setSearch] = useState('')

  const allFeatures = useMemo<Feature[]>(() => {
    if (!features) return []
    return [...features.in_progress, ...features.pending, ...features.done]
  }, [features])

  const filteredFeatures = useMemo<Feature[]>(() => {
    let result = allFeatures
    if (filter === 'in_progress') result = result.filter((f) => f.in_progress)
    else if (filter === 'pending') result = result.filter((f) => !f.in_progress && !f.passes)
    else if (filter === 'done') result = result.filter((f) => f.passes)

    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(
        (f) =>
          f.name.toLowerCase().includes(q) ||
          (f.description || '').toLowerCase().includes(q) ||
          getFeatureAcs(f).some((ac) => ac.toLowerCase().includes(q)),
      )
    }

    return result
  }, [allFeatures, filter, search])

  const counts = useMemo(() => {
    return {
      all: allFeatures.length,
      in_progress: allFeatures.filter((f) => f.in_progress).length,
      pending: allFeatures.filter((f) => !f.in_progress && !f.passes).length,
      done: allFeatures.filter((f) => f.passes).length,
    }
  }, [allFeatures])

  if (!features || allFeatures.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <Target size={48} className="mx-auto mb-3 opacity-20" />
        <p>No stories yet. Add stories or run the initializer to get started.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="inline-flex rounded-lg border p-1 bg-background">
          {(['all', 'in_progress', 'pending', 'done'] as FilterMode[]).map((mode) => (
            <button
              key={mode}
              onClick={() => setFilter(mode)}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                filter === mode
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {mode === 'all' ? 'All' : mode === 'in_progress' ? 'In progress' : mode === 'pending' ? 'Pending' : 'Done'}
              <span className="ml-1.5 text-[10px] opacity-70">({counts[mode]})</span>
            </button>
          ))}
        </div>

        <div className="flex-1 min-w-[200px] max-w-md">
          <div className="relative">
            <Filter size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by name, description, or AC…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-sm bg-background border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>

        <div className="text-xs text-muted-foreground">
          {filteredFeatures.length} of {allFeatures.length} stories
        </div>
      </div>

      {/* Goal cards */}
      {filteredFeatures.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground text-sm">
          No stories match the current filter.
        </div>
      ) : (
        <div className="space-y-3">
          {filteredFeatures.map((feature) => (
            <GoalCard
              key={feature.id}
              feature={feature}
              projectName={projectName}
              onClick={onFeatureClick ? () => onFeatureClick(feature) : undefined}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default GoalsView
