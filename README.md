# Proxmox CPU Dashboard v2

Нативное расширение Proxmox VE: сбор максимума данных с железа и управление CPU через **официальный API** (`:8006`, ACL, CSRF). Без отдельного HTTP-сервиса на `:8087`.

## Стек

| Слой | Технология |
|------|------------|
| API | Perl `PVE::API2::Nodes::Nodeinfo` (`register_method`) |
| Сбор данных | Python 3 `pve-hw-collect.py` (sysfs, lm-sensors, powercap, hwmon, meminfo, lsblk) |
| Применение настроек | Python 3 `pve-hw-apply.py` + bash `pve-cpufreq-set.sh` / `pve-cpus-set.sh` |
| UI | ExtJS override `PVE.node.StatusView` → `Proxmox.Utils.API2Request` |

## API (нативное, порт 8006)

Требуются права PVE: `Sys.Audit` (чтение), `Sys.Modify` (запись).

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/nodes/{node}/hw` | Полный снимок железа (JSON) |
| POST | `/nodes/{node}/hw/cpufreq` | Governor + max_freq (kHz) |
| POST | `/nodes/{node}/hw/cpus` | Число online logical CPUs |
| POST | `/nodes/{node}/hw/apply` | Профиль или комбинация параметров |
| POST | `/nodes/{node}/cpufreq` | Legacy alias → тот же apply |
| GET | `/nodes/{node}/status` | Поле `thermalstate` = compact JSON от коллектора |

Примеры:

```bash
pvesh get /nodes/$(hostname -s)/hw
pvesh create /nodes/$(hostname -s)/hw/apply --profile balanced
pvesh create /nodes/$(hostname -s)/hw/cpufreq --governor ondemand --max_freq 1700000
```

Home Assistant: [ha-proxmox-cpu-ctl](https://github.com/mrkvka/ha-proxmox-cpu-ctl) — перевести на PVE API token (`:8006`), не на `:8087`.

## Что собирается

- **CPU**: governor, частоты, per-core, topology, online/offline
- **Sensors**: lm-sensors (`sensors -jA`), нормализованные temp/fan/voltage/power
- **hwmon**: все `/sys/class/hwmon/*`
- **RAPL**: powercap zones, package watts
- **Memory**: `/proc/meminfo`
- **Disks**: `lsblk -J` (модель, размер, температура если есть)
- **System**: load, uptime, kernel, `pveversion`
- **Profiles**: performance, balanced, powersave, emergency, restore

## Установка

```bash
git clone https://github.com/mrkvka/proxmox-cpu-dashboard.git
cd proxmox-cpu-dashboard
git checkout cursor/native-hw-v2-aa7b   # или master после merge
bash install.sh
```

В браузере: **Node → Summary → Ctrl+Shift+R**.

## Удаление

```bash
bash uninstall.sh
```

## Безопасность

- Весь трафик через **pveproxy** (TLS, роли, audit).
- Нет открытого API на `:8087`.
- Запись в sysfs только через валидированные скрипты.

## Аудит железа

```bash
/usr/local/bin/pve-hw-collect.py --pretty | less
```

## Лицензия

MIT
