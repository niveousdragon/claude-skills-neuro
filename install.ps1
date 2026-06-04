# Установка скиллов в ~/.claude/skills (Windows / PowerShell)
# Запуск:  .\install.ps1
# Копирует все папки из skills/ в личный каталог скиллов Claude Code.

$ErrorActionPreference = "Stop"

$src  = Join-Path $PSScriptRoot "skills"
$dest = Join-Path $env:USERPROFILE ".claude\skills"

if (-not (Test-Path $src)) {
    Write-Host "Не найдена папка skills рядом со скриптом: $src" -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path $dest | Out-Null

$skills = Get-ChildItem -Path $src -Directory
if ($skills.Count -eq 0) {
    Write-Host "В skills/ нет ни одного скилла." -ForegroundColor Yellow
    exit 0
}

foreach ($skill in $skills) {
    $target = Join-Path $dest $skill.Name
    if (Test-Path $target) {
        Write-Host ("Обновляю {0}" -f $skill.Name) -ForegroundColor Cyan
        Remove-Item -Recurse -Force $target
    } else {
        Write-Host ("Ставлю   {0}" -f $skill.Name) -ForegroundColor Green
    }
    Copy-Item -Recurse -Force $skill.FullName $target
}

Write-Host ""
Write-Host ("Готово. Установлено скиллов: {0}" -f $skills.Count) -ForegroundColor Green
Write-Host ("Каталог: {0}" -f $dest)
Write-Host "Открой Claude Code и спроси: «Какие скиллы тебе доступны?»"
