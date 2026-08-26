import type { LoginFlow as OryLoginFlow } from '@ory/client-fetch'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  ERROR_VALIDATION_INVALID_CREDENTIALS,
  LoginFlowError,
  loadLoginFlow,
  mapLoginFlow,
  submitLoginFlow,
} from '@/features/auth/login-flow'

const validFlow = {
  id: 'login-flow-id',
  return_to: '/users',
  type: 'browser',
  ui: {
    action: '/self-service/login?flow=login-flow-id',
    method: 'POST',
    messages: [],
    nodes: [
      {
        type: 'input',
        messages: [],
        attributes: {
          disabled: false,
          name: 'csrf_token',
          node_type: 'input',
          type: 'hidden',
          value: 'csrf-token',
        },
      },
      {
        type: 'input',
        messages: [],
        attributes: {
          disabled: false,
          name: 'identifier',
          node_type: 'input',
          required: true,
          type: 'text',
          value: 'operator',
        },
      },
      {
        type: 'input',
        messages: [],
        attributes: {
          disabled: false,
          name: 'password',
          node_type: 'input',
          required: true,
          type: 'password',
        },
      },
      {
        type: 'input',
        messages: [],
        attributes: {
          disabled: false,
          name: 'method',
          node_type: 'input',
          type: 'submit',
          value: 'password',
        },
      },
    ],
  },
} as unknown as OryLoginFlow

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('login flow adapter', () => {
  it('maps the browser password flow without exposing Kratos node details', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(jsonResponse(validFlow))
    vi.stubGlobal('fetch', fetchMock)

    await expect(loadLoginFlow('login-flow-id')).resolves.toEqual({
      login: { defaultValue: 'operator', disabled: false, messages: [] },
      password: { disabled: false, messages: [] },
      messages: [],
    })
    expect(fetchMock).toHaveBeenCalledWith(
      `${window.location.origin}/self-service/login/flows?id=login-flow-id`,
      expect.objectContaining({ credentials: 'include', method: 'GET' }),
    )
  })

  it('submits browser credentials through the SDK and returns the Kratos return_to target', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse(validFlow))
      .mockResolvedValueOnce(jsonResponse({}))
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      submitLoginFlow('login-flow-id', { login: 'operator', password: 'secret' }),
    ).resolves.toEqual({ kind: 'success', redirectTo: '/users' })

    const [url, init] = fetchMock.mock.lastCall ?? []
    expect(url).toBe(`${window.location.origin}/self-service/login?flow=login-flow-id`)
    expect(init).toMatchObject({
      credentials: 'include',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      method: 'POST',
    })
    expect(JSON.parse(String(init?.body))).toEqual({
      csrf_token: 'csrf-token',
      identifier: 'operator',
      password: 'secret',
      method: 'password',
    })
  })

  it('translates incorrect credentials without exposing a node-level error', async () => {
    const invalidFlow = {
      ...validFlow,
      ui: {
        ...validFlow.ui,
        messages: [
          {
            id: ERROR_VALIDATION_INVALID_CREDENTIALS,
            text: 'Unexpected source text',
            type: 'error',
          },
        ],
      },
    }
    vi.stubGlobal(
      'fetch',
      vi
        .fn<typeof fetch>()
        .mockResolvedValueOnce(jsonResponse(validFlow))
        .mockResolvedValueOnce(jsonResponse(invalidFlow, 400)),
    )

    await expect(
      submitLoginFlow('login-flow-id', { login: 'operator', password: 'wrong' }),
    ).resolves.toEqual({ kind: 'credentials' })
  })

  it('uses a safe localized fallback for an unknown Kratos message', () => {
    const flowWithUnknownMessage = {
      ...validFlow,
      ui: {
        ...validFlow.ui,
        messages: [{ id: 123_456_789, text: 'Unexpected source text', type: 'error' }],
      },
    } as unknown as OryLoginFlow

    expect(mapLoginFlow(flowWithUnknownMessage)).toMatchObject({
      messages: ['Не удалось выполнить вход. Проверьте данные и повторите попытку.'],
    })
  })

  it('keeps expired flows distinct from temporary submit failures', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 410 })),
    )

    await expect(
      submitLoginFlow('expired-flow', { login: 'operator', password: 'secret' }),
    ).rejects.toMatchObject({ kind: 'restart' })
  })

  it('keeps a network failure on the login form', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn<typeof fetch>()
        .mockResolvedValueOnce(jsonResponse(validFlow))
        .mockRejectedValueOnce(new TypeError('Network unavailable')),
    )

    await expect(
      submitLoginFlow('login-flow-id', { login: 'operator', password: 'secret' }),
    ).resolves.toEqual({ kind: 'unavailable' })
  })

  it('returns Kratos browser redirects to the UI', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn<typeof fetch>()
        .mockResolvedValueOnce(jsonResponse(validFlow))
        .mockResolvedValueOnce(jsonResponse({ redirect_browser_to: '/login?flow=next-flow' }, 422)),
    )

    await expect(
      submitLoginFlow('login-flow-id', { login: 'operator', password: 'secret' }),
    ).resolves.toEqual({ kind: 'redirect', redirectTo: '/login?flow=next-flow' })
  })

  it('rejects unsupported required nodes without retaining sensitive values in the error', () => {
    const incompatibleFlow = {
      ...validFlow,
      ui: {
        ...validFlow.ui,
        nodes: [
          ...validFlow.ui.nodes,
          {
            type: 'input',
            messages: [],
            attributes: {
              disabled: false,
              name: 'passkey',
              node_type: 'input',
              required: true,
              type: 'text',
              value: 'sensitive-value',
            },
          },
        ],
      },
    } as unknown as OryLoginFlow

    const error = captureError(() => mapLoginFlow(incompatibleFlow))
    if (!(error instanceof LoginFlowError)) {
      throw error
    }

    expect(error.message).not.toContain('sensitive-value')
    expect(error).toMatchObject({ kind: 'unsupported' })
  })
})

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function captureError(callback: () => void) {
  try {
    callback()
  } catch (error) {
    return error
  }
  throw new Error('Expected the incompatible contract to fail.')
}
