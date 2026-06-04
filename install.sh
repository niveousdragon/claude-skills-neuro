#!/usr/bin/env bash
# Установка скиллов в ~/.claude/skills (macOS / Linux)
# Запуск:  ./install.sh
# Копирует все папки из skills/ в личный каталог скиллов Claude Code.

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

echo ""
echo "Готово. Установлено скиллов: $count"
echo "Каталог: $dest"
echo "Открой Claude Code и спроси: «Какие скиллы тебе доступны?»"
