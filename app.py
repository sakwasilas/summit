from flask import Flask, render_template, request, redirect, url_for, session
from models import User, Admin
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
    return render_template('admin/admin_dashboard.html', username=session.get('username'))

"""
student dashboard
"""
@app.route('/student_dashboard')
def student_dashboard():
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('login')) 
    return render_template('students/student_dashboard.html',username=session.get('username'))




@app.route('/logout')
def logout():
   
    session.pop('username', None)
    session.pop('user_id', None)
    session.pop('role', None)
    
    
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
