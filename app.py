""" APP Class"""
import os
import random
import flask
from flask_cors import CORS, cross_origin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from dotenv import find_dotenv, load_dotenv
from flask_wtf import FlaskForm
from flask import jsonify, request, session
from flask_wtf.csrf import CSRFProtect
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from jose import JWTError, jwt
from twilio.rest import Client
from movie import trendingMoviesOfTheYear
import sshtunnel



app = flask.Flask(__name__)
CORS(app)
load_dotenv(find_dotenv())
app = flask.Flask(__name__)
from datetime import timedelta
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('LOCAL_DATABASE_URL')
app.config['SECRET_KEY'] = os.getenv('secretKey')
db = SQLAlchemy(app)
app.config['JWT_SECRET_KEY'] = 'your_secret_key'  # Replace with a strong secret key
jwt = JWTManager(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token = os.environ["TWILIO_AUTH_TOKEN"]
VERIFY_SERVICE_SID = os.getenv("VERIFY_SERVICE_SID")
client = Client(account_sid, auth_token)
from wtforms import StringField, PasswordField, IntegerField
from wtforms.validators import InputRequired, Email, Length



class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    phone = db.Column(db.String(30), nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Comments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name= db.Column(db.String(50), nullable=False)
    email =  db.Column(db.String(100), nullable=False)
    movieId = db.Column(db.String(100), nullable=False)
    comment = db.Column(db.String(400), nullable=False)
    like = db.Column(db.Integer, nullable=True, default=0)
    dislike = db.Column(db.Integer, nullable=True, default=0)


class UserList(db.Model):
    id = db.Column(db.Integer, primary_key=True)# pylint: disable=trailing-whitespace
    email =  db.Column(db.String(100), nullable=False)
    favorites = db.Column(db.String(200), nullable=True) 
    bookmarked = db.Column(db.String(200), nullable=True)


class Expired_token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(1000), nullable=False)
    expired = db.Column(db.Boolean, nullable=False)


def send_verification_code(phone):
    """sends varification code to user via phone number"""
    verification = client.verify.services(VERIFY_SERVICE_SID).verifications.create(
        to=phone, channel="sms"
    )
    return verification.status


def check_verification_token(phone, token):
    """checks varification code of user via phone number"""
    verification_check = client.verify.services(
        VERIFY_SERVICE_SID
    ).verification_checks.create(to=phone, code=token)
    if verification_check.status == "approved":
        return True
    # elif verification_check.status == "pending":
    return False

@app.route('/register', methods=['POST'])
@cross_origin()
def register():
    if request.is_json:
        data = request.json
        hashed_password = generate_password_hash(data['Password'], method='pbkdf2:sha256')
        existing_user = Users.query.filter_by(email=data['Email']).first()
        if existing_user:
            return jsonify({"message": "User Already Exists"}), 400
        new_user = Users(
            name=data['Name'],
            email=data['Email'],
            phone=data['Phone'],
            password=hashed_password,
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "Registration successful"}), 201
    else:
        return jsonify({"error": "Invalid content type, expected JSON"}), 400
    

@app.route('/login', methods=['POST'])
@cross_origin()
def login():
    if request.is_json:
        data = request.json
        user = Users.query.filter_by(email=data['Email']).first()
        
        if user:
            if check_password_hash(user.password, data['Password']):
                email = data['Email'];
                access_token = create_access_token(identity=email, expires_delta=timedelta(hours=4))
                is_token = Expired_token.query.filter_by(token=access_token).first();
                if not is_token:
                    new_token = Expired_token(
                        token=access_token,
                        expired=False
                    )
                    db.session.add(new_token)
                    db.session.commit()
                    token_serilized = {
                        "token": new_token.token,
                        "expired": new_token.expired
                    }
                    return jsonify(access_token=token_serilized), 200
            else:
                return jsonify({"message": "Login failed"}), 401
        else:
            return jsonify({"message": "User Does not exist failed"}), 401
    else:
        return jsonify({"error": "Invalid content type, expected JSON"}), 400
    

@app.route('/addComment', methods=['POST'])
@cross_origin()
@jwt_required()
def add_comment():
    if request.is_json:
        data = request.json
        current_user = get_jwt_identity()
        user = Users.query.filter_by(email=current_user).first();
        new_comment = Comments(
            name=user.name,
            email=current_user,
            movieId=data['movieId'],
            comment=data['comment'],
        )
        db.session.add(new_comment)
        db.session.commit()
        return jsonify({"message": "Comment Added  Successful"}), 201
    else:
        return jsonify({"error": "Invalid content type, expected JSON"}), 400
    

@app.route('/addToUserList', methods=['POST'])
@cross_origin()
@jwt_required()
def add_to_user_list():
    if request.is_json:
        data = request.json
        if data['favorite'] == None or data['bookmark'] == None:
            return jsonify({"error": "Null data is not excepted"}), 404
        current_user = get_jwt_identity()
        user_list_exists = UserList.query.filter_by(email=current_user).first()
        if user_list_exists:
            return jsonify({"error": "User List already exists"}), 404
        new_userlist = UserList(
            email=current_user,
            favorites=data['favorite'],
            bookmarked=data['bookmark'],
        )
        db.session.add(new_userlist)
        db.session.commit()
        return jsonify({"message": "User List Added  Successful"}), 201
    else:
        return jsonify({"error": "Invalid content type, expected JSON"}), 400




@app.route('/deleteUserList', methods=['DELETE'])
@cross_origin()
@jwt_required()
def delete_user_list():
    current_user = get_jwt_identity()
    user_list_exists = UserList.query.filter_by(email=current_user).first()
    if not user_list_exists:
        return jsonify({"error": "User List does not exists"}), 404
    db.session.delete(user_list_exists)
    db.session.commit()
    return jsonify({"message": "User List Deleted  Successful"}), 201
    
@app.route('/getUser', methods=['GET'])
@cross_origin()
@jwt_required()
def get_user():
    current_user = get_jwt_identity()
    user_exists = Users.query.filter_by(email=current_user).first()
    if not user_exists:
        return jsonify({"error": "User List does not exists"}), 404
    
    user_json_serialized = {
        "id": user_exists.id,
        "name": user_exists.name,
        "email": user_exists.email,
        "phone": user_exists.phone,
    }
    return jsonify({"Data": user_json_serialized}), 201

@app.route('/updateUserList', methods=['PUT'])
@cross_origin()
@jwt_required()
def update_user_list():
    if request.is_json:
        data = request.json
        current_user = get_jwt_identity()
        user_list_exists = UserList.query.filter_by(email=current_user).first()
        if not user_list_exists:
            return jsonify({"error": "User List does not exist"}), 404
        user_list_exists.favorites = user_list_exists.favorites + "," + data['favorite'] if user_list_exists.favorites else (user_list_exists.favorites + data['favorite'])
        user_list_exists.bookmarked = user_list_exists.bookmarked + "," + data['bookmark'] if user_list_exists.bookmarked else (user_list_exists.bookmarked + data['bookmark'])
        db.session.commit()
        return jsonify({"message": "User List Updated  Successful"}), 201
    else:
        return jsonify({"error": "Invalid content type, expected JSON"}), 400

@app.route('/deleteFromUserList', methods=['PUT'])
@cross_origin()
@jwt_required()
def delete_from_user_list():
    if request.is_json:
        data = request.json
        current_user = get_jwt_identity()
        user_list_exists = UserList.query.filter_by(email=current_user).first()
        if not user_list_exists:
            return jsonify({"error": "User List does not exist"}), 404
        
        fav = data['favorite']
        fav_list = user_list_exists.favorites.split(',')
        fav_list.remove(fav)
        updated_fav = ",".join(fav_list)

        bookmarks = data['bookmark']
        bookmarks_list = user_list_exists.bookmarked.split(',')
        bookmarks_list.remove(bookmarks)
        updated_bookmark = ",".join(bookmarks_list)

        user_list_exists.favorites = updated_fav;
        user_list_exists.bookmarked = updated_bookmark;
        db.session.commit()
        return jsonify({"message": "Deleted from user List Successful"}), 201
    else:
        return jsonify({"error": "Invalid content type, expected JSON"}), 400

@app.route('/getComments/<int:movieId>', methods=['GET'])
@cross_origin()
def get_comments(movieId):
    comments = Comments.query.filter_by(movieId=movieId).all();
    if not comments:
        return jsonify({"error": "Error getting movie"}), 404
    comments_list = []
    for comment in comments:
        comment_dict = {
            'id': comment.id,
            'email': comment.email,
            'movieId': comment.movieId,
            'comment': comment.comment,
            'like': comment.like,
            'dislike': comment.dislike,
            'name': comment.name,
        }
        comments_list.append(comment_dict)

    return jsonify({"comments": comments_list}), 200

# @app.route('/getUserList', methods=['GET'])
# @cross_origin()
# @jwt_required()
# def get_user_list():
#     current_user = get_jwt_identity()
#     user_list = UserList.query.filter_by(email=current_user).all()
    
#     user_list_list = []
#     for user_l in user_list:
#         user_list_dict = {
#             'id': user_l.id,
#             'email': user_l.email,
#             'favorites': user_l.favorites,
#             'bookmarked': user_l.bookmarked,
       
#         }
#         user_list_list.append(user_list_dict)

#     return jsonify({"comments": user_list_list}), 200

@app.route('/editComment/<int:id>', methods=['PUT'])
@cross_origin()
@jwt_required()
def edit_comment(id):
    if request.is_json:
        data = request.json
        if data['comment'] == "" or data['comment'] == None:
            return jsonify({"error": "Invalid data"}), 400
        edited_comment = Comments.query.filter_by(id=id).first()
        if not edited_comment:
            return jsonify({"error": "Comment not found"}), 404
        edited_comment.comment = data['comment'];
        db.session.commit()
        return jsonify({"message": "Comment updated successfully"}), 200
    else:
        return jsonify({"error": "Invalid content type, expected JSON"}), 400

@app.route('/updateLike/<int:id>', methods=['PUT'])
@cross_origin()
@jwt_required()
def edit_like(id):
    comment_like_update = Comments.query.filter_by(id=id).first()
    if not comment_like_update:
        return jsonify({"error": "Comment not found"}), 404
    comment_like_update.like = comment_like_update.like + 1;
    db.session.commit()
    return jsonify({"message": "Comment like updated successfully"}), 200

    
@app.route('/updateDisLike/<int:id>', methods=['PUT'])
@cross_origin()
@jwt_required()
def edit_dislike(id):
    comment_like_update = Comments.query.filter_by(id=id).first()
    if not comment_like_update:
        return jsonify({"error": "Comment not found"}), 404
    comment_like_update.dislike = comment_like_update.dislike + 1;
    db.session.commit()
    return jsonify({"message": "Comment dislike updated successfully"}), 200


@app.route('/deleteComment/<int:id>', methods=['DELETE'])
@cross_origin()
@jwt_required()
def delete_comment(id):
    delete_comment = Comments.query.filter_by(id=id).first()
    if not delete_comment:
        return jsonify({"error": "Comment not found"}), 404
    db.session.delete(delete_comment)
    db.session.commit()
    return jsonify({"message": "Comment deleted successfully"}), 200


@app.route('/getUserList', methods=['GET'])
@cross_origin()
@jwt_required()
def get_user_list():
    current_user = get_jwt_identity()
    user_list_exists = UserList.query.filter_by(email=current_user).first();
    if not user_list_exists:
        return jsonify({"error": "userlist not found"}), 404
    
    user_list_exists_serialized = {
        "email" : user_list_exists.email,
        "favorites": user_list_exists.favorites,
        # "bookmarked": user_list_exists.bookmarked,
    }
    return jsonify({"message": user_list_exists_serialized}), 200


@app.route('/resetPassword', methods=['POST'])
@cross_origin()
def reset_password():
    if request.is_json:
        data = request.json
        current_user = data['email']
        user = Users.query.filter_by(email=current_user).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        try:
            send_verification_code(user.phone)
            return jsonify({"status": "verification code sent"}), 200
        except Exception as e:
            return jsonify({"status": "Something went wrong"}), 400
    else:
        return jsonify({"error": "Invalid content type, expected JSON"}), 400


@app.route('/verifyCode', methods=['POST'])
@cross_origin()
def verify_verification_code():
    if request.is_json:
        data = request.json
        user = Users.query.filter_by(email=data['email']).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        status = check_verification_token(user.phone, data['verification_code'])   
        if not status:
            return jsonify({"message": "Incorrect code"}), 400     
        return jsonify({"message": "verification successful"}), 200
    else:
        return jsonify({"error": "Invalid content type, expected JSON"}), 400

@app.route('/updateUserPassword', methods=['PUT'])
@cross_origin()
def update_user_password():
    if request.is_json:
        data = request.json
        current_user = data['email']
        user = Users.query.filter_by(email=current_user).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        if data['password'] == "" or data['password'] == None:
            return jsonify({"error": "Invalid password"}), 404
        hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
        user.password = hashed_password;
        db.session.commit()
        return jsonify({"message": "Password updated  Successful"}), 201
    else:
        return jsonify({"error": "Invalid content type, expected JSON"}), 400


@app.route('/expiredToken', methods=['PUT'])
@cross_origin()
@jwt_required()
def expired_token():
    if request.is_json:
        data = request.json
        expired_toke = data['token']
        token_data = Expired_token.query.filter_by(token=expired_toke).first();
        if token_data:
            token_data.expired = True;
            db.session.commit()
        return jsonify({"error": "Token has Expired"}), 200
    else:
        return jsonify({"error": "Invalid content type, expected JSON"}), 400
    

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(
        host=os.getenv('IP', '0.0.0.0'),
        port=int(os.getenv('PORT', 8080)),
        debug=True
    )