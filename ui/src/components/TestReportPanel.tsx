import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useTestReport, useTestHistory } from '../hooks/useProjects'
import { ChevronDown, ChevronRight, FlaskConical, CheckCircle2, BarChart3 } from 'lucide-react'
import type { TestRunSummary } from '../lib/types'

interface TestReportPanelProps {
  projectName: string
}

export function TestReportPanel({ projectName }: TestReportPanelProps) {
  const { data: report, isLoading } = useTestReport(projectName, true)
  const [expandedFeature, setExpandedFeature] = useState<number | null>(null)

  if (isLoading) {
    return (
      <Card className="p-8 text-center">
        <div className="animate-pulse text-muted-foreground">Loading test report...</div>
      </Card>
    )
  }

  if (!report || report.total_features === 0) {
    return (
      <Card className="p-8 text-center">
        <FlaskConical size={32} className="mx-auto mb-3 text-muted-foreground" />
        <p className="text-muted-foreground">No test data available yet. Run the agent to generate test results.</p>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <SummaryCard
          label="Total Features"
          value={report.total_features}
          icon={<BarChart3 size={18} className="text-blue-500" />}
        />
        <SummaryCard
          label="Tested"
          value={report.features_tested}
          subtitle={`${report.features_never_tested} untested`}
          icon={<FlaskConical size={18} className="text-purple-500" />}
        />
        <SummaryCard
          label="Pass Rate"
          value={`${report.overall_pass_rate}%`}
          icon={<CheckCircle2 size={18} className="text-green-500" />}
        />
        <SummaryCard
          label="Test Runs"
          value={report.total_test_runs}
          icon={<BarChart3 size={18} className="text-orange-500" />}
        />
      </div>

      {/* Feature table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Feature Test Results</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="text-left py-2 px-4 font-medium w-8"></th>
                  <th className="text-left py-2 px-4 font-medium">Feature</th>
                  <th className="text-center py-2 px-4 font-medium">Pass</th>
                  <th className="text-center py-2 px-4 font-medium">Fail</th>
                  <th className="text-left py-2 px-4 font-medium w-40">Pass Rate</th>
                  <th className="text-center py-2 px-4 font-medium">Last Result</th>
                </tr>
              </thead>
              <tbody>
                {report.feature_summaries.map((summary) => (
                  <FeatureRow
                    key={summary.feature_id}
                    summary={summary}
                    isExpanded={expandedFeature === summary.feature_id}
                    onToggle={() =>
                      setExpandedFeature(
                        expandedFeature === summary.feature_id ? null : summary.feature_id
                      )
                    }
                    projectName={projectName}
                  />
                ))}
                {report.feature_summaries.length === 0 && (
                  <tr>
                    <td colSpan={6} className="text-center py-6 text-muted-foreground">
                      No features with test results
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function SummaryCard({
  label,
  value,
  subtitle,
  icon,
}: {
  label: string
  value: string | number
  subtitle?: string
  icon: React.ReactNode
}) {
  return (
    <Card className="p-4">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs text-muted-foreground font-medium">{label}</span>
      </div>
      <div className="text-2xl font-bold">{value}</div>
      {subtitle && <div className="text-xs text-muted-foreground mt-0.5">{subtitle}</div>}
    </Card>
  )
}

function FeatureRow({
  summary,
  isExpanded,
  onToggle,
  projectName,
}: {
  summary: TestRunSummary
  isExpanded: boolean
  onToggle: () => void
  projectName: string
}) {
  const passRate = summary.total_runs > 0
    ? Math.round((summary.pass_count / summary.total_runs) * 100)
    : 0

  return (
    <>
      <tr
        className="border-b hover:bg-muted/30 cursor-pointer transition-colors"
        onClick={onToggle}
      >
        <td className="py-2 px-4">
          {summary.total_runs > 0 ? (
            isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />
          ) : (
            <span className="w-3.5 inline-block" />
          )}
        </td>
        <td className="py-2 px-4 font-medium">
          <span className="text-muted-foreground text-xs mr-1.5">#{summary.feature_id}</span>
          {summary.feature_name}
        </td>
        <td className="text-center py-2 px-4 text-green-600 font-medium">{summary.pass_count}</td>
        <td className="text-center py-2 px-4 text-red-600 font-medium">{summary.fail_count}</td>
        <td className="py-2 px-4">
          <div className="flex items-center gap-2">
            <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 rounded-full transition-all"
                style={{ width: `${passRate}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground w-8 text-right">{passRate}%</span>
          </div>
        </td>
        <td className="text-center py-2 px-4">
          {summary.last_result === null ? (
            <Badge variant="outline" className="text-xs">Untested</Badge>
          ) : summary.last_result ? (
            <Badge className="bg-green-500/15 text-green-600 border-green-500/30 text-xs">Pass</Badge>
          ) : (
            <Badge className="bg-red-500/15 text-red-600 border-red-500/30 text-xs">Fail</Badge>
          )}
        </td>
      </tr>
      {isExpanded && summary.total_runs > 0 && (
        <tr>
          <td colSpan={6} className="bg-muted/20 px-4 py-3">
            <TestHistoryHeatmap projectName={projectName} featureId={summary.feature_id} />
          </td>
        </tr>
      )}
    </>
  )
}

function TestHistoryHeatmap({
  projectName,
  featureId,
}: {
  projectName: string
  featureId: number
}) {
  const { data, isLoading } = useTestHistory(projectName, featureId, 100)

  if (isLoading) {
    return <div className="text-xs text-muted-foreground animate-pulse">Loading history...</div>
  }

  if (!data || data.runs.length === 0) {
    return <div className="text-xs text-muted-foreground">No test history</div>
  }

  // Compute stats
  const runs = data.runs
  const byAgent: Record<string, { total: number; passed: number }> = {}
  for (const r of runs) {
    if (!byAgent[r.agent_type]) byAgent[r.agent_type] = { total: 0, passed: 0 }
    byAgent[r.agent_type].total++
    if (r.passed) byAgent[r.agent_type].passed++
  }

  // Show newest on the right (reverse chronological order → oldest first)
  const sortedRuns = [...runs].reverse()

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <span className="font-medium">{data.total_count} total runs</span>
        {Object.entries(byAgent).map(([agent, stats]) => (
          <span key={agent}>
            {agent}: {stats.passed}/{stats.total} passed
          </span>
        ))}
      </div>
      <div className="flex gap-0.5 flex-wrap">
        {sortedRuns.map((run) => (
          <div
            key={run.id}
            className={`w-3 h-3 rounded-sm ${
              run.passed
                ? 'bg-green-500 hover:bg-green-400'
                : 'bg-red-500 hover:bg-red-400'
            } transition-colors cursor-default`}
            title={`${run.passed ? 'Pass' : 'Fail'} | ${run.agent_type} | ${new Date(run.completed_at).toLocaleString()}`}
          />
        ))}
      </div>
      <div className="flex gap-3 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <div className="w-2.5 h-2.5 rounded-sm bg-green-500" /> Pass
        </span>
        <span className="flex items-center gap-1">
          <div className="w-2.5 h-2.5 rounded-sm bg-red-500" /> Fail
        </span>
        <span className="ml-auto">oldest → newest</span>
      </div>
    </div>
  )
}
