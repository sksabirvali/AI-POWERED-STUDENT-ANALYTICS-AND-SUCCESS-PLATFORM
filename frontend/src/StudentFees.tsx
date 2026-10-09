import { useEffect, useMemo, useState } from 'react'
import { WalletCards } from 'lucide-react'
import { readApiResponse } from './api'
import StudentLookup from './StudentLookup'

type Student = {
  student_id: string
  name: string
}

type FeeYear = {
  academic_year: number
  tuition_fee: number
  cultural_activity_fee: number
  activities: { activity_name: string; amount: number }[]
  total_fee: number
  paid_fee: number
  due_fee: number
}

type FeeSummary = {
  student_id: string
  currency: string
  demo_data: boolean
  total_fee: number
  paid_fee: number
  due_fee: number
  years: FeeYear[]
}

type SessionUser = {
  role: 'admin' | 'faculty' | 'student'
  student_id: string | null
  access_token: string
}

const money = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})

function FeeCard({ label, amount, tone }: { label: string; amount: number; tone: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-2 text-2xl font-semibold ${tone}`}>{money.format(amount)}</p>
    </div>
  )
}

export default function StudentFees({ students, user }: { students: Student[]; user: SessionUser }) {
  const editable = user.role === 'admin' || user.role === 'faculty'
  const visibleStudents = useMemo(
    () => user.role === 'student' ? students.filter((student) => student.student_id === user.student_id) : students,
    [students, user.role, user.student_id],
  )
  const [studentId, setStudentId] = useState(user.student_id ?? '')
  const [fees, setFees] = useState<FeeSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (user.role === 'student') setStudentId(user.student_id ?? '')
    else if (!studentId && visibleStudents.length) setStudentId(visibleStudents[0].student_id)
  }, [studentId, user.role, user.student_id, visibleStudents])

  useEffect(() => {
    if (!studentId) {
      setFees(null)
      return
    }
    const controller = new AbortController()
    setLoading(true)
    setError('')
    fetch(`/api/fees?student_id=${encodeURIComponent(studentId)}`, {
      signal: controller.signal,
      headers: { Authorization: `Bearer ${user.access_token}` },
    })
      .then((response) => readApiResponse<FeeSummary>(response))
      .then(setFees)
      .catch((fetchError: Error) => {
        if (fetchError.name !== 'AbortError') setError(fetchError.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [studentId, user.access_token])

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.25em] text-blue-600">Student account</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">Fees & Due Balance</h1>
          <p className="mt-2 text-sm text-slate-600">Year-wise tuition fee summary for the four-year student journey.</p>
        </div>
        {editable && (
          <label className="text-sm text-slate-600">Student
            <StudentLookup value={studentId} accessToken={user.access_token} onChange={setStudentId} />
          </label>
        )}
      </header>

      <div role="note" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        These are randomly generated demo amounts for display only. They are not official fee statements, payment records, or a payment request.
      </div>

      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {loading ? <div className="h-36 animate-pulse rounded-2xl bg-slate-200" /> : fees ? (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <FeeCard label="Total fees (4 years)" amount={fees.total_fee} tone="text-slate-900" />
            <FeeCard label="Paid amount (sample)" amount={fees.paid_fee} tone="text-emerald-700" />
            <FeeCard label="Due balance (sample)" amount={fees.due_fee} tone={fees.due_fee > 0 ? 'text-red-700' : 'text-emerald-700'} />
          </div>

          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-100 text-blue-700"><WalletCards className="h-5 w-5" /></div>
              <div>
                <h2 className="font-semibold text-slate-900">Year-wise fee details</h2>
                <p className="text-sm text-slate-500">Student ID: {fees.student_id}</p>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px] text-left text-sm">
                <thead className="bg-slate-50 text-slate-500">
                  <tr><th className="px-3 py-3">Academic year</th><th className="px-3 py-3">Tuition</th><th className="px-3 py-3">Cultural activities</th><th className="px-3 py-3">Total fee</th><th className="px-3 py-3">Paid</th><th className="px-3 py-3">Due</th><th className="px-3 py-3">Status</th></tr>
                </thead>
                <tbody>
                  {fees.years.map((year) => (
                    <tr key={year.academic_year} className="border-t border-slate-100">
                      <td className="px-3 py-3 font-medium text-slate-800">{year.academic_year}</td>
                      <td className="px-3 py-3">{money.format(year.tuition_fee)}</td>
                      <td className="px-3 py-3">
                        <div className="font-medium">{money.format(year.cultural_activity_fee)}</div>
                        <ul className="mt-1 space-y-1 text-xs text-slate-500">
                          {year.activities.map((activity) => (
                            <li key={activity.activity_name}>{activity.activity_name}: {money.format(activity.amount)}</li>
                          ))}
                        </ul>
                      </td>
                      <td className="px-3 py-3">{money.format(year.total_fee)}</td>
                      <td className="px-3 py-3 text-emerald-700">{money.format(year.paid_fee)}</td>
                      <td className="px-3 py-3 font-medium text-red-700">{money.format(year.due_fee)}</td>
                      <td className="px-3 py-3"><span className={`rounded-full px-2 py-1 text-xs font-medium ${year.due_fee ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'}`}>{year.due_fee ? 'Balance shown' : 'Sample paid in full'}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : !error ? <p className="text-sm text-slate-500">No fee sample is available for this student.</p> : null}
    </div>
  )
}
