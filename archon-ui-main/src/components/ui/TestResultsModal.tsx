import { useEffect, useState } from 'react'
import { X, BarChart, AlertCircle, CheckCircle, XCircle, Activity, RefreshCw, ExternalLink, TestTube, Target } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface TestResults {
  summary: {
    total: number
    passed: number
    failed: number
    skipped: number
    duration: number
  }
  suites: Array<{
    name: string
    tests: number
    passed: number
    failed: number
    skipped: number
    duration: number
  }>
}

interface CoverageSummary {
  total: {
    lines: { pct: number; covered: number; total: number }
    statements: { pct: number; covered: number; total: number }
    functions: { pct: number; covered: number; total: number }
    branches: { pct: number; covered: number; total: number }
  }
}

interface TestResultsModalProps {
  isOpen: boolean
  onClose: () => void
}

export function TestResultsModal({ isOpen, onClose }: TestResultsModalProps) {
  const [testResults, setTestResults] = useState<TestResults | null>(null)
  const [coverage, setCoverage] = useState<CoverageSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchResults = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Fetch test results JSON
      const testResponse = await fetch('/coverage/test-results.json')
      if (testResponse.ok) {
        const testData = await testResponse.json()
        
        // Parse vitest results format
        const results: TestResults = {
          summary: {
            total: testData.numTotalTests || 0,
            passed: testData.numPassedTests || 0,
            failed: testData.numFailedTests || 0,
            skipped: testData.numSkippedTests || 0,
            duration: testData.testResults?.reduce((acc: number, suite: any) => 
              acc + (suite.perfStats?.end - suite.perfStats?.start || 0), 0) || 0
          },
          suites: testData.testResults?.map((suite: any) => ({
            name: suite.name?.replace(process.cwd(), '') || 'Unknown',
            tests: suite.numTotalTests || 0,
            passed: suite.numPassedTests || 0,
            failed: suite.numFailedTests || 0,
            skipped: suite.numSkippedTests || 0,
            duration: (suite.perfStats?.end - suite.perfStats?.start) || 0
          })) || []
        }
        setTestResults(results)
      }

      // Fetch coverage data
      const coverageResponse = await fetch('/coverage/coverage-summary.json')
      if (coverageResponse.ok) {
        const coverageData = await coverageResponse.json()
        setCoverage(coverageData)
      }

      if (!testResponse.ok && !coverageResponse.ok) {
        throw new Error('No test results or coverage data available')
      }

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load test results'
      setError(message)
      console.error('Test results fetch error:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      fetchResults()
    }
  }, [isOpen])

  const getHealthScore = () => {
    if (!testResults || !coverage) return 0
    
    const testScore = testResults.summary.total > 0 
      ? (testResults.summary.passed / testResults.summary.total) * 100 
      : 0
    const coverageScore = coverage.total.lines.pct
    
    return Math.round((testScore + coverageScore) / 2)
  }

  const getHealthColor = (score: number) => {
    if (score >= 80) return 'text-green-500'
    if (score >= 60) return 'text-yellow-500'
    return 'text-red-500'
  }

  const getHealthBg = (score: number) => {
    if (score >= 80) return 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
    if (score >= 60) return 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800'
    return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
  }

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  if (!isOpen) return null

  const healthScore = getHealthScore()

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
          className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 w-full max-w-4xl max-h-[90vh] overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3">
              <TestTube className="w-6 h-6 text-blue-500" />
              <h2 className="text-xl font-semibold text-gray-800 dark:text-white">
                Test Results Report
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
                  <span className="text-gray-600 dark:text-gray-400">Loading test results...</span>
                </div>
              </div>
            )}

            {error && !testResults && !coverage && (
              <div className="flex flex-col items-center justify-center py-12 space-y-4">
                <AlertCircle className="w-12 h-12 text-yellow-500" />
                <div className="text-center">
                  <p className="text-gray-600 dark:text-gray-400 mb-2">No test results available</p>
                  <p className="text-sm text-gray-500 dark:text-gray-500">Run tests to generate the report</p>
                </div>
              </div>
            )}

            {(testResults || coverage) && (
              <div className="space-y-6">
                {/* Health Score */}
                <div className={`p-6 rounded-lg border ${getHealthBg(healthScore)}`}>
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-3">
                      <Target className={`w-8 h-8 ${getHealthColor(healthScore)}`} />
                      <div>
                        <h3 className="text-xl font-bold text-gray-800 dark:text-white">
                          Test Health Score
                        </h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          Overall test and coverage quality
                        </p>
                      </div>
                    </div>
                    <div className="ml-auto text-right">
                      <div className={`text-4xl font-bold ${getHealthColor(healthScore)}`}>
                        {healthScore}%
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {healthScore >= 80 ? 'Excellent' : healthScore >= 60 ? 'Good' : 'Needs Work'}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Test Results Summary */}
                  {testResults && (
                    <div className="bg-gray-50 dark:bg-gray-900/50 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
                      <div className="flex items-center gap-3 mb-4">
                        <TestTube className="w-5 h-5 text-blue-500" />
                        <h3 className="text-lg font-semibold text-gray-800 dark:text-white">
                          Test Summary
                        </h3>
                      </div>

                      {/* Overall Stats */}
                      <div className="grid grid-cols-2 gap-4 mb-4">
                        <div className="text-center p-3 bg-white dark:bg-gray-800 rounded-lg border">
                          <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                            {testResults.summary.passed}
                          </div>
                          <div className="text-sm text-gray-600 dark:text-gray-400">Passed</div>
                        </div>
                        <div className="text-center p-3 bg-white dark:bg-gray-800 rounded-lg border">
                          <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                            {testResults.summary.failed}
                          </div>
                          <div className="text-sm text-gray-600 dark:text-gray-400">Failed</div>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4 mb-4">
                        <div className="text-center p-3 bg-white dark:bg-gray-800 rounded-lg border">
                          <div className="text-lg font-semibold text-gray-700 dark:text-gray-300">
                            {testResults.summary.total}
                          </div>
                          <div className="text-sm text-gray-600 dark:text-gray-400">Total Tests</div>
                        </div>
                        <div className="text-center p-3 bg-white dark:bg-gray-800 rounded-lg border">
                          <div className="text-lg font-semibold text-gray-700 dark:text-gray-300">
                            {formatDuration(testResults.summary.duration)}
                          </div>
                          <div className="text-sm text-gray-600 dark:text-gray-400">Duration</div>
                        </div>
                      </div>

                      {/* Test Suites */}
                      <div className="space-y-2 max-h-40 overflow-y-auto">
                        {testResults.suites.map((suite, index) => (
                          <div key={index} className="flex items-center justify-between p-2 bg-white dark:bg-gray-800 rounded border text-sm">
                            <div className="flex items-center gap-2">
                              {suite.failed > 0 ? (
                                <XCircle className="w-4 h-4 text-red-500" />
                              ) : (
                                <CheckCircle className="w-4 h-4 text-green-500" />
                              )}
                              <span className="font-mono text-xs truncate max-w-[200px]" title={suite.name}>
                                {suite.name.split('/').pop()}
                              </span>
                            </div>
                            <div className="flex items-center gap-2 text-xs">
                              <span className="text-green-600">{suite.passed}</span>
                              <span className="text-gray-400">/</span>
                              <span className="text-red-600">{suite.failed}</span>
                              <span className="text-gray-500">({formatDuration(suite.duration)})</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Coverage Summary */}
                  {coverage && (
                    <div className="bg-gray-50 dark:bg-gray-900/50 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
                      <div className="flex items-center gap-3 mb-4">
                        <BarChart className="w-5 h-5 text-blue-500" />
                        <h3 className="text-lg font-semibold text-gray-800 dark:text-white">
                          Coverage Analysis
                        </h3>
                      </div>

                      <div className="space-y-4">
                        {[
                          { label: 'Lines', data: coverage.total.lines },
                          { label: 'Functions', data: coverage.total.functions },
                          { label: 'Statements', data: coverage.total.statements },
                          { label: 'Branches', data: coverage.total.branches }
                        ].map(({ label, data }) => (
                          <div key={label} className="space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                {label}
                              </span>
                              <span className="text-sm font-semibold text-gray-800 dark:text-white">
                                {data.pct.toFixed(1)}%
                              </span>
                            </div>
                            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                              <div 
                                className={`h-2 rounded-full transition-all duration-500 ${
                                  data.pct >= 80 ? 'bg-green-500' :
                                  data.pct >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                                }`}
                                style={{ width: `${data.pct}%` }}
                              />
                            </div>
                            <div className="text-xs text-gray-500 dark:text-gray-400">
                              {data.covered} of {data.total} covered
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <button
                    onClick={fetchResults}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Refresh
                  </button>
                  <button
                    onClick={() => window.open('/coverage/index.html', '_blank')}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
                  >
                    <ExternalLink className="w-4 h-4" />
                    Detailed Report
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