param(
    [string]$EnvPath = (Join-Path $PSScriptRoot "..\.env")
)

if (-not (Test-Path $EnvPath)) {
    throw "Env file not found: $EnvPath"
}

$vars = @{}
Get-Content $EnvPath | ForEach-Object {
    if ($_ -match '^\s*#') { return }
    if ($_ -match '^(SUPABASE_URL|SUPABASE_ANON_KEY)=(.+)$') {
        $vars[$matches[1]] = $matches[2].Trim()
    }
}

if (-not $vars.ContainsKey("SUPABASE_URL") -or [string]::IsNullOrWhiteSpace($vars["SUPABASE_URL"])) {
    throw "SUPABASE_URL is missing from $EnvPath"
}

$url = "$($vars['SUPABASE_URL'].TrimEnd('/'))/auth/v1/.well-known/jwks.json"

try {
    $response = Invoke-WebRequest -Uri $url -Method Get -UseBasicParsing
    Write-Output ("Supabase keepalive OK | status=" + [int]$response.StatusCode + " | url=" + $vars["SUPABASE_URL"])
}
catch {
    $message = $_.Exception.Message
    throw "Supabase keepalive failed for $($vars['SUPABASE_URL']): $message"
}
