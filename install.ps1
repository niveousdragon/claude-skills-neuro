# Установка скиллов в ~/.claude/skills (Windows / PowerShell)
# Запуск:  .\install.ps1
# Копирует все папки из skills/ в личный каталог скиллов Claude Code и вписывает
# общий протокол из protocol/CLAUDE.md в ~/.claude/CLAUDE.md.

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

# Общий протокол вписывается в ~/.claude/CLAUDE.md размеченным блоком: при обновлении
# заменяется только блок, а свои правила пользователя вне его остаются нетронутыми.
$protoSrc = Join-Path $PSScriptRoot "protocol\CLAUDE.md"
$claudeMd = Join-Path $env:USERPROFILE ".claude\CLAUDE.md"
$begin = "<!-- claude-skills-neuro:protocol:begin (managed by install script; put your own rules outside this block) -->"
$end   = "<!-- claude-skills-neuro:protocol:end -->"
$utf8  = New-Object System.Text.UTF8Encoding($false)

$proto = [IO.File]::ReadAllText($protoSrc, $utf8).TrimEnd()
$block = "$begin`n$proto`n$end"

if (Test-Path $claudeMd) {
    $old = [IO.File]::ReadAllText($claudeMd, $utf8)
    $backup = "$claudeMd.bak-{0}" -f (Get-Date -Format "yyyyMMdd-HHmmss")
    Copy-Item $claudeMd $backup
    $i = $old.IndexOf($begin)
    $j = $old.IndexOf($end)
    if ($i -ge 0 -and $j -gt $i) {
        $new = $old.Substring(0, $i) + $block + $old.Substring($j + $end.Length)
        Write-Host "Обновляю общий протокол в $claudeMd" -ForegroundColor Cyan
    } else {
        $new = "$block`n`n$old"
        Write-Host "Добавляю общий протокол в начало $claudeMd" -ForegroundColor Green
    }
    Write-Host ("Прежняя версия сохранена: {0}" -f $backup)
} else {
    $new = "$block`n"
    Write-Host "Создаю $claudeMd с общим протоколом" -ForegroundColor Green
}
[IO.File]::WriteAllText($claudeMd, $new, $utf8)

Write-Host ""
Write-Host ("Готово. Установлено скиллов: {0}" -f $skills.Count) -ForegroundColor Green
Write-Host ("Каталог: {0}" -f $dest)
Write-Host "Открой Claude Code и спроси: «Какие скиллы тебе доступны?»"
