/**
 * StuckStateModal — shown when the orchestrator detects a stuck state
 * and needs human input (confidence < 0.8 or max auto-recoveries reached).
 */

import { useState, useEffect, useCallback } from 'react'
import type { StuckStateData, StuckSuggestion } from '../lib/types'
import { getStuckState, submitStuckDecision } from '../lib/api'

interface Props {
  projectName: string
  isStuck: boolean
  onResolved: () => void
}

export default function StuckStateModal({ projectName, isStuck, onResolved }: Props) {
  const [data, setData] = useState<StuckStateData | null>(null)
  const [showAnalysis, setShowAnalysis] = useState(false)
  const [selectedSuggestions, setSelectedSuggestions] = useState<Set<number>>(new Set())
  const [submitting, setSubmitting] = useState(false)

  // Fetch stuck state data when triggered by WebSocket OR via polling fallback
  useEffect(() => {
    if (!projectName) return

    const fetchStuckState = () => {
      getStuckState(projectName).then(d => {
        if (d && d.decision === null) {
          setData(d)
          const indices = new Set(d.analysis.suggestions.map((_: StuckSuggestion, i: number) => i))
          setSelectedSuggestions(indices)
        } else if (!d) {
          setData(null)
        }
      })
    }

    // Fetch immediately if WebSocket says stuck
    if (isStuck) {
      fetchStuckState()
      return
    }

    // Polling fallback: check every 10s in case WebSocket missed the event
    fetchStuckState()
    const interval = setInterval(fetchStuckState, 10000)
    return () => clearInterval(interval)
  }, [isStuck, projectName])

  const handleDecision = useCallback(async (decision: 'stop' | 'retry' | 'modify') => {
    if (!data) return
    setSubmitting(true)
    try {
      const mods = decision === 'modify'
        ? data.analysis.suggestions.filter((_: StuckSuggestion, i: number) => selectedSuggestions.has(i))
        : undefined
      await submitStuckDecision(projectName, decision, mods)
      onResolved()
    } finally {
      setSubmitting(false)
    }
  }, [data, projectName, selectedSuggestions, onResolved])

  const toggleSuggestion = (index: number) => {
    setSelectedSuggestions(prev => {
      const next = new Set(prev)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  if (!data) return null

  const { analysis, failed_features, blocked_features, passing_count, total_count } = data

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white border-3 border-black shadow-[6px_6px_0_0_black] max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="bg-red-400 border-b-3 border-black p-4">
          <h2 className="text-xl font-black uppercase">Engine Vastgelopen</h2>
          <p className="text-sm font-bold mt-1">Beslissing nodig — {passing_count}/{total_count} features passing</p>
        </div>

        {/* Summary */}
        <div className="p-4 border-b-2 border-black/20">
          <p className="font-semibold">{analysis.human_summary}</p>
          {data.auto_recovery_count > 0 && (
            <p className="text-sm text-gray-600 mt-1">
              {data.auto_recovery_count}x auto-recovery eerder uitgevoerd
            </p>
          )}
        </div>

        {/* Failed features */}
        {failed_features.length > 0 && (
          <div className="p-4 border-b-2 border-black/20">
            <h3 className="font-bold text-sm uppercase text-red-600 mb-2">Gefaalde Features</h3>
            <div className="space-y-1">
              {failed_features.map(f => (
                <div key={f.id} className="flex justify-between text-sm bg-red-50 p-2 border border-red-200">
                  <span className="font-mono">#{f.id} {f.name}</span>
                  <span className="text-red-600 font-bold">{f.failure_count}x gefaald</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Blocked features */}
        {blocked_features.length > 0 && (
          <div className="p-4 border-b-2 border-black/20">
            <h3 className="font-bold text-sm uppercase text-amber-600 mb-2">Geblokkeerde Features</h3>
            <div className="space-y-1">
              {blocked_features.map(f => (
                <div key={f.id} className="flex justify-between text-sm bg-amber-50 p-2 border border-amber-200">
                  <span className="font-mono">#{f.id} {f.name}</span>
                  <span className="text-amber-600">blocked by #{f.blocked_by.join(', #')}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* LLM Analysis (collapsible) */}
        <div className="p-4 border-b-2 border-black/20">
          <button
            onClick={() => setShowAnalysis(!showAnalysis)}
            className="text-sm font-bold uppercase text-blue-600 hover:underline"
          >
            {showAnalysis ? 'Verberg' : 'Toon'} LLM Analyse
          </button>
          {showAnalysis && (
            <div className="mt-2 p-3 bg-gray-50 border border-gray-200 text-sm whitespace-pre-wrap font-mono">
              {analysis.root_cause_analysis}
            </div>
          )}
        </div>

        {/* Suggestions */}
        {analysis.suggestions.length > 0 && (
          <div className="p-4 border-b-2 border-black/20">
            <h3 className="font-bold text-sm uppercase mb-2">LLM Suggesties</h3>
            <div className="space-y-2">
              {analysis.suggestions.map((s: StuckSuggestion, i: number) => (
                <label
                  key={i}
                  className={`flex items-start gap-2 p-2 border cursor-pointer transition-colors ${
                    selectedSuggestions.has(i)
                      ? 'bg-blue-50 border-blue-300'
                      : 'bg-white border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedSuggestions.has(i)}
                    onChange={() => toggleSuggestion(i)}
                    className="mt-0.5"
                  />
                  <div className="flex-1 text-sm">
                    <div className="flex justify-between">
                      <span className="font-bold">
                        {s.type.replace(/_/g, ' ')} — #{s.feature_id}
                      </span>
                      <span className={`font-mono text-xs px-1 ${
                        s.confidence >= 0.8 ? 'bg-green-100 text-green-700'
                          : s.confidence >= 0.5 ? 'bg-amber-100 text-amber-700'
                            : 'bg-red-100 text-red-700'
                      }`}>
                        {(s.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-gray-600 mt-0.5">{s.reason}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="p-4 flex gap-3">
          <button
            onClick={() => handleDecision('stop')}
            disabled={submitting}
            className="px-4 py-2 bg-red-500 text-white font-bold border-2 border-black shadow-[3px_3px_0_0_black] hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-[2px_2px_0_0_black] transition-all disabled:opacity-50"
          >
            Stop Engine
          </button>
          <button
            onClick={() => handleDecision('retry')}
            disabled={submitting}
            className="px-4 py-2 bg-amber-400 text-black font-bold border-2 border-black shadow-[3px_3px_0_0_black] hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-[2px_2px_0_0_black] transition-all disabled:opacity-50"
          >
            Retry Gefaalde Features
          </button>
          {analysis.suggestions.length > 0 && (
            <button
              onClick={() => handleDecision('modify')}
              disabled={submitting || selectedSuggestions.size === 0}
              className="px-4 py-2 bg-green-400 text-black font-bold border-2 border-black shadow-[3px_3px_0_0_black] hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-[2px_2px_0_0_black] transition-all disabled:opacity-50"
            >
              Pas Suggesties Toe ({selectedSuggestions.size})
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
