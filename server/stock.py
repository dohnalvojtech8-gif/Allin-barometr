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
        if p.get('kind') not in ('piece','keg','wine') or p.get('unit') not in ('ks','l','kg','balení'):raise StockValidationError('Neplatná jednotka nebo typ produktu.')
        if not all(number(p.get(k)) for k in ('cost','min','tare','capacity')) or not number(p.get('density'),True):raise StockValidationError('Neplatné množství nebo cena produktu.')
        if p['kind'] in ('keg','wine') and (p['unit']!='l' or p['capacity']<=0):raise StockValidationError('Sudy a víno vyžadují jednotku l a kladný objem.')
        if not text(p.get('supplier',''),150,True) or not text(p.get('barcode',''),100,True):raise StockValidationError('Neplatný dodavatel nebo čárový kód.')
    for kind,seen in [('counts',count_ids),('moves',move_ids)]:
        for row in data[kind]:
            if not isinstance(row,dict) or not text(row.get('id'),100) or row['id'] in seen or row.get('store') not in stores or row.get('product') not in products or not date(row.get('at')):raise StockValidationError('Neplatný skladový záznam.')
            seen.add(row['id'])
            q=row.get('qty')
            if kind=='counts' and not number(q):raise StockValidationError('Neplatný inventurní stav.')
            if kind=='moves' and (type(q) not in (int,float) or not math.isfinite(q) or abs(q)>1e12 or q==0 or row.get('reason') not in ('Příjem','Výdej','Odpis','Přesun','Vratka')):raise StockValidationError('Neplatný skladový pohyb.')
    draft=data.get('draft')
    if draft is not None:
        if not isinstance(draft,dict) or draft.get('store') not in stores or not date(draft.get('at')) or not isinstance(draft.get('products'),list) or not draft['products'] or len(draft['products'])!=len(set(draft['products'])) or not set(draft['products']).issubset(products) or not isinstance(draft.get('values'),dict):raise StockValidationError('Neplatná rozpracovaná inventura.')
        for k,v in draft['values'].items():
            if k not in draft['products']:raise StockValidationError('Neplatná položka inventury.')
            if v=='':continue
            try: valid=number(float(v))
            except (ValueError,TypeError):valid=False
            if not valid:raise StockValidationError('Neplatný počet v inventuře.')
    return {k:data[k] for k in limits}|{'draft':draft}
