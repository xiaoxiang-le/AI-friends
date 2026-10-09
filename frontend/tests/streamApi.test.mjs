import { readFile } from 'node:fs/promises'
import vm from 'node:vm'
import assert from 'node:assert/strict'
import { test } from 'node:test'

async function loadStream(fetchEventSource, refresh = async () => ({ data: { access: 'new-token' } })) {
  const user = { accessToken: 'old-token', setAccessToken(token) { this.accessToken = token } }
  const context = vm.createContext({ Error, JSON })
  const source = await readFile(new URL('../src/js/http/streamApi.js', import.meta.url), 'utf8')
  const module = new vm.SourceTextModule(source, { context })
  const dependencies = {
    '@microsoft/fetch-event-source': { fetchEventSource },
    '@/stores/user.js': { useUserStore: () => user },
    './api.js': { default: { post: refresh } },
    '@/js/config/config.js': { default: { HTTP_URL: 'http://127.0.0.1:8000' } },
  }
  await module.link(name => {
    const exports = dependencies[name]
    return new vm.SyntheticModule(Object.keys(exports), function () {
      for (const [key, value] of Object.entries(exports)) this.setExport(key, value)
    }, { context })
  })
  await module.evaluate()
  return { stream: module.namespace.default, user }
}

const response = (status = 200, result = '') => ({ status, ok: status === 200,
  headers: { get: () => status === 200 ? 'text/event-stream' : 'application/json' },
  json: async () => ({ result }) })

test('successful SSE delivers content, completion and cookies', async () => {
  const received = []
  const { stream } = await loadStream(async (url, options) => {
    assert.equal(options.credentials, 'include')
    await options.onopen(response())
    options.onmessage({ data: '{"content":"hello"}' })
    options.onmessage({ data: '[DONE]' })
    options.onclose()
  })
  await stream('/chat', { onmessage: (data, done) => received.push([data, done]) })
  assert.equal(received[0][0].content, 'hello')
  assert.equal(received[1][1], true)
})

test('401 refreshes token once and sends the refreshed authorization', async () => {
  let calls = 0
  const { stream, user } = await loadStream(async (url, options) => {
    calls++
    await options.onopen(response(calls === 1 ? 401 : 200))
    assert.equal(options.headers.Authorization, 'Bearer new-token')
    options.onmessage({ data: '[DONE]' })
    options.onclose()
  })
  await stream('/chat')
  assert.equal(calls, 2)
  assert.equal(user.accessToken, 'new-token')
})

test('persistent 401 stops after one refresh', async () => {
  let calls = 0
  const { stream } = await loadStream(async (url, options) => {
    calls++
    await options.onopen(response(401, 'expired'))
  })
  await assert.rejects(stream('/chat'), /expired/)
  assert.equal(calls, 2)
})

test('configuration failure is surfaced without retry loops', async () => {
  let calls = 0
  let shown = ''
  const { stream } = await loadStream(async (url, options) => {
    calls++
    await options.onopen(response(503, 'AI service not configured'))
  })
  await assert.rejects(stream('/chat', { onerror: error => shown = error.message }), /not configured/)
  assert.equal(calls, 1)
  assert.match(shown, /not configured/)
})

test('SSE provider errors and premature close reject', async () => {
  for (const action of [options => options.onmessage({ data: '{"error":"provider failed"}' }),
                         options => options.onclose()]) {
    const { stream } = await loadStream(async (url, options) => {
      await options.onopen(response())
      action(options)
    })
    await assert.rejects(stream('/chat'))
  }
})

test('closing chat aborts without showing a send failure', async () => {
  let shown = false
  const { stream } = await loadStream(async () => { throw new Error('aborted') })
  await stream('/chat', { signal: { aborted: true }, onerror: () => shown = true })
  assert.equal(shown, false)
})
