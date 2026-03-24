import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Check, Loader2, Layers } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { usePlanningCycles, useImportPlanningCycle, usePlanningConfig } from '../hooks/useProjects'

export function SprintSwitchButton({ projectName }: { projectName: string }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const { data: cycles, refetch, isFetching } = usePlanningCycles(projectName)
  const { data: config } = usePlanningConfig(projectName)
  const importCycle = useImportPlanningCycle()

  // Only show sprints with dates set (= klaar gezet in mq-planning)
  const readyCycles = (cycles ?? []).filter(c => c.start_date !== null)
  const activeCycleId = config?.planning_active_cycle_id
  const activeCycle = readyCycles.find(c => c.id === activeCycleId)

  // Close on outside click
  useEffect(() => {
    if (!open) return
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  const handleToggle = () => {
    const next = !open
    setOpen(next)
    if (next) refetch()
  }

  const handleImport = (cycleId: string) => {
    importCycle.mutate({ cycleId, projectName }, {
      onSuccess: () => setOpen(false),
    })
  }

  return (
    <div ref={ref} className="relative">
      <Button variant="outline" size="sm" className="gap-1.5" onClick={handleToggle}>
        <Layers size={15} />
        <span className="max-w-32 truncate">{activeCycle?.name ?? 'Sprint wisselen'}</span>
        <ChevronDown size={13} className="text-muted-foreground shrink-0" />
      </Button>

      {open && (
        <div className="absolute right-0 top-full mt-1 z-50 w-72 rounded-md border bg-card shadow-md p-2">
          {isFetching ? (
            <div className="flex justify-center py-4">
              <Loader2 size={18} className="animate-spin text-muted-foreground" />
            </div>
          ) : readyCycles.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-4 px-2">
              Geen sprints klaar gezet.<br />
              Stel datums in op een sprint in mq-planning.
            </p>
          ) : (
            <div className="space-y-0.5">
              {readyCycles.map(cycle => {
                const isActive = cycle.id === activeCycleId
                const isLoading = importCycle.isPending && (importCycle.variables as { cycleId: string } | undefined)?.cycleId === cycle.id
                return (
                  <button
                    key={cycle.id}
                    onClick={() => handleImport(cycle.id)}
                    disabled={importCycle.isPending}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-sm hover:bg-muted transition-colors text-left disabled:opacity-60 ${isActive ? 'bg-primary/5' : ''}`}
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5 font-medium">
                        {isActive && <Check size={13} className="text-primary shrink-0" />}
                        <span className="truncate">{cycle.name}</span>
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {cycle.completed_issues}/{cycle.total_issues} items
                        {cycle.start_date && ` · ${cycle.start_date.slice(0, 10)}`}
                      </div>
                    </div>
                    {isLoading && <Loader2 size={14} className="animate-spin text-primary shrink-0 ml-2" />}
                  </button>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
