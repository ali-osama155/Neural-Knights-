import { createContext, useContext, useState, useCallback, useEffect } from 'react'

/**
 * AuthContext - Manages the authenticated user's identity globally.
 * Fetches the real logged-in user's profile from GET /api/v1/users/me
 * using the JWT stored in localStorage, so every page (Navbar, Dashboard,
 * Profile, etc.) shows the *actual* logged-in user instead of a
 * hardcoded name.
 */
const BACKEND = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TOKEN_KEY = 'access_token'

const AuthContext = createContext()

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const getToken = useCallback(() => localStorage.getItem(TOKEN_KEY), [])

  /**
   * Fetch the current user's profile from the backend.
   * Called on mount, and can be re-called after login or profile edits.
   */
  const refreshUser = useCallback(async () => {
    const token = getToken()
    if (!token) {
      setUser(null)
      setLoading(false)
      return null
    }

    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${BACKEND}/api/v1/users/me`, {
        method: 'GET',
        headers: { Authorization: `Bearer ${token}` },
      })

      if (res.status === 401) {
        // Token expired/invalid — clear it so the user is treated as logged out
        localStorage.removeItem(TOKEN_KEY)
        setUser(null)
        return null
      }

      if (!res.ok) {
        throw new Error(`Failed to load profile (${res.status})`)
      }

      const data = await res.json()
      setUser(data)
      return data
    } catch (err) {
      setError(err.message || 'Failed to load user')
      setUser(null)
      return null
    } finally {
      setLoading(false)
    }
  }, [getToken])

  // Load the user as soon as the app mounts (and whenever a token appears)
  useEffect(() => {
    refreshUser()
  }, [refreshUser])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    setUser(null)
  }, [])

  const value = {
    user,
    loading,
    error,
    isAuthenticated: !!user,
    refreshUser,
    logout,
    getToken,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

/**
 * Hook to access the authenticated user's data anywhere in the app.
 */
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
