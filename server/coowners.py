"""Shared owner workspace; central membership remains authoritative in every venue."""
from contextlib import closing
import re
import secrets
import time
from flask import g, jsonify


def owner_scope(user=None):
    user=user or g.user
    return user.get('stock_owner_id') or user['id']


def valid_owner(user, venue=None):
    from server.app import connect, one
    with closing(connect(central=True)) as c:
        account=one(c,"SELECT * FROM users WHERE id=%s AND role='admin' AND status='active'",(user['id'],))
        if not account:return False
        root=one(c,"SELECT * FROM users WHERE id=%s AND role='admin' AND status='active' AND stock_owner_id IS NULL",(owner_scope(account),))
    return bool(root and (not venue or root['id']==venue['owner_id']))


def provision_owner(venue, force=False):
    """Copy identities, never central passwords. Keep actor and stock principal separate."""
    from server.app import db, connect, one, allrows, execute, password_hash, ApiError
    actor=getattr(g,'user',None)
    if not actor or actor['role']!='admin' or owner_scope(actor)!=venue['owner_id']:return
    if not force and actor['id']==venue['owner_id']:return
    done=getattr(g,'_provisioned_owners',set())
    if venue['id'] in done:return
    with db() as c:
        existing_ids={r['id'] for r in allrows(c,'SELECT id FROM users WHERE id=%s OR id=%s',(venue['owner_id'],actor['id']))}
    if {venue['owner_id'],actor['id']}.issubset(existing_ids):
        g._provisioned_owners=done|{venue['id']}
        return
    with closing(connect(central=True)) as c:
        users=[one(c,'SELECT * FROM users WHERE id=%s',(id,)) for id in dict.fromkeys((venue['owner_id'],actor['id']))]
    with db() as c:
        for user in users:
            if not user:raise ApiError('Majitel neexistuje.',403)
            existing=one(c,'SELECT * FROM users WHERE id=%s',(user['id'],))
            if existing:continue
            # Employee names may already occupy the same name inside a venue.
            username=user['username']
            if one(c,'SELECT id FROM users WHERE username_key=%s',(username.casefold(),)):username='owner_'+user['id']
            execute(c,"""INSERT INTO users (id,username,username_key,first_name,last_name,password_hash,role,status,created_at,stock_owner_id,phone,email)
                VALUES (%s,%s,%s,%s,%s,%s,'admin','active',%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING""",
                (user['id'],username,username.casefold(),user['first_name'],user['last_name'],password_hash(secrets.token_urlsafe(48)),user['created_at'],user.get('stock_owner_id'),user.get('phone',''),user.get('email','')))


def register(app):
    from server.app import authenticated, db, execute, one, allrows, body, textfield, password_hash, public_user, uid, ApiError, audit, rate_limit
    from server.employees import contact_values

    @app.get('/api/owner/coowners')
    @authenticated(admin=True)
    def coowners():
        primary=owner_scope()
        with db(central=True) as c:
            users=allrows(c,"SELECT * FROM users WHERE role='admin' AND (id=%s OR stock_owner_id=%s) ORDER BY created_at,id",(primary,primary))
        return jsonify(owners=[{**public_user(u),'isPrimary':u['id']==primary} for u in users],canManage=g.user['id']==primary)

    @app.post('/api/owner/coowners')
    @authenticated(admin=True)
    def create_coowner():
        values=body();first=textfield(values,'firstName');last=textfield(values,'lastName');username=textfield(values,'username',3,32);password=values.get('password')
        if not re.fullmatch(r'[A-Za-z0-9_.-]{3,32}',username):raise ApiError('Uživatelské jméno: 3–32 písmen bez diakritiky, číslic nebo znaků . _ -')
        if not isinstance(password,str) or not 8<=len(password)<=128:raise ApiError('Heslo musí mít 8–128 znaků.')
        phone,email=contact_values(values)
        rate_limit(['coowner-create:'+g.user['id']],15)
        with db(central=True) as c:
            execute(c,'UPDATE users SET last_seen=last_seen WHERE id=%s',(owner_scope(),))
            if one(c,'SELECT user_id FROM staff_login_directory WHERE username_key=%s',(username.casefold(),)):raise ApiError('Toto uživatelské jméno je již obsazené.',409)
            id=uid()
            inserted=execute(c,"""INSERT INTO users (id,username,username_key,first_name,last_name,password_hash,role,created_at,stock_owner_id,phone,email)
                VALUES (%s,%s,%s,%s,%s,%s,'admin',%s,%s,%s,%s) ON CONFLICT (username_key) DO NOTHING""",
                (id,username,username.casefold(),first,last,password_hash(password),time.time(),owner_scope(),phone,email))
            if inserted.rowcount!=1:raise ApiError('Toto uživatelské jméno je již obsazené.',409)
            audit(c,g.user['id'],'coowner_created','Vytvoření spolumajitele: '+username)
            user=one(c,'SELECT * FROM users WHERE id=%s',(id,))
        return jsonify(user=public_user(user)),201

    @app.put('/api/owner/coowners/<id>/status')
    @authenticated(admin=True)
    def coowner_status(id):
        primary=owner_scope()
        if g.user['id']!=primary or id==primary:raise ApiError('Přístup spolumajitelů spravuje hlavní majitel.',403)
        status=body().get('status')
        if status not in ('active','suspended'):raise ApiError('Neplatný stav.')
        with db(central=True) as c:
            target=one(c,"SELECT * FROM users WHERE id=%s AND stock_owner_id=%s AND role='admin'",(id,primary))
            if not target:raise ApiError('Spolumajitel neexistuje.',404)
            execute(c,'UPDATE users SET status=%s WHERE id=%s',(status,id))
            execute(c,'DELETE FROM sessions WHERE user_id=%s',(id,))
            audit(c,g.user['id'],'coowner_status_changed','Změna přístupu spolumajitele: '+target['username']+' · '+status)
        from server.allin import venue_context
        with db(central=True) as c:venues=allrows(c,'SELECT * FROM allin_venues WHERE owner_id=%s',(primary,))
        for venue in venues:
            with venue_context(venue),db() as c:
                execute(c,'DELETE FROM sessions WHERE user_id=%s',(id,))
                execute(c,'DELETE FROM work_sessions WHERE user_id=%s',(id,))
        # Membership is also checked centrally on every request.
        return jsonify(ok=True)
