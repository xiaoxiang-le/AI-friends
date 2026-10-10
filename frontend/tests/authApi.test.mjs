import {readFile} from 'node:fs/promises'
import vm from 'node:vm'
import assert from 'node:assert/strict'
import {test} from 'node:test'

async function loadRequestInterceptor() {
  let requestInterceptor
  const context = vm.createContext({Promise, Error})
  const user = {accessToken: 'stale-access-token'}
  const axios = {create: () => ({interceptors: {
    request: {use: callback => {requestInterceptor = callback}},
    response: {use: () => {}},
  }})}
  const module = new vm.SourceTextModule(await readFile(new URL('../src/js/http/api.js', import.meta.url), 'utf8'), {context})
  const dependencies = {
    axios: {default: axios},
    '@/stores/user.js': {useUserStore: () => user},
    '@/js/config/config.js': {default: {HTTP_URL: 'http://127.0.0.1:8000'}},
  }
  await module.link(name => {
    const values = dependencies[name]
    return new vm.SyntheticModule(Object.keys(values), function () {
      for (const [key, value] of Object.entries(values)) this.setExport(key, value)
    }, {context})
  })
  await module.evaluate()
  return requestInterceptor
}

test('login, registration and cookie refresh omit stale access tokens', async () => {
  const intercept = await loadRequestInterceptor()
  for (const endpoint of ['login', 'register', 'refresh_token']) {
    const config = {url: `/api/user/account/${endpoint}/`, headers: {Authorization: 'Bearer stale'}}
    intercept(config)
    assert.equal(config.headers.Authorization, undefined)
  }
})

test('private requests still carry the current access token', async () => {
  const intercept = await loadRequestInterceptor()
  const config = {url: '/api/user/account/get_user_info/', headers: {}}
  intercept(config)
  assert.equal(config.headers.Authorization, 'Bearer stale-access-token')
})
