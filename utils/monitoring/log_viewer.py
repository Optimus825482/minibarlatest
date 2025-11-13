"""
Log Viewer Service
Real-time log görüntüleme ve filtreleme servisi
"""
import logging
import os
import re
from datetime import datetime
from typing import List, Dict, Optional, Generator
from collections import Counter

logger = logging.getLogger(__name__)


class LogViewer:
    """Log dosyalarını okuma ve filtreleme servisi"""
    
    def __init__(self, log_file_path: str = None):
        """
        LogViewer servisini başlat
        
        Args:
            log_file_path: Log dosya yolu (default: app.log)
        """
        self.log_file_path = log_file_path or 'app.log'
        logger.info(f"LogViewer başlatıldı: {self.log_file_path}")
    
    def tail_logs(self, lines: int = 100) -> List[Dict]:
        """
        Son N satır log'u getir
        
        Args:
            lines: Kaç satır
            
        Returns:
            List[Dict]: Log satırları
        """
        try:
            if not os.path.exists(self.log_file_path):
                logger.warning(f"Log dosyası bulunamadı: {self.log_file_path}")
                return []
            
            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            parsed_logs = []
            for line in last_lines:
                parsed = self._parse_log_line(line)
                if parsed:
                    parsed_logs.append(parsed)
            
            logger.info(f"{len(parsed_logs)} log satırı alındı")
            return parsed_logs
            
        except Exception as e:
            logger.error(f"Log tail hatası: {str(e)}", exc_info=True)
            return []
    
    def filter_logs(self, level: Optional[str] = None, search: Optional[str] = None, 
                   lines: int = 100) -> List[Dict]:
        """
        Filtrelenmiş log'ları getir
        
        Args:
            level: Log seviyesi (ERROR, WARNING, INFO, DEBUG)
            search: Arama terimi
            lines: Maksimum satır sayısı
            
        Returns:
            List[Dict]: Filtrelenmiş log'lar
        """
        try:
            all_logs = self.tail_logs(lines=lines * 2)  # Daha fazla al, filtrele
            
            filtered = all_logs
            
            # Level filtresi
            if level:
                level = level.upper()
                filtered = [log for log in filtered if log.get('level') == level]
            
            # Search filtresi
            if search:
                search_lower = search.lower()
                filtered = [
                    log for log in filtered 
                    if search_lower in log.get('message', '').lower()
                ]
            
            # Limit uygula
            filtered = filtered[-lines:]
            
            logger.info(f"{len(filtered)} filtrelenmiş log bulundu")
            return filtered
            
        except Exception as e:
            logger.error(f"Log filtreleme hatası: {str(e)}", exc_info=True)
            return []
    
    def get_log_stats(self, lines: int = 1000) -> Dict:
        """
        Log istatistikleri
        
        Args:
            lines: Analiz edilecek satır sayısı
            
        Returns:
            Dict: İstatistikler
        """
        try:
            logs = self.tail_logs(lines=lines)
            
            if not logs:
                return {
                    "total_lines": 0,
                    "by_level": {},
                    "error_count": 0,
                    "warning_count": 0
                }
            
            levels = [log.get('level', 'UNKNOWN') for log in logs]
            level_counts = Counter(levels)
            
            stats = {
                "total_lines": len(logs),
                "by_level": dict(level_counts),
                "error_count": level_counts.get('ERROR', 0),
                "warning_count": level_counts.get('WARNING', 0),
                "info_count": level_counts.get('INFO', 0),
                "debug_count": level_counts.get('DEBUG', 0),
                "analyzed_lines": lines,
                "last_updated": datetime.now().isoformat()
            }
            
            logger.info(f"Log istatistikleri oluşturuldu: {len(logs)} satır")
            return stats
            
        except Exception as e:
            logger.error(f"Log stats hatası: {str(e)}", exc_info=True)
            return {}
    
    def get_recent_errors(self, count: int = 50) -> List[Dict]:
        """
        Son hataları getir
        
        Args:
            count: Kaç hata
            
        Returns:
            List[Dict]: Hata log'ları
        """
        try:
            # ERROR ve CRITICAL seviyeli log'ları al
            all_logs = self.tail_logs(lines=count * 5)  # Daha fazla al
            errors = [
                log for log in all_logs 
                if log.get('level') in ['ERROR', 'CRITICAL']
            ]
            
            # Son N hata
            errors = errors[-count:]
            
            logger.info(f"{len(errors)} hata log'u bulundu")
            return errors
            
        except Exception as e:
            logger.error(f"Recent errors hatası: {str(e)}", exc_info=True)
            return []
    
    def search_logs(self, pattern: str, lines: int = 1000, 
                   case_sensitive: bool = False) -> List[Dict]:
        """
        Log'larda regex arama
        
        Args:
            pattern: Arama pattern'i
            lines: Aranacak satır sayısı
            case_sensitive: Case sensitive arama
            
        Returns:
            List[Dict]: Eşleşen log'lar
        """
        try:
            all_logs = self.tail_logs(lines=lines)
            
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)
            
            matches = [
                log for log in all_logs
                if regex.search(log.get('message', ''))
            ]
            
            logger.info(f"{len(matches)} eşleşme bulundu: {pattern}")
            return matches
            
        except re.error as e:
            logger.error(f"Regex hatası: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Log search hatası: {str(e)}", exc_info=True)
            return []
    
    def stream_logs(self) -> Generator[Dict, None, None]:
        """
        Real-time log stream (SSE için)
        
        Yields:
            Dict: Log satırı
        """
        try:
            if not os.path.exists(self.log_file_path):
                logger.warning(f"Log dosyası bulunamadı: {self.log_file_path}")
                return
            
            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Dosyanın sonuna git
                f.seek(0, os.SEEK_END)
                
                while True:
                    line = f.readline()
                    if line:
                        parsed = self._parse_log_line(line)
                        if parsed:
                            yield parsed
                    else:
                        # Yeni satır yoksa bekle
                        import time
                        time.sleep(0.5)
                        
        except Exception as e:
            logger.error(f"Log stream hatası: {str(e)}", exc_info=True)
    
    def _parse_log_line(self, line: str) -> Optional[Dict]:
        """
        Log satırını parse et
        
        Args:
            line: Log satırı
            
        Returns:
            Dict: Parse edilmiş log
        """
        try:
            line = line.strip()
            if not line:
                return None
            
            # Python logging format: 2025-11-12 20:34:18,423 - __main__ - INFO - mesaj
            pattern = r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})\s+-\s+([^\s]+)\s+-\s+(\w+)\s+-\s+(.*)'
            match = re.match(pattern, line)
            
            if match:
                timestamp_str, module, level, message = match.groups()
                return {
                    "timestamp": timestamp_str,
                    "level": level.strip(),
                    "module": module.strip(),
                    "message": message.strip(),
                    "raw": line
                }
            else:
                # Parse edilemeyen satırlar için basit format
                return {
                    "timestamp": datetime.now().isoformat(),
                    "level": "UNKNOWN",
                    "module": "unknown",
                    "message": line,
                    "raw": line
                }
                
        except Exception as e:
            logger.error(f"Log parse hatası: {str(e)}")
            return None


# Singleton instance
_log_viewer_instance = None


def get_log_viewer() -> LogViewer:
    """
    LogViewer singleton instance'ını getir
    
    Returns:
        LogViewer: Servis instance
    """
    global _log_viewer_instance
    if _log_viewer_instance is None:
        _log_viewer_instance = LogViewer()
    return _log_viewer_instance
