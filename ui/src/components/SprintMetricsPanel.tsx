import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { usePlanningSyncStatus, useTestReport, useBurndown } from '../hooks/useProjects'
import { Trophy, Activity, Zap, AlertCircle, Clock, Ban, TrendingDown } from 'lucide-react'
import { BurndownChart } from './BurndownChart'

interface SprintMetricsPanelProps {
  projectName: string
}

export function SprintMetricsPanel({ projectName }: SprintMetricsPanelProps) {
  const { data: syncStatus, isLoading: syncLoading } = usePlanningSyncStatus()
  const { data: report, isLoading: reportLoading } = useTestReport(projectName, true)
  const { data: burndown } = useBurndown(projectName)

  if (syncLoading || reportLoading) {
    return (
      <Card className="p-8 text-center">
        <div className="animate-pulse text-muted-foreground">Loading sprint metrics...</div>
      </Card>
    )
  }

  const stats = syncStatus?.sprint_stats
  const cycleName = syncStatus?.active_cycle_name

  return (
    <div className="space-y-4">
      {/* Sprint Progress */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Trophy size={18} className="text-yellow-500" />
              Sprint Progress
            </CardTitle>
            {syncStatus?.sprint_complete && (
              <Badge className="bg-green-500/15 text-green-600 border-green-500/30">
                Complete
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {cycleName ? (
            <div className="space-y-4">
              <div>
                <div className="text-sm text-muted-foreground mb-1">Sprint</div>
                <div className="font-bold text-lg">{cycleName}</div>
              </div>
              {stats && (
                <>
                  {/* Stacked progress bar: Done | In Progress | Blocked | Pending */}
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-muted-foreground">Sprint voortgang</span>
                      <span className="font-medium">{stats.passing} / {stats.total} klaar</span>
                    </div>
                    <div className="h-3 bg-muted rounded-full overflow-hidden flex">
                      {stats.total > 0 && (
                        <>
                          <div
                            className="h-full bg-green-500 transition-all"
                            style={{ width: `${(stats.passing / stats.total) * 100}%` }}
                            title={`${stats.passing} passing`}
                          />
                          <div
                            className="h-full bg-primary/70 transition-all"
                            style={{ width: `${((stats.in_progress ?? 0) / stats.total) * 100}%` }}
                            title={`${stats.in_progress ?? 0} in progress`}
                          />
                          <div
                            className="h-full bg-orange-400 transition-all"
                            style={{ width: `${((stats.blocked ?? 0) / stats.total) * 100}%` }}
                            title={`${stats.blocked ?? 0} blocked`}
                          />
                        </>
                      )}
                    </div>
                    {/* Legend */}
                    <div className="flex gap-3 mt-1.5 text-[10px] text-muted-foreground">
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500 inline-block" />{stats.passing} klaar</span>
                      {(stats.in_progress ?? 0) > 0 && <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-primary/70 inline-block" />{stats.in_progress} actief</span>}
                      {(stats.blocked ?? 0) > 0 && <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-400 inline-block" />{stats.blocked} geblokkeerd</span>}
                    </div>
                  </div>
                  {/* Alert badges */}
                  <div className="flex flex-wrap gap-2">
                    {stats.failed > 0 && (
                      <div className="flex items-center gap-1.5 text-sm text-red-600">
                        <AlertCircle size={14} />
                        {stats.failed} failing
                      </div>
                    )}
                    {(stats.in_progress ?? 0) > 0 && (
                      <div className="flex items-center gap-1.5 text-sm text-primary">
                        <Clock size={14} />
                        {stats.in_progress} in progress
                      </div>
                    )}
                    {(stats.blocked ?? 0) > 0 && (
                      <div className="flex items-center gap-1.5 text-sm text-orange-600">
                        <Ban size={14} />
                        {stats.blocked} geblokkeerd
                      </div>
                    )}
                  </div>
                </>
              )}
              {!stats && (
                <div className="text-sm text-muted-foreground">
                  Enable sync to see sprint progress.
                </div>
              )}
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">
              No active sprint. Import a planning cycle to track sprint progress.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Burn-down Chart */}
      {burndown && (burndown.points.length > 0 || burndown.total > 0) && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <TrendingDown size={18} className="text-blue-500" />
                Burn-down
              </CardTitle>
              {burndown.sprint_name && (
                <span className="text-xs text-muted-foreground">{burndown.sprint_name}</span>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <BurndownChart points={burndown.points} total={burndown.total} />
          </CardContent>
        </Card>
      )}

      {/* Test Activity */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Activity size={18} className="text-blue-500" />
            Test Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          {report && report.total_test_runs > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <MetricItem label="Overall Pass Rate" value={`${report.overall_pass_rate}%`} />
              <MetricItem label="Total Test Runs" value={report.total_test_runs} />
              <MetricItem label="Features Tested" value={`${report.features_tested} / ${report.total_features}`} />
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">
              No test runs recorded yet.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Feature Velocity */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Zap size={18} className="text-orange-500" />
            Feature Velocity
          </CardTitle>
        </CardHeader>
        <CardContent>
          {report && report.total_features > 0 ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <MetricItem label="Tested" value={report.features_tested} />
                <MetricItem label="Untested" value={report.features_never_tested} />
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-muted-foreground">Test Coverage</span>
                  <span className="font-medium">
                    {report.total_features > 0
                      ? Math.round((report.features_tested / report.total_features) * 100)
                      : 0}%
                  </span>
                </div>
                <div className="h-3 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full transition-all"
                    style={{
                      width: report.total_features > 0
                        ? `${(report.features_tested / report.total_features) * 100}%`
                        : '0%',
                    }}
                  />
                </div>
              </div>
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">
              No features found.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Sync Status */}
      {syncStatus && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Sync Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="text-muted-foreground mb-0.5">Status</div>
                <Badge variant={syncStatus.enabled ? 'default' : 'outline'}>
                  {syncStatus.enabled ? 'Enabled' : 'Disabled'}
                </Badge>
              </div>
              <div>
                <div className="text-muted-foreground mb-0.5">Items Synced</div>
                <div className="font-medium">{syncStatus.items_synced}</div>
              </div>
              <div>
                <div className="text-muted-foreground mb-0.5">Webhooks</div>
                <div className="font-medium">{syncStatus.webhook_count}</div>
              </div>
              <div>
                <div className="text-muted-foreground mb-0.5">Last Sync</div>
                <div className="font-medium text-xs">
                  {syncStatus.last_sync_at
                    ? new Date(syncStatus.last_sync_at).toLocaleString()
                    : 'Never'}
                </div>
              </div>
            </div>
            {syncStatus.last_error && (
              <div className="mt-3 text-sm text-red-600 bg-red-50 dark:bg-red-950/30 rounded p-2">
                {syncStatus.last_error}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function MetricItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="text-xs text-muted-foreground mb-0.5">{label}</div>
      <div className="text-xl font-bold">{value}</div>
    </div>
  )
}
