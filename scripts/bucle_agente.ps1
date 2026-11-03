# Bucle de implementacion con pruebas protegidas.
# Uso (desde la carpeta del proyecto):
#   powershell -ExecutionPolicy Bypass -File scripts\bucle_agente.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\bucle_agente.ps1 -Rondas 30

param([int]$Rondas = 20)

Set-Location (Split-Path $PSScriptRoot -Parent)
$protegidos = @("tests/test_criticos.py", "docs/CONTRATO_VISOR.md")
$base = "pruebas-aprobadas"
New-Item -ItemType Directory -Force logs | Out-Null

git rev-parse -q --verify "refs/tags/$base" | Out-Null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Falta la etiqueta '$base'. Crea primero el commit de las pruebas protegidas." -ForegroundColor Red
  exit 1
}

$instruccion = "Lee AGENTS.md, docs/CONTRATO_VISOR.md y docs/VERIFICACION.md. " +
  "Toma el primer REQ CRITICO en FALLA; si no hay ninguno, el primer REQ de MEJORA en FALLA. " +
  "Implementalo en el codigo del visor hasta que su prueba pase. " +
  "PROHIBIDO modificar tests/test_criticos.py y docs/CONTRATO_VISOR.md. " +
  "PROHIBIDO usar escalas negativas o espejados. " +
  "Ejecuta scripts/verificar.py, actualiza docs/BITACORA.md, haz commit y push. Despues termina."

for ($i = 1; $i -le $Rondas; $i++) {
  uv run python scripts/verificar.py
  if ($LASTEXITCODE -eq 0) {
    Write-Host "TODOS LOS REQUISITOS PASAN" -ForegroundColor Green
    break
  }

  Write-Host "Ronda $i de $Rondas" -ForegroundColor Yellow
  opencode run $instruccion

  # Si el agente altero los archivos protegidos (con o sin commit), se restauran.
  $alterados = @(git diff --name-only $base HEAD -- $protegidos) + @(git diff --name-only -- $protegidos)
  $alterados = $alterados | Where-Object { $_ } | Sort-Object -Unique
  if ($alterados) {
    "$(Get-Date -Format s) Ronda ${i}: el agente altero $($alterados -join ', '). Se restauraron." |
      Add-Content logs/bucle_alertas.log
    git checkout $base -- $protegidos
    git commit -m "chore: restaurar pruebas protegidas" | Out-Null
    git push | Out-Null
    Write-Host "Archivos protegidos restaurados (ver logs/bucle_alertas.log)" -ForegroundColor Red
  }
}