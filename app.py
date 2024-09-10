from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///daily_chess.db'
app.config['SECRETE_KEY'] = 'secrete_key'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
db = SQLAlchemy(app)
CORS(app)

class Puzzle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fen = db.Column(db.String(100), nullable=False) #FEN representation
    solution = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    hint = db.Column(db.String(200))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    puzzle_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    attempts = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

class HintSolutionUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    puzzle_id = db.Column(db.Integer, db.ForeignKey('puzzle.id'), nullable=False)
    date = db.Column(db.Integer, nullable=False)
    hints_used = db.Column(db.Integer, default=0)
    solution_revealed = db.Column(db.Boolean, default=False)

@app.route('/')
def index():
    today = date.today()
    difficulty = request.args.get('difficulty', 'all')
    #Fetch random puzzle that hasn't been used in the last 30 days
    puzzle = Puzzle.query.filter(
        ~db.exists().where(Score.puzzle_id == Puzzle.id, Score.date >= today - timedelta(days=30))
    ).order_by(db.func.random()).first()

    if difficulty != 'all':
        query = query.filter_by(difficulty=difficulty)

        puzzle = query.order_by(db.func.random()).first()
    if not puzzle:
        #Handle case where no new puzzles are available
        return render_template('no_puzzles.html')
    
    # Convert the puzzle object to a dictionary before passing it to the template
    puzzle_dict = {
        'fen': puzzle.fen,
        'id': puzzle.id
    }
    
    return render_template('index.html', puzzle=puzzle_dict)

@app.route('/get_chess_piece_image')
def get_chess_piece_image():
    piece_type = request.args.get('piece')

    # Chess.com image URLs follow a specific pattern
    image_url = f'https://images.chesscomfiles.com/chess-themes/pieces/neo/150/{piece_type}.png' 

    # Fetch the image from chess.com (optional, for error handling)
    try:
        response = requests.get(image_url)
        response.raise_for_status()  # Raise an exception for bad responses
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Failed to fetch image'}), 500

    return jsonify({'image_url': image_url})

@app.route('/update_score/<int:puzzle_id>', methods=['POST'])
@login_required #Ensure user is logged in
def update_score(puzzle_id):
    #Check if the user has already solved this puzzle today
    existing_score = Score.query.filter_by(user_id=current_user.id, puzzle_id=puzzle_id, date=date.today()).first()

    if existing_score:
        existing_score.attempts += 1
    else:
        new_score = Score(user_id=current_user.id, puzzle_id=puzzle_id, attempts=1)
        db.session.add(new_score)

    usage = HintSolutionUsage.query.filter_by(
        user_id=current_user.id, puzzle_id=puzzle_id, date=today
    ).first()

    if usage and (usage.hints_used > 0 or usage.solution_revealed):
        #Add the penalty as needed
        existing_score.attempts += 2

    db.session.commit()
    return jsonify({'success':True})

@app.route('/leaderboard')
def leaderboard():
    #Calculate scores for each user
    scores = db.sessions.query(
        User.username,
        db.func.count(Score.id).lable('puzzles_solved'), #Count solved puzzles
        db.func.sum(Score.attempts).lable('total_attempts')
    ).join(Score).group_by(User.id).order_by('total_attempts', 'puzzles_solved DESC').all()

    return render_template('leaderboard.html', scores=scores)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)

            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)

        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/get_hint/<int:puzzle_id>')
@login_required
def get_hint(puzzle_id):
    puzzle = Puzzle.query.get_or_404(puzzle_id)
    return jsonify({'hint': puzzle.hint})

@app.route('/get_solution/<int:puzzle_id>')
@login_required
def get_solution(puzzle_id):
    # Check if the user has exceeded the limit for hints or solutions
    usage = HintSolutionUsage.query.filter_by(
    user_id=current_user.id, puzzle_id=puzzle_id, date=today
    ).first()

    if not usage:
        usage = HintSolutionUsage(user_id=current_user.id, puzzle_id=puzzle_id, date=today)
        db.session.add(usage)

    if (request.path == f'/get_hint/{puzzle_id}' and usage.hints_used >= 3) or \
        (request.path == f'/get_solution/{puzzle_id}' and usage.solution_revealed):
        return jsonify({'error': 'Limit exceeded'}), 400  # Return an error if limit is exceeded

# Update usage and commit changes
    if request.path == f'/get_hint/{puzzle_id}':
        usage.hints_used += 1
    elif request.path == f'/get_solution/{puzzle_id}':
        usage.solution_revealed = True

    db.session.commit()
    puzzle =Puzzle.query.get_or_404(puzzle_id)
    return jsonify({'solution': puzzle.soution})

if __name__ == '__main__':
    app.run(debug=True)