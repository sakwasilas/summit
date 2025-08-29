from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import pandas as pd
from flask import send_file
import os

from connections import SessionLocal
from models import User, Admin, Course, Subject, Question, Quiz, Video, Document,StudentProfile,Result
from utils import parse_docx_questions

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# -----------------------------
# Upload folders & allowed types
# -----------------------------
BASE_UPLOAD = os.path.join(os.getcwd(), 'static', 'uploads')
VIDEOS_UPLOAD_FOLDER = os.path.join(BASE_UPLOAD, 'videos')
DOCUMENTS_UPLOAD_FOLDER = os.path.join(BASE_UPLOAD, 'documents')
EXAMS_UPLOAD_FOLDER = os.path.join(BASE_UPLOAD, 'exams')
QUESTION_IMAGES_FOLDER = os.path.join('static', 'question_images')

for path in [BASE_UPLOAD, VIDEOS_UPLOAD_FOLDER, DOCUMENTS_UPLOAD_FOLDER, EXAMS_UPLOAD_FOLDER, QUESTION_IMAGES_FOLDER]:
    os.makedirs(path, exist_ok=True)

ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}
ALLOWED_EXAM_EXTENSIONS = {'docx'}

def allowed(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set


# -----------------------------
# Routes: Auth + Dashboards
# -----------------------------
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = False
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        db = SessionLocal()
        try:
            # Admin
            admin = db.query(Admin).filter_by(username=username).first()
            if admin and admin.password == password:
                session.update({'username': admin.username, 'user_id': admin.id, 'role': 'admin'})
                return redirect(url_for('admin_dashboard'))

            # Student
            user = db.query(User).filter_by(username=username).first()
            if user and user.password == password:
                session.update({'username': user.username, 'user_id': user.id, 'role': 'student'})
                return redirect(url_for('student_dashboard'))

            error = True
        finally:
            db.close()
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    db = SessionLocal()
    try:
        courses = db.query(Course).all()
        return render_template('admin/admin_dashboard.html', courses=courses, username=session.get('username'))
    finally:
        db.close()

# -----------------------------
# Courses & Subjects
# -----------------------------
@app.route('/add_course', methods=['GET', 'POST'])
def add_course():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))  

    db = SessionLocal()
    try:
        if request.method == 'POST':
            course_name = request.form['course_name']
            course_level = request.form['course_level']

            # 🔍 Check if course already exists
            existing_course = db.query(Course).filter_by(name=course_name).first()
            if existing_course:
                flash(f"Course '{course_name}' already exists!", "warning")
                return redirect(url_for('add_course'))

            # Add new course
            new_course = Course(name=course_name, level=course_level)
            db.add(new_course)
            db.commit()
            flash("Course added successfully!", "success")
            return redirect(url_for('admin_dashboard'))

        return render_template('admin/add_course.html')

    except Exception as e:
        db.rollback()
        print("❌ Error in /add_course:", e)
        flash("An error occurred while adding the course.", "danger")
        return redirect(url_for('add_course'))

    finally:
        db.close()


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


# -----------------------------
# Exams (.docx parsing)
# -----------------------------
'''
@app.route('/upload_exam', methods=['GET', 'POST'])
def upload_exam():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    db = SessionLocal()
    try:
        courses, subjects = db.query(Course).all(), db.query(Subject).all()
        if request.method == 'POST':
            title = request.form['title'].strip()
            course_id, subject_id = int(request.form['course']), int(request.form['subject'])
            duration = int(request.form.get('duration', 30))
            file = request.files.get('quiz_file')

            if not file or not allowed(file.filename, ALLOWED_EXAM_EXTENSIONS):
                flash('❌ Upload a valid .docx file.', 'danger'); return redirect(request.url)

            filename = secure_filename(file.filename)
            file_path = os.path.join(EXAMS_UPLOAD_FOLDER, filename)
            file.save(file_path)

            questions = parse_docx_questions(file_path, image_output_dir=QUESTION_IMAGES_FOLDER)
            if not questions:
                flash("❌ No valid questions found.", "danger"); return redirect(request.url)

            quiz = Quiz(title=title, course_id=course_id, subject_id=subject_id,
                        duration=duration, status='active')
            db.add(quiz); db.commit(); db.refresh(quiz)

            for q in questions:
                db.add(Question(quiz_id=quiz.id, question_text=q.get("question", ""),
                                option_a=q.get("a", ""), option_b=q.get("b", ""),
                                option_c=q.get("c", ""), option_d=q.get("d", ""),
                                correct_option=q.get("answer", "").lower(),
                                marks=q.get("marks", 1), extra_content=q.get("extra_content"),
                                image=q.get("image")))
            db.commit()
            flash(f"✅ Uploaded quiz with {len(questions)} question(s).", "success")
            return redirect(url_for('upload_exam'))
        return render_template('admin/upload_exams.html', courses=courses, subjects=subjects)
    finally:
        db.close()
'''
@app.route('/upload_exam', methods=['GET', 'POST'])
def upload_exam():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    db = SessionLocal()
    try:
        courses, subjects = db.query(Course).all(), db.query(Subject).all()
        if request.method == 'POST':
            title = request.form['title'].strip()
            course_id, subject_id = int(request.form['course']), int(request.form['subject'])
            duration = int(request.form.get('duration', 30))
            file = request.files.get('quiz_file')

            if not file or not allowed(file.filename, ALLOWED_EXAM_EXTENSIONS):
                flash('❌ Upload a valid .docx file.', 'danger')
                return redirect(request.url)

            filename = secure_filename(file.filename)
            file_path = os.path.join(EXAMS_UPLOAD_FOLDER, filename)
            file.save(file_path)

            questions = parse_docx_questions(file_path, image_output_dir=QUESTION_IMAGES_FOLDER)
            if not questions:
                flash("❌ No valid questions found.", "danger")
                return redirect(request.url)

            quiz = Quiz(title=title, course_id=course_id, subject_id=subject_id,
                        duration=duration, status='active')
            db.add(quiz)
            db.commit()
            db.refresh(quiz)

            for q in questions:
                db.add(Question(quiz_id=quiz.id, question_text=q.get("question", ""),
                                option_a=q.get("a", ""), option_b=q.get("b", ""),
                                option_c=q.get("c", ""), option_d=q.get("d", ""),
                                correct_option=q.get("answer", "").lower(),
                                marks=q.get("marks", 1), extra_content=q.get("extra_content"),
                                image=q.get("image")))
            db.commit()
            flash(f"✅ Uploaded quiz with {len(questions)} question(s).", "success")

            # Pass quiz.id to template so we can show the review link
            return render_template('admin/upload_exams.html', courses=courses, subjects=subjects, uploaded_quiz_id=quiz.id)

        return render_template('admin/upload_exams.html', courses=courses, subjects=subjects)
    finally:
        db.close()


# -----------------------------
# Videos
# -----------------------------
@app.route('/admin/upload_video', methods=['GET', 'POST'])
def upload_video():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    db = SessionLocal()
    try:
        courses, subjects = db.query(Course).all(), db.query(Subject).all()
        if request.method == 'POST':
            title = request.form['title'].strip()
            course_id, subject_id = int(request.form['course']), int(request.form['subject'])
            file = request.files.get('video_file')
            if not file or not allowed(file.filename, ALLOWED_VIDEO_EXTENSIONS):
                flash('❌ Invalid video file.', 'danger'); return redirect(request.url)

            filename = secure_filename(file.filename)
            file.save(os.path.join(VIDEOS_UPLOAD_FOLDER, filename))

            db.add(Video(title=title, course_id=course_id, subject_id=subject_id, filename=filename))
            db.commit()
            flash(f"✅ Video '{title}' uploaded!", "success")
            return redirect(url_for('upload_video'))
        return render_template('admin/upload_video.html', courses=courses, subjects=subjects)
    finally:
        db.close()

@app.route('/admin/delete_video/<int:video_id>', methods=['POST'])
def delete_video(video_id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    db = SessionLocal()
    try:
        video = db.query(Video).get(video_id)
        if not video: flash('Video not found.', 'danger'); return redirect(url_for('upload_video'))
        path = os.path.join(VIDEOS_UPLOAD_FOLDER, video.filename)
        if os.path.exists(path): os.remove(path)
        db.delete(video); db.commit()
        flash("Video deleted.", "success")
        return redirect(url_for('upload_video'))
    finally:
        db.close()


# -----------------------------
# Documents
# -----------------------------
@app.route("/admin/upload_document", methods=["GET", "POST"])
def upload_document():
    db = SessionLocal()
    try:
        courses = db.query(Course).all()
        subjects = db.query(Subject).all()

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            course_id = request.form.get("course")
            subject_id = request.form.get("subject")
            file = request.files.get("document")  # must match <input name="document">

            if not title or not course_id or not subject_id:
                flash("⚠️ Please fill in all fields.", "danger")
                return redirect(request.url)

            if not file or not allowed(file.filename, ALLOWED_DOCUMENT_EXTENSIONS):
                flash("❌ Please upload a valid document (PDF, DOC, DOCX, PPT, PPTX).", "danger")
                return redirect(request.url)

            filename = secure_filename(file.filename)
            save_path = os.path.join(DOCUMENTS_UPLOAD_FOLDER, filename)
            file.save(save_path)

            new_doc = Document(
                title=title,
                filename=filename,
                course_id=int(course_id),
                subject_id=int(subject_id),
            )
            db.add(new_doc)
            db.commit()

            flash(f"✅ Document '{title}' uploaded successfully!", "success")
            return redirect(url_for("upload_document"))

        return render_template("admin/upload_document.html", courses=courses, subjects=subjects)
    finally:
        db.close()



#-----------------------------
#student functionality
#----------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']  # plain text password

        # Create a new user in the database
        db = SessionLocal()
        user = User(username=username, password=password)
        db.add(user)
        db.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('students/student_register.html')



'''
student complete profile route
'''
@app.route('/complete_profile', methods=['GET', 'POST'])
def complete_profile():
    if 'username' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
       
        user = db.query(User).filter_by(username=session['username']).first()

        if request.method == 'POST':
            
            full_name = request.form['full_name']
            exam_type = request.form['exam_type']
            course_id = request.form['course_id']
            level = request.form['level']
            admission_number = request.form['admission_number']
            phone_number = request.form['phone_number']

           
            student_profile = StudentProfile(
                full_name=full_name,
                exam_type=exam_type,
                course_id=course_id,
                level=level,
                admission_number=admission_number,
                phone_number=phone_number,
                user_id=user.id  
            )

            
            db.add(student_profile)
            db.commit()

            flash('Profile completed successfully!', 'success')
            return redirect(url_for('student_dashboard'))  

        
        courses = db.query(Course).all()  
        return render_template('students/complete_profile.html', courses=courses)

    finally:
        db.close()

'''
student dashboard
'''

@app.route('/student/dashboard')
def student_dashboard():
    if 'username' not in session or session.get('role') != 'student':
        flash('Please log in as a student first.', 'error')
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username=session['username']).first()
        if not user:
            flash("User not found.", "error")
            return redirect(url_for('logout'))

        student_profile = db.query(StudentProfile).filter_by(user_id=user.id).first()
        if not student_profile:
            flash("Complete your profile before proceeding.", "warning")
            return redirect(url_for('complete_profile'))

        # Get available quizzes for student's course
        available_quizzes = db.query(Quiz).filter_by(course_id=student_profile.course_id, status='active').all()
        student_profile=db.query(StudentProfile).filter_by(user_id=user.id).first()

        # Get quizzes already taken by the student
        taken_quiz_ids = set(
            r.quiz_id for r in db.query(Result).filter_by(student_id=user.id).all()
        )

        available_videos = db.query(Video).filter_by(course_id=student_profile.course_id).all()
        available_documents = db.query(Document).filter_by(course_id=student_profile.course_id).all()

        return render_template(
            'students/student_dashboard.html',
            username=user.username,
            quizzes=available_quizzes,
            videos=available_videos,
            documents=available_documents,
            taken_quiz_ids=taken_quiz_ids ,
            student_profile=student_profile
        )
    finally:
        db.close()

'''
doucments and videos
'''
@app.route('/view_document/<int:document_id>')
def view_document(document_id):
    db = SessionLocal()  
    student = db.query(StudentProfile).filter_by(user_id=session['user_id']).first()  
    
    if student and student.blocked:
        flash("You can't access this material. Please clear the fee to regain access.", "danger")
        return redirect(url_for('student_dashboard'))  
    
    document = db.query(Document).filter(Document.id == document_id).first()

    if document:
        document_path = os.path.join(DOCUMENTS_UPLOAD_FOLDER, document.filename)
        
        # Get file extension
        file_extension = document.filename.split('.')[-1].lower()

        if file_extension == 'pdf':
            return render_template('students/view_document.html', document=document, is_pdf=True)
        elif file_extension in ['docx', 'doc', 'pptx', 'ppt']:
            return render_template('students/view_document.html', document=document, is_pdf=False)
        else:
            return "Unsupported file type", 404
    else:
        return "Document not found", 404

@app.route('/watch_video/<int:video_id>')
def watch_video(video_id):
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        student = db.query(StudentProfile).filter_by(user_id=session['user_id']).first()
        if not student:
            flash("Student profile not found.", "danger")
            return redirect(url_for('student_dashboard'))

        # Check if student is blocked
        if student.blocked:
            flash("You can't access this material. Please clear the fee to regain access.", "danger")
            return redirect(url_for('student_dashboard'))

        # Fetch the video
        video = db.query(Video).filter_by(id=video_id).first()
        if not video:
            return "Video not found", 404

        return render_template('students/watch_video.html', video=video)

    finally:
        db.close()



from sqlalchemy.orm import joinedload
from sqlalchemy import or_

@app.route('/manage_students', methods=['GET', 'POST'])
def manage_students():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    db = SessionLocal()

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        action = request.form.get('action')
        student = db.query(StudentProfile).get(student_id)

        if action == 'toggle_block' and student:
            student.blocked = not student.blocked
            db.commit()

        elif action == 'delete' and student:
            # Delete associated user first
            user = student.user
            if user:
                db.delete(user)
            db.delete(student)
            db.commit()

        return redirect(url_for('manage_students'))

    # GET method: handle search query
    search_query = request.args.get('search', '').strip()

    if search_query:
        students = db.query(StudentProfile).filter(
            or_(
                StudentProfile.full_name.ilike(f'%{search_query}%'),
                StudentProfile.exam_type.ilike(f'%{search_query}%'),
                StudentProfile.admission_number.ilike(f'%{search_query}%'),
                StudentProfile.phone_number.ilike(f'%{search_query}%'),
                StudentProfile.course.has(name=search_query)
            )
        ).all()
    else:
        students = db.query(StudentProfile).all()

    return render_template('admin/manage_students.html', students=students, search_query=search_query)




'''
show username and pasword
'''
from sqlalchemy.orm import joinedload
@app.route('/show_credentials')
def show_credentials():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        
        users = db.query(User).options(joinedload(User.student_profile)).all()
    finally:
        db.close()

    return render_template('admin/show_credentials.html', users=users)

@app.route('/student/take_exam/<int:quiz_id>', methods=['GET', 'POST'])
def take_exam(quiz_id):
    if 'username' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username=session['username']).first()
        if not user:
            flash("User not found.", "error")
            return redirect(url_for('logout'))

        quiz = db.query(Quiz).filter_by(id=quiz_id).first()
        if not quiz:
            flash("Quiz not found.", "error")
            return redirect(url_for('student_dashboard'))

        # Check for retake here
        existing_result = db.query(Result).filter_by(student_id=user.id, quiz_id=quiz.id).first()
        if existing_result:
            flash("You have already taken this exam. Retakes are not allowed.", "warning")
            return redirect(url_for('student_results', result_id=existing_result.id))

        questions = db.query(Question).filter_by(quiz_id=quiz.id).all()

        if request.method == 'POST':
            answers = request.form
            total_score = 0
            total_marks = 0

            for question in questions:
                selected_answer = answers.get(f"question_{question.id}")
                print(f"Selected answer for question {question.id}: {selected_answer} | Correct answer: {question.correct_option}")

                if selected_answer and selected_answer.upper() == question.correct_option.upper():
                    total_score += question.marks

                total_marks += question.marks

            percentage = round((total_score / total_marks) * 100) if total_marks else 0

            result = Result(  
                student_id=user.id,
                quiz_id=quiz.id,
                score=total_score,
                total_marks=total_marks,
                percentage=percentage
            )
            db.add(result)
            db.commit()

            flash(f'✅ You scored {total_score} out of {total_marks} ({percentage}%)', 'success')

            return redirect(url_for('student_results', result_id=result.id))

        return render_template('students/take_exam.html', quiz=quiz, questions=questions)

    except Exception as e:
        db.rollback()
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('student_dashboard'))
    finally:
        db.close()


'''
results
'''
@app.route('/student/results')
def student_results():
    if 'username' not in session or session.get('role') != 'student':
        flash('Please log in as a student first.', 'error')
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username=session['username']).first()
        if not user:
            flash("User not found.", "error")
            return redirect(url_for('logout'))

        # Retrieve student's results
        results = (
            db.query(Result)
              .join(Quiz, Result.quiz_id == Quiz.id)
              .filter(Result.student_id == user.id)
              .all()
        )

        return render_template('students/results.html', results=results)

    finally:
        db.close()


'''
admin view all results  
'''
@app.route('/admin/view_results', methods=['GET', 'POST'])
def view_results():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Admin access required", "danger")
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        courses = db.query(Course).all()
        subjects = db.query(Subject).all()

        selected_course = request.form.get('course')
        selected_subject = request.form.get('subject')
        export = request.form.get('export')

        # Query setup
        query = db.query(Result).join(Result.quiz).join(Quiz.course).join(Quiz.subject).join(Result.student)

        if selected_course:
            query = query.filter(Quiz.course_id == int(selected_course))
        if selected_subject:
            query = query.filter(Quiz.subject_id == int(selected_subject))

        results = query.all()

        # Export to Excel
        if export == 'true':
            data = []
            for r in results:
                data.append({
                    'Student Username': r.student.username,
                    'Full Name': r.student.profile.full_name if r.student.profile else 'N/A',
                    'Course': r.quiz.course.name if r.quiz.course else 'N/A',
                    'Subject': r.quiz.subject.name if r.quiz.subject else 'N/A',
                    'Quiz Title': r.quiz.title,
                    'Score': r.score,
                    'Total Marks': r.total_marks,
                    'Percentage': r.percentage,
                    'Taken On': r.taken_on.strftime("%Y-%m-%d %H:%M:%S")
                })

            df = pd.DataFrame(data)
            excel_path = os.path.join(EXAMS_UPLOAD_FOLDER, 'quiz_results.xlsx')
            df.to_excel(excel_path, index=False)

            return send_file(
                excel_path,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='quiz_results.xlsx'
            )

        return render_template('admin/view_results.html',
                               results=results,
                               courses=courses,
                               subjects=subjects,
                               selected_course=selected_course,
                               selected_subject=selected_subject)

    finally:
        db.close()

'''
manage quizzes
'''
@app.route('/admin/manage_quizzes', methods=['GET', 'POST'])
def manage_quizzes():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        if request.method == 'POST':
            quiz_id = int(request.form.get('quiz_id'))
            action = request.form.get('action')

            quiz = db.query(Quiz).filter_by(id=quiz_id).first()
            if not quiz:
                flash("Quiz not found.", "danger")
                return redirect(url_for('manage_quizzes'))

            if action == 'activate':
                quiz.status = 'active'
            elif action == 'deactivate':
                quiz.status = 'inactive'

            db.commit()
            flash(f"Quiz '{quiz.title}' has been {quiz.status}.", "success")
            return redirect(url_for('manage_quizzes'))

        quizzes = db.query(Quiz).all()
        return render_template('admin/manage_quizzes.html', quizzes=quizzes)
    finally:
        db.close()

'''
delete quiz
'''

@app.route('/admin/delete_quiz/<int:quiz_id>', methods=['POST'])
def delete_quiz(quiz_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    db = SessionLocal()
    quiz = db.query(Quiz).filter_by(id=quiz_id).first()
    if quiz:
        db.delete(quiz)
        db.commit()
        flash('Quiz deleted successfully.', 'success')
    else:
        flash('Quiz not found.', 'danger')
    return redirect(url_for('manage_quizzes')) 

'''
confirm and delete exams
'''
@app.route('/admin/review_quiz/<int:quiz_id>', methods=['GET', 'POST'])
def review_uploaded_quiz(quiz_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        quiz = db.query(Quiz).filter_by(id=quiz_id).first()
        if not quiz:
            flash("Quiz not found.", "danger")
            return redirect(url_for('upload_exam'))

        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'delete':
                # Delete questions
                db.query(Question).filter_by(quiz_id=quiz.id).delete()
                # Delete quiz
                db.delete(quiz)
                db.commit()
                flash("❌ Quiz deleted.", "warning")
                return redirect(url_for('upload_exam'))

            elif action == 'confirm':
                flash("✅ Quiz confirmed and saved.", "success")
                return redirect(url_for('upload_exam'))

        questions = db.query(Question).filter_by(quiz_id=quiz.id).all()
        return render_template('admin/review_uploaded_quiz.html', quiz=quiz, questions=questions)
    finally:
        db.close()


'''
toggle document active/inactive
'''
@app.route("/admin/document/<int:doc_id>/toggle")
def toggle_document_status(doc_id):
    db = SessionLocal()
    try:
        document = db.query(Document).filter_by(id=doc_id).first()
        if document:
            document.is_active = not document.is_active
            db.commit()
            flash("✅ Document status updated.", "success")
        else:
            flash("❌ Document not found.", "danger")
    finally:
        db.close()
    return redirect(url_for("list_documents"))
'''
delete document
'''
@app.route("/admin/document/<int:doc_id>/delete", methods=["POST"])
def delete_document(doc_id):
    db = SessionLocal()
    try:
        document = db.query(Document).filter_by(id=doc_id).first()
        if document:
            # Delete file from disk
            filepath = os.path.join(DOCUMENTS_UPLOAD_FOLDER, document.filename)
            if os.path.exists(filepath):
                os.remove(filepath)

            db.delete(document)
            db.commit()
            flash("🗑️ Document deleted successfully.", "success")
        else:
            flash("❌ Document not found.", "danger")
    finally:
        db.close()
    return redirect(url_for("list_documents"))
'''
admin view uploaded video
'''
@app.route('/admin/videos')
def list_videos():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    db = SessionLocal()
    try:
        videos = db.query(Video).all()
        return render_template('admin/list_videos.html', videos=videos)
    finally:
        db.close()
'''
List document
'''




# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
