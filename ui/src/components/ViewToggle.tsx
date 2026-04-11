import { LayoutGrid, GitBranch, BarChart3, Target } from 'lucide-react'
import { Button } from '@/components/ui/button'

// Sprint 1 Blok E task 1.15 (2026-04-11): added 'goals' view for AC + tool-call drilldown
export type ViewMode = 'kanban' | 'graph' | 'analytics' | 'goals'

interface ViewToggleProps {
  viewMode: ViewMode
  onViewModeChange: (mode: ViewMode) => void
}

/**
 * Toggle button to switch between Kanban, Graph, Analytics, and Goals views
 */
export function ViewToggle({ viewMode, onViewModeChange }: ViewToggleProps) {
  return (
    <div className="inline-flex rounded-lg border p-1 bg-background">
      <Button
        variant={viewMode === 'kanban' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => onViewModeChange('kanban')}
        title="Kanban View"
      >
        <LayoutGrid size={16} />
        Kanban
      </Button>
      <Button
        variant={viewMode === 'goals' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => onViewModeChange('goals')}
        title="Goals View — AC + tool-call drilldown (Sprint 1 Blok E)"
      >
        <Target size={16} />
        Goals
      </Button>
      <Button
        variant={viewMode === 'graph' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => onViewModeChange('graph')}
        title="Dependency Graph View"
      >
        <GitBranch size={16} />
        Graph
      </Button>
      <Button
        variant={viewMode === 'analytics' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => onViewModeChange('analytics')}
        title="Analytics Dashboard (I)"
      >
        <BarChart3 size={16} />
        Analytics
      </Button>
    </div>
  )
}
