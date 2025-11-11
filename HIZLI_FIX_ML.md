# 🚨 HIZLI ML SEQUENCE FIX

## Sorun
```
null value in column "id" of relation "ml_metrics" violates not-null constraint
```

## ⚡ Hızlı Çözüm (Tek Komut)

```bash
docker exec -it c2358aa575ec psql -U postgres -d minibar_takip -c "
DO \$\$
DECLARE
    max_id INTEGER;
BEGIN
    -- ml_metrics
    SELECT COALESCE(MAX(id), 0) INTO max_id FROM ml_metrics;
    CREATE SEQUENCE IF NOT EXISTS ml_metrics_id_seq;
    EXECUTE format('ALTER SEQUENCE ml_metrics_id_seq RESTART WITH %s', max_id + 1);
    ALTER TABLE ml_metrics ALTER COLUMN id SET DEFAULT nextval('ml_metrics_id_seq');
    ALTER SEQUENCE ml_metrics_id_seq OWNED BY ml_metrics.id;
    RAISE NOTICE 'ml_metrics OK (next: %)', max_id + 1;
    
    -- ml_models
    SELECT COALESCE(MAX(id), 0) INTO max_id FROM ml_models;
    CREATE SEQUENCE IF NOT EXISTS ml_models_id_seq;
    EXECUTE format('ALTER SEQUENCE ml_models_id_seq RESTART WITH %s', max_id + 1);
    ALTER TABLE ml_models ALTER COLUMN id SET DEFAULT nextval('ml_models_id_seq');
    ALTER SEQUENCE ml_models_id_seq OWNED BY ml_models.id;
    RAISE NOTICE 'ml_models OK (next: %)', max_id + 1;
    
    -- ml_alerts
    SELECT COALESCE(MAX(id), 0) INTO max_id FROM ml_alerts;
    CREATE SEQUENCE IF NOT EXISTS ml_alerts_id_seq;
    EXECUTE format('ALTER SEQUENCE ml_alerts_id_seq RESTART WITH %s', max_id + 1);
    ALTER TABLE ml_alerts ALTER COLUMN id SET DEFAULT nextval('ml_alerts_id_seq');
    ALTER SEQUENCE ml_alerts_id_seq OWNED BY ml_alerts.id;
    RAISE NOTICE 'ml_alerts OK (next: %)', max_id + 1;
    
    -- ml_training_logs
    SELECT COALESCE(MAX(id), 0) INTO max_id FROM ml_training_logs;
    CREATE SEQUENCE IF NOT EXISTS ml_training_logs_id_seq;
    EXECUTE format('ALTER SEQUENCE ml_training_logs_id_seq RESTART WITH %s', max_id + 1);
    ALTER TABLE ml_training_logs ALTER COLUMN id SET DEFAULT nextval('ml_training_logs_id_seq');
    ALTER SEQUENCE ml_training_logs_id_seq OWNED BY ml_training_logs.id;
    RAISE NOTICE 'ml_training_logs OK (next: %)', max_id + 1;
END \$\$;
"
```

## ✅ Kontrol

```bash
docker exec -it c2358aa575ec psql -U postgres -d minibar_takip -c "
SELECT 
    'ml_metrics' as tablo,
    last_value as sonraki_id
FROM ml_metrics_id_seq
UNION ALL
SELECT 'ml_models', last_value FROM ml_models_id_seq
UNION ALL
SELECT 'ml_alerts', last_value FROM ml_alerts_id_seq
UNION ALL
SELECT 'ml_training_logs', last_value FROM ml_training_logs_id_seq;
"
```

## 🔄 Uygulama Restart

```bash
# Coolify'da uygulamayı restart et
docker restart 1c40bfcee1a3
```

## 🧪 Test

ML Dashboard'a git ve hata kaybolmalı:
http://h8k8wo040wc48gc4k8skwokw.185.9.38.66.sslip.io/ml/dashboard
