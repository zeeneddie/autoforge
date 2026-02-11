import { LayoutGrid, GitBranch, BarChart3 } from 'lucide-react'
import { Button } from '@/components/ui/button'

export type ViewMode = 'kanban' | 'graph' | 'analytics'

interface ViewToggleProps {
  viewMode: ViewMode
  onViewModeChange: (mode: ViewMode) => void
}

/**
 * Toggle button to switch between Kanban, Graph, and Analytics views
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
