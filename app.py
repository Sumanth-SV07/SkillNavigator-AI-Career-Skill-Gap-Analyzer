from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from roadmap_data import roadmaps
from PyPDF2 import PdfReader
import os
from skill_categories import skill_categories
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from skill_database import skills_db
from resource_links import resources




app = Flask(__name__)
app.secret_key = "talentlens"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['UPLOAD_FOLDER'] = 'uploads'

db = SQLAlchemy(app)



# ---------------------DATABASE MODEL--------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    password = db.Column(db.String(100))

with app.app_context():
    db.create_all()



#-----------------------------HOME------------------------------
@app.route('/')
def home():
    return render_template('index.html')



# ----------------------------------REGISTER----------------------------------
@app.route('/register', methods=['GET','POST'])
def register():

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        new_user = User(username=username, password=password)

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')




# ---------------------------LOGIN-----------------------------
@app.route('/login', methods=['GET','POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username, password=password).first()

        if user:
            session['user'] = user.username
            return redirect(url_for('dashboard'))

    return render_template('login.html')




#---------------------------------------- DASHBOARD-------------------------------------------
@app.route('/dashboard', methods=['GET','POST'])
def dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':

        session['branch'] = request.form['branch']
        session['goal'] = request.form['goal']
        session['level'] = request.form['level']
        session['learning'] = request.form['learning']

        return redirect(url_for('upload'))

    return render_template('dashboard.html')




#---------------------------------- UPLOAD RESUME-----------------------------------------
@app.route('/upload', methods=['GET','POST'])
def upload():

    if request.method == 'POST':

        file = request.files['resume']

        if file:

            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            reader = PdfReader(filepath)

            text = ""

            for page in reader.pages:
                text += page.extract_text()

            session['skills_text'] = text.lower()

            return redirect(url_for('result'))

    return render_template('upload.html')



# ------------------------------MANUAL ENTRY----------------------------------------
@app.route('/manual', methods=['GET','POST'])
def manual():

    if request.method == 'POST':

        skills = request.form['skills']

        session['skills_text'] = skills.lower()

        return redirect(url_for('result'))

    return render_template('manual_entry.html')



#--------------------------- RESULT---------------------------------------
@app.route('/result')
def result():

    goal = session.get('goal')
    user_skills = session.get('skills_text','')

    required = skills_db.get(goal, [])

    found = []
    missing = []

    for skill in required:
        if skill.lower() in user_skills:
            found.append(skill)
        else:
            missing.append(skill)

    # GRAPH
    values = [len(found), len(missing)]
    labels = ['Found','Missing']

    plt.bar(labels, values)
    plt.title("Skill Gap Analysis")

    # Create unique graph name
    graph_path = f"static/graph_{session.get('user')}.png"

    plt.savefig(graph_path)
    plt.close()

    # Resources
    links = {}
    for skill in missing:
        links[skill] = resources.get(skill, ["https://www.google.com/search?q=" + skill + "+course"])

# -------- Skill Priority --------

    high_priority = []
    medium_priority = []
    low_priority = []

    for skill in missing:

      if skill in required[:5]:
        high_priority.append(skill)

      elif skill in required[5:10]:
        medium_priority.append(skill)

      else:
        low_priority.append(skill)

    # Roadmap
    roadmap = roadmaps.get(goal, [])

    # Progress
    total_skills = len(found) + len(missing)

    if total_skills > 0:
        progress = int((len(found) / total_skills) * 100)
    else:
        progress = 0

    # -------- SKILL CATEGORY FILTER --------

    filtered_categories = {}

    for category, skills in skill_categories.items():

        role_skills = []

        for skill in skills:
            if skill in required:
                role_skills.append(skill)

        if role_skills:
            filtered_categories[category] = role_skills

    return render_template(
        "result.html",
        username=session.get('user'),
        branch=session.get('branch'),
        goal=session.get('goal'),
        level=session.get('level'),
        learning=session.get('learning'),
        found=found,
        missing=missing,
        graph=graph_path,
        resources=links,
        roadmap=roadmap,
        progress=progress,
        categories=filtered_categories,
        high_priority=high_priority,
        medium_priority=medium_priority,
        low_priority=low_priority
    )


#--------------------- LOGOUT--------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)