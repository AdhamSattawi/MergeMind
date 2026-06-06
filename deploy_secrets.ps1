# deploy_secrets.ps1
# Creates all secrets in GCP Secret Manager from the local .env file
# Run once before deploying to Cloud Run

$gcloud = "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
$project = "mergemind-497820"

# Read .env file and create each secret
Get-Content .env | Where-Object { $_ -notmatch '^\s*#' -and $_ -match '=' } | ForEach-Object {
    $parts = $_ -split '=', 2
    $name  = $parts[0].Trim()
    $value = $parts[1].Trim().Trim("`r").Trim()

    if (-not $name -or -not $value) { return }

    Write-Host "Creating secret: $name ..." -ForegroundColor Cyan

    # Create the secret (ignore error if it already exists)
    & $gcloud secrets create $name --project=$project --replication-policy="automatic" 2>$null

    # Write to a temp file to avoid PowerShell piping adding CRLF
    $tempFile = [System.IO.Path]::GetTempFileName()
    [System.IO.File]::WriteAllText($tempFile, $value)
    
    & $gcloud secrets versions add $name --project=$project --data-file=$tempFile 2>&1
    
    Remove-Item $tempFile

    Write-Host "  ✅ $name" -ForegroundColor Green
}

Write-Host "`n✅ All secrets created in Secret Manager." -ForegroundColor Green
