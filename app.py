from flask import Flask, render_template, request, redirect, url_for, session,flash
from models import User, Admin,Course,Subject
from connections import SessionLocal

app = Flask(__name__)
app.secret_key = 'your_secret_key'

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = False  
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        db = SessionLocal()  
        try:
          
            admin = db.query(Admin).filter_by(username=username).first()
            if admin and admin.password == password:  
                session['username'] = admin.username
                session['user_id'] = admin.id
                session['role'] = 'admin' 
                return redirect(url_for('admin_dashboard'))  

            
            user = db.query(User).filter_by(username=username).first()
            if user and user.password == password:  
                session['username'] = user.username 
                session['user_id'] = user.id
                session['role'] = 'student'  
                return redirect(url_for('student_dashboard')) 

            error = True  

        finally:
            db.close() 

    return render_template('login.html', error=error)

# Admin Dashboard route
@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))  
    
    
    db = SessionLocal()
    courses = db.query(Course).all()

    return render_template('admin/admin_dashboard.html', courses=courses, username=session.get('username'))


"""
student dashboard
"""
@app.route('/student_dashboard')
def student_dashboard():
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('login')) 
    
    return render_template('students/student_dashboard.html',username=session.get('username'))

'''
add course
'''
@app.route('/add_course', methods=['GET', 'POST'])
def add_course():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))  
    
    db = SessionLocal()
    
    if request.method == 'POST':
        course_name = request.form['course_name']
        course_level = request.form['course_level'] 
        
        new_course = Course(name=course_name, level=course_level)
        db.add(new_course)
        db.commit()
        
        return redirect(url_for('admin_dashboard'))  

    return render_template('admin/add_course.html')

'''
edit a course
'''
@app.route('/edit_course/<int:course_id>', methods=['GET', 'POST'])
def edit_course(course_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))  
    
    db = SessionLocal()
    
   
    course = db.query(Course).filter(Course.id == course_id).first()
    
    if not course:
        return "Course not found", 404  

    if request.method == 'POST':
       
        course.name = request.form['course_name']
        course.level = request.form['course_level']  
        
        db.commit() 
        
        return redirect(url_for('admin_dashboard'))  
    
    
    return render_template('admin/edit_course.html', course=course)

'''
delete a course
'''
@app.route('/delete_course/<int:course_id>', methods=['POST'])
def delete_course(course_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))  
    
    db = SessionLocal()
    
    
    course = db.query(Course).filter(Course.id == course_id).first()
    
    if not course:
        return "Course not found", 404  
    
    db.delete(course)  
    db.commit() 
    
    return redirect(url_for('admin_dashboard')) 


'''
manage course 
'''
@app.route('/manage_courses', methods=['GET'])
def manage_courses():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))  # Redirect if the user is not an admin
    
    db = SessionLocal()
    courses = db.query(Course).all()  # Fetch all courses from the database
    return render_template('admin/manage_courses.html', courses=courses)

'''
add subject
'''
@app.route('/add_subject', methods=['GET', 'POST'])
def add_subject():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))  # Redirect if the user is not an admin
    
    db = SessionLocal()

    if request.method == 'POST':
        subject_name = request.form['subject_name']
        course_id = request.form['course_id']

        # Check if the subject already exists
        existing_subject = db.query(Subject).filter_by(name=subject_name, course_id=course_id).first()
        if existing_subject:
            flash('Subject already exists for this course!', 'danger')
            return redirect(url_for('add_subject'))

        new_subject = Subject(name=subject_name, course_id=course_id)
        db.add(new_subject)
        db.commit()
        flash('Subject added successfully!', 'success')

        return redirect(url_for('manage_courses'))  
    
    
    courses = db.query(Course).all()
    return render_template('admin/add_subject.html', courses=courses)


'''edit subject'''

@app.route('/edit_subject/<int:subject_id>', methods=['GET', 'POST'])
def edit_subject(subject_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))  
    db = SessionLocal()
    subject = db.query(Subject).filter(Subject.id == subject_id).first()

    if not subject:
        return "Subject not found", 404  

    if request.method == 'POST':
        
        subject.name = request.form['subject_name']
        db.commit()  
        return redirect(url_for('manage_courses'))  

    return render_template('admin/edit_subject.html', subject=subject)

'''
delete subject 
'''

@app.route('/delete_subject/<int:subject_id>', methods=['POST'])
def delete_subject(subject_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))  
    
    db = SessionLocal()
    subject = db.query(Subject).filter(Subject.id == subject_id).first()

    if not subject:
        return "Subject not found", 404  
    
    db.delete(subject)  
    db.commit() 

    return redirect(url_for('manage_courses'))  




@app.route('/logout')
def logout():
   
    session.pop('username', None)
    session.pop('user_id', None)
    session.pop('role', None)
    
    
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
