param([string]$BaseUrl = 'http://127.0.0.1:5173/api/v1')

$ErrorActionPreference = 'Stop'
$healthUrl = $BaseUrl -replace '/api/v1$', '/health'
$health = Invoke-RestMethod -Uri $healthUrl
if ($health.ai_provider -ne 'openai' -or -not $health.ai_ready) {
    throw 'OpenAI is not ready. Set LLM_PROVIDER=openai and LLM_API_KEY in .env, then recreate the backend container.'
}

$email = 'openai-smoke-' + [guid]::NewGuid().ToString('N') + '@example.com'
$registration = Invoke-RestMethod -Method Post -Uri "$BaseUrl/auth/register" -ContentType application/json -Body (@{
    email = $email; password = 'OpenAISmoke123!'; display_name = 'OpenAI Smoke Test'
} | ConvertTo-Json)
$headers = @{ Authorization = 'Bearer ' + $registration.access_token }
$nonce = [guid]::NewGuid().ToString('N').Substring(0, 8)
$response = Invoke-WebRequest -Method Post -Uri "$BaseUrl/tutor/stream" -Headers $headers -ContentType application/json -Body (@{
    session_id = $null
    mode = 'free_conversation'
    message = "Reply naturally as an English tutor. Mention this test marker once: $nonce"
} | ConvertTo-Json)

$eventName = ''
$meta = $null
$done = $null
$tokens = @()
foreach ($line in ($response.Content -split "`n")) {
    if ($line.StartsWith('event: ')) { $eventName = $line.Substring(7).Trim() }
    if ($line.StartsWith('data: ')) {
        $payload = $line.Substring(6) | ConvertFrom-Json
        if ($eventName -eq 'meta') { $meta = $payload }
        elseif ($eventName -eq 'token') { $tokens += [string]$payload.token }
        elseif ($eventName -eq 'done') { $done = $payload }
        elseif ($eventName -eq 'error') { throw "OpenAI request failed: $($payload.message)" }
    }
}

if ($meta.provider -ne 'openai' -or $done.provider -ne 'openai') { throw 'Tutor did not use the OpenAI provider.' }
if (-not ([string]$done.response_id).StartsWith('resp_')) { throw 'OpenAI response id is missing.' }
if ([int]$done.usage.total_tokens -le 0) { throw 'OpenAI token usage is missing.' }
if (($tokens -join '').Length -lt 20) { throw 'OpenAI returned an empty tutor response.' }

[pscustomobject]@{
    provider = $done.provider
    model = $done.model
    response_id = $done.response_id
    input_tokens = $done.usage.input_tokens
    output_tokens = $done.usage.output_tokens
    total_tokens = $done.usage.total_tokens
    marker_returned = ($tokens -join '') -match $nonce
} | ConvertTo-Json
