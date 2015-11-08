import os
import urllib
import urlparse
import datetime
import json

from google.appengine.api import users
from google.appengine.ext import ndb

from collections import namedtuple

import jinja2
import webapp2
import endpoints

from webapp2_extras import sessions
from StringIO import StringIO

from protorpc import messages
from protorpc import message_types
from protorpc import remote

''' Jinja filters '''
j = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__),'views')),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

def datetimeformat(value, format='%Y-%b-%d %H:%M:%S %p'):
	return value.strftime(format)

def dateNumberFormat(value, format='%Y-%m-%d'):
	return value.strftime(format)

def dateformat(value, format='%Y-%b-%d'):
	return value.strftime(format)

def floatToDollar(value):
	return '$ ' + format(value,'.2f')

def floatToDecimal(value):
	return format(value,'.2f')


j.filters['datetimeformat'] = datetimeformat
j.filters['dateNumberFormat'] = dateNumberFormat
j.filters['dateformat'] = dateformat
j.filters['floatToDollar'] = floatToDollar
j.filters['floatToDecimal'] = floatToDecimal


''' Functions '''
# Sets the user values in any page.
def set_user_values(user,users,logout_url='/',login_url='/'):
	values = { 'user' : user }
	values['admin_user'] = True if users.is_current_user_admin() else False
	values['logout_url'] = users.create_logout_url(logout_url)
	values['login_url'] = users.create_logout_url(login_url)
	return values

# Sets the dashboard values in Dashboard page.
def set_dashboard_values():
	values = {}
	values['stores_count'] = Stores.query().count()
	# Users
	values['dbusers_count'] = DbUsers.query().count()
	values['active_dbusers_count'] = DbUsers.query(DbUsers.status=='active').count()
	values['inactive_dbusers_count'] = DbUsers.query(DbUsers.status=='inactive').count()
	# Customers
	values['customers_count'] = Customers.query().count()
	values['active_customers_count'] = Customers.query(Customers.status=='active').count()
	values['inactive_customers_count'] = Customers.query(Customers.status=='inactive').count()
	# Transactions
	values['loans_count'] = Transactions.query(Transactions.transactionType=='Loan').count()
	values['loans_total'] = getTotalTransactions('Loan')
	values['purchase_count'] = Transactions.query(Transactions.transactionType=='Purchase').count()
	values['purchases_total'] = getTotalTransactions('Purchase')
	values['invoice_count'] = Transactions.query(Transactions.transactionType=='Invoice').count()
	values['invoices_total'] = getTotalTransactions('Invoice')
	return values

def getTotalTransactions(transactionType):
	transactions = Transactions.query(Transactions.transactionType==transactionType).fetch()
	total = []
	for transaction in transactions:
		subTotal = transaction.principalAmount + transaction.setupFee + transaction.insuranceFee
		total.append(subTotal)
	return sum(total)

def birthdateformat(value,format='%Y-%m-%d'):
	return datetime.datetime.strptime(value, '%Y-%m-%d')

def dateFormat(value, format='%Y-%m-%d'):
	return datetime.datetime.strptime(value,format)
	# datetime.datetime.strptime("2013-1-25", '%Y-%m-%d').strftime('%m/%d/%y')

def createJsonResource(resource):
	try: 
		resource = resource.to_dict()
		for key, value in resource.items():
			if isinstance(value, datetime.date):
				resource[key] = dateformat(value)
		# io = stringIO()
	except None:
		pass
	return json.dumps(resource)


# Sets the values in the Settings page.
def setSettings():
	settings_list = []
	setting = Settings(name = "nextLoanNumber", label = "Next Loan Number", value = "L1000001")
	settings_list.append(setting)

	setting = Settings(name = "nextReceiptNumber", label = "Next Receipt Number", value = "R1000001")
	settings_list.append(setting)

	setting = Settings(name = "nextInvoiceNumber", label = "Next Invoice Number", value = "N1000001")
	settings_list.append(setting)

	settingsKeys = ndb.put_multi(settings_list)

	settings = ndb.get_multi(settingsKeys)
	return settings

# returns the settings if there are any.
def checkSettings():
	settings = Settings.query().get()
	settings_list = []
	if settings is None:
		return setSettings()
	else:
		settings = Settings.query()
		# getSettings
		return settings




''' Models '''
class Address(ndb.Model):
	addressType = ndb.StringProperty()
	address1 = ndb.StringProperty()
	address2 = ndb.StringProperty()
	city = ndb.StringProperty()
	state = ndb.StringProperty()
	zipCode = ndb.StringProperty()

class Phone(ndb.Model):
	phoneType = ndb.StringProperty()
	phone = ndb.StringProperty()

class Email(ndb.Model):
	emailType = ndb.StringProperty()
	email = ndb.StringProperty()

class Stores(ndb.Model):
	storeName = ndb.StringProperty(indexed=True)
	phoneNumber = ndb.StringProperty(indexed=True)
	faxNumber = ndb.StringProperty()
	address = ndb.StructuredProperty(Address,repeated=False)
	status = ndb.StringProperty()
	dateCreated = ndb.DateTimeProperty(auto_now_add=True)
	dateUpdated = ndb.DateTimeProperty(auto_now=True)

class DbUsers(ndb.Model):
	name = ndb.StringProperty(indexed=True)
	username = ndb.StringProperty(indexed=True)
	email = ndb.StringProperty(indexed=True,repeated=True)
	phone = ndb.StringProperty(indexed=True,repeated=True)
	stores = ndb.KeyProperty(kind=Stores,repeated=True)
	password = ndb.StringProperty()
	status = ndb.StringProperty()
	dateCreated = ndb.DateTimeProperty(auto_now_add=True)
	dateUpdated = ndb.DateTimeProperty(auto_now=True)

class Customers(ndb.Model):
	firstname = ndb.StringProperty()
	lastname = ndb.StringProperty(indexed=True)
	birthdate = ndb.DateProperty(indexed=True)
	status = ndb.StringProperty()
	address = ndb.StructuredProperty(Address,repeated=False)
	license = ndb.StringProperty(indexed=True)
	gunLicense = ndb.StringProperty(indexed=True)
	phone = ndb.StringProperty(indexed=True)
	email = ndb.StringProperty(indexed=True)
	gunLicense = ndb.StringProperty(indexed=True)
	dateCreated = ndb.DateTimeProperty(auto_now_add=True)
	dateUpdated = ndb.DateTimeProperty(auto_now=True)

class Items(ndb.Model):
	itemNumber = ndb.StringProperty()
	description = ndb.TextProperty()
	quantity = ndb.IntegerProperty()
	price = ndb.FloatProperty()

class ItemCategoryElectronics(ndb.Model):
	brandName = ndb.StringProperty()
	modelNumber = ndb.StringProperty()
	serialNumber = ndb.StringProperty(indexed=True)

class ItemCategoryJewelry(ndb.Model):
	karat = ndb.StringProperty()
	deadWeight = ndb.StringProperty()
	grams = ndb.StringProperty()
	ounces = ndb.StringProperty()
	counts = ndb.StringProperty()

class ItemCategoryMusical(ndb.Model):
	instrumentBrand = ndb.StringProperty()
	instrumentKind = ndb.StringProperty()

class ItemCategoryGun(ndb.Model):
	gunCaliber = ndb.StringProperty()
	gunType = ndb.StringProperty()
	gunAction = ndb.StringProperty()

class Transactions(ndb.Model):
	transactionType = ndb.StringProperty(choices=['Loan','Purchase','Invoice'])
	# types of transaction numbers
	transactionNumber = ndb.StringProperty(indexed=True,required=True)
	originalLoanNumber = ndb.StringProperty()
	previousLoanNumber = ndb.StringProperty()
	nextLoanNumber = ndb.StringProperty()
	# customer information
	customer = ndb.KeyProperty(kind=Customers,repeated=False)
	# category properties
	category = ndb.StringProperty(choices=['Electronics','Jewelry','Musical Instrument','Gun','Other'])
	electronics = ndb.StructuredProperty(ItemCategoryElectronics,repeated=False)
	jewelry = ndb.StructuredProperty(ItemCategoryJewelry,repeated=False)
	musical = ndb.StructuredProperty(ItemCategoryMusical,repeated=False)
	gun = ndb.StructuredProperty(ItemCategoryGun,repeated=False)
	# item information
	description = ndb.TextProperty()
	itemsList = ndb.StructuredProperty(Items)
	image = ndb.BlobProperty(compressed=True)
	# other information
	inPremises = ndb.BooleanProperty()
	extended = ndb.BooleanProperty()
	itemLocation = ndb.StringProperty()
	# fees and amount
	principalAmount = ndb.FloatProperty()
	setupFee = ndb.FloatProperty()
	insuranceFee = ndb.FloatProperty()
	discount = ndb.FloatProperty()
	total = ndb.FloatProperty()
	# status
	status = ndb.StringProperty(required=True,choices=['Active','Expired','Redeemed','Extended','Redeemed','Void','Sold','In Stock'])
	dateCreated = ndb.DateTimeProperty(auto_now_add=True)
	dateUpdated = ndb.DateTimeProperty(auto_now=True)

class Payment(ndb.Model):
	# payment information
	transactionType = ndb.StringProperty(choices=['Loan','Purchase','Invoice'])
	paymentNumber = ndb.StringProperty(indexed=True)
	paidTransactionNumbers = ndb.StringProperty(indexed=True,repeated=True)
	status = ndb.StringProperty(required=True,choices=['Active','Expired','Redeemed','Extended','Redeemed','Void','Sold','In Stock'])
	paymentDate = ndb.DateTimeProperty()
	paymentAmount = ndb.FloatProperty()

class Settings(ndb.Model):
	label = ndb.StringProperty()
	name = ndb.StringProperty()
	value = ndb.GenericProperty()
	dateCreated = ndb.DateTimeProperty(auto_now_add=True)
	dateUpdated = ndb.DateTimeProperty(auto_now=True)


''' Views '''
class BaseHandler(webapp2.RequestHandler):
	def render_html(self,template,values):
		values['url'] = urlparse.urlparse(self.request.url)
		template = j.get_template(template)
		self.response.write(template.render(values))


class DashboardHandler(BaseHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			values = set_user_values(user,users)
			values.update(set_dashboard_values())
			self.render_html('dashboard.html',values)
		else:
			self.redirect(users.create_login_url(self.request.uri))

class StoresHandler(BaseHandler):
	def get(self):
		user = users.get_current_user()
		view = self.request.get('view')
		storeKey = str(self.request.get('store'))
		if user:
			values = set_user_values(user,users,'/stores')
			if view=='add':
				values['url'] = urlparse.urlparse(str(self.request.url))
				self.render_html('add-stores.html',values)
			elif view=='edit':
				storeKey = ndb.Key(urlsafe=storeKey)
				values['params'] = urlparse.urlparse(str(self.request.params))
				values['store'] = storeKey.get()
				self.render_html('edit-store.html',values)
			elif view=='info':
				storeKey = ndb.Key(urlsafe=storeKey)
				values['store'] = storeKey.get()
				self.render_html('info-store.html',values)
			elif view=="csv":
				values['stores'] = Stores.query()
				self.render_html('stores.html',values)
			else:
				values['stores'] = Stores.query()
				self.render_html('stores.html',values)

		else:
			self.redirect(users.create_login_url(self.request.uri))

	def post(self):
		user = users.get_current_user()
		view = self.request.get('view')
		if user:
			values = set_user_values(user,users,'/stores')
			if view=='add':
				store = Stores(
					storeName = self.request.get('storeName'),
					phoneNumber = self.request.get('phone'),
					faxNumber = self.request.get('fax'),
					status = 'active',
					address = Address(
						addressType = 'work',
						address1 = str(self.request.get('address1')),
						address2 = str(self.request.get('address2')),
						city = str(self.request.get('city')),
						state = str(self.request.get('state')),
						zipCode = str(self.request.get('zipCode'))
					)
				)
				storeKey = store.put()
				if (storeKey):
					values['store'] = storeKey.get()
					values['message'] = {'message_status':'success','message': 'Successfully saved store'}
					self.render_html('info-store.html',values)
				else:
					values['message'] = {'message_status':'error','message': 'Failed to save store'}
					self.render_html('info-store.html',values)
				storeKey = store.put()
				self.render_html('add-stores.html',values)
			elif view=='info':
				storeUrlSafe = str(self.request.get('store'))
				values['store'] = ndb.Key(urlsafe=storeUrlSafe).get()
				self.render_html('info-store.html',values)
			elif view=='edit':
				storeUrlSafe = str(self.request.get('store'))
				store = ndb.Key(urlsafe=storeUrlSafe).get()
				store.storeName = str(self.request.get('storeName'))
				store.phoneNumber = str(self.request.get('phone'))
				store.faxNumber = str(self.request.get('fax'))
				store.status = 'active'
				store.address = Address(
					addressType = 'work',
					address1 = str(self.request.get('address1')),
					address2 = str(self.request.get('address2')),
					city = str(self.request.get('city')),
					state = str(self.request.get('state')),
					zipCode = str(self.request.get('zipCode'))
				)
				storeKey = store.put()
				values['store'] = storeKey.get()
				self.render_html('info-store.html',values)
			else:
				self.render_html('stores.html',values)		
		else:
			self.redirect(users.create_login_url(self.request.uri))
		self.redirect('/stores')


class DbUsersHandler(BaseHandler):
	def get(self):
		user = users.get_current_user()
		view = str(self.request.get('view'))
		userUrlSafe = str(self.request.get('dbuser'))
		if user:
			values = set_user_values(user,users,'/users')
			if view=='add':
				self.render_html('add-user.html',values)
			elif view=='info':
				values['dbuser'] = ndb.Key(urlsafe=userUrlSafe).get()
				self.render_html('info-user.html',values)
			elif view=='edit':
				values['dbuser'] = ndb.Key(urlsafe=userUrlSafe).get()
				self.render_html('edit-user.html',values)
			else:
				values['dbusers'] = DbUsers.query()
				self.render_html('users.html',values)
		else:
			self.redirect(users.create_login_url(self.request.uri))

	def post(self):
		user = users.get_current_user()
		view = str(self.request.get('view'))
		if user:
			values = set_user_values(user,users,'/users')
			if view=='add':
				email = []
				email.append(str(self.request.get('email')))
				phone = []
				phone.append(str(self.request.get('phone')))
				dbuser = DbUsers(
					name = str(self.request.get('name')),
					email = email,
					phone = phone,
					username = str(self.request.get('username')),
					password = str(self.request.get('password')),
					status = 'active'
				)
				dbuser.put()
				values['dbuser'] = dbuser
				self.render_html('info-user.html',values)
			elif view=='edit':
				dbuserUrlSafe = str(self.request.get('dbuser'))
				email = []
				email.append(str(self.request.get('email')))
				phone = []
				phone.append(str(self.request.get('phone')))
				dbuser = ndb.Key(urlsafe=dbuserUrlSafe).get()
				dbuser.name = str(self.request.get('name'))
				dbuser.email = email
				dbuser.phone = phone
				dbuser.username = str(self.request.get('username'))
				dbuser.password = str(self.request.get('password'))
				dbuser.status = 'active'
				dbuser.put()
				dbuserKey = dbuser.put()
				values['dbuser'] = dbuserKey.get()
				self.render_html('info-user.html',values)
			else:
				self.render_html('users.html',values)
		else:
			self.redirect(users.create_login_url(self.request.uri))


class CustomersHandler(BaseHandler):
	def get(self):
		user = users.get_current_user()
		view = str(self.request.get('view'))
		customerUrlSafe = str(self.request.get('customer'))
		if user:
			values = set_user_values(user,users,'/customers')
			if view=='add':
				self.render_html('add-customer.html',values)
			elif view=='edit':
				values['customer'] = ndb.Key(urlsafe=customerUrlSafe).get()
				self.render_html('edit-customer.html',values)
			elif view=='info':
				values['customer'] = ndb.Key(urlsafe=customerUrlSafe).get()
				self.render_html('info-customer.html',values)
			elif view=='resource':
				customer = ndb.Key(urlsafe=customerUrlSafe).get()
				values['customer'] = createJsonResource(customer)
				self.render_html('resource-customer.json',values)
			else:
				values['customers'] = Customers.query()
				self.render_html('customers.html',values)
		else:
			self.redirect(users.create_login_url(self.request.uri))

	def post(self):
		user = users.get_current_user()
		view = str(self.request.get('view'))
		customerUrlSafe = str(self.request.get('customer'))
		if user:
			values = set_user_values(user,users,'/customers')
			if view=='add':
				customer = Customers(
					firstname = str(self.request.get('firstname')),
					lastname = str(self.request.get('lastname')),
					birthdate = birthdateformat(str(self.request.get('birthdate'))),
					status = 'active',
					address = Address(
						addressType = 'home',
						address1 = str(self.request.get('address1')),
						address2 = str(self.request.get('address2')),
						city = str(self.request.get('city')),
						state = str(self.request.get('state')),
						zipCode = str(self.request.get('zipCode'))
					),
					license = str(self.request.get('license')),
					gunLicense = str(self.request.get('gunLicense')),
					phone = str(self.request.get('phone')),
					email = str(self.request.get('email')),
				)
				customerKey = customer.put()
				values['customer'] = customerKey.get()
				self.render_html('info-customer.html',values)
			elif view=='edit':
				customer = ndb.Key(urlsafe=customerUrlSafe).get()
				customer.firstname = str(self.request.get('firstname'))
				customer.lastname = str(self.request.get('lastname'))
				customer.birthdate = birthdateformat(str(self.request.get('birthdate')))
				customer.status = str(self.request.get('status'))
				customer.address = Address(
					addressType = 'home',
					address1 = str(self.request.get('address1')),
					address2 = str(self.request.get('address2')),
					city = str(self.request.get('city')),
					state = str(self.request.get('state')),
					zipCode = str(self.request.get('zipCode'))
				)
				customer.license = str(self.request.get('license'))
				customer.gunLicense = str(self.request.get('gunLicense'))
				customer.phone = str(self.request.get('phone'))
				customer.email = str(self.request.get('email'))
				customerKey = customer.put()
				values['customer'] = customerKey.get()
				self.render_html('info-customer.html',values)
			else:
				self.render_html('customers.html',values)
		else:
			self.redirect(users.create_login_url(self.request.uri))		


class TransactionsHandler(BaseHandler):
	def get(self):
		user = users.get_current_user()
		transaction_type = str(self.request.get('type'))
		view = str(self.request.get('view'))
		key = str(self.request.get('key'))
		if user:
			values = set_user_values(user,users,'/transactions')
			values['transactions'] = Transactions.query().fetch()
			self.render_html('transactions.html',values)
		else:
			self.redirect(users.create_login_url(self.request.uri))

class TransactionInvoicesHandler(BaseHandler):
	def get(self):
		user = users.get_current_user()
		transaction_type = str(self.request.get('type'))
		view = str(self.request.get('view'))
		key = str(self.request.get('key'))
		if user:
			values = set_user_values(user,users,'/transactions?view=create')
			if view=='create':
				self.render_html('create-transaction-invoice.html',values)
			else:
				self.render_html('transactions.html',values)
		else:
			self.redirect(users.create_login_url(self.request.uri))

class TransactionLoansHandler(BaseHandler):
	def get(self):
		user = users.get_current_user()
		transaction_type = str(self.request.get('type'))
		view = str(self.request.get('view'))
		transactionKey = str(self.request.get('transaction'))
		if user:
			if view=='create':
				values = set_user_values(user,users,'/transactions/loans?view=create')
				values['customers'] = Customers.query().fetch()
				self.render_html('create-transaction-loan.html',values)
			elif view=='edit':
				values = set_user_values(user,users,'/transactions/loans?view=edit')
				self.render_html('edit-transaction-loan.html',values)
			elif view=='info':
				values = set_user_values(user,users,'/transactions/loans?view=info')
				transaction = ndb.Key(urlsafe=transactionKey).get()
				values['transaction'] = transaction
				values['customer'] = transaction
				# values['customer'] = ndb.Key(urlsafe=transaction.customer)
				self.render_html('info-transaction-loan.html',values)
			elif view=="resource":
				values = set_user_values(user,users,'/transactions/loans?view=resource')
				transaction = ndb.Key(urlsafe=transactionKey).get()
				values['transaction'] = createJsonResource(transaction)
				self.render_html('resource-transaction-loan.json',values)
			else:
				values = set_user_values(user,users,'/transactions/loans')
				self.render_html('transactions.html',values)
		else:
			self.redirect(users.create_login_url(self.request.uri))

	def post(self):
		user = users.get_current_user()
		view = str(self.request.get('view'))
		if user:
			if view=='create':
				values = set_user_values(user,users,'/transactions/loans?view=create')
				category = str(self.request.get('category'))
				transaction = Transactions(
					transactionType = 'Loan',
					transactionNumber = str(self.request.get('loanNumber')),
					# customer = ndb.Key(urlsafe=str(self.request.get('customerKey')),
					category = category,
					electronics = ItemCategoryElectronics(
						brandName = str(self.request.get('brandName')),
						modelNumber = str(self.request.get('modelNumber')),
						serialNumber = str(self.request.get('serialNumber'))
					),
					jewelry = ItemCategoryJewelry(
						karat = str(self.request.get('karat')),
						deadWeight = str(self.request.get('deadWeight')),
						grams = str(self.request.get('grams')),
						ounces = str(self.request.get('ounces')),
						counts = str(self.request.get('counts'))
					),
					musical = ItemCategoryMusical(
						instrumentBrand = str(self.request.get('instrumentBrand')),
						instrumentKind = str(self.request.get('instrumentKind'))
					),
					gun = ItemCategoryGun(
						gunCaliber = str(self.request.get('gunCaliber')),
						gunType = str(self.request.get('gunType')),
						gunAction = str(self.request.get('gunAction'))
					),
					customer = ndb.Key(urlsafe=str(self.request.get('customerKey'))),
					description = str(self.request.get('description')),
					principalAmount = 0.00 if str(self.request.get('principalAmount'))=='' else float(self.request.get('principalAmount')),
					setupFee = 0.00 if str(self.request.get('setupFee'))=='' else float(self.request.get('setupFee')),
					insuranceFee = 0.00 if str(self.request.get('insuranceFee'))=='' else float(self.request.get('insuranceFee')),
					total = 0.00 if str(self.request.get('total'))=='' else float(self.request.get('total')),
					status = 'Active'
				)
				transaction.put()
				self.render_html('info-transaction-loan.html',values)
			elif view=='edit':
				values = set_user_values(user,users,'/transactions/loans?view=edit')
				self.render_html('edit-transaction-loan.html',values)
			else:
				self.render_html('transactions.html',values)
		else:
			self.redirect(users.create_login_url(self.request.uri))


class TransactionReceiptsHandler(BaseHandler):
	def get(self):
		user = users.get_current_user()
		transaction_type = str(self.request.get('type'))
		view = str(self.request.get('view'))
		key = str(self.request.get('key'))
		if user:
			values = set_user_values(user,users,'/transactions/receipts?view=create')
			if view=='create':
				self.render_html('create-transaction-receipt.html',values)
			else:
				self.render_html('transactions.html',values)
		else:
			self.redirect(users.create_login_url(self.request.uri))
		

class TransactionRedeemsHandler(BaseHandler):
	def get(self):
		user = users.get_current_user()
		transaction_type = str(self.request.get('type'))
		view = str(self.request.get('view'))
		key = str(self.request.get('key'))
		if user:
			values = set_user_values(user,users,'/transactions/redeems?view=create')
			if view=='create':
				self.render_html('create-transaction-redeem.html',values)
			else:
				self.render_html('transactions.html',values)
		else:
			self.redirect(users.create_login_url(self.request.uri))
		

class TransactionStocksHandler(BaseHandler):
	def get(self):
		user = users.get_current_user()
		transaction_type = str(self.request.get('type'))
		view = str(self.request.get('view'))
		key = str(self.request.get('key'))
		if user:
			values = set_user_values(user,users,'/transactions/stocks?view=create')
			if view=='create':
				self.render_html('create-transaction-stock.html',values)
			else:
				self.render_html('transactions.html',values)
		else:
			self.redirect(users.create_login_url(self.request.uri))



class ItemsHandler(BaseHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			values = set_user_values(user,users,'/items')
			self.render_html('items.html',values)
		else:
			self.redirect(users.create_login_url(self.request.uri))


class ReportsHandler(BaseHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			values = set_user_values(user,users,'/reports')
			self.render_html('reports.html',values)
		else:
			self.redirect(users.create_login_url(self.request.uri))

class SettingsHandler(BaseHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			values = set_user_values(user,users,'/settings')
			view = str(self.request.get('view'))
			if view=='add':
				self.render_html('settings.html',values)
			elif view=='edit':
				self.render_html('settings.html',values)
			elif view=='info':
				self.render_html('settings.html',values)
			else:
				values['settings'] = checkSettings()
				self.render_html('settings.html',values)
		else:
			self.redirect(users.create_login_url(self.request.uri))

	def post(self):
		user = users.get_current_user()
		if user:
			values = set_user_values(user,users,'/settings')
			view = str(self.request.get('view'))
			if view=='edit':
				multi_settings = []
				settings = self.request.params.items()
				# for i,setting in enumerate(settings):
				# 	multi_settings[i] = Settings(name=setting)
				settingsKey = ndb.put_multi(multi_settings)
				values['demo'] = multi_settings # settingsKey
				values['settings'] = Settings.query()
				self.render_html('settings.html',values)
			elif view=='info':
				self.render_html('settings.html',values)
			else:
				self.render_html('settings.html',values)
		else:
			self.redirect(users.create_login_url(self.request.uri))


''' Delete Handlers '''
class StoresDeleteHandler(BaseHandler):
	def get(self,storesUrlSafe):
		user = users.get_current_user()
		if user:
			ndb.Key(urlsafe=storesUrlSafe).delete()
			self.redirect('/stores')
		else:
			self.redirect('/stores')


class DbUsersDeleteHandler(BaseHandler):
	def get(self,userUrlSafe):
		user = users.get_current_user()
		if user:
			ndb.Key(urlsafe=userUrlSafe).delete()
			self.redirect('/users')
		else:
			self.redirect('/users')

class CustomersDeleteHandler(BaseHandler):
	def get(self,userUrlSafe):
		user = users.get_current_user()
		if user:
			ndb.Key(urlsafe=userUrlSafe).delete()
			self.redirect('/customers')
		else:
			self.redirect('/customers')


app = ndb.toplevel(webapp2.WSGIApplication([
    ('/', DashboardHandler),
    ('/stores/delete/(.*?)', StoresDeleteHandler),
    ('/users/delete/(.*?)', DbUsersDeleteHandler),
    ('/customers/delete/(.*?)', CustomersDeleteHandler),
    ('/stores', StoresHandler),
    ('/users', DbUsersHandler),
    ('/customers', CustomersHandler),
    ('/items', ItemsHandler),
    ('/transactions/invoices', TransactionInvoicesHandler),
    ('/transactions/loans', TransactionLoansHandler),
    ('/transactions/receipts', TransactionReceiptsHandler),
    ('/transactions/redeems', TransactionRedeemsHandler),
    ('/transactions/stocks', TransactionStocksHandler),
    ('/transactions', TransactionsHandler),
    ('/reports', ReportsHandler),
    ('/settings', SettingsHandler),
], debug=True))







