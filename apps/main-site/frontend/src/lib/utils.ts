export const API = '/api'
export const API_BASE = '/api'

export async function apiFetch(path: string, opts?: RequestInit) {
  const headers = new Headers(opts?.headers || {})
  if (!headers.has('Content-Type') && opts?.body && !(opts.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const res = await fetch(API + path, {
    credentials: 'same-origin',
    headers,
    ...opts,
  })
  const contentType = res.headers.get('content-type') || ''

  if (res.status === 401 && !path.startsWith('/auth/')) {
    window.dispatchEvent(new Event('app:unauthorized'))
  }

  if (!res.ok) {
    const errorBody = contentType.includes('application/json')
      ? JSON.stringify(await res.json())
      : await res.text()
    throw new Error(errorBody)
  }
  if (res.status === 204) return null
  if (contentType.includes('application/json')) return res.json()
  return res.text()
}
