param(
    [string]$Server = "fsp-beget"
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$revision = (& git -C $repo rev-parse --short HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw "Не удалось определить ревизию Git" }

$archive = Join-Path $env:TEMP "fsp-hack-$revision.tar"
try {
    & git -C $repo archive --format=tar --output=$archive HEAD
    if ($LASTEXITCODE -ne 0) { throw "Не удалось собрать архив ревизии $revision" }

    & scp -O $archive "${Server}:/tmp/fsp-hack-update.tar"
    if ($LASTEXITCODE -ne 0) { throw "Не удалось передать архив на сервер" }

    $remote = 'set -eu; cd /opt/fsp-hack; tar -xf /tmp/fsp-hack-update.tar; rm /tmp/fsp-hack-update.tar; docker compose -f compose.production.yml config -q; docker compose -f compose.production.yml up -d --build --remove-orphans; docker compose -f compose.production.yml ps'
    & ssh -n $Server $remote
    if ($LASTEXITCODE -ne 0) { throw "Обновление контейнеров не завершилось" }
    Write-Host "Развёрнута ревизия $revision"
}
finally {
    Remove-Item -LiteralPath $archive -ErrorAction SilentlyContinue
}
