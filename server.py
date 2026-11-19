from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote, parse_qs
import json, sqlite3, uuid, os, threading, hashlib, secrets, hmac

ROOT=Path(__file__).parent.resolve(); DB=Path(os.environ.get('NEXOFLOW_DB',ROOT/'nexoflow.sqlite3')); lock=threading.Lock()
def db():
 c=sqlite3.connect(DB,timeout=10); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
def open_tenant_db(path):
 path=Path(path).resolve()
 if path==DB.resolve():
  c=db();c.isolation_level=None;return c
 path.parent.mkdir(parents=True,exist_ok=True);c=sqlite3.connect(path,timeout=10);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
 c.executescript('''CREATE TABLE IF NOT EXISTS products(id TEXT PRIMARY KEY,sku TEXT UNIQUE NOT NULL,name TEXT NOT NULL,category TEXT DEFAULT '',price REAL NOT NULL DEFAULT 0,cost REAL NOT NULL DEFAULT 0,stock REAL NOT NULL DEFAULT 0,min_stock REAL NOT NULL DEFAULT 0,barcode TEXT DEFAULT '',variant TEXT DEFAULT '',lot TEXT DEFAULT '',expiry_date TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP);CREATE TABLE IF NOT EXISTS customers(id TEXT PRIMARY KEY,name TEXT NOT NULL,email TEXT DEFAULT '',phone TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP);CREATE TABLE IF NOT EXISTS sales(id TEXT PRIMARY KEY,number INTEGER UNIQUE NOT NULL,customer TEXT DEFAULT '',channel TEXT DEFAULT 'PDV',total REAL NOT NULL,status TEXT DEFAULT 'paid',created_at TEXT DEFAULT CURRENT_TIMESTAMP);CREATE TABLE IF NOT EXISTS sale_items(id TEXT PRIMARY KEY,sale_id TEXT NOT NULL REFERENCES sales(id),product_id TEXT REFERENCES products(id),description TEXT NOT NULL,quantity REAL NOT NULL,unit_price REAL NOT NULL);CREATE TABLE IF NOT EXISTS movements(id TEXT PRIMARY KEY,product_id TEXT NOT NULL REFERENCES products(id),kind TEXT NOT NULL,quantity REAL NOT NULL,note TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP);CREATE TABLE IF NOT EXISTS finance(id TEXT PRIMARY KEY,description TEXT NOT NULL,kind TEXT NOT NULL,due_date TEXT DEFAULT '',category TEXT DEFAULT '',amount REAL NOT NULL,status TEXT DEFAULT 'open',created_at TEXT DEFAULT CURRENT_TIMESTAMP);CREATE TABLE IF NOT EXISTS xml_imports(id TEXT PRIMARY KEY,filename TEXT NOT NULL,supplier TEXT DEFAULT '',invoice_number TEXT DEFAULT '',total REAL DEFAULT 0,payload TEXT NOT NULL,status TEXT DEFAULT 'review',created_at TEXT DEFAULT CURRENT_TIMESTAMP);CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);CREATE TABLE IF NOT EXISTS operations(id TEXT PRIMARY KEY,kind TEXT NOT NULL,title TEXT NOT NULL,status TEXT DEFAULT 'open',payload TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);CREATE TABLE IF NOT EXISTS locations(id TEXT PRIMARY KEY,name TEXT UNIQUE NOT NULL);CREATE TABLE IF NOT EXISTS product_locations(product_id TEXT NOT NULL REFERENCES products(id),location_id TEXT NOT NULL REFERENCES locations(id),quantity REAL NOT NULL DEFAULT 0,PRIMARY KEY(product_id,location_id));''')
 c.execute("INSERT OR IGNORE INTO locations(id,name) VALUES('loc-main','Loja principal'),('loc-north','Filial 2')");c.isolation_level=None;return c
def init():
 with db() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS products(id TEXT PRIMARY KEY,sku TEXT UNIQUE NOT NULL,name TEXT NOT NULL,category TEXT DEFAULT '',price REAL NOT NULL DEFAULT 0,cost REAL NOT NULL DEFAULT 0,stock REAL NOT NULL DEFAULT 0,min_stock REAL NOT NULL DEFAULT 0,barcode TEXT DEFAULT '',variant TEXT DEFAULT '',lot TEXT DEFAULT '',expiry_date TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS customers(id TEXT PRIMARY KEY,name TEXT NOT NULL,email TEXT DEFAULT '',phone TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS sales(id TEXT PRIMARY KEY,number INTEGER UNIQUE NOT NULL,customer TEXT DEFAULT '',channel TEXT DEFAULT 'PDV',total REAL NOT NULL,status TEXT DEFAULT 'paid',created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS sale_items(id TEXT PRIMARY KEY,sale_id TEXT NOT NULL REFERENCES sales(id),product_id TEXT REFERENCES products(id),description TEXT NOT NULL,quantity REAL NOT NULL,unit_price REAL NOT NULL); CREATE TABLE IF NOT EXISTS movements(id TEXT PRIMARY KEY,product_id TEXT NOT NULL REFERENCES products(id),kind TEXT NOT NULL,quantity REAL NOT NULL,note TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS finance(id TEXT PRIMARY KEY,description TEXT NOT NULL,kind TEXT NOT NULL,due_date TEXT DEFAULT '',category TEXT DEFAULT '',amount REAL NOT NULL,status TEXT DEFAULT 'open',created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS xml_imports(id TEXT PRIMARY KEY,filename TEXT NOT NULL,supplier TEXT DEFAULT '',invoice_number TEXT DEFAULT '',total REAL DEFAULT 0,payload TEXT NOT NULL,status TEXT DEFAULT 'review',created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE IF NOT EXISTS operations(id TEXT PRIMARY KEY,kind TEXT NOT NULL,title TEXT NOT NULL,status TEXT DEFAULT 'open',payload TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS locations(id TEXT PRIMARY KEY,name TEXT UNIQUE NOT NULL); CREATE TABLE IF NOT EXISTS product_locations(product_id TEXT NOT NULL REFERENCES products(id),location_id TEXT NOT NULL REFERENCES locations(id),quantity REAL NOT NULL DEFAULT 0,PRIMARY KEY(product_id,location_id)); CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'Operador',status TEXT NOT NULL DEFAULT 'Ativo',last_access TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS access_logs(id TEXT PRIMARY KEY,user_id TEXT,email TEXT NOT NULL,event TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),expires_at TEXT NOT NULL);''')
  c.executescript('''CREATE TABLE IF NOT EXISTS tenants(id TEXT PRIMARY KEY,name TEXT NOT NULL,owner_email TEXT DEFAULT '',plan TEXT NOT NULL DEFAULT 'pro',status TEXT NOT NULL DEFAULT 'Ativo',db_file TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS plans(code TEXT PRIMARY KEY,name TEXT NOT NULL,price REAL NOT NULL,description TEXT NOT NULL,features TEXT NOT NULL,highlighted INTEGER NOT NULL DEFAULT 0);''')
  user_columns={row['name'] for row in c.execute('PRAGMA table_info(users)').fetchall()}
  if 'tenant_id' not in user_columns:c.execute('ALTER TABLE users ADD COLUMN tenant_id TEXT')
  c.execute("INSERT OR IGNORE INTO tenants(id,name,plan,status,db_file) VALUES('tenant-main','Vértice Comércio','pro','Ativo',?)",(DB.name,))
  defaults=[('start','Essencial',79,'Para começar a organizar a operação.',json.dumps(['Vendas e PDV','Estoque e produtos','Financeiro essencial'],ensure_ascii=False),0),('pro','Pro',149,'Mais controle para uma equipe em crescimento.',json.dumps(['Tudo do Essencial','XML e compras','Relatórios e serviços'],ensure_ascii=False),1),('multi','Multiunidade',299,'Gestão integrada para várias lojas.',json.dumps(['Tudo do Pro','Múltiplas unidades','Acessos e indicadores avançados'],ensure_ascii=False),0)]
  for plan in defaults:c.execute('INSERT OR IGNORE INTO plans(code,name,price,description,features,highlighted) VALUES(?,?,?,?,?,?)',plan)
  c.execute("UPDATE users SET tenant_id='tenant-main' WHERE tenant_id IS NULL")
  legacy=c.execute("SELECT id FROM users WHERE role IN ('Administrador','Administradora') ORDER BY created_at LIMIT 1").fetchone()
  if legacy and not c.execute("SELECT 1 FROM users WHERE role='Superadmin'").fetchone():c.execute("UPDATE users SET role='Superadmin' WHERE id=?",(legacy['id'],))
  admin_email=os.environ.get('NEXOFLOW_SUPERADMIN_EMAIL','').strip().lower();admin_password=os.environ.get('NEXOFLOW_SUPERADMIN_PASSWORD','')
  if admin_email and admin_password and len(admin_password)>=12:
   superadmin=c.execute("SELECT id,email FROM users WHERE role='Superadmin' ORDER BY created_at LIMIT 1").fetchone()
   if not superadmin:
    sid=str(uuid.uuid4());salt=secrets.token_hex(16);digest=hashlib.pbkdf2_hmac('sha256',admin_password.encode(),salt.encode(),240000).hex();c.execute("INSERT OR IGNORE INTO users(id,name,email,password_hash,role,tenant_id) VALUES(?,?,?,?,?,?)",(sid,'Administrador da Plataforma',admin_email,f'pbkdf2_sha256${salt}${digest}','Superadmin','tenant-main'));c.execute('INSERT INTO access_logs(id,user_id,email,event) VALUES(?,?,?,?)',(str(uuid.uuid4()),sid,admin_email,'Superadmin configurado no servidor'))
   elif superadmin['email'].lower()!=admin_email and not c.execute('SELECT 1 FROM users WHERE email=?',(admin_email,)).fetchone():
    c.execute("UPDATE users SET email=? WHERE id=?",(admin_email,superadmin['id']))
  existing={row['name'] for row in c.execute('PRAGMA table_info(products)').fetchall()}
  for column,definition in [('barcode',"TEXT DEFAULT ''"),('variant',"TEXT DEFAULT ''"),('lot',"TEXT DEFAULT ''"),('expiry_date',"TEXT DEFAULT ''")]:
   if column not in existing:c.execute(f'ALTER TABLE products ADD COLUMN {column} {definition}')
  if c.execute('SELECT COUNT(*) FROM products').fetchone()[0]==0:
   for p in [('FON-2041','Fone Bluetooth Wave Pro','Eletrônicos',249.9,130,34,8),('GAR-1180','Garrafa Térmica Inox 750ml','Acessórios',89.9,42,4,8),('MOC-0902','Mochila Urbana Compact','Bolsas',179,88,21,5)]: c.execute('INSERT INTO products(id,sku,name,category,price,cost,stock,min_stock) VALUES(?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),*p))
  c.execute("INSERT OR IGNORE INTO locations(id,name) VALUES('loc-main','Loja Centro'),('loc-north','Filial Norte')")
  for row in c.execute('SELECT id,stock FROM products').fetchall(): c.execute("INSERT OR IGNORE INTO product_locations(product_id,location_id,quantity) VALUES(?,?,?)",(row['id'],'loc-main',row['stock']))
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw): super().__init__(*a,directory=str(ROOT),**kw)
 def log_message(self,*a): pass
 def send_json(self,obj,status=200,cookie=None):
  body=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.send_header('Access-Control-Allow-Origin','*')
  if cookie:
   if self.headers.get('X-Forwarded-Proto','').lower()=='https':cookie+='; Secure'
   self.send_header('Set-Cookie',cookie)
  self.end_headers(); self.wfile.write(body)
 def current_user(self,c):
  from http.cookies import SimpleCookie
  jar=SimpleCookie(); jar.load(self.headers.get('Cookie','')); morsel=jar.get('nf_session')
  if not morsel:return None
  return c.execute("SELECT u.id,u.name,u.email,u.role,u.tenant_id,t.name company,t.status tenant_status FROM sessions s JOIN users u ON u.id=s.user_id LEFT JOIN tenants t ON t.id=u.tenant_id WHERE s.token=? AND s.expires_at>CURRENT_TIMESTAMP AND u.status='Ativo' AND (t.status='Ativo' OR u.role='Superadmin')",(morsel.value,)).fetchone()
 def current_admin(self,c):
  user=self.current_user(c)
  return user if user and user['role'] in ('Administrador','Administradora','Superadmin') else None
 def current_superadmin(self,c):
  user=self.current_user(c)
  return user if user and user['role']=='Superadmin' else None
 def request_db(self,path):
  central=db()
  if path.startswith('/api/auth/') or path.startswith('/api/platform/') or path in ('/api/users','/api/access-logs','/api/admin-state','/api/me','/api/public/plans'):
   return central
  user=self.current_user(central)
  if user and user['tenant_id']:
   tenant=central.execute('SELECT db_file FROM tenants WHERE id=?',(user['tenant_id'],)).fetchone()
   if tenant:
    db_file=tenant['db_file'];central.close()
    return open_tenant_db(DB.parent/db_file)
  return central
 def read_json(self): return json.loads(self.rfile.read(int(self.headers.get('Content-Length',0)) or 0) or b'{}')
 def do_OPTIONS(self): self.send_response(204); self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Access-Control-Allow-Methods','GET,POST,PUT,DELETE,OPTIONS'); self.send_header('Access-Control-Allow-Headers','Content-Type'); self.end_headers()
 def do_GET(self):
  url=urlparse(self.path); path=unquote(url.path)
  if path=='/api/health':
   with db() as c:
    admin=c.execute("SELECT email FROM users WHERE role='Superadmin' ORDER BY created_at LIMIT 1").fetchone()
    return self.send_json({'ok':True,'database':'SQLite','app':'NexoFlow','superadmin_configured':bool(admin),'superadmin_email':admin['email'] if admin else None,'database_path':str(DB)})
  if path in ('/admin','/admin.html'):
   with db() as c:
    if not self.current_superadmin(c):self.send_response(302);self.send_header('Location','/login.html?next=admin');self.end_headers();return
   self.path='/admin.html';return super().do_GET()
  if path.startswith('/api/'):
   with db() as auth:
    has_users=bool(auth.execute('SELECT COUNT(*) FROM users').fetchone()[0]); actor=self.current_user(auth)
    if has_users and path not in ('/api/health','/api/admin-state','/api/me','/api/public/plans','/api/auth/login','/api/auth/signup') and not actor and path not in ('/api/users','/api/access-logs'):
     return self.send_json({'error':'Sua sessão expirou. Entre novamente para continuar.'},401)
    if path=='/api/admin-state':return self.send_json({'has_admin':bool(auth.execute("SELECT COUNT(*) FROM users WHERE role IN ('Administrador','Administradora','Superadmin')").fetchone()[0])})
    if path=='/api/me':
     if not actor:return self.send_json({'error':'Faça login para continuar.'},401)
     return self.send_json({'id':actor['id'],'name':actor['name'],'email':actor['email'],'role':actor['role'],'tenant_id':actor['tenant_id'],'company':actor['company'],'is_superadmin':actor['role']=='Superadmin'})
    if path=='/api/public/plans':return self.send_json([dict(x)|{'features':json.loads(x['features'])} for x in auth.execute('SELECT * FROM plans ORDER BY price').fetchall()])
    if path.startswith('/api/platform/'):
     if not self.current_superadmin(auth):return self.send_json({'error':'A área da plataforma é exclusiva do administrador NexoFlow.'},403)
     if path=='/api/platform/plans':return self.send_json([dict(x)|{'features':json.loads(x['features'])} for x in auth.execute('SELECT * FROM plans ORDER BY price').fetchall()])
     if path=='/api/platform/access-logs':return self.send_json([dict(x) for x in auth.execute('SELECT email,event,created_at FROM access_logs ORDER BY created_at DESC LIMIT 200').fetchall()])
     if path=='/api/platform/users':return self.send_json([dict(x) for x in auth.execute('SELECT u.id,u.name,u.email,u.role,u.status,u.last_access,t.name company FROM users u LEFT JOIN tenants t ON t.id=u.tenant_id ORDER BY u.created_at DESC').fetchall()])
     if path=='/api/platform/overview':
      return self.send_json({'tenants':auth.execute('SELECT COUNT(*) FROM tenants').fetchone()[0],'active':auth.execute("SELECT COUNT(*) FROM tenants WHERE status='Ativo'").fetchone()[0],'users':auth.execute('SELECT COUNT(*) FROM users').fetchone()[0],'monthly':auth.execute("SELECT COALESCE(SUM(p.price),0) FROM tenants t JOIN plans p ON p.code=t.plan WHERE t.status='Ativo'").fetchone()[0]})
     if path=='/api/platform/tenants':
      rows=auth.execute('SELECT t.*,p.name plan_name,p.price,(SELECT COUNT(*) FROM users u WHERE u.tenant_id=t.id) user_count FROM tenants t LEFT JOIN plans p ON p.code=t.plan ORDER BY t.created_at DESC').fetchall();return self.send_json([dict(x) for x in rows])
     return self.send_json({'error':'Rota administrativa não encontrada.'},404)
   if path in ('/api/auth/login','/api/auth/logout','/api/auth/signup'):return self.send_json({'error':'Use POST neste endpoint.'},405)
   with self.request_db(path) as c:
    routes={'/api/products':'SELECT * FROM products ORDER BY name','/api/sales':'SELECT * FROM sales ORDER BY number DESC LIMIT 100','/api/finance':'SELECT * FROM finance ORDER BY due_date','/api/movements':'SELECT m.*,p.name product FROM movements m JOIN products p ON p.id=m.product_id ORDER BY m.created_at DESC LIMIT 100','/api/xml':'SELECT id,filename,supplier,invoice_number,total,status,created_at FROM xml_imports ORDER BY created_at DESC'}
    if path=='/api/locations':return self.send_json([dict(x) for x in c.execute('SELECT * FROM locations ORDER BY name').fetchall()])
    if path=='/api/users':
     if not actor:return self.send_json({'error':'Faça login para continuar.'},401)
     if not self.current_admin(auth):return self.send_json({'error':'Somente o administrador da empresa pode gerenciar usuários.'},403)
     return self.send_json([dict(x) for x in auth.execute('SELECT id,name,email,role,status,last_access,created_at FROM users WHERE tenant_id=? ORDER BY created_at DESC',(actor['tenant_id'],)).fetchall()])
    if path=='/api/access-logs':
     if not actor:return self.send_json({'error':'Faça login para continuar.'},401)
     if not self.current_admin(auth):return self.send_json({'error':'Somente o administrador da empresa pode consultar os acessos.'},403)
     return self.send_json([dict(x) for x in auth.execute('SELECT id,email,event,created_at FROM access_logs WHERE user_id IN (SELECT id FROM users WHERE tenant_id=?) ORDER BY created_at DESC LIMIT 100',(actor['tenant_id'],)).fetchall()])
    if path=='/api/stock-by-location':return self.send_json([dict(x) for x in c.execute('SELECT p.name product,l.name location,pl.quantity FROM product_locations pl JOIN products p ON p.id=pl.product_id JOIN locations l ON l.id=pl.location_id ORDER BY p.name,l.name').fetchall()])
    if path=='/api/operations':
     kind=parse_qs(url.query).get('kind',[''])[0]; rows=c.execute('SELECT * FROM operations WHERE kind=? ORDER BY created_at DESC',(kind,)).fetchall() if kind else c.execute('SELECT * FROM operations ORDER BY created_at DESC').fetchall(); return self.send_json([dict(x) | {'payload':json.loads(x['payload'])} for x in rows])
    if path=='/api/dashboard':
     return self.send_json({'products':c.execute('SELECT COUNT(*) FROM products').fetchone()[0],'lowStock':c.execute('SELECT COUNT(*) FROM products WHERE stock<=min_stock').fetchone()[0],'sales':c.execute("SELECT COALESCE(SUM(total),0) FROM sales WHERE date(created_at)=date('now','localtime')").fetchone()[0],'orders':c.execute("SELECT COUNT(*) FROM sales WHERE date(created_at)=date('now','localtime')").fetchone()[0],'financeOpen':c.execute("SELECT COALESCE(SUM(amount),0) FROM finance WHERE status='open'").fetchone()[0]})
    if path in routes:return self.send_json([dict(x) for x in c.execute(routes[path]).fetchall()])
    if path.startswith('/api/settings/'): 
     row=c.execute('SELECT value FROM settings WHERE key=?',(path.rsplit('/',1)[-1],)).fetchone(); return self.send_json(json.loads(row['value']) if row else {})
   return self.send_json({'error':'Rota não encontrada'},404)
  if path=='/': path='/sales-page.html'; self.path='/sales-page.html'
  if path=='/signup.html':self.path='/login.html'
  if path in ('/index.html','/app.html'):
   actor=None
   with db() as c:
    actor=self.current_user(c);has_users=bool(c.execute('SELECT COUNT(*) FROM users').fetchone()[0])
    if has_users and not actor:self.send_response(302);self.send_header('Location','/login.html');self.end_headers();return
    self.path='/index.html'
   if self.path=='/index.html':
    if actor and actor['role']=='Superadmin':self.path='/admin.html'
  return super().do_GET()
 def do_POST(self):
  path=unquote(urlparse(self.path).path); data=self.read_json()
  try:
   with lock,db() as c:
    has_users=bool(c.execute('SELECT COUNT(*) FROM users').fetchone()[0]);actor=self.current_user(c)
    if has_users and path not in ('/api/auth/login','/api/auth/logout','/api/auth/signup','/api/users') and not actor:
     return self.send_json({'error':'Sua sessão expirou. Entre novamente para continuar.'},401)
    if path=='/api/auth/logout':
     from http.cookies import SimpleCookie
     jar=SimpleCookie();jar.load(self.headers.get('Cookie',''));m=jar.get('nf_session')
     if m:c.execute('DELETE FROM sessions WHERE token=?',(m.value,))
     return self.send_json({'ok':True},cookie='nf_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0')
    if path=='/api/auth/signup':
     email=(data.get('email') or '').strip().lower();name=(data.get('name') or '').strip();company=(data.get('company') or '').strip();password=data.get('password') or '';plan=data.get('plan') or 'start'
     if not name or not company or '@' not in email:return self.send_json({'error':'Preencha nome, empresa e e-mail válido.'},400)
     if len(password)<8:return self.send_json({'error':'Use uma senha com pelo menos 8 caracteres.'},400)
     if not c.execute('SELECT 1 FROM plans WHERE code=?',(plan,)).fetchone():return self.send_json({'error':'Plano não encontrado.'},400)
     if c.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone():return self.send_json({'error':'Já existe uma conta com este e-mail.'},409)
     tid=str(uuid.uuid4());uid=str(uuid.uuid4());db_file=f'tenants/{tid}.sqlite3';salt=secrets.token_hex(16);digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),240000).hex()
     c.execute('INSERT INTO tenants(id,name,owner_email,plan,status,db_file) VALUES(?,?,?,?,?,?)',(tid,company,email,plan,'Ativo',db_file));c.execute('INSERT INTO users(id,name,email,password_hash,role,tenant_id) VALUES(?,?,?,?,?,?)',(uid,name,email,f'pbkdf2_sha256${salt}${digest}','Administrador',tid));c.execute('INSERT INTO access_logs(id,user_id,email,event) VALUES(?,?,?,?)',(str(uuid.uuid4()),uid,email,'Conta criada'))
     tenant_conn=open_tenant_db(DB.parent/db_file);tenant_conn.close()
     token=secrets.token_urlsafe(32);c.execute("INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,datetime('now','+12 hours'))",(token,uid))
     return self.send_json({'ok':True,'user':{'name':name,'email':email,'role':'Administrador','company':company}},201,cookie=f'nf_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=43200')
    if path=='/api/platform/tenants' and self.current_superadmin(c):
     name=(data.get('name') or '').strip();email=(data.get('email') or '').strip().lower();plan=data.get('plan') or 'start';password=data.get('password') or ''
     if not name or '@' not in email or len(password)<8:return self.send_json({'error':'Informe empresa, e-mail válido e senha inicial de 8 caracteres.'},400)
     if c.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone():return self.send_json({'error':'Já existe uma conta com este e-mail.'},409)
     tid=str(uuid.uuid4());uid=str(uuid.uuid4());db_file=f'tenants/{tid}.sqlite3';salt=secrets.token_hex(16);digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),240000).hex();c.execute('INSERT INTO tenants(id,name,owner_email,plan,status,db_file) VALUES(?,?,?,?,?,?)',(tid,name,email,plan,'Ativo',db_file));c.execute('INSERT INTO users(id,name,email,password_hash,role,tenant_id) VALUES(?,?,?,?,?,?)',(uid,name,email,f'pbkdf2_sha256${salt}${digest}','Administrador',tid));c.execute('INSERT INTO access_logs(id,user_id,email,event) VALUES(?,?,?,?)',(str(uuid.uuid4()),uid,email,'Conta criada pelo superadmin'))
     tenant_conn=open_tenant_db(DB.parent/db_file);tenant_conn.close()
     return self.send_json({'id':tid,'name':name,'email':email,'plan':plan,'status':'Ativo'},201)
    if path=='/api/auth/login':
     email=(data.get('email') or '').strip().lower(); password=data.get('password') or ''; user=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
     if not user or user['status']!='Ativo':return self.send_json({'error':'Acesso não encontrado ou suspenso.'},401)
     try:_,salt,expected=user['password_hash'].split('$',2)
     except ValueError:return self.send_json({'error':'Credencial inválida.'},401)
     actual=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),240000).hex()
     if not hmac.compare_digest(actual,expected):return self.send_json({'error':'E-mail ou senha incorretos.'},401)
     token=secrets.token_urlsafe(32);c.execute("INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,datetime('now','+12 hours'))",(token,user['id']));c.execute("UPDATE users SET last_access=CURRENT_TIMESTAMP WHERE id=?",(user['id'],));c.execute('INSERT INTO access_logs(id,user_id,email,event) VALUES(?,?,?,?)',(str(uuid.uuid4()),user['id'],email,'Login realizado'))
     return self.send_json({'ok':True,'user':{'name':user['name'],'email':email,'role':user['role'],'company':c.execute('SELECT name FROM tenants WHERE id=?',(user['tenant_id'],)).fetchone()['name'] if user['tenant_id'] else ''}},cookie=f'nf_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=43200')
    if path=='/api/users':
     name=(data.get('name') or '').strip(); email=(data.get('email') or '').strip().lower(); password=data.get('password') or ''; role=(data.get('role') or 'Operador').strip()
     if not name or not email or '@' not in email:return self.send_json({'error':'Informe nome e um e-mail válido.'},400)
     if len(password)<8:return self.send_json({'error':'A senha inicial precisa ter pelo menos 8 caracteres.'},400)
     if not actor or not self.current_admin(c):return self.send_json({'error':'Entre como administrador da empresa para criar acessos.'},401)
     salt=secrets.token_hex(16); digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),240000).hex(); uid=str(uuid.uuid4())
     c.execute('INSERT INTO users(id,name,email,password_hash,role,tenant_id) VALUES(?,?,?,?,?,?)',(uid,name,email,f'pbkdf2_sha256${salt}${digest}',role,actor['tenant_id']))
     c.execute('INSERT INTO access_logs(id,user_id,email,event) VALUES(?,?,?,?)',(str(uuid.uuid4()),uid,email,'Acesso criado'))
     return self.send_json({'id':uid,'name':name,'email':email,'role':role,'status':'Ativo'},201)
    if path.startswith('/api/platform/'):
     if not self.current_superadmin(c):return self.send_json({'error':'A área da plataforma é exclusiva do administrador NexoFlow.'},403)
     if path.startswith('/api/platform/tenants/'):
      tid=path.rsplit('/',1)[-1];status=data.get('status')
      if status not in ('Ativo','Suspenso'):return self.send_json({'error':'Status de empresa inválido.'},400)
      c.execute('UPDATE tenants SET status=? WHERE id=?',(status,tid));return self.send_json({'ok':True})
     if path.startswith('/api/platform/plans/'):
      code=path.rsplit('/',1)[-1];price=float(data.get('price') or 0)
      if price<0:return self.send_json({'error':'Preço inválido.'},400)
      c.execute('UPDATE plans SET price=? WHERE code=?',(price,code));return self.send_json({'ok':True})
     return self.send_json({'error':'Rota administrativa não encontrada.'},404)
    c=self.request_db(path)
    if path=='/api/operations':
     kind=(data.get('kind') or 'note').strip(); title=(data.get('title') or '').strip()
     if not title:return self.send_json({'error':'Informe um título para o registro.'},400)
     oid=str(uuid.uuid4()); c.execute('INSERT INTO operations(id,kind,title,status,payload) VALUES(?,?,?,?,?)',(oid,kind,title,data.get('status','open'),json.dumps(data.get('payload') or {},ensure_ascii=False))); return self.send_json({'id':oid,'kind':kind,'title':title,'status':data.get('status','open')},201)
    if path=='/api/products':
     sku=(data.get('sku') or '').strip(); name=(data.get('name') or '').strip()
     if not sku or not name: return self.send_json({'error':'Informe SKU e nome do produto.'},400)
     pid=str(uuid.uuid4()); initial=float(data.get('stock') or 0); c.execute('INSERT INTO products(id,sku,name,category,price,cost,stock,min_stock,barcode,variant,lot,expiry_date) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(pid,sku,name,data.get('category',''),float(data.get('price') or 0),float(data.get('cost') or 0),initial,float(data.get('min_stock') or 0),data.get('barcode',''),data.get('variant',''),data.get('lot',''),data.get('expiry_date',''))); c.execute("INSERT INTO product_locations(product_id,location_id,quantity) VALUES(?,?,?)",(pid,'loc-main',initial)); return self.send_json({'id':pid},201)
    if path.startswith('/api/sales/') and path.endswith('/convert'):
     sid=path.split('/')[-2]; sale=c.execute("SELECT * FROM sales WHERE id=? AND status='quote'",(sid,)).fetchone()
     if not sale:return self.send_json({'error':'Este orçamento não está mais aguardando aprovação.'},409)
     items=c.execute('SELECT * FROM sale_items WHERE sale_id=?',(sid,)).fetchall(); normalized=[]
     for item in items:
      product=c.execute('SELECT * FROM products WHERE id=?',(item['product_id'],)).fetchone()
      if not product or product['stock']<item['quantity']:return self.send_json({'error':f"Estoque insuficiente para {item['description']} ao converter o orçamento."},409)
      normalized.append((product,item))
     for product,item in normalized:
      c.execute('UPDATE products SET stock=stock-? WHERE id=?',(item['quantity'],product['id']));c.execute("UPDATE product_locations SET quantity=quantity-? WHERE product_id=? AND location_id='loc-main'",(item['quantity'],product['id']));c.execute('INSERT INTO movements(id,product_id,kind,quantity,note) VALUES(?,?,?,?,?)',(str(uuid.uuid4()),product['id'],'sale',-item['quantity'],f"Orçamento #{sale['number']} convertido"))
     c.execute("UPDATE sales SET status='paid' WHERE id=?",(sid,));return self.send_json({'ok':True,'number':sale['number']})
    if path=='/api/sales':
     items=data.get('items') or []
     if not items:return self.send_json({'error':'Adicione pelo menos um produto.'},400)
     total=0; normalized=[]
     for item in items:
      product=c.execute('SELECT * FROM products WHERE id=? OR sku=?',(item.get('product_id'),item.get('sku'))).fetchone(); qty=float(item.get('quantity') or 1)
      if product:
       if data.get('status')!='quote' and product['stock']<qty:return self.send_json({'error':f"Estoque insuficiente para {product['name']} (disponível: {product['stock']:g})."},409)
       price=float(item.get('unit_price') if item.get('unit_price') is not None else product['price']); normalized.append((product,qty,price)); total+=qty*price
      else:return self.send_json({'error':'Produto não encontrado no catálogo.'},404)
     number=c.execute('SELECT COALESCE(MAX(number),2840)+1 FROM sales').fetchone()[0]; sid=str(uuid.uuid4()); c.execute('INSERT INTO sales(id,number,customer,channel,total,status) VALUES(?,?,?,?,?,?)',(sid,number,data.get('customer','Consumidor final'),data.get('channel','PDV'),total,'quote' if data.get('status')=='quote' else 'paid'))
     for p,q,price in normalized:
      c.execute('INSERT INTO sale_items(id,sale_id,product_id,description,quantity,unit_price) VALUES(?,?,?,?,?,?)',(str(uuid.uuid4()),sid,p['id'],p['name'],q,price))
      if data.get('status')!='quote':
       c.execute('UPDATE products SET stock=stock-? WHERE id=?',(q,p['id']))
       c.execute("UPDATE product_locations SET quantity=quantity-? WHERE product_id=? AND location_id='loc-main'",(q,p['id']))
       c.execute('INSERT INTO movements(id,product_id,kind,quantity,note) VALUES(?,?,?,?,?)',(str(uuid.uuid4()),p['id'],'sale',-q,f'Venda #{number}'))
     return self.send_json({'id':sid,'number':number,'total':total},201)
    if path=='/api/transfers':
     product=c.execute('SELECT * FROM products WHERE id=?',(data.get('product_id'),)).fetchone(); qty=float(data.get('quantity') or 0); src=c.execute('SELECT * FROM locations WHERE name=?',(data.get('source'),)).fetchone(); dst=c.execute('SELECT * FROM locations WHERE name=?',(data.get('destination'),)).fetchone()
     if not product or not src or not dst or src['id']==dst['id'] or qty<=0:return self.send_json({'error':'Confira produto, quantidade e lojas de origem/destino.'},400)
     balance=c.execute('SELECT quantity FROM product_locations WHERE product_id=? AND location_id=?',(product['id'],src['id'])).fetchone(); available=balance['quantity'] if balance else 0
     if available<qty:return self.send_json({'error':f"Saldo insuficiente em {src['name']} (disponível: {available:g})."},409)
     c.execute('UPDATE product_locations SET quantity=quantity-? WHERE product_id=? AND location_id=?',(qty,product['id'],src['id']));c.execute('INSERT INTO product_locations(product_id,location_id,quantity) VALUES(?,?,?) ON CONFLICT(product_id,location_id) DO UPDATE SET quantity=quantity+excluded.quantity',(product['id'],dst['id'],qty));c.execute('INSERT INTO movements(id,product_id,kind,quantity,note) VALUES(?,?,?,?,?)',(str(uuid.uuid4()),product['id'],'transfer',qty,f"{src['name']} → {dst['name']}"));return self.send_json({'ok':True},201)
    if path=='/api/movements':
     p=c.execute('SELECT * FROM products WHERE id=?',(data.get('product_id'),)).fetchone(); qty=float(data.get('quantity') or 0); kind=data.get('kind','in')
     if not p or qty<=0:return self.send_json({'error':'Produto e quantidade válida são obrigatórios.'},400)
     delta=qty if kind=='in' else -qty
     if p['stock']+delta<0:return self.send_json({'error':'A movimentação deixaria o estoque negativo.'},409)
     c.execute('UPDATE products SET stock=stock+? WHERE id=?',(delta,p['id']));c.execute("INSERT INTO product_locations(product_id,location_id,quantity) VALUES(?, 'loc-main', ?) ON CONFLICT(product_id,location_id) DO UPDATE SET quantity=quantity+excluded.quantity",(p['id'],delta));c.execute('INSERT INTO movements(id,product_id,kind,quantity,note) VALUES(?,?,?,?,?)',(str(uuid.uuid4()),p['id'],kind,delta,data.get('note','Ajuste manual')));return self.send_json({'ok':True},201)
    if path=='/api/finance':
     desc=(data.get('description') or '').strip(); amount=float(data.get('amount') or 0)
     if not desc or amount<=0:return self.send_json({'error':'Descrição e valor maior que zero são obrigatórios.'},400)
     fid=str(uuid.uuid4());c.execute('INSERT INTO finance(id,description,kind,due_date,category,amount,status) VALUES(?,?,?,?,?,?,?)',(fid,desc,data.get('kind','pay'),data.get('due_date',''),data.get('category','Geral'),amount,'open'));return self.send_json({'id':fid},201)
    if path=='/api/xml':
     payload=data.get('payload') or {}; iid=str(uuid.uuid4());c.execute('INSERT INTO xml_imports(id,filename,supplier,invoice_number,total,payload,status) VALUES(?,?,?,?,?,?,?)',(iid,data.get('filename','nota.xml'),payload.get('supplier',''),payload.get('number',''),float(payload.get('total') or 0),json.dumps(payload,ensure_ascii=False),'review'));return self.send_json({'id':iid,'payload':payload},201)
    if path=='/api/xml/read':
     xml=data.get('xml',''); filename=data.get('filename','nota.xml')
     import xml.etree.ElementTree as ET
     root=ET.fromstring(xml); ns={'n':'http://www.portalfiscal.inf.br/nfe'}
     def first(path):
      el=root.find(path,ns); return (el.text or '').strip() if el is not None else ''
     supplier=first('.//n:emit/n:xNome'); number=first('.//n:ide/n:nNF'); total=first('.//n:ICMSTot/n:vNF')
     items=[]
     for det in root.findall('.//n:det',ns):
      prod=det.find('n:prod',ns)
      if prod is not None:
       def val(tag):
        el=prod.find('n:'+tag,ns);return (el.text or '').strip() if el is not None else ''
       items.append({'name':val('xProd'),'sku':val('cProd'),'ean':val('cEAN'),'quantity':val('qCom'),'unit_price':val('vUnCom'),'total':val('vProd')})
     payload={'supplier':supplier,'number':number,'total':float(total or 0),'items':items}
     iid=str(uuid.uuid4());c.execute('INSERT INTO xml_imports(id,filename,supplier,invoice_number,total,payload,status) VALUES(?,?,?,?,?,?,?)',(iid,filename,supplier,number,float(total or 0),json.dumps(payload,ensure_ascii=False),'review'));return self.send_json({'id':iid,'payload':payload},201)
    if path.startswith('/api/settings/'): key=path.rsplit('/',1)[-1];c.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,json.dumps(data,ensure_ascii=False)));return self.send_json({'ok':True})
    if path=='/api/xml/process':
     iid=data.get('id'); rows=data.get('items') or []; total=float(data.get('total') or 0); due=data.get('due_date',''); note=c.execute('SELECT * FROM xml_imports WHERE id=?',(iid,)).fetchone()
     if not note:return self.send_json({'error':'Nota não encontrada.'},404)
     for item in rows:
      p=c.execute('SELECT * FROM products WHERE id=?',(item.get('product_id'),)).fetchone(); qty=float(item.get('quantity') or 0)
      if not p or qty<=0:return self.send_json({'error':'Vincule cada item a um produto e informe a quantidade.'},400)
      c.execute('UPDATE products SET stock=stock+? WHERE id=?',(qty,p['id']));c.execute("INSERT INTO product_locations(product_id,location_id,quantity) VALUES(?, 'loc-main', ?) ON CONFLICT(product_id,location_id) DO UPDATE SET quantity=quantity+excluded.quantity",(p['id'],qty));c.execute('INSERT INTO movements(id,product_id,kind,quantity,note) VALUES(?,?,?,?,?)',(str(uuid.uuid4()),p['id'],'in',qty,f"Entrada da nota {note['invoice_number']}"))
     if total>0:c.execute('INSERT INTO finance(id,description,kind,due_date,category,amount,status) VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),f"Compra {note['invoice_number']} · {note['supplier']}",'pay',due,'Fornecedores',total,'open'))
     c.execute("UPDATE xml_imports SET status='processed' WHERE id=?",(iid,));return self.send_json({'ok':True})
  except sqlite3.IntegrityError as ex:return self.send_json({'error':'SKU já cadastrado ou dados relacionados inválidos.'},409)
  except (ValueError,TypeError) as ex:return self.send_json({'error':'Confira os valores informados.'},400)
 def do_PUT(self):
  path=unquote(urlparse(self.path).path); data=self.read_json()
  if path.startswith('/api/users/'):
   status=data.get('status','Suspenso')
   if status not in ('Ativo','Suspenso'):return self.send_json({'error':'Status de acesso inválido.'},400)
   uid=path.rsplit('/',1)[-1]
   with db() as c:
    if not self.current_admin(c):return self.send_json({'error':'Entre como administrador para alterar acessos.'},401)
    user=c.execute('SELECT id,email FROM users WHERE id=?',(uid,)).fetchone()
    actor=self.current_admin(c)
    if not user or not actor or c.execute('SELECT tenant_id FROM users WHERE id=?',(uid,)).fetchone()['tenant_id']!=actor['tenant_id']:return self.send_json({'error':'Acesso não encontrado nesta empresa.'},404)
    c.execute('UPDATE users SET status=? WHERE id=?',(status,uid));c.execute('INSERT INTO access_logs(id,user_id,email,event) VALUES(?,?,?,?)',(str(uuid.uuid4()),uid,user['email'],'Acesso '+('ativado' if status=='Ativo' else 'suspenso')))
    return self.send_json({'ok':True,'status':status})
  if path.startswith('/api/platform/tenants/'):
   data=self.read_json()
   with db() as c:
    if not self.current_superadmin(c):return self.send_json({'error':'A área da plataforma é exclusiva do administrador NexoFlow.'},403)
    tid=path.rsplit('/',1)[-1];status=data.get('status','Suspenso')
    if status not in ('Ativo','Suspenso'):return self.send_json({'error':'Status de empresa inválido.'},400)
    c.execute('UPDATE tenants SET status=? WHERE id=?',(status,tid));return self.send_json({'ok':True})
  if path.startswith('/api/platform/users/'):
   data=self.read_json()
   with db() as c:
    if not self.current_superadmin(c):return self.send_json({'error':'A área da plataforma é exclusiva do administrador NexoFlow.'},403)
    uid=path.rsplit('/',1)[-1];status=data.get('status','Suspenso')
    if status not in ('Ativo','Suspenso'):return self.send_json({'error':'Status de usuário inválido.'},400)
    user=c.execute('SELECT id,email FROM users WHERE id=?',(uid,)).fetchone()
    if not user:return self.send_json({'error':'Usuário não encontrado.'},404)
    c.execute('UPDATE users SET status=? WHERE id=?',(status,uid));c.execute('DELETE FROM sessions WHERE user_id=?',(uid,));c.execute('INSERT INTO access_logs(id,user_id,email,event) VALUES(?,?,?,?)',(str(uuid.uuid4()),uid,user['email'],'Conta da plataforma '+status.lower()))
    return self.send_json({'ok':True})
  if path.startswith('/api/platform/plans/'):
   data=self.read_json()
   with db() as c:
    if not self.current_superadmin(c):return self.send_json({'error':'A área da plataforma é exclusiva do administrador NexoFlow.'},403)
    code=path.rsplit('/',1)[-1]
    try:price=float(data.get('price') or 0)
    except (ValueError,TypeError):return self.send_json({'error':'Informe um preço válido.'},400)
    if price<0:return self.send_json({'error':'O preço não pode ser negativo.'},400)
    c.execute('UPDATE plans SET price=? WHERE code=?',(price,code));return self.send_json({'ok':True})
  if path.startswith('/api/operations/'):
   data=self.read_json()
   with self.request_db(path) as c:c.execute('UPDATE operations SET status=? WHERE id=?',(data.get('status','done'),path.rsplit('/',1)[-1]));return self.send_json({'ok':True})
  if path.startswith('/api/finance/'): 
   with self.request_db(path) as c:c.execute('UPDATE finance SET status=? WHERE id=?',(data.get('status','paid'),path.rsplit('/',1)[-1]));return self.send_json({'ok':True})
  return self.send_json({'error':'Rota não encontrada'},404)
 def do_DELETE(self):
  path=unquote(urlparse(self.path).path)
  with db() as auth:
   if auth.execute('SELECT COUNT(*) FROM users').fetchone()[0] and not self.current_user(auth):return self.send_json({'error':'Entre no sistema antes de remover registros.'},401)
  if path.startswith('/api/operations/'):
   with self.request_db(path) as c:c.execute('DELETE FROM operations WHERE id=?',(path.rsplit('/',1)[-1],));return self.send_json({'ok':True})
  if path.startswith('/api/finance/'):
   with self.request_db(path) as c:c.execute('DELETE FROM finance WHERE id=?',(path.rsplit('/',1)[-1],));return self.send_json({'ok':True})
  return self.send_json({'error':'Rota não encontrada'},404)
if __name__=='__main__':
 init(); port=int(os.environ.get('PORT','8765')); host=os.environ.get('HOST','127.0.0.1'); print(f'NexoFlow disponível em http://{host}:{port}'); ThreadingHTTPServer((host,port),Handler).serve_forever()
