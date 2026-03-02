# Atlas Visual PoC (Крок 1)

**Proof of Concept:** Atlas надсилає жест з камери → візуальна програма змінює колір квадрата.

## Архітектура

- **Сенсор:** камера + MediaPipe (уже в `VisionManager`).
- **Ядро:** Atlas (`core/atlas.py`, `core/vision_manager.py`).
- **Міст:** `core/visual_bridge.py` — OSC (UDP) + WebSocket.
- **Клієнт:** ця папка (браузер) або TouchDesigner/Unity за адресами OSC.

## Як запустити

1. **Залежності (один раз):**
   ```bash
   pip install python-osc websockets
   ```

2. **Запустити Atlas** (з увімкненим зором), наприклад:
   ```bash
   python main_with_atlas.py
   ```
   Скажи: «Активуй зір» або виконай команду для `vision:start`.

3. **Відкрити PoC-клієнт:**
   - Варіант A: подвійний клік по `index.html` (браузер підключиться до `ws://127.0.0.1:8766`).
   - Варіант B: з кореня проєкту:
     ```bash
     python -m http.server 8000 --directory visual_poc
     ```
     Відкрити в браузері: http://127.0.0.1:8000

4. Підніми руку перед камерою — жест (idle / ready / action / scroll / raised_hand) змінює колір квадрата.

**Як протестувати зір, кліки вказівним і інтерактивні зони:** → **[TESTING.md](TESTING.md)**

## Налаштування (config.py або .env)

| Змінна | Опис | За замовчуванням |
|--------|------|-------------------|
| `VISUAL_BRIDGE_ENABLED` | Увімкнути міст | `true` |
| `VISUAL_OSC_HOST` | IP приймача OSC (TouchDesigner тощо) | `127.0.0.1` |
| `VISUAL_OSC_PORT` | Порт OSC (UDP) | `9000` |
| `VISUAL_WS_PORT` | Порт WebSocket для веб-клієнтів | `8766` |
| `VISUAL_QUIET_UI` | Не оновлювати статус з жестів (менше мерехтіння) | `true` |
| `VISUAL_GESTURE_HOLD_SEC` | Секунд утримання пози для шорткат-жестів | `1.2` |
| `VISUAL_GESTURE_SCREENSHOT` | Жест «скріншот» (утримати пози) | `false` |
| `VISUAL_GESTURE_MEDIA` | Жест «медіа play/pause» | `false` |
| `VISUAL_GESTURE_SHOW_DESKTOP` | Жест «показати робочий стіл» (Win+D) | `false` |
| `VISUAL_GESTURE_LOCK_PC` | Жест «блокувати ПК» (Win+L) | `false` |

## Адреси OSC (для TouchDesigner / Unity / Unreal)

- `/atlas/hand/gesture` (string) — `idle` | `ready` | `action` | `scroll` | `raised_hand`
- `/atlas/hand/x` (float) — нормалізована X [0..1]
- `/atlas/hand/y` (float) — нормалізована Y [0..1]
- `/atlas/visual/color` (string) — PoC колір: `red` | `yellow` | `green` | `blue` | `cyan`

## Далі (Roadmap)

- **Фізичний тест і простір:** TouchDesigner (OSC In CHOP/DAT, Lag CHOP, коло за x/y, жести), KantanMapper, проектор. → **[TOUCHDESIGNER_SETUP.md](TOUCHDESIGNER_SETUP.md)**
- **Повний план у просторі:** тест "відчуття простору", прив'язка до стін, інтерактивні зони (кліки), реальні віджети. → **[SPATIAL_ROADMAP.md](SPATIAL_ROADMAP.md)**
