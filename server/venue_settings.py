"""Venue lifecycle and validated presentation settings for the owner hub."""
import json
import re
import time
from pathlib import Path
from flask import g,jsonify
from server.coowners import owner_scope

CARD_DEFAULTS={'style':'classic','font':'system','titleSize':25,'textSize':14,'textColor':'#f7f0e4','mutedColor':'#bdb4a4','background':'#1d2023','accent':'#d8bd87','radius':16,'shadow':False,'bold':False,'italic':False}
CARD_STYLES=('classic','clean','stripe','banner','editorial','compact','gradient','minimal','ledger','columns','outline','square')

def card_style(values):
    from server.app import ApiError
    if not isinstance(values,dict) or set(values)-set(CARD_DEFAULTS):raise ApiError('Neplatné nastavení vzhledu karty.')
    clean={**CARD_DEFAULTS,**values}
    if clean['style'] not in CARD_STYLES or clean['font'] not in ('system','georgia','arial','verdana','tahoma','mono'):raise ApiError('Vyberte platný styl a písmo.')
    for key,lo,hi in [('titleSize',16,34),('textSize',12,18),('radius',0,32)]:
        if type(clean[key]) is not int or not lo<=clean[key]<=hi:raise ApiError('Velikosti vzhledu jsou mimo povolený rozsah.')
    for key in ('textColor','mutedColor','background','accent'):
        if not isinstance(clean[key],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',clean[key]):raise ApiError('Barvu zadejte ve formátu HEX, například #D8BD87.')
        clean[key]=clean[key].lower()
    if any(type(clean[k]) is not bool for k in ('shadow','bold','italic')):raise ApiError('Neplatné nastavení stínu.')
    return clean


def register(app):
    from server.app import authenticated,db,execute,one,body,ApiError,audit,TEST_DB
    from server.allin import venue_context

    def owned(c,id):
        venue=one(c,'SELECT * FROM allin_venues WHERE id=%s AND owner_id=%s',(id,owner_scope()))
        if not venue:raise ApiError('Provoz neexistuje nebo k němu nemáte přístup.',404)
        return venue

    def revoke(venue):
        with venue_context(venue),db() as c:
            for table in ('sessions','work_sessions','work_devices'):execute(c,'DELETE FROM '+table)

    @app.put('/api/owner/venues/<venue_id>/card')
    @authenticated(admin=True)
    def save_card(venue_id):
        settings=card_style(body())
        with db(central=True) as c:
            venue=owned(c,venue_id)
            execute(c,'UPDATE allin_venues SET card_style_json=%s WHERE id=%s',(json.dumps(settings),venue_id))
            audit(c,g.user['id'],'venue_card_changed','Úprava vzhledu karty provozu '+venue['name'])
        return jsonify(cardStyle=settings)

    @app.post('/api/owner/venues/<venue_id>/archive')
    @authenticated(admin=True)
    def archive(venue_id):
        with db(central=True) as c:
            venue=owned(c,venue_id)
            execute(c,'UPDATE allin_venues SET archived_at=%s WHERE id=%s',(venue.get('archived_at') or time.time(),venue_id))
            audit(c,g.user['id'],'venue_archived','Vypnutí a archivace provozu '+venue['name'])
        revoke(venue)
        return jsonify(ok=True)

    @app.post('/api/owner/venues/<venue_id>/restore')
    @authenticated(admin=True)
    def restore(venue_id):
        with db(central=True) as c:venue=owned(c,venue_id)
        revoke(venue)
        with db(central=True) as c:
            owned(c,venue_id)
            execute(c,'UPDATE allin_venues SET archived_at=NULL WHERE id=%s',(venue_id,))
            audit(c,g.user['id'],'venue_restored','Obnovení provozu '+venue['name'])
        return jsonify(ok=True)

    @app.delete('/api/owner/venues/<venue_id>')
    @authenticated(admin=True)
    def delete_venue(venue_id):
        values=body()
        with db(central=True) as c:
            venue=owned(c,venue_id)
            if values.get('confirmation')!=venue['name']:raise ApiError('Pro potvrzení napište přesný název provozu.')
            # PostgreSQL schema removal and all central cascades are one transaction.
            if not TEST_DB:
                execute(c,'SELECT id FROM allin_venues WHERE id=%s FOR UPDATE',(venue_id,))
                if not re.fullmatch(r'[a-f0-9-]{36}',venue['id']):raise ApiError('Neplatný identifikátor provozu.')
                execute(c,'DROP SCHEMA IF EXISTS venue_'+venue['id'].replace('-','')+' CASCADE')
            execute(c,'DELETE FROM notification_subscriptions WHERE scope=%s',(venue_id,))
            execute(c,'DELETE FROM notification_profiles WHERE scope=%s',(venue_id,))
            execute(c,'DELETE FROM allin_venues WHERE id=%s',(venue_id,))
            audit(c,g.user['id'],'venue_deleted','Trvalé vymazání provozu '+venue['name'])
        if TEST_DB:
            path=Path(TEST_DB).with_name('venue_'+venue_id+'.sqlite3')
            for suffix in ('','-wal','-shm'):Path(str(path)+suffix).unlink(missing_ok=True)
        return jsonify(ok=True)
