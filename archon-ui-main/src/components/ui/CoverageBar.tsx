import { useEffect, useState } from 'react'
import { BarChart, AlertCircle, CheckCircle, Activity } from 'lucide-react'

interface CoverageSummary {
  total: {
    lines: { pct: number }
    statements: { pct: number }
    functions: { pct: number }
    branches: { pct: number }
  }
}

export function CoverageBar() {
  const [summary, setSummary] = useState<CoverageSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchCoverage = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/coverage/coverage-summary.json')
      if (!response.ok) {
        throw new Error(`Failed to fetch coverage: ${response.status}`)
      }
      const data: CoverageSummary = await response.json()
      setSummary(data)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load coverage data'
      setError(message)
      console.error('Coverage fetch error:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCoverage()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center gap-2 p-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
        <Activity className="w-4 h-4 animate-pulse text-blue-500" />
        <span className="text-sm text-blue-600 dark:text-blue-400">Loading coverage...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 p-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md">
        <AlertCircle className="w-4 h-4 text-yellow-500" />
        <span className="text-sm text-yellow-600 dark:text-yellow-400">
          Coverage not available
        </span>
        <button 
          onClick={fetchCoverage}
          className="text-xs text-yellow-700 dark:text-yellow-300 hover:underline ml-2"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!summary) {
    return null
  }

  const linesPct = summary.total.lines.pct
  const statementsPct = summary.total.statements.pct
  const functionsPct = summary.total.functions.pct
  const branchesPct = summary.total.branches.pct

  const getColorClass = (pct: number) => {
    if (pct >= 80) return 'bg-green-500'
    if (pct >= 60) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const getTextColor = (pct: number) => {
    if (pct >= 80) return 'text-green-600 dark:text-green-400'
    if (pct >= 60) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  const overallPct = Math.round((linesPct + statementsPct + functionsPct + branchesPct) / 4)

  return (
    <div className="space-y-3">
      {/* Overall Coverage */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          {overallPct >= 80 ? (
            <CheckCircle className="w-5 h-5 text-green-500" />
          ) : (
            <BarChart className="w-5 h-5 text-blue-500" />
          )}
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Overall Coverage
          </span>
        </div>
        <div className="flex-1 bg-slate-200 dark:bg-slate-700 rounded-full h-6 overflow-hidden">
          <div 
            className={`h-full rounded-full transition-all duration-500 ${getColorClass(overallPct)}`}
            style={{ width: `${overallPct}%` }}
          />
        </div>
        <span className={`text-sm font-medium ${getTextColor(overallPct)} min-w-[3rem] text-right`}>
          {overallPct}%
        </span>
      </div>

      {/* Detailed Metrics */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="flex items-center justify-between">
          <span className="text-gray-600 dark:text-gray-400">Lines:</span>
          <div className="flex items-center gap-2">
            <div className="w-12 bg-slate-200 dark:bg-slate-700 rounded-full h-2">
              <div 
                className={`h-full rounded-full ${getColorClass(linesPct)}`}
                style={{ width: `${linesPct}%` }}
              />
            </div>
            <span className={`${getTextColor(linesPct)} min-w-[2rem] text-right`}>
              {linesPct.toFixed(1)}%
            </span>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-gray-600 dark:text-gray-400">Functions:</span>
          <div className="flex items-center gap-2">
            <div className="w-12 bg-slate-200 dark:bg-slate-700 rounded-full h-2">
              <div 
                className={`h-full rounded-full ${getColorClass(functionsPct)}`}
                style={{ width: `${functionsPct}%` }}
              />
            </div>
            <span className={`${getTextColor(functionsPct)} min-w-[2rem] text-right`}>
              {functionsPct.toFixed(1)}%
            </span>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-gray-600 dark:text-gray-400">Statements:</span>
          <div className="flex items-center gap-2">
            <div className="w-12 bg-slate-200 dark:bg-slate-700 rounded-full h-2">
              <div 
                className={`h-full rounded-full ${getColorClass(statementsPct)}`}
                style={{ width: `${statementsPct}%` }}
              />
            </div>
            <span className={`${getTextColor(statementsPct)} min-w-[2rem] text-right`}>
              {statementsPct.toFixed(1)}%
            </span>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-gray-600 dark:text-gray-400">Branches:</span>
          <div className="flex items-center gap-2">
            <div className="w-12 bg-slate-200 dark:bg-slate-700 rounded-full h-2">
              <div 
                className={`h-full rounded-full ${getColorClass(branchesPct)}`}
                style={{ width: `${branchesPct}%` }}
              />
            </div>
            <span className={`${getTextColor(branchesPct)} min-w-[2rem] text-right`}>
              {branchesPct.toFixed(1)}%
            </span>
          </div>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={() => window.open('/coverage/index.html', '_blank')}
          className="text-xs bg-blue-100 hover:bg-blue-200 dark:bg-blue-900/20 dark:hover:bg-blue-900/30 text-blue-600 dark:text-blue-400 px-2 py-1 rounded transition-colors"
        >
          View Full Report
        </button>
        <button
          onClick={fetchCoverage}
          className="text-xs bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 px-2 py-1 rounded transition-colors"
        >
          Refresh
        </button>
      </div>
    </div>
  )
} 