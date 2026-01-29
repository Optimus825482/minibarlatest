# Design Document: Kod İnceleme Düzeltmeleri

## Overview

Bu tasarım dokümanı, KOD_INCELEME_RAPORU_2026.md'de tespit edilen güvenlik açıkları ve kod kalitesi sorunlarının düzeltilmesi için teknik çözümleri detaylandırır. Düzeltmeler öncelik sırasına göre (Kritik → Yüksek → Orta) uygulanacaktır.

## Architecture

Mevcut Flask tabanlı monolitik mimari korunacak. Değişiklikler aşağıdaki katmanlarda yapılacaktır:

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (JS)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ DOMPurify   │  │ Constants   │  │ Sanitized innerHTML │ │
│  │ Integration │  │ Definition  │  │ Usage               │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                      Backend (Python)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Secure Auth │  │ SQL         │  │ Error Response      │ │
│  │ (Env Vars)  │  │ Whitelist   │  │ Standardization     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ JSON        │  │ Query       │  │ Logging             │ │
│  │ Validation  │  │ Optimization│  │ Consistency         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Secure Authentication Component

**Dosya:** `routes/developer_routes.py`

```python
import os
from werkzeug.security import check_password_hash

# Environment variable'dan hash'li şifre oku
DEVELOPER_PASSWORD_HASH = os.getenv('DEVELOPER_PASSWORD_HASH')

def verify_developer_password(password: str) -> bool:
    """
    Developer şifresini güvenli şekilde doğrula.

    Args:
        password: Kullanıcının girdiği şifre

    Returns:
        bool: Şifre doğruysa True
    """
    if not DEVELOPER_PASSWORD_HASH:
        return False
    return check_password_hash(DEVELOPER_PASSWORD_HASH, password)
```

### 2. SQL Whitelist Component

**Dosya:** `utils/rollback_manager.py`

```python
# İzin verilen tablo adları whitelist'i
ALLOWED_TABLES = [
    'kullanicilar', 'oteller', 'odalar', 'katlar', 'urunler',
    'urun_gruplari', 'stok_hareketleri', 'minibar_islemler',
    'misafir_kayitlari', 'gorevler', 'zimmetler', 'zimmet_detaylari',
    'tedarikci', 'satin_alma_islem', 'satin_alma_detay',
    'fiyatlandirma', 'kampanyalar', 'oda_tipi', 'setup',
    'setup_urun', 'ml_alerts', 'ml_features', 'query_logs'
]

def validate_table_name(table: str) -> None:
    """
    Tablo adını whitelist'e karşı doğrula.

    Args:
        table: Doğrulanacak tablo adı

    Raises:
        ValueError: Tablo adı whitelist'te yoksa
    """
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Geçersiz tablo adı: {table}")
```

**Dosya:** `utils/monitoring/query_analyzer.py`

```python
ALLOWED_QUERY_PREFIXES = ['SELECT', 'WITH']

def validate_query_for_explain(query_text: str) -> bool:
    """
    Query'nin explain için güvenli olup olmadığını kontrol et.

    Args:
        query_text: SQL query metni

    Returns:
        bool: Query güvenliyse True
    """
    query_upper = query_text.strip().upper()
    return any(query_upper.startswith(prefix) for prefix in ALLOWED_QUERY_PREFIXES)
```

### 3. XSS Protection Component

**Dosya:** `static/js/vendor/purify.min.js` (DOMPurify kütüphanesi)

**Kullanım Örneği:**

```javascript
// Güvenli innerHTML kullanımı
function safeSetInnerHTML(element, html) {
  if (typeof DOMPurify !== "undefined") {
    element.innerHTML = DOMPurify.sanitize(html);
  } else {
    element.textContent = html.replace(/<[^>]*>/g, "");
  }
}
```

### 4. JSON Validation Helper

**Dosya:** `utils/helpers.py`

```python
from flask import jsonify, request

def get_json_or_error():
    """
    Request JSON'ını güvenli şekilde al.

    Returns:
        tuple: (data, error_response) - data varsa error_response None
    """
    data = request.get_json()
    if not data:
        return None, (jsonify({
            'success': False,
            'error': 'Geçersiz JSON verisi'
        }), 400)
    return data, None
```

### 5. Error Response Helper

**Dosya:** `utils/helpers.py`

```python
def error_response(message: str, status_code: int = 400):
    """
    Standart hata response'u oluştur.

    Args:
        message: Hata mesajı
        status_code: HTTP status kodu

    Returns:
        tuple: (jsonify response, status_code)
    """
    return jsonify({
        'success': False,
        'error': message,
        'status_code': status_code
    }), status_code

def success_response(data: dict = None, message: str = None):
    """
    Standart başarı response'u oluştur.

    Args:
        data: Response data
        message: Başarı mesajı

    Returns:
        jsonify response
    """
    response = {'success': True}
    if data:
        response['data'] = data
    if message:
        response['message'] = message
    return jsonify(response)
```

## Data Models

Mevcut veri modelleri korunacak. Değişiklik yapılmayacak.

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Property 1: Password Hash Verification

_For any_ password string, if the password matches the original password used to create the hash, `check_password_hash(hash, password)` should return True; otherwise it should return False.

**Validates: Requirements 1.2**

### Property 2: SQL Table Whitelist Validation

_For any_ table name string, if the table name is in ALLOWED_TABLES, `validate_table_name()` should not raise an exception; if the table name is not in ALLOWED_TABLES, it should raise ValueError.

**Validates: Requirements 2.1, 2.2**

### Property 3: Query Prefix Validation

_For any_ SQL query string, if the query starts with 'SELECT' or 'WITH' (case-insensitive), `validate_query_for_explain()` should return True; otherwise it should return False.

**Validates: Requirements 2.3, 2.4**

### Property 4: JSON Validation Response

_For any_ HTTP request with invalid or missing JSON body, the endpoint should return a response with `{'success': False, 'error': 'Geçersiz JSON verisi'}` and status code 400.

**Validates: Requirements 4.1, 4.2**

### Property 5: Error Response Format Consistency

_For any_ error condition in any API endpoint, the response should follow the format `{'success': False, 'error': <message>, 'status_code': <code>}`.

**Validates: Requirements 8.1, 8.2**

### Property 6: Optimized Query Performance

_For any_ call to `get_product_stats()`, the function should execute at most 3 database queries regardless of the number of products.

**Validates: Requirements 5.1, 5.3**

## Error Handling

### Backend Error Handling

```python
# Standart hata yakalama pattern'i
try:
    # İş mantığı
    result = perform_operation()
    return success_response(data=result)
except ValueError as e:
    logger.warning(f"Validation hatası: {str(e)}")
    return error_response(str(e), 400)
except Exception as e:
    logger.error(f"Beklenmeyen hata: {str(e)}", exc_info=True)
    db.session.rollback()
    return error_response("Sunucu hatası oluştu", 500)
```

### Frontend Error Handling

```javascript
// Standart AJAX hata yakalama
fetch(url, options)
  .then((response) => {
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return response.json();
  })
  .then((data) => {
    if (!data.success) {
      throw new Error(data.error || "Bilinmeyen hata");
    }
    // Başarılı işlem
  })
  .catch((error) => {
    console.error("Hata:", error);
    toastGoster(error.message, "error");
  });
```

## Testing Strategy

### Unit Tests

Unit testler `pytest` framework'ü ile yazılacaktır.

**Test Dosyaları:**

- `tests/test_security.py` - Güvenlik testleri
- `tests/test_validation.py` - Validation testleri
- `tests/test_helpers.py` - Helper fonksiyon testleri

### Property-Based Tests

Property-based testler `hypothesis` kütüphanesi ile yazılacaktır.

**Konfigürasyon:**

- Minimum 100 iterasyon per test
- Her test design document property'sine referans verecek

**Test Örnekleri:**

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=100))
def test_password_hash_verification(password):
    """
    Feature: kod-inceleme-duzeltmeleri
    Property 1: Password Hash Verification
    Validates: Requirements 1.2
    """
    from werkzeug.security import generate_password_hash, check_password_hash

    hash = generate_password_hash(password)
    assert check_password_hash(hash, password) == True
    assert check_password_hash(hash, password + "x") == False

@given(st.text(min_size=1, max_size=50))
def test_table_whitelist_validation(table_name):
    """
    Feature: kod-inceleme-duzeltmeleri
    Property 2: SQL Table Whitelist Validation
    Validates: Requirements 2.1, 2.2
    """
    from utils.rollback_manager import ALLOWED_TABLES, validate_table_name

    if table_name in ALLOWED_TABLES:
        validate_table_name(table_name)  # Should not raise
    else:
        with pytest.raises(ValueError):
            validate_table_name(table_name)

@given(st.text(min_size=1, max_size=500))
def test_query_prefix_validation(query):
    """
    Feature: kod-inceleme-duzeltmeleri
    Property 3: Query Prefix Validation
    Validates: Requirements 2.3, 2.4
    """
    from utils.monitoring.query_analyzer import validate_query_for_explain

    query_upper = query.strip().upper()
    expected = query_upper.startswith('SELECT') or query_upper.startswith('WITH')
    assert validate_query_for_explain(query) == expected
```

### Integration Tests

- API endpoint'lerinin doğru response formatı döndürdüğünü test et
- XSS korumasının çalıştığını browser testleri ile doğrula
- N+1 query optimizasyonunun performans artışı sağladığını ölç

## Implementation Notes

### Environment Variable Setup

`.env` dosyasına eklenecek:

```bash
# Developer panel şifresi (hash'lenmiş)
# Oluşturmak için: python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('YOUR_PASSWORD'))"
DEVELOPER_PASSWORD_HASH=pbkdf2:sha256:260000$...
```

### DOMPurify Entegrasyonu

1. DOMPurify CDN veya npm'den indirilecek
2. `static/js/vendor/purify.min.js` olarak kaydedilecek
3. `templates/base.html`'e script tag eklenecek
4. Tüm innerHTML kullanımları DOMPurify.sanitize() ile sarılacak

### Logging Standardizasyonu

```python
import logging

logger = logging.getLogger(__name__)

# print() yerine:
logger.info("Bilgi mesajı")
logger.warning("Uyarı mesajı")
logger.error("Hata mesajı", exc_info=True)
logger.debug("Debug mesajı")
```
