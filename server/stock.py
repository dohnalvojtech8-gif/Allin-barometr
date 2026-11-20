"""Account-owned warehouse records, isolated from existing bottle/profile state."""
import math
import re
from datetime import datetime

class StockValidationError(ValueError):
    pass

def validate_stock(data):
    if not isinstance(data, dict):
        raise StockValidationError('Neplatná skladová data.')
    limits={'stores':100,'products':1000,'counts':20000,'moves':30000}
    for key,limit in limits.items():
        if not isinstance(data.get(key),list) or len(data[key])>limit:
            raise StockValidationError('Příliš mnoho nebo neplatné položky: '+key)
    def text(value,limit=150,empty=False):
        return isinstance(value,str) and (empty or bool(value.strip())) and len(value)<=limit and not any(ord(c)<32 for c in value)
    def number(value,positive=False):
        return type(value) in (int,float) and math.isfinite(value) and (value>0 if positive else value>=0) and value<=1e12
    def date(value):
        try:
            if not isinstance(value,str) or len(value)>40:return False
            d=datetime.fromisoformat(value.replace('Z','+00:00'))
            return d.tzinfo is not None and d.timestamp()<=datetime.now().astimezone().timestamp()+60
        except (ValueError,OverflowError):return False
    stores=set();products=set();count_ids=set();move_ids=set()
    for s in data['stores']:
        if not isinstance(s,dict) or not text(s.get('id'),100) or s['id'] in stores or not text(s.get('name'),100):raise StockValidationError('Neplatný sklad.')
        if 'color' in s and (not isinstance(s['color'],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',s['color'])):raise StockValidationError('Neplatná barva skladu.')
        if s.get('colorStyle','fill') not in ('fill','border'):raise StockValidationError('Neplatné zobrazení barvy skladu.')
        if 'categories' in s:
            categories=s['categories']
            if not isinstance(categories,list) or len(categories)>50:raise StockValidationError('Neplatné kategorie skladu.')
            names=set()
            for category in categories:
                if not isinstance(category,dict) or not text(category.get('name'),80) or category.get('kind') not in ('piece','keg','liquid','wine','weight') or category['name'].casefold() in names:raise StockValidationError('Kategorie musí mít jedinečný název a platný typ.')
                names.add(category['name'].casefold())
        stores.add(s['id'])
        if s.get('archivedAt') is not None and not date(s['archivedAt']):raise StockValidationError('Neplatné datum odstranění skladu.')
    for p in data['products']:
        if not isinstance(p,dict) or not text(p.get('id'),100) or p['id'] in products or not text(p.get('name')) or not text(p.get('category'),80):raise StockValidationError('Neplatný produkt.')
        products.add(p['id'])
        if p.get('store') is not None and p['store'] not in stores:raise StockValidationError('Produkt musí patřit do existujícího skladu.')
        for optional in ('unitWeightKg','packSize','fullWeightKg'):
            if optional in p and not number(p[optional]):raise StockValidationError('Neplatná hmotnost kusu nebo velikost balení.')
        if p.get('fullWeightKg',0)>0 and p['fullWeightKg']<=p.get('tare',0):raise StockValidationError('Plný obal musí vážit více než prázdný.')
        if not text(p.get('referenceId',''),100,True):raise StockValidationError('Neplatný odkaz na zdroj produktu.')
        if not text(p.get('tapName',''),150,True):raise StockValidationError('Neplatný název volby sládků.')
        if p.get('kind') not in ('piece','keg','wine','liquid','weight') or p.get('unit') not in ('ks','l','ml','kg','balení'):raise StockValidationError('Neplatná jednotka nebo typ produktu.')
        if p.get('min') is None:p['min']=0;p['minEnabled']=False
        if 'minEnabled' in p and type(p['minEnabled']) is not bool:raise StockValidationError('Neplatné nastavení minimální zásoby.')
        if not all(number(p.get(k)) for k in ('cost','min','tare','capacity')) or not number(p.get('density'),True):raise StockValidationError('Neplatné množství nebo cena produktu.')
        for key in ('catalogProductId','kegProfileId'):
            if p.get(key) is not None and not text(p[key],100,True):raise StockValidationError('Neplatné propojení produktu.')
        if p.get('catalogProductId') and (type(p.get('catalogCapacityMl')) is not int or not 0<p['catalogCapacityMl']<=100000):raise StockValidationError('Neplatná velikost lahve.')
        if p.get('kegWeightState','') not in ('','full','empty'):raise StockValidationError('Neplatný stav sudu.')
        if not text(p.get('supplier',''),150,True) or not text(p.get('barcode',''),100,True):raise StockValidationError('Neplatný dodavatel nebo čárový kód.')
    for kind,seen in [('counts',count_ids),('moves',move_ids)]:
        for row in data[kind]:
            if not isinstance(row,dict) or not text(row.get('id'),100) or row['id'] in seen or row.get('store') not in stores or row.get('product') not in products or not date(row.get('at')):raise StockValidationError('Neplatný skladový záznam.')
            if kind=='counts' and any(p['id']==row['product'] and not whole_bottles(p,row.get('qty')) for p in data['products']):raise StockValidationError('Počet skladových lahví musí být celé číslo.')
            seen.add(row['id'])
            if row.get('inventoryId') is not None and not text(row['inventoryId'],100):raise StockValidationError('Neplatné ID inventury.')
            if row.get('kind','warehouse') not in ('warehouse','bar'):raise StockValidationError('Neplatný typ inventury.')
            for key in ('note',):
                if key in row and not text(row[key],500,True):raise StockValidationError('Neplatný důvod odpisu.')
            for key in ('reference','supplier'):
                if key in row and not text(row[key],150,True):raise StockValidationError('Neplatný údaj dodávky.')
            q=row.get('qty')
            if kind=='counts' and not number(q):raise StockValidationError('Neplatný inventurní stav.')
            if kind=='moves' and (type(q) not in (int,float) or not math.isfinite(q) or abs(q)>1e12 or q==0 or row.get('reason') not in ('Příjem','Výdej','Odpis','Přesun','Vratka')):raise StockValidationError('Neplatný skladový pohyb.')
    draft=data.get('draft')
    if draft is not None:
        if not isinstance(draft,dict) or draft.get('store') not in stores or not date(draft.get('at')) or not isinstance(draft.get('products'),list) or len(draft['products'])!=len(set(draft['products'])) or not set(draft['products']).issubset(products) or not isinstance(draft.get('values'),dict):raise StockValidationError('Neplatná rozpracovaná inventura.')
        for k,v in draft['values'].items():
            if k not in draft['products']:raise StockValidationError('Neplatná položka inventury.')
            if v=='':continue
            try: valid=number(float(v))
            except (ValueError,TypeError):valid=False
            if not valid:raise StockValidationError('Neplatný počet v inventuře.')
    bar=data.get('barInventories',[])
    bar_draft=data.get('barDraft')
    if bar_draft is not None:
        if not isinstance(bar_draft,dict) or not text(bar_draft.get('id'),100) or not date(bar_draft.get('at')) or not isinstance(bar_draft.get('items'),list):raise StockValidationError('Neplatná rozpracovaná inventura baru.')
    if not isinstance(bar,list) or len(bar)>2000:raise StockValidationError('Příliš mnoho inventur baru.')
    bar_ids=set()
    for run in bar+([bar_draft] if bar_draft else []):
        if not isinstance(run,dict) or not text(run.get('id'),100) or run['id'] in bar_ids or not date(run.get('at')) or not isinstance(run.get('items'),list) or len(run['items'])>1000:raise StockValidationError('Neplatná inventura baru.')
        bar_ids.add(run['id'])
        for item in run['items']:
            if not isinstance(item,dict) or not text(item.get('name')) or not number(item.get('qty')) or item.get('unit') not in ('l','ml','ks','kg','balení') or not number(item.get('cost',0)) or (item.get('expected') is not None and not number(item['expected'])):raise StockValidationError('Neplatná položka inventury baru.')
    return {k:data[k] for k in limits}|{'draft':draft,'barInventories':bar,'barDraft':bar_draft}

# Historical values are derived on the server and frozen when an inventory closes.
def current_quantity(data,pid,sid,at=None):
    end=datetime.fromisoformat(at.replace('Z','+00:00')).timestamp() if at else float('inf')
    eligible=[r for r in data.get('counts',[]) if r['product']==pid and r['store']==sid and datetime.fromisoformat(r['at'].replace('Z','+00:00')).timestamp()<=end]
    last=max(eligible,key=lambda r:datetime.fromisoformat(r['at'].replace('Z','+00:00')).timestamp(),default=None)
    start=datetime.fromisoformat(last['at'].replace('Z','+00:00')).timestamp() if last else -float('inf')
    moves=[r for r in data.get('moves',[]) if r['product']==pid and r['store']==sid and start<datetime.fromisoformat(r['at'].replace('Z','+00:00')).timestamp()<=end]
    if last is None and not moves:return None
    return (last['qty'] if last else 0)+sum(r['qty'] for r in moves)

def prepare_counts(before,after):
    previous={r['id']:r for r in before.get('counts',[])}
    products={p['id']:p for p in after['products']}
    for r in after['counts']:
        if r['id'] in previous:
            # Expected quantities and historical prices are not editable by clients.
            for k in ('expected','cost','productName','unit'):
                if k in previous[r['id']]:r[k]=previous[r['id']][k]
                else:r.pop(k,None)
        else:
            p=products[r['product']]
            r.update(expected=current_quantity(before,r['product'],r['store'],r['at']),cost=p['cost'],productName=p['name'],unit=p['unit'])
    return after

def required_permissions(before,after):
    result=set()
    if before.get('stores',[])!=after['stores'] or before.get('products',[])!=after['products']:result.add('stock.edit')
    old_counts={r['id']:r for r in before.get('counts',[])};new_counts={r['id']:r for r in after['counts']}
    if set(new_counts)-set(old_counts) or before.get('draft')!=after.get('draft') or before.get('barInventories',[])!=after.get('barInventories',[]) or before.get('barDraft')!=after.get('barDraft'):result.add('inventory.run')
    if set(old_counts)-set(new_counts) or any(new_counts[k]!=v for k,v in old_counts.items() if k in new_counts):result.add('inventory.adjust')
    old_moves={r['id']:r for r in before.get('moves',[])}
    for r in after['moves']:
        if old_moves.get(r['id'])!=r:result.add('stock.writeoff' if r['reason']=='Odpis' else 'stock.receive' if r['id'] not in old_moves and r['reason'] in ('Příjem','Vratka') and r['qty']>0 else 'stock.move')
    if set(old_moves)-{r['id'] for r in after['moves']}:result.add('stock.move')
    old_bars={r['id']:r for r in before.get('barInventories',[])};new_bars={r['id']:r for r in after.get('barInventories',[])}
    new_moves={r['id']:r for r in after['moves']}
    if any(new_moves.get(k)!=v for k,v in old_moves.items()) or any(new_bars.get(k)!=v for k,v in old_bars.items()):result.add('inventory.adjust')
    if before.get('draft')!=after.get('draft') or any(r['id'] not in old_counts and r.get('kind','warehouse')=='warehouse' for r in after['counts']):result.add('inventory.warehouse')
    if before.get('barDraft')!=after.get('barDraft') or before.get('barInventories',[])!=after.get('barInventories',[]) or any(r['id'] not in old_counts and r.get('kind')=='bar' for r in after['counts']):result.add('inventory.bar')
    return result

def change_rows(before,after):
    changes=[]
    stores={s['id']:s['name'] for s in before.get('stores',[])+after['stores']}
    products={p['id']:p for p in before.get('products',[])+after['products']}
    for collection,kind in [('stores','sklad'),('products','produkt'),('counts','inventura'),('moves','pohyb'),('barInventories','inventura baru')]:
        old={r['id']:r for r in before.get(collection,[])};new={r['id']:r for r in after.get(collection,[])}
        for key in sorted(set(old)|set(new)):
            a=old.get(key);b=new.get(key)
            if a==b:continue
            row=b or a;sid=row.get('store','') if collection!='stores' else key
            label=row.get('name') or row.get('productName') or products.get(row.get('product'),{}).get('name') or row.get('label') or stores.get(sid) or kind
            for field in sorted(set(a or {})|set(b or {})):
                if field in ('id','inventoryId','deliveryId','transferId','photoId','actorId','actorName','actorUsername','recordedAt'):continue
                if field in ('at','product','store','expected','productName','unit','cost') and collection in ('counts','moves'):continue
                av=(a or {}).get(field);bv=(b or {}).get(field)
                if av!=bv:
                    if collection=='counts' and field=='qty' and not a:av=current_quantity(before,row['product'],sid,row['at'])
                    if collection=='moves' and field=='qty' and not a:
                        av=current_quantity(before,row['product'],sid,row['at']) or 0;bv=av+row['qty']
                    changes.append({'store':sid,'entity':key,'kind':kind,'label':label,'field':field,'before':av,'after':bv})
    if before.get('barDraft')!=after.get('barDraft'):
        changes.append({'store':'','entity':'bar-draft','kind':'rozpracovaná inventura baru','label':'Sudy a víno','field':'items','before':(before.get('barDraft') or {}).get('items'),'after':(after.get('barDraft') or {}).get('items')})
    if before.get('draft')!=after.get('draft'):
        a=before.get('draft') or {};b=after.get('draft') or {};sid=b.get('store',a.get('store',''))
        if a and not b:
            closed=any(r['id'] not in {x['id'] for x in before.get('counts',[])} and r['store']==sid for r in after['counts'])
            changes.append({'store':sid,'entity':'draft','kind':'inventura','label':stores.get(sid,'Sklad'),'field':'status','before':'Rozpracovaná','after':'Uzavřená' if closed else 'Zrušená'})
        for key in (set(a.get('values',{}))|set(b.get('values',{}))) if b else set():
            av=a.get('values',{}).get(key);bv=b.get('values',{}).get(key)
            if av!=bv:changes.append({'store':sid,'entity':key,'kind':'rozpracovaná inventura','label':products.get(key,{}).get('name','Položka'),'field':'qty','before':av,'after':bv})
    return changes

def validate_active_changes(before,after):
    """Removing a warehouse hides it; its historical records remain valid."""
    archived={s['id'] for s in after['stores'] if s.get('archivedAt')}
    if after.get('draft') and after['draft']['store'] in archived:
        raise StockValidationError('Nejprve dokončete nebo zrušte rozpracovanou inventuru skladu.')
    if any(i.get('store') in archived for i in (after.get('barDraft') or {}).get('items',[])):
        raise StockValidationError('Nejprve uložte rozpracovanou inventuru baru s položkami tohoto skladu.')
    old_moves={r['id'] for r in before.get('moves',[])}
    for row in after.get('moves',[]):
        if row['id'] not in old_moves and row['reason']=='Odpis':
            if row['qty']>=0 or not isinstance(row.get('note'),str) or not 5<=len(row['note'].strip())<=500:
                raise StockValidationError('U odpisu zadejte záporný pohyb a důvod (5–500 znaků).')
    for collection in ('products','counts','moves'):
        old={r['id']:r for r in before.get(collection,[])}
        for row in after[collection]:
            if row.get('store') in archived and old.get(row['id'])!=row:
                raise StockValidationError('Odstraněný sklad nejdříve obnovte; nelze do něj zapisovat nové změny.')


def attribute_records(before,after,actor):
    """Freeze historical authors and derive new authors from the authenticated session."""
    from datetime import timezone
    now=datetime.now(timezone.utc);name=(actor.get('first_name','')+' '+actor.get('last_name','')).strip() or actor['username']
    fields={'actorId':actor['id'],'actorName':name,'actorUsername':actor['username'],'recordedAt':now.timestamp()}
    for key in ('counts','moves','barInventories'):
        old={r['id']:r for r in before.get(key,[])}
        for row in after.get(key,[]):
            if row['id'] in old:
                for field in fields:
                    if field in old[row['id']]:row[field]=old[row['id']][field]
                    else:row.pop(field,None)
            else:
                row.pop('opening',None)
                row.update(fields)
                if actor['role']!='admin':row['at']=now.isoformat()
    return after


def minimum_enabled(product):
    return product.get('minEnabled',product.get('min',0)>0) is True


def at_minimum(product,quantity):
    return quantity is not None and minimum_enabled(product) and quantity<=product.get('min',0)


def low_stock(document):
    from server.work import local_products
    rows=[]
    for store in document.get('stores',[]):
        if store.get('archivedAt'):continue
        for product in local_products(document,store['id']):
            quantity=current_quantity(document,product['id'],store['id'])
            if at_minimum(product,quantity):rows.append({'productId':product['id'],'productName':product['name'],'storeId':store['id'],'storeName':store['name'],'quantity':quantity,'minimum':product.get('min',0),'unit':product['unit']})
    return rows


def whole_bottles(product,quantity):
    if not product.get('catalogProductId') or product['unit'] not in ('ks','balení'):return True
    if type(quantity) not in (int,float) or not math.isfinite(quantity):return False
    pack=product.get('packSize',1) if product['unit']=='balení' else 1
    number=quantity*pack
    return pack>0 and float(pack).is_integer() and abs(number-round(number))<1e-8
