import { z } from 'zod'

type IssueCode = z.core.$ZodIssue['code']

export type FieldMessages = Readonly<Record<string, Readonly<Partial<Record<IssueCode, string>>>>>

function characters(count: number): string {
  return count % 10 === 1 && count % 100 !== 11 ? `${count} символа` : `${count} символов`
}

/**
 * Messages of the rules forms take from the generated API schemas, such as
 * `zUserCreate.shape.name`. A pattern has no message a person can act on, so
 * a form names it with `fieldMessages`.
 */
export const validationMessage: z.core.$ZodErrorMap = (issue) => {
  switch (issue.code) {
    case 'too_small':
      if (issue.origin === 'string') {
        return Number(issue.minimum) === 1
          ? 'Заполните поле.'
          : `Не менее ${characters(Number(issue.minimum))}.`
      }
      if (issue.origin === 'array' || issue.origin === 'set') {
        return 'Добавьте хотя бы одно значение.'
      }
      return issue.inclusive ? `Не меньше ${issue.minimum}.` : `Больше ${issue.minimum}.`
    case 'too_big':
      if (issue.origin === 'string') {
        return `Не более ${characters(Number(issue.maximum))}.`
      }
      if (issue.origin === 'array' || issue.origin === 'set') {
        return `Не более ${issue.maximum} значений.`
      }
      return issue.inclusive ? `Не больше ${issue.maximum}.` : `Меньше ${issue.maximum}.`
    case 'invalid_type':
      return issue.input === undefined || issue.input === null || issue.input === ''
        ? 'Заполните поле.'
        : 'Неверное значение.'
    case 'invalid_value':
      return 'Выберите значение из списка.'
    case 'invalid_format':
      return 'Неверный формат.'
    default:
      return undefined
  }
}

export function installValidationMessages(): void {
  z.config(z.locales.ru())
  z.config({ customError: validationMessage })
}

/**
 * An error map for one form, keyed by field path and issue code; pass it as
 * `zodResolver(schema, { error })`. It takes precedence over `validationMessage`.
 */
export function fieldMessages(messages: FieldMessages): z.core.$ZodErrorMap {
  return (issue) => messages[(issue.path ?? []).join('.')]?.[issue.code]
}

/** Trim a text input before checking it against an API field schema. */
export function trimmed<T extends z.core.$ZodType<unknown, string>>(schema: T) {
  return z.string().trim().pipe(schema)
}

/**
 * An optional text input checked against an API field schema such as
 * `zBatchCreate.shape.description`: trimmed, and `null` when left empty, which
 * also clears the value in a PATCH request.
 */
export function optionalText<T extends z.core.$ZodType<unknown, string | null | undefined>>(
  schema: T,
) {
  // An optional API field also accepts undefined, which zod's pipe does not allow for.
  const field = schema as unknown as z.ZodType<z.output<T>, string | null>
  return z
    .string()
    .trim()
    .transform((value) => value || null)
    .pipe(field)
}
