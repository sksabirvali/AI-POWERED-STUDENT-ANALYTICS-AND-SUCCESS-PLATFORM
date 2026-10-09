import { useState } from 'react'
import type { FormEvent } from 'react'
import { Bot, Send } from 'lucide-react'
import { readApiResponse } from './api'

type SessionUser = {
  access_token: string
}

type Message = {
  question: string
  answer: string
}

export default function StudentAssistant({ user }: { user: SessionUser }) {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const ask = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const submittedQuestion = question.trim()
    if (!submittedQuestion || busy) return
    setBusy(true)
    setError('')
    try {
      const response = await fetch('/api/student/assistant', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${user.access_token}`,
        },
        body: JSON.stringify({ question: submittedQuestion }),
      })
      const result = await readApiResponse<{ answer: string }>(response)
      setMessages((current) => [...current, { question: submittedQuestion, answer: result.answer }])
      setQuestion('')
    } catch (askError) {
      setError(askError instanceof Error ? askError.message : 'Could not get an answer')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="rounded-2xl border border-blue-100 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-100 text-blue-700"><Bot className="h-5 w-5" /></div>
        <div>
          <h2 className="font-semibold text-slate-900">Student study assistant</h2>
          <p className="text-sm text-slate-500">Ask about your own marks, attendance, results, backlogs, fees, or study suggestions.</p>
        </div>
      </div>
      <div aria-live="polite" className="mb-4 max-h-80 space-y-3 overflow-y-auto">
        {messages.length === 0 && (
          <p className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600">
            Try “How can I improve my marks?” or “What is my attendance?”. This assistant uses your records and built-in study guidance; it does not access other students’ personal information.
          </p>
        )}
        {messages.map((message, index) => (
          <div key={`${index}-${message.question}`} className="space-y-2">
            <p className="ml-auto max-w-[90%] rounded-xl bg-blue-600 p-3 text-sm text-white">{message.question}</p>
            <p className="max-w-[90%] whitespace-pre-wrap rounded-xl bg-slate-100 p-3 text-sm leading-6 text-slate-700">{message.answer}</p>
          </div>
        ))}
      </div>
      {error && <p role="alert" className="mb-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      <form onSubmit={ask} className="flex gap-2">
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          maxLength={500}
          placeholder="Ask about your academic progress…"
          aria-label="Ask the student study assistant"
          className="min-w-0 flex-1 rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500"
        />
        <button disabled={busy || !question.trim()} className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
          <Send className="h-4 w-4" />{busy ? 'Thinking…' : 'Ask'}
        </button>
      </form>
    </section>
  )
}