from fastapi import FastAPI, HTTPException, Depends, status
from database import db
from models import User, Swipe, Match, Message, ForumPost, TrainingPlan
from bson import ObjectId
from auth import verify_password, get_password_hash, create_access_token
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import timedelta, datetime
from jose import JWTError, jwt
from typing import Dict

SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


@app.get("/")
def root():
    return {"message": "SkillLink Backend is running!"}


@app.post("/register")
def register_user(user: User):
    try:
        if db.users.find_one({"email": user.email}):
            raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

        user_dict = user.dict()
        user_dict['password'] = get_password_hash(user.password)
        user_dict['_id'] = ObjectId()
        user_dict['points'] = 0
        user_dict['point_history'] = []

        db.users.insert_one(user_dict)

        return {"message": "Пользователь успешно зарегистрирован", "user_id": str(user_dict['_id'])}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка регистрации: {str(e)}")


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.users.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user['password']):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user['email']},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.users.find_one({"email": email})
    if user is None:
        raise credentials_exception
    return user


@app.get("/users")
def get_users():
    users = list(db.users.find({}, {"_id": 0}))
    return users


@app.get("/profile/{user_id}")
def get_profile(user_id: str):
    user = db.users.find_one({"_id": ObjectId(user_id)}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/profile/{user_id}")
def update_profile(user_id: str, updated_data: dict):
    result = db.users.update_one({"_id": ObjectId(user_id)}, {"$set": updated_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Profile updated successfully."}


@app.get("/recommendation/{user_id}")
def recommend(user_id: str):
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_interests = set(user['interests'])
    all_users = db.users.find({"_id": {"$ne": ObjectId(user_id)}})

    best_match = None
    max_common = 0

    for other in all_users:
        other_interests = set(other.get('interests', []))
        common = len(user_interests & other_interests)
        if common > max_common:
            max_common = common
            best_match = other

    if best_match:
        best_match['_id'] = str(best_match['_id'])
        return best_match
    else:
        return {"message": "No suitable recommendation found."}


@app.post("/swipe")
def swipe_user(swipe: Swipe):
    if swipe.direction == "right":
        existing = db.swipes.find_one({
            "swiper_id": swipe.target_id,
            "target_id": swipe.swiper_id,
            "direction": "right"
        })
        if existing:
            db.matches.insert_one({"user1": swipe.swiper_id, "user2": swipe.target_id})
            return {"message": "It's a match!"}
    db.swipes.insert_one(swipe.dict())
    return {"message": f"Swiped {swipe.direction}"}


@app.get("/matches/{user_id}")
def get_matches(user_id: str):
    matches = list(db.matches.find({
        "$or": [{"user1": user_id}, {"user2": user_id}]
    }, {"_id": 0}))
    return matches


@app.post("/message")
def send_message(msg: Message):
    db.messages.insert_one(msg.dict())
    return {"message": "Message sent."}


@app.get("/messages/{match_id}")
def get_messages(match_id: str):
    messages = list(db.messages.find({"match_id": match_id}, {"_id": 0}))
    return messages


@app.post("/forum")
def create_forum_post(post: ForumPost):
    post_dict = post.dict()
    post_dict['reactions'] = {}
    post_dict['responses'] = []
    db.forum.insert_one(post_dict)
    return {"message": "Forum post created."}


@app.get("/forum")
def get_forum_posts():
    posts = list(db.forum.find({}, {"_id": 0}))
    return posts


@app.post("/forum/{post_id}/respond")
def respond_to_post(post_id: str, response: Dict[str, str], current_user: dict = Depends(get_current_user)):
    db.forum.update_one({"_id": ObjectId(post_id)}, {"$push": {"responses": response['response']}})
    db.users.update_one({"_id": current_user['_id']}, {"$inc": {"points": 5}, "$push": {"point_history": {"source": "forum_response", "points": 5}}})
    return {"message": "Response added and points awarded."}


@app.post("/forum/{post_id}/react")
def react_to_post(post_id: str, reaction: Dict[str, str], current_user: dict = Depends(get_current_user)):
    field = f"reactions.{reaction['reaction']}"
    db.forum.update_one({"_id": ObjectId(post_id)}, {"$inc": {field: 1}})
    db.users.update_one({"_id": current_user['_id']}, {"$inc": {"points": 2}, "$push": {"point_history": {"source": "reaction", "points": 2}}})
    return {"message": "Reaction added and points awarded."}

@app.post("/calendar/event")
def create_calendar_event(event: Dict, current_user: dict = Depends(get_current_user)):
    event['creator'] = current_user['email']
    event['created_at'] = datetime.utcnow()
    db.calendar.insert_one(event)
    return {"message": "Event created."}


@app.get("/calendar/{user_id}")
def get_user_events(user_id: str):
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    events = list(db.calendar.find({"participants": user['email']}))
    return events


@app.get("/calendar/today/{user_id}")
def get_today_events(user_id: str):
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    today = datetime.utcnow().date()
    events = list(db.calendar.find({
        "participants": user['email'],
        "date": today.strftime('%Y-%m-%d')
    }))
    return events
@app.get("/calendar/{user_id}/events")
def get_user_calendar_events(user_id: str):
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    events = list(db.calendar.find({"participants": user['email']}))
    return events

@app.post("/training_plan")
def create_training_plan(plan: TrainingPlan):
    db.training_plans.insert_one(plan.dict())
    return {"message": "Training plan created."}


@app.get("/training_plan/{match_id}")
def get_training_plan(match_id: str):
    plan = db.training_plans.find_one({"match_id": match_id}, {"_id": 0})
    return plan


@app.get("/protected")
def protected_route(current_user: dict = Depends(get_current_user)):
    return {"message": f"Добро пожаловать, {current_user['name']}!"}


@app.get("/protected_profile")
def protected_profile(current_user: dict = Depends(get_current_user)):
    return {"email": current_user['email'], "username": current_user['username'], "points": current_user.get('points', 0), "point_history": current_user.get('point_history', [])}
