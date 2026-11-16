"""Atomic employee provisioning shared by the owner hub and venue administration."""
import json
import re
import time


def create_employee(connection, values, owner_id, actor_id):
    from server.app import (ApiError, allrows, audit, execute, one, password_hash,
                            password_ok, public_user, textfield, uid)

    first = textfield(values, 'firstName', 1, 64)
    last = textfield(values, 'lastName', 1, 64)
    username = textfield(values, 'username', 3, 32)
    password = values.get('password')
    pin = values.get('pin')
    if not re.fullmatch(r'[A-Za-z0-9_.-]{3,32}', username):
        raise ApiError('Uživatelské jméno: 3–32 písmen bez diakritiky, číslic nebo znaků . _ -')
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        raise ApiError('Heslo musí mít 8–128 znaků.')
    if not isinstance(pin, str) or not re.fullmatch(r'[0-9]{4}', pin):
        raise ApiError('PIN musí obsahovat přesně čtyři číslice.')

    owner = one(connection, "SELECT id FROM users WHERE id=%s AND role='admin'", (owner_id,))
    if not owner:
        raise ApiError('Majitel provozu neexistuje.', 404)
    # Use the same owner-row lock as work-access configuration so PIN assignment
    # cannot race another employee creation or a PIN change on PostgreSQL.
    execute(connection, 'UPDATE users SET last_seen=last_seen WHERE id=%s', (owner_id,))
    if one(connection, 'SELECT id FROM users WHERE username_key=%s', (username.casefold(),)):
        raise ApiError('Toto uživatelské jméno je již obsazené.', 409)
    peers = allrows(connection, 'SELECT pin_hash FROM work_access WHERE owner_id=%s AND pin_hash IS NOT NULL', (owner_id,))
    if any(password_ok(pin, peer['pin_hash']) for peer in peers):
        raise ApiError('Tento PIN už v pracovním prostoru používá jiný zaměstnanec.', 409)

    user_id = uid()
    inserted = execute(connection, """INSERT INTO users
        (id,username,username_key,first_name,last_name,password_hash,role,created_at,stock_owner_id,permissions_json)
        VALUES (%s,%s,%s,%s,%s,%s,'user',%s,%s,%s)
        ON CONFLICT (username_key) DO NOTHING""",
        (user_id, username, username.casefold(), first, last, password_hash(password), time.time(), owner_id, json.dumps({})))
    if inserted.rowcount != 1:
        raise ApiError('Toto uživatelské jméno je již obsazené.', 409)
    execute(connection, 'INSERT INTO work_access (user_id,owner_id,pin_hash,stores_json) VALUES (%s,%s,%s,%s)',
            (user_id, owner_id, password_hash(pin), 'null'))
    audit(connection, actor_id, 'employee_created', 'Vytvoření zaměstnaneckého profilu: ' + username)
    return public_user(one(connection, 'SELECT * FROM users WHERE id=%s', (user_id,)))
