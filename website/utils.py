from functools import wraps
from flask import session, redirect, url_for, request
import hashlib
import json

def admin_auth(f):
    ''' This decorator checks for admin login and redirects to login page if necessary '''
    @wraps(f)
    def decorated(*args, **kwargs):
        # tarkistetaan onko admin kirjautunut
        if 'adminKirjautunut' not in session:
            return redirect(url_for('auth.admin')) 
        return f(*args, **kwargs)
    return decorated

def auth(f):
    ''' This decorator checks for general login and redirects to login page if necessary '''
    @wraps(f)
    def decorated(*args, **kwargs):
        # Tarkistetaan onko käyttäjä kirjautunut
        if 'kirjautunut' not in session:
            return redirect(url_for('auth.kirjaudu'))  
        return f(*args, **kwargs)
    return decorated


# Salasanan hashaus apufunktio
def hashPassword(joukkueid, salasana):
    m = hashlib.sha512()
    m.update(str(joukkueid).encode("UTF-8"))
    m.update(salasana.encode("UTF-8"))
    return m.hexdigest()

# Funktio jolla päivitetään joukkuetiedot
def handleJoukkueUpdate(request, con, cur, joukkueid):
    joukkueenNimi = request.form.get("nimi", "").strip()
    salasana = request.form.get("salasana", "").strip()
    sarja = request.form.get("sarja")
    jasenet = [jasen.strip() for jasen in request.form.getlist('jasenet[]') if jasen.strip()]

    if not joukkueenNimi:
        return {"error_message": "Joukkueen nimi ei saa olla tyhjä!"}

    if len(jasenet) < 2:
        return {"error_message": "Joukkueessa tulee olla vähintään 2 jäsentä"}
    
    if len(jasenet) != len(set(map(str.lower, jasenet))):
        return {"error_message": "Jäsenet eivät saa olla saman nimisiä!"}

    cur.execute("""SELECT nimi FROM joukkueet WHERE LOWER(nimi) = LOWER(%s) AND sarja = %s AND joukkueid != %s""", (joukkueenNimi, sarja, joukkueid))
    result = cur.fetchone()
    if result:
        return {"error_message": "Joukkueen nimi on jo käytössä kilpailussa"}

    jasenet_json = json.dumps(jasenet)
    
    try:
        if salasana:
            hashUusiSalasana = hashPassword(joukkueid, salasana)
            cur.execute("""UPDATE joukkueet SET nimi = %s, salasana = %s, sarja = %s, jasenet = %s WHERE joukkueid = %s""",
                        (joukkueenNimi, hashUusiSalasana, sarja, jasenet_json, joukkueid))
        else:
            cur.execute("""UPDATE joukkueet SET nimi = %s, sarja = %s, jasenet = %s WHERE joukkueid = %s""",
                        (joukkueenNimi, sarja, jasenet_json, joukkueid))

        con.commit()
        return {"error_message": ""}
    except:
        return {"error_message": "Joukkueen nimi on jo käytössä."}

# Funktio joukkueen lisäämiseen
def handleJoukkueLisaaminen(con, cur):
    nimi1 = request.form.get("nimi")
    salasana = request.form.get("salasana", "").strip()
    sarja = session.get('sarjaid')
    jasenet = [jasen.strip() for jasen in request.form.getlist('jasenet[]') if jasen.strip()]
    joukkueid = session.get('joukkueid')
    kisaid = session.get('kisaid')

    # Validoidaan nimi ja salasana
    if not nimi1:
        return {"error_message": "Joukkueen nimi ei saa olla tyhjä!"}
    if not salasana:
        return {"error_message": "Joukkueen salasana ei saa olla tyhjä!"}
    
    if len(jasenet) < 2:
        return {"error_message": "Joukkueessa tulee olla vähintään 2 jäsentä"}
    if len(jasenet) != len(set(map(str.lower, jasenet))):
        return {"error_message": "Jäsenet eivät saa olla saman nimisiä!"}

    cur.execute("""SELECT sarjaid FROM sarjat WHERE kilpailu = %s""", (kisaid,))
    sarjaIds = cur.fetchall() 
    sarjaIds = [sarja['sarjaid'] for sarja in sarjaIds]

    # Tarkistetaan, onko joukkue olemassa muissa sarjoissa
    for sarjaid in sarjaIds:
        cur.execute("""SELECT nimi FROM joukkueet WHERE LOWER(nimi) = LOWER(%s) AND sarja = %s""", (nimi1, sarjaid))
        result = cur.fetchone()
        if result:
            return {"error_message": "Joukkueen nimi on jo käytössä kilpailussa"}

    jasenet_json = json.dumps(jasenet)

    # Salasana hashataan
    hashedSalasana = hashPassword(joukkueid, salasana)
    try:
        cur.execute("""INSERT INTO joukkueet (nimi, salasana, jasenet, sarja) VALUES (%s, %s, %s, %s)""", 
                    (nimi1, hashedSalasana, jasenet_json, sarja))
        con.commit()
        return {"error_message": ""}
    except Exception as e:
        return {"error_message": "Joukkueen nimi on jo käytössä toisessa kilpailussa."}

# Funktio joka poistaa joukkueen
def handleJoukkueenPoistaminen(con, cur):    
    joukkueid = session.get('joukkueid')

    try:
        # Tarkistetaan, onko joukkueella rasteja
        cur.execute("""SELECT rastit.* FROM rastit JOIN tupa ON tupa.rasti = rastit.id WHERE tupa.joukkue = %s""", (joukkueid,))
        rasti = cur.fetchall()
        
        if rasti:
            return {"error_message": "Ei voi poistaa, joukkueella on rastileimauksia"}
        
        # Poisto
        cur.execute("""DELETE FROM joukkueet WHERE joukkueid = %s""", (joukkueid,))
        con.commit()           

        session['joukkueid'] = None  
        return {"error_message": ""}
    except:
        return {"error_message": "Joukkueen poisto epäonnistui."}