# Инструкция для Claude: отключить Remote Control на этом компьютере

**Цель:** жёстко запретить Claude Code Remote Control, чтобы локальные CLI-сессии
никогда не синхронизировались и не появлялись в веб-приложении `claude.ai/code`.

Причина: Anthropic раскатывает серверный флаг `remote-control-auto-on`, который
может сам включать Remote Control, если в конфигах нет явного запрета. Ниже —
жёсткий opt-out во всех местах.

> Отдай этот файл Claude Code в новой сессии на новом компьютере и скажи:
> «Выполни инструкцию из этого файла». Claude сам найдёт все конфиги и пропишет запрет.

---

## Что нужно проставить

| Файл | Ключ | Значение |
|------|------|----------|
| `~/.claude/settings.json` (глобальный) | `disableRemoteControl` | `true` |
| `~/.claude/settings.local.json` | `disableRemoteControl` | `true` |
| `~/.claude.json` (главный конфиг) | `remoteEnabled` (top-level) | `false` |
| каждый `<проект>/.claude/settings.local.json` | `disableRemoteControl` | `true` |

`~` на Windows = `C:\Users\<имя_пользователя>` (например `C:\Users\witka`).
`disableRemoteControl: true` — это жёсткая политика, перекрывающая авто-включатель.

---

## Шаги для Claude

### 1. Глобальные настройки (`~/.claude/`)
- Открыть `~/.claude/settings.json`. Добавить ключ `"disableRemoteControl": true`
  на верхнем уровне (рядом с другими ключами). Не сломать JSON, не удалять
  существующие поля.
- То же самое в `~/.claude/settings.local.json`. Если файла нет — создать
  минимальный: `{ "disableRemoteControl": true }`.

### 2. Главный конфиг (`~/.claude.json`)
Этот файл большой (в нём хранятся проекты, кэш фиче-флагов и т.д.). Менять
**безопасно и с сохранением всего содержимого** через Python:

```bash
python -c "
import json
p=r'C:\Users\<ИМЯ>\.claude.json'
d=json.load(open(p,encoding='utf-8'))
d['remoteEnabled']=False
json.dump(d,open(p,'w',encoding='utf-8'),ensure_ascii=False,indent=2)
print('remoteEnabled =', json.load(open(p,encoding='utf-8')).get('remoteEnabled'))
print('projects intact:', len(d.get('projects',{})))
"
```

Заменить `<ИМЯ>` на имя пользователя. Не редактировать этот файл текстовым
Edit'ом целиком — только точечно через скрипт, чтобы не повредить структуру.

> Проверка (необязательно): найти реальное состояние ключа рекурсивно —
> `remoteEnabled` в `cachedGrowthBookFeatures/...` это КЭШ серверного флага,
> а не пользовательская настройка; менять надо именно top-level `remoteEnabled`.

### 3. Все проектные конфиги
Найти все `settings.local.json` в папках проектов и в каждый добавить
`"disableRemoteControl": true` на верхнем уровне (сохранив блок `permissions`
и прочее). Пути к проектам на этом компьютере могут отличаться — искать реально
существующие файлы, а не копировать чужие пути. Например, если проекты лежат в
`C:\Users\<ИМЯ>\PycharmProjects`:

```bash
find "C:/Users/<ИМЯ>/PycharmProjects" -maxdepth 3 -name "settings*.json"
```

Для каждого найденного файла: прочитать → добавить ключ → сохранить.

### 4. Проверка (обязательно)
Убедиться, что все затронутые файлы остаются валидным JSON и ключ проставлен:

```bash
python -c "import json; d=json.load(open(r'C:\Users\<ИМЯ>\.claude\settings.json',encoding='utf-8')); print('disableRemoteControl =', d.get('disableRemoteControl'))"
```

Повторить для каждого изменённого файла.

---

## После настройки (делает пользователь вручную)

Настройки читаются **при старте** сессии. Уже запущенные сессии Claude нужно
перезапустить, чтобы запрет вступил в силу:

1. В сессии набрать `/exit` (или `Ctrl+C` дважды).
2. Снова запустить `claude` в той же папке.
   Продолжить прошлую беседу можно через `claude --continue` или `claude --resume`.

Убивать процесс через `taskkill` не нужно. История сессий (`~/.claude/projects/*/*.jsonl`)
не теряется.

---

## Важные оговорки
- Посессионных конфигов для Remote Control нет — под `~/.claude/projects/*`
  лежат только транскрипты (`.jsonl`). Менять там нечего.
- Настройки НЕ переносятся между компьютерами автоматически — на каждой машине
  этот запрет нужно проставить отдельно (для этого и нужна инструкция).
- В организациях с Zero Data Retention Remote Control и так недоступен.
