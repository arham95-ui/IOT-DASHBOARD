from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
from sqlalchemy import func, desc
import random

from config import Config
from models import db, Machine, SensorReading, Alert

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)  # Enable CORS for ESP32

db.init_app(app)

# ---------- HELPER FUNCTIONS ----------

def calculate_health_score(machine, reading):
    """Calculate Machine Health Score (0-100)"""
    score = 100
    
    # Temperature deviation
    temp_dev = abs(reading.temperature - machine.temp_normal)
    if temp_dev > 0:
        score -= temp_dev * 2  # 2 points per degree
    
    # Vibration deviation
    vib_dev = abs(reading.vibration - machine.vib_normal)
    if vib_dev > 0:
        score -= vib_dev * 5  # 5 points per mm/s
    
    # RPM deviation
    rpm_dev = abs(reading.rpm - machine.rpm_normal)
    if rpm_dev > 0:
        score -= (rpm_dev / 10) * 2  # 2 points per 10 RPM
    
    # Current deviation
    current_dev = abs(reading.current - machine.current_normal)
    if current_dev > 0:
        score -= current_dev * 3  # 3 points per Amp
    
    return max(0, min(100, int(score)))

def check_alerts(machine, reading):
    """Check and create alerts based on readings"""
    alerts = []
    
    # Temperature alerts
    if reading.temperature > Config.TEMP_MAX:
        alerts.append({
            'level': 'Critical',
            'issue': f'🔥 High Temperature: {reading.temperature}°C (Threshold: {Config.TEMP_MAX}°C)',
            'action': 'Immediately inspect cooling system and reduce load'
        })
    elif reading.temperature > Config.TEMP_WARNING:
        alerts.append({
            'level': 'Warning',
            'issue': f'🌡️ Temperature Rising: {reading.temperature}°C (Normal: {machine.temp_normal}°C)',
            'action': 'Check cooling system and ambient temperature'
        })
    
    # Vibration alerts
    if reading.vibration > Config.VIBRATION_MAX:
        alerts.append({
            'level': 'Critical',
            'issue': f'📳 High Vibration: {reading.vibration} mm/s (Threshold: {Config.VIBRATION_MAX} mm/s)',
            'action': 'Immediately inspect bearings and alignment'
        })
    elif reading.vibration > Config.VIBRATION_WARNING:
        alerts.append({
            'level': 'Warning',
            'issue': f'📳 Vibration Increasing: {reading.vibration} mm/s (Normal: {machine.vib_normal} mm/s)',
            'action': 'Schedule bearing inspection and balancing check'
        })
    
    # RPM alerts
    if reading.rpm < Config.RPM_MIN:
        alerts.append({
            'level': 'Warning',
            'issue': f'🔄 Low RPM: {reading.rpm} RPM (Min: {Config.RPM_MIN} RPM)',
            'action': 'Check motor voltage and mechanical load'
        })
    elif reading.rpm > Config.RPM_MAX:
        alerts.append({
            'level': 'Warning',
            'issue': f'🔄 High RPM: {reading.rpm} RPM (Max: {Config.RPM_MAX} RPM)',
            'action': 'Check motor controller and load'
        })
    
    # Current alerts
    if reading.current > Config.CURRENT_MAX:
        alerts.append({
            'level': 'Critical',
            'issue': f'⚡ Overload Current: {reading.current} A (Max: {Config.CURRENT_MAX} A)',
            'action': 'Immediately reduce load or check for mechanical binding'
        })
    elif reading.current > Config.CURRENT_WARNING:
        alerts.append({
            'level': 'Warning',
            'issue': f'⚡ Current Rising: {reading.current} A (Normal: {machine.current_normal} A)',
            'action': 'Check for increasing load or electrical issue'
        })
    
    # Create Alert objects in database
    created_alerts = []
    for alert_data in alerts:
        alert = Alert(
            machine_id=machine.machine_id,
            level=alert_data['level'],
            issue=alert_data['issue'],
            action=alert_data['action']
        )
        db.session.add(alert)
        created_alerts.append(alert)
    
    return created_alerts

# ---------- ROUTES ----------

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/dashboard')
def get_dashboard_summary():
    """Level 1: Dashboard summary cards"""
    total = Machine.query.count()
    
    # Online devices (last 5 minutes)
    online = Machine.query.filter(
        Machine.last_reading > datetime.utcnow() - timedelta(minutes=5)
    ).count()
    
    # Warning machines (40-69%)
    warning = Machine.query.filter(
        Machine.health_score.between(40, 69)
    ).count()
    
    # Critical machines (<40%)
    critical = Machine.query.filter(
        Machine.health_score < 40
    ).count()
    
    # Average health
    avg_health = db.session.query(func.avg(Machine.health_score)).scalar() or 0
    
    # Recent alerts (last 5)
    recent_alerts = Alert.query.filter_by(resolved=False)\
        .order_by(desc(Alert.timestamp)).limit(5).all()
    
    return jsonify({
        'total': total,
        'online': online,
        'warning': warning,
        'critical': critical,
        'avg_health': round(avg_health, 1),
        'alerts': [alert.to_dict() for alert in recent_alerts]
    })

@app.route('/api/machines')
def get_machines():
    """Level 2: List of all machines"""
    machines = Machine.query.all()
    return jsonify([{
        'id': m.machine_id,
        'name': m.name,
        'factory': m.factory,
        'status': m.status,
        'health': m.health_score,
        'last_reading': m.last_reading.strftime('%Y-%m-%d %H:%M')
    } for m in machines])

@app.route('/api/machine/<machine_id>')
def get_machine_detail(machine_id):
    """Level 3: Detailed machine data"""
    machine = Machine.query.filter_by(machine_id=machine_id).first()
    if not machine:
        return jsonify({'error': 'Machine not found'}), 404
    
    # Get latest reading
    latest = SensorReading.query.filter_by(machine_id=machine_id)\
        .order_by(desc(SensorReading.timestamp)).first()
    
    # Get last 24 hours readings for graph
    history = SensorReading.query.filter_by(machine_id=machine_id)\
        .filter(SensorReading.timestamp > datetime.utcnow() - timedelta(hours=24))\
        .order_by(SensorReading.timestamp).all()
    
    # Get recent alerts (last 10)
    alerts = Alert.query.filter_by(machine_id=machine_id)\
        .order_by(desc(Alert.timestamp)).limit(10).all()
    
    # Get maintenance history
    maintenance = Alert.query.filter_by(machine_id=machine_id)\
        .filter(Alert.issue.like('%Maintenance%'))\
        .order_by(desc(Alert.timestamp)).limit(5).all()
    
    return jsonify({
        'info': {
            'id': machine.machine_id,
            'name': machine.name,
            'factory': machine.factory,
            'status': machine.status,
            'health': machine.health_score,
            'last_reading': machine.last_reading.strftime('%Y-%m-%d %H:%M')
        },
        'latest': {
            'temperature': latest.temperature if latest else None,
            'vibration': latest.vibration if latest else None,
            'rpm': latest.rpm if latest else None,
            'current': latest.current if latest else None,
            'time': latest.timestamp.strftime('%Y-%m-%d %H:%M') if latest else None
        },
        'normal_ranges': {
            'temp_normal': machine.temp_normal,
            'vib_normal': machine.vib_normal,
            'rpm_normal': machine.rpm_normal,
            'current_normal': machine.current_normal
        },
        'history': [reading.to_dict() for reading in history],
        'alerts': [alert.to_dict() for alert in alerts],
        'maintenance': [alert.to_dict() for alert in maintenance]
    })

@app.route('/api/machine/<machine_id>/reading', methods=['POST'])
def add_reading(machine_id):
    """ESP32 data receive endpoint"""
    data = request.json
    
    # Get or create machine
    machine = Machine.get_or_create(machine_id)
    
    # Create reading
    reading = SensorReading(
        machine_id=machine_id,
        temperature=data.get('temperature'),
        vibration=data.get('vibration'),
        rpm=data.get('rpm'),
        current=data.get('current')
    )
    db.session.add(reading)
    
    # Update machine
    machine.last_reading = datetime.utcnow()
    
    # Calculate health score
    health = calculate_health_score(machine, reading)
    machine.health_score = health
    
    # Determine status
    if health >= 90:
        machine.status = 'Normal'
    elif health >= 70:
        machine.status = 'Attention'
    elif health >= 40:
        machine.status = 'Warning'
    else:
        machine.status = 'Critical'
    
    # Check alerts
    new_alerts = check_alerts(machine, reading)
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'health_score': health,
        'machine_status': machine.status,
        'alerts_created': len(new_alerts)
    })

@app.route('/api/machine/<machine_id>/health-trend')
def get_health_trend(machine_id):
    """Get health score trend for last 7 days"""
    readings = SensorReading.query.filter_by(machine_id=machine_id)\
        .filter(SensorReading.timestamp > datetime.utcnow() - timedelta(days=7))\
        .order_by(SensorReading.timestamp).all()
    
    machine = Machine.query.filter_by(machine_id=machine_id).first()
    if not machine:
        return jsonify({'error': 'Machine not found'}), 404
    
    trend = []
    for reading in readings:
        health = calculate_health_score(machine, reading)
        trend.append({
            'time': reading.timestamp.strftime('%Y-%m-%d %H:%M'),
            'health': health
        })
    
    return jsonify(trend)

@app.route('/api/machine/<machine_id>/stats')
def get_machine_stats(machine_id):
    """Get summary statistics for a machine"""
    machine = Machine.query.filter_by(machine_id=machine_id).first()
    if not machine:
        return jsonify({'error': 'Machine not found'}), 404
    
    # Get readings for last 24 hours
    readings = SensorReading.query.filter_by(machine_id=machine_id)\
        .filter(SensorReading.timestamp > datetime.utcnow() - timedelta(hours=24)).all()
    
    if not readings:
        return jsonify({'error': 'No readings found'}), 404
    
    temps = [r.temperature for r in readings]
    vibs = [r.vibration for r in readings]
    rpms = [r.rpm for r in readings]
    currents = [r.current for r in readings]
    
    return jsonify({
        'avg_temp': round(sum(temps) / len(temps), 1),
        'max_temp': round(max(temps), 1),
        'min_temp': round(min(temps), 1),
        'avg_vib': round(sum(vibs) / len(vibs), 1),
        'max_vib': round(max(vibs), 1),
        'avg_rpm': round(sum(rpms) / len(rpms)),
        'avg_current': round(sum(currents) / len(currents), 1),
        'reading_count': len(readings),
        'time_range': f'{readings[0].timestamp.strftime("%H:%M")} - {readings[-1].timestamp.strftime("%H:%M")}'
    })

@app.route('/api/demo-data')
def generate_demo_data():
    """Generate demo data for testing"""
    machine = Machine.get_or_create('M-001')
    
    # Generate 100 readings
    for i in range(100):
        timestamp = datetime.utcnow() - timedelta(hours=24) + timedelta(minutes=i*15)
        
        temp = 42.0 + random.uniform(-3, 5)
        vib = 2.0 + random.uniform(-0.5, 1.5)
        rpm = 1480 + random.uniform(-20, 20)
        current = 5.0 + random.uniform(-0.5, 1.0)
        
        # Add anomalies
        if i % 30 == 0:
            temp += 8
            vib += 1.0
        
        reading = SensorReading(
            machine_id='M-001',
            timestamp=timestamp,
            temperature=round(temp, 1),
            vibration=round(vib, 1),
            rpm=int(rpm),
            current=round(current, 1)
        )
        db.session.add(reading)
    
    db.session.commit()
    return jsonify({'message': 'Demo data generated successfully'})

# ---------- CREATE TABLES ----------
with app.app_context():
    db.create_all()
    print("✅ Database tables created successfully!")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)