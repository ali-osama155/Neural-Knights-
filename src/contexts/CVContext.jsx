import { createContext, useContext, useState, useCallback } from 'react'

const BACKEND = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * CVContext - Manages CV analysis data globally
 * Stores: CV upload status, analysis results (score, skills, role), and polling state
 */
const CVContext = createContext()

export function CVProvider({ children }) {
  const [cvData, setCvData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [isPolling, setIsPolling] = useState(false)

  /**
   * Upload CV file to backend
   * @param {File} file - CV file to upload (PDF/DOCX)
   * @param {string} token - JWT token for auth
   * @returns {Promise<Object>} Initial CV upload response with id and status
   */
  const uploadCV = useCallback(async (file, token) => {
    setLoading(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`${BACKEND}/api/v1/cv/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      })

      if (!response.ok) {
        const errData = await response.json()
        throw new Error(errData.detail || `Upload failed with status ${response.status}`)
      }

      const data = await response.json()
      setCvData(data)
      return data
    } catch (err) {
      const errorMessage = err.message || 'Failed to upload CV'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Poll for CV analysis results
   * Calls GET /api/v1/cv/latest repeatedly until status is "analyzed"
   * @param {string} token - JWT token for auth
   * @param {number} maxAttempts - Max number of polls (default 30, ~30 seconds)
   * @returns {Promise<Object>} Complete CV analysis with score, skills, role, etc.
   */
  const pollAnalysisResults = useCallback(async (token, maxAttempts = 30) => {
    setIsPolling(true)
    setError(null)
    try {
      let attempts = 0
      while (attempts < maxAttempts) {
        const response = await fetch(`${BACKEND}/api/v1/cv/latest`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        })

        if (!response.ok) {
          throw new Error(`Failed to fetch CV results: ${response.status}`)
        }

        const data = await response.json()
        setCvData(data)

        if (data.status === 'analyzed') {
          setIsPolling(false)
          return data
        }

        if (data.status === 'failed') {
          throw new Error('CV analysis failed on backend')
        }

        // Wait 1 second before next poll
        await new Promise(r => setTimeout(r, 1000))
        attempts++
      }

      throw new Error('CV analysis timeout - please try again')
    } catch (err) {
      const errorMessage = err.message || 'Failed to retrieve analysis'
      setError(errorMessage)
      setIsPolling(false)
      throw err
    }
  }, [])

  /**
   * Clear CV data and reset state
   */
  const clearCV = useCallback(() => {
    setCvData(null)
    setError(null)
    setLoading(false)
    setIsPolling(false)
  }, [])

  /**
   * Get CV analysis results (for display)
   * @returns {Object|null} CV data object or null if not ready
   */
  const getAnalysisData = useCallback(() => {
    if (!cvData || cvData.status !== 'analyzed') return null
    return {
      score: cvData.score,
      skills: cvData.skills || [],
      strengths: cvData.strengths || [],
      recommendations: cvData.recommendations || [],
      bestFitRole: cvData.best_fit_role,
    }
  }, [cvData])

  const value = {
    // State
    cvData,
    loading,
    error,
    isPolling,
    
    // Methods
    uploadCV,
    pollAnalysisResults,
    clearCV,
    getAnalysisData,
  }

  return (
    <CVContext.Provider value={value}>
      {children}
    </CVContext.Provider>
  )
}

/**
 * Hook to use CV context
 * @returns {Object} CV context value
 */
export function useCV() {
  const context = useContext(CVContext)
  if (!context) {
    throw new Error('useCV must be used within CVProvider')
  }
  return context
}
