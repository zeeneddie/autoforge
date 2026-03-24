import { useState } from 'react'
import { ChevronDown, Check, Loader2, Layers } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { usePlanningCycles, useImportPlanningCycle, usePlanningConfig } from '../hooks/useProjects'

export function SprintSwitchButton({ projectName }: { projectName: string }) {
  const [open, setOpen] = useState(false)
  const { data: cycles, refetch, isFetching } = usePlanningCycles(projectName)
  const { data: config } = usePlanningConfig(projectName)
  const importCycle = useImportPlanningCycle()

  // Only show sprints with dates set (= klaar gezet in mq-planning)
  const readyCycles = (cycles ?? []).filter(c => c.start_date !== null)
  const activeCycleId = config?.planning_active_cycle_id
  const activeCycle = readyCycles.find(c => c.id === activeCycleId)

  const handleOpen = (isOpen: boolean) => {
    setOpen(isOpen)
    if (isOpen) refetch()
  }

  const handleImport = (cycleId: string) => {
    importCycle.mutate({ cycleId, projectName }, {
      onSuccess: () => setOpen(false),
    })
  }

  return (
    <Popover open={open} onOpenChange={handleOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="gap-1.5">
          <Layers size={15} />
          {activeCycle?.name ?? 'Sprint wisselen'}
          <ChevronDown size={13} className="text-muted-foreground" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-72 p-2" align="end">
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
      </PopoverContent>
    </Popover>
  )
}
