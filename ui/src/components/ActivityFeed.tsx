import { Activity } from 'lucide-react'
import { AgentAvatar } from './AgentAvatar'
import type { AgentMascot } from '../lib/types'
import { AVATAR_COLORS } from './mascotData'
import { Card, CardContent } from '@/components/ui/card'

interface ActivityItem {
  agentName: string
  thought: string
  timestamp: string
  featureId: number
}

interface ActivityFeedProps {
  activities: ActivityItem[]
  maxItems?: number
  showHeader?: boolean
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSec = Math.floor(diffMs / 1000)

  if (diffSec < 5) return 'just now'
  if (diffSec < 60) return `${diffSec}s ago`
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export function ActivityFeed({ activities, maxItems = 5, showHeader = true }: ActivityFeedProps) {
  const displayedActivities = activities.slice(0, maxItems)

  if (displayedActivities.length === 0) {
    return null
  }

  return (
    <div>
      {showHeader && (
        <div className="flex items-center gap-2 mb-2">
          <Activity size={14} className="text-muted-foreground" />
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            Recent Activity
          </span>
        </div>
      )}

      <div className="space-y-2">
        {displayedActivities.map((activity) => (
          <Card
            key={`${activity.featureId}-${activity.timestamp}-${activity.thought.slice(0, 20)}`}
            className="py-1.5"
          >
            <CardContent className="p-2 flex items-start gap-2">
              <AgentAvatar
                name={activity.agentName as AgentMascot}
                state="working"
                size="sm"
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold" style={{
                    color: getMascotColor(activity.agentName as AgentMascot)
                  }}>
                    {activity.agentName}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    #{activity.featureId}
                  </span>
                  <span className="text-[10px] text-muted-foreground ml-auto">
                    {formatTimestamp(activity.timestamp)}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground truncate" title={activity.thought}>
                  {activity.thought}
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

function getMascotColor(name: AgentMascot): string {
  const palette = AVATAR_COLORS[name]
  return palette ? palette.primary : '#6B7280'
}
