# Конфигурация для ML Inference Cloud.ru

## 1. Push образа в Artifact Registry

### Шаг 1: Получение ключей доступа

1. Войдите в консоль Cloud.ru
2. Перейдите в **Artifact Registry**
3. Создайте реестр (если еще не создан)
4. Перейдите в **Ключи доступа**
5. Создайте новый ключ и сохраните:
   - **Key ID** (используется как username)
   - **Key Secret** (используется как password)

### Шаг 2: Аутентификация в Artifact Registry

```bash
# Замените на ваш registry endpoint (например: registry-xxxxx.cr.cloud.ru)
export REGISTRY_ENDPOINT="registry-xxxxx.cr.cloud.ru"
export KEY_ID="your-key-id"
export KEY_SECRET="your-key-secret"

# Вход в registry
docker login $REGISTRY_ENDPOINT -u $KEY_ID -p $KEY_SECRET
```

### Шаг 3: Тегирование образа

```bash
# Создаем тег с полным путем к registry
docker tag paddleocr-vl-service:latest $REGISTRY_ENDPOINT/paddleocr-vl-service:latest
docker tag paddleocr-vl-service:latest $REGISTRY_ENDPOINT/paddleocr-vl-service:1.0.0
```

### Шаг 4: Push образа

```bash
# Push в Artifact Registry
docker push $REGISTRY_ENDPOINT/paddleocr-vl-service:latest
docker push $REGISTRY_ENDPOINT/paddleocr-vl-service:1.0.0
```

**Примечание:** Размер образа ~18GB, push может занять 10-30 минут в зависимости от скорости соединения.

---

## 2. Настройки для ML Inference

### Базовая конфигурация

**Docker Image:**
```
registry-xxxxx.cr.cloud.ru/paddleocr-vl-service:latest
```

**Platform:** `linux/amd64`

### Порты (Ports)

| Порт | Протокол | Назначение | Публичный доступ |
|------|----------|------------|------------------|
| 8081 | HTTP | FastAPI Handler (основной API) | ✅ Да (8081) |
| 8080 | HTTP | vLLM Server (опционально) | ⚠️ Опционально |

**Рекомендация:** Экспонируйте только порт 8081 для внешнего доступа.

### Health Checks

#### Liveness Probe

**Endpoint:** `GET http://localhost:8081/health`

**Конфигурация:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8081
  initialDelaySeconds: 60      # Даем время на инициализацию моделей
  periodSeconds: 30            # Проверка каждые 30 секунд
  timeoutSeconds: 10           # Таймаут 10 секунд
  failureThreshold: 3          # 3 неудачных попытки = рестарт
  successThreshold: 1
```

**Ожидаемый ответ:**
```json
{
  "status": "healthy",
  "paddleocr": "ready",
  "s3_storage": "configured|not_configured"
}
```

#### Readiness Probe

**Endpoint:** `GET http://localhost:8081/health`

**Конфигурация:**
```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8081
  initialDelaySeconds: 90      # Больше времени на полную инициализацию
  periodSeconds: 15            # Частая проверка готовности
  timeoutSeconds: 5
  failureThreshold: 3
  successThreshold: 1
```

**Примечание:** Readiness probe использует тот же endpoint, но с более строгими требованиями к времени инициализации.

#### Startup Probe (опционально, рекомендуется)

**Endpoint:** `GET http://localhost:8081/health`

**Конфигурация:**
```yaml
startupProbe:
  httpGet:
    path: /health
    port: 8081
  initialDelaySeconds: 0
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 30         # До 5 минут на старт (30 * 10s)
  successThreshold: 1
```

### Ресурсы (Resources)

**Рекомендуемые значения:**

```yaml
resources:
  requests:
    cpu: "4"                   # Минимум 4 CPU
    memory: "16Gi"             # Минимум 16GB RAM
    nvidia.com/gpu: "1"        # 1 GPU (обязательно для CUDA)
  limits:
    cpu: "8"                   # До 8 CPU
    memory: "32Gi"             # До 32GB RAM
    nvidia.com/gpu: "1"        # 1 GPU
```

**Минимальные требования:**
- CPU: 4 cores
- Memory: 16GB
- GPU: 1x NVIDIA GPU (CUDA 12.6+)

### Переменные окружения (Environment Variables)

#### Обязательные (для работы OCR)

Не требуется обязательных переменных для базовой работы.

#### Опциональные (для S3 сохранения)

```yaml
env:
  - name: CLOUDRU_S3_ENDPOINT
    value: "https://s3.cloud.ru"              # Endpoint Object Storage
  
  - name: CLOUDRU_S3_BUCKET
    value: "your-bucket-name"                 # Имя bucket
  
  - name: CLOUDRU_S3_ACCESS_KEY
    valueFrom:
      secretKeyRef:
        name: cloudru-s3-credentials
        key: access-key
  
  - name: CLOUDRU_S3_SECRET_KEY
    valueFrom:
      secretKeyRef:
        name: cloudru-s3-credentials
        key: secret-key
```

**Создание Secret для S3 credentials:**
```bash
kubectl create secret generic cloudru-s3-credentials \
  --from-literal=access-key=your-access-key \
  --from-literal=secret-key=your-secret-key
```

### Volumes (если требуется локальное хранение)

Для локального хранения результатов (опционально):

```yaml
volumeMounts:
  - name: output-storage
    mountPath: /app/output
volumes:
  - name: output-storage
    persistentVolumeClaim:
      claimName: paddleocr-output-pvc
```

**Примечание:** Если настроен S3, локальное хранение не требуется.

### Replicas и Scaling

**Рекомендации:**
- **Min replicas:** 1 (GPU ресурсы дорогие)
- **Max replicas:** 2-3 (в зависимости от нагрузки)
- **Autoscaling:** На основе CPU/Memory (не GPU метрик)

```yaml
autoscaling:
  minReplicas: 1
  maxReplicas: 3
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

---

## 3. Полная конфигурация YAML для Kubernetes

Пример полной конфигурации для деплоя:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: paddleocr-vl-service
  labels:
    app: paddleocr-vl
spec:
  replicas: 1
  selector:
    matchLabels:
      app: paddleocr-vl
  template:
    metadata:
      labels:
        app: paddleocr-vl
    spec:
      containers:
      - name: paddleocr-vl
        image: registry-xxxxx.cr.cloud.ru/paddleocr-vl-service:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8081
          name: http-api
          protocol: TCP
        - containerPort: 8080
          name: vllm
          protocol: TCP
        env:
        - name: CLOUDRU_S3_ENDPOINT
          value: "https://s3.cloud.ru"
        - name: CLOUDRU_S3_BUCKET
          value: "your-bucket-name"
        - name: CLOUDRU_S3_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: cloudru-s3-credentials
              key: access-key
        - name: CLOUDRU_S3_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: cloudru-s3-credentials
              key: secret-key
        resources:
          requests:
            cpu: "4"
            memory: "16Gi"
            nvidia.com/gpu: "1"
          limits:
            cpu: "8"
            memory: "32Gi"
            nvidia.com/gpu: "1"
        livenessProbe:
          httpGet:
            path: /health
            port: 8081
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8081
          initialDelaySeconds: 90
          periodSeconds: 15
          timeoutSeconds: 5
          failureThreshold: 3
        startupProbe:
          httpGet:
            path: /health
            port: 8081
          initialDelaySeconds: 0
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 30
---
apiVersion: v1
kind: Service
metadata:
  name: paddleocr-vl-service
spec:
  type: LoadBalancer
  selector:
    app: paddleocr-vl
  ports:
  - name: http-api
    port: 8081
    targetPort: 8081
    protocol: TCP
```

---

## 4. Настройки через Cloud.ru ML Inference UI

### Основные параметры:

1. **Docker Image:** `registry-xxxxx.cr.cloud.ru/paddleocr-vl-service:latest`
2. **Port:** `8081`
3. **Protocol:** `HTTP`
4. **Health Check Path:** `/health`
5. **Health Check Port:** `8081`

### Ресурсы:
- **CPU:** 4-8 cores
- **Memory:** 16-32 GB
- **GPU:** 1x NVIDIA (CUDA 12.6+)

### Environment Variables:
- `CLOUDRU_S3_ENDPOINT` (опционально)
- `CLOUDRU_S3_BUCKET` (опционально)
- `CLOUDRU_S3_ACCESS_KEY` (опционально)
- `CLOUDRU_S3_SECRET_KEY` (опционально)

---

## 5. Тестирование после деплоя

### Проверка health endpoint

```bash
# Замените на ваш endpoint ML Inference
export ML_ENDPOINT="https://your-modelrun-id.modelrun.inference.cloud.ru"

# Health check
curl $ML_ENDPOINT/health

# Health check vLLM (если нужно)
curl $ML_ENDPOINT/health/vllm
```

### Тест OCR обработки

```bash
# Multipart upload
curl -X POST "$ML_ENDPOINT/ocr" \
  -F "file=@test_image.jpg"

# URL image
curl -X POST "$ML_ENDPOINT/ocr" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "image_url=https://example.com/image.jpg"
```

---

## 6. Мониторинг и логи

### Просмотр логов

```bash
# Логи контейнера
kubectl logs -f deployment/paddleocr-vl-service

# Логи последнего запуска
kubectl logs deployment/paddleocr-vl-service --tail=100
```

### Метрики

Мониторинг через Cloud.ru ML Inference Dashboard:
- CPU/Memory utilization
- GPU utilization
- Request latency
- Error rate

---

## 7. Troubleshooting

### Контейнер не стартует

1. Проверьте логи: `kubectl logs deployment/paddleocr-vl-service`
2. Убедитесь, что GPU доступен: `kubectl describe node`
3. Проверьте ресурсы: увеличьте memory/CPU если нужно

### Health check fails

1. Увеличьте `initialDelaySeconds` до 120-180 секунд
2. Проверьте, что порт 8081 доступен
3. Убедитесь, что FastAPI запустился

### OCR не работает

1. Проверьте, что PaddleOCR-VL инициализирован в логах
2. Убедитесь, что GPU доступен и CUDA работает
3. Проверьте входные данные (формат изображения)

---

## 8. Оптимизация производительности

### Рекомендации:

1. **Pre-warming:** Запустить health check несколько раз после старта для инициализации моделей
2. **Batch processing:** Группируйте запросы для лучшей утилизации GPU
3. **Caching:** Кэшируйте результаты для повторяющихся изображений
4. **Resource allocation:** Мониторьте GPU utilization и корректируйте ресурсы

---

## Итоговая конфигурация для ML Inference

**Минимальные настройки:**
- Port: `8081`
- Health Path: `/health`
- Health Port: `8081`
- Initial Delay: `120` секунд
- CPU: `4`
- Memory: `16Gi`
- GPU: `1`

