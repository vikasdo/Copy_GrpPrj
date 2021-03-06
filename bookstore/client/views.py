import flask
from flask import render_template,jsonify, url_for,request, redirect, flash, session, jsonify, Blueprint ,Response
from flask_login import login_required, current_user, login_user, logout_user,login_manager,LoginManager
from werkzeug.security import check_password_hash
from datetime import datetime
import pandas as pd
import glob,json,re
import os,pickle,collections
from bookstore.models import User,Books,Ratings,OrderList,offer
from bookstore import db, serializer, app
from werkzeug.security import generate_password_hash
from bookstore.client.recommendation_engine import Recommendation_engine
# create A Blueprint
import json
import sqlite3
#connection obj


client = Blueprint('client', __name__)


# Creating login_manager object of LoginManager class for implementing Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.init_app(app)


@app.route('/')
@login_required
def home():
    books = Books.query.limit(18).all()
    ok = User.query.filter_by(id=current_user.id).first()
    return  render_template("client/index.html",books=books,profile=ok)


#route to get discounted users list

@app.route('/getDiscountedUsers')
def getDiscount():
    data = offer.query.all()

    imp_data={}
    for x in data:
        imp_data.update(x.get_json())



    return jsonify(imp_data)


# returns JSON Object as response
@app.route('/get_data')
def get_data():
    
    data={}

    #1 earning 
    conn = sqlite3.connect(app.config["SQLITE_DB_DIR"])
    cur1 = conn.execute("SELECT SUM(quantity)*110 from order_list")
    
    for x in cur1:
        data["earnings"]= x[0]

    #2 Top 5 book revenue

    cur2 = conn.execute('''SELECT book_ISBN,SUM(quantity)*110 as revenue from order_list 
    group by(book_ISBN) ORDER BY revenue DESC LIMIT 5''')

    tmp={}

    for row in cur2:
        tmp[row[0]]=row[1]

    data["book_revenue"]=tmp

    #3 Top 4 Average book ratings

    cur3 = conn.execute('''SELECT book_id,ROUND(AVG(rating),3) as red from ratings group by(book_id) ORDER BY red DESC LIMIT 4''')

    tmp={}

    for row in cur3:
        tmp[row[0]]=float(row[1])

    data["avg_ratings"]=tmp

    #4 total users

    cur4 = conn.execute('''SELECT DISTINCT COUNT(*) from user
    ''')

    for s in cur4:
        data["total_users"]=s[0]


    #5 total Books Rated 

    curr5=conn.execute("""SELECT DISTINCT COUNT(book_id) FROM ratings""")

    for t in curr5:
        data["books_reviewed"]=t;

    #6 total Transactions Perfomed till now

    curr6 = conn.execute('''SELECT COUNT(*) from order_list''')

    for t in curr6:
        data["total_transactions"]=t;

    #7 Data By Age groups
    age_limit,age_group = {"young_age":[20,30],"middle_age":[40,50],"old_age":[60,70]},{}
    
    for key,value in age_limit.items():
        curr7 = conn.execute(f'''SELECT COUNT(*) FROM USER WHERE AGE BETWEEN {value[0]} AND {value[1]}''')
        for y in curr7:
            age_group[key]=y[0];
    
    data["age_group"]=age_group

    #8 User Country

    user_country={'usa':0,'germany':0,'canada':0,'united kingdom':0,'malaysia':0,'spain':0,'france':0}
    for uc in user_country.keys():
        curr8 = conn.execute(f"""SELECT COUNT(location) FROM USER WHERE location LIKE '%{uc}%'""")
        for loc in curr8:
            user_country[uc]=loc[0]
    data["user_country"]=user_country

    #9 Personalized Offers Data

    '''personalized_offers=[]
    curr9 = conn.execute("""SELECT us.id,us.email,us.name,us.location,COUNT(*) AS Purchases FROM order_list o ,user us WHERE us.id=o.user_id GROUP BY(o.user_id) HAVING Purchases>=3""")
    print(curr9[0])
    for po in curr9:
        print(po[0])
    personalized_offers.append(po[1])
    data["personalized_offers"]=personalized_offers
    print(personalized_offers)'''

    conn.close()
    return data

@app.route('/dashboard')
def dashboard():
    data = get_data()
    print(data)
    return render_template('index.html',data = data)



@app.route('/login' , methods=['GET' , 'POST'])
def login():

    if current_user.is_authenticated:
        flash('Already Logged in...','info')
        return redirect(url_for('home'))


    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        ok = User.query.filter_by(email=email).first()
        if ok is not None:
            login_user(ok)
            flash("Login Success :)",'success')
            return redirect(url_for('home'))
        else:
            flash("Email doesn't exit, Signup First...",'error')
            return redirect(url_for('register'))

    return render_template('client/login.html')

@app.route('/register' , methods = ['GET' , 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email =request.form['email']
        password = request.form['password']
        age = request.form['age']
        location = request.form['location']

        ok = User.query.filter_by(email=email).first()

        if ok:
            flash('Existing User Login to continue...','error')
            return redirect(url_for('login'))

        new_user =  User(name=username,email=email,
                        password=generate_password_hash(password, method='sha256'),location=location,age=age)
        db.session.add(new_user)
        db.session.commit()
        flash(f'Account Created for {username}','success')
        return redirect(url_for('login'))
    else:
        return render_template('client/signup.html')



@app.route('/admin/addBook',methods=['GET','POST'])
def addBook():
    if request.method =='POST':
        data = request.form;

        title = data['title']
        publisher = data['publisher']
        author = data['author']
        bookcost = data['book_cost']
        imageURL = data['imageURL']

        ok = Books(title=title,publisher=publisher,author=author,book_cost=bookcost,bookImage = imageURL)

        db.session.add(ok)
        db.session.commit()
        flash(f'Book with title {title} added successfully','success')
        return redirect(url_for('addBook'))

    return render_template('client/admin.html')


import ast

@app.route('/transaction',methods=["GET","POST"])
@login_required
def transaction():

    if request.method=="POST":
        data=json.loads(request.form["order"])
        total =request.form["total-price"]

        for key,value in data.items():
            value=ast.literal_eval(value) 
            frd = OrderList(book_ISBN=key,quantity=value[1],user_id=current_user.id,total_price=total)
            db.session.add(frd) 
            db.session.commit() 

    return render_template("client/index.html")

@app.route('/single_product/<string:bookid>',methods = ['GET','POST'])
@login_required
def single_product(bookid):


    if request.method=='POST':

        pickled_data=None

        user_id=request.form.get('user_id')
        user_rating= request.form.get('user_rating')
        book_id = request.form.get('book_id')

        es=len(book_id)

        if(book_id[es-1]=='!' and book_id[es-2]=='#'):
            book_id=book_id[:es-2]

        print(book_id)

        ok = Ratings.query.filter_by(user_id=user_id).filter_by(book_id=book_id).first();

        if not ok: 
            red = Ratings(user_id=user_id,rating=user_rating,book_id=book_id)
            db.session.add(red)
            db.session.commit();

        else:
            ok.rating=user_rating

        print(Ratings.query.all())
       

    books = Books.query.filter_by(ISBN=bookid).first() 
    #call to recommendation engine
    print(current_user.id)

    user_id=current_user.id
    pickle_file="filename.pickle"
    pickled_data=None
    with open(pickle_file,'rb') as infile:
        pickled_data = pickle.load(infile)

    out=None
    if user_id:#  not in pickled_data:
        Recommendation_engine_obj=Recommendation_engine()
        out=Recommendation_engine_obj.getRecommendedBooks(user_id)
        pickled_data[user_id]=out
    #else:
    #   out=pickled_data[user_id]
       
    filename = "filename.pickle"
    outfile = open(filename,'wb')
    pickle.dump(pickled_data,outfile)
    outfile.close()

    print(out.columns)
    #print(out["imageUrlL"])

    return render_template('client/single.html',books=books,suggestedBooks=out)


@app.route('/myprofile',methods=["GET","POST"])
@login_required
def myprofile():


    ok = User.query.filter_by(id=current_user.id).first()

    print(ok)

    if request.method=="POST":
        password = request.form.get("password")
        print(password)
        ok.password=password
        flash(f'Profile Updated Successfully','success')


    return redirect(url_for('home'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('See you later','success')
    return render_template('client/login.html')



@app.route('/personalized_offers')
def personalized_offers():
        data = offer.query.all()
        imp_data={}
        for x in data:
            imp_data.update(x.get_json())
        print(jsonify(imp_data))

        conn = sqlite3.connect(app.config["SQLITE_DB_DIR"])
        personalized_offers = pd.read_sql_query('SELECT us.id,us.email,us.name,us.location,of.discount,COUNT(*) AS Purchases FROM order_list o ,user us,offer of  WHERE us.id=o.user_id AND o.user_id=of.user_id  GROUP BY(o.user_id) HAVING Purchases>=3', conn) 
        return render_template('offers.html',data=personalized_offers)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/discounts',methods=['POST'])
def discounts():
    user_id = request.form["user-id"]
    discount  = request.form["discount"]
    new_discount =  offer(user_id=user_id,discount=discount)
    stat = offer.query.filter_by(user_id=user_id).first()
    if stat is not None:
        stat.discount = discount
    else:
        db.session.add(new_discount)
    db.session.commit()
    flash(f'Discount Successfully Updated','success')
    return redirect(url_for('personalized_offers'))