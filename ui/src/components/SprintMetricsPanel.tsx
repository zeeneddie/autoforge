import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { usePlaneSyncStatus, useTestReport } from '../hooks/useProjects'
import { Trophy, Activity, Zap, AlertCircle } from 'lucide-react'

interface SprintMetricsPanelProps {
  projectName: string
}

export function SprintMetricsPanel({ projectName }: SprintMetricsPanelProps) {
  const { data: syncStatus, isLoading: syncLoading } = usePlaneSyncStatus()
  const { data: report, isLoading: reportLoading } = useTestReport(projectName, true)

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
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-muted-foreground">Features Passing</span>
                      <span className="font-medium">{stats.passing} / {stats.total}</span>
                    </div>
                    <div className="h-3 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-green-500 rounded-full transition-all"
                        style={{
                          width: stats.total > 0 ? `${(stats.passing / stats.total) * 100}%` : '0%',
                        }}
                      />
                    </div>
                  </div>
                  {stats.failed > 0 && (
                    <div className="flex items-center gap-2 text-sm text-red-600">
                      <AlertCircle size={14} />
                      {stats.failed} feature{stats.failed !== 1 ? 's' : ''} failing
                    </div>
                  )}
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
              No active sprint. Import a Plane cycle to track sprint progress.
            </div>
          )}
        </CardContent>
      </Card>

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
