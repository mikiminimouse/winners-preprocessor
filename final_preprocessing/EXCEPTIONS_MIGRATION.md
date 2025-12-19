# Миграция Exceptions директорий

## ✅ Выполнено

### Изменения в структуре

Exceptions теперь находятся в отдельной директории `Data/Exceptions/YYYY-MM-DD/`, аналогично `Data/Merge/YYYY-MM-DD/`.

**Было:**
```
Data/Processing/2025-03-18/
├── Pending_1/
├── Pending_2/
├── Pending_3/
├── Exceptions_1/  ❌
├── Exceptions_2/  ❌
└── Exceptions_3/  ❌
```

**Стало:**
```
Data/Processing/2025-03-18/
├── Pending_1/
├── Pending_2/
└── Pending_3/

Data/Exceptions/2025-03-18/
├── Exceptions_1/  ✅
├── Exceptions_2/  ✅
└── Exceptions_3/  ✅
```

### Обновления в коде

1. **`docprep/core/config.py`**:
   - ✅ `EXCEPTIONS_DIR` теперь отдельная директория (не внутри Processing)
   - ✅ `get_cycle_paths()` принимает параметр `exceptions_base`
   - ✅ `init_directory_structure()` создает Exceptions в правильном месте
   - ✅ `get_data_paths()` возвращает путь к exceptions

2. **Перемещение данных**:
   - ✅ Все существующие Exceptions перемещены из `Processing/2025-03-18/` в `Exceptions/2025-03-18/`
   - ✅ Старые директории удалены из Processing

### Использование

```python
from docprep.core.config import get_cycle_paths, get_data_paths

# Получение путей для цикла
paths = get_data_paths('2025-03-18')
cycle_paths = get_cycle_paths(
    1, 
    processing_base=paths['processing'],
    merge_base=paths['merge'],
    exceptions_base=paths['exceptions']  # Новый параметр
)

# exceptions теперь указывает на Data/Exceptions/2025-03-18/Exceptions_1
print(cycle_paths['exceptions'])
# Data/Exceptions/2025-03-18/Exceptions_1
```

### Обратная совместимость

Функция `get_cycle_paths()` обратно совместима:
- Если `exceptions_base` не указан, используется `EXCEPTIONS_DIR` по умолчанию
- Все существующие вызовы будут работать корректно

