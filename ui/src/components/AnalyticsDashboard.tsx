import { useState } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ClipboardList, Activity, FileText } from 'lucide-react'
import { TestReportPanel } from './TestReportPanel'
import { SprintMetricsPanel } from './SprintMetricsPanel'
import { ReleaseNotesViewer } from './ReleaseNotesViewer'

type AnalyticsTab = 'test-report' | 'sprint-metrics' | 'release-notes'

interface AnalyticsDashboardProps {
  projectName: string
}

export function AnalyticsDashboard({ projectName }: AnalyticsDashboardProps) {
  const [activeTab, setActiveTab] = useState<AnalyticsTab>('test-report')

  const tabs: { id: AnalyticsTab; label: string; icon: typeof ClipboardList }[] = [
    { id: 'test-report', label: 'Test Report', icon: ClipboardList },
    { id: 'sprint-metrics', label: 'Sprint Metrics', icon: Activity },
    { id: 'release-notes', label: 'Release Notes', icon: FileText },
  ]

  return (
    <div className="space-y-4">
      {/* Tab bar */}
      <Card className="p-1">
        <div className="flex gap-1">
          {tabs.map(({ id, label, icon: Icon }) => (
            <Button
              key={id}
              variant={activeTab === id ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setActiveTab(id)}
              className="flex-1"
            >
              <Icon size={16} className="mr-1.5" />
              {label}
            </Button>
          ))}
        </div>
      </Card>

      {/* Tab content */}
      {activeTab === 'test-report' && <TestReportPanel projectName={projectName} />}
      {activeTab === 'sprint-metrics' && <SprintMetricsPanel projectName={projectName} />}
      {activeTab === 'release-notes' && <ReleaseNotesViewer projectName={projectName} />}
    </div>
  )
}
