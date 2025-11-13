"""
Config Editor - System Configuration Management
Developer Dashboard için config dosya yönetim servisi
"""
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from models import db, ConfigAudit

logger = logging.getLogger(__name__)


class ConfigEditor:
    """Config dosya yönetim servisi"""
    
    # Düzenlenebilir config dosyaları (güvenlik için whitelist)
    ALLOWED_CONFIGS = [
        '.env',
        'config.py',
        'logging.conf'
    ]
    
    def __init__(self):
        """Initialize config editor"""
        self.db = db
        self.workspace_root = os.getcwd()
    
    def list_config_files(self) -> List[Dict[str, Any]]:
        """
        Düzenlenebilir config dosyalarını listele
        
        Returns:
            List[Dict]: Config dosya listesi
        """
        try:
            configs = []
            
            for filename in self.ALLOWED_CONFIGS:
                filepath = os.path.join(self.workspace_root, filename)
                
                if os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    modified_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    configs.append({
                        'filename': filename,
                        'filepath': filepath,
                        'file_size': file_size,
                        'modified_at': modified_time.isoformat(),
                        'exists': True
                    })
                else:
                    configs.append({
                        'filename': filename,
                        'filepath': filepath,
                        'exists': False
                    })
            
            return configs
        except Exception as e:
            logger.error(f"List config files hatası: {str(e)}")
            return []
    
    def get_config_content(self, filename: str) -> Optional[str]:
        """
        Config dosya içeriğini getir
        
        Args:
            filename: Dosya adı
            
        Returns:
            str: Dosya içeriği
        """
        try:
            if filename not in self.ALLOWED_CONFIGS:
                logger.warning(f"İzin verilmeyen config dosyası: {filename}")
                return None
            
            filepath = os.path.join(self.workspace_root, filename)
            
            if not os.path.exists(filepath):
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return content
        except Exception as e:
            logger.error(f"Get config content hatası: {str(e)}")
            return None
    
    def validate_config(self, filename: str, content: str) -> Dict[str, Any]:
        """
        Config içeriğini validate et
        
        Args:
            filename: Dosya adı
            content: Dosya içeriği
            
        Returns:
            Dict: Validasyon sonucu
        """
        try:
            errors = []
            warnings = []
            
            # .env dosyası için validasyon
            if filename == '.env':
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if '=' not in line:
                        errors.append({
                            'line': i,
                            'message': 'Geçersiz format. KEY=VALUE formatı kullanın'
                        })
            
            # config.py için validasyon
            elif filename == 'config.py':
                try:
                    compile(content, filename, 'exec')
                except SyntaxError as e:
                    errors.append({
                        'line': e.lineno,
                        'message': f'Syntax hatası: {e.msg}'
                    })
            
            # Genel kontroller
            if len(content) == 0:
                warnings.append({
                    'message': 'Dosya boş'
                })
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings
            }
        except Exception as e:
            logger.error(f"Validate config hatası: {str(e)}")
            return {
                'valid': False,
                'errors': [{'message': str(e)}],
                'warnings': []
            }
    
    def save_config(
        self,
        filename: str,
        content: str,
        changed_by: Optional[int] = None,
        change_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Config dosyasını kaydet
        
        Args:
            filename: Dosya adı
            content: Yeni içerik
            changed_by: Değiştiren kullanıcı ID
            change_reason: Değişiklik sebebi
            
        Returns:
            Dict: Kaydetme sonucu
        """
        try:
            if filename not in self.ALLOWED_CONFIGS:
                return {
                    'success': False,
                    'error': 'İzin verilmeyen config dosyası'
                }
            
            # Validate et
            validation = self.validate_config(filename, content)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': 'Validasyon hatası',
                    'validation': validation
                }
            
            filepath = os.path.join(self.workspace_root, filename)
            
            # Eski içeriği al (audit için)
            old_content = None
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    old_content = f.read()
            
            # Yeni içeriği kaydet
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Audit log kaydet
            audit = ConfigAudit(
                filename=filename,
                old_content=old_content,
                new_content=content,
                changed_by=changed_by,
                change_reason=change_reason
            )
            self.db.session.add(audit)
            self.db.session.commit()
            
            logger.info(f"Config kaydedildi: {filename}")
            
            return {
                'success': True,
                'message': 'Config başarıyla kaydedildi',
                'audit_id': audit.id
            }
        except Exception as e:
            logger.error(f"Save config hatası: {str(e)}")
            self.db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_config_history(self, filename: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Config değişiklik geçmişini getir
        
        Args:
            filename: Dosya adı
            limit: Maksimum kayıt sayısı
            
        Returns:
            List[Dict]: Değişiklik geçmişi
        """
        try:
            audits = ConfigAudit.query.filter_by(
                filename=filename
            ).order_by(
                ConfigAudit.changed_at.desc()
            ).limit(limit).all()
            
            return [
                {
                    'id': audit.id,
                    'filename': audit.filename,
                    'changed_by': audit.changed_by,
                    'changed_at': audit.changed_at.isoformat() if audit.changed_at else None,
                    'change_reason': audit.change_reason,
                    'has_old_content': audit.old_content is not None,
                    'has_new_content': audit.new_content is not None
                }
                for audit in audits
            ]
        except Exception as e:
            logger.error(f"Get config history hatası: {str(e)}")
            return []
    
    def rollback_config(self, filename: str, version: int) -> Dict[str, Any]:
        """
        Config'i önceki versiyona geri al
        
        Args:
            filename: Dosya adı
            version: Audit ID (version)
            
        Returns:
            Dict: Rollback sonucu
        """
        try:
            audit = ConfigAudit.query.get(version)
            if not audit or audit.filename != filename:
                return {
                    'success': False,
                    'error': 'Version bulunamadı'
                }
            
            if not audit.old_content:
                return {
                    'success': False,
                    'error': 'Eski içerik bulunamadı'
                }
            
            # Eski içeriği geri yükle
            result = self.save_config(
                filename=filename,
                content=audit.old_content,
                change_reason=f'Rollback to version {version}'
            )
            
            if result['success']:
                logger.info(f"Config rollback edildi: {filename} -> version {version}")
            
            return result
        except Exception as e:
            logger.error(f"Rollback config hatası: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
