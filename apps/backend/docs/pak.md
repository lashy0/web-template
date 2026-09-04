# PAK API guide

This guide describes how a PAK receives an access token and reports a
verification session. The administrator provides the device with:

* `client_id`;
* `client_secret`;
* API base URL, for example `https://api.example.com`.

Keep the `client_secret` in the device's protected configuration. Do not put it
in source code, telemetry, or logs.

## Obtain an access token

Request a token before calling the API:

```console
curl --request POST "https://api.example.com/oauth2/token" \
  --user "$CLIENT_ID:$CLIENT_SECRET" \
  --header "Content-Type: application/x-www-form-urlencoded" \
  --data "grant_type=client_credentials"
```

The response contains an `access_token` and its lifetime in `expires_in`:

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

Request a new token when the current one expires. If the request is rejected,
check that the credentials supplied by the administrator are current.

## Call the API

Send the token with every PAK request:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

The PAK may access only its own verification sessions. A deactivated or
archived PAK cannot call these endpoints, even while it has an unexpired token.

## Verification endpoints

All paths below are relative to the API base URL.

### Open a verification session

`POST /verification/sessions`

```json
{
  "kg_dev_eui": "0011223344556677",
  "slot_no": 1,
  "firmware_version": "1.2.0",
  "total_steps": 3
}
```

`kg_dev_eui` contains exactly 16 hexadecimal characters. Save the `id` from the
response as `session_id`; it is required by the following calls.

### Start a verification step

`POST /verification/sessions/{session_id}/steps`

```json
{
  "step_no": 1,
  "test_name": "INSULATION_RESISTANCE",
  "test_label": "Insulation resistance",
  "error_group_code": "INSULATION"
}
```

`step_no` starts at `1` and must not exceed `total_steps` specified when the
session was opened.

### Complete a verification step

`PUT /verification/sessions/{session_id}/steps/{step_no}`

```json
{
  "status": "PASSED",
  "measurement_value": 12.4,
  "measurement_min_value": 10.0,
  "measurement_max_value": 15.0,
  "measurement_unit": "MOhm"
}
```

Use `PASSED` or `FAILED` for `status`. Measurement fields are optional; when a
range is supplied, `measurement_min_value` cannot be greater than
`measurement_max_value`.

### Complete a verification session

`POST /verification/sessions/{session_id}/complete`

```json
{
  "status": "PASSED"
}
```

Use `PASSED`, `FAILED`, or `ABORTED`. Once completed, a session cannot accept
new steps.
