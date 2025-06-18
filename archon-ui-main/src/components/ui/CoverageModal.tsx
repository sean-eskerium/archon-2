import { useEffect, useState } from 'react'
import { X, BarChart, AlertCircle, CheckCircle, Activity, RefreshCw, ExternalLink } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface CoverageSummary {
  total: {
    lines: { pct: number; covered: number; total: number }
    statements: { pct: number; covered: number; total: number }
    functions: { pct: number; covered: number; total: number }
    branches: { pct: number; covered: number; total: number }
  }
}

interface CoverageModalProps {
  isOpen: boolean
  onClose: () => void
}

export function CoverageModal({ isOpen, onClose }: CoverageModalProps) {
  const [summary, setSummary] = useState<CoverageSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)

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

  const generateCoverage = async () => {
    setGenerating(true)
    setError(null)
    
    try {
      const response = await fetch('/api/generate-coverage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      
      if (!response.ok) {
        throw new Error('Failed to generate coverage')
      }

      // Stream the response
      const reader = response.body?.getReader()
      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          
          const chunk = new TextDecoder().decode(value)
          const lines = chunk.split('\n')
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                if (data.type === 'completed' && data.exit_code === 0) {
                  // Coverage generated successfully, fetch the new data
                  setTimeout(fetchCoverage, 1000) // Small delay to ensure files are written
                }
              } catch (e) {
                // Ignore JSON parse errors for streaming
              }
            }
          }
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to generate coverage'
      setError(message)
    } finally {
      setGenerating(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      fetchCoverage()
    }
  }, [isOpen])

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

  const getBgColor = (pct: number) => {
    if (pct >= 80) return 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
    if (pct >= 60) return 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800'
    return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 w-full max-w-2xl max-h-[90vh] overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3">
              <BarChart className="w-6 h-6 text-blue-500" />
              <h2 className="text-xl font-semibold text-gray-800 dark:text-white">
                Test Coverage Report
              </h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
            {loading && (
              <div className="flex items-center justify-center py-12">
                <div className="flex items-center gap-3">
                  <Activity className="w-5 h-5 animate-pulse text-blue-500" />
                  <span className="text-gray-600 dark:text-gray-400">Loading coverage data...</span>
                </div>
              </div>
            )}

            {error && !summary && (
              <div className="flex flex-col items-center justify-center py-12 space-y-4">
                <AlertCircle className="w-12 h-12 text-yellow-500" />
                <div className="text-center">
                  <p className="text-gray-600 dark:text-gray-400 mb-2">Coverage data not available</p>
                  <p className="text-sm text-gray-500 dark:text-gray-500">Run tests with coverage to generate the report</p>
                </div>
                <button
                  onClick={generateCoverage}
                  disabled={generating}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 text-white rounded-lg transition-colors"
                >
                  {generating ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <BarChart className="w-4 h-4" />
                      Generate Coverage
                    </>
                  )}
                </button>
              </div>
            )}

            {summary && (
              <div className="space-y-6">
                {/* Overall Coverage */}
                <div className={`p-4 rounded-lg border ${getBgColor(summary.total.lines.pct)}`}>
                  <div className="flex items-center gap-3 mb-3">
                    {summary.total.lines.pct >= 80 ? (
                      <CheckCircle className="w-6 h-6 text-green-500" />
                    ) : (
                      <BarChart className="w-6 h-6 text-blue-500" />
                    )}
                    <h3 className="text-lg font-semibold text-gray-800 dark:text-white">
                      Overall Coverage
                    </h3>
                  </div>
                  
                  <div className="flex items-center gap-4">
                    <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-8 overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all duration-700 ${getColorClass(summary.total.lines.pct)}`}
                        style={{ width: `${summary.total.lines.pct}%` }}
                      />
                    </div>
                    <span className={`text-2xl font-bold ${getTextColor(summary.total.lines.pct)}`}>
                      {summary.total.lines.pct.toFixed(1)}%
                    </span>
                  </div>
                </div>

                {/* Detailed Metrics */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Lines Coverage */}
                  <div className="bg-gray-50 dark:bg-gray-900/50 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium text-gray-700 dark:text-gray-300">Lines</h4>
                      <span className={`font-semibold ${getTextColor(summary.total.lines.pct)}`}>
                        {summary.total.lines.pct.toFixed(1)}%
                      </span>
                    </div>
                    <div className="mb-2 bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all duration-500 ${getColorClass(summary.total.lines.pct)}`}
                        style={{ width: `${summary.total.lines.pct}%` }}
                      />
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {summary.total.lines.covered} of {summary.total.lines.total} lines covered
                    </p>
                  </div>

                  {/* Functions Coverage */}
                  <div className="bg-gray-50 dark:bg-gray-900/50 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium text-gray-700 dark:text-gray-300">Functions</h4>
                      <span className={`font-semibold ${getTextColor(summary.total.functions.pct)}`}>
                        {summary.total.functions.pct.toFixed(1)}%
                      </span>
                    </div>
                    <div className="mb-2 bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all duration-500 ${getColorClass(summary.total.functions.pct)}`}
                        style={{ width: `${summary.total.functions.pct}%` }}
                      />
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {summary.total.functions.covered} of {summary.total.functions.total} functions covered
                    </p>
                  </div>

                  {/* Statements Coverage */}
                  <div className="bg-gray-50 dark:bg-gray-900/50 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium text-gray-700 dark:text-gray-300">Statements</h4>
                      <span className={`font-semibold ${getTextColor(summary.total.statements.pct)}`}>
                        {summary.total.statements.pct.toFixed(1)}%
                      </span>
                    </div>
                    <div className="mb-2 bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all duration-500 ${getColorClass(summary.total.statements.pct)}`}
                        style={{ width: `${summary.total.statements.pct}%` }}
                      />
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {summary.total.statements.covered} of {summary.total.statements.total} statements covered
                    </p>
                  </div>

                  {/* Branches Coverage */}
                  <div className="bg-gray-50 dark:bg-gray-900/50 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium text-gray-700 dark:text-gray-300">Branches</h4>
                      <span className={`font-semibold ${getTextColor(summary.total.branches.pct)}`}>
                        {summary.total.branches.pct.toFixed(1)}%
                      </span>
                    </div>
                    <div className="mb-2 bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all duration-500 ${getColorClass(summary.total.branches.pct)}`}
                        style={{ width: `${summary.total.branches.pct}%` }}
                      />
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {summary.total.branches.covered} of {summary.total.branches.total} branches covered
                    </p>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <button
                    onClick={fetchCoverage}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Refresh
                  </button>
                  <button
                    onClick={generateCoverage}
                    disabled={generating}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 text-white rounded-lg transition-colors"
                  >
                    {generating ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <BarChart className="w-4 h-4" />
                        Regenerate
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => window.open('/coverage/index.html', '_blank')}
                    className="flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-colors"
                  >
                    <ExternalLink className="w-4 h-4" />
                    Full Report
                  </button>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
} 