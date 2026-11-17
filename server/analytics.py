"""Deterministic inventory evidence. Missing baselines never become zero loss."""
from collections import defaultdict
from datetime import datetime
from statistics import median
from zoneinfo import ZoneInfo
PRAGUE=ZoneInfo('Europe/Prague')

def timestamp(value):
    return datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()

def business_date(value):
    return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(PRAGUE).date().isoformat()

def canonical(unit,quantity):
    if unit=='ml':return 'l',quantity/1000
    if unit=='g':return 'kg',quantity/1000
    return unit,quantity

def observations(document):
    products={p['id']:p for p in document.get('products',[])}
    stores={s['id']:s['name'] for s in document.get('stores',[])}
    groups=defaultdict(list);moves=defaultdict(list);result=[]
    for row in document.get('counts',[]):groups[(row['store'],row['product'])].append(row)
    for row in document.get('moves',[]):moves[(row['store'],row['product'])].append(row)
    for (store,pid),rows in groups.items():
        rows.sort(key=lambda r:(timestamp(r['at']),r['id']));movements=sorted(moves[(store,pid)],key=lambda r:timestamp(r['at']))
        cursor=0;previous=None
        for row in rows:
            at=timestamp(row['at']);changes=[]
            while cursor<len(movements) and timestamp(movements[cursor]['at'])<=at:
                move=movements[cursor];cursor+=1
                if previous is not None and timestamp(move['at'])>timestamp(previous['at']):changes.append(move)
            product=products.get(pid,{})
            unit=row.get('unit') or product.get('unit','ks')
            expected=row.get('expected')
            difference=row['qty']-expected if expected is not None else None
            inbound=sum(m['qty'] for m in changes if m['reason'] in ('Příjem','Vratka','Přesun'))
            waste=-sum(m['qty'] for m in changes if m['reason']=='Odpis')
            issued=-sum(m['qty'] for m in changes if m['reason']=='Výdej')
            consumed=previous['qty']+inbound-row['qty']-waste if previous is not None else None
            result.append({'id':row['id'],'inventoryId':row.get('inventoryId') or row['id'],'kind':row.get('kind','warehouse'),'at':row['at'],
              'date':business_date(row['at']),'startAt':previous['at'] if previous else None,'storeId':store,'storeName':stores.get(store,store),
              'productId':pid,'productName':row.get('productName') or product.get('name',pid),'unit':unit,'qty':row['qty'],'expected':expected,
              'difference':difference,'shortage':max(0,-difference) if difference is not None else None,
              'surplus':max(0,difference) if difference is not None else None,'consumption':consumed,
              'recordedWaste':waste,'recordedIssues':issued,'inbound':inbound,'actorName':row.get('actorName'),
              'rate':max(0,-difference)/abs(expected) if expected is not None and expected>0 else None})
            previous=row
    # Mapped weighted lines are already in warehouse counts; do not count them twice.
    for run in document.get('barInventories',[]):
        for index,item in enumerate(run.get('items',[])):
            if item.get('product') and item.get('store'):continue
            unit,qty=canonical(item['unit'],item['qty']);expected=item.get('expected')
            if expected is not None:_,expected=canonical(item['unit'],expected)
            difference=qty-expected if expected is not None else None
            result.append({'id':run['id']+':'+str(index),'inventoryId':run['id'],'kind':'bar','at':run['at'],'date':business_date(run['at']),
              'startAt':None,'storeId':'bar','storeName':'Bar','productId':item.get('id') or item.get('productId') or item['name'],
              'productName':item['name'],'unit':unit,'qty':qty,'expected':expected,'difference':difference,
              'shortage':max(0,-difference) if difference is not None else None,'surplus':max(0,difference) if difference is not None else None,
              'consumption':None,'recordedWaste':0,'recordedIssues':0,'inbound':0,'actorName':run.get('actorName'),
              'rate':max(0,-difference)/abs(expected) if expected is not None and expected>0 else None})
    return sorted(result,key=lambda r:(timestamp(r['at']),r['id']))

def analyze(document,from_date='',to_date='',store='',product=''):
    all_rows=observations(document);histories=defaultdict(list);alerts=[];selected=[]
    for row in all_rows:
        key=(row['storeId'],row['productId'],row['unit'],row['kind']);prior=histories[key]
        chosen=(not from_date or row['date']>=from_date) and (not to_date or row['date']<=to_date) and (not store or row['storeId']==store) and (not product or row['productId']==product)
        if chosen:
            selected.append(row)
            comparable=[r for r in prior if r['shortage'] is not None]
            recent=(comparable+[row])[-5:]
            loss=[r for r in recent if r['shortage'] is not None and r['shortage']>1e-8]
            if row['shortage'] is not None and row['shortage']>1e-8 and len(recent)>=3 and len(loss)>=3:
                alerts.append({'type':'recurring_shortage','observationId':row['id'],'productName':row['productName'],'storeName':row['storeName'],'date':row['date'],
                 'explanation':f"Manko se objevilo v {len(loss)} z posledních {len(recent)} srovnatelných inventur.",'evidenceIds':[r['id'] for r in recent],
                 'possibleCauses':['Ověřte neevidované výdeje, receptury a přesnost měření.']})
            rates=[r['rate'] for r in prior if r['rate'] is not None][-12:]
            if row['rate'] is not None and len(rates)>=5:
                center=median(rates);mad=median(abs(v-center) for v in rates);threshold=center+max(.10,3*1.4826*mad)
                if row['rate']>threshold:
                    alerts.append({'type':'unusual_deviation','observationId':row['id'],'productName':row['productName'],'storeName':row['storeName'],'date':row['date'],
                      'explanation':f"Manko {row['rate']*100:.1f} % překračuje obvyklou úroveň {center*100:.1f} %; základ tvoří {len(rates)} předchozích inventur.",
                      'baselineRate':center,'thresholdRate':threshold,'sampleCount':len(rates),'possibleCauses':['Jde o statistickou odchylku; příčinu ověřte v pohybech a měření.']})
        prior.append(row)
    def aggregate(fields):
        totals={}
        for row in selected:
            key=tuple((row['date'][:7] if f=='month' else row[f]) for f in fields)+ (row['unit'],)
            group=totals.setdefault(key,{**{f:v for f,v in zip(fields,key)},'unit':row['unit'],'shortage':0,'surplus':0,'measurements':0,'withoutBaseline':0})
            group['measurements']+=1
            if row['shortage'] is None:group['withoutBaseline']+=1
            else:group['shortage']+=row['shortage'];group['surplus']+=row['surplus']
        return list(totals.values())
    return {'observations':selected,'byMonth':aggregate(['month']),'byStore':aggregate(['storeId','storeName']),
            'byProduct':aggregate(['productId','productName']),'alerts':alerts,'withoutBaseline':sum(r['expected'] is None for r in selected),
            'method':'Manko je rozdíl fyzického a evidovaného stavu. Upozornění navrhují ověření příčin; příčinu samotná inventura nedokazuje.'}

def margins(rows):
    currencies=defaultdict(list)
    for row in rows:currencies[row['currency']].append(row)
    result=[]
    for currency,items in currencies.items():
        revenue=sum(int(r['revenue_net']) for r in items);missing=sum(r['cogs'] is None for r in items)
        cogs=sum(int(r['cogs']) for r in items if r['cogs'] is not None)
        operating_missing=sum(r['operating_costs'] is None for r in items)
        result.append({'currency':currency,'revenueNet':revenue,'cogs':None if missing else cogs,
          'grossMarginPercent':100*(revenue-cogs)/revenue if not missing and revenue>0 else None,
          'profitEstimate':revenue-cogs-sum(int(r['operating_costs']) for r in items) if not missing and not operating_missing else None,
          'missingCosts':missing,'missingOperatingCosts':operating_missing,'days':len({r['business_date'] for r in items})})
    return result
