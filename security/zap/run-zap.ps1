$ErrorActionPreference = 'Stop'

$frontendUrl = 'http://localhost:5173'
$apiUrl = 'http://localhost:8000'
$zapApiUrl = 'http://127.0.0.1:8090'
$reportDirectory = Join-Path $PSScriptRoot 'reports'
$zapDataDirectory = Join-Path $PSScriptRoot '.zap-data'
$apiKey = [guid]::NewGuid().ToString('N')
$zapProcess = $null

function Find-ZapExecutable {
  $projectZap = Join-Path $PSScriptRoot 'tools\ZAP_2.17.0\ZAP_2.17.0\zap.bat'
  if (Test-Path -LiteralPath $projectZap -PathType Leaf) {
    return (Resolve-Path -LiteralPath $projectZap).Path
  }

  if ($env:ZAP_PATH -and (Test-Path -LiteralPath $env:ZAP_PATH -PathType Leaf)) {
    return (Resolve-Path -LiteralPath $env:ZAP_PATH).Path
  }

  $command = Get-Command zap.bat -ErrorAction SilentlyContinue
  if ($command) {
    return $command.Source
  }

  $candidates = @(
    (Join-Path $env:ProgramFiles 'ZAP\Zed Attack Proxy\zap.bat'),
    (Join-Path ${env:ProgramFiles(x86)} 'ZAP\Zed Attack Proxy\zap.bat'),
    (Join-Path $env:LOCALAPPDATA 'Programs\ZAP\Zed Attack Proxy\zap.bat')
  ) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) }

  if ($candidates.Count -gt 0) {
    return $candidates[0]
  }

  throw 'No se encontró zap.bat. Instala OWASP ZAP o define ZAP_PATH con la ruta completa a zap.bat.'
}

function Use-ProjectJava {
  $projectJavaRoot = Join-Path $PSScriptRoot 'tools\temurin-jre-21'
  $java = Get-ChildItem -LiteralPath $projectJavaRoot -Filter java.exe -File -Recurse -ErrorAction SilentlyContinue |
    Select-Object -First 1

  if (-not $java) {
    throw 'No se encontró Java local. Ejecuta el setup de ZAP para preparar el JRE del proyecto.'
  }

  $env:JAVA_HOME = Split-Path (Split-Path $java.FullName -Parent) -Parent
  $env:PATH = "$(Split-Path $java.FullName -Parent);$env:PATH"
  return $java.FullName
}

function Invoke-ZapApi {
  param(
    [Parameter(Mandatory)]
    [string]$Path,
    [hashtable]$Parameters = @{}
  )

  $queryParameters = @{ apikey = $apiKey }
  foreach ($key in $Parameters.Keys) {
    $queryParameters[$key] = $Parameters[$key]
  }

  $query = ($queryParameters.GetEnumerator() | ForEach-Object {
    '{0}={1}' -f [uri]::EscapeDataString([string]$_.Key), [uri]::EscapeDataString([string]$_.Value)
  }) -join '&'

  Invoke-RestMethod -Uri "$zapApiUrl$Path`?$query" -TimeoutSec 30
}

function Wait-ForSpider {
  param([Parameter(Mandatory)][string]$ScanId)

  do {
    Start-Sleep -Seconds 2
    $status = Invoke-ZapApi -Path '/JSON/spider/view/status/' -Parameters @{ scanId = $ScanId }
    $progress = [int]$status.status
    Write-Progress -Activity 'OWASP ZAP: rastreando rutas' -Status "$progress% completado" -PercentComplete $progress
  } while ($progress -lt 100)

  Write-Progress -Activity 'OWASP ZAP: rastreando rutas' -Completed
}

foreach ($check in @(
  @{ Url = $frontendUrl; Name = 'Frontend'; Hint = 'Inícialo desde frontend con: pnpm dev' },
  @{ Url = "$apiUrl/openapi.json"; Name = 'API'; Hint = 'Inicia FastAPI en localhost:8000.' }
)) {
  try {
    Invoke-WebRequest -Uri $check.Url -TimeoutSec 5 -UseBasicParsing | Out-Null
  } catch {
    throw "$($check.Name) no está disponible en $($check.Url). $($check.Hint)"
  }
}

$zapExecutable = Find-ZapExecutable
$javaExecutable = Use-ProjectJava
$versionUrl = "$zapApiUrl/JSON/core/view/version/"
try {
  Invoke-RestMethod -Uri $versionUrl -TimeoutSec 2 | Out-Null
  throw 'El puerto local 8090 ya está ocupado. Cierra la instancia de ZAP que lo usa e inténtalo otra vez.'
} catch {
  if ($_.Exception.Message -match 'puerto local 8090 ya está ocupado') {
    throw
  }
}

New-Item -ItemType Directory -Path $reportDirectory, $zapDataDirectory -Force | Out-Null
$zapJar = Join-Path (Split-Path $zapExecutable -Parent) 'zap-2.17.0.jar'
if (-not (Test-Path -LiteralPath $zapJar -PathType Leaf)) {
  throw "No se encontró el archivo principal de ZAP: $zapJar"
}

$zapStdout = Join-Path $zapDataDirectory 'zap-startup.log'
$zapStderr = Join-Path $zapDataDirectory 'zap-errors.log'
$arguments = '-Xmx1g -jar "{0}" -daemon -host 127.0.0.1 -port 8090 -dir "{1}" -config "api.key={2}"' -f $zapJar, $zapDataDirectory, $apiKey
$zapProcess = Start-Process -FilePath $javaExecutable -ArgumentList $arguments -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput $zapStdout -RedirectStandardError $zapStderr

try {
  $ready = $false
  for ($attempt = 0; $attempt -lt 60; $attempt++) {
    if ($zapProcess.HasExited) {
      $startupError = if (Test-Path -LiteralPath $zapStderr) { Get-Content -LiteralPath $zapStderr -Raw } else { '' }
      throw "ZAP terminó durante el inicio (código $($zapProcess.ExitCode)). $startupError"
    }

    try {
      Invoke-ZapApi -Path '/JSON/core/view/version/' | Out-Null
      $ready = $true
      break
    } catch {
      Start-Sleep -Seconds 2
    }
  }

  if (-not $ready) {
    throw 'ZAP no respondió en el puerto 8090 después de 120 segundos.'
  }

  Write-Host 'Importando las rutas de la API desde OpenAPI...'
  Invoke-ZapApi -Path '/JSON/openapi/action/importUrl/' -Parameters @{
    url = "$apiUrl/openapi.json"
    hostOverride = $apiUrl
  } | Out-Null

  foreach ($target in @($frontendUrl, $apiUrl)) {
    Write-Host "Rastreando $target (sin escaneo activo)..."
    $scan = Invoke-ZapApi -Path '/JSON/spider/action/scan/' -Parameters @{
      url = $target
      recurse = 'true'
    }
    Wait-ForSpider -ScanId ([string]$scan.scan)
  }

  do {
    $pendingRecords = Invoke-ZapApi -Path '/JSON/pscan/view/recordsToScan/'
    $recordsRemaining = [int]$pendingRecords.recordsToScan
    if ($recordsRemaining -gt 0) {
      Write-Host "Esperando análisis pasivo de ZAP: $recordsRemaining registros pendientes..."
      Start-Sleep -Seconds 2
    }
  } while ($recordsRemaining -gt 0)

  Write-Host 'Generando informe HTML...'
  $report = Invoke-WebRequest -Uri "$zapApiUrl/OTHER/core/other/htmlreport/?apikey=$apiKey" -TimeoutSec 60 -UseBasicParsing
  $reportPath = Join-Path $reportDirectory 'vortexai-dast.html'
  Set-Content -LiteralPath $reportPath -Value $report.Content -Encoding utf8

  Write-Host "Informe generado: $reportPath"
  Write-Host 'Este análisis es pasivo y no intenta explotar vulnerabilidades.'
} finally {
  if ($zapProcess -and -not $zapProcess.HasExited) {
    try {
      Invoke-ZapApi -Path '/JSON/core/action/shutdown/' | Out-Null
    } catch {
      Stop-Process -Id $zapProcess.Id -ErrorAction SilentlyContinue
    }
  }
}
