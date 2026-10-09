import { useState } from 'react'
import type { FormEvent } from 'react'
import { KeyRound } from 'lucide-react'
import { readApiResponse } from './api'

type AccountSecurityProps = {
  accessToken: string
}

export default function AccountSecurity({ accessToken }: AccountSecurityProps) {
  const [open, setOpen] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const changePassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setMessage('')
    setError('')
    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.')
      return
    }
    setSaving(true)
    try {
      const response = await fetch('/api/auth/password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      })
      const result = await readApiResponse<{ message: string }>(response)
      setMessage(result.message)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not update password')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mt-3">
      <button type="button" onClick={() => setOpen((value) => !value)} className="flex items-center gap-2 rounded-lg border border-slate-600 px-3 py-1.5 text-xs hover:bg-slate-700">
        <KeyRound className="h-3.5 w-3.5" />{open ? 'Close password settings' : 'Change personal password'}
      </button>
      {open && (
        <form onSubmit={changePassword} className="mt-3 space-y-2">
          <input required type="password" autoComplete="current-password" minLength={1} value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} placeholder="Current password" aria-label="Current password" className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-xs text-white placeholder:text-slate-400" />
          <input required type="password" autoComplete="new-password" minLength={8} maxLength={100} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} placeholder="New password (8+ characters)" aria-label="New password" className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-xs text-white placeholder:text-slate-400" />
          <input required type="password" autoComplete="new-password" minLength={8} maxLength={100} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Confirm new password" aria-label="Confirm new password" className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-xs text-white placeholder:text-slate-400" />
          {error && <p role="alert" className="text-xs text-red-300">{error}</p>}
          {message && <p role="status" className="text-xs text-emerald-300">{message}</p>}
          <button disabled={saving} className="w-full rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">{saving ? 'Saving…' : 'Update password'}</button>
        </form>
      )}
    </div>
  )
}
