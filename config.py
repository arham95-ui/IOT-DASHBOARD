import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-12345'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///iot_dashboard.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ===== ALERT THRESHOLDS =====
    TEMP_MAX = 50.0           # °C - Critical
    TEMP_WARNING = 45.0       # °C - Warning
    VIBRATION_MAX = 3.0       # mm/s - Critical
    VIBRATION_WARNING = 2.5   # mm/s - Warning
    RPM_MIN = 1400
    RPM_MAX = 1600
    CURRENT_MAX = 6.0         # Amps - Critical
    CURRENT_WARNING = 5.5     # Amps - Warning
    
    # ===== HEALTH SCORE WEIGHTS =====
    WEIGHT_TEMP = 0.3
    WEIGHT_VIB = 0.3
    WEIGHT_RPM = 0.2
    WEIGHT_CURRENT = 0.2
    
    # ===== MACHINE DEFAULTS =====
    DEFAULT_TEMP_NORMAL = 42.0
    DEFAULT_VIB_NORMAL = 2.0
    DEFAULT_RPM_NORMAL = 1480
    DEFAULT_CURRENT_NORMAL = 5.0