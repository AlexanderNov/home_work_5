from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'YYVX9-NTFWV-6MDM3-9PT4T-4M68B'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reviews.db'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    reviews = db.relationship('Review', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    votes = db.relationship('Vote', backref='user', lazy=True)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    pros = db.Column(db.Text, nullable=False)
    cons = db.Column(db.Text, nullable=False)
    opinion = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    comments = db.relationship('Comment', backref='review', lazy=True)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    review_id = db.Column(db.Integer, db.ForeignKey('review.id'), nullable=False)


class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    review_id = db.Column(db.Integer, db.ForeignKey('review.id'), nullable=False)
    vote_type = db.Column(db.Boolean, nullable=False)  # True = like, False = dislike


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=50)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class ReviewForm(FlaskForm):
    product_name = StringField('Product Name', validators=[DataRequired()])
    pros = TextAreaField('Pros', validators=[DataRequired()])
    cons = TextAreaField('Cons', validators=[DataRequired()])
    opinion = TextAreaField('Overall Opinion', validators=[DataRequired()])
    submit = SubmitField('Submit Review')


class CommentForm(FlaskForm):
    text = TextAreaField('Comment', validators=[DataRequired()])
    submit = SubmitField('Post Comment')


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route('/')
def index():
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    return render_template('index.html', reviews=reviews)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, password=form.password.data)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.password == form.password.data:
            login_user(user)
            return redirect(url_for('index'))
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/review/create', methods=['GET', 'POST'])
@login_required
def create_review():
    form = ReviewForm()
    if form.validate_on_submit():
        review = Review(
            product_name=form.product_name.data,
            pros=form.pros.data,
            cons=form.cons.data,
            opinion=form.opinion.data,
            author=current_user
        )
        db.session.add(review)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('create_review.html', form=form)


@app.route('/review/<int:id>')
def review_detail(id):
    review = Review.query.get_or_404(id)
    form = CommentForm()
    return render_template('review_detail.html', review=review, form=form)


@app.route('/review/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_review(id):
    review = Review.query.get_or_404(id)
    if review.author != current_user:
        return redirect(url_for('index'))
    form = ReviewForm(obj=review)
    if form.validate_on_submit():
        form.populate_obj(review)
        db.session.commit()
        return redirect(url_for('review_detail', id=id))
    return render_template('edit_review.html', form=form, review=review)


@app.route('/review/<int:id>/delete', methods=['POST'])
@login_required
def delete_review(id):
    review = Review.query.get_or_404(id)
    if review.author != current_user:
        return redirect(url_for('index'))
    db.session.delete(review)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/review/<int:id>/comment', methods=['POST'])
@login_required
def add_comment(id):
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(
            text=form.text.data,
            author=current_user,
            review_id=id
        )
        db.session.add(comment)
        db.session.commit()
    return redirect(url_for('review_detail', id=id))


@app.route('/review/<int:id>/vote/<string:vote_type>', methods=['POST'])
@login_required
def vote(id, vote_type):
    review = Review.query.get_or_404(id)
    existing_vote = Vote.query.filter_by(user_id=current_user.id, review_id=id).first()

    if existing_vote:
        if existing_vote.vote_type != (vote_type == 'like'):
            review.likes += 1 if vote_type == 'like' else -1
            review.dislikes += 1 if vote_type == 'dislike' else -1
            existing_vote.vote_type = (vote_type == 'like')
    else:
        vote = Vote(
            user_id=current_user.id,
            review_id=id,
            vote_type=(vote_type == 'like')
        )
        db.session.add(vote)
        review.likes += 1 if vote_type == 'like' else 0
        review.dislikes += 1 if vote_type == 'dislike' else 0

    db.session.commit()
    return redirect(url_for('review_detail', id=id))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False)
