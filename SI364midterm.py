###############################
####### SETUP (OVERALL) #######
###############################

## Import statements
# Import statements
import os
from flask import Flask, render_template, session, redirect, url_for, flash, request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, ValidationError
from wtforms.validators import Required, Length
from flask_sqlalchemy import SQLAlchemy
from flask_script import Manager, Shell
import tweepy
import twitter_info


consumer_key = twitter_info.consumer_key
consumer_secret = twitter_info.consumer_secret
access_token = twitter_info.access_token
access_token_secret = twitter_info.access_token_secret
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)

api = tweepy.API(auth, parser=tweepy.parsers.JSONParser(), wait_on_rate_limit=True)

## App setup code
app = Flask(__name__)
app.debug = True
app.use_reloader = True

## All app.config values
app.config['SECRET_KEY'] = 'password'
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:guest@localhost:5432/midterm"
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


## Statements for db setup (and manager setup if using Manager)
db = SQLAlchemy(app)









##################
##### MODELS #####
##################


class Tweet(db.Model):
    __tablename__ = 'tweets'
    id = db.Column(db.BigInteger, primary_key = True)
    text = db.Column(db.String)
    user = db.Column(db.Integer, db.ForeignKey('users.id'))
    favorites = db.Column(db.Integer)
    retweets = db.Column(db.Integer)
    
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key = True)
    userName = db.Column(db.String(64))
    displayName = db.Column(db.String(124))
    numFollowers = db.Column(db.Integer)

    tweets = db.relationship('Tweet', backref='User')
    followers = db.relationship('Follower', backref = 'User')
   

class Follower(db.Model):
    __tablename__ = 'followers'
    id = db.Column(db.BigInteger, primary_key = True)
    userName = db.Column(db.String(64))
    displayName = db.Column(db.String(124))
    description = db.Column(db.String(280))
    followersCount = db.Column(db.Integer)

    followingUser = db.Column(db.Integer, db.ForeignKey('users.id'))

class Person(db.Model):
    __tablename__ = 'Person'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String)
    age = db.Column(db.Integer)
    

    ######################################
######## HELPER FXNS (If any) ########
######################################

def get_or_create_user(id, user_name, display_name, num_followers): #checks to see if user exists, if not- adds them to table

    user = User.query.filter_by(id = id, userName = user_name, displayName = display_name).first()

    if user:
        return False

    else:
        user = User(id = id, userName = user_name, displayName = display_name, numFollowers = num_followers)
        db.session.add(user)
        db.session.commit()

        return user

def get_or_create_tweet(id, text, retweets, favorites, user):

    tweet = Tweet.query.filter_by(id = id).first()

    if tweet:
        return tweet
    else:
        tweet = Tweet(user = user.id, text = text, id = id, favorites = favorites, retweets = retweets)
        db.session.add(tweet)
        db.session.commit()

        return tweet

def get_or_create_follower(id, userName, displayName, followingUser, description, followersCount):
  # id userName displayName followingUser description

    follower = Follower.query.filter_by(id = id).first()

    if follower: #this user exists, 
        return follower

    else:

        follower = Follower(id = id, userName = userName, displayName = displayName, followingUser = followingUser, description = description, followersCount = followersCount)
        db.session.add(follower)
        db.session.commit()

        return follower

###################
###### FORMS ######
###################



def validate_user(form, field):
    username = field.data
    if username[0] != '@':
        raise ValidationError('Username must begin with \"@\" and cannot contain any spaces! Enter a valid username.')

class personForm(FlaskForm):
    name = StringField('Enter your name: ', validators = [Required()])
    age = IntegerField('Enter your age: ', validators = [Required()])
    submit = SubmitField('Submit')

class followersForm(FlaskForm):

    number = IntegerField('See only followers with more than this many followers: ', validators = [Required()])
    submit = SubmitField('Submit')

class UserSearchForm(FlaskForm):  
    user = StringField('Add user by username- name must begin with \"@\" and cannot contain any spaces.', validators = [Required(), validate_user])
    submit = SubmitField('Add to database')

#######################
###### VIEW FXNS ######
#######################

@app.route('/')
def home():
    return render_template('base.html')

@app.route('/register')
def register():
    form = personForm()
    return render_template('register.html', form = form)

@app.route('/registered_users', methods = ["GET", "POST"])
def registered_users():
    

    if request.args:
        name = request.args['name']
        age = request.args['age']
        registered_user = Person(name = name, age = age)

        person = Person.query.filter_by(name = name, age = age).first()

        if person:
            already = True
            return render_template('registered_users.html', users = Person.query.all(), already = already)

           
        else:
            already = False
            db.session.add(registered_user)
            db.session.commit()        

        return render_template('registered_users.html', users = Person.query.all(), already = already)

    else:
        flash('Could not add user')
        return render_template('register.html')

  

@app.route('/searchusers', methods = ['GET', 'POST'])
def search():  #searches for user and creates user in table

    form = UserSearchForm()

    if form.validate_on_submit():

        user_name = form.user.data

        user = api.get_user(screen_name = user_name)

        user_id = user['id']
        user_name = user['screen_name']
        screen_name = user['name']
        num_followers = user['followers_count']

      
        User = get_or_create_user( id = user_id, user_name = user_name, display_name = screen_name, num_followers = num_followers)

        if User == False: #if get_or_create_user returns false, it means the user already exists in the table
            flash('user already exists, enter another name')
            return redirect('/searchusers')

        else:#new user has been added to the data table

            flash('most recent entry successfully added')
          
            return redirect(url_for('users_result'))

    errors = [v for v in form.errors.values()]
    if len(errors) > 0:
        flash(errors[0][0])

    return render_template('search.html', form = form)


@app.route('/allusers') #shows all users that have been searched/added to table thus far
def users_result():

    users = User.query.all()

    return render_template('all users.html', users = users)


@app.route('/<user_name>tweets') #shows tweets from a particular user
def see_tweets(user_name):


    user = User.query.filter_by(userName = user_name).first()

    tweets = api.user_timeline(id = user.id, count = 10)

    tweet_list = []

    for tweetDict in tweets:

        text = tweetDict['text'] 
        id = tweetDict['id']
        favorites = tweetDict['favorite_count']
        retweets = tweetDict['retweet_count']

        newtweet = get_or_create_tweet(text = text, id = id, favorites = favorites, retweets = retweets, user = user)

        tweet_list.append(newtweet)

# returns template listing tweets and using submission form to add tweets to the database
    return render_template('see_tweets.html', tweets = tweet_list, user = user)

@app.route('/<user_name>followers', methods = ['POST', 'GET'])
def see_followers(user_name):

    user = User.query.filter_by(userName = user_name).first()

    followers = api.followers(id = user.id)

    # id userName displayName followingUser description

    list_followers = [] # creates empty list (will be filled with followers) to give to template

    form = followersForm()

    for each in followers['users']: #creates or retrieves followers

        id = each['id']
        userName = each['screen_name']
        displayName = each['name']
        followingUser = user.id
        description = each ['description']
        num_followers = each[ 'followers_count' ]

        follower = get_or_create_follower(id = id, followersCount = num_followers, userName = userName, displayName = displayName, followingUser = followingUser, description = description)

        list_followers.append(follower)

    user_name = user.displayName
    number = 10

    if form.validate_on_submit():
        number = form.number.data


    return render_template('userfollowers.html', followers = list_followers, user = user_name, number = number, form = form)




@app.route('/alltweets')
def all_tweets():

    tweets = Tweet.query.all()

    return render_template('alltweets.html', tweets = tweets)

## Code to run the application...

@app.route('/mostfavorites')
def most_favorited():
    tweets = Tweet.query.all()
    highestNum = 0
    highestTweet = 'j'

    for tweet in tweets:

        if tweet.favorites > highestNum:
            highestNum = tweet.favorites
            highestTweet = tweet

    if highestTweet == 'j':
        flash('You have not yet saved any tweets')
        return redirect(url_for('home'))

    user = User.query.filter_by(id = highestTweet.user).first()

    return render_template('mostfavorited.html', tweet = highestTweet, user = user.displayName)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404



if __name__ == '__main__':
    db.create_all() # Will create any defined models when you run the application
    app.run(use_reloader=True,debug=True) # The usual

# Put the code to do so here!
# NOTE: Make sure you include the code you need to initialize the database structure when you run the application!
