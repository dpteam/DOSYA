# Сборка и запуск

## Что нужно

* **Python 3.9+** и **Pillow** (`pip install pillow`).
* Больше ничего. DJGPP, CWSDPMI и шрифт скачиваются скриптом.

```powershell
python -m pip install pillow
python tools\setup.py
```

`setup.py` кладёт всё в `vendor/` (он в `.gitignore`) и выбирает нужную
сборку DJGPP по платформе:

| платформа | архив |
|---|---|
| Windows | `djgpp-mingw-gcc1220-standalone.zip` |
| Linux | `djgpp-linux64-gcc1220.tar.bz2` |
| macOS | `djgpp-osx-gcc1220.tar.bz2` |

### Только шрифт

DJGPP нужен только для DOS-сборки. Если вы собираете host-версию (тесты,
кадры, иконка) — качать 120 МБ незачем:

```powershell
python tools\setup.py --font     # только GNU Unifont, ~1 МБ
python tools\build.py host
```

Более того, шрифт скачается сам при первом запуске `genfont.py`, если его
нет: `tools/fetch.py` следит за этим. Так что `build.py host` из чистого
клона работает без `setup.py` вообще. Проверяется на целостность — битая
или недокачанная загрузка перекачивается, а не роняет сборку.

## Сборка

```powershell
python tools\build.py dos     # -> dist\DOSYA.EXE + CWSDPMI.EXE
python tools\build.py host    # -> build\dosya_host.exe (для тестов)
python tools\build.py all     # обе
```

Каждая сборка заново генерирует ассеты в `build/gen/`. Это медленнее на
полсекунды, но исключает классику «я поправил спрайт, а он не изменился».

### Что получается

```
dist\
  DOSYA.EXE     сама игра, 256 КБ
  CWSDPMI.EXE   DPMI-хост, 21 КБ
```

`CWSDPMI.EXE` **обязателен**. Без него игра падает с

```
Load error: no DPMI - Get csdpmi*b.zip
```

потому что DJGPP-бинарник — это 32-битный protected mode, а DOS сам по себе
его не умеет.

## Запуск

### DOSBox

```ini
[autoexec]
mount c dist
c:
DOSYA.EXE
```

Готовый конфиг — `dosbox.conf` в корне.

### Настоящая DOS-машина

Скопируйте оба файла на диск и запустите `DOSYA.EXE`. Нужно хотя бы 386 с
4 МБ памяти; на 486DX2/66 идёт с запасом.

### Откуда 256 КБ

DJGPP-бинарник толстый из-за статически прилинкованной libc. Это нормально
для 1994 года, когда 500 КБ на диске никого не смущали.

## Self-test

Игра умеет проверять себя без клавиатуры:

```
DOSYA.EXE -test 400
```

Рендерит 400 кадров с включённым автопилотом и складывает их в `SHOT000.PPM`,
`SHOT001.PPM`… Потом выходит. Так проверяется, что настоящая DOS-сборка не
падает на третьем кадре.

```powershell
# в DOSBox, из папки с игрой
DOSYA.EXE -test 400
```

PPM открывается любым конвертером (`python tools\frames.py` соберёт
контактный лист).

Именно этот тест нашёл три падения подряд, включая то, где в DOS-сборке
никто не выделил offscreen-буфер и первый же `memset` писал в NULL.

## Тесты

```powershell
python tools\build.py host
python tools\smoke.py
```

`smoke.py` запускает автопилот и проверяет, что:

* пройдены все три уровня;
* достигнут финальный экран;
* автопилот ни разу не умер насмерть (то есть уровень не стал непроходимым).

Выход 0 — всё хорошо. Это же гоняет CI.

## Отладка

### Кадры без DOSBox

Host-сборка умеет писать кадры в PPM:

```powershell
$env:DOSYA_AUTOPILOT="1"
$env:DOSYA_DUMP_EVERY="60"      # каждый 60-й кадр
$env:DOSYA_MAX_FRAMES="3000"
.\build\dosya_host.exe

python tools\frames.py "f*.ppm" tools\prev_frames.png 4 1 16
```

### Трассировка

```powershell
$env:DOSYA_DBG="1"    # переходы между состояниями
$env:DOSYA_DBG="2"    # плюс построчный лог автопилота
```

Печатает в stderr:

```
[tick] state 2 -> 4 lvl=0 x=1825 y=170 lives=3 hearts=3 cause=0
```

Состояния: `0` TITLE, `1` INTRO, `2` PLAY, `3` DEAD, `4` LEVEL_DONE,
`5` WIN, `6` GAMEOVER.

### Ввод по сценарию

```powershell
$env:DOSYA_SCRIPT="build\my_input.txt"
```

Формат файла — `<кадр> <сканкод hex>`, по строке на событие. Старший бит
(`0x80`) означает отпускание клавиши:

```
5 39       # нажать пробел на кадре 5
7 b9       # отпустить на кадре 7
```

Сканкоды: влево `4B`, вправо `4D`, пробел `39`, Esc `01`, Z `2C`, P `19`.

### Экраны

```powershell
python tools\screens.py     # титул, заставка, игра, пауза — одним листом
```

## Если что-то сломалось

**`no DPMI`** — нет `CWSDPMI.EXE` рядом с `DOSYA.EXE`.

**Чёрный экран в DOSBox** — проверьте `output=surface` в конфиге.
С `output=opengl` на некоторых драйверах окно остаётся чёрным.

**Кракозябры вместо русского** — шрифт не CP866. Проверьте, что
`tools/genfont.py` отработал и в `build/gen/font.c` есть данные.

**`cc1.exe: error: no iconv implementation`** — вы пытаетесь
`-finput-charset` на DJGPP. Он не умеет. Текст должен быть уже в CP866
(этим занимается `tools/genstrings.py`).
