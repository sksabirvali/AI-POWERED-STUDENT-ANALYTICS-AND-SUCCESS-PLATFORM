import { useCallback, useEffect, useState } from 'react'
import { readApiResponse } from './api'

type FacultyRequest = {
  username: string
  name: string
  department: string
  email: string | null
}

type FacultyApprovalsProps = {
  accessToken: string
}

export default function FacultyApprovals({ accessToken }: FacultyApprovalsProps) {
  const [requests, setRequests] = useState<FacultyRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [approving, setApproving] = useState<string | null>(null)

  const loadRequests = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await fetch('/api/auth/faculty-requests', {
        headers: { Authorization: `Bearer ${accessToken}` },
      })
      const result = await readApiResponse<FacultyRequest[]>(response)
      setRequests(result)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load faculty requests')
    } finally {
      setLoading(false)
    }
  }, [accessToken])

  useEffect(() => {
    void loadRequests()
  }, [loadRequests])

  const approve = async (username: string) => {
    setApproving(username)
    setError('')
    try {
      const response = await fetch(`/api/auth/faculty-requests/${encodeURIComponent(username)}/approve`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}` },
      })
      await readApiResponse<{ message: string }>(response)
      await loadRequests()
    } catch (approveError) {
      setError(approveError instanceof Error ? approveError.message : 'Could not approve faculty account')
    } finally {
      setApproving(null)
    }
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-slate-900">Faculty registration requests</h2>
        <p className="mt-1 text-sm text-slate-500">Approve a request before the faculty member can sign in.</p>
      </div>
      {error && <p role="alert" className="mb-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {loading ? (
        <p className="text-sm text-slate-500">Loading requests…</p>
      ) : requests.length === 0 ? (
        <p className="text-sm text-slate-500">There are no pending requests.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>{['Account ID', 'Name', 'Branch', 'Email', 'Action'].map((column) => <th key={column} className="px-4 py-3 font-medium">{column}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {requests.map((request) => (
                <tr key={request.username}>
                  <td className="px-4 py-3 font-medium text-slate-900">{request.username}</td>
                  <td className="px-4 py-3">{request.name}</td>
                  <td className="px-4 py-3">{request.department}</td>
                  <td className="px-4 py-3">{request.email}</td>
                  <td className="px-4 py-3">
                    <button
                      disabled={approving !== null}
                      onClick={() => void approve(request.username)}
                      className="rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
                    >
                      {approving === request.username ? 'Approving…' : 'Approve'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
