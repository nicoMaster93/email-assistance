param(
  [Parameter(Mandatory = $true)]
  [string]$InputVideo,

  [string]$OutputVideo = "",

  [string]$EndTime = "00:08:09"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  Write-Error "No se encontro ffmpeg. Instala ffmpeg y vuelve a ejecutar este script."
}

$inputPath = Resolve-Path -LiteralPath $InputVideo

if (-not $OutputVideo) {
  $directory = Split-Path -Parent $inputPath
  $name = [System.IO.Path]::GetFileNameWithoutExtension($inputPath)
  $extension = [System.IO.Path]::GetExtension($inputPath)
  $OutputVideo = Join-Path $directory "$name-recortado$extension"
}

ffmpeg `
  -y `
  -i $inputPath `
  -to $EndTime `
  -c copy `
  $OutputVideo

Write-Host "Video recortado correctamente:"
Write-Host $OutputVideo
