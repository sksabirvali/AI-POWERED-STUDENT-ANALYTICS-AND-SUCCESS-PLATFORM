import { useEffect, useMemo, useState } from 'react'
import { Save } from 'lucide-react'
import { readApiResponse } from './api'
import StudentLookup from './StudentLookup'

type Student = {
  student_id: string
  name: string
  semester: number
}

type ComponentResult = {
  component_name: string
  mid1_marks: number | null
  mid2_marks: number | null
  semester_exam_marks: number | null
  lab_internal_marks: number | null
  lab_external_marks: number | null
  result_status: 'Passed' | 'Backlog' | 'Not Entered'
}

type SemesterResult = {
  academic_year: number
  semester: number
  subjects: ComponentResult[]
  labs: ComponentResult[]
  passed_count: number
  backlog_count: number
}

type AttendanceYear = {
  year: number
  attendance: number
  attended_sessions: number
  total_sessions: number
  condonation_required: boolean
  condonation_fee: number
}

type ResultsResponse = {
  student_id: string
  attendance_years: AttendanceYear[]
  semesters: SemesterResult[]
}

type SessionUser = {
  role: 'admin' | 'faculty' | 'student'
  student_id: string | null
  access_token: string
}

const SUBJECTS_BY_SEMESTER: Record<number, string[]> = {
  1: ['Engineering Mathematics I', 'Applied Physics', 'Programming Fundamentals', 'Basic Electrical Engineering', 'Engineering Graphics', 'Communication Skills'],
  2: ['Engineering Mathematics II', 'Applied Chemistry', 'Data Structures', 'Basic Electronics', 'Environmental Science', 'Professional Communication'],
  3: ['Discrete Mathematics', 'Digital Logic Design', 'Object-Oriented Programming', 'Computer Organization', 'Probability and Statistics', 'Data Structures and Algorithms'],
  4: ['Design and Analysis of Algorithms', 'Database Management Systems', 'Operating Systems', 'Software Engineering', 'Signals and Systems', 'Microprocessors'],
  5: ['Computer Networks', 'Theory of Computation', 'Compiler Design', 'Web Technologies', 'Machine Learning', 'Department Elective I'],
  6: ['Artificial Intelligence', 'Cloud Computing', 'Information Security', 'Mobile Application Development', 'Distributed Systems', 'Department Elective II'],
  7: ['Big Data Analytics', 'Internet of Things', 'DevOps Engineering', 'Data Mining', 'Project Phase I', 'Department Elective III'],
  8: ['Professional Ethics', 'Entrepreneurship', 'Project Phase II', 'Industry Internship', 'Department Elective IV', 'Emerging Technologies'],
}
const LABS_BY_SEMESTER: Record<number, string[]> = {
  1: ['Engineering Physics Lab', 'Programming Lab I', 'Workshop Practice'],
  2: ['Applied Chemistry Lab', 'Data Structures Lab', 'Electronics Lab'],
  3: ['Object-Oriented Programming Lab', 'Digital Systems Lab', 'Algorithms Lab'],
  4: ['Database Systems Lab', 'Operating Systems Lab', 'Microprocessors Lab'],
  5: ['Computer Networks Lab', 'Compiler Design Lab', 'Web Technologies Lab'],
  6: ['Artificial Intelligence Lab', 'Cloud Computing Lab', 'Mobile Applications Lab'],
  7: ['Big Data Lab', 'Internet of Things Lab', 'Project Lab I'],
  8: ['Advanced Computing Lab', 'Project Lab II', 'Internship Evaluation'],
}
const inputClass = 'mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2'

function displayMarks(value: number | null): string {
  return value == null ? '—' : Number.isInteger(value) ? String(value) : value.toFixed(1)
}

export default function SemesterResults({ students, user }: { students: Student[]; user: SessionUser }) {
  const editable = user.role === 'admin' || user.role === 'faculty'
  const visibleStudents = useMemo(
    () => user.role === 'student' ? students.filter((student) => student.student_id === user.student_id) : students,
    [students, user.role, user.student_id],
  )
  const [studentId, setStudentId] = useState(user.student_id ?? '')
  const [data, setData] = useState<ResultsResponse | null>(null)
  const [selectedSemester, setSelectedSemester] = useState('')
  const [semester, setSemester] = useState(1)
  const [componentType, setComponentType] = useState<'subject' | 'lab'>('subject')
  const [componentName, setComponentName] = useState(SUBJECTS_BY_SEMESTER[1][0])
  const [mid1Marks, setMid1Marks] = useState('')
  const [mid2Marks, setMid2Marks] = useState('')
  const [semesterMarks, setSemesterMarks] = useState('')
  const [internalMarks, setInternalMarks] = useState('')
  const [externalMarks, setExternalMarks] = useState('')
  const [resultStatus, setResultStatus] = useState<'Passed' | 'Backlog'>('Passed')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (user.role === 'student') setStudentId(user.student_id ?? '')
    else if (!studentId && visibleStudents.length) setStudentId(visibleStudents[0].student_id)
  }, [studentId, user.role, user.student_id, visibleStudents])

  useEffect(() => {
    if (!studentId) {
      setData(null)
      return
    }
    const controller = new AbortController()
    setLoading(true)
    setError('')
    fetch(`/api/academic/semester-results?student_id=${encodeURIComponent(studentId)}`, {
      signal: controller.signal,
      headers: { Authorization: `Bearer ${user.access_token}` },
    })
      .then((response) => readApiResponse<ResultsResponse>(response))
      .then((result) => {
        setData(result)
        setSelectedSemester((current) => {
          if (result.semesters.some((item) => item.semester === Number(current))) return current
          const preferred = visibleStudents.find((student) => student.student_id === studentId)?.semester
          if (preferred && result.semesters.some((item) => item.semester === preferred)) return String(preferred)
          return result.semesters.length ? String(result.semesters[result.semesters.length - 1].semester) : ''
        })
      })
      .catch((fetchError: Error) => {
        if (fetchError.name !== 'AbortError') setError(fetchError.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [studentId, user.access_token, visibleStudents])

  const semesterOptions = data?.semesters ?? []
  const currentSemester = semesterOptions.find(
    (item) => item.semester === Number(selectedSemester),
  )
  const academicYear = new Date().getFullYear() - Math.floor((8 - semester) / 2)
  const componentNames = componentType === 'subject' ? SUBJECTS_BY_SEMESTER[semester] : LABS_BY_SEMESTER[semester]

  const saveResult = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!studentId) {
      setError('Select a student before saving a result.')
      return
    }
    setSaving(true)
    setError('')
    setMessage('')
    const toNumberOrNull = (value: string) => value === '' ? null : Number(value)
    try {
      const response = await fetch('/api/academic/semester-results', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${user.access_token}`,
        },
        body: JSON.stringify({
          student_id: studentId,
          academic_year: academicYear,
          semester,
          component_type: componentType,
          component_name: componentName,
          mid1_marks: componentType === 'subject' ? toNumberOrNull(mid1Marks) : null,
          mid2_marks: componentType === 'subject' ? toNumberOrNull(mid2Marks) : null,
          semester_exam_marks: componentType === 'subject' ? toNumberOrNull(semesterMarks) : null,
          lab_internal_marks: componentType === 'lab' ? toNumberOrNull(internalMarks) : null,
          lab_external_marks: componentType === 'lab' ? toNumberOrNull(externalMarks) : null,
          result_status: resultStatus,
        }),
      })
      await readApiResponse<{ message: string }>(response)
      setMessage(`${componentName} result saved for ${studentId}.`)
      setSelectedSemester(String(semester))
      const refresh = await fetch(`/api/academic/semester-results?student_id=${encodeURIComponent(studentId)}`, {
        headers: { Authorization: `Bearer ${user.access_token}` },
      })
      setData(await readApiResponse<ResultsResponse>(refresh))
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not save semester result')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm uppercase tracking-[0.25em] text-blue-600">Student academic record</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">Semester Results & Condonation</h1>
        <p className="mt-2 text-sm text-slate-600">Review semester-wise subject and lab results, backlogs, and yearly attendance.</p>
      </header>

      {editable && (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Enter or update a result</h2>
          <p className="mb-4 text-sm text-slate-500">Staff can record six subject results and three lab results for each semester.</p>
          <form onSubmit={saveResult} className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <label className="text-sm text-slate-600">Student
                <StudentLookup value={studentId} accessToken={user.access_token} onChange={(value) => {
                  setStudentId(value)
                  setSelectedSemester('')
                }} />
              </label>
              <label className="text-sm text-slate-600">Academic year
                <div className={`${inputClass} bg-slate-50 text-slate-500`}>{academicYear}</div>
              </label>
              <label className="text-sm text-slate-600">Semester
                <select value={semester} onChange={(event) => {
                  const nextSemester = Number(event.target.value)
                  setSemester(nextSemester)
                  setComponentName((componentType === 'subject' ? SUBJECTS_BY_SEMESTER[nextSemester] : LABS_BY_SEMESTER[nextSemester])[0])
                }} className={inputClass}>
                  {Array.from({ length: 8 }, (_, index) => index + 1).map((value) => <option key={value} value={value}>Semester {value}</option>)}
                </select>
              </label>
              <label className="text-sm text-slate-600">Component type
                <select value={componentType} onChange={(event) => {
                  const nextType = event.target.value as 'subject' | 'lab'
                  setComponentType(nextType)
                  setComponentName((nextType === 'subject' ? SUBJECTS_BY_SEMESTER[semester] : LABS_BY_SEMESTER[semester])[0])
                }} className={inputClass}>
                  <option value="subject">Subject</option><option value="lab">Lab</option>
                </select>
              </label>
              <label className="text-sm text-slate-600">Component
                <select value={componentName} onChange={(event) => setComponentName(event.target.value)} className={inputClass}>
                  {componentNames.map((name) => <option key={name}>{name}</option>)}
                </select>
              </label>
              {componentType === 'subject' ? (
                <>
                  <label className="text-sm text-slate-600">Mid exam 1 marks
                    <input type="number" min="0" max="100" step="0.5" value={mid1Marks} onChange={(event) => setMid1Marks(event.target.value)} className={inputClass} />
                  </label>
                  <label className="text-sm text-slate-600">Mid exam 2 marks
                    <input type="number" min="0" max="100" step="0.5" value={mid2Marks} onChange={(event) => setMid2Marks(event.target.value)} className={inputClass} />
                  </label>
                  <label className="text-sm text-slate-600">Semester exam marks
                    <input type="number" min="0" max="100" step="0.5" value={semesterMarks} onChange={(event) => setSemesterMarks(event.target.value)} className={inputClass} />
                  </label>
                </>
              ) : (
                <>
                  <label className="text-sm text-slate-600">Lab internal marks
                    <input type="number" min="0" max="100" step="0.5" value={internalMarks} onChange={(event) => setInternalMarks(event.target.value)} className={inputClass} />
                  </label>
                  <label className="text-sm text-slate-600">Lab external marks
                    <input type="number" min="0" max="100" step="0.5" value={externalMarks} onChange={(event) => setExternalMarks(event.target.value)} className={inputClass} />
                  </label>
                </>
              )}
              <label className="text-sm text-slate-600">Result status
                <select value={resultStatus} onChange={(event) => setResultStatus(event.target.value as 'Passed' | 'Backlog')} className={inputClass}>
                  <option value="Passed">Passed</option><option value="Backlog">Backlog</option>
                </select>
              </label>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <button disabled={saving} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 font-medium text-white disabled:opacity-50"><Save className="h-4 w-4" />{saving ? 'Saving…' : 'Save result'}</button>
              {message && <span role="status" className="text-sm text-emerald-700">{message}</span>}
            </div>
          </form>
        </section>
      )}

      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Yearly attendance and condonation</h2>
            <p className="text-sm text-slate-500">Under 75% attendance: ₹2,000 for each started 10 percentage-point shortfall in that year.</p>
          </div>
          {editable && (
            <StudentLookup value={studentId} accessToken={user.access_token} onChange={(value) => {
              setStudentId(value)
              setSelectedSemester('')
            }} />
          )}
        </div>
        {loading ? <div className="h-24 animate-pulse rounded-xl bg-slate-100" /> : data?.attendance_years.length ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {data.attendance_years.map((year) => (
              <div key={year.year} className="rounded-xl border border-slate-200 p-4">
                <p className="text-sm text-slate-500">{year.year} attendance</p>
                <p className="mt-1 text-2xl font-semibold text-slate-900">{year.attendance}%</p>
                <p className="mt-1 text-xs text-slate-500">{year.attended_sessions}/{year.total_sessions} recorded sessions</p>
                <p className={`mt-3 text-sm font-medium ${year.condonation_required ? 'text-red-700' : 'text-emerald-700'}`}>
                  {year.condonation_required ? `Condonation fee: ₹${year.condonation_fee.toLocaleString('en-IN')}` : 'No condonation fee'}
                </p>
              </div>
            ))}
          </div>
        ) : <p className="text-sm text-slate-500">No yearly attendance records are available.</p>}
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Semester results</h2>
            <p className="text-sm text-slate-500">Subject mids and semester exam marks; lab internal and external marks.</p>
          </div>
          <select aria-label="Semester results" value={selectedSemester} onChange={(event) => setSelectedSemester(event.target.value)} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
            {semesterOptions.map((item) => {
              return <option key={item.semester} value={item.semester}>Semester {item.semester} · {item.academic_year}</option>
            })}
          </select>
        </div>
        {loading ? <div className="h-72 animate-pulse rounded-xl bg-slate-100" /> : currentSemester ? (
          <div className="space-y-6">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl bg-slate-50 p-4"><p className="text-sm text-slate-500">Subjects passed</p><p className="mt-1 text-2xl font-semibold">{currentSemester.subjects.filter((item) => item.result_status === 'Passed').length} / 6</p></div>
              <div className="rounded-xl bg-slate-50 p-4"><p className="text-sm text-slate-500">Subject backlogs</p><p className="mt-1 text-2xl font-semibold">{currentSemester.subjects.filter((item) => item.result_status === 'Backlog').length}</p></div>
              <div className="rounded-xl bg-slate-50 p-4"><p className="text-sm text-slate-500">Labs passed</p><p className="mt-1 text-2xl font-semibold">{currentSemester.labs.filter((item) => item.result_status === 'Passed').length} / 3</p></div>
            </div>
            <div>
              <h3 className="mb-2 font-semibold text-slate-800">Subjects</h3>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[650px] text-left text-sm">
                  <thead className="bg-slate-50 text-slate-500"><tr><th className="px-3 py-2">Subject</th><th className="px-3 py-2">Mid 1</th><th className="px-3 py-2">Mid 2</th><th className="px-3 py-2">Semester exam</th><th className="px-3 py-2">Status</th></tr></thead>
                  <tbody>
                    {currentSemester.subjects.map((item) => <tr key={item.component_name} className="border-t border-slate-100"><td className="px-3 py-2 font-medium">{item.component_name}</td><td className="px-3 py-2">{displayMarks(item.mid1_marks)}</td><td className="px-3 py-2">{displayMarks(item.mid2_marks)}</td><td className="px-3 py-2">{displayMarks(item.semester_exam_marks)}</td><td className="px-3 py-2"><span className={`rounded-full px-2 py-1 text-xs font-medium ${item.result_status === 'Backlog' ? 'bg-red-100 text-red-700' : item.result_status === 'Passed' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{item.result_status}</span></td></tr>)}
                  </tbody>
                </table>
              </div>
            </div>
            <div>
              <h3 className="mb-2 font-semibold text-slate-800">Labs</h3>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[550px] text-left text-sm">
                  <thead className="bg-slate-50 text-slate-500"><tr><th className="px-3 py-2">Lab</th><th className="px-3 py-2">Internal</th><th className="px-3 py-2">External</th><th className="px-3 py-2">Status</th></tr></thead>
                  <tbody>
                    {currentSemester.labs.map((item) => <tr key={item.component_name} className="border-t border-slate-100"><td className="px-3 py-2 font-medium">{item.component_name}</td><td className="px-3 py-2">{displayMarks(item.lab_internal_marks)}</td><td className="px-3 py-2">{displayMarks(item.lab_external_marks)}</td><td className="px-3 py-2"><span className={`rounded-full px-2 py-1 text-xs font-medium ${item.result_status === 'Backlog' ? 'bg-red-100 text-red-700' : item.result_status === 'Passed' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{item.result_status}</span></td></tr>)}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ) : <p className="text-sm text-slate-500">No semester results are available yet.</p>}
      </section>
    </div>
  )
}
