"""Account-owned warehouse records, isolated from existing bottle/profile state."""
import math
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
        stores.add(s['id'])
    for p in data['products']:
        if not isinstance(p,dict) or not text(p.get('id'),100) or p['id'] in products or not text(p.get('name')) or not text(p.get('category'),80):raise StockValidationError('Neplatný produkt.')
        products.add(p['id'])
        if p.get('store') is not None and p['store'] not in stores:raise StockValidationError('Produkt musí patřit do existujícího skladu.')
        for optional in ('unitWeightKg','packSize'):
            if optional in p and not number(p[optional]):raise StockValidationError('Neplatná hmotnost kusu nebo velikost balení.')
        if p.get('kind') not in ('piece','keg','wine','liquid','weight') or p.get('unit') not in ('ks','l','kg','balení'):raise StockValidationError('Neplatná jednotka nebo typ produktu.')
        if not all(number(p.get(k)) for k in ('cost','min','tare','capacity')) or not number(p.get('density'),True):raise StockValidationError('Neplatné množství nebo cena produktu.')
        if p['kind'] in ('keg','wine','liquid') and (p['unit']!='l' or p['capacity']<=0):raise StockValidationError('Sudy a víno vyžadují jednotku l a kladný objem.')
        if not text(p.get('supplier',''),150,True) or not text(p.get('barcode',''),100,True):raise StockValidationError('Neplatný dodavatel nebo čárový kód.')
    for kind,seen in [('counts',count_ids),('moves',move_ids)]:
        for row in data[kind]:
            if not isinstance(row,dict) or not text(row.get('id'),100) or row['id'] in seen or row.get('store') not in stores or row.get('product') not in products or not date(row.get('at')):raise StockValidationError('Neplatný skladový záznam.')
            seen.add(row['id'])
            if row.get('inventoryId') is not None and not text(row['inventoryId'],100):raise StockValidationError('Neplatné ID inventury.')
            if row.get('kind','warehouse') not in ('warehouse','bar'):raise StockValidationError('Neplatný typ inventury.')
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
    last=max(eligible,key=lambda r:r['at'],default=None)
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
        if old_moves.get(r['id'])!=r:result.add('stock.receive' if r['id'] not in old_moves and r['reason'] in ('Příjem','Vratka') and r['qty']>0 else 'stock.move')
    if set(old_moves)-{r['id'] for r in after['moves']}:result.add('stock.move')
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
                if field in ('id','inventoryId','deliveryId','transferId','photoId'):continue
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
