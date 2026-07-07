from datetime import datetime, timezone
from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from ..extensions import db
from ..models.attendance import Attendance
from . import employee_bp
from .routes import employee_required
from ..utils.logging import get_logger

logger = get_logger(__name__)

@employee_bp.route('/attendance/punch', methods=['POST'])
@employee_required
def punch():
    """
    Handles Punch In and Punch Out logic for employees.
    Expects JSON payload with geolocation and device info.
    """
    data = request.json or {}
    now = datetime.now(timezone.utc)
    today = now.date()
    
    from ..models.employee import Employee
    emp = Employee.query.filter_by(user_id=current_user.id).first()
    if not emp:
        return jsonify({'error': 'Employee profile not found.'}), 404
        
    # Check if there is already an attendance record for today
    record = Attendance.query.filter_by(employee_id=emp.id, date=today).first()
    
    action = data.get('action') # 'in' or 'out'
    lat = data.get('latitude')
    lng = data.get('longitude')
    acc = data.get('accuracy')
    location_status = data.get('location_status', 'Unknown')
    device_info = data.get('device_info', request.user_agent.string)
    ip_address = request.remote_addr
    
    if action == 'in':
        if record and record.punch_in_time:
            return jsonify({'error': 'Already punched in today.'}), 400
            
        if not record:
            record = Attendance(employee_id=emp.id, date=today)
            db.session.add(record)
            
        record.punch_in_time = now
        record.status = 'Present'
        record.latitude = lat
        record.longitude = lng
        record.gps_accuracy = acc
        record.location_status = location_status
        record.device_info = device_info
        record.ip_address = ip_address
        
        db.session.commit()
        
        from flask import current_app
        from ..utils.logging import log_user_action
        log_user_action(current_app.logger, current_user, 'punch_in', module='attendance', entity_type='Attendance', entity_id=record.id, description=f'Punched in at {now.strftime("%I:%M %p")}')
        
        return jsonify({'message': 'Punched in successfully.', 'time': now.strftime('%I:%M %p')}), 200
        
    elif action == 'out':
        if not record or not record.punch_in_time:
            return jsonify({'error': 'You must punch in first.'}), 400
            
        if record.punch_out_time:
            return jsonify({'error': 'Already punched out today.'}), 400
            
        record.punch_out_time = now
        # Calculate total hours
        # Make both naive to avoid offset-naive vs offset-aware TypeError
        t_out = record.punch_out_time.replace(tzinfo=None)
        t_in = record.punch_in_time.replace(tzinfo=None)
        td = t_out - t_in
        record.total_hours = round(td.total_seconds() / 3600.0, 2)
        
        db.session.commit()
        
        from flask import current_app
        from ..utils.logging import log_user_action
        log_user_action(current_app.logger, current_user, 'punch_out', module='attendance', entity_type='Attendance', entity_id=record.id, description=f'Punched out at {now.strftime("%I:%M %p")}')
        return jsonify({'message': 'Punched out successfully.', 'time': now.strftime('%I:%M %p')}), 200
        
    return jsonify({'error': 'Invalid action.'}), 400


@employee_bp.route('/attendance/history', methods=['GET'])
@employee_required
def attendance_history():
    """
    View attendance history for the logged-in employee.
    """
    from ..models.employee import Employee
    emp = Employee.query.filter_by(user_id=current_user.id).first()
    if not emp:
        flash("Employee profile not found.", "danger")
        return redirect(url_for('employee.dashboard'))
        
    page = request.args.get('page', 1, type=int)
    records = Attendance.query.filter_by(employee_id=emp.id).order_by(Attendance.date.desc()).paginate(page=page, per_page=15)
    return render_template('employee/attendance_history.html', records=records)
