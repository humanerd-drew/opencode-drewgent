/**
 * URL state bridge — copy this into a Svelte 5 component
 * or extract to a shared helper module.
 *
 * pattern: mpa-url-state-bridge
 *
 * usage in <script>:
 *   let urlState = $state(readUrlState())
 *   let menuOpen = $derived(urlState.menu === '1')
 *   function toggleMenu() { setUrlState('menu', menuOpen ? null : '1') }
 *   onMount(() => {
 *     const onPopState = () => { urlState = readUrlState() }
 *     window.addEventListener('popstate', onPopState)
 *     return () => window.removeEventListener('popstate', onPopState)
 *   })
 */
import { onMount } from 'svelte'

export type UrlKey = string  // customize per project

export function createUrlStateBridge(keys: UrlKey[]) {
  function readUrlState(): Record<UrlKey, string | null> {
    if (typeof window === 'undefined') return {} as Record<UrlKey, string | null>
    const p = new URLSearchParams(window.location.search)
    const out: Record<string, string | null> = {}
    for (const k of keys) out[k] = p.get(k)
    return out as Record<UrlKey, string | null>
  }

  function setUrlState(
    key: UrlKey,
    value: string | null,
    opts: { history?: 'push' | 'replace' } = {}
  ): void {
    if (typeof window === 'undefined') return
    const url = new URL(window.location.href)
    if (value === null || value === '' || value === '0' || value === 'false') {
      url.searchParams.delete(key)
    } else {
      url.searchParams.set(key, value)
    }
    const method = opts.history === 'push' ? 'pushState' : 'replaceState'
    window.history[method](null, '', url.toString())
  }

  function attachPopStateListener(onChange: () => void): () => void {
    if (typeof window === 'undefined') return () => {}
    window.addEventListener('popstate', onChange)
    return () => window.removeEventListener('popstate', onChange)
  }

  return { readUrlState, setUrlState, attachPopStateListener }
}
