param(
 [Parameter(Mandatory=$true)][string]$Distribution,
 [string]$JavaExe='java'
)
$ErrorActionPreference='Stop'
$runtime=Join-Path $PSScriptRoot 'runtime'
foreach($dir in @('conf','data','logs','run','plugins')) { New-Item -ItemType Directory -Force -Path (Join-Path $runtime $dir) | Out-Null }
if(-not (Test-Path -LiteralPath (Join-Path $runtime 'conf/neo4j.conf'))) { Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'neo4j-local.conf') -Destination (Join-Path $runtime 'conf/neo4j.conf') }
& $JavaExe '-Xms256m' '-Xmx768m' '-Dio.netty.noUnsafe=true' '-cp' (Join-Path $Distribution 'lib/*') 'org.neo4j.server.CommunityEntryPoint' '--home-dir' $runtime '--config-dir' (Join-Path $runtime 'conf')
