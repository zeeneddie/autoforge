import { useState } from 'react'
import { Loader2, AlertCircle, Check, Moon, Sun, ChevronDown, ChevronRight } from 'lucide-react'
import { useSettings, useUpdateSettings, useAvailableModels, usePlaneConfig, useUpdatePlaneConfig, useTestPlaneConnection, usePlaneCycles, useImportPlaneCycle, usePlaneSyncStatus, useTogglePlaneSync, useCompleteSprint } from '../hooks/useProjects'
import { useTheme, THEMES } from '../hooks/useTheme'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import type { ModelInfo, PlaneConnectionResult, PlaneCycleSummary, SprintCompletionResult } from '../lib/types'

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

/** Reusable model selector with Default, known models, and Custom input. */
function ModelSelector({
  label,
  description,
  value,
  models,
  disabled,
  onChange,
}: {
  label: string
  description: string
  value: string | null | undefined
  models: ModelInfo[]
  disabled: boolean
  onChange: (value: string) => void
}) {
  const [showCustom, setShowCustom] = useState(false)
  const [customValue, setCustomValue] = useState('')

  // Determine active selection: null/empty = "Default", known model ID, or custom
  const isDefault = !value
  const isKnownModel = !isDefault && models.some((m) => m.id === value)
  const isCustom = !isDefault && !isKnownModel

  // Initialize custom input if current value is custom
  const displayCustomValue = isCustom ? (value ?? '') : customValue

  return (
    <div className="space-y-2">
      <Label className="font-medium">{label}</Label>
      <p className="text-sm text-muted-foreground">{description}</p>
      <div className="flex rounded-lg border overflow-hidden">
        {/* Default button */}
        <button
          onClick={() => {
            setShowCustom(false)
            onChange('')
          }}
          disabled={disabled}
          className={`py-2 px-3 text-sm font-medium transition-colors ${
            isDefault
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-foreground hover:bg-muted'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          Default
        </button>
        {/* Known model buttons */}
        {models.map((model) => (
          <button
            key={model.id}
            onClick={() => {
              setShowCustom(false)
              onChange(model.id)
            }}
            disabled={disabled}
            className={`flex-1 py-2 px-3 text-sm font-medium transition-colors ${
              value === model.id
                ? 'bg-primary text-primary-foreground'
                : 'bg-background text-foreground hover:bg-muted'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {model.name}
          </button>
        ))}
        {/* Custom button */}
        <button
          onClick={() => setShowCustom(true)}
          disabled={disabled}
          className={`py-2 px-3 text-sm font-medium transition-colors ${
            isCustom || (showCustom && isDefault)
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-foreground hover:bg-muted'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          Custom
        </button>
      </div>
      {/* Custom model input */}
      {(showCustom || isCustom) && (
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="e.g. openai/gpt-4o"
            value={displayCustomValue}
            onChange={(e) => setCustomValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && customValue.trim()) {
                onChange(customValue.trim())
              }
            }}
            disabled={disabled}
            className="flex-1 px-3 py-1.5 text-sm rounded-md border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
          <Button
            size="sm"
            variant="outline"
            disabled={disabled || !customValue.trim()}
            onClick={() => {
              if (customValue.trim()) {
                onChange(customValue.trim())
              }
            }}
          >
            Apply
          </Button>
        </div>
      )}
    </div>
  )
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const { data: settings, isLoading, isError, refetch } = useSettings()
  const { data: modelsData } = useAvailableModels()
  const updateSettings = useUpdateSettings()
  const { theme, setTheme, darkMode, toggleDarkMode } = useTheme()

  const handleYoloToggle = () => {
    if (settings && !updateSettings.isPending) {
      updateSettings.mutate({ yolo_mode: !settings.yolo_mode })
    }
  }

  const handleModelChange = (modelId: string) => {
    if (!updateSettings.isPending) {
      updateSettings.mutate({ model: modelId })
    }
  }

  const handleTestingRatioChange = (ratio: number) => {
    if (!updateSettings.isPending) {
      updateSettings.mutate({ testing_agent_ratio: ratio })
    }
  }

  const handleBatchSizeChange = (size: number) => {
    if (!updateSettings.isPending) {
      updateSettings.mutate({ batch_size: size })
    }
  }

  const models = modelsData?.models ?? []
  const isSaving = updateSettings.isPending

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Settings
            {isSaving && <Loader2 className="animate-spin" size={16} />}
          </DialogTitle>
        </DialogHeader>

        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="animate-spin" size={24} />
            <span className="ml-2">Loading settings...</span>
          </div>
        )}

        {/* Error State */}
        {isError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Failed to load settings
              <Button
                variant="link"
                onClick={() => refetch()}
                className="ml-2 p-0 h-auto"
              >
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {/* Settings Content */}
        {settings && !isLoading && (
          <div className="space-y-6">
            {/* Theme Selection */}
            <div className="space-y-3">
              <Label className="font-medium">Theme</Label>
              <div className="grid gap-2">
                {THEMES.map((themeOption) => (
                  <button
                    key={themeOption.id}
                    onClick={() => setTheme(themeOption.id)}
                    className={`flex items-center gap-3 p-3 rounded-lg border-2 transition-colors text-left ${
                      theme === themeOption.id
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50 hover:bg-muted/50'
                    }`}
                  >
                    {/* Color swatches */}
                    <div className="flex gap-0.5 shrink-0">
                      <div
                        className="w-5 h-5 rounded-sm border border-border/50"
                        style={{ backgroundColor: themeOption.previewColors.background }}
                      />
                      <div
                        className="w-5 h-5 rounded-sm border border-border/50"
                        style={{ backgroundColor: themeOption.previewColors.primary }}
                      />
                      <div
                        className="w-5 h-5 rounded-sm border border-border/50"
                        style={{ backgroundColor: themeOption.previewColors.accent }}
                      />
                    </div>

                    {/* Theme info */}
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm">{themeOption.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {themeOption.description}
                      </div>
                    </div>

                    {/* Checkmark */}
                    {theme === themeOption.id && (
                      <Check size={18} className="text-primary shrink-0" />
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Dark Mode Toggle */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="dark-mode" className="font-medium">
                  Dark Mode
                </Label>
                <p className="text-sm text-muted-foreground">
                  Switch between light and dark appearance
                </p>
              </div>
              <Button
                id="dark-mode"
                variant="outline"
                size="sm"
                onClick={toggleDarkMode}
                className="gap-2"
              >
                {darkMode ? <Sun size={16} /> : <Moon size={16} />}
                {darkMode ? 'Light' : 'Dark'}
              </Button>
            </div>

            <hr className="border-border" />

            {/* YOLO Mode Toggle */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="yolo-mode" className="font-medium">
                  YOLO Mode
                </Label>
                <p className="text-sm text-muted-foreground">
                  Skip testing for rapid prototyping
                </p>
              </div>
              <Switch
                id="yolo-mode"
                checked={settings.yolo_mode}
                onCheckedChange={handleYoloToggle}
                disabled={isSaving}
              />
            </div>

            {/* Headless Browser Toggle */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="playwright-headless" className="font-medium">
                  Headless Browser
                </Label>
                <p className="text-sm text-muted-foreground">
                  Run browser without visible window (saves CPU)
                </p>
              </div>
              <Switch
                id="playwright-headless"
                checked={settings.playwright_headless}
                onCheckedChange={() => updateSettings.mutate({ playwright_headless: !settings.playwright_headless })}
                disabled={isSaving}
              />
            </div>

            {/* Default Model Selection */}
            <div className="space-y-2">
              <Label className="font-medium">Default Model</Label>
              <p className="text-sm text-muted-foreground">
                Fallback model used when no per-type override is set
              </p>
              <div className="flex rounded-lg border overflow-hidden">
                {models.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => handleModelChange(model.id)}
                    disabled={isSaving}
                    className={`flex-1 py-2 px-3 text-sm font-medium transition-colors ${
                      settings.model === model.id
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-background text-foreground hover:bg-muted'
                    } ${isSaving ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    {model.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Per-Type Model Selectors */}
            <ModelSelector
              label="Initializer Model"
              description="Model for creating features from app spec"
              value={settings.model_initializer}
              models={models}
              disabled={isSaving}
              onChange={(v) => updateSettings.mutate({ model_initializer: v || null })}
            />

            <ModelSelector
              label="Coding Model"
              description="Model for implementing features"
              value={settings.model_coding}
              models={models}
              disabled={isSaving}
              onChange={(v) => updateSettings.mutate({ model_coding: v || null })}
            />

            <ModelSelector
              label="Testing Model"
              description="Model for regression testing"
              value={settings.model_testing}
              models={models}
              disabled={isSaving}
              onChange={(v) => updateSettings.mutate({ model_testing: v || null })}
            />

            {/* Regression Agents */}
            <div className="space-y-2">
              <Label className="font-medium">Regression Agents</Label>
              <p className="text-sm text-muted-foreground">
                Number of regression testing agents (0 = disabled)
              </p>
              <div className="flex rounded-lg border overflow-hidden">
                {[0, 1, 2, 3].map((ratio) => (
                  <button
                    key={ratio}
                    onClick={() => handleTestingRatioChange(ratio)}
                    disabled={isSaving}
                    className={`flex-1 py-2 px-3 text-sm font-medium transition-colors ${
                      settings.testing_agent_ratio === ratio
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-background text-foreground hover:bg-muted'
                    } ${isSaving ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    {ratio}
                  </button>
                ))}
              </div>
            </div>

            {/* Features per Agent */}
            <div className="space-y-2">
              <Label className="font-medium">Features per Agent</Label>
              <p className="text-sm text-muted-foreground">
                Number of features assigned to each coding agent
              </p>
              <div className="flex rounded-lg border overflow-hidden">
                {[1, 2, 3].map((size) => (
                  <button
                    key={size}
                    onClick={() => handleBatchSizeChange(size)}
                    disabled={isSaving}
                    className={`flex-1 py-2 px-3 text-sm font-medium transition-colors ${
                      (settings.batch_size ?? 1) === size
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-background text-foreground hover:bg-muted'
                    } ${isSaving ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    {size}
                  </button>
                ))}
              </div>
            </div>

            {/* Update Error */}
            {updateSettings.isError && (
              <Alert variant="destructive">
                <AlertDescription>
                  Failed to save settings. Please try again.
                </AlertDescription>
              </Alert>
            )}

            <hr className="border-border" />

            {/* Plane Integration Section */}
            <PlaneSettingsSection />
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

/** Collapsible Plane integration settings section. */
function PlaneSettingsSection() {
  const [expanded, setExpanded] = useState(false)
  const { data: planeConfig, isLoading } = usePlaneConfig()
  const updateConfig = useUpdatePlaneConfig()
  const testConnection = useTestPlaneConnection()
  const { data: cycles, refetch: fetchCycles, isFetching: cyclesLoading } = usePlaneCycles()
  const importCycle = useImportPlaneCycle()
  const { data: syncStatus } = usePlaneSyncStatus()
  const toggleSync = useTogglePlaneSync()
  const completeSprint = useCompleteSprint()
  const [completionResult, setCompletionResult] = useState<SprintCompletionResult | null>(null)

  const [formValues, setFormValues] = useState({
    plane_api_url: '',
    plane_api_key: '',
    plane_workspace_slug: '',
    plane_project_id: '',
    plane_webhook_secret: '',
  })
  const [formDirty, setFormDirty] = useState(false)
  const [connectionResult, setConnectionResult] = useState<PlaneConnectionResult | null>(null)
  const [importResult, setImportResult] = useState<{ imported: number; updated: number; skipped: number } | null>(null)

  // Initialize form values from config
  const initForm = () => {
    if (planeConfig && !formDirty) {
      setFormValues({
        plane_api_url: planeConfig.plane_api_url || '',
        plane_api_key: '',
        plane_workspace_slug: planeConfig.plane_workspace_slug || '',
        plane_project_id: planeConfig.plane_project_id || '',
      })
    }
  }

  const handleToggle = () => {
    if (!expanded) initForm()
    setExpanded(!expanded)
  }

  const handleFieldChange = (field: string, value: string) => {
    setFormValues((prev) => ({ ...prev, [field]: value }))
    setFormDirty(true)
  }

  const handleSave = () => {
    const update: Record<string, string> = {}
    if (formValues.plane_api_url) update.plane_api_url = formValues.plane_api_url
    if (formValues.plane_api_key) update.plane_api_key = formValues.plane_api_key
    if (formValues.plane_workspace_slug) update.plane_workspace_slug = formValues.plane_workspace_slug
    if (formValues.plane_project_id) update.plane_project_id = formValues.plane_project_id
    if (formValues.plane_webhook_secret) update.plane_webhook_secret = formValues.plane_webhook_secret

    updateConfig.mutate(update, {
      onSuccess: () => {
        setFormDirty(false)
        setConnectionResult(null)
      },
    })
  }

  const handleTestConnection = () => {
    setConnectionResult(null)
    testConnection.mutate(undefined, {
      onSuccess: (result) => setConnectionResult(result),
    })
  }

  const handleFetchCycles = () => {
    fetchCycles()
  }

  const handleImport = (cycle: PlaneCycleSummary) => {
    // For now, use a prompt or the first project. In a real app, this would come from context.
    const projectName = prompt('Project name to import into:')
    if (!projectName) return

    setImportResult(null)
    importCycle.mutate(
      { cycleId: cycle.id, projectName },
      {
        onSuccess: (result) => {
          setImportResult({
            imported: result.imported,
            updated: result.updated,
            skipped: result.skipped,
          })
        },
      },
    )
  }

  const isSaving = updateConfig.isPending

  return (
    <div className="space-y-3">
      <button
        onClick={handleToggle}
        className="flex items-center gap-2 w-full text-left"
      >
        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        <Label className="font-medium cursor-pointer">Plane Integration</Label>
        {planeConfig?.plane_api_key_set && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/10 text-green-600">
            Connected
          </span>
        )}
      </button>

      {expanded && (
        <div className="space-y-4 pl-6">
          {isLoading ? (
            <div className="flex items-center gap-2 py-4">
              <Loader2 className="animate-spin" size={16} />
              <span className="text-sm text-muted-foreground">Loading...</span>
            </div>
          ) : (
            <>
              {/* API URL */}
              <div className="space-y-1">
                <Label className="text-sm">API URL</Label>
                <input
                  type="text"
                  placeholder="http://localhost:8080"
                  value={formValues.plane_api_url}
                  onChange={(e) => handleFieldChange('plane_api_url', e.target.value)}
                  className="w-full px-3 py-1.5 text-sm rounded-md border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>

              {/* API Key */}
              <div className="space-y-1">
                <Label className="text-sm">API Key</Label>
                <input
                  type="password"
                  placeholder={planeConfig?.plane_api_key_set ? planeConfig.plane_api_key_masked : 'plane_api_xxxx'}
                  value={formValues.plane_api_key}
                  onChange={(e) => handleFieldChange('plane_api_key', e.target.value)}
                  className="w-full px-3 py-1.5 text-sm rounded-md border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>

              {/* Workspace Slug */}
              <div className="space-y-1">
                <Label className="text-sm">Workspace Slug</Label>
                <input
                  type="text"
                  placeholder="my-workspace"
                  value={formValues.plane_workspace_slug}
                  onChange={(e) => handleFieldChange('plane_workspace_slug', e.target.value)}
                  className="w-full px-3 py-1.5 text-sm rounded-md border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>

              {/* Project ID */}
              <div className="space-y-1">
                <Label className="text-sm">Project ID</Label>
                <input
                  type="text"
                  placeholder="project-uuid"
                  value={formValues.plane_project_id}
                  onChange={(e) => handleFieldChange('plane_project_id', e.target.value)}
                  className="w-full px-3 py-1.5 text-sm rounded-md border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>

              {/* Webhook Secret */}
              <div className="space-y-1">
                <Label className="text-sm">Webhook Secret {planeConfig?.plane_webhook_secret_set && <span className="text-xs text-green-600">(set)</span>}</Label>
                <input
                  type="password"
                  placeholder={planeConfig?.plane_webhook_secret_set ? '********' : 'Optional HMAC secret'}
                  value={formValues.plane_webhook_secret || ''}
                  onChange={(e) => handleFieldChange('plane_webhook_secret', e.target.value)}
                  className="w-full px-3 py-1.5 text-sm rounded-md border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
                <p className="text-xs text-muted-foreground">
                  Configure in Plane's webhook settings. URL: <code className="bg-muted px-1 rounded">{'{your-autoforge-url}'}/api/plane/webhooks</code>
                </p>
              </div>

              {/* Save + Test buttons */}
              <div className="flex gap-2">
                <Button
                  size="sm"
                  disabled={!formDirty || isSaving}
                  onClick={handleSave}
                >
                  {isSaving ? <Loader2 className="animate-spin mr-1" size={14} /> : null}
                  Save
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={testConnection.isPending}
                  onClick={handleTestConnection}
                >
                  {testConnection.isPending ? <Loader2 className="animate-spin mr-1" size={14} /> : null}
                  Test Connection
                </Button>
              </div>

              {/* Connection result */}
              {connectionResult && (
                <Alert variant={connectionResult.status === 'ok' ? 'default' : 'destructive'}>
                  <AlertDescription>
                    {connectionResult.status === 'ok' ? (
                      <span className="flex items-center gap-1">
                        <Check size={14} className="text-green-600" />
                        Connected to project "{connectionResult.project_name}" in workspace "{connectionResult.workspace}"
                      </span>
                    ) : (
                      connectionResult.message
                    )}
                  </AlertDescription>
                </Alert>
              )}

              <hr className="border-border" />

              {/* Cycles section */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-sm font-medium">Sprint Cycles</Label>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={cyclesLoading}
                    onClick={handleFetchCycles}
                  >
                    {cyclesLoading ? <Loader2 className="animate-spin mr-1" size={14} /> : null}
                    Load Cycles
                  </Button>
                </div>

                {cycles && cycles.length > 0 && (
                  <div className="space-y-1">
                    {cycles.map((cycle) => (
                      <div
                        key={cycle.id}
                        className="flex items-center justify-between p-2 rounded-md border text-sm"
                      >
                        <div>
                          <span className="font-medium">{cycle.name}</span>
                          {cycle.status && (
                            <span className={`ml-2 text-xs px-1.5 py-0.5 rounded-full ${
                              cycle.status === 'current'
                                ? 'bg-blue-500/10 text-blue-600'
                                : 'bg-muted text-muted-foreground'
                            }`}>
                              {cycle.status}
                            </span>
                          )}
                          <span className="ml-2 text-xs text-muted-foreground">
                            {cycle.completed_issues}/{cycle.total_issues} done
                          </span>
                        </div>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={importCycle.isPending}
                          onClick={() => handleImport(cycle)}
                        >
                          Import
                        </Button>
                      </div>
                    ))}
                  </div>
                )}

                {cycles && cycles.length === 0 && (
                  <p className="text-sm text-muted-foreground">No cycles found in this project.</p>
                )}
              </div>

              {/* Import result */}
              {importResult && (
                <Alert>
                  <AlertDescription>
                    Imported {importResult.imported} features, updated {importResult.updated}, skipped {importResult.skipped}.
                  </AlertDescription>
                </Alert>
              )}

              {importCycle.isError && (
                <Alert variant="destructive">
                  <AlertDescription>
                    Import failed: {importCycle.error?.message || 'Unknown error'}
                  </AlertDescription>
                </Alert>
              )}

              <hr className="border-border" />

              {/* Background Sync */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label className="text-sm font-medium">Background Sync</Label>
                    <p className="text-xs text-muted-foreground">
                      Auto-sync status between AutoForge and Plane
                    </p>
                  </div>
                  <Switch
                    checked={syncStatus?.enabled ?? false}
                    onCheckedChange={() => toggleSync.mutate()}
                    disabled={toggleSync.isPending}
                  />
                </div>

                {syncStatus?.enabled && (
                  <div className="space-y-1 text-xs text-muted-foreground">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${syncStatus.running ? 'bg-green-500 animate-pulse' : 'bg-muted-foreground/30'}`} />
                      <span>{syncStatus.running ? 'Sync active' : 'Sync idle'}</span>
                      {syncStatus.active_cycle_name && (
                        <span className="text-muted-foreground">({syncStatus.active_cycle_name})</span>
                      )}
                    </div>
                    {syncStatus.last_sync_at && (
                      <div>
                        Last sync: {new Date(syncStatus.last_sync_at).toLocaleTimeString()}
                        {syncStatus.items_synced > 0 && ` (${syncStatus.items_synced} items)`}
                      </div>
                    )}
                    {syncStatus.last_error && (
                      <div className="text-destructive">
                        Error: {syncStatus.last_error}
                      </div>
                    )}
                    {syncStatus.webhook_count > 0 && (
                      <div>
                        Webhooks: {syncStatus.webhook_count} received
                        {syncStatus.last_webhook_at && ` (last: ${new Date(syncStatus.last_webhook_at).toLocaleTimeString()})`}
                      </div>
                    )}
                  </div>
                )}
              </div>

              <hr className="border-border" />

              {/* Sprint Completion */}
              <div className="space-y-3">
                <Label className="text-sm font-medium">Sprint Completion</Label>

                {syncStatus?.sprint_stats && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm">
                      <span>{syncStatus.sprint_stats.passing}/{syncStatus.sprint_stats.total} features passing</span>
                      {syncStatus.sprint_complete && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/10 text-green-600 font-medium">
                          Sprint Complete!
                        </span>
                      )}
                    </div>

                    {syncStatus.sprint_stats.total_test_runs != null && syncStatus.sprint_stats.total_test_runs > 0 && (
                      <div className="text-xs text-muted-foreground">
                        {syncStatus.sprint_stats.total_test_runs} test runs, {syncStatus.sprint_stats.overall_pass_rate?.toFixed(0) ?? 0}% pass rate
                      </div>
                    )}

                    {!syncStatus.sprint_complete && syncStatus.sprint_stats.failed > 0 && (
                      <p className="text-xs text-muted-foreground">
                        {syncStatus.sprint_stats.failed} feature(s) still need to pass before the sprint can be completed.
                      </p>
                    )}
                  </div>
                )}

                {!syncStatus?.sprint_stats && (
                  <p className="text-xs text-muted-foreground">
                    Enable background sync to track sprint progress.
                  </p>
                )}

                <Button
                  size="sm"
                  disabled={!syncStatus?.sprint_complete || completeSprint.isPending}
                  onClick={() => {
                    const projectName = prompt('Project name to complete sprint for:')
                    if (!projectName) return
                    setCompletionResult(null)
                    completeSprint.mutate(projectName, {
                      onSuccess: (result) => setCompletionResult(result),
                    })
                  }}
                >
                  {completeSprint.isPending ? <Loader2 className="animate-spin mr-1" size={14} /> : null}
                  Complete Sprint
                </Button>

                {completionResult && (
                  <Alert variant={completionResult.success ? 'default' : 'destructive'}>
                    <AlertDescription>
                      {completionResult.success ? (
                        <div className="space-y-1">
                          <div className="flex items-center gap-1">
                            <Check size={14} className="text-green-600" />
                            Sprint completed! {completionResult.features_completed} features passing.
                          </div>
                          {completionResult.git_tag && (
                            <div className="text-xs text-muted-foreground">
                              Git tag: <code className="bg-muted px-1 rounded">{completionResult.git_tag}</code>
                            </div>
                          )}
                          {completionResult.release_notes_path && (
                            <div className="text-xs text-muted-foreground">
                              Release notes: <code className="bg-muted px-1 rounded">{completionResult.release_notes_path}</code>
                            </div>
                          )}
                        </div>
                      ) : (
                        completionResult.error
                      )}
                    </AlertDescription>
                  </Alert>
                )}

                {completeSprint.isError && (
                  <Alert variant="destructive">
                    <AlertDescription>
                      Sprint completion failed: {completeSprint.error?.message || 'Unknown error'}
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
