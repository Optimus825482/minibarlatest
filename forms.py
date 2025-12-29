from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, IntegerField, SelectField, SelectMultipleField, DecimalField, DateField, DateTimeField
from wtforms.validators import DataRequired, InputRequired, Email, Length, EqualTo, NumberRange, Optional, ValidationError
import re


def pattern_validator(pattern, message):
    """Return a validator that enforces a regex pattern when field has data."""
    compiled = re.compile(pattern)

    def _validator(form, field):
        data = field.data or ''
        if data and not compiled.match(data):
            raise ValidationError(message)

    return _validator


def password_strength_validator(message):
    """Ensure password includes upper, lower, digit and special characters."""
    def _validator(form, field):
        data = field.data or ''
        if not data:
            return

        conditions = (
            re.search(r'[A-Z]', data),
            re.search(r'[a-z]', data),
            re.search(r'\d', data),
            re.search(r'[!@#$%^&*(),.?":{}|<>]', data)
        )

        if not all(conditions):
            raise ValidationError(message)

    return _validator

class BaseForm(FlaskForm):
    """Base form with common validators"""
    
    def validate_email(self, field):
        """Custom email validation with Turkish domain support"""
        email = field.data
        if email and '@' in email:
            # Allow common Turkish email domains
            turkish_domains = ['hotmail.com', 'gmail.com', 'yahoo.com', 'yandex.com', 
                              'outlook.com', 'msn.com', 'windowslive.com',
                              'edu.tr', '.gov.tr', '.org.tr', '.net.tr',
                              'turkcell.com.tr', 'ttk.gov.tr']
            
            if not any(domain in email.lower() for domain in turkish_domains):
                # Basic email pattern validation
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, email):
                    raise ValidationError('Geçerli bir e-posta adresi giriniz.')

class LoginForm(BaseForm):
    """Enhanced login form with advanced validation"""
    kullanici_adi = StringField(
        'Kullanıcı Adı', 
        validators=[
            DataRequired(message='Kullanıcı adı zorunludur.'),
            Length(min=3, max=50, message='Kullanıcı adı 3-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-Z0-9_.-]+$', 'Kullanıcı adı sadece harf, rakam ve özel karakterler (_ - .) içerebilir.')
        ]
    )
    
    sifre = PasswordField(
        'Şifre', 
        validators=[
            DataRequired(message='Şifre zorunludur.'),
            Length(min=6, max=128, message='Şifre 6-128 karakter arasında olmalıdır.')
        ]
    )
    
    remember_me = BooleanField('Beni Hatırla')

class SetupForm(BaseForm):
    """Enhanced setup form with comprehensive validation"""
    otel_adi = StringField(
        'Otel Adı', 
        validators=[
            DataRequired(message='Otel adı zorunludur.'),
            Length(min=2, max=200, message='Otel adı 2-200 karakter arasında olmalıdır.')
        ]
    )
    
    adres = StringField(
        'Adres', 
        validators=[
            Optional(),
            Length(max=500, message='Adres 500 karakterden uzun olamaz.')
        ]
    )
    
    telefon = StringField(
        'Telefon', 
        validators=[
            DataRequired(message='Telefon numarası zorunludur.'),
            Length(min=10, max=20, message='Telefon numarası 10-20 karakter arasında olmalıdır.'),
            pattern_validator(r'^[\d\s\-\+\(\)\.]+$', 'Geçerli bir telefon numarası giriniz.')
        ]
    )
    
    email = StringField(
        'E-posta', 
        validators=[
            Optional(),
            Email(message='Geçerli bir e-posta adresi giriniz.'),
            Length(max=100, message='E-posta adresi 100 karakterden uzun olamaz.')
        ]
    )
    
    vergi_no = StringField(
        'Vergi Numarası', 
        validators=[
            Optional(),
            Length(max=20, message='Vergi numarası 20 karakterden uzun olamaz.'),
            pattern_validator(r'^\d+$', 'Vergi numarası sadece rakam içerebilir.')
        ]
    )
    
    kullanici_adi = StringField(
        'Sistem Yöneticisi Kullanıcı Adı', 
        validators=[
            DataRequired(message='Kullanıcı adı zorunludur.'),
            Length(min=3, max=50, message='Kullanıcı adı 3-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-Z0-9_.-]+$', 'Kullanıcı adı sadece harf, rakam ve özel karakterler (_ - .) içerebilir.')
        ]
    )
    
    ad = StringField(
        'Ad', 
        validators=[
            DataRequired(message='Ad zorunludur.'),
            Length(min=2, max=50, message='Ad 2-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-ZğüşöçıİĞÜŞÖÇı\s]+$', 'Ad sadece harf içerebilir.')
        ]
    )
    
    soyad = StringField(
        'Soyad', 
        validators=[
            DataRequired(message='Soyad zorunludur.'),
            Length(min=2, max=50, message='Soyad 2-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-ZğüşöçıİĞÜŞÖÇı\s]+$', 'Soyad sadece harf içerebilir.')
        ]
    )
    
    admin_email = StringField(
        'Sistem Yöneticisi E-posta', 
        validators=[
            DataRequired(message='E-posta adresi zorunludur.'),
            Email(message='Geçerli bir e-posta adresi giriniz.'),
            Length(max=100, message='E-posta adresi 100 karakterden uzun olamaz.')
        ]
    )
    
    admin_telefon = StringField(
        'Sistem Yöneticisi Telefon', 
        validators=[
            Optional(),
            Length(max=20, message='Telefon numarası 20 karakterden uzun olamaz.'),
            pattern_validator(r'^[\d\s\-\+\(\)\.]+$', 'Geçerli bir telefon numarası giriniz.')
        ]
    )
    
    sifre = PasswordField(
        'Şifre', 
        validators=[
            DataRequired(message='Şifre zorunludur.'),
            Length(min=8, max=128, message='Şifre en az 8 karakter olmalıdır.'),
            password_strength_validator('Şifre en az bir büyük harf, bir küçük harf, bir rakam ve bir özel karakter içermelidir.')
        ]
    )
    
    sifre_onay = PasswordField(
        'Şifre Onayı', 
        validators=[
            DataRequired(message='Şifre onayı zorunludur.'),
            EqualTo('sifre', message='Şifreler eşleşmiyor.')
        ]
    )

class PersonelForm(BaseForm):
    """Enhanced personnel form"""
    kullanici_adi = StringField(
        'Kullanıcı Adı', 
        validators=[
            DataRequired(message='Kullanıcı adı zorunludur.'),
            Length(min=3, max=50, message='Kullanıcı adı 3-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-Z0-9_.-]+$', 'Kullanıcı adı sadece harf, rakam ve özel karakterler (_ - .) içerebilir.')
        ]
    )
    
    ad = StringField(
        'Ad', 
        validators=[
            DataRequired(message='Ad zorunludur.'),
            Length(min=2, max=50, message='Ad 2-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-ZğüşöçıİĞÜŞÖÇı\s]+$', 'Ad sadece harf içerebilir.')
        ]
    )
    
    soyad = StringField(
        'Soyad', 
        validators=[
            DataRequired(message='Soyad zorunludur.'),
            Length(min=2, max=50, message='Soyad 2-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-ZğüşöçıİĞÜŞÖÇı\s]+$', 'Soyad sadece harf içerebilir.')
        ]
    )
    
    email = StringField(
        'E-posta', 
        validators=[
            Optional(),
            Email(message='Geçerli bir e-posta adresi giriniz.'),
            Length(max=100, message='E-posta adresi 100 karakterden uzun olamaz.')
        ]
    )
    
    telefon = StringField(
        'Telefon', 
        validators=[
            Optional(),
            Length(max=20, message='Telefon numarası 20 karakterden uzun olamaz.'),
            pattern_validator(r'^[\d\s\-\+\(\)\.]+$', 'Geçerli bir telefon numarası giriniz.')
        ]
    )
    
    rol = SelectField(
        'Rol',
        choices=[
            ('sistem_yoneticisi', 'Sistem Yöneticisi'),
            ('depo_sorumlusu', 'Depo Sorumlusu'),
            ('kat_sorumlusu', 'Kat Sorumlusu')
        ],
        validators=[DataRequired(message='Rol seçimi zorunludur.')]
    )
    
    sifre = PasswordField(
        'Şifre', 
        validators=[
            DataRequired(message='Şifre zorunludur.'),
            Length(min=8, max=128, message='Şifre en az 8 karakter olmalıdır.'),
            password_strength_validator('Şifre en az bir büyük harf, bir küçük harf, bir rakam ve bir özel karakter içermelidir.')
        ]
    )

# İkinci PersonelForm tanımı kaldırıldı - duplicate temizliği (29.12.2025)
# Yukarıdaki "Enhanced personnel form" versiyonu kullanılıyor

class PersonelDuzenleForm(BaseForm):
    """Personel düzenleme formu (şifre opsiyonel)"""
    kullanici_adi = StringField(
        'Kullanıcı Adı',
        validators=[
            DataRequired(message='Kullanıcı adı zorunludur.'),
            Length(min=3, max=50, message='Kullanıcı adı 3-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-Z0-9_.-]+$', 'Kullanıcı adı sadece harf, rakam ve (_-.) karakterleri içerebilir.')
        ]
    )

    ad = StringField(
        'Ad',
        validators=[
            DataRequired(message='Ad zorunludur.'),
            Length(min=2, max=50, message='Ad 2-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-ZğüşöçıİĞÜŞÖÇı\s]+$', 'Ad sadece harf içerebilir.')
        ]
    )

    soyad = StringField(
        'Soyad',
        validators=[
            DataRequired(message='Soyad zorunludur.'),
            Length(min=2, max=50, message='Soyad 2-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-ZğüşöçıİĞÜŞÖÇı\s]+$', 'Soyad sadece harf içerebilir.')
        ]
    )

    email = StringField(
        'E-posta',
        validators=[
            Optional(),
            Email(message='Geçerli bir e-posta adresi giriniz.'),
            Length(max=100, message='E-posta adresi 100 karakterden uzun olamaz.')
        ]
    )

    telefon = StringField(
        'Telefon',
        validators=[
            Optional(),
            Length(max=20, message='Telefon numarası 20 karakterden uzun olamaz.'),
            pattern_validator(r'^[\d\s\-\+\(\)\.]+$', 'Geçerli bir telefon numarası giriniz.')
        ]
    )

    rol = SelectField(
        'Rol',
        choices=[
            ('sistem_yoneticisi', 'Sistem Yöneticisi'),
            ('depo_sorumlusu', 'Depo Sorumlusu'),
            ('kat_sorumlusu', 'Kat Sorumlusu')
        ],
        validators=[DataRequired(message='Rol seçimi zorunludur.')]
    )

    yeni_sifre = PasswordField(
        'Yeni Şifre',
        validators=[
            Optional(),
            Length(min=8, max=128, message='Şifre en az 8 karakter olmalıdır.'),
            password_strength_validator('Şifre en az bir büyük harf, bir küçük harf, bir rakam ve bir özel karakter içermelidir.')
        ]
    )

class UrunForm(BaseForm):
    """Enhanced product form"""
    grup_id = SelectField(
        'Ürün Grubu', 
        coerce=int,
        choices=[],
        validators=[DataRequired(message='Ürün grubu seçimi zorunludur.')]
    )
    
    urun_adi = StringField(
        'Ürün Adı', 
        validators=[
            DataRequired(message='Ürün adı zorunludur.'),
            Length(min=2, max=100, message='Ürün adı 2-100 karakter arasında olmalıdır.')
        ]
    )
    
    barkod = StringField(
        'Barkod', 
        validators=[
            Optional(),
            Length(max=50, message='Barkod 50 karakterden uzun olamaz.'),
            pattern_validator(r'^[a-zA-Z0-9_.-]+$', 'Barkod sadece harf, rakam ve özel karakterler içerebilir.')
        ]
    )
    
    birim = SelectField(
        'Birim', 
        choices=[('Adet', 'Adet'), ('Kutu', 'Kutu'), ('Şişe', 'Şişe'), ('Paket', 'Paket')],
        validators=[DataRequired(message='Birim seçimi zorunludur.')]
    )
    
    kritik_stok_seviyesi = IntegerField(
        'Kritik Stok Seviyesi', 
        validators=[
            DataRequired(message='Kritik stok seviyesi zorunludur.'),
            NumberRange(min=0, max=10000, message='Kritik stok seviyesi 0-10000 arasında olmalıdır.')
        ]
    )

class StokHareketForm(BaseForm):
    """Enhanced stock movement form"""
    urun_id = SelectField(
        'Ürün',
        coerce=int,
        choices=[],
        validators=[DataRequired(message='Ürün seçimi zorunludur.')]
    )
    
    hareket_tipi = SelectField(
        'Hareket Tipi',
        choices=[('giris', 'Giriş'), ('cikis', 'Çıkış')],
        validators=[DataRequired(message='Hareket tipi seçimi zorunludur.')]
    )
    
    miktar = IntegerField(
        'Miktar', 
        validators=[
            DataRequired(message='Miktar zorunludur.'),
            NumberRange(min=1, max=1000000, message='Miktar 1-1000000 arasında olmalıdır.')
        ]
    )
    
    aciklama = TextAreaField(
        'Açıklama', 
        validators=[
            Optional(),
            Length(max=500, message='Açıklama 500 karakterden uzun olamaz.')
        ]
    )

class MinibarKontrolForm(BaseForm):
    """Enhanced minibar control form"""
    oda_id = SelectField(
        'Oda',
        coerce=int,
        choices=[],
        validators=[DataRequired(message='Oda seçimi zorunludur.')]
    )
    
    islem_tipi = SelectField(
        'İşlem Tipi',
        choices=[('kontrol', 'Kontrol'), ('dolum', 'Dolum')],
        validators=[DataRequired(message='İşlem tipi seçimi zorunludur.')]
    )
    
    aciklama = TextAreaField(
        'Açıklama', 
        validators=[
            Optional(),
            Length(max=500, message='Açıklama 500 karakterden uzun olamaz.')
        ]
    )
    
    # Dynamic fields will be added based on selected products
    @classmethod
    def create_dynamic_fields(cls, urun_ids):
        """Create dynamic fields for product quantities"""
        for urun_id in urun_ids:
            # Quantity field
            field_name = f'miktar_{urun_id}'
            setattr(cls, field_name, IntegerField(
                f'Miktar_{urun_id}',
                validators=[Optional()]
            ))
            
            # Starting stock field
            field_name = f'baslangic_{urun_id}'
            setattr(cls, field_name, IntegerField(
                f'Başlangıç Stok_{urun_id}',
                validators=[Optional()]
            ))
            
            # Ending stock field
            field_name = f'bitis_{urun_id}'
            setattr(cls, field_name, IntegerField(
                f'Bitiş Stok_{urun_id}',
                validators=[Optional()]
            ))

class OtelForm(BaseForm):
    """Otel tanımlama/düzenleme formu"""
    ad = StringField(
        'Otel Adı',
        validators=[
            DataRequired(message='Otel adı zorunludur.'),
            Length(min=2, max=200, message='Otel adı 2-200 karakter arasında olmalıdır.')
        ]
    )

    adres = TextAreaField(
        'Adres',
        validators=[
            Optional(),
            Length(max=500, message='Adres 500 karakterden uzun olamaz.')
        ]
    )

    telefon = StringField(
        'Telefon',
        validators=[
            Optional(),
            Length(max=20, message='Telefon numarası 20 karakterden uzun olamaz.'),
            pattern_validator(r'^[\d\s\-\+\(\)\.]+$', 'Geçerli bir telefon numarası giriniz.')
        ]
    )

    email = StringField(
        'E-posta',
        validators=[
            Optional(),
            Email(message='Geçerli bir e-posta adresi giriniz.'),
            Length(max=100, message='E-posta adresi 100 karakterden uzun olamaz.')
        ]
    )
    
    vergi_no = StringField(
        'Vergi No',
        validators=[
            Optional(),
            Length(max=50, message='Vergi no 50 karakterden uzun olamaz.')
        ]
    )
    
    logo = FileField(
        'Otel Logosu',
        validators=[
            Optional(),
            FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Sadece resim dosyaları yüklenebilir (jpg, jpeg, png, gif)')
        ]
    )
    
    aktif = BooleanField('Aktif', default=True)

class KatForm(BaseForm):
    """Kat tanımlama/düzenleme formu"""
    otel_id = SelectField(
        'Otel',
        coerce=int,
        choices=[],
        validators=[DataRequired(message='Otel seçimi zorunludur.')]
    )
    
    kat_adi = StringField(
        'Kat Adı',
        validators=[
            DataRequired(message='Kat adı zorunludur.'),
            Length(min=1, max=50, message='Kat adı 1-50 karakter arasında olmalıdır.')
        ]
    )

    kat_no = IntegerField(
        'Kat Numarası',
        validators=[
            InputRequired(message='Kat numarası zorunludur.'),
            NumberRange(min=-5, max=100, message='Kat numarası -5 ile 100 arasında olmalıdır. (0: Zemin Kat)')
        ]
    )

    aciklama = TextAreaField(
        'Açıklama',
        validators=[
            Optional(),
            Length(max=500, message='Açıklama 500 karakterden uzun olamaz.')
        ]
    )
    
    aktif = BooleanField('Aktif', default=True)

class OdaForm(BaseForm):
    """Oda tanımlama/düzenleme formu"""
    otel_id = SelectField(
        'Otel',
        coerce=int,
        choices=[],
        validators=[DataRequired(message='Otel seçimi zorunludur.')]
    )
    
    kat_id = SelectField(
        'Kat',
        coerce=int,
        choices=[],
        validators=[DataRequired(message='Kat seçimi zorunludur.')]
    )

    oda_no = StringField(
        'Oda Numarası',
        validators=[
            DataRequired(message='Oda numarası zorunludur.'),
            Length(min=1, max=20, message='Oda numarası 1-20 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-Z0-9\-]+$', 'Oda numarası sadece harf, rakam ve tire içerebilir.')
        ]
    )

    oda_tipi_id = SelectField(
        'Oda Tipi',
        coerce=int,
        choices=[],
        validators=[
            Optional()
        ]
    )

    kapasite = IntegerField(
        'Kapasite',
        validators=[
            Optional(),
            NumberRange(min=1, max=20, message='Kapasite 1-20 arasında olmalıdır.')
        ]
    )
    
    aktif = BooleanField('Aktif', default=True)

class UrunGrupForm(BaseForm):
    """Ürün grubu tanımlama/düzenleme formu"""
    grup_adi = StringField(
        'Grup Adı',
        validators=[
            DataRequired(message='Grup adı zorunludur.'),
            Length(min=2, max=100, message='Grup adı 2-100 karakter arasında olmalıdır.')
        ]
    )

    aciklama = TextAreaField(
        'Açıklama',
        validators=[
            Optional(),
            Length(max=500, message='Açıklama 500 karakterden uzun olamaz.')
        ]
    )

class ZimmetForm(BaseForm):
    """Personel zimmet formu"""
    personel_id = SelectField(
        'Personel',
        coerce=int,
        choices=[],
        validators=[DataRequired(message='Personel seçimi zorunludur.')]
    )

    aciklama = TextAreaField(
        'Açıklama',
        validators=[
            Optional(),
            Length(max=500, message='Açıklama 500 karakterden uzun olamaz.')
        ]
    )

class StokGirisForm(BaseForm):
    """Stok giriş formu"""
    urun_id = SelectField(
        'Ürün',
        coerce=int,
        choices=[],
        validators=[DataRequired(message='Ürün seçimi zorunludur.')]
    )
    
    miktar = IntegerField(
        'Miktar',
        validators=[
            DataRequired(message='Miktar zorunludur.'),
            NumberRange(min=1, max=1000000, message='Miktar 1-1000000 arasında olmalıdır.')
        ]
    )
    
    aciklama = TextAreaField(
        'Açıklama',
        validators=[
            Optional(),
            Length(max=500, message='Açıklama 500 karakterden uzun olamaz.')
        ]
    )


class DepoSorumlusuForm(BaseForm):
    """Depo sorumlusu tanımlama formu (çoklu otel)"""
    kullanici_adi = StringField(
        'Kullanıcı Adı',
        validators=[
            DataRequired(message='Kullanıcı adı zorunludur.'),
            Length(min=3, max=50, message='Kullanıcı adı 3-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-Z0-9_.-]+$', 'Kullanıcı adı sadece harf, rakam ve (_-.) karakterleri içerebilir.')
        ]
    )

    ad = StringField(
        'Ad',
        validators=[
            DataRequired(message='Ad zorunludur.'),
            Length(min=2, max=50, message='Ad 2-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-ZğüşöçıİĞÜŞÖÇı\s]+$', 'Ad sadece harf içerebilir.')
        ]
    )

    soyad = StringField(
        'Soyad',
        validators=[
            DataRequired(message='Soyad zorunludur.'),
            Length(min=2, max=50, message='Soyad 2-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-ZğüşöçıİĞÜŞÖÇı\s]+$', 'Soyad sadece harf içerebilir.')
        ]
    )

    email = StringField(
        'E-posta',
        validators=[
            Optional(),
            Email(message='Geçerli bir e-posta adresi giriniz.'),
            Length(max=100, message='E-posta adresi 100 karakterden uzun olamaz.')
        ]
    )

    telefon = StringField(
        'Telefon',
        validators=[
            Optional(),
            Length(max=20, message='Telefon numarası 20 karakterden uzun olamaz.'),
            pattern_validator(r'^[\d\s\-\+\(\)\.]+$', 'Geçerli bir telefon numarası giriniz.')
        ]
    )
    
    otel_ids = SelectMultipleField(
        'Oteller',
        coerce=int,
        choices=[],
        validators=[DataRequired(message='En az bir otel seçimi zorunludur.')]
    )

    sifre = PasswordField(
        'Şifre',
        validators=[
            DataRequired(message='Şifre zorunludur.'),
            Length(min=8, max=128, message='Şifre en az 8 karakter olmalıdır.'),
            password_strength_validator('Şifre en az bir büyük harf, bir küçük harf, bir rakam ve bir özel karakter içermelidir.')
        ]
    )
    
    aktif = BooleanField('Aktif', default=True)


class DepoSorumlusuDuzenleForm(BaseForm):
    """Depo sorumlusu düzenleme formu (çoklu otel, şifre opsiyonel)"""
    kullanici_adi = StringField(
        'Kullanıcı Adı',
        validators=[
            DataRequired(message='Kullanıcı adı zorunludur.'),
            Length(min=3, max=50, message='Kullanıcı adı 3-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-Z0-9_.-]+$', 'Kullanıcı adı sadece harf, rakam ve (_-.) karakterleri içerebilir.')
        ]
    )

    ad = StringField(
        'Ad',
        validators=[
            DataRequired(message='Ad zorunludur.'),
            Length(min=2, max=50, message='Ad 2-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-ZğüşöçıİĞÜŞÖÇı\s]+$', 'Ad sadece harf içerebilir.')
        ]
    )

    soyad = StringField(
        'Soyad',
        validators=[
            DataRequired(message='Soyad zorunludur.'),
            Length(min=2, max=50, message='Soyad 2-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-ZğüşöçıİĞÜŞÖÇı\s]+$', 'Soyad sadece harf içerebilir.')
        ]
    )

    email = StringField(
        'E-posta',
        validators=[
            Optional(),
            Email(message='Geçerli bir e-posta adresi giriniz.'),
            Length(max=100, message='E-posta adresi 100 karakterden uzun olamaz.')
        ]
    )

    telefon = StringField(
        'Telefon',
        validators=[
            Optional(),
            Length(max=20, message='Telefon numarası 20 karakterden uzun olamaz.'),
            pattern_validator(r'^[\d\s\-\+\(\)\.]+$', 'Geçerli bir telefon numarası giriniz.')
        ]
    )
    
    otel_ids = SelectMultipleField(
        'Oteller',
        coerce=int,
        choices=[],
        validators=[DataRequired(message='En az bir otel seçimi zorunludur.')]
    )

    yeni_sifre = PasswordField(
        'Yeni Şifre',
        validators=[
            Optional(),
            Length(min=8, max=128, message='Şifre en az 8 karakter olmalıdır.'),
            password_strength_validator('Şifre en az bir büyük harf, bir küçük harf, bir rakam ve bir özel karakter içermelidir.')
        ]
    )
    
    aktif = BooleanField('Aktif', default=True)


class KatSorumlusuForm(BaseForm):
    """Kat sorumlusu tanımlama formu (tekli otel)"""
    kullanici_adi = StringField(
        'Kullanıcı Adı',
        validators=[
            DataRequired(message='Kullanıcı adı zorunludur.'),
            Length(min=3, max=50, message='Kullanıcı adı 3-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-Z0-9_.-]+$', 'Kullanıcı adı sadece harf, rakam ve (_-.) karakterleri içerebilir.')
        ]
    )

    ad = StringField(
        'Ad',
        validators=[
            DataRequired(message='Ad zorunludur.'),
            Length(min=2, max=50, message='Ad 2-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-ZğüşöçıİĞÜŞÖÇı\s]+$', 'Ad sadece harf içerebilir.')
        ]
    )

    soyad = StringField(
        'Soyad',
        validators=[
            DataRequired(message='Soyad zorunludur.'),
            Length(min=2, max=50, message='Soyad 2-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-ZğüşöçıİĞÜŞÖÇı\s]+$', 'Soyad sadece harf içerebilir.')
        ]
    )

    email = StringField(
        'E-posta',
        validators=[
            Optional(),
            Email(message='Geçerli bir e-posta adresi giriniz.'),
            Length(max=100, message='E-posta adresi 100 karakterden uzun olamaz.')
        ]
    )

    telefon = StringField(
        'Telefon',
        validators=[
            Optional(),
            Length(max=20, message='Telefon numarası 20 karakterden uzun olamaz.'),
            pattern_validator(r'^[\d\s\-\+\(\)\.]+$', 'Geçerli bir telefon numarası giriniz.')
        ]
    )
    
    otel_id = SelectField(
        'Otel',
        coerce=int,
        choices=[],
        validators=[DataRequired(message='Otel seçimi zorunludur.')]
    )
    
    depo_sorumlusu_id = SelectField(
        'Bağlı Depo Sorumlusu',
        coerce=int,
        choices=[],
        validators=[Optional()]
    )

    sifre = PasswordField(
        'Şifre',
        validators=[
            DataRequired(message='Şifre zorunludur.'),
            Length(min=8, max=128, message='Şifre en az 8 karakter olmalıdır.'),
            password_strength_validator('Şifre en az bir büyük harf, bir küçük harf, bir rakam ve bir özel karakter içermelidir.')
        ]
    )
    
    aktif = BooleanField('Aktif', default=True)


class KatSorumlusuDuzenleForm(BaseForm):
    """Kat sorumlusu düzenleme formu (tekli otel, şifre opsiyonel)"""
    kullanici_adi = StringField(
        'Kullanıcı Adı',
        validators=[
            DataRequired(message='Kullanıcı adı zorunludur.'),
            Length(min=3, max=50, message='Kullanıcı adı 3-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-Z0-9_.-]+$', 'Kullanıcı adı sadece harf, rakam ve (_-.) karakterleri içerebilir.')
        ]
    )

    ad = StringField(
        'Ad',
        validators=[
            DataRequired(message='Ad zorunludur.'),
            Length(min=2, max=50, message='Ad 2-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-ZğüşöçıİĞÜŞÖÇı\s]+$', 'Ad sadece harf içerebilir.')
        ]
    )

    soyad = StringField(
        'Soyad',
        validators=[
            DataRequired(message='Soyad zorunludur.'),
            Length(min=2, max=50, message='Soyad 2-50 karakter arasında olmalıdır.'),
            pattern_validator(r'^[a-zA-ZğüşöçıİĞÜŞÖÇı\s]+$', 'Soyad sadece harf içerebilir.')
        ]
    )

    email = StringField(
        'E-posta',
        validators=[
            Optional(),
            Email(message='Geçerli bir e-posta adresi giriniz.'),
            Length(max=100, message='E-posta adresi 100 karakterden uzun olamaz.')
        ]
    )

    telefon = StringField(
        'Telefon',
        validators=[
            Optional(),
            Length(max=20, message='Telefon numarası 20 karakterden uzun olamaz.'),
            pattern_validator(r'^[\d\s\-\+\(\)\.]+$', 'Geçerli bir telefon numarası giriniz.')
        ]
    )
    
    otel_id = SelectField(
        'Otel',
        coerce=int,
        choices=[],
        validators=[DataRequired(message='Otel seçimi zorunludur.')]
    )
    
    depo_sorumlusu_id = SelectField(
        'Bağlı Depo Sorumlusu',
        coerce=int,
        choices=[],
        validators=[Optional()]
    )

    yeni_sifre = PasswordField(
        'Yeni Şifre',
        validators=[
            Optional(),
            Length(min=8, max=128, message='Şifre en az 8 karakter olmalıdır.'),
            password_strength_validator('Şifre en az bir büyük harf, bir küçük harf, bir rakam ve bir özel karakter içermelidir.')
        ]
    )
    
    aktif = BooleanField('Aktif', default=True)


# ============================================================================
# TEDARİKÇİ VE SATIN ALMA MODÜLÜ FORMLARI
# ============================================================================

class TedarikciForm(BaseForm):
    """
    Tedarikçi tanımlama ve düzenleme formu
    Gereksinimler: 1.1, 1.2, 1.3
    """
    tedarikci_adi = StringField(
        'Tedarikçi Adı',
        validators=[
            DataRequired(message='Tedarikçi adı zorunludur.'),
            Length(min=2, max=200, message='Tedarikçi adı 2-200 karakter arasında olmalıdır.')
        ]
    )
    
    telefon = StringField(
        'Telefon',
        validators=[
            Optional(),
            Length(min=10, max=20, message='Telefon numarası 10-20 karakter arasında olmalıdır.'),
            pattern_validator(r'^[\d\s\-\+\(\)\.]+$', 'Geçerli bir telefon numarası giriniz.')
        ]
    )
    
    email = StringField(
        'E-posta',
        validators=[
            Optional(),
            Email(message='Geçerli bir e-posta adresi giriniz.'),
            Length(max=100, message='E-posta adresi 100 karakterden uzun olamaz.')
        ]
    )
    
    adres = TextAreaField(
        'Adres',
        validators=[
            Optional(),
            Length(max=500, message='Adres 500 karakterden uzun olamaz.')
        ]
    )
    
    vergi_no = StringField(
        'Vergi Numarası',
        validators=[
            Optional(),
            Length(max=50, message='Vergi numarası 50 karakterden uzun olamaz.')
        ]
    )
    
    odeme_kosullari = TextAreaField(
        'Ödeme Koşulları',
        validators=[
            Optional(),
            Length(max=500, message='Ödeme koşulları 500 karakterden uzun olamaz.')
        ]
    )
    
    aktif = BooleanField('Aktif', default=True)


class UrunTedarikciFiyatForm(BaseForm):
    """
    Ürün-tedarikçi fiyat tanımlama formu
    Gereksinimler: 2.1, 2.2, 2.3
    """
    urun_id = SelectField(
        'Ürün',
        coerce=int,
        choices=[],
        validators=[DataRequired(message='Ürün seçimi zorunludur.')]
    )
    
    tedarikci_id = SelectField(
        'Tedarikçi',
        coerce=int,
        choices=[],
        validators=[DataRequired(message='Tedarikçi seçimi zorunludur.')]
    )
    
    alis_fiyati = DecimalField(
        'Alış Fiyatı',
        places=2,
        validators=[
            DataRequired(message='Alış fiyatı zorunludur.'),
            NumberRange(min=0, message='Alış fiyatı 0\'dan büyük olmalıdır.')
        ]
    )
    
    minimum_miktar = IntegerField(
        'Minimum Sipariş Miktarı',
        validators=[
            DataRequired(message='Minimum sipariş miktarı zorunludur.'),
            NumberRange(min=1, message='Minimum sipariş miktarı en az 1 olmalıdır.')
        ]
    )
    
    baslangic_tarihi = DateField(
        'Başlangıç Tarihi',
        format='%Y-%m-%d',
        validators=[DataRequired(message='Başlangıç tarihi zorunludur.')]
    )
    
    bitis_tarihi = DateField(
        'Bitiş Tarihi',
        format='%Y-%m-%d',
        validators=[Optional()]
    )
    
    aktif = BooleanField('Aktif', default=True)
    
    def validate_bitis_tarihi(self, field):
        """Bitiş tarihinin başlangıç tarihinden sonra olduğunu kontrol et"""
        if field.data and self.baslangic_tarihi.data:
            if field.data < self.baslangic_tarihi.data:
                raise ValidationError('Bitiş tarihi başlangıç tarihinden önce olamaz.')


class TedarikciIletisimForm(BaseForm):
    """
    Tedarikçi iletişim kaydı formu
    Gereksinimler: 10.1, 10.2
    """
    siparis_id = SelectField(
        'İlgili Sipariş',
        coerce=int,
        choices=[],
        validators=[Optional()]
    )
    
    konu = StringField(
        'Konu',
        validators=[
            DataRequired(message='Konu zorunludur.'),
            Length(min=2, max=200, message='Konu 2-200 karakter arasında olmalıdır.')
        ]
    )
    
    aciklama = TextAreaField(
        'Açıklama',
        validators=[
            DataRequired(message='Açıklama zorunludur.'),
            Length(min=5, max=1000, message='Açıklama 5-1000 karakter arasında olmalıdır.')
        ]
    )
    
    iletisim_tarihi = DateTimeField(
        'İletişim Tarihi',
        format='%Y-%m-%d %H:%M',
        validators=[DataRequired(message='İletişim tarihi zorunludur.')]
    )


class SatinAlmaSiparisForm(BaseForm):
    """
    Satın alma siparişi oluşturma formu
    Gereksinimler: 3.1, 3.2, 3.3
    """
    tedarikci_id = SelectField(
        'Tedarikçi',
        coerce=int,
        choices=[],
        validators=[DataRequired(message='Tedarikçi seçimi zorunludur.')]
    )
    
    tahmini_teslimat_tarihi = DateField(
        'Tahmini Teslimat Tarihi',
        format='%Y-%m-%d',
        validators=[DataRequired(message='Tahmini teslimat tarihi zorunludur.')]
    )
    
    aciklama = TextAreaField(
        'Açıklama',
        validators=[
            Optional(),
            Length(max=1000, message='Açıklama 1000 karakterden uzun olamaz.')
        ]
    )
    
    def validate_tahmini_teslimat_tarihi(self, field):
        """Teslimat tarihinin bugünden önce olmadığını kontrol et"""
        from datetime import date
        if field.data and field.data < date.today():
            raise ValidationError('Tahmini teslimat tarihi bugünden önce olamaz.')


class SiparisStokGirisForm(BaseForm):
    """
    Sipariş teslimatından stok giriş formu
    Gereksinimler: 5.1, 5.2, 5.3
    """
    gerceklesen_teslimat_tarihi = DateField(
        'Gerçekleşen Teslimat Tarihi',
        format='%Y-%m-%d',
        validators=[DataRequired(message='Teslimat tarihi zorunludur.')]
    )
    
    aciklama = TextAreaField(
        'Açıklama',
        validators=[
            Optional(),
            Length(max=500, message='Açıklama 500 karakterden uzun olamaz.')
        ]
    )
    
    def validate_gerceklesen_teslimat_tarihi(self, field):
        """Teslimat tarihinin gelecekte olmadığını kontrol et"""
        from datetime import date
        if field.data and field.data > date.today():
            raise ValidationError('Teslimat tarihi gelecekte olamaz.')


class TedarikciDokumanForm(BaseForm):
    """
    Tedarikçi belge yükleme formu
    Gereksinimler: 10.3, 10.4
    """
    siparis_id = SelectField(
        'İlgili Sipariş',
        coerce=int,
        choices=[],
        validators=[Optional()]
    )
    
    dokuman_tipi = SelectField(
        'Belge Tipi',
        choices=[
            ('fatura', 'Fatura'),
            ('irsaliye', 'İrsaliye'),
            ('sozlesme', 'Sözleşme'),
            ('diger', 'Diğer')
        ],
        validators=[DataRequired(message='Belge tipi seçimi zorunludur.')]
    )
    
    dosya = FileField(
        'Belge Dosyası',
        validators=[
            DataRequired(message='Dosya seçimi zorunludur.'),
            FileAllowed(['pdf', 'xlsx', 'xls', 'jpg', 'jpeg', 'png'], 
                       'Sadece PDF, Excel ve resim dosyaları yüklenebilir.')
        ]
    )
    
    aciklama = TextAreaField(
        'Açıklama',
        validators=[
            Optional(),
            Length(max=500, message='Açıklama 500 karakterden uzun olamaz.')
        ]
    )


class TopluSiparisForm(BaseForm):
    """
    Excel ile toplu sipariş yükleme formu
    Gereksinimler: 9.1, 9.2, 9.3
    """
    excel_dosyasi = FileField(
        'Excel Dosyası',
        validators=[
            DataRequired(message='Excel dosyası seçimi zorunludur.'),
            FileAllowed(['xlsx', 'xls', 'xlsm'], 'Sadece Excel dosyaları yüklenebilir.')
        ]
    )
    
    tedarikci_id = SelectField(
        'Varsayılan Tedarikçi',
        coerce=int,
        choices=[],
        validators=[Optional()]
    )
    
    tahmini_teslimat_tarihi = DateField(
        'Varsayılan Teslimat Tarihi',
        format='%Y-%m-%d',
        validators=[Optional()]
    )
