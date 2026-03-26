"""
Deep Feature Learning - Autoencoder ile feature öğrenme
Yüksek boyutlu feature'ları düşük boyutlu latent space'e çevirir
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)


class DeepFeatureLearner:
    """
    Autoencoder ile deep feature learning
    
    Not: TensorFlow/Keras gerektirir
    pip install tensorflow
    """
    
    def __init__(self, encoding_dim=10):
        self.encoding_dim = encoding_dim
        self.autoencoder = None
        self.encoder = None
        self.has_keras = False
        
        try:
            from tensorflow import keras  # type: ignore[import]
            from tensorflow.keras import layers  # type: ignore[import]

            self.keras = keras
            self.layers = layers
            self.has_keras = True
        except ImportError:
            logger.warning("⚠️  TensorFlow/Keras bulunamadı. Deep feature learning devre dışı.")
    
    def build_autoencoder(self, input_dim):
        """
        Autoencoder modeli oluştur
        Args:
            input_dim: Input feature sayısı
        """
        if not self.has_keras:
            logger.error("TensorFlow/Keras yüklü değil!")
            return None
        
        try:
            # Encoder
            input_layer = self.keras.Input(shape=(input_dim,))
            
            # Encoding layers
            encoded = self.layers.Dense(64, activation='relu')(input_layer)
            encoded = self.layers.Dense(32, activation='relu')(encoded)
            encoded = self.layers.Dense(self.encoding_dim, activation='relu')(encoded)
            
            # Decoder
            decoded = self.layers.Dense(32, activation='relu')(encoded)
            decoded = self.layers.Dense(64, activation='relu')(decoded)
            decoded = self.layers.Dense(input_dim, activation='linear')(decoded)
            
            # Autoencoder model
            self.autoencoder = self.keras.Model(input_layer, decoded)
            self.autoencoder.compile(optimizer='adam', loss='mse')
            
            # Encoder model (sadece encoding kısmı)
            self.encoder = self.keras.Model(input_layer, encoded)
            
            logger.info(f"✅ Autoencoder oluşturuldu: {input_dim} → {self.encoding_dim}")
            
            return self.autoencoder
            
        except Exception as e:
            logger.error(f"Autoencoder oluşturma hatası: {str(e)}")
            return None
    
    def train(self, X, epochs=50, batch_size=32, validation_split=0.2):
        """
        Autoencoder'ı eğit
        Args:
            X: Training data
            epochs: Epoch sayısı
            batch_size: Batch size
            validation_split: Validation oranı
        """
        if not self.has_keras or self.autoencoder is None:
            logger.error("Autoencoder hazır değil!")
            return None
        
        try:
            logger.info("🎓 Autoencoder eğitimi başladı...")
            
            history = self.autoencoder.fit(
                X, X,  # Autoencoder kendini yeniden oluşturmayı öğrenir
                epochs=epochs,
                batch_size=batch_size,
                validation_split=validation_split,
                verbose=0
            )
            
            final_loss = history.history['loss'][-1]
            final_val_loss = history.history['val_loss'][-1]

            logger.info("✅ Autoencoder eğitildi")
            logger.info(f"   - Final loss: {final_loss:.4f}")
            logger.info(f"   - Final val_loss: {final_val_loss:.4f}")
            
            return history
            
        except Exception as e:
            logger.error(f"Autoencoder eğitim hatası: {str(e)}")
            return None
    
    def encode(self, X):
        """
        Feature'ları encode et (latent space'e çevir)
        Args:
            X: Input features
        Returns: Encoded features
        """
        if not self.has_keras or self.encoder is None:
            logger.error("Encoder hazır değil!")
            return X
        
        try:
            X_encoded = self.encoder.predict(X, verbose=0)
            
            logger.info(f"✅ Features encoded: {X.shape[1]} → {X_encoded.shape[1]}")
            
            return X_encoded
            
        except Exception as e:
            logger.error(f"Encoding hatası: {str(e)}")
            return X
    
    def decode(self, X_encoded):
        """
        Encoded feature'ları decode et (orijinal space'e geri çevir)
        """
        if not self.has_keras or self.autoencoder is None:
            logger.error("Autoencoder hazır değil!")
            return X_encoded
        
        try:
            X_decoded = self.autoencoder.predict(X_encoded, verbose=0)
            return X_decoded
        except Exception as e:
            logger.error(f"Decoding hatası: {str(e)}")
            return X_encoded
    
    def get_reconstruction_error(self, X):
        """
        Reconstruction error hesapla (anomali tespiti için kullanılabilir)
        Yüksek error = anomali
        """
        if not self.has_keras or self.autoencoder is None:
            logger.error("Autoencoder hazır değil!")
            return None
        
        try:
            X_reconstructed = self.autoencoder.predict(X, verbose=0)
            mse = np.mean(np.square(X - X_reconstructed), axis=1)
            
            return mse
            
        except Exception as e:
            logger.error(f"Reconstruction error hatası: {str(e)}")
            return None
    
    def save_model(self, filepath):
        """Modeli kaydet"""
        if not self.has_keras or self.autoencoder is None:
            logger.error("Autoencoder hazır değil!")
            return False
        
        try:
            self.autoencoder.save(filepath)
            logger.info(f"✅ Autoencoder kaydedildi: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Model kaydetme hatası: {str(e)}")
            return False
    
    def load_model(self, filepath):
        """Modeli yükle"""
        if not self.has_keras:
            logger.error("TensorFlow/Keras yüklü değil!")
            return False
        
        try:
            self.autoencoder = self.keras.models.load_model(filepath)
            
            # Encoder'ı yeniden oluştur
            input_layer = self.autoencoder.input
            encoded_layer = self.autoencoder.layers[2].output  # Encoding layer
            self.encoder = self.keras.Model(input_layer, encoded_layer)
            
            logger.info(f"✅ Autoencoder yüklendi: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Model yükleme hatası: {str(e)}")
            return False


# Kullanım örneği
def learn_deep_features(X, encoding_dim=10, epochs=50):
    """
    Deep feature learning uygula
    Args:
        X: Feature matrix
        encoding_dim: Latent space boyutu
        epochs: Eğitim epoch sayısı
    Returns: Encoded features
    """
    try:
        learner = DeepFeatureLearner(encoding_dim=encoding_dim)
        
        if not learner.has_keras:
            logger.warning("⚠️  TensorFlow yok, deep learning atlanıyor")
            return X
        
        # Autoencoder oluştur ve eğit
        learner.build_autoencoder(X.shape[1])
        learner.train(X, epochs=epochs)
        
        # Encode et
        X_encoded = learner.encode(X)
        
        logger.info(f"✅ Deep feature learning tamamlandı: {X.shape[1]} → {X_encoded.shape[1]}")
        
        return X_encoded
        
    except Exception as e:
        logger.error(f"Deep feature learning hatası: {str(e)}")
        return X


# Anomali tespiti için reconstruction error kullanımı
def detect_anomalies_with_autoencoder(X, threshold_percentile=95):
    """
    Autoencoder reconstruction error ile anomali tespiti
    Args:
        X: Feature matrix
        threshold_percentile: Error percentile eşiği
    Returns: Anomali indeksleri
    """
    try:
        learner = DeepFeatureLearner(encoding_dim=10)
        
        if not learner.has_keras:
            logger.warning("⚠️  TensorFlow yok, anomali tespiti atlanıyor")
            return []
        
        # Eğit
        learner.build_autoencoder(X.shape[1])
        learner.train(X, epochs=50)
        
        # Reconstruction error
        errors = learner.get_reconstruction_error(X)
        
        # Threshold
        threshold = np.percentile(errors, threshold_percentile)  # type: ignore[arg-type]
        anomaly_indices = np.where(errors > threshold)[0]
        
        logger.info(f"✅ {len(anomaly_indices)} anomali tespit edildi (threshold: {threshold:.4f})")
        
        return anomaly_indices
        
    except Exception as e:
        logger.error(f"Anomali tespiti hatası: {str(e)}")
        return []
