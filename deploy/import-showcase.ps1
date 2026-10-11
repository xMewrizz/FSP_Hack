param(
    [string]$Server = "fsp-beget"
)

$ErrorActionPreference = "Stop"
$remote = 'set -eu; cd /opt/fsp-hack; docker compose -f compose.production.yml cp data/platform_showcase_v1 backend:/tmp/platform_showcase_v1; docker compose -f compose.production.yml exec -T backend python showcase_import.py /tmp/platform_showcase_v1'
& ssh -n $Server $remote
if ($LASTEXITCODE -ne 0) { throw "Импорт демонстрационных данных не завершился" }
