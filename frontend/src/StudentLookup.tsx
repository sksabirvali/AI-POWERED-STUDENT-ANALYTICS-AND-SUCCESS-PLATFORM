import { useEffect, useState } from 'react'
import { readApiResponse } from './api'

type StudentMatch = {
  student_id: string
  name: string
  department: string
  semester: number
}

type StudentLookupProps = {
  value: string
  accessToken: string
  onChange: (studentId: string) => void
  includeAll?: boolean
}

export default function StudentLookup({ value, accessToken, onChange, includeAll = false }: StudentLookupProps) {
  const [query, setQuery] = useState(value === 'all' ? 'All students' : '')
  const [matches, setMatches] = useState<StudentMatch[]>([])
  const [selected, setSelected] = useState<StudentMatch | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (value === 'all') {
      return
    }
    if (!value) {
      return
    }
    const controller = new AbortController()
    fetch(`/api/students?student_id=${encodeURIComponent(value)}&limit=1`, {
      signal: controller.signal,
      headers: { Authorization: `Bearer ${accessToken}` },
    })
      .then((response) => readApiResponse<StudentMatch[]>(response))
      .then((students) => {
        const student = students[0] ?? null
        setSelected(student)
        setQuery(student ? `${student.student_id} · ${student.name}` : value)
      })
      .catch((fetchError: Error) => {
        if (fetchError.name !== 'AbortError') setError(fetchError.message)
      })
    return () => controller.abort()
  }, [value, accessToken])

  useEffect(() => {
    const search = query.trim()
    if ((value === 'all' && query === 'All students') || search.length < 2 || selected && query === `${selected.student_id} · ${selected.name}`) {
      return
    }
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      fetch(`/api/students?search=${encodeURIComponent(search)}&limit=10`, {
        signal: controller.signal,
        headers: { Authorization: `Bearer ${accessToken}` },
      })
        .then((response) => readApiResponse<StudentMatch[]>(response))
        .then(setMatches)
        .catch((fetchError: Error) => {
          if (fetchError.name !== 'AbortError') setError(fetchError.message)
        })
    }, 250)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [query, selected, accessToken, value])

  return (
    <div className="relative mt-1">
      <input
        value={query}
        onChange={(event) => {
          setQuery(event.target.value)
          setSelected(null)
          setMatches([])
          setError('')
        }}
        placeholder="Search name or student ID"
        aria-label="Search student by name or ID"
        autoComplete="off"
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2"
      />
      {matches.length > 0 && (
        <div className="absolute z-20 mt-1 max-h-60 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-lg">
          {includeAll && (
            <button
              type="button"
              onClick={() => {
                setSelected(null)
                setQuery('All students')
                setMatches([])
                onChange('all')
              }}
              className="block w-full px-3 py-2 text-left text-sm font-medium text-blue-700 hover:bg-blue-50"
            >
              All students
            </button>
          )}
          {matches.map((student) => (
            <button
              key={student.student_id}
              type="button"
              onClick={() => {
                setSelected(student)
                setQuery(`${student.student_id} · ${student.name}`)
                setMatches([])
                onChange(student.student_id)
              }}
              className="block w-full px-3 py-2 text-left text-sm hover:bg-blue-50"
            >
              <span className="font-medium">{student.student_id} · {student.name}</span>
              <span className="block text-xs text-slate-500">{student.department} · Semester {student.semester}</span>
            </button>
          ))}
        </div>
      )}
      {query.trim().length >= 2 && matches.length === 0 && !selected && <p className="mt-1 text-xs text-slate-500">No matching students found.</p>}
      {error && <p role="alert" className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  )
}