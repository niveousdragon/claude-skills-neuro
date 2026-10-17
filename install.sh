#!/usr/bin/env bash
# Установка скиллов в ~/.claude/skills (macOS / Linux)
# Запуск:  ./install.sh
# Копирует все папки из skills/ в личный каталог скиллов Claude Code и вписывает
# общий протокол из protocol/CLAUDE.md в ~/.claude/CLAUDE.md.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
src="$script_dir/skills"
dest="$HOME/.claude/skills"

if [ ! -d "$src" ]; then
    echo "Не найдена папка skills рядом со скриптом: $src" >&2
    exit 1
fi

mkdir -p "$dest"

count=0
for skill in "$src"/*/; do
    [ -d "$skill" ] || continue
    name="$(basename "$skill")"
    target="$dest/$name"
    if [ -d "$target" ]; then
        echo "Обновляю $name"
        rm -rf "$target"
    else
        echo "Ставлю   $name"
    fi
    cp -R "$skill" "$target"
    count=$((count + 1))
done

if [ "$count" -eq 0 ]; then
    echo "В skills/ нет ни одного скилла."
    exit 0
fi

# Общий протокол вписывается в ~/.claude/CLAUDE.md размеченным блоком: при обновлении
# заменяется только блок, а свои правила пользователя вне его остаются нетронутыми.
proto_src="$script_dir/protocol/CLAUDE.md"
claude_md="$HOME/.claude/CLAUDE.md"
begin='<!-- claude-skills-neuro:protocol:begin (managed by install script; put your own rules outside this block) -->'
end='<!-- claude-skills-neuro:protocol:end -->'
block="$(mktemp)"
{ echo "$begin"; cat "$proto_src"; echo "$end"; } > "$block"

if [ -f "$claude_md" ]; then
    backup="$claude_md.bak-$(date +%Y%m%d-%H%M%S)"
    cp "$claude_md" "$backup"
    if grep -qF "$begin" "$claude_md" && grep -qF "$end" "$claude_md"; then
        awk -v b="$begin" -v e="$end" -v f="$block" '
            $0 == b { while ((getline line < f) > 0) print line; skip = 1; next }
            $0 == e { skip = 0; next }
            !skip' "$claude_md" > "$claude_md.tmp"
        echo "Обновляю общий протокол в $claude_md"
    else
        { cat "$block"; echo ""; cat "$claude_md"; } > "$claude_md.tmp"
        echo "Добавляю общий протокол в начало $claude_md"
    fi
    mv "$claude_md.tmp" "$claude_md"
    echo "Прежняя версия сохранена: $backup"
else
    cp "$block" "$claude_md"
    echo "Создаю $claude_md с общим протоколом"
fi
rm -f "$block"

echo ""
echo "Готово. Установлено скиллов: $count"
echo "Каталог: $dest"
echo "Открой Claude Code и спроси: «Какие скиллы тебе доступны?»"
