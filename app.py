# importing required packages
from flask import Flask, render_template
from flask import request, redirect, url_for
from flask import session
import sqlite3 as sql
from utils import *
import datetime

# initializing flask app with secret key, needed to utilize sessions
app = Flask(__name__)
app.secret_key = "lionauction"


@app.route('/')
def home():
    '''
    Function for loading the home page
    '''
    if 'email' not in session: # if not logged in go to login
        return redirect(url_for('login'))
    else: # else dashboard
        return redirect(url_for('dashboard'))

@app.route('/login', methods = ['GET', 'POST'])
def login():
    '''
    Function for managing login of the user
    '''
    if request.method == 'POST':

        email = request.form['email']
        raw_pwd = request.form['password']
        user_type = request.form['user_type']
        pwd = sha256_encode(raw_pwd) # convert password to hash to match with db

        conn = sql.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE email = ? AND password = ?;", (email, pwd))
        credentials = cursor.fetchone() # fetch the user from db for credentials
        
        session['roles'] = []

        if credentials == None: # no user found. Error to try again.
            error = 'Invalid Email or Password. Please try again.'
            return render_template('login.html', error=error)

        # valid user

        cursor.execute("SELECT * FROM Bidders WHERE email=?", (email,))
        bidder_details = cursor.fetchone() # getting bidder details if bidder
        cursor.execute("SELECT * FROM Sellers WHERE email=?", (email,))
        seller_details = cursor.fetchone() # getting seller details if seller
        
        # adding roles to session to keep track of possible roles
        if bidder_details != None:
            session['roles'].append('Bidder') 
        if seller_details != None:
            session['roles'].append('Seller')


        if user_type == "bidder":

            if bidder_details == None: # if not bidder
                error = "Invalid Role. Please try again."
                return render_template('login.html', error=error)
            
            else:
                session['role'] = 'Bidder'
        
        elif user_type == "seller":


            if seller_details == None: # if not seller
                error = "Invalid Role. Please try again."
                return render_template('login.html', error=error)
        
            else:
                session['role'] = 'Seller'

        
        session['email'] = email
        # if login success, direct to profile
        return redirect(url_for('profile'))

    else:
        return render_template('login.html')

@app.route('/logout', methods = ['GET', 'POST'])
def logout():
    '''
    Function that logs out the user. Pops the email from session.
    '''
    session.pop('email', None)
    return redirect(url_for('home'))

@app.route('/dashboard', methods = ['GET', 'POST'])
def dashboard():
    '''
    Function that redirects dashboard page to one of bidder_dashboard/seller_dashboard based on role of user.
    '''
    if session['role'] == "Bidder":
        return redirect(url_for('bidder_dashboard'))
    elif session['role'] == "Seller":
        return redirect(url_for('seller_dashboard'))

@app.route('/bidder_dashboard', methods = ['GET', 'POST'])
def bidder_dashboard():
    '''
        Function that handles the bidder dashboard
    '''
    if 'email' not in session: #not logged in
        return redirect(url_for('login'))

    if session['role'] != "Bidder":
        return redirect(url_for('dashboard'))

    conn = sql.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT parent_category FROM Categories")
    
    # fetching all the categories
    cat_tups = cursor.fetchall()
    cats = ["All"] + [x[0] for x in cat_tups]

    #query that gets all the listings with the current price
    temp_qry = "SELECT AL.*, (SELECT MAX(Bid_Price) FROM Bids B WHERE B.Listing_ID = AL.Listing_ID) AS Current_Bid_Price FROM Auction_Listings AL WHERE Status=1"

    cursor.execute(temp_qry)
    rows = cursor.fetchall() # has all the data for the website

    headers = [x[0] for x in cursor.description] #headers to access that particular column

    available_listings = []
    # loading all the listings to a list that will be rendered in the website
    for row in rows:
        row_dict = {}
        for i in range(len(row)):
            if row[i] == None:
                row_dict[headers[i]] = 0
            else:
                row_dict[headers[i]] = row[i]

        cursor.execute("SELECT Bidder_Email FROM Bids WHERE Listing_ID=? ORDER BY Bid_ID DESC LIMIT 1", (row_dict["Listing_ID"],))

        # getting the last bidder which restricts the user to have only one bid at a time.
        last_bidder_email_tuple = cursor.fetchone()
        if last_bidder_email_tuple != None:
            last_bidder_email = last_bidder_email_tuple[0]
        else:
            last_bidder_email = ""
        row_dict["Last_Bidder"] = last_bidder_email

        # fetching the number of bids for the product to match max bids and then proceed to payment
        cursor.execute("SELECT nBids FROM Bid_Counter WHERE Listing_ID=?", (row_dict["Listing_ID"],))
        n_bids = cursor.fetchone()[0]
        # print("$$$", n_bids)
        row_dict["Total_Bids"] = n_bids
        row_dict["Atleast_New_Price"] = float(row_dict["Current_Bid_Price"]) + 1
        available_listings.append(row_dict) # loading each item as a dictionary to a list that will be rendered

    # loading all the sub categories for each of the category
    subcats = {"All": []}
    for cat in cats[1:]:
        cursor.execute("SELECT DISTINCT category_name FROM Categories WHERE parent_category=?", (cat, ))   
        sub_tups = cursor.fetchall()
        temp_sub = [x[0] for x in sub_tups]
        subcats[cat] = temp_sub
    
    parent_category = "All"
    #handling the forms, which is filtering the products.
    if request.method == "POST":
        parent_category = request.form['pcat'] # loading category
        sub_category = request.form['psubcat'] # loading sub category
        
        if parent_category != "All":
            cursor.execute(temp_qry + " AND Category=?", (parent_category, ))
        else:
            cursor.execute(temp_qry)
        
        rows = cursor.fetchall() # fetching all items belonging to that category
        headers = [x[0] for x in cursor.description] # headers for those items

        available_listings = []
        for row in rows:
            row_dict = {}
            for i in range(len(row)):
                if row[i] == None:
                    row_dict[headers[i]] = 0
                else:
                    row_dict[headers[i]] = row[i]

            cursor.execute("SELECT Bidder_Email FROM Bids WHERE Listing_ID=? ORDER BY Bid_ID DESC LIMIT 1", (row_dict["Listing_ID"],))

            # getting the last bidder which restricts the user to have only one bid at a time.
            last_bidder_email_tuple = cursor.fetchone()
            if last_bidder_email_tuple != None:
                last_bidder_email = last_bidder_email_tuple[0]
            else:
                last_bidder_email = ""
            row_dict["Last_Bidder"] = last_bidder_email

            # fetching the number of bids for the product to match max bids and then proceed to payment
            cursor.execute("SELECT nBids FROM Bid_Counter WHERE Listing_ID=?", (row_dict["Listing_ID"],))
            n_bids = cursor.fetchone()[0]
            # print("$$$", n_bids)
            row_dict["Total_Bids"] = n_bids
            row_dict["Atleast_New_Price"] = float(row_dict["Current_Bid_Price"]) + 1

            available_listings.append(row_dict) # saving all items in the list to be rendered later

        return render_template('bidder_dashboard.html', user=session['email'], av_listings = available_listings, categories=cats, current_category=parent_category, current_sub_category = sub_category, sub_categories = subcats)


    return render_template('bidder_dashboard.html', user=session['email'], categories=cats, current_category=parent_category, av_listings = available_listings, sub_categories = subcats)

@app.route('/seller_dashboard', methods=['GET', 'POST'])
def seller_dashboard():
    '''
        Function that handles the Seller dashboard
    '''    
    if 'email' not in session: #not logged in
        return redirect(url_for('login'))

    if session['role'] != "Seller":
        return redirect(url_for('dashboard'))

    conn = sql.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT parent_category FROM Categories")
    cat_tups = cursor.fetchall()
    cats = [x[0] for x in cat_tups] #extracting all categories

    temp_qry = "SELECT AL.*, (SELECT MAX(Bid_Price) FROM Bids B WHERE B.Listing_ID = AL.Listing_ID) AS Current_Bid_Price, (SELECT COUNT(*) FROM BIDS B WHERE B.Listing_ID = AL.Listing_ID) AS Number_Of_Bids FROM Auction_Listings AL"
    temp_qry += " WHERE Seller_Email=?"
    cursor.execute(temp_qry, (session['email'], ))
    # listing all items belonging to the seller with the current price.

    rows = cursor.fetchall()
    headers = [x[0] for x in cursor.description]

    my_listings = []
    for row in rows:
        row_dict = {}
        for i in range(len(row)):
            if row[i] == None:
                row_dict[headers[i]] = 0
            else:
                row_dict[headers[i]] = row[i]

        my_listings.append(row_dict) # creating a list of all items belonging to the seller

    # render appropriate template when seller wishes to view their products/add new products
    if request.method == "POST":
        if request.form["action"] == "show_my": 
            return render_template('seller_dashboard.html', listings=my_listings, create=False, categories=cats)
    
        elif request.form["action"] == "add_new":
            return render_template('seller_dashboard.html', listings=[], create=True, categories=cats)

    return render_template('seller_dashboard.html', listings=my_listings, create=False, categories=cats)

@app.route('/pay', methods = ['GET', 'POST'])
def pay():
    '''
        Function that handles the confirm payment page that summarizes the purchase
    '''
    if 'email' not in session: #not logged in
        return redirect(url_for('login'))
    
    pay_dict = {}
    pay_dict["Bidder"] = session["email"]

    if request.method == "POST":
        listing_id = request.form["item_id_bid"]
        last_bid = request.form["prev_bid"]
        seller_id = request.form["seller"]
        pay_dict["Bid_Price"] = last_bid
        pay_dict["Seller"] = seller_id

        # pay_dict["product_details"] = details
        conn = sql.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE Auction_Listings SET Status = 2 WHERE Listing_ID = ?", (listing_id,)) # setting the status of item to sold
        
        cursor.execute("SELECT * FROM Auction_Listings WHERE Listing_ID = ?", (listing_id,))
        row = cursor.fetchone()
        headers = [x[0] for x in cursor.description]

        product_card = {}
        for i in range(len(row)):
            product_card[headers[i]] = row[i]
        
        listing = product_card #fetching details of the product on purchase
        
        cursor.execute("SELECT credit_card_num FROM Credit_Cards WHERE Owner_email=?", (session["email"],)) #getting credit card of bidder
        cc_no = cursor.fetchone()[0]
        cc_no = cc_no[:4] + "-****-****-" + cc_no[-4:]
        pay_dict["cc_no"] = cc_no
        
        conn.commit()
        conn.close()
        
        return render_template("pay.html", data = pay_dict, listing=listing)

    return render_template("pay.html", data = pay_dict)

@app.route('/modify_item', methods=['GET', 'POST'])
def modify_item():
    '''
        Function that lets the seller modify the status of the item from available to unavailable and vice versa.
    '''

    if request.method == "POST":
        listing_id, curr_status = request.form["lid"], int(request.form["status"])

        # toggling the status
        if curr_status == 0:
            new_status = 1
        elif curr_status == 1:
            new_status = 0
        else:
            new_status = curr_status

        conn = sql.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE Auction_Listings SET Status=? WHERE Listing_ID=?", (new_status, listing_id)) #updating the status of item
        conn.commit()
        conn.close()
    
    return redirect(url_for("seller_dashboard"))

def load_details_from_id(table_name, id_name, id_in_table, data):
    '''
        Helper function that takes table_name, id_name, name of id in that table, and all data as inputs
        and returns the modified data.
    '''
    conn = sql.connect('database.db')
    cursor = conn.cursor()
    id = data[id_name]
    cursor.execute("SELECT * FROM " + table_name + " LIMIT 0")
    headers = [x[0] for x in cursor.description]
    cursor.execute("SELECT * FROM " + table_name + " WHERE " + id_in_table +"=?", (id,))
    details = cursor.fetchone()
    print(details, headers)
    for i in range(len(headers)):
        if headers[i] == id_in_table:
            continue
        data[headers[i]] = details[i]

    return data

@app.route('/add_item', methods = ['GET', 'POST'])
def add_item():


    '''
        Function that handles adding new item from seller.
    '''
    conn = sql.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(Listing_ID) FROM Auction_Listings")
    new_lid = float(cursor.fetchone()[0]) + 1 # getting the new listing id. Max of current LIDs + 1

    if request.method == "POST":
        cursor.execute("INSERT INTO Bid_Counter VALUES (?,?)", (new_lid, 0)) # adding new entry to Bid_Counter stating there are no bids currently
        status = 0 #initially unavailable

        #loading data
        category = request.form["category"]
        title = request.form["title"]
        name = request.form["name"]
        desc = request.form["desc"]
        qty = request.form["qty"]
        price = request.form["Reserve Price"]
        max_bids = request.form["max_bids"]
        seller = session["email"]

        # adding new item to Auction_Listings table
        cursor.execute("INSERT INTO Auction_Listings VALUES (?,?,?,?,?,?,?,?,?,?)", (seller, new_lid, category, title, name, desc, qty, price, max_bids, status))
        
        conn.commit()
        conn.close()

        print("added new item")
    
    return redirect(url_for("dashboard"))

@app.route('/bid', methods = ['GET', 'POST'])
def bid():
    '''
        Function that handles bid from the bidder
    '''
    if request.method == "POST":
        item_listing_id = request.form["item_id_bid"]
        bid_amount = request.form["bid_val"]
        prev_bid = request.form["prev_bid"]
        conn = sql.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT Seller_Email FROM Auction_Listings WHERE Listing_ID=?", (item_listing_id,))
        seller_email = cursor.fetchone()[0]

        if prev_bid == None: #if there is no bid, start from 0
            prev_bid = 0
        # new_price = float(prev_bid) + float(bid_amount)
        new_price = float(bid_amount) #new bid price
        cursor.execute("SELECT MAX(Bid_ID) FROM Bids") #finding new bid id. Max bid id + 1
        bid_id = cursor.fetchone()[0] + 1
        
        # adding new bid
        cursor.execute("INSERT INTO Bids VALUES (?,?,?,?,?)", (bid_id, seller_email, item_listing_id, session["email"], new_price))
        
        #updating bid counter with number of bids for the item
        cursor.execute("UPDATE Bid_Counter SET nBids = nBids + 1 WHERE Listing_ID = ?", (item_listing_id,))
        conn.commit()
        conn.close()
        return redirect(url_for("bidder_dashboard"))

    return redirect(url_for("dashboard"))

@app.route('/profile', methods = ['GET', 'POST'])
def profile():

    '''
        Function that displays user information in the profile page
    '''

    if 'email' not in session: #not logged in
        return redirect(url_for('login'))
    
    if request.method == "POST":
        # changing roles
        if session['role'] == 'Bidder' and 'Seller' in session['roles']:
            session['role'] = 'Seller'
        
        elif session['role'] == 'Seller' and 'Bidder' in session['roles']:
            session['role'] = 'Bidder'
        
        print('role_changed')
        return redirect(url_for('profile'))


    conn = sql.connect('database.db')
    cursor = conn.cursor()

    data = {'Role': session['role']}

    # data['roles'] = session['roles']
    # creating data to keep track of all the data belonging to the user.
    if session['role'] == "Bidder":
        cursor.execute("SELECT * FROM Bidders LIMIT 0")
        headers = [x[0] for x in cursor.description]
        cursor.execute("SELECT * FROM Bidders WHERE email=?", (session['email'],))
        details = cursor.fetchone()
        for i in range(len(headers)):
            data[headers[i]] = details[i]

        data = load_details_from_id('Address', 'home_address_id', 'address_id', data)
        data = load_details_from_id('Zipcode_Info', 'zipcode', 'zipcode', data)

        cursor.execute("SELECT credit_card_num FROM Credit_Cards WHERE Owner_email=?", (session['email'],))
        cc_num = "****-****-****-" + cursor.fetchone()[0][-4:]
        data['Credit Card Number'] = cc_num
        data.pop('home_address_id')

    return render_template('profile.html', data = data)

@app.route('/pay_handle', methods = ["GET", "POST"])
def pay_handle():
    '''
        Handles the final payment.
    '''
    today = datetime.datetime.now().strftime('%m/%d/%y') #extracting todays date as an entry to transactions table

    conn = sql.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(Transaction_ID) FROM Transactions") 
    new_tid = float(cursor.fetchone()[0]) + 1 # fetching new TID. Max current TID + 1

    if request.method == "POST":
        lid = request.form["listing_id"]
        seller = request.form["seller_email"]
        bidder = request.form["bidder_email"]
        price = request.form["price"]

        # insert the new transaction into transaction table
        cursor.execute('INSERT INTO Transactions VALUES (?,?,?,?,?,?)', (new_tid, seller, lid, bidder, today, price))
        conn.commit()
        conn.close()

        return render_template('pay_handle.html', bidder=bidder, seller=seller, date=today, tid=new_tid)
    
    return render_template('pay_handle.html', tid = new_tid)

@app.route('/review', methods=["POST", "GET"])
def review():
    '''
        Function that handles reviews by the bidder to the seller. It is completely optional
    '''
    if request.method == "POST":
        seller = request.form["seller"]
        bidder = request.form["bidder"]
        date = request.form["date"]
        rating = request.form["rating"]

        if rating != '0': # 0 is the default rating. This means no rating was provided.
            desc = request.form["desc"]

            conn = sql.connect("database.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Ratings VALUES (?,?,?,?,?)", (bidder, seller, date, rating, desc))
            # adding new rating to the Ratings table.
            conn.commit()
            conn.close()

    # after rating, bidder goes back to their dashboard
    return redirect(url_for("dashboard"))

if __name__ == '__main__':
    # app.run(host="127.0.0.1", port=8080, debug=True)
    app.run(debug = True)
    # app.run()