const PAK_CODE_MESSAGE_MAX_LENGTH = 32

export function pakCodeForMessage(code: string): string {
  return code.length > PAK_CODE_MESSAGE_MAX_LENGTH
    ? `${code.slice(0, PAK_CODE_MESSAGE_MAX_LENGTH - 1)}…`
    : code
}
