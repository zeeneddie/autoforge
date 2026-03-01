import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Plus, FolderOpen, Loader2, Trash2 } from 'lucide-react'
import type { ProjectSummary } from '../lib/types'
import { NewProjectModal } from './NewProjectModal'
import { ConfirmDialog } from './ConfirmDialog'
import { useDeleteProject } from '../hooks/useProjects'
import { Badge } from '@/components/ui/badge'

interface ProjectSelectorProps {
  projects: ProjectSummary[]
  selectedProject: string | null
  onSelectProject: (name: string | null) => void
  isLoading: boolean
  onSpecCreatingChange?: (isCreating: boolean) => void
}

export function ProjectSelector({
  projects,
  selectedProject,
  onSelectProject,
  isLoading,
  onSpecCreatingChange,
}: ProjectSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [showNewProjectModal, setShowNewProjectModal] = useState(false)
  const [projectToDelete, setProjectToDelete] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const deleteProject = useDeleteProject()

  // Close dropdown on outside click
  useEffect(() => {
    if (!isOpen) return
    const handleClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [isOpen])

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false)
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [isOpen])

  const handleProjectCreated = (projectName: string) => {
    onSelectProject(projectName)
    setIsOpen(false)
  }

  const handleDeleteClick = (e: React.MouseEvent, projectName: string) => {
    e.stopPropagation()
    e.preventDefault()
    setProjectToDelete(projectName)
  }

  const handleConfirmDelete = async () => {
    if (!projectToDelete) return

    try {
      await deleteProject.mutateAsync(projectToDelete)
      if (selectedProject === projectToDelete) {
        onSelectProject(null)
      }
      setProjectToDelete(null)
    } catch (error) {
      console.error('Failed to delete project:', error)
      setProjectToDelete(null)
    }
  }

  const handleCancelDelete = () => {
    setProjectToDelete(null)
  }

  const selectedProjectData = projects.find(p => p.name === selectedProject)

  return (
    <div className="relative" ref={containerRef}>
      {/* Trigger button */}
      <button
        type="button"
        className="inline-flex min-w-[200px] items-center justify-between gap-2 rounded-md border bg-background px-4 py-2 text-sm font-medium shadow-xs hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50 dark:bg-input/30 dark:border-input dark:hover:bg-input/50"
        disabled={isLoading}
        onClick={() => setIsOpen(!isOpen)}
      >
        {isLoading ? (
          <Loader2 size={18} className="animate-spin" />
        ) : selectedProject ? (
          <>
            <span className="flex items-center gap-2">
              <FolderOpen size={18} />
              {selectedProject}
            </span>
            {selectedProjectData && selectedProjectData.stats.total > 0 && (
              <Badge className="ml-2">{selectedProjectData.stats.percentage}%</Badge>
            )}
          </>
        ) : (
          <span className="text-muted-foreground">Select Project</span>
        )}
        <ChevronDown size={18} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown panel */}
      {isOpen && (
        <div className="absolute left-0 top-full z-50 mt-1 w-[280px] overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md animate-in fade-in-0 zoom-in-95 slide-in-from-top-2">
          {projects.length > 0 ? (
            <div className="max-h-[300px] overflow-y-auto p-1">
              {projects.map(project => (
                <div
                  key={project.name}
                  className={`flex items-center justify-between cursor-pointer rounded-sm px-2 py-1.5 text-sm outline-hidden select-none hover:bg-accent hover:text-accent-foreground ${
                    project.name === selectedProject ? 'bg-primary/10' : ''
                  }`}
                  onClick={() => {
                    onSelectProject(project.name)
                    setIsOpen(false)
                  }}
                >
                  <span className="flex items-center gap-2 flex-1">
                    <FolderOpen size={16} />
                    {project.name}
                    {project.stats.total > 0 && (
                      <span className="text-sm font-mono text-muted-foreground ml-auto">
                        {project.stats.passing}/{project.stats.total}
                      </span>
                    )}
                  </span>
                  <button
                    type="button"
                    onClick={(e: React.MouseEvent) => handleDeleteClick(e, project.name)}
                    className="inline-flex items-center justify-center rounded-sm p-1 text-muted-foreground hover:text-destructive hover:bg-accent"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 text-center text-muted-foreground">
              No projects yet
            </div>
          )}

          <div className="bg-border h-px" />

          <div className="p-1">
            <div
              className="flex items-center gap-2 cursor-pointer rounded-sm px-2 py-1.5 text-sm font-semibold outline-hidden select-none hover:bg-accent hover:text-accent-foreground"
              onClick={() => {
                setShowNewProjectModal(true)
                setIsOpen(false)
              }}
            >
              <Plus size={16} />
              New Project
            </div>
          </div>
        </div>
      )}

      {/* New Project Modal */}
      <NewProjectModal
        isOpen={showNewProjectModal}
        onClose={() => setShowNewProjectModal(false)}
        onProjectCreated={handleProjectCreated}
        onStepChange={(step) => onSpecCreatingChange?.(step === 'chat')}
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={projectToDelete !== null}
        title="Delete Project"
        message={`Are you sure you want to remove "${projectToDelete}" from the registry? This will unregister the project but preserve its files on disk.`}
        confirmLabel="Delete"
        cancelLabel="Cancel"
        variant="danger"
        isLoading={deleteProject.isPending}
        onConfirm={handleConfirmDelete}
        onCancel={handleCancelDelete}
      />
    </div>
  )
}
