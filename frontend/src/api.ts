export async function readApiResponse<T>(response: Response): Promise<T> {
  const body = await response.text()
  if (!body.trim()) {
    throw new Error(
      response.ok
        ? `The server returned an empty response (HTTP ${response.status}). Please retry; if this continues, check the backend logs.`
        : `The server request failed (HTTP ${response.status}) and returned no error details.`,
    )
  }

  let result: unknown
  try {
    result = JSON.parse(body)
  } catch {
    const preview = body.replace(/\s+/g, ' ').slice(0, 160)
    throw new Error(`The server returned an invalid response (HTTP ${response.status}): ${preview}`)
  }

  if (!response.ok) {
    if (typeof result === 'object' && result !== null && 'detail' in result) {
      const detail = (result as { detail: unknown }).detail
      if (typeof detail === 'string') throw new Error(detail)
      if (Array.isArray(detail)) {
        throw new Error(detail.map((item) => typeof item === 'object' && item !== null && 'msg' in item ? String(item.msg) : String(item)).join('; '))
      }
    }
    throw new Error(`The server request failed (HTTP ${response.status}).`)
  }

  return result as T
}
