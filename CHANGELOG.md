# Changelog

## [3.0.0] — 2026-05-22

Стабильный релиз нативного hardware dashboard для Proxmox VE 9.x.

### Добавлено
- Вкладка **Node → Hardware** (сразу после Summary)
- Таблица инвентаря: Parameter | Available | Applied | Source
- Live-обновление `GET /nodes/{node}/hwlive` каждую 1 с
- Подсветка изменений ячеек (flash up/down/changed)
- Полный сбор: CPU, sensors, RAPL, память, диски (SMART/NVMe), сеть, платформа
- Управление: governor, max MHz, online CPUs, пресеты, Apply
- Метрики дисков: ёмкость и lifetime read/write в **GiB/TiB**, Power-on hours в **часах**

### Изменено
- API только через **pveproxy :8006** (без sidecar `:8087`)
- `thermalstate` = compact JSON от `pve-hw-collect.py`
- Summary: термометрия и CPU controls; инвентарь перенесён на Hardware

### Удалено
- `pve-cpufreq-api.py` и systemd-сервис на порту 8087

### Требования
- Proxmox VE 9.x, `lm-sensors`, `smartctl` (опционально, для дисков)

## [0.5.0] и ранее
- Summary-only UI + HTTP API на :8087 (legacy, см. теги до v3)
