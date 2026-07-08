# Установка Claude Science на чистую Windows-машину (через WSL)

Инструкция для агента (Claude Code или аналогичного), выполняющего установку.
Claude Science — локальный демон с веб-интерфейсом в браузере
(«run Claude on your data, locally, in your browser»). Дистрибутив — один
нативный Linux-бинарник (ELF x86-64, ~158 МБ), поэтому на Windows он
запускается внутри WSL2. Внутри WSL он использует песочницу (bubblewrap),
веб-интерфейс открывается в обычном браузере Windows.

Проверено на: Windows 11 Home 26200, Ubuntu-24.04 в WSL2,
claude-science 0.1.16-dev.

---

## Шаг 0. Что нужно иметь заранее

- **Бинарник** `linux-x64` — нативная Linux-сборка claude-science.
  Официальная страница продукта: <https://claude.com/product/claude-science>,
  прямая ссылка на актуальную сборку:

  ```text
  https://downloads.claude.ai/claude-science/latest/linux-x64
  ```

  Скачать можно прямо изнутри WSL (после шага 1):

  ```powershell
  wsl -d Ubuntu-24.04 -- bash -c "curl -fL -o /tmp/linux-x64 https://downloads.claude.ai/claude-science/latest/linux-x64"
  ```

  После установки бинарник умеет самообновляться (`claude-science update`).
- Права администратора могут понадобиться только для установки WSL.

Проверка, что файл правильный (первые байты — ELF-магия `7f 45 4c 46`):

```bash
head -c 4 linux-x64 | od -A n -t x1    # ожидается: 7f 45 4c 46
```

## Шаг 1. WSL

Проверь состояние:

```powershell
wsl --status
wsl -l -v
```

Возможные исходы:

- **WSL нет вообще** (`wsl` не распознан или предлагает установку):

  ```powershell
  wsl --install -d Ubuntu-24.04
  ```

  Требует прав администратора и **перезагрузки Windows**. После перезагрузки
  при первом запуске Ubuntu интерактивно спросит имя пользователя и пароль —
  это должен сделать человек (агент не может пройти интерактивный ввод;
  предложи пользователю выполнить `wsl -d Ubuntu-24.04` самому в терминале).

- **WSL есть, но версия 1**: выполни `wsl --set-version <дистрибутив> 2`.
  Нужна именно WSL2.

- **WSL2 с любым свежим Ubuntu/Debian есть** — используй его, ничего
  ставить не надо. Далее в командах замени `Ubuntu-24.04` на имя дистрибутива
  из `wsl -l -v`.

## Шаг 2. Системные зависимости внутри WSL

Демон при старте требует `bubblewrap` (песочница) и `socat` (сетевой мост
песочницы). Без них он не стартует — падает с понятными ошибками в логах.
Ставь сразу оба, от root (пароль не нужен):

```powershell
wsl -d Ubuntu-24.04 -u root -- bash -c "apt-get update -qq && apt-get install -y -qq bubblewrap socat"
```

## Шаг 3. Установка бинарника

Положи бинарник в `~/.local/bin` (он в PATH login-шелла Ubuntu по умолчанию).
Источник — `/tmp/linux-x64`, если качал по ссылке из шага 0 изнутри WSL,
или `/mnt/c/<путь>/linux-x64`, если файл лежит на диске Windows:

```powershell
wsl -d Ubuntu-24.04 -- bash -c "mkdir -p ~/.local/bin && cp /tmp/linux-x64 ~/.local/bin/claude-science && chmod +x ~/.local/bin/claude-science"
wsl -d Ubuntu-24.04 -- bash -lc "claude-science --version"
```

Ожидаемый вывод: `claude-science <версия> (release, public)`.

> **Грабли:** `bash -c` (не-login) не включает `~/.local/bin` в PATH —
> для команд по имени используй `bash -lc`, либо полный путь
> `~/.local/bin/claude-science`.

## Шаг 4. Первый запуск и проверка

```powershell
wsl -d Ubuntu-24.04 -- bash -lc "claude-science serve --no-browser --detached"
wsl -d Ubuntu-24.04 -- bash -lc "claude-science status"
```

`status` должен вернуть JSON с `"running": true` и `"port": 8000`.
Если `running: false` — смотри логи:

```powershell
wsl -d Ubuntu-24.04 -- bash -lc "cat ~/.claude-science/logs/spawn.log; tail -50 ~/.claude-science/logs/server-*.log"
```

Проверка из Windows (WSL2 пробрасывает localhost автоматически):

```powershell
curl.exe -s -o NUL -w "%{http_code}" http://localhost:8000
```

**Ожидается `401` — это успех**: сервер отвечает, но требует одноразовую
ссылку для входа. `000` или connection refused — порт не пробросился или
демон не запущен.

Вход в интерфейс — только по одноразовой ссылке (живёт ~3 минуты):

```powershell
wsl -d Ubuntu-24.04 -- bash -lc "claude-science url"
```

Открой напечатанный `http://localhost:8000/?nonce=...` в браузере Windows.

Заодно проверь исходящую сеть из WSL (нужна для работы LLM):

```powershell
wsl -d Ubuntu-24.04 -- bash -c "curl -s -o /dev/null -w '%{http_code}' https://api.anthropic.com --max-time 10"
```

Ожидается `404` (API отвечает). `000` — см. «Известные проблемы → VPN».

## Шаг 5. Ярлык на рабочем столе (опционально, рекомендуется)

Три части: bash-скрипт в WSL, `.cmd`-обёртка, ярлык `.lnk`.

**5.1. Скрипт в WSL** — поднимает демон при необходимости и печатает ссылку.
Создай файл на стороне Windows и скопируй с конвертацией CRLF→LF:

```bash
#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"
if ! claude-science status 2>/dev/null | grep -q '"running": *true'; then
  claude-science serve --no-browser --detached >/dev/null 2>&1
  for i in $(seq 1 15); do
    claude-science status 2>/dev/null | grep -q '"running": *true' && break
    sleep 1
  done
fi
claude-science url 2>/dev/null | grep -o 'http://[^[:space:]]*' | head -1
```

```powershell
wsl -d Ubuntu-24.04 -- bash -c "tr -d '\r' < /mnt/c/<путь>/claude-science-start.sh > ~/.local/bin/claude-science-start.sh && chmod +x ~/.local/bin/claude-science-start.sh"
```

> **Грабли:** без `tr -d '\r'` скрипт, созданный в Windows, сломается
> (CRLF). Без строки `export PATH=...` не найдёт `claude-science`
> (скрипт зовётся через не-login shell).

**5.2. `.cmd`-обёртка** (например, `C:\Tools\claude-science.cmd`):

```bat
@echo off
rem Start Claude Science in WSL and open the web UI
set "URL="
for /f "usebackq delims=" %%u in (`wsl -d Ubuntu-24.04 -- bash -c "~/.local/bin/claude-science-start.sh"`) do set "URL=%%u"
if defined URL (
    start "" "%URL%"
) else (
    echo Failed to start Claude Science or obtain a login link.
    echo Check manually: wsl -d Ubuntu-24.04 -- bash -lc "claude-science status"
    pause
)
```

> **Грабли:** файл должен быть **строго ASCII** (комментарии и сообщения —
> только латиницей). cmd.exe читает файл в OEM-кодировке: UTF-8 с кириллицей
> ломает парсинг строк и батник сыплется на ровном месте.

**5.3. Ярлык:**

```powershell
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut("$([Environment]::GetFolderPath('Desktop'))\Claude Science.lnk")
$lnk.TargetPath = 'C:\Tools\claude-science.cmd'
$lnk.WindowStyle = 7   # свернутое окно
# $lnk.IconLocation = 'C:\Tools\icon.ico,0'   # если есть .ico
$lnk.Save()
```

Иконка (опционально): официальный логотип есть, например, здесь —
<https://i0.wp.com/9to5mac.com/wp-content/uploads/sites/6/2026/06/claude-science.webp>
(оранжевая плашка с ДНК на коричневом фоне). Нужно вырезать плашку,
скруглить углы прозрачностью и сохранить как многоразмерный `.ico`
(256/64/48/32/16 px) — удобно через Python + Pillow
(`Image.save('icon.ico', sizes=[...])`). Windows не принимает
`.png`/`.webp` в качестве иконки ярлыка — только `.ico`.

Проверь двойным кликом (или `cmd /c <путь>.cmd`): должна открыться вкладка
браузера с интерфейсом. При «холодном» старте WSL первые 5–15 секунд ничего
не происходит — это нормально.

## Известные проблемы

| Симптом | Причина | Решение |
|---|---|---|
| В интерфейсе «connection error», в логах `[LLM] connection error` с ретраями | **VPN (WireGuard и т.п.) блокирует NAT-трафик WSL2.** DNS при этом работает, а ping/HTTPS из WSL — нет | Создай `C:\Users\<user>\.wslconfig` с содержимым `[wsl2]`↵`networkingMode=mirrored`, затем `wsl --shutdown` и перезапусти демон |
| После перезапуска WSL демон на порту 8001 вместо 8000 (`fell_back_from: 8000` в status) | При старте порт 8000 был временно занят (старый релей WSL) | `claude-science stop`, затем `serve` снова — вернётся на 8000. Ссылки от `claude-science url` в любом случае указывают на актуальный порт |
| Ссылка `localhost:8000` не открывается спустя время | WSL глушит ВМ при простое — демон умирает вместе с ней | Запуск через ярлык/скрипт из шага 5 — он поднимает демон заново |
| `401` при открытии `localhost:8000` напрямую | Это штатно: вход только по одноразовой ссылке | `claude-science url` → открыть ссылку в течение 3 минут |
| Демон не стартует, в логах `bwrap not found` / `socat is required` | Не установлены зависимости | Шаг 2 |

## Чек-лист финальной проверки

1. `claude-science --version` печатает версию.
2. `claude-science status` → `"running": true`.
3. `curl http://localhost:8000` из **Windows** → HTTP 401.
4. `curl https://api.anthropic.com` из **WSL** → HTTP 404 (при включённом
   VPN пользователя, если он есть!).
5. Ссылка из `claude-science url` открывается в браузере Windows и показывает
   интерфейс.
6. Двойной клик по ярлыку открывает интерфейс (если делали шаг 5).

## Полезные команды

```text
claude-science status          # состояние (JSON, всегда exit 0)
claude-science url             # новая одноразовая ссылка для входа
claude-science logs --tail     # живые логи
claude-science stop            # остановить демон
claude-science update --check  # есть ли новая версия
```

Данные хранятся в `~/.claude-science` внутри WSL (перенос на другую машину —
`claude-science import`).
