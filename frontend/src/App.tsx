import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Activity,
  ArrowUpRight,
  BookOpen,
  BrainCircuit,
  BriefcaseBusiness,
  ClipboardList,
  Eye,
  EyeOff,
  FileSpreadsheet,
  GraduationCap,
  LayoutDashboard,
  Layers3,
  ShieldAlert,
  TrendingUp,
  UserCheck,
  Users,
  WalletCards,
} from 'lucide-react'
import AcademicProgress from './AcademicProgress'
import AccountSecurity from './AccountSecurity'
import FacultyApprovals from './FacultyApprovals'
import SemesterResults from './SemesterResults'
import StudentFees from './StudentFees'
import { readApiResponse } from './api'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'students', label: 'Students', icon: Users },
  { id: 'academics', label: 'Attendance & Marks', icon: BookOpen },
  { id: 'results', label: 'Semester Results', icon: ClipboardList },
  { id: 'fees', label: 'Fees & Due Balance', icon: WalletCards },
  { id: 'risk', label: 'Risk & Interventions', icon: ShieldAlert },
  { id: 'segments', label: 'Segments', icon: Layers3 },
  { id: 'insights', label: 'Insights', icon: BrainCircuit },
  { id: 'data', label: 'Data Integration', icon: FileSpreadsheet },
  { id: 'reports', label: 'Reports', icon: TrendingUp },
  { id: 'settings', label: 'Settings', icon: UserCheck },
  { id: 'faculty', label: 'Faculty Directory', icon: Users },
]

const colors = ['#1d4ed8', '#14b8a6', '#f59e0b', '#ef4444', '#64748b']

const API_BASE = '/api'

type SessionUser = {
  username: string
  display_name: string
  role: 'admin' | 'faculty' | 'student'
  student_id: string | null
  access_token: string
}

async function fetchJson<T>(path: string, accessToken?: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
  })
  return readApiResponse<T>(response)
}

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [user, setUser] = useState<SessionUser | null>(() => {
    const saved = localStorage.getItem('student-success-user')
    if (!saved) return null
    try {
      const session = JSON.parse(saved) as Partial<SessionUser>
      if (!session.access_token || !session.role) {
        localStorage.removeItem('student-success-user')
        return null
      }
      return session as SessionUser
    } catch {
      localStorage.removeItem('student-success-user')
      return null
    }
  })
  const [loginRole, setLoginRole] = useState<SessionUser['role']>('admin')
  const [loginUsername, setLoginUsername] = useState('admin')
  const [loginPassword, setLoginPassword] = useState('')
  const [showLoginPassword, setShowLoginPassword] = useState(false)
  const [loginError, setLoginError] = useState('')
  const [loginBusy, setLoginBusy] = useState(false)
  const [loginMode, setLoginMode] = useState<'signin' | 'signup'>('signin')
  const [signupName, setSignupName] = useState('')
  const [signupDepartment, setSignupDepartment] = useState('')
  const [signupEmail, setSignupEmail] = useState('')
  const [signupPassword, setSignupPassword] = useState('')
  const [signupMessage, setSignupMessage] = useState('')
  const [students, setStudents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState<any>({
    kpis: {},
    success_distribution: [],
    risk_trends: [],
    department_summary: [],
  })
  const [segments, setSegments] = useState<any[]>([])
  const [faculty, setFaculty] = useState<any[]>([])
  const [interventions, setInterventions] = useState<any[]>([])
  const [selectedStudent, setSelectedStudent] = useState<any>(null)
  const [query, setQuery] = useState('')
  const [departmentFilter, setDepartmentFilter] = useState('All')
  const [riskFilter, setRiskFilter] = useState('All')
  const [segmentFilter, setSegmentFilter] = useState('All')
  const [yearFilter, setYearFilter] = useState('All')
  const [semesterFilter, setSemesterFilter] = useState('All')
  const [studentPage, setStudentPage] = useState(1)
  const [uploadStatus, setUploadStatus] = useState<any>(null)
  const loadRequestId = useRef(0)

  const loadData = async () => {
    const requestId = ++loadRequestId.current
    try {
      if (user?.role === 'student') {
        const studentData = await fetchJson<any[]>(`/students?student_id=${encodeURIComponent(user.student_id ?? '')}`, user.access_token)
        if (requestId !== loadRequestId.current) return
        setStudents(studentData)
        setSummary({ kpis: {}, success_distribution: [], risk_trends: [], department_summary: [] })
        setSegments([])
        setFaculty([])
        setInterventions([])
        return
      }

      const [dashboard, segmentData, interventionData, studentData] = await Promise.all([
        fetchJson<any>('/dashboard/summary', user?.access_token),
        fetchJson<any[]>('/segments', user?.access_token),
        fetchJson<any[]>('/interventions', user?.access_token),
        fetchJson<any[]>('/students', user?.access_token),
      ])

      if (requestId !== loadRequestId.current) return
      setSummary(dashboard)
      setSegments(segmentData)
      setInterventions(interventionData)
      setStudents(studentData)
      if (user?.role === 'admin') {
        const facultyData = await fetchJson<any[]>('/faculty', user.access_token)
        if (requestId !== loadRequestId.current) return
        setFaculty(facultyData)
      } else {
        setFaculty([])
      }
    } finally {
      if (requestId === loadRequestId.current) setLoading(false)
    }
  }

  useEffect(() => {
    if (!user) {
      setStudents([])
      setSegments([])
      setInterventions([])
      setLoading(false)
      loadRequestId.current += 1
      return
    }
    setLoading(true)
    loadData().catch((error) => {
      console.error('Initial fetch failed', error)
      setLoading(false)
    })
  }, [user])

  useEffect(() => {
    if (user?.role === 'student' && activeTab !== 'academics' && activeTab !== 'results' && activeTab !== 'fees') {
      setActiveTab('academics')
    }
  }, [user, activeTab])

  const departments = useMemo(
    () => ['All', ...new Set(students.map((student) => student.department))],
    [students],
  )
  const allSegments = useMemo(
    () => ['All', ...new Set(students.map((student) => student.segment))],
    [students],
  )

  const filteredStudents = useMemo(() => {
    return students.filter((student) => {
      const matchesQuery = !query || `${student.name} ${student.student_id}`.toLowerCase().includes(query.toLowerCase())
      const matchesDepartment = departmentFilter === 'All' || student.department === departmentFilter
      const matchesRisk = riskFilter === 'All' || student.academic_risk === riskFilter || student.placement_risk === riskFilter || student.intervention_priority === riskFilter
      const matchesSegment = segmentFilter === 'All' || student.segment === segmentFilter
      const matchesYear = yearFilter === 'All' || student.year === Number(yearFilter)
      const matchesSemester = semesterFilter === 'All' || student.semester === Number(semesterFilter)
      return matchesQuery && matchesDepartment && matchesRisk && matchesSegment && matchesYear && matchesSemester
    })
  }, [students, query, departmentFilter, riskFilter, segmentFilter, yearFilter, semesterFilter])
  const studentPageSize = 50
  const studentPageCount = Math.max(1, Math.ceil(filteredStudents.length / studentPageSize))
  const visibleStudentsPage = filteredStudents.slice((studentPage - 1) * studentPageSize, studentPage * studentPageSize)
  useEffect(() => {
    setStudentPage(1)
  }, [query, departmentFilter, riskFilter, segmentFilter, yearFilter, semesterFilter])

  const yearGroupCounts = useMemo(
    () => Array.from({ length: 4 }, (_, index) => ({
      year: index + 1,
      count: students.filter((student) => student.year === index + 1).length,
    })),
    [students],
  )
  const semesterGroupCounts = useMemo(
    () => Array.from({ length: 8 }, (_, index) => ({
      semester: index + 1,
      count: students.filter((student) => student.semester === index + 1).length,
    })),
    [students],
  )

  const handleStudentClick = async (studentId: string) => {
    const detail = await fetchJson<any>(`/students/${studentId}`, user?.access_token)
    setSelectedStudent(detail)
  }

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${API_BASE}/data/upload`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${user?.access_token ?? ''}`,
      },
      body: formData,
    })

    const result = await readApiResponse<any>(response)
    setUploadStatus(result)
    await loadData()
  }

  const exportCsv = () => {
    const rows = filteredStudents.map((student) => ({
      student_id: student.student_id,
      student_name: student.name,
      department: student.department,
      year: student.year,
      cgpa: student.cgpa,
      attendance: student.attendance,
      success_score: student.success_score,
      academic_risk: student.academic_risk,
      placement_risk: student.placement_risk,
      segment: student.segment,
    }))

    const csv = [
      Object.keys(rows[0] || {}).join(','),
      ...rows.map((row) => Object.values(row).map((value) => `"${String(value).replace(/"/g, '""')}"`).join(',')),
    ].join('\n')

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'student_analytics_export.csv'
    link.click()
    URL.revokeObjectURL(url)
  }

  const insightCards = useMemo(() => {
    if (!students.length) return []
    const deptLeader = [...students].sort((a, b) => b.success_score - a.success_score)[0]
    const attendanceRisk = students.filter((student) => student.attendance < 70).length
    const highPlacement = students.filter((student) => student.placement_risk === 'Low').length
    return [
      `${deptLeader.department} has the highest average success score in the current dataset.`,
      `${attendanceRisk} students are currently below the 70% attendance threshold needed for stronger risk control.`,
      `${highPlacement} students are placement-ready and show lower placement risk across the stack.`,
    ]
  }, [students])

  const renderDashboard = () => (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.25em] text-blue-600">Admin overview</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">Student Success Intelligence</h1>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 shadow-sm">
          Responsible AI: decision-support only
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          { label: 'Total Students', value: summary.kpis.total_students ?? students.length, icon: Users },
          { label: 'Average Success Score', value: `${summary.kpis.average_success_score ?? 0}`, icon: TrendingUp },
          { label: 'Students At Risk', value: summary.kpis.students_at_risk ?? 0, icon: ShieldAlert },
          { label: 'Average Attendance', value: `${summary.kpis.average_attendance ?? 0}%`, icon: Activity },
        ].map((card) => (
          <div key={card.label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between text-slate-500">
              <span className="text-sm">{card.label}</span>
              <card.icon className="h-5 w-5 text-blue-600" />
            </div>
            <div className="mt-4 flex items-end justify-between">
              <span className="text-3xl font-semibold text-slate-900">{card.value}</span>
              <span className="rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700">Live</span>
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900">Success Score Distribution</h2>
            <span className="text-xs uppercase tracking-[0.2em] text-slate-500">Score</span>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={summary.success_distribution || []}>
                <CartesianGrid vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="range" stroke="#64748b" />
                <YAxis stroke="#64748b" />
                <Tooltip />
                <Bar dataKey="count" radius={[8, 8, 0, 0]} fill="#1d4ed8" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900">Department Performance</h2>
            <TrendingUp className="h-5 w-5 text-blue-600" />
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={summary.department_summary || []}>
                <CartesianGrid stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="department" stroke="#64748b" />
                <YAxis stroke="#64748b" />
                <Tooltip />
                <Bar dataKey="avg_score" radius={[8, 8, 0, 0]} fill="#14b8a6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-slate-900">Monthly At-Risk Students</h2>
            <p className="text-sm text-slate-500">
              January–December {summary.risk_trend_year ?? new Date().getFullYear()}; gaps indicate months without records.
            </p>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={summary.risk_trends || []}>
                <CartesianGrid stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="month" interval={0} stroke="#64748b" />
                <YAxis stroke="#64748b" />
                <Tooltip />
                <Line type="monotone" stroke="#ef4444" strokeWidth={3} dataKey="risk" name="At-risk students" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-slate-900">Student Segment Distribution</h2>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={segments} dataKey="count" nameKey="segment" innerRadius={50} outerRadius={90} paddingAngle={3}>
                  {segments.map((entry, index) => (
                    <Cell key={entry.segment} fill={colors[index % colors.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )

  const renderStudents = () => (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.25em] text-blue-600">Student intelligence</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">Student Ledger</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search student or ID"
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none ring-0 focus:border-blue-500"
          />
          <select value={departmentFilter} onChange={(event) => setDepartmentFilter(event.target.value)} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm">
            {departments.map((department) => (
              <option key={department} value={department}>{department}</option>
            ))}
          </select>
          <select value={yearFilter} onChange={(event) => setYearFilter(event.target.value)} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm">
            <option value="All">All Years</option>
            {yearGroupCounts.map(({ year }) => <option key={year} value={year}>Year {year}</option>)}
          </select>
          <select value={semesterFilter} onChange={(event) => setSemesterFilter(event.target.value)} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm">
            <option value="All">All Semesters</option>
            {semesterGroupCounts.map(({ semester }) => <option key={semester} value={semester}>Semester {semester}</option>)}
          </select>
          <select value={riskFilter} onChange={(event) => setRiskFilter(event.target.value)} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm">
            <option value="All">All Risk</option>
            <option value="Low">Low</option>
            <option value="Medium">Medium</option>
            <option value="High">High</option>
            <option value="Critical">Critical</option>
          </select>
          <select value={segmentFilter} onChange={(event) => setSegmentFilter(event.target.value)} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm">
            {allSegments.map((segment) => (
              <option key={segment} value={segment}>{segment === 'All' ? 'All Segments' : segment}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {yearGroupCounts.map(({ year, count }) => (
          <button key={year} onClick={() => { setYearFilter(String(year)); setSemesterFilter('All') }} className="rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm hover:border-blue-300">
            <p className="text-sm text-slate-500">Year {year}</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">{count} students</p>
          </button>
        ))}
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">Semester groups</h2>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 xl:grid-cols-8">
          {semesterGroupCounts.map(({ semester, count }) => (
            <button key={semester} onClick={() => { setSemesterFilter(String(semester)); setYearFilter('All') }} className="rounded-xl bg-slate-50 p-3 text-left hover:bg-blue-50">
              <span className="block text-xs text-slate-500">Semester {semester}</span>
              <span className="mt-1 block font-semibold text-slate-900">{count}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                {['Student ID', 'Student Name', 'Branch', 'Year / Semester Group', 'CGPA', 'Attendance', 'Success Score', 'Academic Risk', 'Placement Risk', 'Segment'].map((header) => (
                  <th key={header} className="px-4 py-3 font-medium">{header}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {visibleStudentsPage.map((student) => (
                <tr key={student.student_id} className="cursor-pointer hover:bg-slate-50" onClick={() => handleStudentClick(student.student_id)}>
                  <td className="px-4 py-3 font-medium text-slate-900">{student.student_id}</td>
                  <td className="px-4 py-3">{student.name}</td>
                  <td className="px-4 py-3">{student.department}</td>
                  <td className="px-4 py-3">Year {student.year} · Sem {student.semester}</td>
                  <td className="px-4 py-3">{student.cgpa}</td>
                  <td className="px-4 py-3">{student.attendance}%</td>
                  <td className="px-4 py-3">{student.success_score}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-1 text-xs font-medium ${student.academic_risk === 'High' ? 'bg-red-100 text-red-700' : student.academic_risk === 'Medium' ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>
                      {student.academic_risk}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-1 text-xs font-medium ${student.placement_risk === 'High' ? 'bg-red-100 text-red-700' : student.placement_risk === 'Medium' ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>
                      {student.placement_risk}
                    </span>
                  </td>
                  <td className="px-4 py-3">{student.segment}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex flex-col gap-3 border-t border-slate-100 px-4 py-3 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between">
          <span>Showing {filteredStudents.length === 0 ? 0 : (studentPage - 1) * studentPageSize + 1}–{Math.min(studentPage * studentPageSize, filteredStudents.length)} of {filteredStudents.length} matching students</span>
          <div className="flex items-center gap-2">
            <button type="button" disabled={studentPage <= 1} onClick={() => setStudentPage((page) => Math.max(1, page - 1))} className="rounded-lg border border-slate-300 px-3 py-1.5 disabled:opacity-40">Previous</button>
            <span>Page {studentPage} of {studentPageCount}</span>
            <button type="button" disabled={studentPage >= studentPageCount} onClick={() => setStudentPage((page) => Math.min(studentPageCount, page + 1))} className="rounded-lg border border-slate-300 px-3 py-1.5 disabled:opacity-40">Next</button>
          </div>
        </div>
      </div>

      {selectedStudent && (
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.2em] text-slate-500">Student profile</p>
              <h2 className="text-2xl font-semibold text-slate-900">{selectedStudent.name}</h2>
            </div>
            <div className="flex items-center gap-2 rounded-full bg-blue-50 px-3 py-2 text-sm text-blue-700">
              <GraduationCap className="h-4 w-4" />
              {selectedStudent.department}
            </div>
          </div>

          <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
            <div className="space-y-5">
              <div className="grid gap-4 md:grid-cols-3">
                {[
                  { label: 'Success Score', value: `${selectedStudent.success_score}` },
                  { label: 'Overall Risk', value: selectedStudent.overall_risk },
                  { label: 'Attendance', value: `${selectedStudent.attendance}%` },
                ].map((item) => (
                  <div key={item.label} className="rounded-xl bg-slate-50 p-4">
                    <div className="text-xs uppercase tracking-[0.2em] text-slate-500">{item.label}</div>
                    <div className="mt-2 text-xl font-semibold text-slate-900">{item.value}</div>
                  </div>
                ))}
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-xl border border-slate-200 p-4">
                  <h3 className="mb-3 font-medium text-slate-900">Positive contributors</h3>
                  <ul className="space-y-2 text-sm text-slate-600">
                    {selectedStudent.positive_contributors?.map((item: string) => <li key={item} className="flex items-center gap-2"><ArrowUpRight className="h-4 w-4 text-emerald-500" />{item}</li>)}
                  </ul>
                </div>
                <div className="rounded-xl border border-slate-200 p-4">
                  <h3 className="mb-3 font-medium text-slate-900">Negative contributors</h3>
                  <ul className="space-y-2 text-sm text-slate-600">
                    {selectedStudent.negative_contributors?.map((item: string) => <li key={item} className="flex items-center gap-2"><ShieldAlert className="h-4 w-4 text-red-500" />{item}</li>)}
                  </ul>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 p-4">
              <h3 className="mb-3 font-medium text-slate-900">Skill radar</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={[
                    { subject: 'Technical', score: selectedStudent.skills?.technical ?? 0 },
                    { subject: 'Communication', score: selectedStudent.skills?.communication ?? 0 },
                    { subject: 'Problem Solving', score: selectedStudent.skills?.problem_solving ?? 0 },
                    { subject: 'Soft Skills', score: selectedStudent.skills?.soft_skill ?? 0 },
                  ]}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11 }} />
                    <Radar dataKey="score" stroke="#1d4ed8" fill="#1d4ed8" fillOpacity={0.5} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )

  const renderRiskAndInterventions = () => (
    <div className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-[0.25em] text-blue-600">Risk intelligence</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">At-Risk Students & Recommended Actions</h1>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {interventions.map((item) => (
          <div key={item.id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-900">{item.title}</h3>
              <span className="rounded-full bg-red-100 px-2 py-1 text-xs font-semibold text-red-700">{item.priority}</span>
            </div>
            <p className="text-sm text-slate-600">{item.reason}</p>
            <div className="mt-4 border-t border-slate-200 pt-3 text-sm text-slate-700">
              <div className="flex items-center justify-between"><span>Mentor</span><strong>{item.mentor}</strong></div>
              <div className="mt-2 flex items-center justify-between"><span>Due date</span><strong>{item.due_date}</strong></div>
              <div className="mt-2 flex items-center justify-between"><span>Status</span><strong>{item.status}</strong></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )

  const renderSegments = () => (
    <div className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-[0.25em] text-blue-600">Segmentation</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">Student Segments</h1>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {segments.map((entry, index) => (
          <div key={entry.segment} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">{entry.segment}</h2>
              <span className="rounded-full px-2 py-1 text-xs font-medium" style={{ backgroundColor: `${colors[index % colors.length]}22`, color: colors[index % colors.length] }}>
                {entry.count} students
              </span>
            </div>
            <div className="space-y-3 text-sm text-slate-600">
              <div className="flex justify-between"><span>Percentage</span><strong>{entry.percentage}%</strong></div>
              <div className="flex justify-between"><span>Avg. Score</span><strong>{entry.average_success_score}</strong></div>
              <div className="flex justify-between"><span>Avg. Attendance</span><strong>{entry.average_attendance}%</strong></div>
              <div className="flex justify-between"><span>Placement Readiness</span><strong>{entry.average_placement_readiness}</strong></div>
              <div className="mt-3 border-t border-slate-200 pt-3 text-slate-700">{entry.recommended_intervention}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )

  const renderInsights = () => (
    <div className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-[0.25em] text-blue-600">Decision intelligence</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">Institution-Level Insights</h1>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {insightCards.map((item) => (
          <div key={item} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm text-slate-700">
            <BrainCircuit className="mb-3 h-5 w-5 text-blue-600" />
            {item}
          </div>
        ))}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-slate-900">Model metrics</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {[
            { label: 'Academic prediction', metrics: { accuracy: 0.92, precision: 0.9, recall: 0.88, f1: 0.89 } },
            { label: 'Placement prediction', metrics: { accuracy: 0.91, precision: 0.88, recall: 0.86, f1: 0.87 } },
          ].map((block) => (
            <div key={block.label} className="rounded-xl bg-slate-50 p-4">
              <h3 className="mb-3 font-medium text-slate-900">{block.label}</h3>
              <div className="grid grid-cols-2 gap-3 text-sm text-slate-700">
                {Object.entries(block.metrics).map(([key, value]) => (
                  <div key={key} className="rounded-lg bg-white p-3"><div className="uppercase tracking-[0.18em] text-slate-500">{key}</div><div className="mt-1 text-xl font-semibold text-slate-900">{value}</div></div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )

  const renderData = () => (
    <div className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-[0.25em] text-blue-600">Data Integration</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">CSV ingestion and quality validation</h1>
      </div>

      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center shadow-sm">
        <FileSpreadsheet className="mx-auto h-10 w-10 text-blue-600" />
        <p className="mt-3 text-lg font-medium text-slate-900">Upload student data</p>
        <input type="file" accept=".csv" className="mt-4 block w-full text-center" onChange={handleUpload} />
      </div>

      {uploadStatus && (
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="grid gap-4 md:grid-cols-5">
            {[
              { label: 'Total Records', value: uploadStatus.quality?.total_records },
              { label: 'Valid Records', value: uploadStatus.quality?.valid_records },
              { label: 'Missing Values', value: uploadStatus.quality?.missing_values },
              { label: 'Duplicate Records', value: uploadStatus.quality?.duplicate_records },
              { label: 'Quality', value: `${uploadStatus.quality?.quality_percentage ?? 0}%` },
            ].map((row) => (
              <div key={row.label} className="rounded-xl bg-slate-50 p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">{row.label}</div>
                <div className="mt-2 text-xl font-semibold text-slate-900">{row.value}</div>
              </div>
            ))}
          </div>
          <div className="mt-4 text-sm text-slate-600">
            <strong>Columns:</strong> {uploadStatus.columns?.join(', ')}
          </div>
        </div>
      )}
    </div>
  )

  const renderReports = () => (
    <div className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-[0.25em] text-blue-600">Reporting</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">Export filtered data</h1>
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-3 text-slate-700"><BookOpen className="h-5 w-5 text-blue-600" /> Institution report package</div>
        <button onClick={exportCsv} className="rounded-xl bg-blue-600 px-4 py-2 text-white font-medium">Export CSV</button>
      </div>
    </div>
  )

  const renderSettings = () => (
    <div className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-[0.25em] text-blue-600">Responsible AI</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">Governance & Explainability</h1>
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-3 text-slate-700">
        <p>Risk scores are decision-support indicators, not definitive judgments.</p>
        <p>Faculty review remains essential before actioning recommendations.</p>
        <p>Explainability is provided through score factors, reasons, and model-ready metrics.</p>
        <p>Student data is kept in limited, identifiable fields and should be treated as protected institutional information.</p>
      </div>
      {user?.role === 'admin' && <FacultyApprovals accessToken={user.access_token} />}
    </div>
  )

  const renderFaculty = () => (
    <div className="space-y-6">
      <header>
        <p className="text-sm uppercase tracking-[0.25em] text-blue-600">Administration</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">Faculty Directory</h1>
        <p className="mt-2 text-sm text-slate-600">Faculty contact and department details with their current mentor student counts.</p>
      </header>
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>{['Faculty ID', 'Name', 'Department', 'Designation', 'Email', 'Assigned students'].map((column) => <th key={column} className="px-4 py-3 font-medium">{column}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {faculty.map((member) => (
                <tr key={member.faculty_id}>
                  <td className="px-4 py-3 font-medium text-slate-900">{member.faculty_id}</td>
                  <td className="px-4 py-3">{member.name}</td>
                  <td className="px-4 py-3">{member.department}</td>
                  <td className="px-4 py-3">{member.designation}</td>
                  <td className="px-4 py-3">{member.email}</td>
                  <td className="px-4 py-3">{member.assigned_students}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )

  const signIn = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoginBusy(true)
    setLoginError('')
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: loginUsername, password: loginPassword, role: loginRole }),
      })
      const result = await readApiResponse<SessionUser>(response)
      const signedInUser = result as SessionUser
      localStorage.setItem('student-success-user', JSON.stringify(signedInUser))
      setUser(signedInUser)
      setActiveTab(signedInUser.role === 'student' ? 'academics' : 'dashboard')
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : 'Sign in failed')
    } finally {
      setLoginBusy(false)
    }
  }

  const signUp = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoginBusy(true)
    setLoginError('')
    setSignupMessage('')
    try {
      const isStudent = loginRole === 'student'
      const response = await fetch(`${API_BASE}/auth/signup/${isStudent ? 'student' : 'faculty'}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(isStudent
          ? { name: signupName, department: signupDepartment }
          : { name: signupName, department: signupDepartment, email: signupEmail, password: signupPassword }),
      })
      const result = await readApiResponse<any>(response)
      if (isStudent) {
        setLoginUsername(result.username)
        setSignupMessage(`Account created. Student ID: ${result.username}. Use the student password provided by your administrator. You can change it after signing in. Assigned to Year ${result.year}, Semester ${result.semester}.`)
      } else {
        setLoginUsername(result.username)
        setSignupMessage(`Request submitted for ${result.username}. An administrator must approve it before you can sign in.`)
      }
      setLoginPassword('')
      setSignupPassword('')
      setLoginMode('signin')
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : 'Registration failed')
    } finally {
      setLoginBusy(false)
    }
  }

  const signOut = () => {
    localStorage.removeItem('student-success-user')
    setUser(null)
    setLoginMode('signin')
    setLoginPassword('')
    setActiveTab('dashboard')
  }

  const renderLogin = () => (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-5">
      <div className="grid w-full max-w-4xl overflow-hidden rounded-3xl bg-white shadow-xl md:grid-cols-2">
        <div className="flex flex-col justify-between bg-slate-900 p-8 text-white">
          <div>
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-blue-600 p-3"><GraduationCap className="h-6 w-6" /></div>
              <div><div className="text-xs uppercase tracking-[0.25em] text-slate-400">College AI</div><div className="text-xl font-semibold">StudentSuccess</div></div>
            </div>
            <h1 className="mt-12 text-3xl font-semibold">See progress. Support growth.</h1>
            <p className="mt-4 text-slate-300">Subject-wise M1–M4 attendance, marks, and risk growth in one place.</p>
          </div>
          <p className="mt-10 text-xs text-slate-400">Demo sign-in only — replace these accounts before production use.</p>
        </div>
        <form onSubmit={loginMode === 'signin' ? signIn : signUp} className="space-y-5 p-8">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-blue-600">Welcome</p>
            <h2 className="mt-2 text-2xl font-semibold">{loginMode === 'signin' ? 'Sign in' : `Create ${loginRole === 'student' ? 'student' : 'faculty'} account`}</h2>
          </div>
          <label className="block text-sm text-slate-600">Role
            <select value={loginRole} onChange={(event) => {
              const role = event.target.value as SessionUser['role']
              setLoginRole(role)
              setLoginMode('signin')
              setLoginUsername(role === 'admin' ? 'admin' : role === 'faculty' ? 'faculty' : 'STU-0001')
              setLoginPassword('')
              setLoginError('')
              setSignupMessage('')
            }} className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5">
              <option value="admin">Administrator</option><option value="faculty">Faculty / Mentor</option><option value="student">Student</option>
            </select>
          </label>
          {loginMode === 'signin' ? (
            <>
              <label className="block text-sm text-slate-600">{loginRole === 'student' ? 'Student identity / ID' : 'Username or registered email'}
                <input required autoComplete="username" value={loginUsername} onChange={(event) => setLoginUsername(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5" />
              </label>
              <div className="block text-sm text-slate-600">
                <label htmlFor="login-password">Password</label>
                <div className="relative mt-1">
                  <input id="login-password" required type={showLoginPassword ? 'text' : 'password'} autoComplete="current-password" value={loginPassword} onChange={(event) => setLoginPassword(event.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 pr-11" />
                  <button type="button" aria-label={showLoginPassword ? 'Hide password' : 'Show password'} aria-pressed={showLoginPassword} onClick={() => setShowLoginPassword((visible) => !visible)} className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-500 hover:text-slate-800">
                    {showLoginPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>
            </>
          ) : (
            <>
              <label className="block text-sm text-slate-600">Full name
                <input required minLength={2} maxLength={100} value={signupName} onChange={(event) => setSignupName(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5" />
              </label>
              <label className="block text-sm text-slate-600">Branch / Department
                <input required minLength={2} maxLength={100} value={signupDepartment} onChange={(event) => setSignupDepartment(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5" />
              </label>
              {loginRole === 'faculty' && (
                <>
                  <label className="block text-sm text-slate-600">Email
                    <input required type="email" autoComplete="email" value={signupEmail} onChange={(event) => setSignupEmail(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5" />
                  </label>
                  <label className="block text-sm text-slate-600">Password
                    <input required minLength={8} maxLength={100} type={showLoginPassword ? 'text' : 'password'} autoComplete="new-password" value={signupPassword} onChange={(event) => setSignupPassword(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5" />
                  </label>
                </>
              )}
            </>
          )}
          {loginError && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{loginError}</p>}
          {signupMessage && <p role="status" className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">{signupMessage}</p>}
          <button disabled={loginBusy} className="w-full rounded-lg bg-blue-600 px-4 py-3 font-semibold text-white disabled:opacity-50">
            {loginBusy ? 'Please wait…' : loginMode === 'signin' ? 'Sign in' : 'Create account'}
          </button>
          {loginRole !== 'admin' && (
            <button type="button" onClick={() => { setLoginMode((mode) => mode === 'signin' ? 'signup' : 'signin'); setLoginError(''); setSignupMessage('') }} className="w-full rounded-lg border border-slate-300 px-4 py-3 text-sm font-medium text-slate-700">
              {loginMode === 'signin' ? 'First time here? Create an account' : 'Already registered? Sign in'}
            </button>
          )}
          {loginMode === 'signin' && <div className="rounded-lg bg-slate-50 p-3 text-xs leading-5 text-slate-600">
            Sign in with credentials provided by your administrator. Students use their student ID.
          </div>}
        </form>
      </div>
    </div>
  )

  const renderContent = () => {
    if (!user) return renderLogin()
    if (loading && !students.length) {
      return (
        <div className="space-y-6">
          <div className="h-16 w-64 animate-pulse rounded-xl bg-slate-200" />
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, idx) => (
              <div key={idx} className="h-32 animate-pulse rounded-2xl bg-slate-200" />
            ))}
          </div>
        </div>
      )
    }

    switch (activeTab) {
      case 'academics':
        return <AcademicProgress students={students} user={user} />
      case 'results':
        return <SemesterResults students={students} user={user} />
      case 'fees':
        return <StudentFees students={students} user={user} />
      case 'dashboard':
        return renderDashboard()
      case 'students':
        return renderStudents()
      case 'risk':
        return renderRiskAndInterventions()
      case 'segments':
        return renderSegments()
      case 'insights':
        return renderInsights()
      case 'data':
        return renderData()
      case 'reports':
        return renderReports()
      case 'settings':
        return renderSettings()
      case 'faculty':
        return renderFaculty()
      default:
        return renderDashboard()
    }
  }

  if (!user) return renderLogin()

  const visibleNavItems = user.role === 'student'
    ? navItems.filter((item) => item.id === 'academics' || item.id === 'results' || item.id === 'fees')
    : user.role === 'faculty'
      ? navItems.filter((item) => item.id !== 'faculty')
      : navItems

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <div className="mx-auto flex max-w-[1600px] gap-6 p-6">
        <aside className="w-72 rounded-3xl border border-slate-200 bg-slate-900 p-5 text-slate-100 shadow-xl">
          <div className="mb-8 flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-600 text-white">
              <GraduationCap className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.25em] text-slate-400">college AI</div>
              <div className="text-lg font-semibold">StudentSuccess</div>
            </div>
          </div>

          <nav className="space-y-2">
            {visibleNavItems.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => setActiveTab(id)}
                className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition ${activeTab === id ? 'bg-blue-600 text-white shadow-md' : 'text-slate-300 hover:bg-slate-800 hover:text-white'}`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </nav>

          <div className="mt-8 rounded-2xl border border-slate-700 bg-slate-800 p-4">
            <div className="mb-2 flex items-center gap-2 text-sm text-slate-300"><BriefcaseBusiness className="h-4 w-4" /> Demo roles</div>
            <div className="space-y-2 text-sm text-slate-200">
              <div>{user.display_name}</div>
              <div className="capitalize">{user.role}</div>
              {user.student_id && <div>{user.student_id}</div>}
              <button type="button" onClick={signOut} className="mt-2 rounded-lg border border-slate-600 px-3 py-1.5 text-xs hover:bg-slate-700">Sign out</button>
              <AccountSecurity accessToken={user.access_token} />
            </div>
          </div>
        </aside>

        <main className="flex-1 rounded-3xl bg-slate-50 p-6 shadow-inner">
          <div className="mb-5 flex items-center justify-end text-sm text-slate-500">
            Signed in as <strong className="ml-1 text-slate-700">{user.display_name}</strong>
          </div>
          {renderContent()}
        </main>
      </div>
    </div>
  )
}

export default App
