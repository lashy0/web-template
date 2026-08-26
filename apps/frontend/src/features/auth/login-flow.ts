import {
  Configuration,
  FetchError,
  FrontendApi,
  ResponseError,
  type LoginFlow as OryLoginFlow,
  type UiNode,
  type UiNodeInputAttributes,
  type UpdateLoginFlowWithPasswordMethod,
  type UiText,
} from '@ory/client-fetch'

const frontend = new FrontendApi(
  new Configuration({
    basePath: window.location.origin,
    credentials: 'include',
  }),
)

const flowReturnTos = new Map<string, string>()

/** Kratos v26.2.0: ErrorValidationInvalidCredentials. */
export const ERROR_VALIDATION_INVALID_CREDENTIALS = 4_000_006

type LoginMessageKind = 'invalid-credentials' | 'unknown'

const KRATOS_LOGIN_MESSAGE_KINDS: Readonly<Record<number, LoginMessageKind>> = {
  [ERROR_VALIDATION_INVALID_CREDENTIALS]: 'invalid-credentials',
}

const LOGIN_MESSAGE_LOCALIZATION: Readonly<Record<LoginMessageKind, string>> = {
  'invalid-credentials': 'Неверный логин или пароль',
  unknown: 'Не удалось выполнить вход. Проверьте данные и повторите попытку.',
}

export type LoginFlow = Readonly<{
  login: Readonly<{
    defaultValue: string
    disabled: boolean
    messages: readonly string[]
  }>
  password: Readonly<{
    disabled: boolean
    messages: readonly string[]
  }>
  messages: readonly string[]
}>

export type LoginCredentials = Readonly<{
  login: string
  password: string
}>

export type LoginSubmission =
  | Readonly<{ kind: 'success'; redirectTo: string }>
  | Readonly<{ kind: 'redirect'; redirectTo: string }>
  | Readonly<{
      kind: 'validation'
      messages: readonly string[]
      loginMessages: readonly string[]
      passwordMessages: readonly string[]
    }>
  | Readonly<{ kind: 'credentials' }>
  | Readonly<{ kind: 'unavailable' }>

type LoginFlowFields = Readonly<{
  csrfToken: string
}>

type PasswordLoginFlowUpdate = Readonly<
  UpdateLoginFlowWithPasswordMethod & {
    method: 'password'
  }
>

type InputNode = UiNode & Readonly<{ attributes: UiNodeInputAttributes }>

export class LoginFlowError extends Error {
  readonly kind: 'restart' | 'unavailable' | 'unsupported'

  constructor(kind: 'restart' | 'unavailable' | 'unsupported') {
    super(
      kind === 'unsupported'
        ? 'Форма входа несовместима с приложением.'
        : 'Не удалось загрузить форму входа. Попробуйте ещё раз.',
    )
    this.name = 'LoginFlowError'
    this.kind = kind
  }
}

export async function loadLoginFlow(flowId: string): Promise<LoginFlow> {
  try {
    const flow = await frontend.getLoginFlow({ id: flowId })
    flowReturnTos.set(flowId, getRedirectTarget(flow.return_to))
    return mapLoginFlow(flow)
  } catch (error) {
    throw toLoginFlowError(error)
  }
}

export async function submitLoginFlow(
  flowId: string,
  credentials: LoginCredentials,
): Promise<LoginSubmission> {
  let flow: OryLoginFlow

  try {
    flow = await frontend.getLoginFlow({ id: flowId })
  } catch (error) {
    return toSubmissionError(error)
  }

  const fields = getLoginFlowFields(flow)
  flowReturnTos.set(flowId, getRedirectTarget(flow.return_to))

  try {
    const update: PasswordLoginFlowUpdate = {
      csrf_token: fields.csrfToken,
      identifier: credentials.login,
      password: credentials.password,
      method: 'password',
    }

    const response = await frontend.updateLoginFlowRaw(
      {
        flow: flowId,
        updateLoginFlowBody: update,
      },
      { headers: { Accept: 'application/json', 'Content-Type': 'application/json' } },
    )

    const redirectedFlow = getRedirectedLoginFlow(response.raw.url)
    if (redirectedFlow) {
      return { kind: 'redirect', redirectTo: redirectedFlow }
    }

    await response.value()
    return { kind: 'success', redirectTo: flowReturnTos.get(flowId) ?? '/' }
  } catch (error) {
    return handleLoginSubmissionError(error)
  }
}

export function mapLoginFlow(flow: OryLoginFlow): LoginFlow {
  getLoginFlowFields(flow)
  const inputs = getInputNodes(flow)
  const login = inputs.find((node) => node.attributes.name === 'identifier')
  const password = inputs.find((node) => node.attributes.name === 'password')

  if (!login || !password) {
    throw new LoginFlowError('unsupported')
  }

  return {
    login: {
      defaultValue: typeof login.attributes.value === 'string' ? login.attributes.value : '',
      disabled: login.attributes.disabled,
      messages: toMessages(login.messages),
    },
    password: {
      disabled: password.attributes.disabled,
      messages: toMessages(password.messages),
    },
    messages: toMessages(flow.ui.messages ?? []),
  }
}

export function restartLoginFlow(flowId?: string) {
  const url = new URL('/self-service/login/browser', window.location.origin)
  const returnTo = flowId ? flowReturnTos.get(flowId) : getReturnToFromLocation()

  if (returnTo && returnTo !== '/') {
    url.searchParams.set('return_to', returnTo)
  }

  window.location.assign(url.href)
}

function getLoginFlowFields(flow: OryLoginFlow): LoginFlowFields {
  if (flow.type !== 'browser' || flow.ui.method.toUpperCase() !== 'POST') {
    throw new LoginFlowError('unsupported')
  }

  const inputs = getInputNodes(flow)
  let csrfToken: string | undefined
  let hasIdentifier = false
  let hasPassword = false
  let hasPasswordMethod = false

  for (const node of inputs) {
    const { attributes } = node

    if (attributes.name === 'csrf_token' && attributes.type === 'hidden') {
      if (typeof attributes.value !== 'string') {
        throw new LoginFlowError('unsupported')
      }
      csrfToken = attributes.value
      continue
    }

    if (attributes.name === 'method' && attributes.type === 'submit') {
      if (attributes.value !== 'password') {
        throw new LoginFlowError('unsupported')
      }
      hasPasswordMethod = true
      continue
    }

    if (attributes.name === 'identifier' && attributes.type === 'text') {
      hasIdentifier = true
      continue
    }

    if (attributes.name === 'password' && attributes.type === 'password') {
      hasPassword = true
      continue
    }

    if (attributes.required) {
      throw new LoginFlowError('unsupported')
    }
  }

  if (!csrfToken || !hasIdentifier || !hasPassword || !hasPasswordMethod) {
    throw new LoginFlowError('unsupported')
  }

  return { csrfToken }
}

function getInputNodes(flow: OryLoginFlow): InputNode[] {
  const inputs = flow.ui.nodes.filter(
    (node): node is InputNode => node.type === 'input' && node.attributes.node_type === 'input',
  )

  if (inputs.length !== flow.ui.nodes.length) {
    throw new LoginFlowError('unsupported')
  }

  return inputs
}

async function handleLoginSubmissionError(error: unknown): Promise<LoginSubmission> {
  if (error instanceof ResponseError) {
    if ([404, 410].includes(error.response.status)) {
      throw new LoginFlowError('restart')
    }

    if (error.response.status === 400) {
      const flow = await readLoginFlow(error.response)
      const mappedFlow = mapLoginFlow(flow)

      if (hasInvalidCredentials(flow)) {
        return { kind: 'credentials' }
      }

      return {
        kind: 'validation',
        messages: mappedFlow.messages,
        loginMessages: mappedFlow.login.messages,
        passwordMessages: mappedFlow.password.messages,
      }
    }

    if (error.response.status === 422) {
      const redirectTo = await readBrowserRedirect(error.response)
      if (redirectTo) {
        return { kind: 'redirect', redirectTo }
      }
    }
  }

  return toSubmissionError(error)
}

async function readLoginFlow(response: Response): Promise<OryLoginFlow> {
  try {
    return (await response.json()) as OryLoginFlow
  } catch {
    throw new LoginFlowError('unavailable')
  }
}

async function readBrowserRedirect(response: Response): Promise<string | undefined> {
  try {
    const payload = (await response.json()) as { redirect_browser_to?: unknown }
    return typeof payload.redirect_browser_to === 'string'
      ? getRedirectTarget(payload.redirect_browser_to)
      : undefined
  } catch {
    return undefined
  }
}

function toLoginFlowError(error: unknown): LoginFlowError {
  if (error instanceof LoginFlowError) {
    return error
  }

  if (error instanceof ResponseError && [400, 404, 410].includes(error.response.status)) {
    return new LoginFlowError('restart')
  }

  if (error instanceof FetchError) {
    return new LoginFlowError('unavailable')
  }

  return new LoginFlowError('unavailable')
}

function toSubmissionError(error: unknown): LoginSubmission {
  const flowError = toLoginFlowError(error)

  if (flowError.kind === 'unavailable') {
    return { kind: 'unavailable' }
  }

  throw flowError
}

function hasInvalidCredentials(flow: OryLoginFlow) {
  return [
    ...(flow.ui.messages ?? []),
    ...flow.ui.nodes.flatMap((node) => node.messages ?? []),
  ].some((message) => getLoginMessageKind(message) === 'invalid-credentials')
}

function toMessages(messages: readonly UiText[]) {
  return messages.map(translateKratosMessage)
}

function getLoginMessageKind(message: Pick<UiText, 'id'>): LoginMessageKind {
  return KRATOS_LOGIN_MESSAGE_KINDS[message.id] ?? 'unknown'
}

function translateKratosMessage(message: Pick<UiText, 'id'>) {
  return LOGIN_MESSAGE_LOCALIZATION[getLoginMessageKind(message)]
}

function getReturnToFromLocation() {
  return getRedirectTarget(new URLSearchParams(window.location.search).get('return_to') ?? '/')
}

function getRedirectedLoginFlow(value: string) {
  const url = new URL(value, window.location.origin)
  return url.origin === window.location.origin &&
    url.pathname === '/login' &&
    url.searchParams.has('flow')
    ? `${url.pathname}${url.search}${url.hash}`
    : undefined
}

function getRedirectTarget(value: string | null | undefined) {
  try {
    const url = new URL(value ?? '/', window.location.origin)
    return url.origin === window.location.origin ? `${url.pathname}${url.search}${url.hash}` : '/'
  } catch {
    return '/'
  }
}
