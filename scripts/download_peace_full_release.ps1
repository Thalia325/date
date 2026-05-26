param(
    [string]$Url = "https://pennstateoffice365-my.sharepoint.com/:u:/g/personal/njz5124_psu_edu/ESmEFZMuTK5EnQ2sHLWvDs8BWosWkCHUEvgeQCcdIJq8LA?download=1",
    [string]$Output = "data/raw/PEaCE.tar.gz",
    [switch]$Extract,
    [string]$ExtractTo = "data/raw"
)

$ErrorActionPreference = "Stop"

function Copy-Stream {
    param(
        [System.IO.Stream]$InputStream,
        [System.IO.Stream]$OutputStream
    )
    $buffer = New-Object byte[] (8MB)
    while (($read = $InputStream.Read($buffer, 0, $buffer.Length)) -gt 0) {
        $OutputStream.Write($buffer, 0, $read)
    }
}

$outputPath = Resolve-Path -LiteralPath (Split-Path -Parent $Output) -ErrorAction SilentlyContinue
if (-not $outputPath) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Output) | Out-Null
}

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$head = Invoke-WebRequest -Uri $Url -Method Head -MaximumRedirection 10 -WebSession $session -UseBasicParsing
$downloadUri = $head.BaseResponse.ResponseUri.AbsoluteUri
$expectedLength = [int64]$head.Headers["Content-Length"]
$currentLength = if (Test-Path -LiteralPath $Output) { (Get-Item -LiteralPath $Output).Length } else { 0 }

if ($currentLength -gt $expectedLength) {
    throw "Existing file is larger than expected: $currentLength > $expectedLength"
}

if ($currentLength -lt $expectedLength) {
    $request = [System.Net.HttpWebRequest]::Create($downloadUri)
    $request.Method = "GET"
    $request.CookieContainer = New-Object System.Net.CookieContainer
    foreach ($cookie in $session.Cookies.GetCookies([Uri]$downloadUri)) {
        $request.CookieContainer.Add($cookie)
    }
    if ($currentLength -gt 0) {
        $request.AddRange($currentLength)
    }

    $response = $request.GetResponse()
    try {
        $mode = if ($currentLength -gt 0) { [System.IO.FileMode]::Append } else { [System.IO.FileMode]::Create }
        $fileStream = [System.IO.File]::Open($Output, $mode, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        try {
            Copy-Stream -InputStream $response.GetResponseStream() -OutputStream $fileStream
        }
        finally {
            $fileStream.Dispose()
        }
    }
    finally {
        $response.Dispose()
    }
}

$finalLength = (Get-Item -LiteralPath $Output).Length
if ($finalLength -ne $expectedLength) {
    throw "Download incomplete: $finalLength / $expectedLength bytes"
}

Write-Host "Downloaded PEaCE full release: $Output ($finalLength bytes)"

if ($Extract) {
    New-Item -ItemType Directory -Force -Path $ExtractTo | Out-Null
    tar -xzf $Output -C $ExtractTo
    Write-Host "Extracted to $ExtractTo"
}
