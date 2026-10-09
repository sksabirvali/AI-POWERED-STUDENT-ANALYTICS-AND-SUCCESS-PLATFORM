import { useEffect, useMemo, useState } from 'react'
import { Activity, Save } from 'lucide-react'
import StudentAssistant from './StudentAssistant'
import { readApiResponse } from './api'
import StudentLookup from './StudentLookup'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

type Student = {
  student_id: string
  name: string
  department: string
}

type SessionUser = {
  role: 'admin' | 'faculty' | 'student'
  student_id: string | null
  access_token: string
}

type TrendPoint = {
  date: string
  label: string
  attendance: number | null
  marks: number | null
  risk: number
  at_risk_students: number
  students: number
  subjects: Record<string, { attendance: number | null; marks: number | null }>
}

const SUBJECTS = ['M1', 'M2', 'M3', 'M4']
const PERIODS = ['daily', 'weekly', 'monthly', 'yearly'] as const

function localDate(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

export default function AcademicProgress({ students, user }: { students: Student[]; user: SessionUser }) {
  const editable = user.role === 'admin' || user.role === 'faculty'
  const visibleStudents = useMemo(
    () => user.role === 'student' ? students.filter((student) => student.student_id === user.student_id) : students,
    [students, user.role, user.student_id],
  )
  const [studentId, setStudentId] = useState(user.student_id ?? '')
  const [trendStudentId, setTrendStudentId] = useState(user.student_id ?? 'all')
  const [subject, setSubject] = useState('M1')
  const [period, setPeriod] = useState<(typeof PERIODS)[number]>('weekly')
  const [metric, setMetric] = useState<'marks' | 'attendance'>('marks')
  const [entryDate, setEntryDate] = useState(localDate())
  const [attendance, setAttendance] = useState('Present')
  const [marks, setMarks] = useState('')
  const [trend, setTrend] = useState<TrendPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!studentId && visibleStudents.length) setStudentId(visibleStudents[0].student_id)
    if (user.role === 'student') {
      setStudentId(user.student_id ?? '')
      setTrendStudentId(user.student_id ?? 'all')
    }
  }, [visibleStudents, user.role, user.student_id, studentId])

  useEffect(() => {
    const controller = new AbortController()
    const params = new URLSearchParams({ period })
    if (trendStudentId !== 'all') params.set('student_id', trendStudentId)
    setLoading(true)
    setError('')
    fetch(`/api/academic/trends?${params.toString()}`, {
      signal: controller.signal,
      headers: { Authorization: `Bearer ${user.access_token}` },
    })
      .then(async (response) => {
        return readApiResponse<{ trend: TrendPoint[] }>(response)
      })
      .then((data: { trend: TrendPoint[] }) => setTrend(data.trend))
      .catch((fetchError: Error) => {
        if (fetchError.name !== 'AbortError') setError(fetchError.message)
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [period, trendStudentId])

  const chartData = trend.map((point) => ({
    ...point,
    M1: point.subjects.M1?.[metric] ?? null,
    M2: point.subjects.M2?.[metric] ?? null,
    M3: point.subjects.M3?.[metric] ?? null,
    M4: point.subjects.M4?.[metric] ?? null,
  }))
  const latest = trend[trend.length - 1]
  const growthWindow = period === 'yearly' ? 1 : period === 'monthly' ? 3 : 4
  const growthDelta = (key: 'marks' | 'attendance') => {
    const validPoints = trend.filter((point) => point[key] != null)
    if (validPoints.length < 2) return null
    const windowSize = Math.min(growthWindow, Math.floor(validPoints.length / 2))
    const average = (points: TrendPoint[]) => points.reduce((sum, point) => sum + (point[key] ?? 0), 0) / points.length
    return average(validPoints.slice(-windowSize)) - average(validPoints.slice(0, windowSize))
  }
  const marksChange = growthDelta('marks')
  const attendanceChange = growthDelta('attendance')

  const saveEntry = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!studentId) {
      setError('Select a student before saving a record.')
      return
    }
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const response = await fetch('/api/academic/entries', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${user.access_token}`,
        },
        body: JSON.stringify({
          student_id: studentId,
          subject,
          entry_date: entryDate,
          attendance,
          marks: marks === '' ? null : Number(marks),
          max_marks: 100,
        }),
      })
      await readApiResponse<{ message: string }>(response)
      setMessage(`${subject} record saved for ${studentId} on ${entryDate}.`)
      setMarks('')
      setTrendStudentId(studentId)
      setPeriod('daily')
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not save this record')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm uppercase tracking-[0.25em] text-blue-600">Academic growth</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">Subject Attendance & Marks</h1>
        <p className="mt-2 text-sm text-slate-600">Track M1–M4 performance over daily, weekly, monthly, and yearly periods.</p>
      </header>

      {user.role === 'student' && <StudentAssistant user={user} />}

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Current marks trend</p>
          <p className="mt-2 text-2xl font-semibold">{marksChange == null ? '—' : `${marksChange >= 0 ? '+' : ''}${marksChange.toFixed(1)} pts`}</p>
          <p className="mt-1 text-xs text-slate-500">First to latest {period} point</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Attendance growth</p>
          <p className="mt-2 text-2xl font-semibold">{attendanceChange == null ? '—' : `${attendanceChange >= 0 ? '+' : ''}${attendanceChange.toFixed(1)}%`}</p>
          <p className="mt-1 text-xs text-slate-500">First to latest {period} point</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Current risk indicator</p>
          <p className="mt-2 text-2xl font-semibold">{latest ? `${latest.risk}%` : '—'}</p>
          <p className="mt-1 text-xs text-slate-500">{latest?.at_risk_students ?? 0} students need attention in the latest period</p>
        </div>
      </div>

      {editable && (
        <form onSubmit={saveEntry} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-slate-900">Record class attendance and marks</h2>
            <p className="text-sm text-slate-500">Admin and faculty can save one student, subject, and class date at a time.</p>
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <label className="text-sm text-slate-600">Student
              <StudentLookup value={studentId} accessToken={user.access_token} onChange={setStudentId} />
            </label>
            <label className="text-sm text-slate-600">Subject
              <select value={subject} onChange={(event) => setSubject(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2">
                {SUBJECTS.map((value) => <option key={value}>{value}</option>)}
              </select>
            </label>
            <label className="text-sm text-slate-600">Class date
              <input type="date" value={entryDate} onChange={(event) => setEntryDate(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2" required />
            </label>
            <label className="text-sm text-slate-600">Attendance
              <select value={attendance} onChange={(event) => setAttendance(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2">
                <option>Present</option><option>Absent</option>
              </select>
            </label>
            <label className="text-sm text-slate-600">Marks (out of 100)
              <input type="number" min="0" max="100" step="0.5" value={marks} onChange={(event) => setMarks(event.target.value)} placeholder="Optional" className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2" />
            </label>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button disabled={saving} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 font-medium text-white disabled:opacity-50"><Save className="h-4 w-4" />{saving ? 'Saving…' : 'Save record'}</button>
            {message && <span role="status" className="text-sm text-emerald-700">{message}</span>}
          </div>
        </form>
      )}

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Growth by subject</h2>
            <p className="text-sm text-slate-500">Class records are aggregated over the selected time range.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {user.role !== 'student' && (
              <StudentLookup value={trendStudentId} accessToken={user.access_token} onChange={setTrendStudentId} includeAll />
            )}
            <select aria-label="Growth metric" value={metric} onChange={(event) => setMetric(event.target.value as 'marks' | 'attendance')} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
              <option value="marks">Marks</option><option value="attendance">Attendance</option>
            </select>
            <select aria-label="Growth period" value={period} onChange={(event) => setPeriod(event.target.value as (typeof PERIODS)[number])} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
              {PERIODS.map((value) => <option key={value} value={value}>{value[0].toUpperCase() + value.slice(1)}</option>)}
            </select>
          </div>
        </div>
        {error && <p role="alert" className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        {loading ? <div className="h-72 animate-pulse rounded-xl bg-slate-100" /> : chartData.length ? (
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="label" minTickGap={24} tick={{ fontSize: 11 }} />
                <YAxis domain={metric === 'marks' ? [0, 100] : [0, 100]} unit="%" />
                <Tooltip />
                <Legend />
                {SUBJECTS.map((subjectName, index) => (
                  <Line key={subjectName} type="monotone" connectNulls dataKey={subjectName} stroke={['#2563eb', '#14b8a6', '#f59e0b', '#a855f7'][index]} strokeWidth={2} dot={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex h-64 flex-col items-center justify-center text-center text-slate-500"><Activity className="mb-2 h-8 w-8" /><p>No records are available for this period.</p></div>
        )}
      </section>

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-slate-900">Student risk growth</h2>
          <p className="mb-3 text-sm text-slate-500">Higher means more students have low marks and/or attendance. This is a support signal, not a judgment.</p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="label" minTickGap={24} tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} unit="%" />
                <Tooltip />
                <Line type="monotone" dataKey="risk" name="Risk indicator" stroke="#ef4444" strokeWidth={3} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
        <section className="overflow-x-auto rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-slate-900">Latest subject summary</h2>
          {latest ? (
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b text-slate-500"><th className="py-2">Subject</th><th>Attendance</th><th>Average marks</th></tr></thead>
              <tbody>
                {SUBJECTS.map((name) => (
                  <tr key={name} className="border-b last:border-0">
                    <td className="py-3 font-semibold">{name}</td>
                    <td>{latest.subjects[name]?.attendance == null ? '—' : `${latest.subjects[name].attendance}%`}</td>
                    <td>{latest.subjects[name]?.marks == null ? '—' : `${latest.subjects[name].marks}%`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <p className="text-sm text-slate-500">No current-period summary is available.</p>}
        </section>
      </div>
    </div>
  )
}
