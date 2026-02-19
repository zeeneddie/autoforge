import { X, Copy, Check, User, Bot, Wrench, Brain, ChevronDown, ChevronRight } from 'lucide-react'
import { useState, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { AgentAvatar } from './AgentAvatar'
import type { ActiveAgent, AgentLogEntry, AgentType, DialogueEntry } from '../lib/types'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

/**
 * Parse raw agent log entries into structured dialogue entries.
 * Classifies lines based on known patterns from agent.py output.
 */
function parseLogsToDialogue(logs: AgentLogEntry[]): DialogueEntry[] {
  const entries: DialogueEntry[] = []

  for (const log of logs) {
    const line = log.line
    const timestamp = log.timestamp

    // @@PROMPT: marker → prompt entry
    if (line.startsWith('@@PROMPT:')) {
      entries.push({
        type: 'prompt',
        content: line.slice('@@PROMPT:'.length),
        timestamp,
      })
      continue
    }

    // [Thinking] ... → thinking entry
    const thinkingMatch = line.match(/^\[Thinking\]\s*(.*)/)
    if (thinkingMatch) {
      entries.push({
        type: 'thinking',
        content: thinkingMatch[1],
        timestamp,
      })
      continue
    }

    // [Tool: name] → tool_use entry
    const toolMatch = line.match(/^\[Tool:\s*(.+?)\]/)
    if (toolMatch) {
      entries.push({
        type: 'tool_use',
        content: '',
        toolName: toolMatch[1],
        timestamp,
      })
      continue
    }

    // >>> [MCP] feature_xxx(...) → attach MCP info to last tool_use
    const mcpMatch = line.match(/^\s*>>>\s*\[MCP\]\s*(.+)/)
    if (mcpMatch) {
      const lastTool = findLastOfType(entries, 'tool_use')
      if (lastTool) {
        lastTool.toolInput = mcpMatch[1]
      }
      continue
    }

    //    Input: ... → attach to last tool_use
    const inputMatch = line.match(/^\s{2,}Input:\s*(.*)/)
    if (inputMatch) {
      const lastTool = findLastOfType(entries, 'tool_use')
      if (lastTool) {
        lastTool.toolInput = inputMatch[1]
      }
      continue
    }

    //    [Done] → tool_result with done status
    if (/^\s{2,}\[Done\]/.test(line)) {
      const lastTool = findLastOfType(entries, 'tool_use')
      if (lastTool) {
        lastTool.toolStatus = 'done'
      }
      entries.push({
        type: 'tool_result',
        content: 'Done',
        toolStatus: 'done',
        timestamp,
      })
      continue
    }

    //    [Error] ... → tool_result with error
    const errorMatch = line.match(/^\s{2,}\[Error\]\s*(.*)/)
    if (errorMatch) {
      const lastTool = findLastOfType(entries, 'tool_use')
      if (lastTool) {
        lastTool.toolStatus = 'error'
      }
      entries.push({
        type: 'tool_result',
        content: errorMatch[1],
        toolStatus: 'error',
        timestamp,
      })
      continue
    }

    //    [BLOCKED] ... → tool_result with blocked
    const blockedMatch = line.match(/^\s{2,}\[BLOCKED\]\s*(.*)/)
    if (blockedMatch) {
      const lastTool = findLastOfType(entries, 'tool_use')
      if (lastTool) {
        lastTool.toolStatus = 'blocked'
      }
      entries.push({
        type: 'tool_result',
        content: blockedMatch[1],
        toolStatus: 'blocked',
        timestamp,
      })
      continue
    }

    // Skip noise lines (separators, "Sending prompt...", session summary, stream events)
    if (
      /^-{10,}$/.test(line.trim()) ||
      /^={10,}$/.test(line.trim()) ||
      line.startsWith('Sending prompt to Claude') ||
      line.startsWith('[Stream]') ||
      line.startsWith('[System]') ||
      line.startsWith('[Session Summary]') ||
      line.trim() === ''
    ) {
      continue
    }

    // Everything else → text (Claude's response)
    // Merge consecutive text entries
    const lastEntry = entries[entries.length - 1]
    if (lastEntry?.type === 'text') {
      lastEntry.content += '\n' + line
    } else {
      entries.push({
        type: 'text',
        content: line,
        timestamp,
      })
    }
  }

  return entries
}

function findLastOfType(entries: DialogueEntry[], type: DialogueEntry['type']): DialogueEntry | undefined {
  for (let i = entries.length - 1; i >= 0; i--) {
    if (entries[i].type === type) return entries[i]
  }
  return undefined
}

// Get agent type badge config (duplicated from AgentCard to avoid circular deps)
function getAgentTypeBadge(agentType: AgentType): { label: string; className: string } {
  if (agentType === 'testing') {
    return {
      label: 'TEST',
      className: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
    }
  }
  return {
    label: 'CODE',
    className: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  }
}

interface RunInfo {
  run_id: number
  log_count: number
  started_at: string
  ended_at: string
}

interface AgentDialogueModalProps {
  agent: ActiveAgent
  logs: AgentLogEntry[]
  runs?: RunInfo[]
  onClose: () => void
}

export function AgentDialogueModal({ agent, logs, runs = [], onClose }: AgentDialogueModalProps) {
  const [copied, setCopied] = useState(false)
  const [expandedThinking, setExpandedThinking] = useState<Set<number>>(new Set())
  // When multiple runs exist, default to the latest run
  const [selectedRunId, setSelectedRunId] = useState<number | null>(
    runs.length > 1 ? runs[runs.length - 1].run_id : null
  )
  const typeBadge = getAgentTypeBadge(agent.agentType || 'coding')

  // Filter logs by selected run if applicable
  const filteredLogs = useMemo(() => {
    if (selectedRunId === null || runs.length <= 1) return logs
    // Persisted logs have run_id info encoded — filter by matching run
    // The logs come from the API with run_id as part of the timestamp ordering
    // Since in-memory logs don't have run_id, we use the run boundaries
    const run = runs.find(r => r.run_id === selectedRunId)
    if (!run) return logs
    return logs.filter(log => {
      const logTime = new Date(log.timestamp).getTime()
      return logTime >= new Date(run.started_at).getTime() && logTime <= new Date(run.ended_at).getTime() + 1000
    })
  }, [logs, selectedRunId, runs])

  const dialogue = useMemo(() => parseLogsToDialogue(filteredLogs), [filteredLogs])

  const handleCopy = async () => {
    const text = dialogue
      .map((entry) => {
        switch (entry.type) {
          case 'prompt':
            return `[PROMPT] ${entry.content}`
          case 'text':
            return entry.content
          case 'tool_use':
            return `[Tool: ${entry.toolName}]${entry.toolInput ? ` ${entry.toolInput}` : ''}`
          case 'tool_result':
            return `  → ${entry.toolStatus}: ${entry.content}`
          case 'thinking':
            return `[Thinking] ${entry.content}`
        }
      })
      .join('\n')
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const toggleThinking = (idx: number) => {
    setExpandedThinking((prev) => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }

  return createPortal(
    <div
      className="fixed inset-0 flex items-center justify-center p-4 bg-black/50"
      style={{ zIndex: 9999 }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <Card className="w-full max-w-4xl max-h-[85vh] flex flex-col py-0">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-3">
            <AgentAvatar name={agent.agentName} state={agent.state} size="sm" />
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-semibold text-lg">
                  {agent.agentName} Dialogue
                </h2>
                <Badge variant="outline" className={`text-[10px] ${typeBadge.className}`}>
                  {typeBadge.label}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground">
                {agent.featureIds && agent.featureIds.length > 1
                  ? `Batch: ${agent.featureIds.map((id) => `#${id}`).join(', ')}`
                  : `Feature #${agent.featureId}: ${agent.featureName}`}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              {dialogue.length} entries
            </Badge>
            <Button variant="outline" size="sm" onClick={handleCopy}>
              {copied ? <Check size={14} /> : <Copy size={14} />}
              {copied ? 'Copied!' : 'Copy'}
            </Button>
            <Button variant="ghost" size="icon-sm" onClick={onClose}>
              <X size={20} />
            </Button>
          </div>
        </div>

        {/* Run selector — shown when multiple attempts exist */}
        {runs.length > 1 && (
          <div className="flex items-center gap-2 px-4 py-2 border-b bg-muted/30">
            <span className="text-xs font-semibold text-muted-foreground">
              {runs.length} attempts:
            </span>
            <div className="flex gap-1 flex-wrap">
              {runs.map((run, idx) => (
                <button
                  key={run.run_id}
                  onClick={() => setSelectedRunId(run.run_id)}
                  className={`
                    px-2 py-0.5 rounded text-xs font-mono transition-colors
                    ${(selectedRunId === run.run_id) || (selectedRunId === null && idx === runs.length - 1)
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted hover:bg-muted-foreground/20 text-muted-foreground'
                    }
                  `}
                  title={`${run.log_count} lines, ${new Date(run.started_at).toLocaleTimeString()}`}
                >
                  #{idx + 1}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Dialogue content */}
        <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-3">
          {dialogue.length === 0 ? (
            <p className="text-muted-foreground italic text-center py-8">
              No dialogue entries yet. Waiting for agent activity...
            </p>
          ) : (
            dialogue.map((entry, idx) => (
              <DialogueEntryRow
                key={idx}
                entry={entry}
                isThinkingExpanded={expandedThinking.has(idx)}
                onToggleThinking={() => toggleThinking(idx)}
              />
            ))
          )}
        </div>
      </Card>
    </div>,
    document.body,
  )
}

function DialogueEntryRow({
  entry,
  isThinkingExpanded,
  onToggleThinking,
}: {
  entry: DialogueEntry
  isThinkingExpanded: boolean
  onToggleThinking: () => void
}) {
  switch (entry.type) {
    case 'prompt':
      return (
        <div className="flex gap-3 p-3 rounded-lg bg-muted/60">
          <User size={16} className="text-muted-foreground shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] text-muted-foreground font-semibold uppercase">
                Prompt
              </span>
              <span className="text-[10px] text-muted-foreground font-mono">
                {new Date(entry.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <p className="text-sm text-foreground whitespace-pre-wrap break-words">
              {entry.content}
            </p>
          </div>
        </div>
      )

    case 'text':
      return (
        <div className="flex gap-3 p-3 rounded-lg border bg-card">
          <Bot size={16} className="text-primary shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] text-muted-foreground font-semibold uppercase">
                Response
              </span>
              <span className="text-[10px] text-muted-foreground font-mono">
                {new Date(entry.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <p className="text-sm text-foreground whitespace-pre-wrap break-words">
              {entry.content}
            </p>
          </div>
        </div>
      )

    case 'tool_use':
      return (
        <div className="flex gap-3 p-2 pl-8 rounded border-l-2 border-blue-400 bg-blue-50/50 dark:bg-blue-950/20">
          <Wrench size={14} className="text-blue-500 shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-semibold text-blue-700 dark:text-blue-300">
                {entry.toolName}
              </span>
              <span className="text-[10px] text-muted-foreground font-mono ml-auto">
                {new Date(entry.timestamp).toLocaleTimeString()}
              </span>
              {entry.toolStatus && (
                <Badge
                  variant="outline"
                  className={`text-[10px] ${
                    entry.toolStatus === 'done'
                      ? 'text-green-600 border-green-300'
                      : entry.toolStatus === 'error'
                        ? 'text-red-600 border-red-300'
                        : 'text-yellow-600 border-yellow-300'
                  }`}
                >
                  {entry.toolStatus}
                </Badge>
              )}
            </div>
            {entry.toolInput && (
              <p className="text-xs text-muted-foreground font-mono mt-1 truncate" title={entry.toolInput}>
                {entry.toolInput}
              </p>
            )}
          </div>
        </div>
      )

    case 'tool_result':
      return (
        <div className="pl-12">
          <span
            className={`text-xs font-mono ${
              entry.toolStatus === 'error'
                ? 'text-red-500'
                : entry.toolStatus === 'blocked'
                  ? 'text-yellow-500'
                  : 'text-green-600'
            }`}
          >
            {entry.toolStatus === 'done' ? null : `→ ${entry.content}`}
          </span>
        </div>
      )

    case 'thinking':
      return (
        <div className="pl-8">
          <button
            onClick={onToggleThinking}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <Brain size={12} className="shrink-0" />
            {isThinkingExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            <span className="italic">Thinking...</span>
          </button>
          {isThinkingExpanded && (
            <p className="text-xs text-muted-foreground italic mt-1 pl-6 whitespace-pre-wrap">
              {entry.content}
            </p>
          )}
        </div>
      )
  }
}
