# run-tests.ps1 - run ALL Teleos tests
# Usage: .\run-tests.ps1

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$failed = 0

function Print-Header($title) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  $title" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
}

# 1. Python pytest
Print-Header "Python - pytest (39 tests)"
Set-Location $root
python -m pytest tests/ -v --tb=short
if ($LASTEXITCODE -ne 0) { $failed++ }

# 2. Python CLI - teleos test on example files
Print-Header "Python CLI - teleos test"
Set-Location $root
$examples = @("examples\access.teleos", "examples\grades.teleos", "examples\import-demo.teleos")
foreach ($ex in $examples) {
    Write-Host ""
    Write-Host ">> teleos test $ex" -ForegroundColor Yellow
    python -m teleos test $ex
    if ($LASTEXITCODE -ne 0) { $failed++ }
}

# 3. Rust - cargo test
Print-Header "Rust - cargo test (25 tests)"
Set-Location "$root\teleos-core"
cargo test
if ($LASTEXITCODE -ne 0) { $failed++ }
Set-Location $root

# 4. Rust binary - teleos-core test on example files
Print-Header "Rust binary - teleos-core test"
$binary = "$root\teleos-core\target\release\teleos-core.exe"
if (Test-Path $binary) {
    Set-Location $root
    foreach ($ex in $examples) {
        Write-Host ""
        Write-Host ">> teleos-core.exe test $ex" -ForegroundColor Yellow
        & $binary test $ex
        if ($LASTEXITCODE -ne 0) { $failed++ }
    }
} else {
    Write-Host "  SKIP - release binary not found (run: cargo build --release)" -ForegroundColor DarkYellow
}

# Summary
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
if ($failed -eq 0) {
    Write-Host "  ALL TESTS PASSED" -ForegroundColor Green
} else {
    Write-Host "  $failed SUITE(S) FAILED" -ForegroundColor Red
}
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
exit $failed
