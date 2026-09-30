from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from config import Config

db = SQLAlchemy()

class Machine(db.Model):
    __tablename__ = 'machines'
    
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    factory = db.Column(db.String(100))
    status = db.Column(db.String(20), default='Normal')
    health_score = db.Column(db.Integer, default=100)
    last_reading = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Normal operating ranges
    temp_normal = db.Column(db.Float, default=Config.DEFAULT_TEMP_NORMAL)
    vib_normal = db.Column(db.Float, default=Config.DEFAULT_VIB_NORMAL)
    rpm_normal = db.Column(db.Integer, default=Config.DEFAULT_RPM_NORMAL)
    current_normal = db.Column(db.Float, default=Config.DEFAULT_CURRENT_NORMAL)
    
    # Relationships
    readings = db.relationship('SensorReading', backref='machine', lazy=True)
    alerts = db.relationship('Alert', backref='machine', lazy=True)
    
    @classmethod
    def get_or_create(cls, machine_id, **kwargs):
        """Get machine by ID or create new one"""
        machine = cls.query.filter_by(machine_id=machine_id).first()
        if not machine:
            machine = cls(
                machine_id=machine_id,
                name=kwargs.get('name', f'Machine {machine_id}'),
                factory=kwargs.get('factory', 'Faisalabad Textile Unit'),
                temp_normal=kwargs.get('temp_normal', Config.DEFAULT_TEMP_NORMAL),
                vib_normal=kwargs.get('vib_normal', Config.DEFAULT_VIB_NORMAL),
                rpm_normal=kwargs.get('rpm_normal', Config.DEFAULT_RPM_NORMAL),
                current_normal=kwargs.get('current_normal', Config.DEFAULT_CURRENT_NORMAL)
            )
            db.session.add(machine)
            db.session.commit()
        return machine
    
    def __repr__(self):
        return f'<Machine {self.machine_id}: {self.name}>'

class SensorReading(db.Model):
    __tablename__ = 'sensor_readings'
    
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.String(20), db.ForeignKey('machines.machine_id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    temperature = db.Column(db.Float)
    vibration = db.Column(db.Float)
    rpm = db.Column(db.Integer)
    current = db.Column(db.Float)
    
    def to_dict(self):
        return {
            'time': self.timestamp.isoformat(),
            'temp': self.temperature,
            'vibration': self.vibration,
            'rpm': self.rpm,
            'current': self.current
        }

class Alert(db.Model):
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.String(20), db.ForeignKey('machines.machine_id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    level = db.Column(db.String(20))  # Info, Warning, Critical
    issue = db.Column(db.String(200))
    action = db.Column(db.String(200))
    resolved = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'machine': self.machine_id,
            'time': self.timestamp.strftime('%Y-%m-%d %H:%M'),
            'level': self.level,
            'issue': self.issue,
            'action': self.action,
            'resolved': self.resolved
        }