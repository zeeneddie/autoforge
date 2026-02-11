import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useReleaseNotesList, useReleaseNotesContent } from '../hooks/useProjects'
import { FileText, Calendar, HardDrive } from 'lucide-react'

interface ReleaseNotesViewerProps {
  projectName: string
}

export function ReleaseNotesViewer({ projectName }: ReleaseNotesViewerProps) {
  const { data: notesList, isLoading: listLoading } = useReleaseNotesList(projectName)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const { data: content, isLoading: contentLoading } = useReleaseNotesContent(
    projectName,
    selectedFile
  )

  if (listLoading) {
    return (
      <Card className="p-8 text-center">
        <div className="animate-pulse text-muted-foreground">Loading release notes...</div>
      </Card>
    )
  }

  if (!notesList || notesList.items.length === 0) {
    return (
      <Card className="p-8 text-center">
        <FileText size={32} className="mx-auto mb-3 text-muted-foreground" />
        <p className="text-muted-foreground">
          No release notes available. Complete a sprint to generate release notes.
        </p>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* File list */}
      <Card className="md:col-span-1">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Release Notes</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {notesList.items.map((item) => (
              <button
                key={item.filename}
                onClick={() => setSelectedFile(item.filename)}
                className={`w-full text-left px-4 py-3 hover:bg-muted/50 transition-colors ${
                  selectedFile === item.filename ? 'bg-muted/70' : ''
                }`}
              >
                <div className="font-medium text-sm">{item.cycle_name || item.filename}</div>
                <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Calendar size={10} />
                    {new Date(item.created_at).toLocaleDateString()}
                  </span>
                  <span className="flex items-center gap-1">
                    <HardDrive size={10} />
                    {formatBytes(item.size_bytes)}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Content viewer */}
      <Card className="md:col-span-2">
        <CardContent className="p-4">
          {selectedFile ? (
            contentLoading ? (
              <div className="animate-pulse text-muted-foreground">Loading...</div>
            ) : content ? (
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <SimpleMarkdown text={content.content} />
              </div>
            ) : (
              <div className="text-muted-foreground">Failed to load content.</div>
            )
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <FileText size={32} className="mx-auto mb-3" />
              <p>Select a release notes file to view its contents.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/**
 * Simple markdown renderer supporting headers, bold, italic, lists, tables, and code blocks.
 * No external dependencies.
 */
function SimpleMarkdown({ text }: { text: string }) {
  const lines = text.split('\n')
  const elements: React.ReactNode[] = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    // Code block
    if (line.startsWith('```')) {
      const codeLines: string[] = []
      i++
      while (i < lines.length && !lines[i].startsWith('```')) {
        codeLines.push(lines[i])
        i++
      }
      i++ // skip closing ```
      elements.push(
        <pre key={elements.length} className="bg-muted rounded-md p-3 overflow-x-auto text-xs font-mono">
          <code>{codeLines.join('\n')}</code>
        </pre>
      )
      continue
    }

    // Table (starts with |)
    if (line.trim().startsWith('|') && i + 1 < lines.length && lines[i + 1].trim().match(/^\|[\s\-:|]+\|/)) {
      const tableLines: string[] = []
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        tableLines.push(lines[i])
        i++
      }
      elements.push(<MarkdownTable key={elements.length} lines={tableLines} />)
      continue
    }

    // Headers
    if (line.startsWith('# ')) {
      elements.push(<h1 key={elements.length} className="text-xl font-bold mt-4 mb-2">{renderInline(line.slice(2))}</h1>)
      i++; continue
    }
    if (line.startsWith('## ')) {
      elements.push(<h2 key={elements.length} className="text-lg font-bold mt-3 mb-1.5">{renderInline(line.slice(3))}</h2>)
      i++; continue
    }
    if (line.startsWith('### ')) {
      elements.push(<h3 key={elements.length} className="text-base font-bold mt-2 mb-1">{renderInline(line.slice(4))}</h3>)
      i++; continue
    }

    // Unordered list
    if (line.match(/^[\s]*[-*]\s/)) {
      const listItems: string[] = []
      while (i < lines.length && lines[i].match(/^[\s]*[-*]\s/)) {
        listItems.push(lines[i].replace(/^[\s]*[-*]\s/, ''))
        i++
      }
      elements.push(
        <ul key={elements.length} className="list-disc list-inside space-y-0.5 my-1">
          {listItems.map((item, j) => <li key={j}>{renderInline(item)}</li>)}
        </ul>
      )
      continue
    }

    // Checkbox list
    if (line.match(/^[\s]*- \[[ x]\]/i)) {
      const checkItems: { checked: boolean; text: string }[] = []
      while (i < lines.length && lines[i].match(/^[\s]*- \[[ x]\]/i)) {
        const match = lines[i].match(/^[\s]*- \[([ x])\]\s*(.*)/i)
        if (match) {
          checkItems.push({ checked: match[1].toLowerCase() === 'x', text: match[2] })
        }
        i++
      }
      elements.push(
        <ul key={elements.length} className="space-y-0.5 my-1">
          {checkItems.map((item, j) => (
            <li key={j} className="flex items-center gap-2">
              <span className={`inline-block w-4 h-4 rounded border text-center text-xs leading-4 ${
                item.checked ? 'bg-green-500/20 border-green-500 text-green-600' : 'border-muted-foreground/40'
              }`}>
                {item.checked ? '✓' : ''}
              </span>
              {renderInline(item.text)}
            </li>
          ))}
        </ul>
      )
      continue
    }

    // Horizontal rule
    if (line.match(/^---+$/)) {
      elements.push(<hr key={elements.length} className="my-3 border-border" />)
      i++; continue
    }

    // Empty line
    if (line.trim() === '') {
      i++; continue
    }

    // Regular paragraph
    elements.push(<p key={elements.length} className="my-1">{renderInline(line)}</p>)
    i++
  }

  return <>{elements}</>
}

function renderInline(text: string): React.ReactNode {
  // Process bold, italic, inline code, and links
  const parts: React.ReactNode[] = []
  let remaining = text
  let key = 0

  while (remaining.length > 0) {
    // Inline code
    const codeMatch = remaining.match(/^`([^`]+)`/)
    if (codeMatch) {
      parts.push(
        <code key={key++} className="bg-muted px-1 py-0.5 rounded text-xs font-mono">
          {codeMatch[1]}
        </code>
      )
      remaining = remaining.slice(codeMatch[0].length)
      continue
    }

    // Bold
    const boldMatch = remaining.match(/^\*\*(.+?)\*\*/)
    if (boldMatch) {
      parts.push(<strong key={key++}>{boldMatch[1]}</strong>)
      remaining = remaining.slice(boldMatch[0].length)
      continue
    }

    // Italic
    const italicMatch = remaining.match(/^\*(.+?)\*/)
    if (italicMatch) {
      parts.push(<em key={key++}>{italicMatch[1]}</em>)
      remaining = remaining.slice(italicMatch[0].length)
      continue
    }

    // Link
    const linkMatch = remaining.match(/^\[([^\]]+)\]\(([^)]+)\)/)
    if (linkMatch) {
      parts.push(
        <a key={key++} href={linkMatch[2]} className="text-primary underline" target="_blank" rel="noopener noreferrer">
          {linkMatch[1]}
        </a>
      )
      remaining = remaining.slice(linkMatch[0].length)
      continue
    }

    // Regular text (take one char at a time until next special char)
    const nextSpecial = remaining.search(/[`*\[]/)
    if (nextSpecial === -1) {
      parts.push(remaining)
      break
    } else if (nextSpecial === 0) {
      // Special char that didn't match any pattern, treat as text
      parts.push(remaining[0])
      remaining = remaining.slice(1)
    } else {
      parts.push(remaining.slice(0, nextSpecial))
      remaining = remaining.slice(nextSpecial)
    }
  }

  return parts.length === 1 ? parts[0] : <>{parts}</>
}

function MarkdownTable({ lines }: { lines: string[] }) {
  if (lines.length < 2) return null

  const parseRow = (line: string) =>
    line.split('|').slice(1, -1).map(cell => cell.trim())

  const headers = parseRow(lines[0])
  const rows = lines.slice(2).map(parseRow) // Skip separator row

  return (
    <div className="overflow-x-auto my-2">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b-2 border-border">
            {headers.map((h, i) => (
              <th key={i} className="text-left py-1.5 px-2 font-medium">{renderInline(h)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-border/50">
              {row.map((cell, j) => (
                <td key={j} className="py-1.5 px-2">{renderInline(cell)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
