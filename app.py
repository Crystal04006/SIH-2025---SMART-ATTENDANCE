import os
import time
import uuid
import csv
import io
import qrcode
import json # Import the json library
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response, flash
from flask_sqlalchemy import SQLAlchemy

# --- App Configuration ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_very_secret_key_that_should_be_changed'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

QR_CODE_FOLDER = os.path.join('static', 'qrcodes')
os.makedirs(QR_CODE_FOLDER, exist_ok=True)
app.config['QR_CODE_FOLDER'] = QR_CODE_FOLDER
QR_CODE_VALIDITY_SECONDS = 30

# --- Database Models (User model updated) ---
class Institution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class AcademicYear(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.String(20), nullable=False)
    institution_id = db.Column(db.Integer, db.ForeignKey('institution.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('year', 'institution_id', name='_year_institution_uc'),)

class Batch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    year_id = db.Column(db.Integer, db.ForeignKey('academic_year.id'), nullable=False)
    institution_id = db.Column(db.Integer, db.ForeignKey('institution.id'), nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    institution_id = db.Column(db.Integer, db.ForeignKey('institution.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=True)
    # NEW: Field to store the face descriptor as a JSON string
    face_descriptor = db.Column(db.Text, nullable=True)
    __table_args__ = (db.UniqueConstraint('username', 'institution_id', name='_username_institution_uc'),)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    institution_id = db.Column(db.Integer, db.ForeignKey('institution.id'), nullable=False)

class SessionLog(db.Model):
    id = db.Column(db.String(80), primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    timestamp = db.Column(db.Integer, nullable=False)

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, nullable=False)
    session_id = db.Column(db.String(80), db.ForeignKey('session_log.id'), nullable=False)
    timestamp = db.Column(db.Integer, nullable=False)

# --- Decorators for Auth ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('role') != role:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Main & Auth Routes ---
@app.route('/')
def index():
    if 'user_id' not in session: return redirect(url_for('login'))
    role = session.get('role')
    if role == 'admin': return redirect(url_for('admin_dashboard'))
    if role == 'teacher': return redirect(url_for('teacher_dashboard'))
    return redirect(url_for('student_dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    institutions = Institution.query.all()
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username'), institution_id=request.form.get('institution')).first()
        if user and user.password == request.form.get('password'):
            session['user_id'], session['role'], session['institution_id'] = user.id, user.role, user.institution_id
            return redirect(url_for('index'))
        else:
            flash("Invalid credentials for the selected institution.", "danger")
    return render_template('login.html', institutions=institutions)

@app.route('/register-institution', methods=['GET', 'POST'])
def register_institution():
    if request.method == 'POST':
        inst_name, admin_user, admin_pass = request.form.get('institution_name'), request.form.get('admin_username'), request.form.get('admin_password')
        if Institution.query.filter_by(name=inst_name).first():
            flash("An institution with this name already exists.", "danger")
            return redirect(url_for('register_institution'))
        new_institution = Institution(name=inst_name)
        db.session.add(new_institution)
        db.session.commit()
        new_admin = User(username=admin_user, name=admin_user, password=admin_pass, role='admin', institution_id=new_institution.id)
        db.session.add(new_admin)
        db.session.commit()
        flash("Institution registered successfully! Please login.", "success")
        return redirect(url_for('login'))
    return render_template('register_institution.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/forgot-password')
def forgot_password_info():
    return render_template('forgot_password_info.html')

# --- Admin Routes ---
@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    inst_id = session['institution_id']
    user = User.query.get(session['user_id'])
    years = AcademicYear.query.filter_by(institution_id=inst_id).order_by(AcademicYear.year.desc()).all()
    return render_template('admin_dashboard.html', user=user, years=years)

@app.route('/admin/add-year', methods=['POST'])
@login_required
@role_required('admin')
def add_year():
    year_name = request.form.get('year')
    if year_name:
        new_year = AcademicYear(year=year_name, institution_id=session['institution_id'])
        db.session.add(new_year)
        db.session.commit()
        flash(f"Academic Year '{year_name}' created.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/manage-year/<int:year_id>')
@login_required
@role_required('admin')
def manage_year(year_id):
    year = AcademicYear.query.get_or_404(year_id)
    if year.institution_id != session['institution_id']: return redirect(url_for('admin_dashboard'))
    user = User.query.get(session['user_id'])
    batches = Batch.query.filter_by(year_id=year.id).all()
    return render_template('manage_year.html', user=user, year=year, batches=batches)

@app.route('/admin/add-batch', methods=['POST'])
@login_required
@role_required('admin')
def add_batch():
    year_id = request.form.get('year_id')
    batch_name = request.form.get('batch_name')
    if year_id and batch_name:
        new_batch = Batch(name=batch_name, year_id=year_id, institution_id=session['institution_id'])
        db.session.add(new_batch)
        db.session.commit()
        flash(f"Batch '{batch_name}' created.", "success")
    return redirect(url_for('manage_year', year_id=year_id))

@app.route('/admin/manage-batch/<int:batch_id>')
@login_required
@role_required('admin')
def manage_batch(batch_id):
    batch = Batch.query.get_or_404(batch_id)
    if batch.institution_id != session['institution_id']: return redirect(url_for('admin_dashboard'))
    user = User.query.get(session['user_id'])
    students = User.query.filter_by(batch_id=batch.id).all()
    return render_template('manage_batch.html', user=user, batch=batch, students=students)

@app.route('/admin/add-single-student', methods=['POST'])
@login_required
@role_required('admin')
def add_single_student():
    batch_id = request.form.get('batch_id')
    student_id, student_name = request.form.get('student_id'), request.form.get('student_name')
    if not (batch_id and student_id and student_name):
        flash("All fields are required.", "danger")
        return redirect(request.referrer)
    if User.query.filter_by(username=student_id, institution_id=session['institution_id']).first():
        flash(f"A student with ID '{student_id}' already exists.", "danger")
    else:
        new_student = User(username=student_id, name=student_name, password='changeme123', role='student', institution_id=session['institution_id'], batch_id=batch_id)
        db.session.add(new_student)
        db.session.commit()
        flash(f"Student '{student_name}' added successfully.", "success")
    return redirect(url_for('manage_batch', batch_id=batch_id))

@app.route('/admin/import-students-csv', methods=['POST'])
@login_required
@role_required('admin')
def import_students_csv():
    batch_id = request.form.get('batch_id')
    csv_file = request.files.get('csv_file')
    if not csv_file or csv_file.filename == '':
        flash("No file selected.", "danger")
        return redirect(url_for('manage_batch', batch_id=batch_id))
    try:
        stream = io.StringIO(csv_file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.reader(stream)
        next(csv_reader)
        imported, skipped = 0, 0
        for row in csv_reader:
            student_id, student_name = row[0].strip(), row[1].strip()
            if not User.query.filter_by(username=student_id, institution_id=session['institution_id']).first():
                new_student = User(username=student_id, name=student_name, password='changeme123', role='student', institution_id=session['institution_id'], batch_id=batch_id)
                db.session.add(new_student)
                imported += 1
            else:
                skipped += 1
        db.session.commit()
        flash(f"Successfully imported {imported} new students. Skipped {skipped} duplicates.", "success")
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
    return redirect(url_for('manage_batch', batch_id=batch_id))

@app.route('/admin/manage-staff')
@login_required
@role_required('admin')
def manage_staff():
    inst_id = session['institution_id']
    all_users = User.query.filter_by(institution_id=inst_id).all()
    teachers = [u for u in all_users if u.role == 'teacher']
    user = User.query.get(session['user_id'])
    return render_template('manage_staff.html', teachers=teachers, all_users=all_users, user=user)

@app.route('/admin/add-teacher', methods=['POST'])
@login_required
@role_required('admin')
def add_teacher():
    inst_id = session['institution_id']
    username, name, password = request.form.get('username'), request.form.get('name'), request.form.get('password')
    if User.query.filter_by(username=username, institution_id=inst_id).first():
        flash("A user with this username already exists.", "danger")
    else:
        new_teacher = User(username=username, name=name, password=password, role='teacher', institution_id=inst_id)
        db.session.add(new_teacher)
        db.session.commit()
        flash("Teacher added successfully.", "success")
    return redirect(url_for('manage_staff'))

@app.route('/admin/reset-password', methods=['POST'])
@login_required
@role_required('admin')
def reset_password():
    user_to_reset = User.query.get(request.form.get('user_id'))
    if user_to_reset and user_to_reset.institution_id == session['institution_id']:
        user_to_reset.password = request.form.get('new_password')
        db.session.commit()
        flash(f"Password for {user_to_reset.name} has been reset.", "success")
    else:
        flash("Could not find user or permission denied.", "danger")
    return redirect(url_for('manage_staff'))

# --- Teacher Routes ---
@app.route('/teacher/dashboard')
@login_required
@role_required('teacher')
def teacher_dashboard():
    user = User.query.get(session['user_id'])
    courses = Course.query.filter_by(teacher_id=user.id).all()
    return render_template('teacher_dashboard.html', courses=courses, user=user)

@app.route('/teacher/add-course', methods=['POST'])
@login_required
@role_required('teacher')
def add_course():
    course_name = request.form.get('course_name')
    if course_name:
        new_course = Course(name=course_name, teacher_id=session['user_id'], institution_id=session['institution_id'])
        db.session.add(new_course)
        db.session.commit()
    return redirect(url_for('teacher_dashboard'))

@app.route('/teacher/manage/course/<int:course_id>')
@login_required
@role_required('teacher')
def manage_course(course_id):
    course = Course.query.get_or_404(course_id)
    if course.teacher_id != session['user_id']: return redirect(url_for('teacher_dashboard'))
    enrollments = Enrollment.query.filter_by(course_id=course_id).all()
    enrolled_students = [User.query.get(e.student_id) for e in enrollments]
    user = User.query.get(session['user_id'])
    return render_template('manage_course.html', course=course, students=enrolled_students, user=user)
    
@app.route('/teacher/enroll-student', methods=['POST'])
@login_required
@role_required('teacher')
def enroll_student():
    student_id, course_id = request.form.get('student_id'), request.form.get('course_id')
    student = User.query.filter_by(username=student_id, role='student', institution_id=session['institution_id']).first()
    if student:
        if not Enrollment.query.filter_by(student_id=student.id, course_id=course_id).first():
            new_enrollment = Enrollment(student_id=student.id, course_id=course_id)
            db.session.add(new_enrollment)
            db.session.commit()
            flash(f"{student.name} enrolled successfully.", "success")
        else:
            flash(f"{student.name} is already enrolled in this course.", "warning")
    else:
        flash(f"No student found with ID '{student_id}'. Please contact your administrator.", "danger")
    return redirect(url_for('manage_course', course_id=course_id))

@app.route('/teacher/history/student/<int:student_id>/course/<int:course_id>')
@login_required
@role_required('teacher')
def student_history(student_id, course_id):
    student, course = User.query.get_or_404(student_id), Course.query.get_or_404(course_id)
    total_sessions = SessionLog.query.filter_by(course_id=course_id).count()
    days_present = db.session.query(Attendance.id).join(SessionLog).filter(Attendance.student_id == student_id, SessionLog.course_id == course_id).count()
    days_absent, percentage = total_sessions - days_present, (days_present / total_sessions * 100) if total_sessions > 0 else 0
    stats = {'total_classes': total_sessions, 'present': days_present, 'absent': days_absent, 'percentage': round(percentage, 2)}
    user = User.query.get(session['user_id'])
    return render_template('student_history.html', student=student, course=course, stats=stats, user=user)
    
@app.route('/teacher/download-report/<int:course_id>')
@login_required
@role_required('teacher')
def download_report(course_id):
    course, enrollments = Course.query.get_or_404(course_id), Enrollment.query.filter_by(course_id=course_id).all()
    total_sessions = SessionLog.query.filter_by(course_id=course_id).count()
    output, writer = io.StringIO(), csv.writer(output)
    writer.writerow(['Student Name', 'Student ID', 'Days Present', 'Days Absent', 'Total Classes', 'Attendance Percentage'])
    for enrollment in enrollments:
        student = User.query.get(enrollment.student_id)
        days_present = db.session.query(Attendance.id).join(SessionLog).filter(Attendance.student_id == student.id, SessionLog.course_id == course_id).count()
        days_absent, percentage = total_sessions - days_present, (days_present / total_sessions * 100) if total_sessions > 0 else 0
        writer.writerow([student.name, student.username, days_present, days_absent, total_sessions, f"{round(percentage, 2)}%"])
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=attendance_report_{course.name}.csv"})

# --- Student Routes ---
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if session.get('role') != 'student': return redirect(url_for('index'))
    user = User.query.get(session['user_id'])
    # NEW: Check if student needs to enroll their face
    if not user.face_descriptor:
        return redirect(url_for('face_enrollment'))
    
    enrollments = Enrollment.query.filter_by(student_id=user.id).all()
    attendance_data = []
    for enrollment in enrollments:
        course = Course.query.get(enrollment.course_id)
        total_sessions = SessionLog.query.filter_by(course_id=course.id).count()
        days_present = db.session.query(Attendance.id).join(SessionLog).filter(Attendance.student_id == user.id, SessionLog.course_id == course.id).count()
        percentage = (days_present / total_sessions * 100) if total_sessions > 0 else 0
        attendance_data.append({'course_name': course.name, 'percentage': round(percentage, 2)})
    return render_template('student_dashboard.html', user=user, attendance_data=attendance_data)

# NEW: Route for the face enrollment page
@app.route('/student/enroll-face')
@login_required
def face_enrollment():
    if session.get('role') != 'student': return redirect(url_for('index'))
    user = User.query.get(session['user_id'])
    return render_template('face_enrollment.html', user=user)

# --- API Routes ---
@app.route('/api/generate-qr', methods=['POST'])
@login_required
@role_required('teacher')
def generate_qr():
    course_id = request.json.get('course_id')
    if not course_id: return jsonify({'error': 'Course ID is required'}), 400
    session_id, timestamp = str(uuid.uuid4()), int(time.time())
    new_session = SessionLog(id=session_id, course_id=course_id, timestamp=timestamp)
    db.session.add(new_session)
    db.session.commit()
    qr_data = f'{{"session_id": "{session_id}", "course_id": "{course_id}", "timestamp": {timestamp}}}'
    img = qrcode.make(qr_data)
    filename = f'{session_id}.png'
    filepath = os.path.join(app.config['QR_CODE_FOLDER'], filename)
    img.save(filepath)
    return jsonify({'qr_code_url': url_for('static', filename=f'qrcodes/{filename}'), 'session_id': session_id})

@app.route('/api/mark-attendance', methods=['POST'])
@login_required
def mark_attendance():
    if session.get('role') != 'student': return jsonify({'error': 'Unauthorized'}), 403
    try: qr_data = eval(request.json.get('scanned_data'))
    except: return jsonify({'success': False, 'message': 'Invalid QR Code format.'}), 400
    session_id, course_id, qr_timestamp = qr_data.get('session_id'), qr_data.get('course_id'), qr_data.get('timestamp')
    if int(time.time()) - qr_timestamp > QR_CODE_VALIDITY_SECONDS:
        return jsonify({'success': False, 'message': 'Expired QR Code.'}), 400
    student_id = session['user_id']
    if not Enrollment.query.filter_by(student_id=student_id, course_id=course_id).first():
        return jsonify({'success': False, 'message': 'Scan failed. You are not enrolled in this course.'}), 400
    if Attendance.query.filter_by(student_id=student_id, session_id=session_id).first():
        return jsonify({'success': False, 'message': 'Attendance already marked for this session.'}), 400
    new_record = Attendance(student_id=student_id, session_id=session_id, timestamp=int(time.time()))
    db.session.add(new_record)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Attendance marked successfully!'})

@app.route('/api/attendance-data/<session_id>')
@login_required
@role_required('teacher')
def attendance_data(session_id):
    records = Attendance.query.filter_by(session_id=session_id).all()
    students_present = [f"{User.query.get(r.student_id).name} - {User.query.get(r.student_id).username}" for r in records]
    return jsonify({'students': students_present})

# NEW: API route to save the student's enrolled face
@app.route('/api/save-face', methods=['POST'])
@login_required
def save_face():
    if session.get('role') != 'student': return jsonify({'error': 'Unauthorized'}), 403
    user, descriptor = User.query.get(session['user_id']), request.json.get('descriptor')
    if user and descriptor:
        user.face_descriptor = json.dumps(descriptor)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Face enrolled successfully!'})
    return jsonify({'success': False, 'message': 'Failed to save face data.'}), 400

# NEW: API route to get enrolled face data for verification
@app.route('/api/get-face-data')
@login_required
def get_face_data():
    if session.get('role') != 'student': return jsonify({'error': 'Unauthorized'}), 403
    user = User.query.get(session['user_id'])
    if user and user.face_descriptor:
        return jsonify({'descriptor': json.loads(user.face_descriptor)})
    return jsonify({'descriptor': None})

# --- Main Execution ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # IMPORTANT: Run with SSL for camera access
    app.run(debug=True, ssl_context='adhoc')

