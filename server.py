from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote
import json, sqlite3, uuid, os, threading

ROOT=Path(__file__).parent.resolve(); DB=ROOT/'nexoflow.sqlite3'; lock=threading.Lock()
def db():
 c=sqlite3.connect(DB,timeout=10); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
def init():
 with db() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS products(id TEXT PRIMARY KEY,sku TEXT UNIQUE NOT NULL,name TEXT NOT NULL,category TEXT DEFAULT '',price REAL NOT NULL DEFAULT 0,cost REAL NOT NULL DEFAULT 0,stock REAL NOT NULL DEFAULT 0,min_stock REAL NOT NULL DEFAULT 0,created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS customers(id TEXT PRIMARY KEY,name TEXT NOT NULL,email TEXT DEFAULT '',phone TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS sales(id TEXT PRIMARY KEY,number INTEGER UNIQUE NOT NULL,customer TEXT DEFAULT '',channel TEXT DEFAULT 'PDV',total REAL NOT NULL,status TEXT DEFAULT 'paid',created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS sale_items(id TEXT PRIMARY KEY,sale_id TEXT NOT NULL REFERENCES sales(id),product_id TEXT REFERENCES products(id),description TEXT NOT NULL,quantity REAL NOT NULL,unit_price REAL NOT NULL); CREATE TABLE IF NOT EXISTS movements(id TEXT PRIMARY KEY,product_id TEXT NOT NULL REFERENCES products(id),kind TEXT NOT NULL,quantity REAL NOT NULL,note TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS finance(id TEXT PRIMARY KEY,description TEXT NOT NULL,kind TEXT NOT NULL,due_date TEXT DEFAULT '',category TEXT DEFAULT '',amount REAL NOT NULL,status TEXT DEFAULT 'open',created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS xml_imports(id TEXT PRIMARY KEY,filename TEXT NOT NULL,supplier TEXT DEFAULT '',invoice_number TEXT DEFAULT '',total REAL DEFAULT 0,payload TEXT NOT NULL,status TEXT DEFAULT 'review',created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);''')
  if c.execute('SELECT COUNT(*) FROM products').fetchone()[0]==0:
   for p in [('FON-2041','Fone Bluetooth Wave Pro','Eletrônicos',249.9,130,34,8),('GAR-1180','Garrafa Térmica Inox 750ml','Acessórios',89.9,42,4,8),('MOC-0902','Mochila Urbana Compact','Bolsas',179,88,21,5)]: c.execute('INSERT INTO products(id,sku,name,category,price,cost,stock,min_stock) VALUES(?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),*p))
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw): super().__init__(*a,directory=str(ROOT),**kw)
 def log_message(self,*a): pass
 def send_json(self,obj,status=200):
  body=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers(); self.wfile.write(body)
 def read_json(self): return json.loads(self.rfile.read(int(self.headers.get('Content-Length',0)) or 0) or b'{}')
 def do_OPTIONS(self): self.send_response(204); self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Access-Control-Allow-Methods','GET,POST,PUT,DELETE,OPTIONS'); self.send_header('Access-Control-Allow-Headers','Content-Type'); self.end_headers()
 def do_GET(self):
  path=unquote(urlparse(self.path).path)
  if path=='/api/health': return self.send_json({'ok':True,'database':'SQLite','app':'NexoFlow'})
  if path.startswith('/api/'):
   with db() as c:
    routes={'/api/products':'SELECT * FROM products ORDER BY name','/api/sales':'SELECT * FROM sales ORDER BY id DESC LIMIT 100','/api/finance':'SELECT * FROM finance ORDER BY due_date','/api/movements':'SELECT m.*,p.name product FROM movements m JOIN products p ON p.id=m.product_id ORDER BY m.created_at DESC LIMIT 100','/api/xml':'SELECT id,filename,supplier,invoice_number,total,status,created_at FROM xml_imports ORDER BY created_at DESC'}
    if path=='/api/dashboard':
     return self.send_json({'products':c.execute('SELECT COUNT(*) FROM products').fetchone()[0],'lowStock':c.execute('SELECT COUNT(*) FROM products WHERE stock<=min_stock').fetchone()[0],'sales':c.execute("SELECT COALESCE(SUM(total),0) FROM sales WHERE date(created_at)=date('now','localtime')").fetchone()[0],'orders':c.execute("SELECT COUNT(*) FROM sales WHERE date(created_at)=date('now','localtime')").fetchone()[0],'financeOpen':c.execute("SELECT COALESCE(SUM(amount),0) FROM finance WHERE status='open'").fetchone()[0]})
    if path in routes:return self.send_json([dict(x) for x in c.execute(routes[path]).fetchall()])
    if path.startswith('/api/settings/'): 
     row=c.execute('SELECT value FROM settings WHERE key=?',(path.rsplit('/',1)[-1],)).fetchone(); return self.send_json(json.loads(row['value']) if row else {})
   return self.send_json({'error':'Rota não encontrada'},404)
  if path=='/': self.path='/index.html'
  return super().do_GET()
 def do_POST(self):
  path=unquote(urlparse(self.path).path); data=self.read_json()
  try:
   with lock,db() as c:
    if path=='/api/products':
     sku=(data.get('sku') or '').strip(); name=(data.get('name') or '').strip()
     if not sku or not name: return self.send_json({'error':'Informe SKU e nome do produto.'},400)
     pid=str(uuid.uuid4()); c.execute('INSERT INTO products(id,sku,name,category,price,cost,stock,min_stock) VALUES(?,?,?,?,?,?,?,?)',(pid,sku,name,data.get('category',''),float(data.get('price') or 0),float(data.get('cost') or 0),float(data.get('stock') or 0),float(data.get('min_stock') or 0))); return self.send_json({'id':pid},201)
    if path=='/api/sales':
     items=data.get('items') or []
     if not items:return self.send_json({'error':'Adicione pelo menos um produto.'},400)
     total=0; normalized=[]
     for item in items:
      product=c.execute('SELECT * FROM products WHERE id=? OR sku=?',(item.get('product_id'),item.get('sku'))).fetchone(); qty=float(item.get('quantity') or 1)
      if product:
       if product['stock']<qty:return self.send_json({'error':f"Estoque insuficiente para {product['name']} (disponível: {product['stock']:g})."},409)
       price=float(item.get('unit_price') if item.get('unit_price') is not None else product['price']); normalized.append((product,qty,price)); total+=qty*price
      else:return self.send_json({'error':'Produto não encontrado no catálogo.'},404)
     number=c.execute('SELECT COALESCE(MAX(number),2840)+1 FROM sales').fetchone()[0]; sid=str(uuid.uuid4()); c.execute('INSERT INTO sales(id,number,customer,channel,total,status) VALUES(?,?,?,?,?,?)',(sid,number,data.get('customer','Consumidor final'),data.get('channel','PDV'),total,'paid'))
     for p,q,price in normalized:
      c.execute('INSERT INTO sale_items(id,sale_id,product_id,description,quantity,unit_price) VALUES(?,?,?,?,?,?)',(str(uuid.uuid4()),sid,p['id'],p['name'],q,price)); c.execute('UPDATE products SET stock=stock-? WHERE id=?',(q,p['id']));c.execute('INSERT INTO movements(id,product_id,kind,quantity,note) VALUES(?,?,?,?,?)',(str(uuid.uuid4()),p['id'],'sale',-q,f'Venda #{number}'))
     return self.send_json({'id':sid,'number':number,'total':total},201)
    if path=='/api/movements':
     p=c.execute('SELECT * FROM products WHERE id=?',(data.get('product_id'),)).fetchone(); qty=float(data.get('quantity') or 0); kind=data.get('kind','in')
     if not p or qty<=0:return self.send_json({'error':'Produto e quantidade válida são obrigatórios.'},400)
     delta=qty if kind=='in' else -qty
     if p['stock']+delta<0:return self.send_json({'error':'A movimentação deixaria o estoque negativo.'},409)
     c.execute('UPDATE products SET stock=stock+? WHERE id=?',(delta,p['id']));c.execute('INSERT INTO movements(id,product_id,kind,quantity,note) VALUES(?,?,?,?,?)',(str(uuid.uuid4()),p['id'],kind,delta,data.get('note','Ajuste manual')));return self.send_json({'ok':True},201)
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
      c.execute('UPDATE products SET stock=stock+? WHERE id=?',(qty,p['id']));c.execute('INSERT INTO movements(id,product_id,kind,quantity,note) VALUES(?,?,?,?,?)',(str(uuid.uuid4()),p['id'],'in',qty,f"Entrada da nota {note['invoice_number']}"))
     if total>0:c.execute('INSERT INTO finance(id,description,kind,due_date,category,amount,status) VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),f"Compra {note['invoice_number']} · {note['supplier']}",'pay',due,'Fornecedores',total,'open'))
     c.execute("UPDATE xml_imports SET status='processed' WHERE id=?",(iid,));return self.send_json({'ok':True})
  except sqlite3.IntegrityError as ex:return self.send_json({'error':'SKU já cadastrado ou dados relacionados inválidos.'},409)
  except (ValueError,TypeError) as ex:return self.send_json({'error':'Confira os valores informados.'},400)
 def do_PUT(self):
  path=unquote(urlparse(self.path).path); data=self.read_json()
  if path.startswith('/api/finance/'): 
   with db() as c:c.execute('UPDATE finance SET status=? WHERE id=?',(data.get('status','paid'),path.rsplit('/',1)[-1]));return self.send_json({'ok':True})
  return self.send_json({'error':'Rota não encontrada'},404)
 def do_DELETE(self):
  path=unquote(urlparse(self.path).path)
  if path.startswith('/api/finance/'): 
   with db() as c:c.execute('DELETE FROM finance WHERE id=?',(path.rsplit('/',1)[-1],));return self.send_json({'ok':True})
  return self.send_json({'error':'Rota não encontrada'},404)
if __name__=='__main__':
 init(); port=int(os.environ.get('PORT','8765')); print(f'NexoFlow disponível em http://127.0.0.1:{port}'); ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
