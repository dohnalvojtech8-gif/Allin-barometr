"""Server-side capabilities. The administrator role always retains owner access."""
import json
PERMISSIONS={
 'stock.view':('Prohlížet sklady',True),
 'stock.edit':('Vytvářet a upravovat sklady a produkty',True),
 'stock.receive':('Přijímat dodávky',True),
 'stock.move':('Vydávat, odepisovat a přesouvat zboží',True),
 'inventory.run':('Provádět a ukládat inventury',True),
 'inventory.bar':('Inventury baru a měření lahví',True),
 'inventory.warehouse':('Inventury skladů a vážení zboží',True),
 'inventory.history':('Prohlížet historii inventur',True),
 'catalog.view':('Prohlížet katalog a knihovnu lahví',True),
 'reference.view':('Prohlížet ověřenou databázi produktů',True),
 'reports.view':('Prohlížet porovnání a přehledy',True),
 'inventory.adjust':('Opravovat uzavřené inventury',False),
 'catalog.unlock':('Odemykat alkoholické nápoje',True),
 'users.manage':('Spravovat běžné zaměstnanecké účty',False),
 'work.inventory':('Spouštět inventury na pracovním terminálu',False),
 'stock.audit':('Číst historii všech skladových změn',False),
}
def effective_permissions(user):
 try:overrides=json.loads(user.get('permissions_json','{}'))
 except (ValueError,TypeError):overrides={}
 result={k:True if user['role']=='admin' else overrides.get(k,default) is True for k,(_,default) in PERMISSIONS.items()}
 if user['role']!='admin':result['inventory.adjust']=False
 return result
def has_permission(user,key):return effective_permissions(user).get(key,False)
