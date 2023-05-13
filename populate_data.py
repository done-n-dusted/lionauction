from utils import *
import csv
import sqlite3 as sql
import os

if os.path.exists('database.db'):
    os.remove('database.db')
conn = sql.connect('database.db')
cursor = conn.cursor()

#creating relations for all the tables

#relations with only primary keys
conn.execute("CREATE TABLE IF NOT EXISTS Users (email TEXT, password TEXT, PRIMARY KEY(email))")
conn.execute("CREATE TABLE IF NOT EXISTS Zipcode_Info (zipcode TEXT, city TEXT, state TEXT, PRIMARY KEY(zipcode))")
conn.execute("CREATE TABLE IF NOT EXISTS Sellers (email TEXT, bank_routing_number TEXT,bank_account_number TEXT,balance INTEGER, PRIMARY KEY(email))")
conn.execute("CREATE TABLE IF NOT EXISTS Helpdesk (email TEXT, position TEXT, PRIMARY KEY(email))")
conn.execute("CREATE TABLE IF NOT EXISTS Bidders (email TEXT,first_name TEXT,last_name TEXT, gender TEXT,age INTEGER, home_address_id TEXT, major TEXT, PRIMARY KEY(email))")
conn.execute("CREATE TABLE IF NOT EXISTS Categories (parent_category TEXT, category_name TEXT, PRIMARY KEY(parent_category, category_name))")

#relations with foreign keys
conn.execute("CREATE TABLE IF NOT EXISTS Address (address_id TEXT,zipcode TEXT, street_num INTEGER, street_name TEXT, PRIMARY KEY(address_id), FOREIGN KEY (zipcode) REFERENCES Zipcode_Info)")
conn.execute("CREATE TABLE IF NOT EXISTS Credit_Cards (credit_card_num TEXT,card_type TEXT,expire_month INTEGER, expire_year INTEGER, security_code TEXT,Owner_email TEXT, PRIMARY KEY(credit_card_num), FOREIGN KEY(Owner_email) REFERENCES Users(email))")
conn.execute("CREATE TABLE IF NOT EXISTS Local_Vendors (Email TEXT, Business_Name TEXT, Business_Address_ID TEXT, Customer_Service_Phone_Number TEXT, PRIMARY KEY(Email), FOREIGN KEY(Business_Address_ID) REFERENCES Address (address_id))")
conn.execute("CREATE TABLE IF NOT EXISTS Ratings (Bidder_Email TEXT, Seller_Email TEXT, Date DATE, Rating INTEGER, Rating_Desc TEXT, FOREIGN KEY(Bidder_Email) REFERENCES Bidders(email), FOREIGN KEY(Seller_Email) REFERENCES Sellers(email))")
conn.execute("CREATE TABLE IF NOT EXISTS Requests (request_id INTEGER, sender_email TEXT, helpdesk_staff_email TEXT, request_type TEXT, request_desc TEXT, request_status BOOLEAN, PRIMARY KEY(request_id), FOREIGN KEY(sender_email) REFERENCES Users(email), FOREIGN KEY(helpdesk_staff_email) REFERENCES Helpdesk(email))")

#creating auction_listings and related relations
conn.execute('''CREATE TABLE IF NOT EXISTS Auction_Listings (Seller_Email TEXT, Listing_ID INTEGER, Category TEXT, Auction_Title TEXT,
             Product_Name TEXT, Product_Description TEXT,Quantity INTEGER,Reserve_Price FLOAT,Max_bids INTEGER,
             Status INTEGER, 
             PRIMARY KEY(Listing_ID),
             FOREIGN KEY(Seller_Email) REFERENCES Sellers(email),
             FOREIGN KEY(Category) REFERENCES Categories(category_name))''')

conn.execute("CREATE TABLE IF NOT EXISTS Bids (Bid_ID INTEGER, Seller_Email TEXT, Listing_ID INTEGER, Bidder_Email TEXT, Bid_Price FLOAT, PRIMARY KEY(Bid_ID), FOREIGN KEY (Seller_Email) REFERENCES Sellers(email), FOREIGN KEY(Listing_ID) REFERENCES Auction_Listings, FOREIGN KEY(Bidder_Email) REFERENCES Bidders(email))")
conn.execute("CREATE TABLE IF NOT EXISTS Transactions (Transaction_ID INTEGER, Seller_Email INTEGER, Listing_ID INTEGER, Bidder_Email TEXT, Date DATE, Payment FLOAT, PRIMARY KEY(Transaction_ID), FOREIGN KEY(Seller_Email) REFERENCES Sellers(email), FOREIGN KEY (Bidder_Email) REFERENCES Bidders(email), FOREIGN KEY(Listing_ID) REFERENCES Auction_Listings)")

#creating own_table
conn.execute("CREATE TABLE IF NOT EXISTS Bid_Counter (Listing_ID INTEGER, nBids INTEGER, FOREIGN KEY (Listing_ID) REFERENCES Auction_Listings)")
all_data_locs = ['data/' + x for x in os.listdir('data/')]


for i in range(len(all_data_locs)):
    tfile = all_data_locs[i]
    table_name = tfile[5:-4]
    once = True
    with open(tfile, 'r') as f:
        reader = csv.reader(f)
        next(reader) #skip header
        for row in reader:
            insert_statement = f"INSERT INTO {table_name} VALUES ("
            for _ in range(len(row)):
                insert_statement += '?,'
            insert_statement = insert_statement[:-1] + ')' #creating insert statement for each file 
            
            if table_name == "Users": #exclusive case for Users to handle passwords
                email, raw_pwd = row
                pwd = sha256_encode(raw_pwd)

                row = email, pwd

            elif table_name == "Auction_Listings": #Since Reserve_Price has a '$'
                row[-3] = float(row[-3].replace(',', '').replace('$', ''))

            cursor.execute(insert_statement, row)


# extracting the number of bids per each item
cursor.execute("SELECT Listing_ID, COUNT(*) FROM Bids GROUP BY Listing_ID")
bid_data = cursor.fetchall()
items_with_bids = set([x[0] for x in bid_data])

# inserting that value into bid_counter, the new table
for one_row in bid_data:
    cursor.execute("INSERT INTO Bid_Counter VALUES (?, ?)", one_row)

cursor.execute("SELECT Listing_ID FROM Auction_Listings")
all_items = cursor.fetchall()
for each_listing in all_items:
    lid = each_listing[0]
    if lid not in items_with_bids:
        cursor.execute("INSERT INTO Bid_Counter VALUES (?, ?)", (lid, 0)) # adding all items even without bids into the bids_counter table

conn.commit()
conn.close()